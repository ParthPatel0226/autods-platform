"""Validate that prediction data matches the training schema.

Provides three functions:
    - ``extract_training_schema`` -- capture schema from training data.
    - ``validate_prediction_schema`` -- check new data against schema.
    - ``adapt_prediction_data`` -- best-effort coercion of new data to
      match the training schema.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ======================================================================
# Schema extraction
# ======================================================================


def extract_training_schema(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Extract a column-level schema from a training DataFrame.

    For every column the schema records data type, basic statistics (for
    numeric columns), and the set of known categories (for categoricals).

    Args:
        df: Training DataFrame.

    Returns:
        Dictionary mapping column names to their schema metadata::

            {
                "column_name": {
                    "dtype": "float64",
                    "min": 0.0,
                    "max": 100.0,
                    "mean": 50.3,
                    "std": 12.1,
                    "categories": None,
                    "n_unique": 98,
                }
            }
    """
    schema: dict[str, dict[str, Any]] = {}

    for col in df.columns:
        entry: dict[str, Any] = {
            "dtype": str(df[col].dtype),
            "n_unique": int(df[col].nunique()),
        }

        if pd.api.types.is_numeric_dtype(df[col]):
            entry["min"] = float(df[col].min()) if df[col].notna().any() else None
            entry["max"] = float(df[col].max()) if df[col].notna().any() else None
            entry["mean"] = float(df[col].mean()) if df[col].notna().any() else None
            entry["std"] = float(df[col].std()) if df[col].notna().any() else None
            entry["categories"] = None
        elif isinstance(df[col].dtype, pd.CategoricalDtype) or df[col].dtype == "object":
            cats = df[col].dropna().unique().tolist()
            entry["categories"] = cats
            entry["min"] = None
            entry["max"] = None
            entry["mean"] = None
            entry["std"] = None
        else:
            entry["min"] = None
            entry["max"] = None
            entry["mean"] = None
            entry["std"] = None
            entry["categories"] = None

        schema[col] = entry

    logger.info("Extracted training schema for %d column(s)", len(schema))
    return schema


# ======================================================================
# Validation
# ======================================================================


def validate_prediction_schema(
    prediction_df: pd.DataFrame,
    training_schema: dict[str, dict[str, Any]],
) -> tuple[bool, list[dict[str, Any]]]:
    """Validate prediction data against the training schema.

    Checks performed:
        1. All required columns are present.
        2. No unexpected extra columns (warning only).
        3. Data types match.
        4. Numeric values within training range (warning if outside).
        5. Categorical values are in known categories (warning if new).

    Args:
        prediction_df: New data to validate.
        training_schema: Schema produced by ``extract_training_schema``.

    Returns:
        Tuple of ``(is_valid, issues)`` where *is_valid* is ``False``
        if any critical issue is found.
    """
    issues: list[dict[str, Any]] = []
    has_critical = False

    train_cols = set(training_schema.keys())
    pred_cols = set(prediction_df.columns)

    # 1. Missing columns
    missing = train_cols - pred_cols
    if missing:
        has_critical = True
        issues.append({
            "type": "missing_columns",
            "severity": "critical",
            "message": f"Missing required column(s): {sorted(missing)}",
            "columns": sorted(missing),
        })

    # 2. Extra columns
    extra = pred_cols - train_cols
    if extra:
        issues.append({
            "type": "extra_columns",
            "severity": "info",
            "message": f"Extra column(s) not in training schema: {sorted(extra)}",
            "columns": sorted(extra),
        })

    # Per-column checks for columns present in both
    common = train_cols & pred_cols
    for col in sorted(common):
        schema_entry = training_schema[col]

        # 3. Dtype mismatch
        expected_dtype = schema_entry["dtype"]
        actual_dtype = str(prediction_df[col].dtype)
        if not _dtypes_compatible(expected_dtype, actual_dtype):
            issues.append({
                "type": "dtype_mismatch",
                "severity": "warning",
                "message": (
                    f"Column '{col}': expected dtype '{expected_dtype}', "
                    f"got '{actual_dtype}'."
                ),
                "columns": [col],
            })

        # 4. Numeric range
        if pd.api.types.is_numeric_dtype(prediction_df[col]):
            train_min = schema_entry.get("min")
            train_max = schema_entry.get("max")
            if train_min is not None and train_max is not None:
                pred_min = prediction_df[col].min()
                pred_max = prediction_df[col].max()
                if pred_min < train_min or pred_max > train_max:
                    issues.append({
                        "type": "out_of_range",
                        "severity": "warning",
                        "message": (
                            f"Column '{col}': values [{pred_min}, {pred_max}] "
                            f"exceed training range [{train_min}, {train_max}]."
                        ),
                        "columns": [col],
                    })

        # 5. Unknown categories
        known_cats = schema_entry.get("categories")
        if known_cats is not None:
            actual_cats = set(prediction_df[col].dropna().unique())
            known_set = set(known_cats)
            new_cats = actual_cats - known_set
            if new_cats:
                # Limit display to avoid enormous messages
                sample = sorted(str(c) for c in list(new_cats)[:10])
                issues.append({
                    "type": "unknown_categories",
                    "severity": "warning",
                    "message": (
                        f"Column '{col}': {len(new_cats)} unseen "
                        f"category value(s): {sample}"
                    ),
                    "columns": [col],
                })

    is_valid = not has_critical
    logger.info(
        "Schema validation %s: %d issue(s)",
        "passed" if is_valid else "FAILED",
        len(issues),
    )
    return is_valid, issues


