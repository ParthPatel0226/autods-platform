"""Page 03 -- Interactive Exploratory Data Analysis.

Displays workflow progress, EDA questions (Guided / Expert), analysis results
with charts and insights, and an AI-generated summary.

Premium dark luxury UI with glass morphism cards and gradient accents.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

_DARK_LUXURY_CSS = """
<style>
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

:root {
    --bg-primary: #0a0a0f;
    --bg-card: #12121a;
    --bg-elevated: #16161f;
    --border-subtle: rgba(99,102,241,0.12);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-primary: #6366f1;
    --accent-secondary: #0ea5e9;
    --accent-success: #22c55e;
    --accent-warning: #f59e0b;
    --gradient-primary: linear-gradient(135deg, #6366f1, #0ea5e9);
    --radius-md: 12px;
    --shadow-card: 0 4px 24px rgba(0,0,0,0.25);
}

.stApp {
    background-color: var(--bg-primary) !important;
}

/* --- Page header with gradient text --- */
.eda-page-header {
    padding: 32px 0 24px 0;
}
.eda-page-header h1 {
    font-size: 2.25rem;
    font-weight: 700;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.02em;
}
.eda-page-header .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 4px;
}

/* --- Section headers --- */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    margin-bottom: 16px;
    padding-bottom: 8px;
    position: relative;
}
.section-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 48px;
    height: 2px;
    background: var(--gradient-primary);
    border-radius: 1px;
}

/* --- Glass card --- */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 16px;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}

/* --- Question card --- */
.question-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 16px;
    position: relative;
}
.question-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}

/* --- Number badge --- */
.number-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: var(--gradient-primary);
    color: #fff;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 12px;
    flex-shrink: 0;
}

.question-title {
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
    display: inline;
    vertical-align: middle;
}

.question-reason {
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-top: 8px;
    padding-left: 40px;
    font-style: italic;
}

/* --- AI summary card --- */
.ai-summary-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--accent-primary);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    margin-bottom: 16px;
}
.ai-summary-card .summary-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent-primary);
    margin-bottom: 8px;
}
.ai-summary-card .summary-text {
    color: var(--text-primary);
    font-size: 0.95rem;
    line-height: 1.65;
}

/* --- Metric card --- */
.metric-glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    text-align: center;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.metric-glass-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}
.metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
}
.metric-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

/* --- Status dots --- */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-dot.success { background-color: var(--accent-success); }
.status-dot.warning { background-color: var(--accent-warning); }
.status-dot.info { background-color: var(--accent-secondary); }

/* --- Chart container --- */
.chart-glass-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    margin-bottom: 16px;
}
.chart-glass-container .chart-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
}

/* --- Insight item --- */
.insight-item {
    color: var(--text-secondary);
    font-size: 0.9rem;
    padding: 8px 0 8px 16px;
    border-left: 2px solid rgba(99,102,241,0.2);
    margin-bottom: 8px;
    line-height: 1.5;
}

/* --- Stat results glass --- */
.stat-result-glass {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px;
    margin-bottom: 8px;
}

/* --- Navigation buttons --- */
.nav-row {
    display: flex;
    gap: 16px;
    padding-top: 24px;
}

/* --- Info placeholder --- */
.info-placeholder {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
}

/* --- Divider override --- */
.eda-divider {
    border: none;
    border-top: 1px solid var(--border-subtle);
    margin: 32px 0;
}

