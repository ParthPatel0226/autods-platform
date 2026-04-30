# Spec 07 — Page Integration & Pipeline Wiring

## Goal

Replace `dashboard/pages/02_configure.py` with a new orchestrator that uses all components from specs 01–06 in a two-column layout.

## File: `dashboard/pages/02_configure.py` (full rewrite)

```python
"""Configure tab — domain confirmation, mode selection, problem type,
target & goal, excluded columns, and live analysis plan summary."""
from __future__ import annotations
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

from dashboard.components.cf_dataset_recap import render as render_recap
from dashboard.components.cf_domain_cards import render as render_domain_cards
from dashboard.components.cf_domain_why import render as render_why
from dashboard.components.cf_compliance_notice import render as render_compliance
from dashboard.components.cf_mode_cards import render as render_mode_cards
from dashboard.components.cf_unsure_helper import render as render_unsure
from dashboard.components.cf_problem_pills import render as render_problem_pills
from dashboard.components.cf_target_goal import render as render_target_goal
from dashboard.components.cf_excluded_columns import render as render_excluded
from dashboard.components.cf_summary_panel import render as render_summary

from domains.domain_registry import DOMAIN_REGISTRY


st.set_page_config(
    page_title="AutoDS — Configure",
    page_icon="⚙️",
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


# ---- topbar ----
top_cols = st.columns([8, 1])
with top_cols[0]:
    st.markdown(
        f'<div class="cf-crumbs">'
        f'  <span>{project.name}</span>'
        f'  <span class="sep">/</span>'
        f'  <span class="cur">Configure</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ---- hero ----
st.markdown(
    '<section class="cf-hero">'
    '  <div class="cf-hero-eyebrow">⚙ Step 2 of 7 — Configure</div>'
    '  <h1>Tell AutoDS how to <em>analyze your data.</em></h1>'
    '  <p>Confirm the detected domain, choose how much control you want, pick a target — '
    '     and we\'ll build the rest of the pipeline around your decisions.</p>'
    '</section>',
    unsafe_allow_html=True,
)

# ---- recap strip (read-only) ----
render_recap()


# ---- detect / re-use domain detection from upload step ----
detected_domain = project.detected_domain or "generic"
detected_problem = _infer_problem_type(df, project, detected_domain)

# Initialize state
st.session_state.setdefault("cf_selected_domain", detected_domain)
st.session_state.setdefault("cf_mode", project.analysis_mode or "guided")
st.session_state.setdefault("cf_problem_type", project.problem_type or detected_problem)
st.session_state.setdefault("cf_target", project.target_column or "")


# ---- Two-column layout ----
left, right = st.columns([1.0, 0.42], gap="large")

with left:
    # ===== Section 01 — Domain =====
    st.markdown(
        '<section class="cf-section">'
        '<div class="cf-sec-header">'
        '  <span class="cf-sec-num">01</span>'
        '  <h2 class="cf-sec-title">Confirm the <em>domain</em></h2>'
        '</div>'
        f'<p class="cf-sec-sub">We auto-detected this dataset as '
        f'<strong>{DOMAIN_REGISTRY.get(detected_domain, {}).get("display_name", detected_domain.title())}</strong>. '
        f'Override if you disagree.</p>',
        unsafe_allow_html=True,
    )

    selected_domain = render_domain_cards(detected_domain, on_select=lambda k: None)
    render_why(selected_domain, df)
    render_compliance(selected_domain)
    st.markdown('</section>', unsafe_allow_html=True)


    # ===== Section 02 — Analysis mode =====
    st.markdown(
        '<section class="cf-section">'
        '<div class="cf-sec-header">'
        '  <span class="cf-sec-num">02</span>'
        '  <h2 class="cf-sec-title">Pick your <em>analysis mode</em></h2>'
        '</div>'
        '<p class="cf-sec-sub">How much control do you want over the pipeline?</p>',
        unsafe_allow_html=True,
    )
    selected_mode = render_mode_cards()
    render_unsure(df)  # only renders body when mode == "auto"
    st.markdown('</section>', unsafe_allow_html=True)


    # ===== Section 03 — Problem type =====
    st.markdown(
        '<section class="cf-section">'
        '<div class="cf-sec-header">'
        '  <span class="cf-sec-num">03</span>'
        '  <h2 class="cf-sec-title">Confirm the <em>problem type</em></h2>'
        '</div>'
        '<p class="cf-sec-sub">We\'ve inferred this from your target column. Override if needed.</p>',
        unsafe_allow_html=True,
    )
    problem = render_problem_pills(detected_problem)
    st.markdown('</section>', unsafe_allow_html=True)


    # ===== Section 04 — Target & goal =====
    st.markdown(
        '<section class="cf-section">'
        '<div class="cf-sec-header">'
        '  <span class="cf-sec-num">04</span>'
        '  <h2 class="cf-sec-title">Set <em>target & goal</em></h2>'
        '</div>'
        '<p class="cf-sec-sub">Tell us what you want to predict and what success looks like.</p>',
        unsafe_allow_html=True,
    )
    target, goal = render_target_goal(df, problem, selected_domain)
    st.markdown('</section>', unsafe_allow_html=True)


    # ===== Section 05 — Excluded columns =====
    st.markdown(
        '<section class="cf-section">'
        '<div class="cf-sec-header">'
        '  <span class="cf-sec-num">05</span>'
        '  <h2 class="cf-sec-title">Exclude <em>columns</em>'
        '    <span style="font-family: var(--font-body); font-size: 14px; color: var(--text-muted); font-weight: 400; font-style: normal;"> (optional)</span>'
        '  </h2>'
        '</div>'
        '<p class="cf-sec-sub">Skip columns that would leak the target, contain PII, or aren\'t useful.</p>',
        unsafe_allow_html=True,
    )
    excluded = render_excluded(df, target, selected_domain)
    st.markdown('</section>', unsafe_allow_html=True)


with right:
    render_summary(df, on_start=_handle_start_analysis)


# ---------------------------------------------------------- helpers


def _infer_problem_type(df, project, domain) -> str:
    """Reuse orchestrator's problem-type inference if available, else heuristic."""
    if project.problem_type:
        return project.problem_type
    try:
        from agents.orchestrator import infer_problem_type
        return infer_problem_type(df, domain=domain)
    except Exception:
        # Fallback heuristic
        return "auto"


def _handle_start_analysis(payload: dict) -> None:
    """Persist all selections to project, advance step status, route to EDA."""
    p = project_service.get_active()
    if not p:
        return

    p.confirmed_domain = payload["domain"]
    p.analysis_mode = payload["mode"]
    p.problem_type = payload["problem_type"]
    p.target_column = payload["target"]
    p.excluded_columns = payload["excluded_columns"]
    p.goal = payload["goal"]

    p.step_status["configure"] = "done"
    p.step_status["eda"] = "active"
    project_service.update(p)

    # Mirror to session_state for downstream pages that read raw keys
    st.session_state["domain"] = payload["domain"]
    st.session_state["analysis_mode"] = payload["mode"]
    st.session_state["problem_type"] = payload["problem_type"]
    st.session_state["target_column"] = payload["target"]
    st.session_state["analysis_goal"] = payload["goal"]
    st.session_state["excluded_columns"] = payload["excluded_columns"]

    st.switch_page("pages/03_eda_interactive.py")
```

