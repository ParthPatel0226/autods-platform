"""Page 09 -- Download.

Download all reports, models, processed data, and notebooks generated
by the pipeline.
"""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

_ALLOWED_OUTPUTS_DIR = Path(os.path.abspath("outputs"))


def _safe_read_bytes(path_str: str) -> bytes:
    """Read file bytes only if the path is contained within the allowed outputs directory."""
    resolved = Path(os.path.abspath(path_str))
    if not str(resolved).startswith(str(_ALLOWED_OUTPUTS_DIR)):
        raise ValueError(f"Path is outside allowed outputs directory: {path_str!r}")
    return resolved.read_bytes()


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
        "current_step": st.session_state.get("current_step", "download"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_reports_section() -> None:
    """Download generated reports (HTML, PDF, executive, notebook)."""
    st.subheader("Reports")

    report_paths: dict[str, str] = st.session_state.get("report_paths", {})
    if report_paths:
        from dashboard.components.download_buttons import render_download_buttons

        render_download_buttons(report_paths)
    else:
        st.info("No reports generated yet. Complete the analysis pipeline first.")


def _render_data_section() -> None:
    """Download processed and original data."""
    st.subheader("Data")

    col1, col2 = st.columns(2)

    with col1:
        # Original data
        df: pd.DataFrame | None = st.session_state.get("uploaded_data")
        if df is not None:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "Original Data (CSV)",
                data=csv_buf.getvalue(),
                file_name="original_data.csv",
                mime="text/csv",
                key="dl_original",
                use_container_width=True,
            )

    with col2:
        # Processed/engineered data
        processed: pd.DataFrame | None = st.session_state.get("processed_data")
        if processed is not None:
            csv_buf = io.StringIO()
            processed.to_csv(csv_buf, index=False)
            st.download_button(
                "Processed Data (CSV)",
                data=csv_buf.getvalue(),
                file_name="processed_data.csv",
                mime="text/csv",
                key="dl_processed",
                use_container_width=True,
            )
        else:
            st.caption("Processed data not yet available.")

    # Prediction results
    pred_results: pd.DataFrame | None = st.session_state.get("batch_prediction_results")
    if pred_results is not None:
        csv_buf = io.StringIO()
        pred_results.to_csv(csv_buf, index=False)
        st.download_button(
            "Prediction Results (CSV)",
            data=csv_buf.getvalue(),
            file_name="predictions.csv",
            mime="text/csv",
            key="dl_pred_results",
            use_container_width=True,
        )


def _render_model_section() -> None:
    """Download model artifacts."""
    st.subheader("Model Artifacts")

    best_path = st.session_state.get("best_model_path", "")
    best_name = st.session_state.get("best_model_name", "")

    if best_path and Path(best_path).is_file():
        try:
            model_bytes = _safe_read_bytes(best_path)
        except ValueError as e:
            st.error(f"Cannot download model: {e}")
            return
        st.download_button(
            f"Best Model: {best_name}",
            data=model_bytes,
            file_name=Path(best_path).name,
            mime="application/octet-stream",
            key="dl_best_model",
            use_container_width=True,
        )
    else:
        st.info("No trained model available for download.")

    # Model card
    card: dict | None = st.session_state.get("model_card")
    if card:
        card_json = json.dumps(card, indent=2, default=str)
        st.download_button(
            "Model Card (JSON)",
            data=card_json,
            file_name="model_card.json",
            mime="application/json",
            key="dl_model_card",
            use_container_width=True,
        )


def _render_deployment_section() -> None:
    """Download deployment artifacts (API code, Dockerfile)."""
    st.subheader("Deployment Package")

    api_code: str | None = st.session_state.get("api_endpoint_code")
    dockerfile: str | None = st.session_state.get("dockerfile_content")

    if not api_code and not dockerfile:
        st.info("Deployment artifacts not yet generated.")
        return

    col1, col2 = st.columns(2)

    with col1:
        if api_code:
            st.download_button(
                "FastAPI Endpoint (api.py)",
                data=api_code,
                file_name="api.py",
                mime="text/x-python",
                key="dl_api",
                use_container_width=True,
            )

    with col2:
        if dockerfile:
            st.download_button(
                "Dockerfile",
                data=dockerfile,
                file_name="Dockerfile",
                mime="text/plain",
                key="dl_dockerfile",
                use_container_width=True,
            )


def _render_audit_section() -> None:
    """Download audit trail and decision log."""
    st.subheader("Audit Trail")

    decision_log: list[dict] = st.session_state.get("decision_log", [])
    pipeline_log: list[dict] = st.session_state.get("pipeline_log", [])

    col1, col2, col3 = st.columns(3)

    with col1:
        if decision_log:
            log_json = json.dumps(decision_log, indent=2, default=str)
            st.download_button(
                "Decision Log (JSON)",
                data=log_json,
                file_name="decision_log.json",
                mime="application/json",
                key="dl_decision_log",
                use_container_width=True,
            )
        else:
            st.caption("No decision log available.")

    with col2:
        if pipeline_log:
            log_json = json.dumps(pipeline_log, indent=2, default=str)
            st.download_button(
                "Pipeline Log (JSON)",
                data=log_json,
                file_name="pipeline_log.json",
                mime="application/json",
                key="dl_pipeline_log",
                use_container_width=True,
            )
        else:
            st.caption("No pipeline log available.")

    with col3:
        cost = st.session_state.get("estimated_cost_usd", 0.0)
        tokens = st.session_state.get("api_token_count", 0)
        calls = st.session_state.get("api_call_count", 0)
        if calls > 0:
            st.metric("API Calls", f"{calls}")
            st.metric("Tokens Used", f"{tokens:,}")
            st.metric("Estimated Cost", f"${cost:.4f}")


def _render_session_summary() -> None:
    """Summary of completed pipeline steps."""
    completed: list[str] = st.session_state.get("completed_steps", [])
    if completed:
        st.subheader("Pipeline Summary")
        for step in completed:
            st.markdown(f"- {step.replace('_', ' ').title()}")

        errors: list[dict] = st.session_state.get("errors", [])
        warnings: list[dict] = st.session_state.get("warnings", [])
        if errors:
            st.error(f"{len(errors)} error(s) occurred during pipeline execution.")
        if warnings:
            st.warning(f"{len(warnings)} warning(s) issued during pipeline execution.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Download Reports & Outputs")
    _render_progress()

    _render_reports_section()
    st.divider()
    _render_data_section()
    st.divider()
    _render_model_section()
    st.divider()
    _render_deployment_section()
    st.divider()
    _render_audit_section()
    st.divider()
    _render_session_summary()

    # Navigation
    st.divider()
    col_back, _ = st.columns(2)
    with col_back:
        if st.button("Back to Chat", use_container_width=True):
            st.switch_page("pages/08_chat.py")


_page()
