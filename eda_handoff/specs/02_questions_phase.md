# Spec 02 — Questions Phase

## Goal

Phase 1 renders a stack of numbered question cards (general + domain-specific labeled with a domain pill), with single-select / multi-select widgets, optional inline tips, and an optional free-text "anything else?" input per question. Sticky bottom action bar shows answered count + estimated runtime + **Run Analysis** button.

## Backend reuse

`agents.eda_agent` exposes question generation. **Open `agents/eda_agent.py` first** to confirm the actual API. Expected interface (adapt if names differ):

```python
# agents/eda_agent.py
def generate_questions(state: dict) -> list[dict]:
    """Returns a list of question dicts, each with:
    {
      "id": str,                       # unique id (e.g., "eda_q1_analysis_goal")
      "step": "eda",
      "question": str,                 # the question text
      "type": Literal["single_select", "multi_select", "slider", "text_input", "number_input", "per_column_table"],
      "options": list[{"value": str, "label": str, "recommended": bool}],
      "recommendation_reason": str,    # optional inline tip
      "domain_specific": bool,         # True if from domain config's eda_questions
    }
    """
```

If the existing function is named differently, **wrap it** in a thin adapter — do not modify the agent.

## File: `dashboard/components/ed_question_card.py`

```python
"""Single numbered question card with options + optional follow-up input."""
from __future__ import annotations
import streamlit as st


def render(question: dict, index: int, domain_label: str, answered: bool) -> dict:
    """Render one question card. Returns the user's answer dict.

    Args:
        question: question spec from agents.eda_agent.generate_questions
        index: 1-based question number
        domain_label: e.g., "🏥 Healthcare" or "" for general
        answered: True if the user has interacted with this question

    Returns:
        {"id": question_id, "value": <answer>, "followup": <free-text>}
    """
    q_id = question["id"]
    q_type = question.get("type", "single_select")
    is_domain = bool(question.get("domain_specific"))

    classes = ["ed-q-card"]
    if answered:
        classes.append("ed-q-answered")

    # ---- header ----
    domain_pill_html = (
        f'<span class="ed-domain-pill ed-domain-{_pill_class(domain_label)}">{domain_label}</span>'
        if is_domain and domain_label
        else '<span class="ed-domain-pill ed-domain-general">General</span>'
    )

    num_inner = "✓" if answered else f'<span>{index:02d}</span>'

    st.markdown(
        f'<div class="{" ".join(classes)}">'
        f'  <div class="ed-q-head">'
        f'    <div class="ed-q-num">{num_inner}</div>'
        f'    <div style="flex:1;">'
        f'      <div class="ed-q-meta">{domain_pill_html}</div>'
        f'      <div class="ed-q-title">{_html_escape(question["question"])}</div>'
        f'    </div>'
        f'  </div>',
        unsafe_allow_html=True,
    )

    # Optional tip
    if question.get("recommendation_reason"):
        st.markdown(
            f'<div class="ed-q-tip">'
            f'  <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="2" x2="12" y2="6"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="18" x2="12" y2="22"/></svg>'
            f'  {_html_escape(question["recommendation_reason"])}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---- options ----
    answer_value = None
    if q_type == "single_select":
        answer_value = _render_single_select(question, q_id)
    elif q_type == "multi_select":
        answer_value = _render_multi_select(question, q_id)
    else:
        # Fallback: render as Streamlit native widget
        answer_value = st.text_input("Your answer", key=f"ed_ans_{q_id}",
                                     label_visibility="collapsed")

    # ---- optional follow-up text input ----
    followup = ""
    if question.get("allow_followup", q_type == "multi_select"):
        st.markdown(
            '<div class="ed-q-followup">'
            '  <label>Anything else? Add a custom request:</label>'
            '</div>',
            unsafe_allow_html=True,
        )
        followup = st.text_input(
            "Custom follow-up", key=f"ed_followup_{q_id}",
            placeholder="e.g., distribution of length_of_stay split by gender",
            label_visibility="collapsed",
        )

    st.markdown('</div>', unsafe_allow_html=True)

    return {"id": q_id, "value": answer_value, "followup": followup}


def _render_single_select(question: dict, q_id: str) -> str:
    options = question.get("options", [])
    selected = st.session_state.get(f"ed_ans_{q_id}", _default_value(options))

    st.markdown('<div class="ed-options">', unsafe_allow_html=True)
    for opt in options:
        val = opt["value"]
        is_sel = val == selected
        rec_html = '<div class="ed-option-rec">★ Recommended</div>' if opt.get("recommended") else ""
        st.markdown(
            f'<div class="ed-option{" ed-option-selected" if is_sel else ""}">'
            f'  <div class="ed-option-radio"></div>'
            f'  <div class="ed-option-label">{_html_escape(opt["label"])}</div>'
            f'  {rec_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(opt["label"], key=f"ed_opt_{q_id}_{val}",
                     use_container_width=True, label_visibility="collapsed"):
            st.session_state[f"ed_ans_{q_id}"] = val
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    return selected


def _render_multi_select(question: dict, q_id: str) -> list[str]:
    options = question.get("options", [])
    state_key = f"ed_ans_{q_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = [o["value"] for o in options if o.get("recommended")]
    selected = st.session_state[state_key]

    st.markdown('<div class="ed-options">', unsafe_allow_html=True)
    for opt in options:
        val = opt["value"]
        is_sel = val in selected
        rec_html = '<div class="ed-option-rec">★ Recommended</div>' if opt.get("recommended") else ""
        st.markdown(
            f'<div class="ed-option{" ed-option-selected" if is_sel else ""}">'
            f'  <div class="ed-option-checkbox"></div>'
            f'  <div class="ed-option-label">{_html_escape(opt["label"])}</div>'
            f'  {rec_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(opt["label"], key=f"ed_opt_{q_id}_{val}",
                     use_container_width=True, label_visibility="collapsed"):
            cur = st.session_state[state_key]
            st.session_state[state_key] = [v for v in cur if v != val] if val in cur else [*cur, val]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    return selected


def _default_value(options: list[dict]) -> str:
    for o in options:
        if o.get("recommended"):
            return o["value"]
    return options[0]["value"] if options else ""


def _pill_class(label: str) -> str:
    """Map domain pill labels to CSS class suffixes."""
    label_lower = (label or "").lower()
    for key in ("healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing"):
        if key in label_lower:
            return key
    return "general"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ed_questions_panel.py`

