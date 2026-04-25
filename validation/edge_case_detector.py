"""Detect data quality edge cases that could break the pipeline.

Each check function returns a (possibly empty) list of issue
dictionaries.  The top-level ``detect_all_edge_cases`` aggregates all
checks into a single ordered list.

Issue schema::

    {
        "type": str,              # machine-readable key
        "severity": str,          # "critical" | "warning" | "info"
        "message": str,           # human-readable description
        "suggestion": str,        # recommended action
        "affected_columns": list  # columns involved (may be empty)
    }
"""

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ======================================================================
# Aggregate runner
# ======================================================================


def detect_all_edge_cases(
    df: pd.DataFrame,
    target_column: str | None = None,
) -> list[dict[str, Any]]:
    """Run all edge-case checks and return combined results.

    Args:
        df: The DataFrame to inspect.
        target_column: Optional name of the target / label column.

    Returns:
        List of issue dictionaries sorted by severity (critical first).
    """
    issues: list[dict[str, Any]] = []

    if target_column is not None and target_column in df.columns:
        issues.extend(check_single_class_target(df, target_column))
        issues.extend(check_extreme_imbalance(df, target_column))
        issues.extend(check_target_leakage(df, target_column))

    issues.extend(check_constant_columns(df))
    issues.extend(check_high_cardinality(df))
    issues.extend(check_too_few_rows(df))
    issues.extend(check_too_many_missing(df))
    issues.extend(check_perfect_correlation(df))
    issues.extend(check_id_like_columns(df))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order.get(i["severity"], 3))

    logger.info(
        "Edge-case detection complete: %d issue(s) found", len(issues)
    )
    return issues


# ======================================================================
# Individual checks
# ======================================================================


def check_single_class_target(
    df: pd.DataFrame,
    target: str | None,
) -> list[dict[str, Any]]:
    """Target has only one unique value -- classification is impossible."""
    if target is None or target not in df.columns:
        return []
    n_unique = df[target].dropna().nunique()
    if n_unique <= 1:
        return [{
            "type": "single_class",
            "severity": "critical",
            "message": (
                f"Target column '{target}' has only {n_unique} unique "
                f"value(s). Classification requires at least two classes."
            ),
            "suggestion": "Verify the target column is correct or add more data.",
            "affected_columns": [target],
        }]
    return []


def check_extreme_imbalance(
    df: pd.DataFrame,
    target: str | None,
    threshold: float = 0.01,
) -> list[dict[str, Any]]:
    """Minority class represents less than *threshold* of total rows."""
    if target is None or target not in df.columns:
        return []
    counts = df[target].value_counts(normalize=True)
    if counts.empty:
        return []
    min_ratio = counts.min()
    if min_ratio < threshold:
        minority_class = counts.idxmin()
        return [{
            "type": "extreme_imbalance",
            "severity": "warning",
            "message": (
                f"Target '{target}' is extremely imbalanced. "
                f"Class '{minority_class}' is only {min_ratio:.2%} of rows."
            ),
            "suggestion": (
                "Consider SMOTE, class weighting, or collecting more "
                "minority-class samples."
            ),
            "affected_columns": [target],
        }]
    return []


def check_target_leakage(
    df: pd.DataFrame,
    target: str | None,
) -> list[dict[str, Any]]:
    """Columns with suspiciously high correlation (> 0.95) to target."""
    if target is None or target not in df.columns:
        return []

    issues: list[dict[str, Any]] = []
    numeric_df = df.select_dtypes(include=[np.number])
    if target not in numeric_df.columns:
        return []

    for col in numeric_df.columns:
        if col == target:
            continue
        try:
            corr = numeric_df[target].corr(numeric_df[col])
            if pd.notna(corr) and abs(corr) > 0.95:
                issues.append({
                    "type": "leakage",
                    "severity": "critical",
                    "message": (
                        f"Column '{col}' has a correlation of {corr:.3f} "
                        f"with target '{target}', indicating potential data leakage."
                    ),
                    "suggestion": (
                        f"Investigate whether '{col}' is derived from or "
                        f"equivalent to the target. Remove it if so."
                    ),
                    "affected_columns": [col, target],
                })
        except (ValueError, TypeError):
            pass
    return issues