## `project_service.py` — add config field setters

Append to `dashboard/components/project_service.py`'s `Project` dataclass:

```python
@dataclass
class Project:
    # ... existing fields ...
    excluded_columns: list[str] = field(default_factory=list)
    goal: Optional[str] = None
```

These persist across resume. The downstream pages should read from the project record OR from `session_state` — the integration above writes both for backward compatibility.

## Pipeline state flow

| When | What is written |
|---|---|
| User selects a domain card | `cf_selected_domain` in session_state (mirrored to summary) |
| User picks a mode card | `cf_mode` in session_state |
| User clicks an unsure quick-goal chip | `cf_target`, `cf_problem_type`, `cf_goal` in session_state |
| User picks problem-type pill | `cf_problem_type` |
| User picks target | `cf_target` |
| User picks goal template / types manually | `cf_goal` / `cf_goal_manual` |
| User toggles a column exclusion | `cf_excluded` (set) |
| User clicks Start Analysis | `project.confirmed_domain`, `analysis_mode`, `problem_type`, `target_column`, `excluded_columns`, `goal`, `step_status[configure]=done`, `step_status[eda]=active` |

## Test plan

1. **Smoke test:** existing project at upload step → click Continue to Configure → see all 5 sections + sticky summary on the right. Click Start Analysis → land on EDA page, sidebar shows Configure ✅, EDA ⏳ pulsing.

2. **Domain test:** click each of the 7 domain cards → summary updates. Click "Why [domain]?" → expander shows top 3 signals. Switch to Healthcare/Finance/HR → compliance notice appears. Switch to Generic/Marketing/Manufacturing → notice disappears.

3. **Auto unsure test:** click Auto mode → unsure block appears. Click "Predict something specific" → target dropdown auto-selects a boolean column, problem pills jump to Classification, goal field fills in. Click "Find natural groups" → target clears, problem jumps to Clustering. Switch to Guided → unsure block hides.

4. **Problem-type test:** click between pills → summary updates. Goal templates change to match the problem type.

5. **Target test:** for sensitive domains, PHI-flagged columns hidden; helper text below dropdown updates per dtype.

6. **Excluded columns test:** suggestions pre-checked with reasons (PII / ID / CONST). Click any column to toggle. Click "Clear all suggestions" to wipe. Footer count updates live. Target column shown as disabled with TARGET tag.

7. **Estimate test:** changing mode (Auto → Expert) increases model count and runtime. Excluding columns reduces chart count. Switching to Healthcare adds ~15% to LLM cost.

8. **Validation test:** with classification + no target → Start button disabled, blocker message shown. Pick a target → button enabled.

9. **Resume test:** complete configure, return to home, click project → routes to EDA. Click back to Configure → all selections restored from project record (domain, mode, problem, target, goal, excluded).

10. **Theme test:** swap to light → all elements render correctly. Provider tiles, mode cards, problem pills, excluded columns grid, summary panel, estimate block — none should leak hardcoded dark colors.

11. **Regression:** `pytest tests/` passes at the existing baseline.

## Final reminder

Do NOT modify:
- `agents/**`, `domains/**`, `core/**`, `data_connectors/**`
- Any other dashboard page (00, 01, 03–09, app.py)
- `mode_selector.py`, `domain_badge.py` etc. (legacy components stay in place)

Verify before changing:
- `domain_registry.detect_domain` shape (spec 02 fallback to local signal-scoring if it doesn't return signals)
- `agents.orchestrator.infer_problem_type` (spec 07 has a try/except fallback)

If those interfaces don't match, write a thin adapter (e.g., `dashboard/components/cf_domain_adapter.py`) — never modify the backend module.
