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

from dashboard.components.shared_css import inject_shared_css

logger = logging.getLogger(__name__)

_ALLOWED_OUTPUTS_DIR = Path(os.path.abspath("outputs"))


def _safe_read_bytes(path_str: str) -> bytes:
    """Read file bytes only if the path is contained within the allowed outputs directory."""
    resolved = Path(os.path.abspath(path_str))
    if not str(resolved).startswith(str(_ALLOWED_OUTPUTS_DIR)):
        raise ValueError(f"Path is outside allowed outputs directory: {path_str!r}")
    return resolved.read_bytes()


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* Page title */
.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-bottom: 1.5rem;
}

/* Download card grid */
.download-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
@media (max-width: 768px) {
    .download-grid { grid-template-columns: 1fr; }
}

/* Download card */
.dl-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.5rem;
    box-shadow: var(--shadow-card);
    transition: all var(--transition-fast);
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.dl-card:hover {
    border-color: var(--border-active);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

/* File type icon (CSS shape) */
.dl-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #ffffff;
    flex-shrink: 0;
}
.dl-icon-indigo { background: linear-gradient(135deg, var(--accent-primary), #818cf8); }
.dl-icon-red { background: linear-gradient(135deg, var(--accent-danger), #f87171); }
.dl-icon-green { background: linear-gradient(135deg, var(--accent-success), #4ade80); }
.dl-icon-purple { background: linear-gradient(135deg, #a855f7, #c084fc); }
.dl-icon-sky { background: linear-gradient(135deg, var(--accent-secondary), #38bdf8); }
.dl-icon-amber { background: linear-gradient(135deg, var(--accent-warning), #fbbf24); }

.dl-card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.dl-card-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
}
.dl-card-desc {
    font-size: 0.78rem;
    color: var(--text-muted);
    line-height: 1.5;
}

/* Audit log entries */
.audit-entry {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--accent-primary-subtle);
}
.audit-entry:last-child { border-bottom: none; }
.audit-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-primary);
    margin-top: 0.35rem;
    flex-shrink: 0;
}
.audit-text {
    font-size: 0.82rem;
    color: var(--text-secondary);
}
.audit-step {
    font-weight: 500;
    color: var(--text-primary);
}

/* Metric mini cards for cost section */
.metric-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}
.metric-mini {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.875rem 1.25rem;
    flex: 1;
    min-width: 120px;
}
.metric-mini-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
}
.metric-mini-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
}

/* Pipeline summary */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
}
.pipeline-check {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(34,197,94,0.15);
    border: 1px solid rgba(34,197,94,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    color: var(--accent-success);
    flex-shrink: 0;
}

.glass-caption {
    font-size: 0.78rem;
    color: var(--text-muted);
}

/* Alert overrides */
div[data-testid="stAlert"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.info("Run the analysis pipeline first to access downloads. This page provides HTML reports, executive PDFs, Jupyter notebooks, trained models, and full audit trails.")
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
    st.markdown('<div class="section-header">Reports</div>', unsafe_allow_html=True)

    report_paths: dict[str, str] = st.session_state.get("report_paths", {})
    if report_paths:
        from dashboard.components.download_buttons import render_download_buttons

        # Map report types to icons/colors
        _type_map = {
            "html": ("HTML", "dl-icon-indigo", "Interactive HTML report with embedded charts"),
            "pdf": ("PDF", "dl-icon-red", "Print-ready PDF report"),
            "executive": ("EXEC", "dl-icon-sky", "One-page executive summary"),
            "notebook": ("IPYNB", "dl-icon-green", "Runnable Jupyter notebook"),
            "zip": ("ZIP", "dl-icon-purple", "Complete output package"),
        }

        cards_html = '<div class="download-grid">'
        for rtype, rpath in report_paths.items():
            rtype_lower = rtype.lower()
            label, icon_cls, desc = _type_map.get(rtype_lower, (rtype.upper()[:4], "dl-icon-indigo", "Report file"))
            fname = Path(rpath).name if rpath else rtype
            cards_html += (
                f'<div class="dl-card">'
                f'<div class="dl-card-header">'
                f'<div class="dl-icon {icon_cls}">{label}</div>'
                f'<div class="dl-card-title">{fname}</div>'
                f'</div>'
                f'<div class="dl-card-desc">{desc}</div>'
                f'</div>'
            )
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        # Actual download buttons
        render_download_buttons(report_paths)
    else:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:var(--text-secondary); margin:0;">No reports generated yet. Complete the analysis pipeline first.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_data_section() -> None:
    """Download processed and original data."""
    st.markdown('<div class="section-header">Data</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        df: pd.DataFrame | None = st.session_state.get("uploaded_data")
        if df is not None:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-sky">CSV</div>'
                '<div class="dl-card-title">Original Data</div>'
                '</div>'
                '<div class="dl-card-desc">Raw uploaded dataset in CSV format</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "Download Original Data",
                data=csv_buf.getvalue(),
                file_name="original_data.csv",
                mime="text/csv",
                key="dl_original",
                use_container_width=True,
            )

    with col2:
        processed: pd.DataFrame | None = st.session_state.get("processed_data")
        if processed is not None:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-green">CSV</div>'
                '<div class="dl-card-title">Processed Data</div>'
                '</div>'
                '<div class="dl-card-desc">Cleaned and engineered dataset</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            csv_buf = io.StringIO()
            processed.to_csv(csv_buf, index=False)
            st.download_button(
                "Download Processed Data",
                data=csv_buf.getvalue(),
                file_name="processed_data.csv",
                mime="text/csv",
                key="dl_processed",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<div class="dl-card" style="opacity:0.5;">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-green" style="opacity:0.4;">CSV</div>'
                '<div class="dl-card-title" style="color:var(--text-muted);">Processed Data</div>'
                '</div>'
                '<div class="dl-card-desc">Not yet available</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    # Prediction results
    pred_results: pd.DataFrame | None = st.session_state.get("batch_prediction_results")
    if pred_results is not None:
        st.markdown(
            '<div class="dl-card" style="margin-top:0.5rem;">'
            '<div class="dl-card-header">'
            '<div class="dl-icon dl-icon-amber">PRED</div>'
            '<div class="dl-card-title">Prediction Results</div>'
            '</div>'
            '<div class="dl-card-desc">Batch prediction output with all scores</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        csv_buf = io.StringIO()
        pred_results.to_csv(csv_buf, index=False)
        st.download_button(
            "Download Predictions",
            data=csv_buf.getvalue(),
            file_name="predictions.csv",
            mime="text/csv",
            key="dl_pred_results",
            use_container_width=True,
        )


def _render_model_section() -> None:
    """Download model artifacts."""
    st.markdown('<div class="section-header">Model Artifacts</div>', unsafe_allow_html=True)

    best_path = st.session_state.get("best_model_path", "")
    best_name = st.session_state.get("best_model_name", "")

    col1, col2 = st.columns(2)

    with col1:
        if best_path and Path(best_path).is_file():
            st.markdown(
                f'<div class="dl-card">'
                f'<div class="dl-card-header">'
                f'<div class="dl-icon dl-icon-indigo">MDL</div>'
                f'<div class="dl-card-title">{best_name}</div>'
                f'</div>'
                f'<div class="dl-card-desc">Best performing trained model artifact</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            try:
                model_bytes = _safe_read_bytes(best_path)
            except ValueError as e:
                st.error(f"Cannot download model: {e}")
                return
            st.download_button(
                f"Download Model",
                data=model_bytes,
                file_name=Path(best_path).name,
                mime="application/octet-stream",
                key="dl_best_model",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<div class="dl-card" style="opacity:0.5;">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-indigo" style="opacity:0.4;">MDL</div>'
                '<div class="dl-card-title" style="color:var(--text-muted);">Model</div>'
                '</div>'
                '<div class="dl-card-desc">No trained model available</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with col2:
        card: dict | None = st.session_state.get("model_card")
        if card:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-purple">JSON</div>'
                '<div class="dl-card-title">Model Card</div>'
                '</div>'
                '<div class="dl-card-desc">Standardized model documentation</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            card_json = json.dumps(card, indent=2, default=str)
            st.download_button(
                "Download Model Card",
                data=card_json,
                file_name="model_card.json",
                mime="application/json",
                key="dl_model_card",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<div class="dl-card" style="opacity:0.5;">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-purple" style="opacity:0.4;">JSON</div>'
                '<div class="dl-card-title" style="color:var(--text-muted);">Model Card</div>'
                '</div>'
                '<div class="dl-card-desc">Not yet generated</div>'
                '</div>',
                unsafe_allow_html=True,
            )


def _render_deployment_section() -> None:
    """Download deployment artifacts (API code, Dockerfile)."""
    st.markdown('<div class="section-header">Deployment Package</div>', unsafe_allow_html=True)

    api_code: str | None = st.session_state.get("api_endpoint_code")
    dockerfile: str | None = st.session_state.get("dockerfile_content")

    if not api_code and not dockerfile:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:var(--text-secondary); margin:0;">Deployment artifacts not yet generated.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    col1, col2 = st.columns(2)

    with col1:
        if api_code:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-green">PY</div>'
                '<div class="dl-card-title">FastAPI Endpoint</div>'
                '</div>'
                '<div class="dl-card-desc">Ready-to-deploy API server code</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download API Code",
                data=api_code,
                file_name="api.py",
                mime="text/x-python",
                key="dl_api",
                use_container_width=True,
            )

    with col2:
        if dockerfile:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-sky">DOCK</div>'
                '<div class="dl-card-title">Dockerfile</div>'
                '</div>'
                '<div class="dl-card-desc">Container build instructions</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download Dockerfile",
                data=dockerfile,
                file_name="Dockerfile",
                mime="text/plain",
                key="dl_dockerfile",
                use_container_width=True,
            )


def _render_audit_section() -> None:
    """Download audit trail and decision log."""
    st.markdown('<div class="section-header">Audit Trail</div>', unsafe_allow_html=True)

    decision_log: list[dict] = st.session_state.get("decision_log", [])
    pipeline_log: list[dict] = st.session_state.get("pipeline_log", [])

    # Cost metrics row
    cost = st.session_state.get("estimated_cost_usd", 0.0)
    tokens = st.session_state.get("api_token_count", 0)
    calls = st.session_state.get("api_call_count", 0)

    if calls > 0:
        st.markdown(
            f'<div class="metric-row" style="margin-bottom:1rem;">'
            f'<div class="metric-mini">'
            f'<div class="metric-mini-label">API Calls</div>'
            f'<div class="metric-mini-value">{calls}</div>'
            f'</div>'
            f'<div class="metric-mini">'
            f'<div class="metric-mini-label">Tokens Used</div>'
            f'<div class="metric-mini-value">{tokens:,}</div>'
            f'</div>'
            f'<div class="metric-mini">'
            f'<div class="metric-mini-label">Estimated Cost</div>'
            f'<div class="metric-mini-value">${cost:.4f}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Log entries displayed as glass card with audit entries
    all_logs = []
    for entry in decision_log:
        all_logs.append(entry)
    for entry in pipeline_log:
        all_logs.append(entry)

    if all_logs:
        entries_html = ""
        for entry in all_logs[:20]:
            step = entry.get("step", entry.get("type", ""))
            detail = entry.get("detail", entry.get("description", entry.get("tool", "")))
            entries_html += (
                f'<div class="audit-entry">'
                f'<div class="audit-dot"></div>'
                f'<div class="audit-text">'
                f'<span class="audit-step">{step}</span> '
                f'{detail}'
                f'</div></div>'
            )

        st.markdown(
            f'<div class="glass-card">{entries_html}</div>',
            unsafe_allow_html=True,
        )

    # Download buttons for logs
    col1, col2 = st.columns(2)

    with col1:
        if decision_log:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-amber">LOG</div>'
                '<div class="dl-card-title">Decision Log</div>'
                '</div>'
                '<div class="dl-card-desc">Record of all agent decisions and reasoning</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            log_json = json.dumps(decision_log, indent=2, default=str)
            st.download_button(
                "Download Decision Log",
                data=log_json,
                file_name="decision_log.json",
                mime="application/json",
                key="dl_decision_log",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<p class="glass-caption">No decision log available.</p>',
                unsafe_allow_html=True,
            )

    with col2:
        if pipeline_log:
            st.markdown(
                '<div class="dl-card">'
                '<div class="dl-card-header">'
                '<div class="dl-icon dl-icon-indigo">LOG</div>'
                '<div class="dl-card-title">Pipeline Log</div>'
                '</div>'
                '<div class="dl-card-desc">Timestamped record of all pipeline actions</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            log_json = json.dumps(pipeline_log, indent=2, default=str)
            st.download_button(
                "Download Pipeline Log",
                data=log_json,
                file_name="pipeline_log.json",
                mime="application/json",
                key="dl_pipeline_log",
                use_container_width=True,
            )
        else:
            st.markdown(
                '<p class="glass-caption">No pipeline log available.</p>',
                unsafe_allow_html=True,
            )


def _render_session_summary() -> None:
    """Summary of completed pipeline steps."""
    completed: list[str] = st.session_state.get("completed_steps", [])
    if completed:
        st.markdown('<div class="section-header">Pipeline Summary</div>', unsafe_allow_html=True)

        steps_html = '<div class="glass-card">'
        for step in completed:
            label = step.replace("_", " ").title()
            steps_html += (
                f'<div class="pipeline-step">'
                f'<div class="pipeline-check">&#10003;</div>'
                f'{label}'
                f'</div>'
            )
        steps_html += '</div>'
        st.markdown(steps_html, unsafe_allow_html=True)

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
    inject_shared_css()
    _guard()
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Download Reports & Outputs</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Access all generated artifacts from your analysis pipeline</div>', unsafe_allow_html=True)
    _render_progress()

    _render_reports_section()
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    _render_data_section()
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    _render_model_section()
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    _render_deployment_section()
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    _render_audit_section()
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    _render_session_summary()

    # Navigation
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:0.5rem 0 1.5rem;"></div>', unsafe_allow_html=True)
    col_back, _ = st.columns(2)
    with col_back:
        if st.button("Back to Chat", use_container_width=True):
            st.switch_page("pages/08_chat.py")



def _is_streamlit_running() -> bool:
    """Return True only when executing inside a Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _is_streamlit_running():
    _page()
