"""Quick goal chips shown in Auto mode to help users who aren't sure of their goal."""
from __future__ import annotations

import streamlit as st

QUICK_GOALS: list[dict] = [
    {
        "key": "predict",
        "label": "Predict an outcome",
        "icon": "🎯",
        "problem_type": "classification",
        "goal": "Predict which records will have a specific outcome",
    },
    {
        "key": "forecast",
        "label": "Forecast a number",
        "icon": "📈",
        "problem_type": "regression",
        "goal": "Forecast or estimate a numeric value",
    },
    {
        "key": "groups",
        "label": "Find natural groups",
        "icon": "🔮",
        "problem_type": "clustering",
        "goal": "Discover natural clusters or segments in the data",
    },
    {
        "key": "anomaly",
        "label": "Detect anomalies",
        "icon": "🚨",
        "problem_type": "classification",
        "goal": "Identify unusual records or outliers",
    },
    {
        "key": "trend",
        "label": "Understand trends",
        "icon": "📊",
        "problem_type": "time_series",
        "goal": "Analyse patterns and trends over time",
    },
]


def render(columns: list[str] | None = None) -> None:
    """Render quick goal chips. Only shown when cf_mode == 'auto'."""
    if st.session_state.get("cf_mode", "guided") != "auto":
        return

    st.markdown('<div class="cf-unsure-label">Not sure? Pick a goal to get started:</div>', unsafe_allow_html=True)

    chips_html = ""
    for g in QUICK_GOALS:
        chips_html += (
            f'<span class="cf-chip" id="cf_chip_{g["key"]}">'
            f'{g["icon"]} {g["label"]}'
            f'</span>'
        )
    st.markdown(f'<div class="cf-chips-row">{chips_html}</div>', unsafe_allow_html=True)

    cols = st.columns(len(QUICK_GOALS))
    for col, g in zip(cols, QUICK_GOALS):
        with col:
            if st.button(
                f'{g["icon"]} {g["label"]}',
                key=f"cf_chip_btn_{g['key']}",
                use_container_width=True,
            ):
                st.session_state["cf_problem_type"] = g["problem_type"]
                st.session_state["cf_goal"] = g["goal"]
                # Don't pre-set target — let user pick after seeing problem type
                st.rerun()
