"""Problem-type pill selector for the Configure tab."""
from __future__ import annotations

import streamlit as st

PROBLEM_TYPES: list[dict] = [
    {"key": "classification", "label": "Classification", "icon": "🏷️", "desc": "Predict a category"},
    {"key": "regression", "label": "Regression", "icon": "📐", "desc": "Predict a number"},
    {"key": "clustering", "label": "Clustering", "icon": "🔮", "desc": "Find groups"},
    {"key": "time_series", "label": "Time Series", "icon": "📅", "desc": "Forecast over time"},
    {"key": "anomaly_detection", "label": "Anomaly", "icon": "🚨", "desc": "Detect outliers"},
    {"key": "auto", "label": "Auto-detect", "icon": "⚡", "desc": "Let AI decide"},
]


def render(detected_type: str = "auto", on_select=None) -> str:
    """Render 6 problem-type pills.

    State key: cf_problem_type
    Returns selected problem type key.
    """
    selected = st.session_state.get("cf_problem_type", detected_type or "auto")

    pills_html = ""
    for pt in PROBLEM_TYPES:
        is_sel = pt["key"] == selected
        is_det = pt["key"] == detected_type
        classes = "cf-problem-pill"
        if is_sel:
            classes += " cf-pill-selected"
        badge = '<span class="cf-pill-badge">Detected</span>' if is_det else ""
        pills_html += (
            f'<span class="{classes}">'
            f'  {badge}{pt["icon"]} {pt["label"]}'
            f'  <small>{pt["desc"]}</small>'
            f'</span>'
        )
    st.markdown(
        f'<div class="cf-pills-row">{pills_html}</div>'
        '<style>'
        '.stMarkdown:has(.cf-pills-row) + [data-testid="stHorizontalBlock"] {'
        '  margin-top: -44px !important;'
        '  opacity: 0 !important;'
        '  position: relative !important;'
        '  z-index: 5 !important;'
        '  height: 44px !important;'
        '  overflow: hidden !important;'
        '}'
        '</style>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(PROBLEM_TYPES))
    for col, pt in zip(cols, PROBLEM_TYPES):
        with col:
            if st.button(
                pt["label"],
                key=f"cf_pt_btn_{pt['key']}",
                use_container_width=True,
            ):
                st.session_state["cf_problem_type"] = pt["key"]
                if on_select:
                    on_select(pt["key"])
                st.rerun()

    return st.session_state.get("cf_problem_type", detected_type or "auto")
