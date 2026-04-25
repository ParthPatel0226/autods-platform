"""Page 05 -- Modeling.

Algorithm selection, training progress, evaluation metrics, model comparison,
and best-model selection.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import (
    MODE_AUTO,
    MODE_EXPERT,
    MODE_GUIDED,
    PROBLEM_CLASSIFICATION,
    PROBLEM_CLUSTERING,
    PROBLEM_REGRESSION,
    PROBLEM_TIME_SERIES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Algorithm catalogue
# ---------------------------------------------------------------------------

_ALGORITHMS: dict[str, dict[str, dict[str, Any]]] = {
    PROBLEM_CLASSIFICATION: {
        "logistic_regression": {"label": "Logistic Regression", "recommended": True},
        "random_forest": {"label": "Random Forest", "recommended": True},
        "xgboost": {"label": "XGBoost", "recommended": True},
        "lightgbm": {"label": "LightGBM", "recommended": False},
        "catboost": {"label": "CatBoost", "recommended": False},
        "svm": {"label": "SVM", "recommended": False},
        "knn": {"label": "K-Nearest Neighbors", "recommended": False},
        "naive_bayes": {"label": "Naive Bayes", "recommended": False},
    },
    PROBLEM_REGRESSION: {
        "linear_regression": {"label": "Linear Regression", "recommended": True},
        "ridge": {"label": "Ridge Regression", "recommended": False},
        "lasso": {"label": "Lasso Regression", "recommended": False},
        "random_forest": {"label": "Random Forest", "recommended": True},
        "xgboost": {"label": "XGBoost", "recommended": True},
        "lightgbm": {"label": "LightGBM", "recommended": False},
        "catboost": {"label": "CatBoost", "recommended": False},
        "svr": {"label": "SVR", "recommended": False},
    },
    PROBLEM_CLUSTERING: {
        "kmeans": {"label": "K-Means", "recommended": True},
        "dbscan": {"label": "DBSCAN", "recommended": True},
        "hierarchical": {"label": "Hierarchical Clustering", "recommended": False},
        "gaussian_mixture": {"label": "Gaussian Mixture", "recommended": False},
    },
    PROBLEM_TIME_SERIES: {
        "arima": {"label": "ARIMA", "recommended": True},
        "prophet": {"label": "Prophet", "recommended": True},
        "xgboost": {"label": "XGBoost (lag features)", "recommended": True},
        "lightgbm": {"label": "LightGBM (lag features)", "recommended": False},
    },
}

_VALIDATION_STRATEGIES: dict[str, str] = {
    "kfold": "K-Fold Cross-Validation (5 folds)",
    "stratified_kfold": "Stratified K-Fold (5 folds)",
    "holdout": "Holdout (80/20 split)",
    "time_split": "Time-based Split",
    "walk_forward": "Walk-Forward Validation",
}

_TUNING_STRATEGIES: dict[str, str] = {
    "default": "Default hyperparameters only",
    "quick": "Quick search (~5 min)",
    "thorough": "Thorough search (~20 min)",
    "expert": "Expert grid (user-defined ranges)",
}


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_progress() -> None:
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "modeling"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_algorithm_selection() -> list[str]:
    """Render algorithm checkboxes based on problem type."""
    problem = st.session_state.get("problem_type", PROBLEM_CLASSIFICATION)
    mode = st.session_state.get("user_mode", MODE_GUIDED)
    algos = _ALGORITHMS.get(problem, _ALGORITHMS[PROBLEM_CLASSIFICATION])

    st.subheader("Algorithm Selection")
    if mode == MODE_AUTO:
        st.caption("Auto mode -- system selects optimal algorithms.")
        return [k for k, v in algos.items() if v.get("recommended")]

    if mode == MODE_GUIDED:
        st.caption("Recommended algorithms are pre-selected. Adjust as needed.")
    else:
        st.caption("Expert mode -- select any combination.")

    selected: list[str] = []
    cols_per_row = 4
    items = list(algos.items())
    for row_start in range(0, len(items), cols_per_row):
        row = items[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, (key, meta) in zip(cols, row):
            default = meta.get("recommended", False)
            if col.checkbox(meta["label"], value=default, key=f"algo_{key}"):
                selected.append(key)
    return selected


def _render_validation_config() -> dict[str, str]:
    """Render validation strategy and tuning options."""
    mode = st.session_state.get("user_mode", MODE_GUIDED)
    problem = st.session_state.get("problem_type", PROBLEM_CLASSIFICATION)

    st.subheader("Validation & Tuning")

    col_val, col_tune = st.columns(2)

    default_val = "stratified_kfold" if problem == PROBLEM_CLASSIFICATION else "kfold"
    if problem == PROBLEM_TIME_SERIES:
        default_val = "time_split"

    val_keys = list(_VALIDATION_STRATEGIES.keys())
    val_labels = list(_VALIDATION_STRATEGIES.values())
    val_idx = val_keys.index(default_val) if default_val in val_keys else 0

    with col_val:
        validation = st.selectbox(
            "Validation Strategy",
            val_labels,
            index=val_idx,
            disabled=mode == MODE_AUTO,
        )
        val_choice = val_keys[val_labels.index(validation)]

    tune_keys = list(_TUNING_STRATEGIES.keys())
    tune_labels = list(_TUNING_STRATEGIES.values())

    with col_tune:
        tuning = st.selectbox(
            "Hyperparameter Tuning",
            tune_labels,
            index=1,
            disabled=mode == MODE_AUTO,
        )
        tune_choice = tune_keys[tune_labels.index(tuning)]

    return {"validation_strategy": val_choice, "tuning_strategy": tune_choice}


def _render_advanced_options() -> dict[str, Any]:
    """Render advanced modeling options in an expander."""
    opts: dict[str, Any] = {}

    with st.expander("Advanced Options", expanded=False):
        problem = st.session_state.get("problem_type", PROBLEM_CLASSIFICATION)

        if problem == PROBLEM_CLASSIFICATION:
            col1, col2 = st.columns(2)
            with col1:
                threshold = st.slider(
                    "Decision Threshold",
                    min_value=0.1,
                    max_value=0.9,
                    value=0.5,
                    step=0.05,
                    key="model_threshold",
                )
                opts["threshold"] = threshold
            with col2:
                use_cost = st.checkbox("Use Cost-Sensitive Learning", key="model_cost_sensitive")
                if use_cost:
                    fn_cost = st.number_input("False Negative Cost", value=1.0, min_value=0.1, key="fn_cost")
                    fp_cost = st.number_input("False Positive Cost", value=1.0, min_value=0.1, key="fp_cost")
                    opts["cost_matrix"] = {"fn": fn_cost, "fp": fp_cost}

        early_stop = st.checkbox("Early stopping (tree-based models)", value=True, key="model_early_stop")
        opts["early_stopping"] = early_stop

    return opts


def _render_training_status() -> None:
    """Show training progress if models are being trained."""
    training_progress: dict[str, str] = st.session_state.get("training_progress", {})
    if not training_progress:
        return

    st.subheader("Training Progress")
    for model_name, status in training_progress.items():
        if status == "complete":
            st.success(f"{model_name}: Complete")
        elif status == "training":
            st.info(f"{model_name}: Training...")
        elif status == "queued":
            st.caption(f"{model_name}: Queued")
        else:
            st.error(f"{model_name}: {status}")


def _render_results() -> None:
    """Display model results: metrics table, comparison chart, best model."""
    model_results: dict[str, dict] = st.session_state.get("model_results", {})
    if not model_results:
        return

    st.subheader("Model Results")

    rows: list[dict[str, Any]] = []
    for name, result in model_results.items():
        row: dict[str, Any] = {"Model": name}
        row.update(result.get("metrics", {}))
        rows.append(row)

    if rows:
        results_df = pd.DataFrame(rows).set_index("Model")
        st.dataframe(results_df.style.highlight_max(axis=0), use_container_width=True)

    _render_comparison_chart(model_results)

    best_name = st.session_state.get("best_model_name", "")
    best_metrics = st.session_state.get("best_model_metrics", {})
    if best_name:
        st.success(f"Best Model: **{best_name}**")
        from dashboard.components.metric_cards import render_metric_cards

        render_metric_cards(best_metrics, columns=4, title="Best Model Metrics")

    _render_feature_importance()
    _render_cv_scores(model_results)


def _render_comparison_chart(model_results: dict[str, dict]) -> None:
    """Bar chart comparing models across primary metric."""
    from dashboard.components.chart_container import render_chart

    try:
        import plotly.graph_objects as go

        metric_names: set[str] = set()
        for result in model_results.values():
            metric_names.update(result.get("metrics", {}).keys())

        if not metric_names:
            return

        primary = next(iter(sorted(metric_names)))
        model_names = list(model_results.keys())
        values = [model_results[m].get("metrics", {}).get(primary, 0) for m in model_names]

        fig = go.Figure(
            data=[go.Bar(x=model_names, y=values, marker_color="steelblue")],
        )
        fig.update_layout(yaxis_title=primary.replace("_", " ").title(), height=350)
        render_chart(fig, title=f"Model Comparison -- {primary}", key="model_comparison")
    except ImportError:
        st.warning("Install plotly for comparison charts.")


def _render_feature_importance() -> None:
    """Show feature importance from best model."""
    importance: dict[str, float] = st.session_state.get("feature_importance", {})
    if not importance:
        return

    from dashboard.components.chart_container import render_chart

    try:
        import plotly.express as px

        sorted_imp = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20])
        fig = px.bar(
            x=list(sorted_imp.values()),
            y=list(sorted_imp.keys()),
            orientation="h",
            labels={"x": "Importance", "y": "Feature"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=400)
        render_chart(fig, title="Feature Importance (Top 20)", key="model_feat_imp")
    except ImportError:
        st.warning("Install plotly for feature importance chart.")


def _render_cv_scores(model_results: dict[str, dict]) -> None:
    """Show cross-validation score distributions."""
    has_cv = any(r.get("cv_scores") for r in model_results.values())
    if not has_cv:
        return

    with st.expander("Cross-Validation Score Distributions"):
        from dashboard.components.chart_container import render_chart

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            for name, result in model_results.items():
                cv = result.get("cv_scores", [])
                if cv:
                    fig.add_trace(go.Box(y=cv, name=name))
            fig.update_layout(yaxis_title="Score", height=350)
            render_chart(fig, title="CV Score Distribution", key="cv_box")
        except ImportError:
            st.warning("Install plotly for CV charts.")


def _render_confusion_matrix() -> None:
    """Show confusion matrix for best model (classification only)."""
    problem = st.session_state.get("problem_type", "")
    if problem != PROBLEM_CLASSIFICATION:
        return

    best = st.session_state.get("best_model_name", "")
    results = st.session_state.get("model_results", {})
    cm = results.get(best, {}).get("confusion_matrix")
    if not cm:
        return

    with st.expander("Confusion Matrix"):
        from dashboard.components.chart_container import render_chart

        try:
            import plotly.figure_factory as ff

            labels = ["Negative", "Positive"]
            fig = ff.create_annotated_heatmap(
                z=cm, x=labels, y=labels, colorscale="Blues",
            )
            fig.update_layout(xaxis_title="Predicted", yaxis_title="Actual", height=350)
            render_chart(fig, title="Confusion Matrix", key="conf_matrix")
        except ImportError:
            st.table(cm)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Model Training & Evaluation")
    _render_progress()

    selected_algos = _render_algorithm_selection()
    st.divider()
    val_config = _render_validation_config()
    adv_opts = _render_advanced_options()
    st.divider()

    already_trained = bool(st.session_state.get("model_results"))

    if not already_trained:
        if st.button(
            "Start Training",
            type="primary",
            use_container_width=True,
            disabled=len(selected_algos) == 0,
        ):
            st.session_state["algorithms_selected"] = selected_algos
            st.session_state["validation_strategy"] = val_config["validation_strategy"]
            st.session_state["tuning_strategy"] = val_config["tuning_strategy"]
            st.session_state.update(adv_opts)
            st.session_state["training_submitted"] = True
            st.info(
                "Training configuration saved. Connect the Modeling Agent "
                "to execute training. Results will appear below."
            )

    _render_training_status()
    st.divider()
    _render_results()
    _render_confusion_matrix()

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Feature Engineering", use_container_width=True):
            st.switch_page("pages/04_feature_engineering.py")
    with col_next:
        if st.button(
            "Proceed to Explainability",
            type="primary",
            use_container_width=True,
            disabled=not already_trained,
        ):
            st.switch_page("pages/06_explainability.py")


_page()
