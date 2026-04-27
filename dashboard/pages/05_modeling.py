"""Page 05 -- Modeling.

Algorithm selection, training progress, evaluation metrics, model comparison,
and best-model selection.

Premium dark luxury UI with glass morphism cards and gradient accents.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components.shared_css import inject_shared_css
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
# Design tokens
# ---------------------------------------------------------------------------

_PAGE_CSS = """
<style>
/* --- Page header --- */
.model-page-header {
    padding: 32px 0 24px 0;
}
.model-page-header h1 {
    font-size: 2.25rem;
    font-weight: 700;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.02em;
}
.model-page-header .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 4px;
}

/* --- Algorithm cards grid --- */
.algo-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}
@media (max-width: 768px) {
    .algo-grid { grid-template-columns: repeat(2, 1fr); }
}

.algo-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
    position: relative;
}
.algo-card:hover {
    border-color: var(--border-active);
    box-shadow: var(--shadow-glow);
}
.algo-card.recommended {
    border-color: var(--accent-primary);
    box-shadow: var(--shadow-glow), var(--shadow-card);
}
.algo-card .algo-name {
    color: var(--text-primary);
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 4px;
}
.algo-card .algo-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--accent-primary-light);
    color: var(--accent-primary);
}

/* --- Training progress container --- */
.training-progress-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    margin-bottom: 24px;
}

.progress-step {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--border-subtle);
}
.progress-step:last-child { border-bottom: none; }

.progress-step .step-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 12px;
    flex-shrink: 0;
}
.step-dot.complete { background-color: var(--accent-success); }
.step-dot.training {
    background-color: var(--accent-secondary);
    animation: pulse-dot 1.5s ease-in-out infinite;
}
.step-dot.queued { background-color: var(--text-muted); }
.step-dot.error { background-color: var(--accent-danger); }

@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.progress-step .step-name {
    color: var(--text-primary);
    font-size: 0.85rem;
    font-weight: 500;
    flex: 1;
}
.progress-step .step-status {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.step-status.complete { color: var(--accent-success); }
.step-status.training { color: var(--accent-secondary); }
.step-status.queued { color: var(--text-muted); }
.step-status.error { color: var(--accent-danger); }

/* --- Animated progress bar --- */
.progress-bar-wrapper {
    background: var(--bg-elevated);
    border-radius: 6px;
    height: 6px;
    overflow: hidden;
    margin-top: 16px;
}
.progress-bar-fill {
    height: 100%;
    border-radius: 6px;
    background: var(--gradient-primary);
    transition: width var(--duration-normal) var(--ease-in-out);
}

/* --- Results table --- */
.results-table-wrapper {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-card);
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}

/* --- Metric cards 4-col --- */
.metric-cards-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}
@media (max-width: 768px) {
    .metric-cards-row { grid-template-columns: repeat(2, 1fr); }
}
.metric-glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    text-align: center;
    transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.metric-glass-card:hover {
    border-color: var(--border-active);
    box-shadow: var(--shadow-glow);
}
.metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
}
.metric-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

/* --- Model comparison chart --- */
.comparison-chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    margin-bottom: 24px;
}
.comparison-chart-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
}

/* --- Best model banner --- */
.best-model-banner {
    background: var(--bg-card);
    border: 1px solid rgba(34,197,94,0.25);
    border-left: 3px solid var(--accent-success);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}
.best-model-banner .banner-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent-success);
    margin-bottom: 4px;
}
.best-model-banner .banner-name {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
}

/* --- Divider --- */
.model-divider {
    border: none;
    border-top: 1px solid var(--border-subtle);
    margin: 32px 0;
}

/* --- Status dot --- */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-dot.info { background-color: var(--accent-secondary); }

/* --- Info placeholder --- */
.info-placeholder {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
}

