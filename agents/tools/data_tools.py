"""Data manipulation tools called by agents.

Replaces ydata-profiling with custom profiling built on pandas/numpy/scipy.
All functions are pure computation -- no LLM calls.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DuckDB helpers
# ---------------------------------------------------------------------------

def load_to_duckdb(
    df: pd.DataFrame,
    table_name: str,
    db_path: str = "data/warehouse.duckdb",
) -> str:
    """Register a DataFrame as a named DuckDB table for SQL queries.

    Args:
        df: Source DataFrame to register.
        table_name: Name to assign to the table inside DuckDB.
        db_path: Path to the DuckDB database file.

    Returns:
        Confirmation message with the registered table name and row count.
    """
    import duckdb

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise ValueError(
            f"Invalid table name '{table_name}'. "
            "Must match ^[a-zA-Z_][a-zA-Z0-9_]*$."
        )

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    try:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        row_count = conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
    finally:
        conn.close()

    msg = f"Loaded {row_count} rows into DuckDB table '{table_name}'"
    logger.info(msg)
    return msg


def query_duckdb(
    query: str,
    table_name: str | None = None,
    db_path: str = "data/warehouse.duckdb",
) -> pd.DataFrame:
    """Execute a SQL query against a DuckDB database.

    Args:
        query: SQL query string to execute.
        table_name: Unused — kept for interface compat.
        db_path: Path to the DuckDB database file.

    Returns:
        DataFrame containing the query results.
    """
    import duckdb

    stripped = query.strip()
    first_word = stripped.split()[0].upper() if stripped else ""
    if first_word not in ("SELECT", "WITH"):
        raise ValueError(
            "Only SELECT or WITH queries are permitted. "
            f"Query starts with: '{first_word}'"
        )

    conn = duckdb.connect(db_path)
    try:
        result = conn.execute(query).fetchdf()
    finally:
        conn.close()
    return result


# ---------------------------------------------------------------------------
# Column stats & type detection  (replaces ydata-profiling)
# ---------------------------------------------------------------------------

def get_column_stats(df: pd.DataFrame) -> dict:
    """Compute descriptive statistics for every column.

    Args:
        df: Input DataFrame.

    Returns:
        Dict mapping column name -> stat summary dict.
        Numeric columns: count, mean, std, min, q25, median, q75, max, skew, kurtosis.
        Categorical/other: count, unique, top, top_freq.
    """
    stats: dict[str, dict] = {}

    for col in df.columns:
        s = df[col]
        base = {
            "dtype": str(s.dtype),
            "count": int(s.count()),
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean()) * 100, 2),
            "unique": int(s.nunique()),
        }

        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            base.update({
                "mean": _safe_float(desc.get("mean")),
                "std": _safe_float(desc.get("std")),
                "min": _safe_float(desc.get("min")),
                "q25": _safe_float(desc.get("25%")),
                "median": _safe_float(desc.get("50%")),
                "q75": _safe_float(desc.get("75%")),
                "max": _safe_float(desc.get("max")),
                "skew": _safe_float(s.skew()),
                "kurtosis": _safe_float(s.kurtosis()),
                "zeros": int((s == 0).sum()),
                "negatives": int((s < 0).sum()),
            })
        else:
            vc = s.value_counts(dropna=True)
            top = vc.index[0] if len(vc) > 0 else None
            base.update({
                "top": str(top) if top is not None else None,
                "top_freq": int(vc.iloc[0]) if len(vc) > 0 else 0,
                "top5": {str(k): int(v) for k, v in vc.head(5).items()},
            })

        stats[col] = base

    return stats


def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    """Infer semantic column types beyond raw dtypes.

    Args:
        df: Input DataFrame.

    Returns:
        Dict mapping column name -> one of:
        'numeric', 'categorical', 'datetime', 'text', 'boolean', 'id'.
    """
    types: dict[str, str] = {}
    n = len(df)

    for col in df.columns:
        s = df[col]
        dtype = s.dtype

        # Boolean
        if pd.api.types.is_bool_dtype(s):
            types[col] = "boolean"
            continue

        # Datetime
        if pd.api.types.is_datetime64_any_dtype(s):
            types[col] = "datetime"
            continue

        # Try parsing as datetime from object columns
        if dtype == "object":
            sample = s.dropna().head(50)
            if len(sample) > 0:
                try:
                    pd.to_datetime(sample)
                    types[col] = "datetime"
                    continue
                except (ValueError, TypeError):
                    pass

        # Numeric
        if pd.api.types.is_numeric_dtype(s):
            nunique = s.nunique()
            # Binary indicator
            if nunique <= 2:
                types[col] = "boolean"
            # ID column heuristic: all unique integers
            elif nunique == n and pd.api.types.is_integer_dtype(s):
                types[col] = "id"
            # Low cardinality numeric -> categorical
            elif nunique <= 20 and nunique / max(n, 1) < 0.05:
                types[col] = "categorical"
            else:
                types[col] = "numeric"
            continue

        # Object / string columns
        nunique = s.nunique()

        # ID heuristic: high cardinality near row count
        if nunique > 0.9 * n and n > 10:
            # Check if it looks like an identifier
            avg_len = s.dropna().astype(str).str.len().mean()
            if avg_len < 30:
                types[col] = "id"
                continue

        # Text heuristic: long strings
        avg_len = s.dropna().astype(str).str.len().mean() if s.count() > 0 else 0
        if avg_len > 50:
            types[col] = "text"
            continue

        # Default: categorical
        types[col] = "categorical"

    return types


def get_missing_summary(df: pd.DataFrame) -> dict:
    """Summarise missing values across all columns.

    Args:
        df: Input DataFrame.

    Returns:
        Dict with:
          - columns: per-column {count, percentage}
          - total_missing: overall count
          - total_cells: row*col
          - overall_pct: total missing / total cells
          - complete_rows: rows with zero missing
          - complete_rows_pct: percentage
    """
    missing_counts = df.isna().sum()
    total_cells = df.shape[0] * df.shape[1]
    total_missing = int(missing_counts.sum())
    complete_rows = int((~df.isna().any(axis=1)).sum())

    columns: dict[str, dict] = {}
    for col in df.columns:
        mc = int(missing_counts[col])
        columns[col] = {
            "count": mc,
            "percentage": round(mc / max(len(df), 1) * 100, 2),
        }

    return {
        "columns": columns,
        "total_missing": total_missing,
        "total_cells": total_cells,
        "overall_pct": round(total_missing / max(total_cells, 1) * 100, 2),
        "complete_rows": complete_rows,
        "complete_rows_pct": round(complete_rows / max(len(df), 1) * 100, 2),
    }


def get_data_profile(df: pd.DataFrame) -> dict:
    """Generate a comprehensive profile report (replaces ydata-profiling).

    Args:
        df: Input DataFrame.

    Returns:
        Dict with: shape, memory_mb, dtypes, column_types, column_stats,
        missing_summary, correlations, sample_rows, warnings.
    """
    col_stats = get_column_stats(df)
    col_types = detect_column_types(df)
    missing = get_missing_summary(df)

    # Correlation matrix for numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    correlations: dict = {}
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        correlations["matrix"] = {
            str(r): {str(c): _safe_float(corr_matrix.loc[r, c]) for c in corr_matrix.columns}
            for r in corr_matrix.index
        }
        # Top correlations (excluding self-correlation)
        pairs = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1:]:
                r = corr_matrix.loc[c1, c2]
                if pd.notna(r):
                    pairs.append({"col1": c1, "col2": c2, "r": round(float(r), 4)})
        pairs.sort(key=lambda p: abs(p["r"]), reverse=True)
        correlations["top_pairs"] = pairs[:20]

    # Warnings
    warnings = _generate_profile_warnings(df, col_stats, col_types, missing)

    return {
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        "column_types": col_types,
        "column_stats": col_stats,
        "missing_summary": missing,
        "correlations": correlations,
        "sample_rows": df.head(5).to_dict(orient="records"),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Missing value handling
# ---------------------------------------------------------------------------

def handle_missing(df: pd.DataFrame, strategy: dict) -> pd.DataFrame:
    """Apply per-column missing-value strategies.

    Args:
        df: Input DataFrame.
        strategy: Map of column -> strategy name.
            Supported: 'mean', 'median', 'mode', 'drop', 'forward_fill',
            'backward_fill', 'zero', 'constant:<value>'.

    Returns:
        New DataFrame with missing values handled.
    """
    result = df.copy()

    for col, method in strategy.items():
        if col not in result.columns:
            logger.warning("Column '%s' not in DataFrame, skipping", col)
            continue

        s = result[col]
        if s.isna().sum() == 0:
            continue

        if method == "mean":
            result[col] = s.fillna(s.mean())
        elif method == "median":
            result[col] = s.fillna(s.median())
        elif method == "mode":
            mode_val = s.mode()
            result[col] = s.fillna(mode_val.iloc[0] if len(mode_val) > 0 else np.nan)
        elif method == "drop":
            result = result.dropna(subset=[col])
        elif method == "forward_fill":
            result[col] = s.ffill()
        elif method == "backward_fill":
            result[col] = s.bfill()
        elif method == "zero":
            result[col] = s.fillna(0)
        elif method.startswith("constant:"):
            val = method.split(":", 1)[1]
            result[col] = s.fillna(val)
        elif method == "knn":
            result = _knn_impute(result, col)
        else:
            logger.warning("Unknown strategy '%s' for column '%s'", method, col)

    return result


def _knn_impute(df: pd.DataFrame, column: str, n_neighbors: int = 5) -> pd.DataFrame:
    """KNN imputation for a single column using sklearn."""
    from sklearn.impute import KNNImputer

    result = df.copy()
    numeric_cols = result.select_dtypes(include="number").columns.tolist()
    if column not in numeric_cols:
        logger.warning("KNN imputation requires numeric column, '%s' skipped", column)
        return result

    imputer = KNNImputer(n_neighbors=n_neighbors)
    result[numeric_cols] = imputer.fit_transform(result[numeric_cols])
    return result


# ---------------------------------------------------------------------------
# Outlier detection & handling
# ---------------------------------------------------------------------------

def detect_outliers(
    df: pd.DataFrame,
    columns: list[str],
    method: str = "iqr",
) -> dict:
    """Detect outliers in numeric columns.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to inspect.
        method: 'iqr' (1.5*IQR) or 'zscore' (|z| > 3).

    Returns:
        Dict mapping column -> {indices, count, percentage, bounds}.
    """
    results: dict[str, dict] = {}

    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue

        s = df[col].dropna()

        if method == "iqr":
            q1 = s.quantile(0.25)
            q3 = s.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (df[col] < lower) | (df[col] > upper)
        elif method == "zscore":
            mean, std = s.mean(), s.std()
            if std == 0:
                results[col] = {"indices": [], "count": 0, "percentage": 0.0}
                continue
            z = ((df[col] - mean) / std).abs()
            mask = z > 3
            lower = mean - 3 * std
            upper = mean + 3 * std
        else:
            raise ValueError(f"Unknown outlier method: {method}")

        outlier_idx = df.index[mask].tolist()
        results[col] = {
            "indices": outlier_idx,
            "count": len(outlier_idx),
            "percentage": round(len(outlier_idx) / max(len(df), 1) * 100, 2),
            "lower_bound": _safe_float(lower),
            "upper_bound": _safe_float(upper),
        }

    return results


def handle_outliers(
    df: pd.DataFrame,
    column: str,
    method: str,
    **kwargs: Any,
) -> pd.DataFrame:
    """Treat outliers in a single column.

    Args:
        df: Input DataFrame.
        column: Target column.
        method: 'clip', 'remove', or 'winsorize'.
        **kwargs: lower/upper for clip; limits for winsorize.

    Returns:
        New DataFrame with outliers treated.
    """
    result = df.copy()
    s = result[column]

    if method == "clip":
        q1 = s.quantile(kwargs.get("lower_q", 0.25))
        q3 = s.quantile(kwargs.get("upper_q", 0.75))
        iqr = q3 - q1
        lower = kwargs.get("lower", q1 - 1.5 * iqr)
        upper = kwargs.get("upper", q3 + 1.5 * iqr)
        result[column] = s.clip(lower=lower, upper=upper)

    elif method == "remove":
        outliers = detect_outliers(df, [column], kwargs.get("detection", "iqr"))
        if column in outliers:
            result = result.drop(index=outliers[column]["indices"])

    elif method == "winsorize":
        from scipy.stats import mstats
        limits = kwargs.get("limits", (0.05, 0.05))
        result[column] = mstats.winsorize(s.values, limits=limits)

    else:
        raise ValueError(f"Unknown outlier method: {method}")

    return result


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------

def detect_duplicates(df: pd.DataFrame) -> dict:
    """Identify duplicate rows.

    Args:
        df: Input DataFrame.

    Returns:
        Dict with count, percentage, and indices of duplicate rows.
    """
    mask = df.duplicated(keep="first")
    dup_idx = df.index[mask].tolist()

    return {
        "count": len(dup_idx),
        "percentage": round(len(dup_idx) / max(len(df), 1) * 100, 2),
        "indices": dup_idx,
    }


def remove_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str = "first",
) -> pd.DataFrame:
    """Remove duplicate rows.

    Args:
        df: Input DataFrame.
        subset: Columns to consider. None = all.
        keep: 'first', 'last', or False (drop all).

    Returns:
        New DataFrame with duplicates removed.
    """
    return df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample_data(
    df: pd.DataFrame,
    n: int = 1000,
    strategy: str = "stratified",
    target_col: str | None = None,
) -> pd.DataFrame:
    """Draw a representative sample.

    Args:
        df: Input DataFrame.
        n: Number of rows.
        strategy: 'random', 'stratified', or 'systematic'.
        target_col: Required for stratified sampling.

    Returns:
        Sampled DataFrame.
    """
    n = min(n, len(df))

    if strategy == "random":
        return df.sample(n=n, random_state=42).reset_index(drop=True)

    elif strategy == "stratified":
        if target_col is None or target_col not in df.columns:
            logger.warning("No valid target_col for stratified; falling back to random")
            return df.sample(n=n, random_state=42).reset_index(drop=True)
        from sklearn.model_selection import train_test_split
        frac = n / len(df)
        if frac >= 1.0:
            return df.copy()
        try:
            _, sample = train_test_split(
                df, test_size=frac, stratify=df[target_col], random_state=42,
            )
        except ValueError:
            logger.warning("Stratified sampling failed (e.g. single class); falling back to random")
            _, sample = train_test_split(
                df, test_size=frac, random_state=42,
            )
        return sample.reset_index(drop=True)

    elif strategy == "systematic":
        step = max(len(df) // n, 1)
        return df.iloc[::step].head(n).reset_index(drop=True)

    else:
        raise ValueError(f"Unknown sampling strategy: {strategy}")


# ---------------------------------------------------------------------------
# Train/test split
# ---------------------------------------------------------------------------

def split_train_test(
    df: pd.DataFrame,
    target_col: str,
    test_size: float = 0.2,
    stratify: bool = True,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split DataFrame into train and test sets.

    Args:
        df: Input DataFrame.
        target_col: Target column name.
        test_size: Fraction for test set.
        stratify: Stratify by target (classification only).
        seed: Random seed.

    Returns:
        (train_df, test_df).
    """
    from sklearn.model_selection import train_test_split

    strat = df[target_col] if stratify else None

    # Stratify only works for classification-like targets
    if strat is not None and strat.nunique() > 50:
        strat = None

    train, test = train_test_split(
        df, test_size=test_size, random_state=seed, stratify=strat,
    )
    return train.reset_index(drop=True), test.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Merge & export