```python
"""Stack of question cards + sticky bottom Run Analysis bar."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service
from dashboard.components.ed_question_card import render as render_card
from domains.domain_registry import DOMAIN_REGISTRY


def render(on_run) -> None:
    """Render the questions phase. on_run(answers) is called when Run Analysis is clicked."""
    project = project_service.get_active()
    if not project:
        return

    domain = project.confirmed_domain or project.detected_domain or "generic"
    mode = project.analysis_mode or "guided"

    domain_cfg = DOMAIN_REGISTRY.get(domain, {})
    domain_label = f'{domain_cfg.get("icon", "📊")} {domain_cfg.get("display_name", domain.title())}'

    # Mode pill
    st.markdown(
        f'<div class="ed-mode-pill">'
        f'  <span class="dot"></span>'
        f'  {mode.title()} Mode · {domain_cfg.get("display_name", domain.title())} context'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Get questions from agent
    questions = _get_questions(project)

    answers = []
    for i, q in enumerate(questions, start=1):
        q_label = domain_label if q.get("domain_specific") else "General"
        ans_key = f"ed_ans_{q['id']}"
        already_answered = ans_key in st.session_state and bool(st.session_state[ans_key])
        answer = render_card(q, i, q_label, answered=already_answered)
        answers.append(answer)

    # Sticky bottom action bar
    n_total = len(questions)
    n_answered = sum(1 for a in answers if _is_answered(a))
    runtime_estimate = _estimate_runtime(answers, project)

    cols = st.columns([3, 1], gap="medium")
    with cols[0]:
        st.markdown(
            f'<div class="ed-actionbar-text">'
            f'  <strong>{n_answered} / {n_total}</strong> questions answered · '
            f'  Estimated runtime: <strong>{runtime_estimate}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        if st.button("Run Analysis ▶", key="ed_run_btn", type="primary", use_container_width=True):
            on_run(answers)


def _get_questions(project) -> list[dict]:
    """Fetch questions from the EDA agent for the active project."""
    try:
        from agents.eda_agent import generate_questions
        # The actual function may take a state dict — adapt as needed
        state = {
            "df_ref": "main",  # actual df_ref name from session state
            "domain": project.confirmed_domain or project.detected_domain,
            "target_column": project.target_column,
            "problem_type": project.problem_type,
            "analysis_mode": project.analysis_mode,
            "goal": project.goal,
        }
        return generate_questions(state)
    except Exception as e:
        # Fallback to a sensible default question set if the agent call fails
        st.warning(f"Could not generate domain-aware questions: {e}. Using defaults.")
        return _default_questions()


def _default_questions() -> list[dict]:
    return [
        {
            "id": "eda_q1_goal",
            "type": "single_select",
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
            "id": "eda_q2_viz",
            "type": "multi_select",
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
            "id": "eda_q3_stats",
            "type": "multi_select",
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


def _estimate_runtime(answers: list[dict], project) -> str:
    """Heuristic runtime based on number of answers selected."""
    total_choices = 0
    for a in answers:
        v = a.get("value")
        if isinstance(v, list):
            total_choices += len(v)
        elif v:
            total_choices += 1
    seconds = max(45, total_choices * 12 + 30)
    if project.analysis_mode == "expert":
        seconds += 60
    m, s = divmod(seconds, 60)
    return f"~{m} min {s}s" if m else f"~{s}s"
```