/* --- Streamlit input overrides --- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div {
    background-color: var(--bg-elevated) !important;
    border-color: var(--border-subtle) !important;
    color: var(--text-primary) !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        inject_shared_css()
        st.info(
            "Complete data preparation first. This page handles algorithm "
            "selection, model training with cross-validation, and statistical "
            "model comparison."
        )
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
    """Render algorithm checkboxes as glass cards in a grid."""
    problem = st.session_state.get("problem_type", PROBLEM_CLASSIFICATION)
    mode = st.session_state.get("user_mode", MODE_GUIDED)
    algos = _ALGORITHMS.get(problem, _ALGORITHMS[PROBLEM_CLASSIFICATION])

    st.markdown('<div class="section-header">Algorithm Selection</div>', unsafe_allow_html=True)

    if mode == MODE_AUTO:
        st.markdown(
            '<div class="info-placeholder">'
            '<span class="status-dot info"></span>'
            'Auto mode -- system selects optimal algorithms.'
            '</div>',
            unsafe_allow_html=True,
        )
        return [k for k, v in algos.items() if v.get("recommended")]

    if mode == MODE_GUIDED:
        st.markdown(
            '<p style="color: var(--text-muted); font-size: 0.8rem;">'
            'Recommended algorithms are pre-selected. Adjust as needed.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color: var(--text-muted); font-size: 0.8rem;">'
            'Expert mode -- select any combination.</p>',
            unsafe_allow_html=True,
        )

    # Render visual algo cards (informational)
    cards_html = '<div class="algo-grid">'
    for key, meta in algos.items():
        rec = meta.get("recommended", False)
        rec_class = " recommended" if rec else ""
        tag_html = '<span class="algo-tag">Recommended</span>' if rec else ""
        cards_html += f"""
            <div class="algo-card{rec_class}">
                <div class="algo-name">{meta["label"]}</div>
                {tag_html}
            </div>
        """
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # Actual checkboxes for selection
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

    st.markdown('<div class="section-header">Validation and Tuning</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="section-header">Training Progress</div>', unsafe_allow_html=True)

    total = len(training_progress)
    completed = sum(1 for s in training_progress.values() if s == "complete")
    pct = int((completed / total) * 100) if total > 0 else 0

    steps_html = '<div class="training-progress-container">'
    for model_name, status in training_progress.items():
        dot_class = status if status in ("complete", "training", "queued") else "error"
        status_label = status.upper() if status != "error" else status.upper()
        steps_html += f"""
            <div class="progress-step">
                <div class="step-dot {dot_class}"></div>
                <div class="step-name">{model_name}</div>
                <div class="step-status {dot_class}">{status_label}</div>
            </div>
        """

    # Progress bar
    steps_html += f"""
        <div class="progress-bar-wrapper">
            <div class="progress-bar-fill" style="width: {pct}%;"></div>
        </div>
        <div style="text-align: right; margin-top: 8px; font-size: 0.75rem; color: var(--text-muted);">
            {completed} / {total} models complete
        </div>
    """
    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)


def _render_results() -> None:
    """Display model results: metrics table, comparison chart, best model."""
    model_results: dict[str, dict] = st.session_state.get("model_results", {})
    if not model_results:
        return

    st.markdown('<div class="section-header">Model Results</div>', unsafe_allow_html=True)

    # Results table
    rows: list[dict[str, Any]] = []
    for name, result in model_results.items():
        row: dict[str, Any] = {"Model": name}
        row.update(result.get("metrics", {}))
        rows.append(row)

    if rows:
        results_df = pd.DataFrame(rows).set_index("Model")
        best_name = st.session_state.get("best_model_name", "")

        # Highlight best model row
        def _highlight_best(row: pd.Series) -> list[str]:
            if row.name == best_name:
                return ["background-color: var(--accent-primary-subtle); font-weight: 600"] * len(row)
            return [""] * len(row)

        styled = results_df.style.apply(_highlight_best, axis=1).highlight_max(axis=0)
        st.dataframe(styled, use_container_width=True)

    _render_comparison_chart(model_results)

    # Best model banner
    best_name = st.session_state.get("best_model_name", "")
    best_metrics = st.session_state.get("best_model_metrics", {})
    if best_name:
        st.markdown(
            f"""
            <div class="best-model-banner">
                <div class="banner-label">Best Model</div>
                <div class="banner-name">{best_name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Metric cards (4-column)
        if best_metrics:
            metric_items = list(best_metrics.items())[:8]
            cards_html = '<div class="metric-cards-row">'
            for metric_name, metric_val in metric_items:
                display_val = f"{metric_val:.4f}" if isinstance(metric_val, float) else str(metric_val)
                display_label = metric_name.replace("_", " ").title()
                cards_html += f"""
                    <div class="metric-glass-card">
                        <div class="metric-value">{display_val}</div>
                        <div class="metric-label">{display_label}</div>
                    </div>
                """
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)

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
            data=[go.Bar(
                x=model_names,
                y=values,
                marker_color="#2563eb",
                marker_line_color="rgba(37,99,235,0.5)",
                marker_line_width=1,
            )],
        )
        fig.update_layout(
            yaxis_title=primary.replace("_", " ").title(),
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#475569"),
            xaxis=dict(gridcolor="rgba(15,23,42,0.06)"),
            yaxis=dict(gridcolor="rgba(15,23,42,0.06)"),
        )

        st.markdown('<div class="section-header">Model Comparison</div>', unsafe_allow_html=True)
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
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#475569"),
            xaxis=dict(gridcolor="rgba(15,23,42,0.06)"),
            yaxis_gridcolor="rgba(15,23,42,0.06)",
        )
        fig.update_traces(marker_color="#2563eb")

        st.markdown('<div class="section-header">Feature Importance (Top 20)</div>', unsafe_allow_html=True)
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
            colors = ["#2563eb", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#7c3aed", "#ec4899", "#14b8a6"]
            for idx, (name, result) in enumerate(model_results.items()):
                cv = result.get("cv_scores", [])
                if cv:
                    fig.add_trace(go.Box(
                        y=cv,
                        name=name,
                        marker_color=colors[idx % len(colors)],
                    ))
            fig.update_layout(
                yaxis_title="Score",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#475569"),
                yaxis=dict(gridcolor="rgba(15,23,42,0.06)"),
            )
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
                z=cm, x=labels, y=labels, colorscale=[[0, "#f1f5f9"], [1, "#2563eb"]],
            )
            fig.update_layout(
                xaxis_title="Predicted",
                yaxis_title="Actual",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#475569"),
            )
            render_chart(fig, title="Confusion Matrix", key="conf_matrix")
        except ImportError:
            st.table(cm)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    inject_shared_css()
    _guard()

    # Inject page-specific CSS
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

    # Page header
    st.markdown(
        """
        <div class="model-page-header">
            <h1>Model Training and Evaluation</h1>
            <div class="subtitle">Algorithm selection, hyperparameter tuning, and performance analysis</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_progress()

    selected_algos = _render_algorithm_selection()
    st.markdown('<hr class="model-divider">', unsafe_allow_html=True)
    val_config = _render_validation_config()
    adv_opts = _render_advanced_options()
    st.markdown('<hr class="model-divider">', unsafe_allow_html=True)

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
            st.markdown(
                """
                <div class="info-placeholder">
                    <span class="status-dot info"></span>
                    Training configuration saved. Connect the Modeling Agent
                    to execute training. Results will appear below.
                </div>
                """,
                unsafe_allow_html=True,
            )

    _render_training_status()
    st.markdown('<hr class="model-divider">', unsafe_allow_html=True)
    _render_results()
    _render_confusion_matrix()

    # Navigation
    st.markdown('<hr class="model-divider">', unsafe_allow_html=True)
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



def _is_streamlit_running() -> bool:
    """Return True only when executing inside a Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _is_streamlit_running():
    _page()
