"""Data Profiling Agent.

Profiles data quality, detects schema issues, and recommends/applies
cleaning strategies based on domain context and user mode.

LangGraph node: reads from and writes to AutoDSState.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from core.state import AutoDSState, ColumnInfo
from core.user_modes import should_ask_questions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFrame loader helper (shared across agents)
# ---------------------------------------------------------------------------

def _get_working_df(state: AutoDSState) -> pd.DataFrame:
    """Retrieve the working DataFrame from DuckDB or the first data source.

    Resolution order:
      1. DuckDB table via ``joined_data_ref``
      2. First entry in ``data_sources`` loaded from disk
      3. Empty DataFrame as last resort

    Args:
        state: Current pipeline state.

    Returns:
        A pandas DataFrame with the working dataset.
    """
    # Attempt 1: load from DuckDB
    joined_ref = state.get("joined_data_ref", "")
    if joined_ref:
        try:
            from agents.tools.data_tools import query_duckdb
            df = query_duckdb(f"SELECT * FROM {joined_ref}")
            if not df.empty:
                logger.info(
                    "Loaded working DataFrame from DuckDB table '%s' (%d rows, %d cols)",
                    joined_ref, len(df), len(df.columns),
                )
                return df
        except Exception as exc:
            logger.warning("Failed to load from DuckDB table '%s': %s", joined_ref, exc)

    # Attempt 2: load from first data source path
    data_sources = state.get("data_sources", [])
    if data_sources:
        src = data_sources[0]
        source_path = src.get("source_path", "")
        fmt = src.get("format", "csv")
        if source_path:
            try:
                if fmt in ("csv", "tsv"):
                    df = pd.read_csv(source_path)
                elif fmt in ("xlsx", "xls", "excel"):
                    df = pd.read_excel(source_path)
                elif fmt == "parquet":
                    df = pd.read_parquet(source_path)
                elif fmt == "json":
                    df = pd.read_json(source_path)
                else:
                    df = pd.read_csv(source_path)

                logger.info(
                    "Loaded working DataFrame from '%s' (%d rows, %d cols)",
                    source_path, len(df), len(df.columns),
                )
                return df
            except Exception as exc:
                logger.warning("Failed to load data source '%s': %s", source_path, exc)

    logger.error("No working DataFrame could be loaded")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cardinality classifier
# ---------------------------------------------------------------------------

def _classify_cardinality(nunique: int, nrows: int) -> str:
    """Return a cardinality label for a column.

    Guards against all-null or completely empty columns where
    ``nunique == 0``, returning ``"constant"`` instead of the
    misleading ``"binary"`` label.
    """
    if nunique == 0:
        return "constant"
    if nunique == 1:
        return "constant"
    if nunique == 2:
        return "binary"
    if nunique <= 10:
        return "low"
    if nunique <= 50:
        return "medium"
    if nunique > 0.9 * nrows:
        return "unique"
    return "high"


# ---------------------------------------------------------------------------
# Main profiling node
# ---------------------------------------------------------------------------

def run_data_profiling(state: AutoDSState) -> AutoDSState:
    """Profile the loaded dataset for quality issues and characteristics.

    Steps:
      1. Load the working DataFrame.
      2. Detect column types and classify columns into lists.
      3. Generate a comprehensive data profile.
      4. Identify quality issues: missing values, duplicates, outliers.
      5. In AUTO mode: auto-apply sensible cleaning defaults.
      6. In GUIDED/EXPERT mode: store issues for the dashboard to display.
      7. Write all results back to state.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with profiling results.
    """
    state["current_step"] = "data_profiling"
    logger.info("Starting data profiling")

    df = _get_working_df(state)
    if df.empty:
        state["errors"] = state.get("errors", []) + [{
            "step": "data_profiling",
            "type": "no_data",
            "detail": "No working DataFrame available for profiling",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["data_profiling"]
        return state

    quality_issues: list[dict] = []
    cleaning_actions: list[dict] = []

    # ------------------------------------------------------------------
    # Step 1: Detect column types
    # ------------------------------------------------------------------
    try:
        from agents.tools.data_tools import detect_column_types
        col_types = detect_column_types(df)
    except Exception as exc:
        logger.error("Column type detection failed: %s", exc)
        col_types = {}
        state["errors"] = state.get("errors", []) + [{
            "step": "data_profiling",
            "type": "column_type_detection",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

    # Build per-column metadata and category lists
    columns_info: list[ColumnInfo] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    datetime_columns: list[str] = []
    text_columns: list[str] = []
    id_columns: list[str] = []

    for col in df.columns:
        inferred = col_types.get(col, "unknown")
        nunique = int(df[col].nunique())
        missing_count = int(df[col].isna().sum())
        sample_vals = df[col].dropna().head(5).astype(str).tolist()

        col_info = ColumnInfo(
            name=col,
            dtype=str(df[col].dtype),
            inferred_type=inferred,
            unique_count=nunique,
            missing_count=missing_count,
            missing_pct=round(missing_count / max(len(df), 1) * 100, 2),
            sample_values=sample_vals,
            cardinality=_classify_cardinality(nunique, len(df)),
        )
        columns_info.append(col_info)

        if inferred == "numeric":
            numeric_columns.append(col)
        elif inferred == "categorical":
            categorical_columns.append(col)
        elif inferred == "datetime":
            datetime_columns.append(col)
        elif inferred == "text":
            text_columns.append(col)
        elif inferred == "id":
            id_columns.append(col)
        elif inferred == "boolean":
            categorical_columns.append(col)

    state["columns"] = columns_info
    state["numeric_columns"] = numeric_columns
    state["categorical_columns"] = categorical_columns
    state["datetime_columns"] = datetime_columns
    state["text_columns"] = text_columns
    state["id_columns"] = id_columns
    state["row_count"] = len(df)
    state["column_count"] = len(df.columns)
    logger.info(
        "Detected column types: %d numeric, %d categorical, %d datetime, %d text, %d id",
        len(numeric_columns), len(categorical_columns),
        len(datetime_columns), len(text_columns), len(id_columns),
    )

    # ------------------------------------------------------------------
    # Step 2: Comprehensive data profile
    # ------------------------------------------------------------------
    try:
        from agents.tools.data_tools import get_data_profile
        profile = get_data_profile(df)
        state["data_profile"] = profile
        shape = profile.get("shape", {})
        logger.info("Data profile generated: %d rows, %d columns", shape.get("rows", 0), shape.get("columns", 0))
    except Exception as exc:
        logger.error("Data profile generation failed: %s", exc)
        state["data_profile"] = {}
        state["errors"] = state.get("errors", []) + [{
            "step": "data_profiling",
            "type": "profile_generation",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

    # ------------------------------------------------------------------
    # Step 3: Missing values
    # ------------------------------------------------------------------
    try:
        from agents.tools.data_tools import get_missing_summary
        missing_summary = get_missing_summary(df)

        for col, info in missing_summary.get("columns", {}).items():
            if info["count"] > 0:
                severity = "high" if info["percentage"] > 30 else (
                    "medium" if info["percentage"] > 10 else "low"
                )
                quality_issues.append({
                    "type": "missing_values",
                    "column": col,
                    "count": info["count"],
                    "percentage": info["percentage"],
                    "severity": severity,
                    "message": f"{col}: {info['percentage']}% missing ({info['count']} values)",
                })
        logger.info("Missing value analysis: %.1f%% overall", missing_summary.get("overall_pct", 0))
    except Exception as exc:
        logger.error("Missing value analysis failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 4: Duplicates
    # ------------------------------------------------------------------
    try:
        from agents.tools.data_tools import detect_duplicates
        dup_info = detect_duplicates(df)

        if dup_info["count"] > 0:
            quality_issues.append({
                "type": "duplicates",
                "column": None,
                "count": dup_info["count"],
                "percentage": dup_info["percentage"],
                "severity": "medium" if dup_info["percentage"] < 10 else "high",
                "message": f"{dup_info['count']} duplicate rows ({dup_info['percentage']}%)",
            })
            logger.info("Found %d duplicate rows (%.1f%%)", dup_info["count"], dup_info["percentage"])
    except Exception as exc:
        logger.error("Duplicate detection failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 5: Outliers in numeric columns
    # ------------------------------------------------------------------
    if numeric_columns:
        try:
            from agents.tools.data_tools import detect_outliers
            outlier_info = detect_outliers(df, numeric_columns)

            for col, oinfo in outlier_info.items():
                if oinfo["count"] > 0:
                    severity = "high" if oinfo["percentage"] > 10 else (
                        "medium" if oinfo["percentage"] > 3 else "low"
                    )
                    quality_issues.append({
                        "type": "outliers",
                        "column": col,
                        "count": oinfo["count"],
                        "percentage": oinfo["percentage"],
                        "severity": severity,
                        "lower_bound": oinfo.get("lower_bound"),
                        "upper_bound": oinfo.get("upper_bound"),
                        "message": (
                            f"{col}: {oinfo['count']} outliers ({oinfo['percentage']}%) "
                            f"outside [{oinfo.get('lower_bound')}, {oinfo.get('upper_bound')}]"
                        ),
                    })
            logger.info("Outlier detection complete for %d numeric columns", len(numeric_columns))
        except Exception as exc:
            logger.error("Outlier detection failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 6: Mode-dependent action
    # ------------------------------------------------------------------
    user_mode = state.get("user_mode", "guided")

    if user_mode == "auto":
        # Auto-apply sensible cleaning defaults
        df_cleaned = df.copy()

        # 6a: Handle missing values (median for numeric, mode for categorical)
        try:
            from agents.tools.data_tools import handle_missing
            missing_strategy: dict[str, str] = {}

            for col in numeric_columns:
                if df_cleaned[col].isna().sum() > 0:
                    missing_pct = df_cleaned[col].isna().mean() * 100
                    if missing_pct > 50:
                        missing_strategy[col] = "drop"
                        cleaning_actions.append({
                            "action": "drop_column",
                            "column": col,
                            "reason": f"Dropped column with {missing_pct:.1f}% missing values",
                        })
                    else:
                        missing_strategy[col] = "median"
                        cleaning_actions.append({
                            "action": "impute_median",
                            "column": col,
                            "reason": f"Imputed {df_cleaned[col].isna().sum()} missing values with median",
                        })

            for col in categorical_columns:
                if df_cleaned[col].isna().sum() > 0:
                    missing_pct = df_cleaned[col].isna().mean() * 100
                    if missing_pct > 50:
                        missing_strategy[col] = "drop"
                        cleaning_actions.append({
                            "action": "drop_column",
                            "column": col,
                            "reason": f"Dropped column with {missing_pct:.1f}% missing values",
                        })
                    else:
                        missing_strategy[col] = "mode"
                        cleaning_actions.append({
                            "action": "impute_mode",
                            "column": col,
                            "reason": f"Imputed {df_cleaned[col].isna().sum()} missing values with mode",
                        })

            # Separate drops from imputes
            cols_to_drop = [c for c, s in missing_strategy.items() if s == "drop"]
            impute_strategy = {c: s for c, s in missing_strategy.items() if s != "drop"}

            if cols_to_drop:
                df_cleaned = df_cleaned.drop(columns=cols_to_drop)

            if impute_strategy:
                df_cleaned = handle_missing(df_cleaned, impute_strategy)

            logger.info("Auto-cleaning: imputed %d columns, dropped %d columns",
                        len(impute_strategy), len(cols_to_drop))
        except Exception as exc:
            logger.error("Auto missing-value handling failed: %s", exc)

        # 6b: Remove exact duplicates
        try:
            from agents.tools.data_tools import remove_duplicates
            pre_dup = len(df_cleaned)
            df_cleaned = remove_duplicates(df_cleaned)
            removed = pre_dup - len(df_cleaned)
            if removed > 0:
                cleaning_actions.append({
                    "action": "remove_duplicates",
                    "column": None,
                    "reason": f"Removed {removed} exact duplicate rows",
                })
                logger.info("Auto-cleaning: removed %d duplicate rows", removed)
        except Exception as exc:
            logger.error("Auto duplicate removal failed: %s", exc)

        # Persist cleaned DataFrame back to DuckDB
        joined_ref = state.get("joined_data_ref", "")
        if joined_ref:
            try:
                from agents.tools.data_tools import load_to_duckdb
                load_to_duckdb(df_cleaned, joined_ref)
                state["row_count"] = len(df_cleaned)
                state["column_count"] = len(df_cleaned.columns)
                logger.info("Persisted cleaned DataFrame to DuckDB table '%s'", joined_ref)
            except Exception as exc:
                logger.warning("Failed to persist cleaned data to DuckDB: %s", exc)
    else:
        # Guided / Expert: store issues for the dashboard without auto-cleaning
        logger.info(
            "Mode '%s': storing %d quality issues for user review",
            user_mode, len(quality_issues),
        )

    # ------------------------------------------------------------------
    # Step 7: Update state
    # ------------------------------------------------------------------
    state["quality_issues"] = quality_issues
    state["cleaning_actions"] = cleaning_actions
    state["profile_timestamp"] = datetime.now(timezone.utc).isoformat()
    state["completed_steps"] = state.get("completed_steps", []) + ["data_profiling"]

    logger.info(
        "Data profiling completed: %d quality issues found, %d cleaning actions applied",
        len(quality_issues), len(cleaning_actions),
    )
    return state