# ---------------------------------------------------------------------------

def merge_dataframes(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    on: str | list[str],
    how: str = "inner",
) -> pd.DataFrame:
    """Merge two DataFrames with validation.

    Args:
        df1: Left DataFrame.
        df2: Right DataFrame.
        on: Join key(s).
        how: 'inner', 'left', 'right', or 'outer'.

    Returns:
        Merged DataFrame.
    """
    pre_rows = len(df1)
    merged = pd.merge(df1, df2, on=on, how=how)
    post_rows = len(merged)

    if post_rows > pre_rows * 3:
        logger.warning(
            "Merge expanded rows from %d to %d — possible many-to-many join",
            pre_rows, post_rows,
        )

    return merged


def export_dataframe(
    df: pd.DataFrame,
    path: str,
    format: str = "csv",
) -> str:
    """Export DataFrame to disk.

    Args:
        df: DataFrame to export.
        path: Destination file path.
        format: 'csv', 'parquet', 'json', or 'excel'.

    Returns:
        Absolute path of written file.
    """
    p = Path(path).resolve()
    allowed_dirs = [Path("outputs").resolve(), Path("data").resolve()]
    if not any(str(p).startswith(str(d)) for d in allowed_dirs):
        raise ValueError(
            f"Export path '{p}' is outside allowed directories "
            f"({', '.join(str(d) for d in allowed_dirs)}). "
            "Use a path under 'outputs/' or 'data/'."
        )
    p.parent.mkdir(parents=True, exist_ok=True)

    if format == "csv":
        df.to_csv(p, index=False)
    elif format == "parquet":
        df.to_parquet(p, index=False)
    elif format == "json":
        df.to_json(p, orient="records", indent=2)
    elif format == "excel":
        df.to_excel(p, index=False)
    else:
        raise ValueError(f"Unsupported export format: {format}")

    logger.info("Exported %d rows to %s", len(df), p)
    return str(p.resolve())


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float | None:
    """Convert to float, returning None for NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else round(f, 6)
    except (ValueError, TypeError):
        return None


def _generate_profile_warnings(
    df: pd.DataFrame,
    col_stats: dict,
    col_types: dict,
    missing: dict,
) -> list[dict]:
    """Generate data quality warnings from profile results."""
    warnings: list[dict] = []

    for col, stats in col_stats.items():
        # High missing
        pct = stats.get("missing_pct", 0)
        if pct > 50:
            warnings.append({
                "column": col,
                "type": "high_missing",
                "severity": "high",
                "message": f"{col}: {pct}% missing values",
            })
        elif pct > 15:
            warnings.append({
                "column": col,
                "type": "moderate_missing",
                "severity": "medium",
                "message": f"{col}: {pct}% missing values",
            })

        # Constant column
        if stats.get("unique", 0) <= 1 and stats["count"] > 0:
            warnings.append({
                "column": col,
                "type": "constant",
                "severity": "high",
                "message": f"{col}: constant column (only 1 unique value)",
            })

        # High cardinality categorical
        if col_types.get(col) == "categorical" and stats.get("unique", 0) > 100:
            warnings.append({
                "column": col,
                "type": "high_cardinality",
                "severity": "medium",
                "message": f"{col}: {stats['unique']} unique values in categorical column",
            })

        # High skew
        skew = stats.get("skew")
        if skew is not None and abs(skew) > 2:
            warnings.append({
                "column": col,
                "type": "high_skew",
                "severity": "low",
                "message": f"{col}: skewness = {skew} (consider transform)",
            })

    # No complete rows
    if missing["complete_rows_pct"] < 50:
        warnings.append({
            "column": None,
            "type": "low_completeness",
            "severity": "high",
            "message": f"Only {missing['complete_rows_pct']}% of rows are fully complete",
        })

    return warnings
