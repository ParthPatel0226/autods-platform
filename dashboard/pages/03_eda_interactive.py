"""EDA Interactive — two-phase: questions → results dashboard.

Auto mode shows compact recommendations instead of full questions.
Results phase has insights, target callout, featured heatmap, charts grid,
stats table, quality flags, generalized chat composer, filters bar, action bar.
"""
from __future__ import annotations
import time
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

from dashboard.components.ed_phase_router import (
    get_phase, set_phase, auto_set_initial_phase, render_phase_toggle,
)
from dashboard.components.ed_questions_panel import render as render_questions
from dashboard.components.ed_auto_recommendations import render as render_auto
from dashboard.components.ed_insights_summary import render as render_insights
from dashboard.components.ed_target_callout import render as render_target
from dashboard.components.ed_featured_chart import render as render_featured
from dashboard.components.ed_charts_grid import render as render_charts
from dashboard.components.ed_stats_findings import render as render_stats
from dashboard.components.ed_quality_flags import render as render_flags
from dashboard.components.ed_chat_composer import render as render_chat
from dashboard.components.ed_filters_bar import render as render_filters
from dashboard.components.ed_action_bar import render as render_actions


def _is_streamlit_running() -> bool:
    try:
        from streamlit.runtime import get_instance
        return get_instance() is not None
    except Exception:
        return False


if not _is_streamlit_running():
    pass
