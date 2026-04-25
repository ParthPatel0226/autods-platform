"""Modeling Agent.

Trains, evaluates, and selects the best ML model with domain-aware algorithm
recommendations and interactive configuration questions.

LangGraph nodes: generate_model_questions and execute_modeling.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
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
# Domain configuration maps
# ---------------------------------------------------------------------------

_DOMAIN_ALGORITHMS: dict[str, list[str]] = {
    "healthcare": ["logistic_regression", "random_forest", "xgboost"],
    "finance": ["logistic_regression", "lightgbm", "xgboost"],
    "hr": ["random_forest", "gradient_boosting", "logistic_regression"],
    "manufacturing": ["random_forest", "gradient_boosting"],
    "ecommerce": ["lightgbm", "xgboost", "random_forest"],
    "marketing": ["lightgbm", "xgboost", "random_forest"],
    "generic": ["random_forest", "gradient_boosting", "logistic_regression"],
}

_DOMAIN_METRICS: dict[str, dict[str, str]] = {
    "healthcare": {"classification": "recall", "regression": "rmse"},
    "finance": {"classification": "roc_auc", "regression": "rmse"},
    "hr": {"classification": "recall", "regression": "rmse"},
    "manufacturing": {"classification": "f1", "regression": "rmse"},
    "ecommerce": {"classification": "f1", "regression": "rmse"},
    "marketing": {"classification": "roc_auc", "regression": "rmse"},
    "generic": {"classification": "f1", "regression": "rmse"},
}

_REGRESSION_ALGORITHMS: list[str] = [
    "linear_regression", "ridge", "random_forest", "gradient_boosting", "xgboost",
]


# ---------------------------------------------------------------------------
# Shared DataFrame loader
# ---------------------------------------------------------------------------

def _get_working_df(state: AutoDSState) -> pd.DataFrame:
    """Retrieve the working DataFrame from DuckDB or the first data source.

    Args:
        state: Current pipeline state.

    Returns:
        A pandas DataFrame with the working dataset, or empty DataFrame.
    """
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
# Question builders
# ---------------------------------------------------------------------------

def _build_priority_question(state: AutoDSState) -> dict:
    """Build the modeling priority question: accuracy vs interpretability vs speed.

    Args:
        state: Current pipeline state.

    Returns:
        Question dict with single_select type.
    """
    domain = state.get("detected_domain", "generic")
    recommended = "interpretability" if domain in ("healthcare", "finance") else "accuracy"

    return {
        "id": "model_q1_priority",
        "step": "modeling",
        "question": "What is your primary modeling priority?",
        "type": "single_select",
        "options": [
            {
                "value": "accuracy",
                "label": "Maximize predictive accuracy",
                "recommended": recommended == "accuracy",
            },
            {
                "value": "interpretability",
                "label": "Interpretable / explainable model (e.g. for clinical or regulatory use)",
                "recommended": recommended == "interpretability",
            },
            {
                "value": "speed",
                "label": "Fast training and inference (real-time scoring)",
                "recommended": False,
            },
        ],
        "user_response": None,
    }


def _build_algorithm_question(state: AutoDSState) -> dict:
    """Build the algorithm multi-select question with domain-aware recommendations.

    Args:
        state: Current pipeline state.

    Returns:
        Question dict with multi_select type.
    """
    domain = state.get("detected_domain", "generic")
    problem_type = state.get("problem_type", "classification")

    if problem_type == "regression":
        available = _REGRESSION_ALGORITHMS
        recommended_set = {"random_forest", "gradient_boosting", "xgboost"}
    else:
        recommended_set = set(_DOMAIN_ALGORITHMS.get(domain, _DOMAIN_ALGORITHMS["generic"]))
        available = [
            "logistic_regression", "random_forest", "gradient_boosting",
            "xgboost", "lightgbm", "decision_tree", "svm",
        ]

    options = [
        {
            "value": algo,
            "label": algo.replace("_", " ").title(),
            "recommended": algo in recommended_set,
        }
        for algo in available
    ]

    return {
        "id": "model_q2_algorithms",
        "step": "modeling",
        "question": "Which algorithms should be trained and compared?",
        "type": "multi_select",
        "options": options,
        "user_response": None,
    }


def _build_validation_question(state: AutoDSState) -> dict:
    """Build the validation strategy question.

    Args:
        state: Current pipeline state.

    Returns:
        Question dict with single_select type.
    """
    problem_type = state.get("problem_type", "classification")
    is_time_series = problem_type == "time_series"

    return {
        "id": "model_q3_validation",
        "step": "modeling",
        "question": "Which validation strategy should be used?",
        "type": "single_select",
        "options": [
            {
                "value": "holdout",
                "label": "Holdout split (80/20 train/test)",
                "recommended": not is_time_series,
            },
            {
                "value": "cv",
                "label": "5-fold cross-validation",
                "recommended": False,
            },
            {
                "value": "time_series_split",
                "label": "Time-series split (no data leakage across time)",
                "recommended": is_time_series,
            },
        ],
        "user_response": None,
    }


def _build_metric_question(state: AutoDSState) -> dict:
    """Build the primary evaluation metric question with domain-aware defaults.

    Args:
        state: Current pipeline state.

    Returns:
        Question dict with single_select type.
    """
    domain = state.get("detected_domain", "generic")
    problem_type = state.get("problem_type", "classification")

    metric_key = problem_type if problem_type in ("classification", "regression") else "classification"
    default_metric = _DOMAIN_METRICS.get(domain, _DOMAIN_METRICS["generic"]).get(metric_key, "f1")

    if problem_type == "regression":
        options = [
            {"value": "rmse", "label": "RMSE (Root Mean Squared Error)", "recommended": default_metric == "rmse"},
            {"value": "mae", "label": "MAE (Mean Absolute Error)", "recommended": default_metric == "mae"},
            {"value": "r2", "label": "R\u00b2 Score", "recommended": False},
        ]
    else:
        options = [
            {"value": "f1", "label": "F1 Score (harmonic mean of precision/recall)", "recommended": default_metric == "f1"},
            {"value": "roc_auc", "label": "ROC-AUC", "recommended": default_metric == "roc_auc"},
            {"value": "recall", "label": "Recall / Sensitivity (minimise false negatives)", "recommended": default_metric == "recall"},
            {"value": "precision", "label": "Precision (minimise false positives)", "recommended": False},
            {"value": "accuracy", "label": "Accuracy", "recommended": False},
        ]

    return {
        "id": "model_q4_metric",
        "step": "modeling",
        "question": "Which metric should be used to select the best model?",
        "type": "single_select",
        "options": options,
        "user_response": None,
    }


# ---------------------------------------------------------------------------
# Question generation node
# ---------------------------------------------------------------------------

def generate_model_questions(state: AutoDSState) -> AutoDSState:
    """Generate modeling configuration questions based on domain and problem type.

    Builds four universal questions (priority, algorithms, validation, metric) and
    appends any domain-specific model questions from the domain config. In AUTO mode
    all choices are auto-selected and stored in model_choices; in Guided/Expert
    mode filtered questions are stored in model_questions_asked for the dashboard.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with model questions or auto-selected choices.
    """
    state["current_step"] = "model_questions"
    logger.info("Generating modeling questions")

    questions: list[dict] = [
        _build_priority_question(state),
        _build_algorithm_question(state),
        _build_validation_question(state),
        _build_metric_question(state),
    ]

    domain_config = state.get("domain_config", {})
    for dq in domain_config.get("model_questions", []):
        dq_copy = dict(dq)
        dq_copy.setdefault("step", "modeling")
        dq_copy.setdefault("user_response", None)
        dq_copy["domain_specific"] = True
        questions.append(dq_copy)

    user_mode = state.get("user_mode", "guided")
    filtered = filter_questions_for_mode(questions, user_mode)

    if user_mode == "auto":
        choices = _auto_select_model_choices(questions, state)
        state["model_choices"] = choices
        state["model_questions_asked"] = questions
        logger.info(
            "AUTO mode: algorithms=%s metric=%s",
            choices.get("algorithms"),
            choices.get("metric"),
        )
    else:
        state["model_questions_asked"] = filtered
        logger.info("Generated %d model questions for mode '%s'", len(filtered), user_mode)

    return state


def _auto_select_model_choices(questions: list[dict], state: AutoDSState) -> dict[str, Any]:
    """Extract recommended defaults from questions for AUTO mode.

    Args:
        questions: All generated model questions.
        state: Current pipeline state.

    Returns:
        Dict with keys: priority, algorithms, validation, metric.
    """
    choices: dict[str, Any] = {}

    for q in questions:
        qid = q.get("id", "")

        if qid == "model_q1_priority":
            choices["priority"] = auto_select_best_option(q, state) or "accuracy"

        elif qid == "model_q2_algorithms":
            choices["algorithms"] = [
                opt["value"] for opt in q.get("options", []) if opt.get("recommended")
            ] or ["random_forest"]

        elif qid == "model_q3_validation":
            choices["validation"] = auto_select_best_option(q, state) or "holdout"

        elif qid == "model_q4_metric":
            choices["metric"] = auto_select_best_option(q, state) or "f1"

    return choices


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _resolve_algorithms(state: AutoDSState) -> list[str]:
    """Determine which algorithms to train from choices or domain defaults.

    Args:
        state: Current pipeline state.

    Returns:
        List of algorithm name strings.
    """
    choices = state.get("model_choices", {})
    algos = choices.get("algorithms")
    if algos:
        return algos

    domain = state.get("detected_domain", "generic")
    problem_type = state.get("problem_type", "classification")
    if problem_type == "regression":
        return ["random_forest", "gradient_boosting"]
    return _DOMAIN_ALGORITHMS.get(domain, _DOMAIN_ALGORITHMS["generic"])


def _resolve_metric(state: AutoDSState) -> str:
    """Determine primary selection metric from choices or domain defaults.

    Args:
        state: Current pipeline state.

    Returns:
        Metric name string.
    """
    choices = state.get("model_choices", {})
    metric = choices.get("metric")
    if metric:
        return metric

    domain = state.get("detected_domain", "generic")
    problem_type = state.get("problem_type", "classification")
    key = problem_type if problem_type in ("classification", "regression") else "classification"
    return _DOMAIN_METRICS.get(domain, _DOMAIN_METRICS["generic"]).get(key, "f1")


def _ensure_output_dir() -> Path:
    """Create and return the models output directory."""
    output_dir = Path("outputs/models")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _log_to_mlflow(
    algorithm: str,
    metrics: dict[str, Any],
    model: Any,
    run_id_map: dict[str, str],
) -> None:
    """Log a single training run to MLflow. No-op on any failure.

    Args:
        algorithm: Algorithm name.
        metrics: Evaluation metrics dict.
        model: Trained sklearn-compatible model object.
        run_id_map: Mutable dict to store the resulting run_id.
    """
    try:
        import mlflow
        import mlflow.sklearn

        with mlflow.start_run(run_name=algorithm) as run:
            mlflow.log_params({"algorithm": algorithm})
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, v)
            mlflow.sklearn.log_model(model, artifact_path="model")
            run_id_map[algorithm] = run.info.run_id
    except Exception as exc:
        logger.debug("MLflow logging skipped for '%s': %s", algorithm, exc)


# ---------------------------------------------------------------------------
# Modeling execution node
# ---------------------------------------------------------------------------

def execute_modeling(state: AutoDSState) -> AutoDSState:
    """Train, evaluate, and select the best model.

    Steps:
      1. Load working DataFrame from DuckDB or file fallback.
      2. Extract feature matrix X and target y using feature_list.
      3. Perform stratified train/test split.
      4. Train each resolved algorithm with hold-out evaluation and CV.
      5. Compare models and select the best by the chosen metric.
      6. Compute feature importance for the best model.
      7. Save the best model artifact to outputs/models/.
      8. Log each run to MLflow (best-effort, non-blocking).
      9. Update state with all results.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with model_results, best_model, best_model_path,
        and feature_importance.
    """
    state["current_step"] = "model_execute"
    logger.info("Starting modeling execution")

    # ------------------------------------------------------------------
    # Step 1: Load data
    # ------------------------------------------------------------------
    df = _get_working_df(state)
    if df.empty:
        state["errors"] = state.get("errors", []) + [{
            "step": "modeling",
            "type": "no_data",
            "detail": "No working DataFrame available for modeling",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]
        return state

    target_col = state.get("target_column")
    if not target_col or target_col not in df.columns:
        state["errors"] = state.get("errors", []) + [{
            "step": "modeling",
            "type": "missing_target",
            "detail": f"Target column '{target_col}' not found in DataFrame",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]
        return state

    # ------------------------------------------------------------------
    # Step 2: Build feature matrix
    # ------------------------------------------------------------------
    feature_list: list[str] = (
        state.get("feature_list")
        or state.get("features_selected")
        or []
    )
    if not feature_list:
        feature_list = [c for c in df.columns if c != target_col]

    available_features = [
        c for c in feature_list
        if c in df.columns and c != target_col and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not available_features:
        state["errors"] = state.get("errors", []) + [{
            "step": "modeling",
            "type": "no_features",
            "detail": "No numeric features available after filtering",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]
        return state

    X = df[available_features].fillna(0)
    y = df[target_col]

    # ------------------------------------------------------------------
    # Step 3: Train/test split
    # ------------------------------------------------------------------
    problem_type = state.get("problem_type", "classification")
    seed = state.get("random_seed", 42)

    try:
        from agents.tools.ml_tools import train_test_split_stratified
        split_result = train_test_split_stratified(
            pd.concat([X, y], axis=1),
            target_col=target_col,
            test_size=0.2,
            seed=seed,
        )
        X_train, X_test, y_train, y_test = split_result
    except Exception as exc:
        logger.error("Train/test split failed: %s", exc)
        state["errors"] = state.get("errors", []) + [{
            "step": "modeling",
            "type": "split_error",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]
        return state

    # ------------------------------------------------------------------
    # Step 4: Train each algorithm
    # ------------------------------------------------------------------
    from agents.tools.ml_tools import (
        compare_models,
        cross_validate_model,
        evaluate_model,
        get_feature_importance,
        save_model,
        select_best_model,
        train_model,
    )

    algorithms = _resolve_algorithms(state)
    selection_metric = _resolve_metric(state)
    model_results: dict[str, Any] = {}
    trained_models_map: dict[str, Any] = {}
    run_id_map: dict[str, str] = {}
    all_results: list[dict] = []

    for algorithm in algorithms:
        try:
            logger.info("Training algorithm: %s", algorithm)
            model = train_model(algorithm, X_train, y_train, problem_type, seed=seed)
            eval_metrics = evaluate_model(model, X_test, y_test, problem_type)
            cv_metrics = cross_validate_model(
                algorithm, X_train, y_train, problem_type, cv=5, seed=seed,
            )

            merged: dict[str, Any] = {
                **eval_metrics,
                "cv_metrics": cv_metrics,
                "algorithm": algorithm,
            }
            model_results[algorithm] = merged
            trained_models_map[algorithm] = model
            all_results.append(merged)

            _log_to_mlflow(algorithm, eval_metrics, model, run_id_map)
            logger.info(
                "Algorithm '%s' trained. '%s'=%.4f",
                algorithm,
                selection_metric,
                eval_metrics.get(selection_metric, 0),
            )

        except Exception as exc:
            logger.error("Training '%s' failed: %s", algorithm, exc)
            state["errors"] = state.get("errors", []) + [{
                "step": "modeling",
                "type": "training_error",
                "detail": f"{algorithm}: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]

    if not model_results:
        state["errors"] = state.get("errors", []) + [{
            "step": "modeling",
            "type": "no_models_trained",
            "detail": "All algorithm training attempts failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]
        return state

    # ------------------------------------------------------------------
    # Step 5: Compare and select best model
    # ------------------------------------------------------------------
    try:
        compare_models(all_results)
        best_result = select_best_model(all_results, metric=selection_metric)
        inner = best_result.get("best_result", {})
        best_name: str = inner.get("algorithm", algorithms[0])
    except Exception as exc:
        logger.warning("Model comparison failed, using first trained model: %s", exc)
        best_name = next(iter(model_results))

    best_model_obj = trained_models_map.get(best_name)
    logger.info("Best model selected: '%s'", best_name)

    # ------------------------------------------------------------------
    # Step 6: Feature importance for best model
    # ------------------------------------------------------------------
    importance: dict[str, float] = {}
    if best_model_obj is not None:
        try:
            importance = get_feature_importance(best_model_obj, available_features)
        except Exception as exc:
            logger.warning("Feature importance failed for '%s': %s", best_name, exc)

    # ------------------------------------------------------------------
    # Step 7: Save best model artifact
    # ------------------------------------------------------------------
    best_model_path = ""
    if best_model_obj is not None:
        try:
            output_dir = _ensure_output_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            artifact_path = output_dir / f"{best_name}_{timestamp}.pkl"
            metadata = {
                "algorithm": best_name,
                "problem_type": problem_type,
                "features": available_features,
                "target_column": target_col,
                "metrics": model_results.get(best_name, {}),
                "selection_metric": selection_metric,
                "trained_at": timestamp,
            }
            save_model(best_model_obj, str(artifact_path), metadata=metadata)
            best_model_path = str(artifact_path)
            logger.info("Best model saved to '%s'", best_model_path)
        except Exception as exc:
            logger.error("Model save failed: %s", exc)
            state["errors"] = state.get("errors", []) + [{
                "step": "modeling",
                "type": "save_error",
                "detail": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]

    # ------------------------------------------------------------------
    # Step 8: Update state
    # ------------------------------------------------------------------
    state["model_results"] = model_results
    state["trained_models"] = {
        algo: {
            "metrics": res,
            "mlflow_run_id": run_id_map.get(algo),
        }
        for algo, res in model_results.items()
    }
    state["best_model"] = best_name
    state["best_model_name"] = best_name
    state["best_model_path"] = best_model_path
    state["best_model_metrics"] = model_results.get(best_name, {})
    state["feature_importance"] = importance
    state["feature_list"] = available_features
    state["completed_steps"] = state.get("completed_steps", []) + ["modeling"]

    logger.info(
        "Modeling completed: %d models trained, best='%s', '%s'=%.4f, artifact='%s'",
        len(model_results),
        best_name,
        selection_metric,
        model_results.get(best_name, {}).get(selection_metric, 0),
        best_model_path,
    )
    return state