# ======================================================================
# Adaptation
# ======================================================================


def adapt_prediction_data(
    prediction_df: pd.DataFrame,
    training_schema: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Best-effort adaptation of prediction data to match training schema.

    Operations:
        - Reorder columns to match training order.
        - Cast columns to expected dtypes where possible.
        - Fill missing required columns with training-mean (numeric) or
          mode placeholder (categorical).

    Args:
        prediction_df: Raw prediction DataFrame.
        training_schema: Schema from ``extract_training_schema``.

    Returns:
        Adapted DataFrame. Columns not in the schema are dropped.
    """
    result = prediction_df.copy()
    schema_cols = list(training_schema.keys())

    # Add missing columns with defaults
    for col in schema_cols:
        if col not in result.columns:
            entry = training_schema[col]
            if entry.get("mean") is not None:
                result[col] = entry["mean"]
                logger.info(
                    "Added missing column '%s' with training mean %.4f",
                    col,
                    entry["mean"],
                )
            elif entry.get("categories"):
                default = entry["categories"][0]
                result[col] = default
                logger.info(
                    "Added missing column '%s' with default category '%s'",
                    col,
                    default,
                )
            else:
                result[col] = np.nan
                logger.info(
                    "Added missing column '%s' filled with NaN", col
                )

    # Reorder and keep only schema columns
    result = result[[c for c in schema_cols if c in result.columns]]

    # Cast dtypes
    for col in result.columns:
        expected = training_schema[col]["dtype"]
        actual = str(result[col].dtype)
        if not _dtypes_compatible(expected, actual):
            try:
                if "int" in expected or "float" in expected:
                    result[col] = pd.to_numeric(result[col], errors="coerce")
                else:
                    result[col] = result[col].astype(expected)
                logger.debug("Cast column '%s' to %s", col, expected)
            except (ValueError, TypeError):
                logger.warning(
                    "Could not cast column '%s' from %s to %s",
                    col,
                    actual,
                    expected,
                )

    return result


# ======================================================================
# Internal helpers
# ======================================================================


def _dtypes_compatible(expected: str, actual: str) -> bool:
    """Check if two dtype strings are broadly compatible.

    Treats all integer variants as compatible with each other, and
    likewise for floats.
    """
    if expected == actual:
        return True

    int_types = {"int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64", "Int64", "Int32"}
    float_types = {"float16", "float32", "float64", "Float64"}

    if expected in int_types and actual in int_types:
        return True
    if expected in float_types and actual in float_types:
        return True
    if expected in int_types and actual in float_types:
        return True
    if expected in float_types and actual in int_types:
        return True

    return False