def check_constant_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Columns with only one unique non-null value."""
    issues: list[dict[str, Any]] = []
    for col in df.columns:
        n_unique = df[col].dropna().nunique()
        if n_unique <= 1:
            issues.append({
                "type": "constant_column",
                "severity": "warning",
                "message": (
                    f"Column '{col}' is constant ({n_unique} unique value). "
                    f"It carries no predictive information."
                ),
                "suggestion": f"Drop column '{col}' before modelling.",
                "affected_columns": [col],
            })
    return issues


def check_high_cardinality(
    df: pd.DataFrame,
    threshold: float = 0.95,
) -> list[dict[str, Any]]:
    """Categorical columns where unique values exceed *threshold* x rows."""
    issues: list[dict[str, Any]] = []
    n_rows = len(df)
    if n_rows == 0:
        return []

    cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns
    for col in cat_cols:
        n_unique = df[col].nunique()
        ratio = n_unique / n_rows
        if ratio > threshold:
            issues.append({
                "type": "high_cardinality",
                "severity": "warning",
                "message": (
                    f"Column '{col}' has very high cardinality "
                    f"({n_unique} unique values in {n_rows} rows, ratio={ratio:.2f})."
                ),
                "suggestion": (
                    f"Column '{col}' may be an ID or free-text field. "
                    "Consider dropping, hashing, or target-encoding."
                ),
                "affected_columns": [col],
            })
    return issues


def check_too_few_rows(
    df: pd.DataFrame,
    min_rows: int = 30,
) -> list[dict[str, Any]]:
    """Dataset has fewer than *min_rows* rows."""
    n_rows = len(df)
    if n_rows < min_rows:
        return [{
            "type": "too_few_rows",
            "severity": "critical" if n_rows < 10 else "warning",
            "message": (
                f"Dataset has only {n_rows} row(s). A minimum of "
                f"{min_rows} is recommended for reliable analysis."
            ),
            "suggestion": "Collect more data or use simpler models.",
            "affected_columns": [],
        }]
    return []


def check_too_many_missing(
    df: pd.DataFrame,
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Columns with more than *threshold* fraction of missing values."""
    issues: list[dict[str, Any]] = []
    n_rows = len(df)
    if n_rows == 0:
        return []

    for col in df.columns:
        missing_ratio = df[col].isna().sum() / n_rows
        if missing_ratio > threshold:
            issues.append({
                "type": "too_many_missing",
                "severity": "warning",
                "message": (
                    f"Column '{col}' is {missing_ratio:.0%} missing "
                    f"(threshold: {threshold:.0%})."
                ),
                "suggestion": (
                    f"Consider dropping '{col}' or using advanced imputation."
                ),
                "affected_columns": [col],
            })
    return issues


def check_perfect_correlation(
    df: pd.DataFrame,
    threshold: float = 0.99,
) -> list[dict[str, Any]]:
    """Pairs of numeric columns with near-perfect correlation."""
    issues: list[dict[str, Any]] = []
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return []

    try:
        corr_matrix = numeric_df.corr()
    except (ValueError, TypeError):
        return []

    seen: set[frozenset[str]] = set()
    for i, col_a in enumerate(corr_matrix.columns):
        for j, col_b in enumerate(corr_matrix.columns):
            if i >= j:
                continue
            pair = frozenset({col_a, col_b})
            if pair in seen:
                continue
            corr_val = corr_matrix.iloc[i, j]
            if pd.notna(corr_val) and abs(corr_val) >= threshold:
                seen.add(pair)
                issues.append({
                    "type": "perfect_correlation",
                    "severity": "warning",
                    "message": (
                        f"Columns '{col_a}' and '{col_b}' have a correlation "
                        f"of {corr_val:.4f}. One is likely redundant."
                    ),
                    "suggestion": (
                        f"Consider dropping one of '{col_a}' / '{col_b}'."
                    ),
                    "affected_columns": [col_a, col_b],
                })
    return issues


def check_id_like_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Detect columns that look like row identifiers.

    Heuristics:
        - Column name matches common ID patterns (``*_id``, ``id``, ``index``).
        - All values are unique.
        - Integer column with sequential values.
    """
    issues: list[dict[str, Any]] = []
    n_rows = len(df)
    if n_rows == 0:
        return []

    id_pattern = re.compile(
        r"^(id|index|row_?id|row_?num(ber)?|pk|"
        r".*_id|.*_pk|.*_key|uuid|guid)$",
        re.IGNORECASE,
    )

    for col in df.columns:
        is_id = False
        reasons: list[str] = []

        # Name match
        if id_pattern.match(str(col)):
            reasons.append("name matches ID pattern")
            is_id = True

        # All unique
        if df[col].nunique() == n_rows and n_rows > 1:
            reasons.append("all values unique")
            is_id = True

        # Sequential integers
        if pd.api.types.is_integer_dtype(df[col]):
            sorted_vals = df[col].dropna().sort_values()
            if len(sorted_vals) > 1:
                diffs = sorted_vals.diff().dropna()
                if (diffs == 1).all():
                    reasons.append("sequential integers")
                    is_id = True

        if is_id:
            issues.append({
                "type": "id_like_column",
                "severity": "info",
                "message": (
                    f"Column '{col}' looks like an ID column "
                    f"({', '.join(reasons)})."
                ),
                "suggestion": (
                    f"Exclude '{col}' from feature engineering and modelling."
                ),
                "affected_columns": [col],
            })

    return issues
