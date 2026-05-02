"""Bottom action bar — 2-column (Next steps + Run summary)."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render(on_continue, on_reconfigure, on_export) -> None:
    """Render the bottom action bar.

    Args:
        on_continue() — Continue to Features
        on_reconfigure() — go back to Questions phase
        on_export() — export EDA report
    """
    project = project_service.get_active()  # noqa: F841 — used for future guard

    st.markdown('<section class="ed-actions">', unsafe_allow_html=True)
    cols = st.columns([1.4, 1], gap="medium")

    with cols[0]:
        st.markdown(
            '<div class="ed-actions-card">'
            '  <h4>Next steps</h4>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Continue to Features →", key="ed_action_continue",
                     type="primary", use_container_width=True):
            on_continue()
        if st.button("⟲ Reconfigure questions", key="ed_action_reconfig",
                     use_container_width=True):
            on_reconfigure()
        if st.button("⬇ Export EDA report", key="ed_action_export",
                     use_container_width=True):
            on_export()

    with cols[1]:
        n_charts = len(st.session_state.get("eda_charts", []))
        n_stats = len(st.session_state.get("eda_stats", []))
        n_insights = len(st.session_state.get("eda_insights", []))
        runtime = st.session_state.get("ed_run_runtime_str", "—")
        cost = st.session_state.get("ed_run_cost_str", "—")

        st.markdown(
            f'<div class="ed-actions-card ed-actions-summary">'
            f'  <h4>Run summary</h4>'
            f'  <div class="ed-run-summary">'
            f'    <div>{n_charts} charts generated</div>'
            f'    <div>{n_stats} stat tests run</div>'
            f'    <div>{n_insights} insights extracted</div>'
            f'    <div>Runtime: {runtime}</div>'
            f'    <div>LLM cost: {cost}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</section>', unsafe_allow_html=True)