## CSS additions

```css
/* ============ Mode pill ============ */
.ed-mode-pill {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 5px 14px 5px 10px;
  background: rgba(139,92,246,0.1);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-family: var(--font-mono); font-size: 11px;
  color: var(--violet); letter-spacing: 0.6px;
  text-transform: uppercase; margin-bottom: 22px;
}
.ed-mode-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); }

/* ============ Question cards ============ */
.ed-q-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 26px 28px; margin-bottom: 20px;
  backdrop-filter: blur(14px); transition: all 0.22s ease;
  position: relative; overflow: hidden;
}
.ed-q-card:hover { border-color: var(--border-strong); }
.ed-q-answered::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--green); box-shadow: 0 0 14px rgba(52,211,153,0.5);
}
.ed-q-head { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 6px; }
.ed-q-num {
  width: 32px; height: 32px; flex-shrink: 0;
  border-radius: 50%; display: grid; place-items: center;
  background: rgba(139,92,246,0.12);
  border: 1px solid var(--border-default);
  color: var(--violet);
  font-family: var(--font-mono); font-size: 13px; font-weight: 600;
}
.ed-q-answered .ed-q-num {
  background: var(--green); border-color: var(--green); color: white;
  font-size: 16px;
}
.ed-q-meta {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px;
}
.ed-domain-pill {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 3px 10px; border-radius: 999px;
  letter-spacing: 0.6px; text-transform: uppercase;
}
.ed-domain-general { color: var(--text-muted); background: rgba(139,92,246,0.06); border: 1px solid var(--border-subtle); }
.ed-domain-healthcare { color: var(--green); background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.ed-domain-finance    { color: var(--cyan);  background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.3); }
.ed-domain-ecommerce  { color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.ed-domain-hr         { color: var(--pink);  background: rgba(236,72,153,0.1); border: 1px solid rgba(236,72,153,0.3); }
.ed-domain-marketing  { color: var(--pink);  background: rgba(236,72,153,0.1); border: 1px solid rgba(236,72,153,0.3); }
.ed-domain-manufacturing { color: var(--violet); background: rgba(139,92,246,0.1); border: 1px solid var(--border-default); }

.ed-q-title {
  font-family: var(--font-display); font-size: 22px;
  line-height: 1.25; color: var(--text-primary);
}
.ed-q-tip {
  display: flex; align-items: flex-start; gap: 10px;
  margin: 14px 0 18px;
  padding: 10px 14px;
  background: rgba(251,191,36,0.06);
  border: 1px solid rgba(251,191,36,0.2); border-radius: 10px;
  font-size: 12.5px; color: var(--text-secondary); font-style: italic;
}
.ed-q-tip svg { width: 14px; height: 14px; color: var(--amber); flex-shrink: 0; margin-top: 2px; }

/* Options */
.ed-options { display: flex; flex-direction: column; gap: 8px; }
.ed-option {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px;
  background: rgba(7,9,26,0.3);
  border: 1px solid var(--border-subtle); border-radius: 10px;
  cursor: pointer; transition: all 0.15s ease;
}
[data-theme="light"] .ed-option { background: rgba(255,255,255,0.5); }
.ed-option:hover { background: rgba(139,92,246,0.06); border-color: var(--border-default); }
.ed-option-selected {
  background: rgba(139,92,246,0.14) !important;
  border-color: var(--violet) !important;
  box-shadow: 0 0 14px -4px var(--violet);
}
.ed-option-radio, .ed-option-checkbox {
  width: 18px; height: 18px;
  border: 1.5px solid var(--text-faint);
  display: grid; place-items: center; flex-shrink: 0;
  transition: all 0.15s ease;
}
.ed-option-radio { border-radius: 50%; }
.ed-option-checkbox { border-radius: 5px; }
.ed-option-selected .ed-option-radio { border-color: var(--violet); }
.ed-option-selected .ed-option-radio::after {
  content: ""; width: 9px; height: 9px; border-radius: 50%;
  background: var(--violet); box-shadow: 0 0 8px var(--violet);
}
.ed-option-selected .ed-option-checkbox {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-color: var(--violet);
}
.ed-option-selected .ed-option-checkbox::after {
  content: "✓"; color: white; font-size: 11px; font-weight: 700;
}
.ed-option-label { font-size: 14px; color: var(--text-primary); flex: 1; }
.ed-option-rec {
  display: inline-flex; align-items: center; gap: 4px;
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 2px 8px; background: rgba(168,85,247,0.1);
  border: 1px solid rgba(168,85,247,0.3); border-radius: 999px;
  color: var(--purple); letter-spacing: 0.5px; text-transform: uppercase;
  white-space: nowrap;
}

.ed-q-followup { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border-subtle); }
.ed-q-followup label {
  display: block; font-size: 11.5px; color: var(--text-muted);
  margin-bottom: 6px; font-family: var(--font-mono);
  letter-spacing: 0.5px; text-transform: uppercase;
}

/* Sticky action bar */
.ed-actionbar-text { font-family: var(--font-mono); font-size: 12px; color: var(--text-muted); padding: 12px 0; }
.ed-actionbar-text strong { color: var(--text-primary); }

[data-testid="stMain"] .stButton > button[key="ed_run_btn"] {
  padding: 12px 26px !important;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 12px !important;
  font-size: 14px !important; font-weight: 500 !important;
  box-shadow: 0 0 24px rgba(139,92,246,0.4) !important;
}
[data-testid="stMain"] .stButton > button[key="ed_run_btn"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 32px rgba(139,92,246,0.6) !important;
}
```

## Implementation note

The "render visual card via markdown + sibling Streamlit button to handle click" pattern is reused from previous handoffs. If the absolute-positioning trick is unreliable in the current Streamlit version, the spec falls back to ordinary Streamlit `st.radio` / `st.multiselect` widgets — wrap them in a styled container so the visual identity is preserved.
