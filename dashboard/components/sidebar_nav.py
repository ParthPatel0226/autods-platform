"""Sidebar navigation component.

Renders the brand header, workspace status, pipeline step buttons with
status dots, tool shortcuts, and footer actions.

Usage in any page:
    from dashboard.components.sidebar_nav import render as render_sidebar
    render_sidebar()
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.auth_service import current_user, logout

try:
    from core.constants import PLATFORM_VERSION
except Exception:  # graceful fallback when core not on path
    PLATFORM_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

_PIPELINE_STEPS: list[dict[str, str]] = [
    {"key": "upload",              "label": "Upload Data",    "page": "pages/01_upload.py"},
    {"key": "configure",           "label": "Configure",      "page": "pages/02_configure.py"},
    {"key": "eda",                 "label": "EDA",            "page": "pages/03_eda_interactive.py"},
    {"key": "feature_engineering", "label": "Features",       "page": "pages/04_feature_engineering.py"},
    {"key": "modeling",            "label": "Modeling",       "page": "pages/05_modeling.py"},
    {"key": "explainability",      "label": "Explain",        "page": "pages/06_explainability.py"},
    {"key": "predict",             "label": "Predict",        "page": "pages/07_predict.py"},
]

_TOOL_STEPS: list[dict[str, str]] = [
    {"key": "followup", "label": "Chat",     "page": "pages/08_chat.py"},
    {"key": "download", "label": "Download", "page": "pages/09_download.py"},
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _step_status(key: str) -> str:
    """Return 'done', 'current', or 'pending' for a pipeline step."""
    completed: list[str] = st.session_state.get("completed_steps", [])
    current: str = st.session_state.get("current_step", "upload")
    if key in completed:
        return "done"
    if key == current:
        return "current"
    return "pending"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_brand() -> None:
    user = current_user()
    email = user["email"] if user else "Guest"
    st.markdown(
        f'<div class="snav-brand">'
        f'<div class="snav-logo-mark">'
        f'<svg viewBox="0 0 16 16" fill="none" width="20" height="20">'
        f'<path d="M2 8 L6 4 L10 8 L14 4" stroke="white" stroke-width="2"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M2 12 L6 8 L10 12 L14 8" stroke="white" stroke-width="2"'
        f' stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
        f"</svg></div>"
        f'<div><div class="snav-logo-name">AutoDS</div>'
        f'<div class="snav-logo-sub">v{PLATFORM_VERSION}&nbsp;·&nbsp;{email}</div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_workspace() -> None:
    st.markdown('<div class="snav-section-label">Workspace</div>', unsafe_allow_html=True)
    has_data = "uploaded_data" in st.session_state
    dataset_name = st.session_state.get("uploaded_file_name", "No dataset loaded")
    dot_cls = "snav-status-ok" if has_data else "snav-status-idle"
    st.markdown(
        f'<div class="snav-workspace-card">'
        f'<span class="{dot_cls}">&#9679;</span>&nbsp;{dataset_name}'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_pipeline() -> None:
    st.markdown('<div class="snav-section-label">Pipeline</div>', unsafe_allow_html=True)
    has_data = "uploaded_data" in st.session_state
    st.markdown('<div class="snav-pipeline">', unsafe_allow_html=True)
    for step in _PIPELINE_STEPS:
        status = _step_status(step["key"])
        st.markdown(
            f'<div class="snav-step-row">'
            f'<div class="snav-dot snav-dot-{status}"></div>',
            unsafe_allow_html=True,
        )
        enabled = has_data or step["key"] == "upload"
        if st.button(
            step["label"],
            key=f"snav_{step['key']}",
            use_container_width=True,
            disabled=not enabled,
        ):
            st.switch_page(step["page"])
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_tools() -> None:
    st.markdown('<div class="snav-section-label">Tools</div>', unsafe_allow_html=True)
    has_data = "uploaded_data" in st.session_state
    for step in _TOOL_STEPS:
        if st.button(
            step["label"],
            key=f"snav_{step['key']}",
            use_container_width=True,
            disabled=not has_data,
        ):
            st.switch_page(step["page"])


def _render_footer() -> None:
    st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)
    if st.button("New Session", key="snav_new_session", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    if st.button("Logout", key="snav_logout", use_container_width=True):
        logout()
        st.rerun()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full sidebar navigation inside st.sidebar."""
    with st.sidebar:
        _render_brand()
        st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)
        _render_workspace()
        st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)
        _render_pipeline()
        st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)
        _render_tools()
        _render_footer()
