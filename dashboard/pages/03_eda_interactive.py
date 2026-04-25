"""Page 03 -- Interactive Exploratory Data Analysis.

Displays workflow progress, EDA questions (Guided / Expert), analysis results
with charts and insights, and an AI-generated summary.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED

logger = logging.getLogger(__name__)


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
    """Show pipeline progress bar in the sidebar."""
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "eda"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_summary() -> None:
    """Show the AI-generated EDA summary if available."""
    summary = st.session_state.get("eda_summary", "")
    if summary:
        st.info(summary)


def _render_quality_metrics() -> None:
    """Show data-quality metric cards."""
    from dashboard.components.metric_cards import render_metric_cards

    df: pd.DataFrame = st.session_state["uploaded_data"]
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    completeness = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 1.0
    duplicate_rows = int(df.duplicated().sum())

    quality_metrics: dict[str, float] = {
        "completeness": completeness,
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "columns": float(df.shape[1]),
        "rows": float(df.shape[0]),
    }
    render_metric_cards(quality_metrics, columns=5, title="Data Quality Overview")


def _render_questions() -> None:
    """Render EDA questions for Guided / Expert modes."""
    from dashboard.components.question_renderer import render_question_group

    mode = st.session_state.get("user_mode", MODE_GUIDED)
    if mode == MODE_AUTO:
        st.caption("Auto mode -- the system selects analyses automatically.")
        return

    questions = st.session_state.get("eda_questions", [])
    if not questions:
        questions = _generate_default_questions()
        st.session_state["eda_questions"] = questions

    st.subheader("Analysis Options")

    if mode == MODE_EXPERT:
        st.caption("Expert mode -- you have full control over every analysis.")
    else:
        st.caption("Guided mode -- AI recommendations are highlighted.")

    responses = render_question_group(questions, key_prefix="eda")

    if st.button("Run Selected Analyses", key="eda_run_btn", type="primary"):
        st.session_state["eda_user_responses"] = responses
        st.session_state["eda_analyses_submitted"] = True
        st.rerun()


def _generate_default_questions() -> list[dict[str, Any]]:
    """Build a default set of EDA questions when none come from the agent."""
    df: pd.DataFrame = st.session_state["uploaded_data"]
    numeric_cols = list(df.select_dtypes(include="number").columns)
    has_target = st.session_state.get("target_column") is not None

    questions: list[dict[str, Any]] = [
        {
            "id": "eda_goal",
            "question": "What is your primary analysis goal?",
            "type": "single_select",
            "options": [
                {"value": "understand_target", "label": "Understand what drives the target", "recommended": has_target},
                {"value": "relationships", "label": "Explore feature relationships", "recommended": not has_target},
                {"value": "quality", "label": "Deep data quality investigation"},
                {"value": "segments", "label": "Find natural segments / clusters"},
                {"value": "comprehensive", "label": "Comprehensive analysis (all of the above)"},
            ],
            "recommendation_reason": (
                "Analysing target drivers is most actionable when a target is defined."
                if has_target
                else "Exploring relationships helps surface patterns in unsupervised settings."
            ),
        },
        {
            "id": "eda_charts",
            "question": "Which visualisations would you like?",
            "type": "multi_select",
            "options": [
                {"value": "distributions", "label": "Distribution plots", "recommended": True},
                {"value": "correlations", "label": "Correlation heatmap", "recommended": len(numeric_cols) > 1},
                {"value": "boxplots", "label": "Box plots (outlier detection)", "recommended": True},
                {"value": "scatter_matrix", "label": "Scatter matrix"},
                {"value": "missing_heatmap", "label": "Missing-value heatmap"},
                {"value": "target_analysis", "label": "Target variable analysis", "recommended": has_target},
            ],
            "recommendation_reason": "Distributions and box plots are the most informative starting point.",
        },
        {
            "id": "eda_stat_tests",
            "question": "Which statistical tests should be run?",
            "type": "multi_select",
            "options": [
                {"value": "normality", "label": "Normality tests (Shapiro-Wilk)", "recommended": True},
                {"value": "correlation_test", "label": "Correlation significance tests", "recommended": True},
                {"value": "group_comparison", "label": "Group comparison tests (t-test / ANOVA)"},
                {"value": "chi_square", "label": "Chi-square independence tests"},
                {"value": "multicollinearity", "label": "VIF / multicollinearity check"},
            ],
            "recommendation_reason": "Normality and correlation tests guide later modelling decisions.",
        },
    ]
    return questions


def _render_charts() -> None:
    """Display EDA charts stored in session state."""
    from dashboard.components.chart_container import render_chart

    charts: list[dict[str, Any]] = st.session_state.get("eda_charts", [])
    if not charts:
        return

    st.subheader("Visualisations")
    for i, chart_spec in enumerate(charts):
        fig = chart_spec.get("figure")
        title = chart_spec.get("title", f"Chart {i + 1}")
        if fig is not None:
            render_chart(fig, title=title, key=f"eda_chart_{i}")


def _render_insights() -> None:
    """Show bullet-point insights from EDA."""
    insights: list[str] = st.session_state.get("eda_insights", [])
    if not insights:
        return

    st.subheader("Key Insights")
    for insight in insights:
        st.markdown(f"- {insight}")


def _render_stat_results() -> None:
    """Show statistical test results in expandable tables."""
    results: dict[str, Any] = st.session_state.get("eda_results", {})
    if not results:
        return

    st.subheader("Statistical Test Results")
    for test_name, result in results.items():
        with st.expander(test_name.replace("_", " ").title()):
            if isinstance(result, dict):
                rows = [{"Statistic": k, "Value": str(v)} for k, v in result.items()]
                st.table(rows)
            elif isinstance(result, pd.DataFrame):
                st.dataframe(result, use_container_width=True)
            else:
                st.write(result)


def _render_auto_placeholder() -> None:
    """Placeholder for auto-mode where analyses run without user input."""
    mode = st.session_state.get("user_mode", MODE_GUIDED)
    submitted = st.session_state.get("eda_analyses_submitted", False)

    if mode == MODE_AUTO or submitted:
        has_results = bool(st.session_state.get("eda_results")) or bool(st.session_state.get("eda_charts"))
        if not has_results:
            st.info(
                "Analyses are ready to execute. Connect the EDA agent to see "
                "live results here. In the meantime, the pipeline will populate "
                "charts, insights, and statistical tests in this section."
            )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Exploratory Data Analysis")
    _render_progress()

    # Summary at top
    _render_summary()

    # Quality metrics
    _render_quality_metrics()

    st.divider()

    # Questions (Guided / Expert) or auto notice
    _render_questions()

    st.divider()

    # Results sections
    _render_auto_placeholder()
    _render_charts()
    _render_insights()
    _render_stat_results()

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Configure", use_container_width=True):
            st.switch_page("pages/02_configure.py")
    with col_next:
        if st.button("Proceed to Feature Engineering", type="primary", use_container_width=True):
            st.switch_page("pages/04_feature_engineering.py")


_page()