/* --- Streamlit input overrides --- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div {
    background-color: var(--bg-elevated) !important;
    border-color: var(--border-subtle) !important;
    color: var(--text-primary) !important;
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
        st.markdown(
            f"""
            <div class="ai-summary-card">
                <div class="summary-label">AI Analysis Summary</div>
                <div class="summary-text">{summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_quality_metrics() -> None:
    """Show data-quality metric cards in glass style."""
    df: pd.DataFrame = st.session_state["uploaded_data"]
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    completeness = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 1.0
    duplicate_rows = int(df.duplicated().sum())

    st.markdown('<div class="section-header">Data Quality Overview</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    metrics = [
        (f"{completeness:.1%}", "Completeness"),
        (f"{missing_cells:,}", "Missing Cells"),
        (f"{duplicate_rows:,}", "Duplicate Rows"),
        (f"{df.shape[1]:,}", "Columns"),
        (f"{df.shape[0]:,}", "Rows"),
    ]
    for col, (value, label) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-glass-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_questions() -> None:
    """Render EDA questions for Guided / Expert modes."""
    from dashboard.components.question_renderer import render_question_group

    mode = st.session_state.get("user_mode", MODE_GUIDED)
    if mode == MODE_AUTO:
        st.markdown(
            '<div class="info-placeholder">'
            '<span class="status-dot info"></span>'
            'Auto mode -- the system selects analyses automatically.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    questions = st.session_state.get("eda_questions", [])
    if not questions:
        questions = _generate_default_questions()
        st.session_state["eda_questions"] = questions

    st.markdown('<div class="section-header">Analysis Options</div>', unsafe_allow_html=True)

    if mode == MODE_EXPERT:
        st.markdown(
            '<p style="color: var(--text-muted); font-size: 0.8rem;">'
            'Expert mode -- you have full control over every analysis.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color: var(--text-muted); font-size: 0.8rem;">'
            'Guided mode -- AI recommendations are highlighted.</p>',
            unsafe_allow_html=True,
        )

    # Render each question in a glass card with number badge
    for idx, q in enumerate(questions, 1):
        reason = q.get("recommendation_reason", "")
        st.markdown(
            f"""
            <div class="question-card">
                <div>
                    <span class="number-badge">{idx}</span>
                    <span class="question-title">{q.get("question", "")}</span>
                </div>
                {"<div class='question-reason'>" + reason + "</div>" if reason else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

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

    st.markdown('<div class="section-header">Visualisations</div>', unsafe_allow_html=True)
    for i, chart_spec in enumerate(charts):
        fig = chart_spec.get("figure")
        title = chart_spec.get("title", f"Chart {i + 1}")
        if fig is not None:
            st.markdown(
                f"""
                <div class="chart-glass-container">
                    <div class="chart-title">{title}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_chart(fig, title=title, key=f"eda_chart_{i}")


def _render_insights() -> None:
    """Show bullet-point insights from EDA."""
    insights: list[str] = st.session_state.get("eda_insights", [])
    if not insights:
        return

    st.markdown('<div class="section-header">Key Insights</div>', unsafe_allow_html=True)
    for insight in insights:
        st.markdown(
            f'<div class="insight-item">{insight}</div>',
            unsafe_allow_html=True,
        )


def _render_stat_results() -> None:
    """Show statistical test results in expandable tables."""
    results: dict[str, Any] = st.session_state.get("eda_results", {})
    if not results:
        return

    st.markdown('<div class="section-header">Statistical Test Results</div>', unsafe_allow_html=True)
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
            st.markdown(
                """
                <div class="info-placeholder">
                    <span class="status-dot info"></span>
                    Analyses are ready to execute. Connect the EDA agent to see
                    live results here. In the meantime, the pipeline will populate
                    charts, insights, and statistical tests in this section.
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.set_page_config(page_title="Exploratory Analysis", layout="wide") if not hasattr(st, "_is_running_with_streamlit") else None

    # Inject CSS
    st.markdown(_DARK_LUXURY_CSS, unsafe_allow_html=True)

    # Page header
    st.markdown(
        """
        <div class="eda-page-header">
            <h1>Exploratory Analysis</h1>
            <div class="subtitle">Interactive data exploration with AI-powered insights</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_progress()

    # Summary at top
    _render_summary()

    # Quality metrics
    _render_quality_metrics()

    st.markdown('<hr class="eda-divider">', unsafe_allow_html=True)

    # Questions (Guided / Expert) or auto notice
    _render_questions()

    st.markdown('<hr class="eda-divider">', unsafe_allow_html=True)

    # Results sections
    _render_auto_placeholder()
    _render_charts()
    _render_insights()
    _render_stat_results()

    # Navigation
    st.markdown('<hr class="eda-divider">', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Configure", use_container_width=True):
            st.switch_page("pages/02_configure.py")
    with col_next:
        if st.button("Proceed to Feature Engineering", type="primary", use_container_width=True):
            st.switch_page("pages/04_feature_engineering.py")


_page()
