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
        from dashboard.components.metric_cards import render_metric_cards

        st.info(f"Using model: **{best}**")
        if metrics:
            render_metric_cards(metrics, columns=4, title="Model Performance")


def _render_batch_upload() -> None:
    """Batch prediction via file upload."""
    st.subheader("Batch Predictions")

    uploaded = st.file_uploader(
        "Upload data for predictions",
        type=["csv", "xlsx", "parquet", "json"],
        key="predict_upload",
        help="Upload a file with the same columns as training data (target column optional).",
    )

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

        st.success(f"Loaded {len(new_df)} rows, {len(new_df.columns)} columns")
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
    st.subheader("Prediction Results")
    st.dataframe(results, use_container_width=True)

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
            render_chart(fig, title="Prediction Distribution", key="pred_dist")
        except ImportError:
            pass


def _render_single_prediction() -> None:
    """Single-row prediction form."""
    st.subheader("Single Prediction")

    feature_list: list[str] = st.session_state.get("feature_list", [])
    if not feature_list:
        # Fallback: use training data columns minus target
        df = st.session_state.get("uploaded_data")
        target = st.session_state.get("target_column")
        if df is not None:
            feature_list = [c for c in df.columns if c != target]

    if not feature_list:
        st.info("Feature list not available.")
        return

    df: pd.DataFrame = st.session_state["uploaded_data"]
    target = st.session_state.get("target_column")

    st.caption("Enter values for each feature to get a prediction.")

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
    """Display a single prediction result."""
    prediction = result.get("prediction")
    confidence = result.get("confidence")
    explanation = result.get("explanation", [])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Prediction", str(prediction))
    with col2:
        if confidence is not None:
            st.metric("Confidence", f"{confidence:.1%}")

    if explanation:
        st.markdown("**Key factors:**")
        for factor in explanation[:5]:
            st.markdown(f"- {factor}")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Predictions")
    _render_progress()
    _render_model_info()
    st.divider()

    tab_batch, tab_single = st.tabs(["Batch Predictions", "Single Prediction"])

    with tab_batch:
        _render_batch_upload()
    with tab_single:
        _render_single_prediction()

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Explainability", use_container_width=True):
            st.switch_page("pages/06_explainability.py")
    with col_next:
        if st.button("Proceed to Chat", type="primary", use_container_width=True):
            st.switch_page("pages/08_chat.py")


_page()
