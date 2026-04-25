"""Feature Engineering Agent.

Creates domain-aware features with interactive per-column control.
Handles missing values, encoding, scaling, and domain-specific features.

LangGraph nodes: generate_fe_questions and execute_feature_engineering.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from core.state import AutoDSState
from core.user_modes import (
    auto_select_best_option,
    filter_questions_for_mode,
    should_ask_questions,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared DataFrame loader
# ---------------------------------------------------------------------------

def _get_working_df(state: AutoDSState) -> pd.DataFrame:
    """Retrieve the working DataFrame from DuckDB or the first data source."""
    joined_ref = state.get("joined_data_ref", "")
    if joined_ref:
        try:
            from agents.tools.data_tools import query_duckdb
            df = query_duckdb(f"SELECT * FROM {joined_ref}")
            if not df.empty:
                return df
        except Exception as exc:
            logger.warning("Failed to load from DuckDB table '%s': %s", joined_ref, exc)

    data_sources = state.get("data_sources", [])
    if data_sources:
        src = data_sources[0]
        source_path = src.get("source_path", "")
        fmt = src.get("format", "csv")
        if source_path:
            try:
                if fmt in ("csv", "tsv"):
                    return pd.read_csv(source_path)
                elif fmt in ("xlsx", "xls", "excel"):
                    return pd.read_excel(source_path)
                elif fmt == "parquet":
                    return pd.read_parquet(source_path)
                elif fmt == "json":
                    return pd.read_json(source_path)
                else:
                    return pd.read_csv(source_path)
            except Exception as exc:
                logger.warning("Failed to load data source '%s': %s", source_path, exc)

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Imputation strategy recommendation
# ---------------------------------------------------------------------------

def _recommend_imputation(col_info: dict, inferred_type: str) -> str:
    """Return the recommended imputation strategy for a column."""
    missing_pct = col_info.get("missing_pct", 0)
    if missing_pct > 50:
        return "drop_column"
    if inferred_type in ("numeric",):
        return "median"
    if inferred_type in ("categorical", "boolean"):
        return "mode"
    if inferred_type == "datetime":
        return "forward_fill"
    return "leave_as_is"


# ---------------------------------------------------------------------------
# Encoding strategy recommendation
# ---------------------------------------------------------------------------

def _recommend_encoding(unique_count: int, cardinality: str) -> str:
    """Return the recommended encoding strategy for a categorical column."""
    if unique_count <= 2:
        return "one_hot"
    if unique_count <= 10:
        return "one_hot"
    if unique_count <= 50:
        return "target_encode"
    return "frequency_encode"


# ---------------------------------------------------------------------------
# Question builders
# ---------------------------------------------------------------------------

def _build_imputation_question(state: AutoDSState) -> dict | None:
    """Build per-column missing value strategy question."""
    columns_info = state.get("columns", [])
    cols_with_missing = [
        ci for ci in columns_info if ci.get("missing_count", 0) > 0
    ]

    if not cols_with_missing:
        return None

    per_column_options: list[dict] = []
    for ci in cols_with_missing:
        col_name = ci["name"]
        inferred = ci.get("inferred_type", "unknown")
        recommended = _recommend_imputation(ci, inferred)

        strategies = [
            {"value": "drop_column", "label": "Drop entire column"},
            {"value": "mean", "label": "Mean"},
            {"value": "median", "label": "Median"},
            {"value": "mode", "label": "Mode (most frequent)"},
            {"value": "forward_fill", "label": "Forward fill"},
            {"value": "knn", "label": "KNN imputation"},
            {"value": "leave_as_is", "label": "Leave as-is"},
        ]

        # Mark the recommended option
        for opt in strategies:
            opt["recommended"] = opt["value"] == recommended

        per_column_options.append({
            "column": col_name,
            "missing_count": ci.get("missing_count", 0),
            "missing_pct": ci.get("missing_pct", 0),
            "dtype": ci.get("dtype", ""),
            "inferred_type": inferred,
            "options": strategies,
            "recommended": recommended,
        })

    return {
        "id": "fe_q1_imputation",
        "step": "feature_engineering",
        "question": "How should missing values be handled for each column?",
        "type": "per_column_table",
        "columns": per_column_options,
        "user_response": None,
    }


def _build_encoding_question(state: AutoDSState) -> dict | None:
    """Build per-column encoding strategy question for categorical columns."""
    columns_info = state.get("columns", [])
    categorical_cols = [
        ci for ci in columns_info
        if ci.get("inferred_type") in ("categorical", "boolean")
    ]

    if not categorical_cols:
        return None

    per_column_options: list[dict] = []
    for ci in categorical_cols:
        col_name = ci["name"]
        nunique = ci.get("unique_count", 0)
        cardinality = ci.get("cardinality", "medium")
        recommended = _recommend_encoding(nunique, cardinality)

        strategies = [
            {"value": "one_hot", "label": "One-Hot Encoding"},
            {"value": "target_encode", "label": "Target Encoding"},
            {"value": "frequency_encode", "label": "Frequency Encoding"},
            {"value": "label_encode", "label": "Label Encoding"},
            {"value": "ordinal", "label": "Ordinal Encoding"},
            {"value": "drop", "label": "Drop column"},
        ]

        # Filter impractical options
        if nunique > 20:
            strategies = [s for s in strategies if s["value"] != "one_hot"]
        if nunique > 50:
            strategies = [s for s in strategies if s["value"] not in ("one_hot", "label_encode")]

        for opt in strategies:
            opt["recommended"] = opt["value"] == recommended

        per_column_options.append({
            "column": col_name,
            "unique_count": nunique,
            "cardinality": cardinality,
            "options": strategies,
            "recommended": recommended,
        })

    return {
        "id": "fe_q2_encoding",
        "step": "feature_engineering",
        "question": "How should categorical columns be encoded?",
        "type": "per_column_table",
        "columns": per_column_options,
        "user_response": None,
    }


def _build_scaling_question(state: AutoDSState) -> dict | None:
    """Build global scaling strategy question."""
    numeric_cols = state.get("numeric_columns", [])
    if not numeric_cols:
        return None

    return {
        "id": "fe_q3_scaling",
        "step": "feature_engineering",
        "question": "Which scaling method should be applied to numeric features?",
        "type": "single_select",
        "options": [
            {"value": "standard", "label": "StandardScaler (zero mean, unit variance)", "recommended": False},
            {"value": "minmax", "label": "MinMaxScaler (0-1 range)", "recommended": False},
            {"value": "robust", "label": "RobustScaler (median/IQR, handles outliers)", "recommended": True},
            {"value": "none", "label": "No scaling", "recommended": False},
        ],
        "user_response": None,
    }


def _build_outlier_question(state: AutoDSState) -> dict | None:
    """Build per-column outlier handling question for numeric columns."""
    quality_issues = state.get("quality_issues", [])
    outlier_issues = [qi for qi in quality_issues if qi.get("type") == "outliers"]

    if not outlier_issues:
        return None

    per_column_options: list[dict] = []
    for issue in outlier_issues:
        col_name = issue.get("column", "")
        if not col_name:
            continue

        strategies = [
            {"value": "leave", "label": "Leave as-is", "recommended": True},
            {"value": "cap_iqr", "label": "Cap at IQR bounds (clip)", "recommended": False},
            {"value": "remove", "label": "Remove outlier rows", "recommended": False},
            {"value": "winsorize", "label": "Winsorize (5th/95th percentile)", "recommended": False},
        ]

        # If outlier percentage is very high, recommend capping instead
        if issue.get("percentage", 0) > 5:
            for opt in strategies:
                opt["recommended"] = opt["value"] == "cap_iqr"

        per_column_options.append({
            "column": col_name,
            "outlier_count": issue.get("count", 0),
            "outlier_pct": issue.get("percentage", 0),
            "options": strategies,
        })

    if not per_column_options:
        return None

    return {
        "id": "fe_q4_outliers",
        "step": "feature_engineering",
        "question": "How should outliers be handled for each numeric column?",
        "type": "per_column_table",
        "columns": per_column_options,
        "user_response": None,
        "expert_only": True,
    }


# ---------------------------------------------------------------------------
# Question generation node
# ---------------------------------------------------------------------------

def generate_fe_questions(state: AutoDSState) -> AutoDSState:
    """Generate feature engineering questions based on data characteristics.

    Builds per-column questions for imputation, encoding, scaling, and
    outlier handling. Adds domain-specific feature questions if available.

    In AUTO mode all questions are auto-answered with recommended defaults.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with ``fe_questions_asked`` populated.
    """
    state["current_step"] = "fe_questions"
    logger.info("Generating feature engineering questions")

    questions: list[dict] = []

    # Core per-column questions
    imputation_q = _build_imputation_question(state)
    if imputation_q is not None:
        questions.append(imputation_q)

    encoding_q = _build_encoding_question(state)
    if encoding_q is not None:
        questions.append(encoding_q)

    scaling_q = _build_scaling_question(state)
    if scaling_q is not None:
        questions.append(scaling_q)

    outlier_q = _build_outlier_question(state)
    if outlier_q is not None:
        questions.append(outlier_q)

    # Domain-specific feature questions
    domain_config = state.get("domain_config", {})
    domain_fe_qs = domain_config.get("feature_questions", [])
    for dq in domain_fe_qs:
        dq_copy = dict(dq)
        dq_copy.setdefault("step", "feature_engineering")
        dq_copy.setdefault("user_response", None)
        dq_copy["domain_specific"] = True
        questions.append(dq_copy)

    # Filter by user mode
    user_mode = state.get("user_mode", "guided")
    filtered = filter_questions_for_mode(questions, user_mode)

    if user_mode == "auto":
        # Auto-answer everything with recommended defaults
        auto_strategies = _auto_select_fe_strategies(questions, state)
        state["imputation_strategy"] = auto_strategies["imputation"]
        state["encoding_strategy"] = auto_strategies["encoding"]
        state["scaling_strategy"] = auto_strategies["scaling"]
        state["outlier_strategy"] = auto_strategies["outliers"]
        state["fe_questions_asked"] = questions  # store for audit trail
        logger.info("AUTO mode: auto-selected all FE strategies")
    else:
        state["fe_questions_asked"] = filtered
        logger.info("Generated %d FE questions for mode '%s'", len(filtered), user_mode)

    return state


def _auto_select_fe_strategies(
    questions: list[dict], state: AutoDSState,
) -> dict[str, Any]:
    """Extract recommended strategies from questions for AUTO mode."""
    strategies: dict[str, Any] = {
        "imputation": {},
        "encoding": {},
        "scaling": "robust",
        "outliers": {},
    }

    for q in questions:
        qid = q.get("id", "")

        if qid == "fe_q1_imputation":
            for col_opt in q.get("columns", []):
                strategies["imputation"][col_opt["column"]] = col_opt.get(
                    "recommended", "leave_as_is"
                )

        elif qid == "fe_q2_encoding":
            for col_opt in q.get("columns", []):
                strategies["encoding"][col_opt["column"]] = col_opt.get(
                    "recommended", "one_hot"
                )

        elif qid == "fe_q3_scaling":
            strategies["scaling"] = auto_select_best_option(q, state) or "robust"

        elif qid == "fe_q4_outliers":
            for col_opt in q.get("columns", []):
                # Find the recommended option
                rec = "leave"
                for opt in col_opt.get("options", []):
                    if opt.get("recommended"):
                        rec = opt["value"]
                        break
                strategies["outliers"][col_opt["column"]] = rec

    return strategies


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _apply_imputation(df: pd.DataFrame, strategy: dict[str, str]) -> tuple[pd.DataFrame, list[str]]:
    """Apply imputation strategies. Returns (new_df, list_of_actions)."""
    actions: list[str] = []
    if not strategy:
        return df, actions

    cols_to_drop = [c for c, s in strategy.items() if s == "drop_column" and c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        actions.append(f"Dropped columns: {cols_to_drop}")

    # Group remaining by method
    from agents.tools.data_tools import handle_missing as _handle_missing

    impute_map: dict[str, str] = {}
    for col, method in strategy.items():
        if method == "drop_column" or col not in df.columns:
            continue
        if method == "leave_as_is":
            continue
        impute_map[col] = method

    if impute_map:
        df = _handle_missing(df, impute_map)
        actions.append(f"Imputed {len(impute_map)} columns: {dict(list(impute_map.items())[:5])}")

    return df, actions


def _apply_encoding(
    df: pd.DataFrame,
    strategy: dict[str, str],
    target_col: str | None,
) -> tuple[pd.DataFrame, list[str]]:
    """Apply encoding strategies. Returns (new_df, list_of_created_features)."""
    created: list[str] = []
    if not strategy:
        return df, created

    cols_to_drop = [c for c, s in strategy.items() if s == "drop" and c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Group columns by encoding method
    method_groups: dict[str, list[str]] = {}
    for col, method in strategy.items():
        if method == "drop" or col not in df.columns:
            continue
        method_groups.setdefault(method, []).append(col)

    pre_cols = set(df.columns)

    for method, cols in method_groups.items():
        try:
            if method == "one_hot":
                from agents.tools.feature_tools import one_hot_encode
                df = one_hot_encode(df, cols)
            elif method == "target_encode":
                if target_col and target_col in df.columns:
                    from agents.tools.feature_tools import target_encode
                    df = target_encode(df, cols, target_col)
                else:
                    from agents.tools.feature_tools import frequency_encode
                    df = frequency_encode(df, cols)
                    logger.info("No target column for target encoding; fell back to frequency encoding")
            elif method == "frequency_encode":
                from agents.tools.feature_tools import frequency_encode
                df = frequency_encode(df, cols)
            elif method == "label_encode":
                from agents.tools.feature_tools import label_encode
                df = label_encode(df, cols)
            elif method == "ordinal":
                from agents.tools.feature_tools import ordinal_encode
                df = ordinal_encode(df, cols)
            else:
                logger.warning("Unknown encoding method '%s', skipping columns: %s", method, cols)
        except Exception as exc:
            logger.error("Encoding '%s' failed for columns %s: %s", method, cols, exc)

    new_cols = set(df.columns) - pre_cols
    created.extend(sorted(new_cols))
    return df, created


def _apply_scaling(
    df: pd.DataFrame,
    scaling: str,
    numeric_cols: list[str],
) -> pd.DataFrame:
    """Apply a global scaling strategy to numeric columns."""
    cols_to_scale = [c for c in numeric_cols if c in df.columns]
    if not cols_to_scale or scaling == "none":
        return df

    try:
        if scaling == "standard":
            from agents.tools.feature_tools import standard_scale
            df = standard_scale(df, cols_to_scale)
        elif scaling == "minmax":
            from agents.tools.feature_tools import minmax_scale
            df = minmax_scale(df, cols_to_scale)
        elif scaling == "robust":
            from agents.tools.feature_tools import robust_scale
            df = robust_scale(df, cols_to_scale)
        else:
            logger.warning("Unknown scaling strategy '%s', skipping", scaling)
    except Exception as exc:
        logger.error("Scaling ('%s') failed: %s", scaling, exc)

    return df


def _apply_outlier_handling(
    df: pd.DataFrame,
    strategy: dict[str, str],
) -> pd.DataFrame:
    """Apply per-column outlier handling strategies."""
    if not strategy:
        return df

    from agents.tools.data_tools import handle_outliers

    for col, method in strategy.items():
        if method == "leave" or col not in df.columns:
            continue
        try:
            if method == "cap_iqr":
                df = handle_outliers(df, col, "clip")
            elif method == "remove":
                df = handle_outliers(df, col, "remove")
            elif method == "winsorize":
                df = handle_outliers(df, col, "winsorize")
            else:
                logger.warning("Unknown outlier method '%s' for column '%s'", method, col)
        except Exception as exc:
            logger.error("Outlier handling failed for '%s': %s", col, exc)

    return df


def _apply_datetime_features(
    df: pd.DataFrame,
    datetime_cols: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Extract date parts from datetime columns."""
    created: list[str] = []
    if not datetime_cols:
        return df, created

    from agents.tools.feature_tools import date_parts

    pre_cols = set(df.columns)
    for dt_col in datetime_cols:
        if dt_col not in df.columns:
            continue
        try:
            df = date_parts(df, dt_col)
        except Exception as exc:
            logger.warning("Date parts extraction failed for '%s': %s", dt_col, exc)

    new_cols = set(df.columns) - pre_cols
    created.extend(sorted(new_cols))
    return df, created


