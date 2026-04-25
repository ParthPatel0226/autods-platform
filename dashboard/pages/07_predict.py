"""Page 07 -- Predictions.

Upload new data for batch predictions or enter a single row manually.
Shows prediction results with confidence scores and explanations.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import PROBLEM_CLASSIFICATION, PROBLEM_REGRESSION

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

section[data-testid="stMain"] { background: #0a0a0f; }
.stApp { background: #0a0a0f; color: #f1f5f9; font-family: 'Inter', sans-serif; }
header[data-testid="stHeader"] { background: transparent; }
.stDeployButton, #MainMenu { display: none; }

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    position: relative;
}
.section-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 48px;
    height: 2px;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    border-radius: 1px;
}

/* Glass card */
.glass-card {
    background: rgba(18, 18, 26, 0.8);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    transition: border-color 0.2s ease;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.25);
}

/* Glass pill tabs */
.pill-tabs {
    display: flex;
    gap: 0.5rem;
    padding: 0.375rem;
    background: rgba(18, 18, 26, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 12px;
    margin-bottom: 1.5rem;
}
.pill-tab {
    padding: 0.5rem 1.25rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #94a3b8;
    transition: all 0.2s ease;
    border: 1px solid transparent;
    background: transparent;
    text-align: center;
    flex: 1;
}
.pill-tab.active {
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(14,165,233,0.15));
    color: #f1f5f9;
    border-color: rgba(99,102,241,0.3);
    box-shadow: 0 0 12px rgba(99,102,241,0.15);
}

/* Drop zone */
.drop-zone {
    background: rgba(18, 18, 26, 0.5);
    backdrop-filter: blur(16px);
    border: 2px dashed rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    transition: all 0.2s ease;
    margin-bottom: 1rem;
}
.drop-zone:hover {
    border-color: rgba(99,102,241,0.4);
    background: rgba(18, 18, 26, 0.7);
}
.drop-zone-icon {
    width: 48px;
    height: 48px;
    margin: 0 auto 1rem;
    border-radius: 12px;
    background: rgba(99,102,241,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
}
.drop-zone-icon svg { width: 24px; height: 24px; }

/* Prediction result card */
.prediction-result {
    background: rgba(18, 18, 26, 0.8);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
}
.prediction-result::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
}
.prediction-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0.5rem 0;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.prediction-label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
}

/* Confidence bar */
.confidence-bar-wrap {
    margin: 1rem auto;
    max-width: 300px;
}
.confidence-bar-bg {
    width: 100%;
    height: 8px;
    background: rgba(99,102,241,0.1);
    border-radius: 4px;
    overflow: hidden;
}
.confidence-bar-fill {
    height: 100%;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    border-radius: 4px;
    transition: width 0.4s ease;
}
.confidence-text {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.4rem;
    text-align: center;
}

/* Glass table */
.glass-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
}
.glass-table thead th {
    background: rgba(99,102,241,0.08);
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid rgba(99,102,241,0.12);
    text-align: left;
}
.glass-table thead th:first-child { border-radius: 8px 0 0 0; }
.glass-table thead th:last-child { border-radius: 0 8px 0 0; }
.glass-table tbody td {
    padding: 0.625rem 1rem;
    color: #f1f5f9;
    border-bottom: 1px solid rgba(99,102,241,0.06);
}
.glass-table tbody tr:hover td {
    background: rgba(99,102,241,0.04);
}

/* Form inputs */
.stNumberInput > div, .stSelectbox > div, .stTextInput > div {
    background: rgba(18, 18, 26, 0.6);
    border-radius: 8px;
}
.stNumberInput input, .stSelectbox select, .stTextInput input {
    color: #f1f5f9 !important;
    background: rgba(22, 22, 31, 0.8) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 8px !important;
}

/* Model info bar */
.model-info-bar {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    background: rgba(18, 18, 26, 0.6);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
}
.model-info-label {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.model-info-value {
    font-size: 0.9rem;
    color: #f1f5f9;
    font-weight: 600;
}

/* Gradient download button */
.gradient-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.625rem 1.5rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 500;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    color: #ffffff;
    border: none;
    cursor: pointer;
    transition: box-shadow 0.2s ease;
}
.gradient-btn:hover { box-shadow: 0 0 20px rgba(99,102,241,0.3); }

/* Key factors list */
.factor-item {
    padding: 0.5rem 0.75rem;
    border-left: 2px solid rgba(99,102,241,0.3);
    color: #94a3b8;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}

/* Page title */
.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.9rem;
    color: #64748b;
    margin-bottom: 1.5rem;
}

.glass-caption {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.25rem;
}

/* Streamlit tabs override */
.stTabs [data-baseweb="tab-list"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding: 0; }

/* Alert overrides */
div[data-testid="stAlert"] {
    background: rgba(18, 18, 26, 0.6) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}

/* File uploader */
div[data-testid="stFileUploader"] {
    background: transparent;
}
div[data-testid="stFileUploader"] section {
    background: rgba(18, 18, 26, 0.5);
    border: 2px dashed rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 1.5rem;
}
div[data-testid="stFileUploader"] section:hover {
    border-color: rgba(99,102,241,0.4);
}
</style>
"""


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()
    if not st.session_state.get("best_model_name"):
        st.warning("Train and select a model before making predictions.")
        st.stop()


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_progress() -> None:
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "predict"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_model_info() -> None:
    """Show currently selected model info."""
    best = st.session_state.get("best_model_name", "")
    metrics = st.session_state.get("best_model_metrics", {})

    if best:
        metrics_html = ""
        if metrics:
            for k, v in list(metrics.items())[:4]:
                val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                metrics_html += (
                    f'<div>'
                    f'<div class="model-info-label">{k}</div>'
                    f'<div class="model-info-value">{val_str}</div>'
                    f'</div>'
                )

        st.markdown(
            f'<div class="model-info-bar">'
            f'<div>'
            f'<div class="model-info-label">Active Model</div>'
            f'<div class="model-info-value">{best}</div>'
            f'</div>'
            f'{metrics_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_batch_upload() -> None:
    """Batch prediction via file upload."""
    st.markdown('<div class="section-header">Batch Predictions</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="glass-card">',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Upload data for predictions",
        type=["csv", "xlsx", "parquet", "json"],
        key="predict_upload",
        help="Upload a file with the same columns as training data (target column optional).",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            elif uploaded.name.endswith((".xlsx", ".xls")):
                new_df = pd.read_excel(uploaded)
            elif uploaded.name.endswith(".parquet"):
                new_df = pd.read_parquet(uploaded)
            elif uploaded.name.endswith(".json"):
                new_df = pd.read_json(uploaded)
            else:
                st.error("Unsupported file format.")
                return
        except Exception as exc:
            st.error(f"Failed to read file: {exc}")
            return

        st.markdown(
            f'<div class="glass-card">'
            f'<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">'
            f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#22c55e;"></span>'
            f'<span style="color:#f1f5f9; font-weight:500;">Loaded {len(new_df)} rows, {len(new_df.columns)} columns</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.dataframe(new_df.head(10), use_container_width=True)

        # Validate columns
        feature_list: list[str] = st.session_state.get("feature_list", [])
        if feature_list:
            missing_cols = [c for c in feature_list if c not in new_df.columns]
            if missing_cols:
                st.warning(f"Missing columns: {', '.join(missing_cols[:10])}")

        st.session_state["prediction_input_data"] = new_df

        if st.button("Run Batch Predictions", type="primary", key="batch_predict_btn"):
            st.session_state["batch_prediction_submitted"] = True
            st.info("Prediction request submitted. Connect the pipeline for results.")

    # Show results
    batch_results = st.session_state.get("batch_prediction_results")
    if batch_results is not None:
        _render_batch_results(batch_results)


def _render_batch_results(results: pd.DataFrame) -> None:
    """Display batch prediction results."""
    st.markdown('<div class="section-header">Prediction Results</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.dataframe(results, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Download results
    csv_buf = io.StringIO()
    results.to_csv(csv_buf, index=False)
    st.download_button(
        "Download Predictions (CSV)",
        data=csv_buf.getvalue(),
        file_name="predictions.csv",
        mime="text/csv",
        key="dl_predictions",
    )

    # Distribution of predictions
    problem = st.session_state.get("problem_type", "")
    pred_col = "prediction" if "prediction" in results.columns else results.columns[-1]

    if problem == PROBLEM_CLASSIFICATION and pred_col in results.columns:
        from dashboard.components.chart_container import render_chart

        try:
            import plotly.express as px

            counts = results[pred_col].value_counts()
            fig = px.bar(x=counts.index.astype(str), y=counts.values, labels={"x": "Class", "y": "Count"})
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(22,22,31,0.6)",
                font=dict(color="#94a3b8"),
            )
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            render_chart(fig, title="Prediction Distribution", key="pred_dist")
            st.markdown('</div>', unsafe_allow_html=True)
        except ImportError:
            pass


def _render_single_prediction() -> None:
    """Single-row prediction form."""
    st.markdown('<div class="section-header">Single Prediction</div>', unsafe_allow_html=True)

    feature_list: list[str] = st.session_state.get("feature_list", [])
    if not feature_list:
        # Fallback: use training data columns minus target
        df = st.session_state.get("uploaded_data")
        target = st.session_state.get("target_column")
        if df is not None:
            feature_list = [c for c in df.columns if c != target]

    if not feature_list:
        st.markdown(
            '<div class="glass-card"><p style="color:#94a3b8; margin:0;">Feature list not available.</p></div>',
            unsafe_allow_html=True,
        )
        return

    df: pd.DataFrame = st.session_state["uploaded_data"]
    target = st.session_state.get("target_column")

    st.markdown(
        '<p class="glass-caption">Enter values for each feature to get a prediction.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    with st.form("single_prediction_form"):
        input_values: dict[str, Any] = {}
        cols_per_row = 3
        display_feats = [f for f in feature_list if f != target]

        for row_start in range(0, len(display_feats), cols_per_row):
            row_feats = display_feats[row_start : row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, feat in zip(cols, row_feats):
                with col:
                    if feat in df.columns and pd.api.types.is_numeric_dtype(df[feat]):
                        median_val = float(df[feat].median()) if not df[feat].isna().all() else 0.0
                        input_values[feat] = st.number_input(feat, value=median_val, key=f"single_{feat}")
                    elif feat in df.columns:
                        options = list(df[feat].dropna().unique()[:50])
                        input_values[feat] = st.selectbox(feat, options, key=f"single_{feat}")
                    else:
                        input_values[feat] = st.text_input(feat, key=f"single_{feat}")

        submitted = st.form_submit_button("Predict", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        st.session_state["single_prediction_input"] = input_values
        st.session_state["single_prediction_submitted"] = True

        # Show stored result if available
        result = st.session_state.get("single_prediction_result")
        if result:
            _render_single_result(result)
        else:
            st.info("Prediction request submitted. Connect the pipeline for results.")


def _render_single_result(result: dict[str, Any]) -> None:
    """Display a single prediction result as a prominent glass card."""
    prediction = result.get("prediction")
    confidence = result.get("confidence")
    explanation = result.get("explanation", [])

    confidence_pct = f"{confidence:.1%}" if confidence is not None else ""
    confidence_width = f"{confidence * 100:.0f}" if confidence is not None else "0"

    confidence_html = ""
    if confidence is not None:
        confidence_html = (
            f'<div class="confidence-bar-wrap">'
            f'<div class="confidence-bar-bg">'
            f'<div class="confidence-bar-fill" style="width:{confidence_width}%"></div>'
            f'</div>'
            f'<div class="confidence-text">Confidence: {confidence_pct}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="prediction-result">'
        f'<div class="prediction-label">Predicted Value</div>'
        f'<div class="prediction-value">{prediction}</div>'
        f'{confidence_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if explanation:
        factors_html = '<div class="glass-card"><div class="section-header">Key Factors</div>'
        for factor in explanation[:5]:
            factors_html += f'<div class="factor-item">{factor}</div>'
        factors_html += '</div>'
        st.markdown(factors_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------

_PRED_TAB_NAMES = ["Batch Predictions", "Single Prediction"]
_PRED_TAB_KEYS = ["batch", "single"]


def _render_pred_tabs() -> str:
    """Render glass pill tab navigation."""
    if "predict_active_tab" not in st.session_state:
        st.session_state["predict_active_tab"] = "batch"

    cols = st.columns(len(_PRED_TAB_NAMES))
    for i, (name, key) in enumerate(zip(_PRED_TAB_NAMES, _PRED_TAB_KEYS)):
        with cols[i]:
            if st.button(name, key=f"predtab_{key}", use_container_width=True):
                st.session_state["predict_active_tab"] = key
                st.rerun()

    active = st.session_state["predict_active_tab"]
    pills_html = '<div class="pill-tabs">'
    for name, key in zip(_PRED_TAB_NAMES, _PRED_TAB_KEYS):
        active_cls = " active" if key == active else ""
        pills_html += f'<div class="pill-tab{active_cls}">{name}</div>'
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    return active


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Predictions</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Generate predictions using your trained model</div>', unsafe_allow_html=True)
    _render_progress()
    _render_model_info()

    active_tab = _render_pred_tabs()

    tab_batch, tab_single = st.tabs(_PRED_TAB_NAMES)

    if active_tab == "batch":
        with tab_batch:
            _render_batch_upload()
    elif active_tab == "single":
        with tab_single:
            _render_single_prediction()

    # Navigation
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1px; background:rgba(99,102,241,0.1); margin:0.5rem 0 1.5rem;"></div>', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Explainability", use_container_width=True):
            st.switch_page("pages/06_explainability.py")
    with col_next:
        if st.button("Proceed to Chat", type="primary", use_container_width=True):
            st.switch_page("pages/08_chat.py")


_page()
