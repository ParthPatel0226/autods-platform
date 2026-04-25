"""Input data cleaning and sanitization.

Provides a suite of functions to clean a raw DataFrame before it enters
the pipeline: whitespace trimming, type coercion, column-name
normalisation, encoding detection, and more.  Every function is
side-effect-free -- it returns a **new** DataFrame rather than mutating
the original.
"""

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ======================================================================
# Public API
# ======================================================================


def sanitize_dataframe(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Sanitize an input DataFrame.

    Runs a sequence of cleaning steps and collects issues found along the
    way.  Returns a new (cleaned) DataFrame and a list of issue
    dictionaries for auditability.

    Cleaning steps (in order):
        1. Clean column names (lowercase, strip, underscores).
        2. Deduplicate column names.
        3. Strip whitespace from string columns.
        4. Convert empty strings to ``NaN``.
        5. Attempt numeric conversion for string columns.
        6. Fix columns with mixed types.
        7. Parse date-like string columns.

    Args:
        df: Raw input DataFrame.

    Returns:
        A tuple of ``(cleaned_df, issues)`` where *issues* is a list of
        dictionaries describing every fix applied.
    """
    if df.empty:
        return df.copy(), [{"type": "empty_dataframe", "message": "Input DataFrame is empty"}]

    issues: list[dict[str, Any]] = []
    result = df.copy()

    # 1. Column names
    old_cols = list(result.columns)
    result = clean_column_names(result)
    new_cols = list(result.columns)
    renamed = [
        (o, n) for o, n in zip(old_cols, new_cols) if o != n
    ]
    if renamed:
        issues.append({
            "type": "column_rename",
            "message": f"Renamed {len(renamed)} column(s)",
            "details": renamed,
        })

    # 2. Duplicate column names
    result, dup_issues = _deduplicate_columns(result)
    issues.extend(dup_issues)

    # 3. Strip whitespace in string columns
    str_cols = result.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        stripped = result[col].map(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        if not stripped.equals(result[col]):
            issues.append({
                "type": "whitespace_stripped",
                "message": f"Stripped whitespace from column '{col}'",
                "affected_columns": [col],
            })
            result.loc[:, col] = stripped

    # 4. Empty strings -> NaN
    for col in str_cols:
        mask = result[col].map(lambda x: isinstance(x, str) and x == "")
        count = mask.sum()
        if count > 0:
            result.loc[mask, col] = np.nan
            issues.append({
                "type": "empty_to_nan",
                "message": f"Converted {count} empty string(s) to NaN in '{col}'",
                "affected_columns": [col],
            })

    # 5. Numeric conversion for object columns
    result, num_issues = _try_numeric_conversion(result)
    issues.extend(num_issues)

    # 6. Fix mixed types
    result, mixed_names = fix_mixed_types(result)
    if mixed_names:
        issues.append({
            "type": "mixed_types_fixed",
            "message": f"Fixed mixed types in {len(mixed_names)} column(s)",
            "affected_columns": mixed_names,
        })

    # 7. Parse dates
    result, date_issues = _try_date_parsing(result)
    issues.extend(date_issues)

    logger.info(
        "Sanitization complete: %d issue(s) found across %d column(s)",
        len(issues),
        len(result.columns),
    )
    return result, issues


def detect_encoding(file_path: str) -> str:
    """Detect the character encoding of a file.

    Tries ``charset_normalizer`` first, then ``chardet``, and finally
    falls back to ``"utf-8"``.

    Args:
        file_path: Path to the file to inspect.

    Returns:
        Detected encoding string (e.g. ``"utf-8"``, ``"latin-1"``).
    """
    raw = Path(file_path).read_bytes()

    # Try charset_normalizer (modern, better accuracy)
    try:
        from charset_normalizer import from_bytes

        result = from_bytes(raw).best()
        if result is not None:
            encoding = str(result.encoding)
            logger.info("charset_normalizer detected encoding: %s", encoding)
            return encoding
    except ImportError:
        pass

    # Try chardet
    try:
        import chardet

        detection = chardet.detect(raw)
        encoding = detection.get("encoding")
        if encoding:
            logger.info("chardet detected encoding: %s (confidence=%.2f)", encoding, detection.get("confidence", 0))
            return encoding
    except ImportError:
        pass

    logger.info("No encoding detector available; defaulting to utf-8")
    return "utf-8"


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names.

    Transforms every column name to lowercase, strips leading/trailing
    whitespace, and replaces interior whitespace and hyphens with
    underscores.  Non-alphanumeric characters (apart from underscores)
    are removed.

    Args:
        df: Input DataFrame.

    Returns:
        New DataFrame with cleaned column names.
    """
    result = df.copy()

    def _clean(name: Any) -> str:
        s = str(name).strip().lower()
        s = re.sub(r"[\s\-]+", "_", s)
        s = re.sub(r"[^\w]", "", s)
        return s if s else "unnamed"

    result.columns = [_clean(c) for c in result.columns]
    return result


def parse_dates(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Try to parse date-like string columns to ``datetime64``.

    If *columns* is ``None``, all ``object``-type columns are inspected.
    Columns that cannot be parsed are left unchanged.

    Args:
        df: Input DataFrame.
        columns: Explicit list of columns to attempt parsing on.

    Returns:
        New DataFrame with successfully parsed date columns.
    """
    result = df.copy()
    target_cols = columns or list(
        result.select_dtypes(include=["object"]).columns
    )
    for col in target_cols:
        if col not in result.columns:
            continue
        try:
            parsed = pd.to_datetime(result[col], errors="coerce")
            non_null_ratio = parsed.notna().sum() / max(len(parsed), 1)
            if non_null_ratio >= 0.5:
                result[col] = parsed
                logger.debug("Parsed column '%s' as datetime", col)
        except (ValueError, TypeError):
            pass
    return result


def fix_mixed_types(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Fix columns containing mixed Python types.

    For each ``object``-typed column the most common non-null type is
    identified and the column is cast to that type.  Unconvertible values
    become ``NaN``.

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of ``(fixed_df, list_of_fixed_column_names)``.
    """
    result = df.copy()
    fixed_cols: list[str] = []

    for col in result.select_dtypes(include=["object"]).columns:
        types = result[col].dropna().map(type)
        if types.empty:
            continue

        type_counts = types.value_counts()
        if len(type_counts) <= 1:
            continue

        dominant_type = type_counts.index[0]
        if dominant_type in (int, float):
            result[col] = pd.to_numeric(result[col], errors="coerce")
            fixed_cols.append(col)
        elif dominant_type is str:
            result[col] = result[col].astype(str).replace({"nan": np.nan, "None": np.nan})
            fixed_cols.append(col)

    return result, fixed_cols


# ======================================================================
# Internal helpers
# ======================================================================


def _deduplicate_columns(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Append ``_1``, ``_2``, ... to duplicate column names."""
    issues: list[dict[str, Any]] = []
    cols = list(df.columns)
    seen: dict[str, int] = {}
    new_cols: list[str] = []

    for col in cols:
        if col in seen:
            seen[col] += 1
            new_name = f"{col}_{seen[col]}"
            new_cols.append(new_name)
            issues.append({
                "type": "duplicate_column_renamed",
                "message": f"Duplicate column '{col}' renamed to '{new_name}'",
                "affected_columns": [col, new_name],
            })
        else:
            seen[col] = 0
            new_cols.append(col)

    result = df.copy()
    result.columns = new_cols
    return result, issues


def _try_numeric_conversion(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Attempt to convert object columns that look numeric."""
    result = df.copy()
    issues: list[dict[str, Any]] = []

    for col in result.select_dtypes(include=["object"]).columns:
        converted = pd.to_numeric(result[col], errors="coerce")
        non_null_original = result[col].notna().sum()
        if non_null_original == 0:
            continue
        conversion_rate = converted.notna().sum() / non_null_original
        if conversion_rate >= 0.8:
            result[col] = converted
            issues.append({
                "type": "numeric_conversion",
                "message": (
                    f"Converted column '{col}' from string to numeric "
                    f"({conversion_rate:.0%} success rate)"
                ),
                "affected_columns": [col],
            })
    return result, issues


def _try_date_parsing(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Attempt datetime parsing on remaining object columns."""
    result = df.copy()
    issues: list[dict[str, Any]] = []

    date_pattern = re.compile(
        r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
        r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    )

    for col in result.select_dtypes(include=["object"]).columns:
        sample = result[col].dropna().head(20).astype(str)
        if sample.empty:
            continue
        matches = sample.map(lambda x: bool(date_pattern.search(x)))
        if matches.sum() < len(sample) * 0.5:
            continue

        try:
            parsed = pd.to_datetime(result[col], errors="coerce")
            success_rate = parsed.notna().sum() / max(result[col].notna().sum(), 1)
            if success_rate >= 0.5:
                result[col] = parsed
                issues.append({
                    "type": "date_parsed",
                    "message": f"Parsed column '{col}' as datetime ({success_rate:.0%} success)",
                    "affected_columns": [col],
                })
        except (ValueError, TypeError):
            pass

    return result, issues
