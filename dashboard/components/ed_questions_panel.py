"""Stack of question cards + sticky bottom Run Analysis bar."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service
from dashboard.components.ed_question_card import render as render_card
from domains.domain_registry import DOMAIN_REGISTRY


def render(on_run) -> None:
    project = project_service.get_active()
    if not project:
        return
    domain = project.confirmed_domain or project.detected_domain or "generic"
    mode = project.analysis_mode or "guided"
    domain_cfg = DOMAIN_REGISTRY.get(domain, {})
    domain_label = f"{domain_cfg.get('icon', '📊')} {domain_cfg.get('display_name', domain.title())}"
    st.markdown(
        f"<div class='ed-mode-pill'><span class='dot'></span>{mode.title()} Mode · {domain_cfg.get('display_name', domain.title())} context</div>",
        unsafe_allow_html=True,
    )
    questions = _get_questions(project)
    answers = []
    for i, q in enumerate(questions, start=1):
        q_label = domain_label if q.get("domain_specific") else "General"
        ans_key = f"ed_ans_{q['id']}"
        already_answered = ans_key in st.session_state and bool(st.session_state[ans_key])
        answer = render_card(q, i, q_label, answered=already_answered)
        answers.append(answer)
    n_total = len(questions)
    n_answered = sum(1 for a in answers if _is_answered(a))
    runtime_estimate = _estimate_runtime(answers, project)
    cols = st.columns([3, 1], gap="medium")
    with cols[0]:
        st.markdown(
            f"<div class='ed-actionbar-text'><strong>{n_answered} / {n_total}</strong> questions answered · Estimated runtime: <strong>{runtime_estimate}</strong></div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        if st.button("Run Analysis ▶", key="ed_run_btn", type="primary", use_container_width=True):
            on_run(answers)


def _get_questions(project) -> list:
    try:
        from agents.eda_agent import generate_questions
        state = {
            "df_ref": "main",
            "domain": project.confirmed_domain or project.detected_domain,
            "target_column": project.target_column,
            "problem_type": project.problem_type,
            "analysis_mode": project.analysis_mode,
            "goal": project.goal,
        }
        return generate_questions(state)
    except Exception as e:
        st.warning(f"Could not generate domain-aware questions: {e}. Using defaults.")
        return _default_questions()


def _default_questions() -> list:
    return [
        {
            "id": "eda_q1_goal", "type": "single_select",
            "question": "What is your primary analysis goal?",
            "domain_specific": False,
            "recommendation_reason": "Since you have a clear target variable, understanding its drivers is most actionable.",
            "options": [
                {"value": "drivers", "label": "Understand what drives the target", "recommended": True},
                {"value": "relationships", "label": "Explore feature relationships"},
                {"value": "quality", "label": "Deep data quality investigation"},
                {"value": "segments", "label": "Find natural segments / clusters"},
                {"value": "comprehensive", "label": "Comprehensive analysis (all of the above)"},
            ],
        },
        {
            "id": "eda_q2_viz", "type": "multi_select",
            "question": "Which visualizations would you like?",
            "domain_specific": False,
            "recommendation_reason": "Distributions and box plots are the most informative starting point.",
            "options": [
                {"value": "dist", "label": "Distribution plots", "recommended": True},
                {"value": "corr", "label": "Correlation heatmap", "recommended": True},
                {"value": "box", "label": "Box plots (outlier detection)", "recommended": True},
                {"value": "scatter", "label": "Scatter matrix"},
                {"value": "missing", "label": "Missing-value heatmap"},
                {"value": "target", "label": "Target variable analysis", "recommended": True},
            ],
        },
        {
            "id": "eda_q3_stats", "type": "multi_select",
            "question": "Which statistical tests should be run?",
            "domain_specific": False,
            "recommendation_reason": "Normality and correlation tests guide later modeling decisions.",
            "options": [
                {"value": "ttest", "label": "Independent t-tests (binary group differences)", "recommended": True},
                {"value": "anova", "label": "ANOVA (multi-group comparisons)", "recommended": True},
                {"value": "chi2", "label": "Chi-square (categorical associations)", "recommended": True},
                {"value": "mw", "label": "Mann-Whitney U (non-parametric)"},
                {"value": "shapiro", "label": "Shapiro-Wilk normality"},
                {"value": "vif", "label": "VIF / multicollinearity"},
            ],
        },
    ]


def _is_answered(answer: dict) -> bool:
    val = answer.get("value")
    if isinstance(val, list):
        return len(val) > 0
    return bool(val)


def _estimate_runtime(answers: list, project) -> str:
    total_choices = 0
    for a in answers:
        v = a.get("value")
        if isinstance(v, list):
            total_choices += len(v)
        elif v:
            total_choices += 1
    seconds = max(45, total_choices * 12 + 30)
    if getattr(project, "analysis_mode", None) == "expert":
        seconds += 60
    m, s = divmod(seconds, 60)
    return f"~{m} min {s}s" if m else f"~{s}s"
