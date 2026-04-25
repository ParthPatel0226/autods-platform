"""Schema matcher for multi-source joins.

Detects potential join keys across multiple data sources by analyzing
column names, types, and value overlap.
"""

import logging
from difflib import SequenceMatcher

import pandas as pd

logger = logging.getLogger(__name__)


def suggest_join_keys(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    name_threshold: float = 0.8,
    overlap_threshold: float = 0.3,
) -> list[dict]:
    """Suggest candidate join keys between two DataFrames.

    Scores candidates by column name similarity, dtype compatibility,
    and value overlap.

    Args:
        left: First DataFrame.
        right: Second DataFrame.
        name_threshold: Minimum name similarity ratio (0-1) to consider.
        overlap_threshold: Minimum value overlap ratio to recommend.

    Returns:
        List of candidate dicts sorted by score descending, each containing:
        - left_col, right_col, name_similarity, dtype_match, value_overlap, score
    """
    candidates: list[dict] = []

    for lcol in left.columns:
        for rcol in right.columns:
            name_sim = _name_similarity(lcol, rcol)
            if name_sim < name_threshold:
                continue

            dtype_match = _dtype_compatible(left[lcol], right[rcol])
            overlap = _value_overlap(left[lcol], right[rcol])

            score = (0.4 * name_sim) + (0.2 * float(dtype_match)) + (0.4 * overlap)

            candidates.append({
                "left_col": lcol,
                "right_col": rcol,
                "name_similarity": round(name_sim, 3),
                "dtype_match": dtype_match,
                "value_overlap": round(overlap, 3),
                "score": round(score, 3),
            })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    logger.info("Found %d join key candidates (threshold %.2f)", len(candidates), name_threshold)
    return candidates


def compare_schemas(
    left: pd.DataFrame,
    right: pd.DataFrame,
) -> dict:
    """Compare schemas of two DataFrames.

    Returns:
        Dict with shared_columns, left_only, right_only, and type_mismatches.
    """
    left_cols = set(left.columns)
    right_cols = set(right.columns)

    shared = left_cols & right_cols
    type_mismatches = []
    for col in shared:
        if left[col].dtype != right[col].dtype:
            type_mismatches.append({
                "column": col,
                "left_dtype": str(left[col].dtype),
                "right_dtype": str(right[col].dtype),
            })

    return {
        "shared_columns": sorted(shared),
        "left_only": sorted(left_cols - right_cols),
        "right_only": sorted(right_cols - left_cols),
        "type_mismatches": type_mismatches,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _name_similarity(a: str, b: str) -> float:
    """Normalized name similarity, case-insensitive."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _dtype_compatible(left_series: pd.Series, right_series: pd.Series) -> bool:
    """Check if two series have broadly compatible dtypes."""
    left_kind = left_series.dtype.kind
    right_kind = right_series.dtype.kind
    # Same kind, or both numeric (i/u/f), or both string-like (O/U/S)
    if left_kind == right_kind:
        return True
    numeric_kinds = {"i", "u", "f"}
    if left_kind in numeric_kinds and right_kind in numeric_kinds:
        return True
    string_kinds = {"O", "U", "S"}
    if left_kind in string_kinds and right_kind in string_kinds:
        return True
    return False


def _value_overlap(left_series: pd.Series, right_series: pd.Series, sample: int = 5000) -> float:
    """Estimate value overlap ratio between two columns.

    Samples up to *sample* values from each for performance.
    Returns fraction of left values found in right.
    """
    left_vals = set(left_series.dropna().head(sample).unique())
    if not left_vals:
        return 0.0
    right_vals = set(right_series.dropna().head(sample).unique())
    return len(left_vals & right_vals) / len(left_vals)