def _run_preliminary_importance(
    df: pd.DataFrame,
    target_col: str,
) -> dict[str, float]:
    """Run a quick feature importance analysis using a tree model."""
    try:
        from agents.tools.feature_tools import select_features_importance
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

        feature_cols = [c for c in df.columns if c != target_col]
        numeric_features = df[feature_cols].select_dtypes(include="number").columns.tolist()
        if not numeric_features:
            return {}

        X = df[numeric_features].fillna(0)
        y = df[target_col]

        if y.nunique() <= 20:
            model = RandomForestClassifier(
                n_estimators=50, max_depth=5, random_state=42, n_jobs=-1,
            )
        else:
            model = RandomForestRegressor(
                n_estimators=50, max_depth=5, random_state=42, n_jobs=-1,
            )

        model.fit(X, y)
        importances = dict(zip(
            numeric_features,
            [round(float(v), 6) for v in model.feature_importances_],
        ))
        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    except Exception as exc:
        logger.warning("Preliminary feature importance failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Feature engineering execution node
# ---------------------------------------------------------------------------

def execute_feature_engineering(state: AutoDSState) -> AutoDSState:
    """Execute feature engineering based on user selections or auto-choices.

    Steps:
      1. Load working DataFrame.
      2. Apply imputation strategies.
      3. Apply outlier handling.
      4. Apply encoding strategies.
      5. Extract date parts from datetime columns.
      6. Apply scaling.
      7. Run preliminary feature importance if target exists.
      8. Persist results and update state.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with engineered features.
    """
    state["current_step"] = "fe_execute"
    logger.info("Starting feature engineering execution")

    df = _get_working_df(state)
    if df.empty:
        state["errors"] = state.get("errors", []) + [{
            "step": "feature_engineering",
            "type": "no_data",
            "detail": "No working DataFrame available for feature engineering",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["feature_engineering"]
        return state

    target_col = state.get("target_column")
    numeric_cols = state.get("numeric_columns", [])
    datetime_cols = state.get("datetime_columns", [])
    id_cols = state.get("id_columns", [])
    all_features_created: list[str] = []
    fe_choices: dict[str, Any] = {}

    initial_shape = df.shape
    logger.info("Initial DataFrame shape: %d rows, %d cols", *initial_shape)

    # Drop ID columns (they add no predictive value)
    id_cols_present = [c for c in id_cols if c in df.columns]
    if id_cols_present:
        df = df.drop(columns=id_cols_present)
        logger.info("Dropped ID columns: %s", id_cols_present)

    # ------------------------------------------------------------------
    # Step 1: Imputation
    # ------------------------------------------------------------------
    imputation_strategy = state.get("imputation_strategy", {})
    try:
        df, imp_actions = _apply_imputation(df, imputation_strategy)
        fe_choices["imputation"] = imputation_strategy
        for action in imp_actions:
            logger.info("Imputation: %s", action)
    except Exception as exc:
        logger.error("Imputation step failed: %s", exc)
        state["errors"] = state.get("errors", []) + [{
            "step": "feature_engineering",
            "type": "imputation",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

    # ------------------------------------------------------------------
    # Step 2: Outlier handling
    # ------------------------------------------------------------------
    outlier_strategy = state.get("outlier_strategy", {})
    try:
        df = _apply_outlier_handling(df, outlier_strategy)
        fe_choices["outlier_handling"] = outlier_strategy
    except Exception as exc:
        logger.error("Outlier handling step failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 3: Encoding
    # ------------------------------------------------------------------
    encoding_strategy = state.get("encoding_strategy", {})
    try:
        df, enc_features = _apply_encoding(df, encoding_strategy, target_col)
        all_features_created.extend(enc_features)
        fe_choices["encoding"] = encoding_strategy
        logger.info("Encoding created %d new features", len(enc_features))
    except Exception as exc:
        logger.error("Encoding step failed: %s", exc)
        state["errors"] = state.get("errors", []) + [{
            "step": "feature_engineering",
            "type": "encoding",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

    # ------------------------------------------------------------------
    # Step 4: Datetime features
    # ------------------------------------------------------------------
    try:
        df, dt_features = _apply_datetime_features(df, datetime_cols)
        all_features_created.extend(dt_features)
        if dt_features:
            logger.info("Created %d datetime features", len(dt_features))
    except Exception as exc:
        logger.error("Datetime feature extraction failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 5: Domain-specific features
    # ------------------------------------------------------------------
    domain_config = state.get("domain_config", {})
    domain_features_fn = domain_config.get("feature_creation_fn")
    if callable(domain_features_fn):
        try:
            pre_cols = set(df.columns)
            df = domain_features_fn(df, state)
            domain_created = sorted(set(df.columns) - pre_cols)
            all_features_created.extend(domain_created)
            logger.info("Created %d domain-specific features", len(domain_created))
        except Exception as exc:
            logger.warning("Domain feature creation failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 6: Scaling (applied after encoding to include encoded columns)
    # ------------------------------------------------------------------
    scaling_strategy = state.get("scaling_strategy", "robust")
    # Identify current numeric columns (may have changed after encoding)
    current_numeric = df.select_dtypes(include="number").columns.tolist()
    if target_col and target_col in current_numeric:
        current_numeric.remove(target_col)

    try:
        df = _apply_scaling(df, scaling_strategy, current_numeric)
        fe_choices["scaling"] = scaling_strategy
    except Exception as exc:
        logger.error("Scaling step failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 7: Preliminary feature importance
    # ------------------------------------------------------------------
    importance: dict[str, float] = {}
    features_selected: list[str] = []
    if target_col and target_col in df.columns:
        try:
            importance = _run_preliminary_importance(df, target_col)
            features_selected = list(importance.keys())[:50]
            logger.info("Preliminary feature importance computed for %d features", len(importance))
        except Exception as exc:
            logger.warning("Feature importance failed: %s", exc)

    if not features_selected:
        features_selected = [c for c in df.columns if c != target_col]

    # ------------------------------------------------------------------
    # Persist engineered DataFrame to DuckDB
    # ------------------------------------------------------------------
    joined_ref = state.get("joined_data_ref", "")
    if joined_ref:
        try:
            from agents.tools.data_tools import load_to_duckdb
            load_to_duckdb(df, joined_ref)
            logger.info("Persisted engineered DataFrame to DuckDB (%d rows, %d cols)", len(df), len(df.columns))
        except Exception as exc:
            logger.warning("Failed to persist to DuckDB: %s", exc)

    # ------------------------------------------------------------------
    # Update state
    # ------------------------------------------------------------------
    state["features_created"] = all_features_created
    state["features_selected"] = features_selected
    state["feature_importance_preliminary"] = importance
    state["fe_choices"] = fe_choices
    state["row_count"] = len(df)
    state["column_count"] = len(df.columns)
    state["completed_steps"] = state.get("completed_steps", []) + ["feature_engineering"]

    logger.info(
        "Feature engineering completed: %d features created, %d selected, shape %s -> %s",
        len(all_features_created), len(features_selected),
        initial_shape, df.shape,
    )
    return state