else:
    st.set_page_config(
        page_title="AutoDS — EDA",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_shared_css()

    # ---- gates ----
    if not auth_service.is_authenticated():
        st.switch_page("pages/00_login.py")
        st.stop()

    render_sidebar()

    project = project_service.get_active()
    if project is None:
        st.warning("Open a project from the home page to continue.")
        if st.button("← Go to home"):
            st.switch_page("app.py")
        st.stop()

    df = st.session_state.get("df")
    if df is None or df.empty:
        st.warning("No dataset loaded. Return to Upload.")
        if st.button("← Back to Upload"):
            st.switch_page("pages/01_upload.py")
        st.stop()

    auto_set_initial_phase()
    current_phase = get_phase()

    # ---- topbar ----
    top_cols = st.columns([6, 2, 1])
    with top_cols[0]:
        st.markdown(
            f'<div class="ed-crumbs">'
            f'  <span>{project.name}</span>'
            f'  <span class="sep">/</span>'
            f'  <span class="cur">EDA</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with top_cols[1]:
        render_phase_toggle()

    # ---- hero ----
    if current_phase == "questions":
        title_html = 'Configure your <em>analysis questions.</em>'
        subtitle = "Pick the goals, visualizations, and statistical tests you want. AutoDS will run them all in one go and show you the results."
    else:
        n_insights = len(st.session_state.get("eda_insights", []))
        n_charts = len(st.session_state.get("eda_charts", []))
        n_stats = len(st.session_state.get("eda_stats", []))
        title_html = 'Your <em>EDA results.</em>'
        subtitle = f"{n_insights} insights, {n_charts} charts, {n_stats} statistical tests. Filter, drill in, or ask a follow-up."

    st.markdown(
        f'<section class="ed-hero">'
        f'  <div class="ed-eyebrow">📊 Step 3 of 7 — Exploratory Data Analysis</div>'
        f'  <h1>{title_html}</h1>'
        f'  <p>{subtitle}</p>'
        f'</section>',
        unsafe_allow_html=True,
    )

    # ---- callbacks ----

    def _run_analysis_from_questions(answers: list[dict]) -> None:
        _execute_eda_run({"answers": answers})

    def _run_analysis_from_auto(spec: dict) -> None:
        _execute_eda_run({"auto_spec": spec})

    def _execute_eda_run(payload: dict) -> None:
        p = project_service.get_active()
        started = time.time()

        with st.spinner("Running analysis — generating charts, statistical tests, and insights..."):
            try:
                from agents.eda_agent import run_analyses
                state = {
                    "df_ref": "main",
                    "domain": p.confirmed_domain or p.detected_domain,
                    "target_column": p.target_column,
                    "problem_type": p.problem_type,
                    "analysis_mode": p.analysis_mode,
                    "goal": p.goal,
                    "excluded_columns": p.excluded_columns,
                    "user_answers": payload,
                }
                results = run_analyses(state)

                st.session_state["eda_results"] = results
                st.session_state["eda_charts"] = results.get("charts", [])
                st.session_state["eda_stats"] = results.get("stats", [])
                st.session_state["eda_insights"] = results.get("insights", [])
                st.session_state["eda_quality_flags"] = results.get("quality_flags", {})

                elapsed = int(time.time() - started)
                m, s = divmod(elapsed, 60)
                st.session_state["ed_run_runtime_str"] = f"{m} min {s:02d} s" if m else f"{s} s"
                st.session_state["ed_run_cost_str"] = results.get("llm_cost_str", "—")

            except Exception as e:
                st.error(f"Analysis failed: {e}. Check that the EDA agent is configured.")
                return

        n_c = len(st.session_state.get("eda_charts", []))
        n_s = len(st.session_state.get("eda_stats", []))
        n_i = len(st.session_state.get("eda_insights", []))

        p.step_status["eda"] = "done"
        p.step_status["features"] = "active"
        p.eda_completed = True
        p.eda_summary = f"{n_i} insights · {n_c} charts · {n_s} tests"
        project_service.update(p)
        set_phase("results")
        st.rerun()

    def _handle_followup(prompt: str) -> None:
        p = project_service.get_active()
        try:
            from agents.eda_agent import add_followup_analysis
            state = {
                "df_ref": "main",
                "domain": p.confirmed_domain or p.detected_domain,
                "target_column": p.target_column,
                "problem_type": p.problem_type,
                "previous_results": st.session_state.get("eda_results"),
            }
            new_outputs = add_followup_analysis(state, prompt)

            if "charts" in new_outputs:
                st.session_state["eda_charts"] = new_outputs["charts"] + st.session_state.get("eda_charts", [])
            if "stats" in new_outputs:
                st.session_state["eda_stats"] = new_outputs["stats"] + st.session_state.get("eda_stats", [])
            if "insights" in new_outputs:
                st.session_state["eda_insights"] = new_outputs["insights"] + st.session_state.get("eda_insights", [])

        except (ImportError, AttributeError):
            try:
                from agents.followup_agent import handle as followup_handle
                followup_handle(prompt, st.session_state.get("eda_results", {}))
                st.success(f"Added: {prompt}")
            except Exception as e:
                st.warning(f"Follow-up not yet wired: {e}")
        except Exception as e:
            st.error(f"Follow-up failed: {e}")

    def _handle_continue() -> None:
        st.switch_page("pages/04_feature_engineering.py")

    def _handle_reconfigure() -> None:
        set_phase("questions")
        st.rerun()

    def _handle_export() -> None:
        try:
            from agents.report_agent import generate_eda_report
            path = generate_eda_report(st.session_state.get("eda_results", {}))
            st.success(f"EDA report exported to {path}")
        except Exception as e:
            st.warning(f"Export not wired yet: {e}")

    # ---- phase rendering ----
    st.markdown('<div class="ed-phase-wrap">', unsafe_allow_html=True)

    if current_phase == "questions":
        if (project.analysis_mode or "guided") == "auto":
            render_auto(on_run=_run_analysis_from_auto)
        else:
            render_questions(on_run=_run_analysis_from_questions)
    else:
        render_insights()
        render_target()
        render_featured()
        render_charts()
        render_stats()
        render_flags()
        render_chat(on_submit=_handle_followup)
        render_filters()
        render_actions(
            on_continue=_handle_continue,
            on_reconfigure=_handle_reconfigure,
            on_export=_handle_export,
        )

    st.markdown('</div>', unsafe_allow_html=True)
