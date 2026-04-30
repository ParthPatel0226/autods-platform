# Spec 07 — Page Integration & Pipeline Wiring

## Goal

Replace `dashboard/pages/03_eda_interactive.py` with a new orchestrator that uses all components from specs 01–06.

## File: `dashboard/pages/03_eda_interactive.py` (full rewrite)

```python
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

# Set initial phase based on whether results exist
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


# ---- hero (per phase) ----
if current_phase == "questions":
    title_html = 'Configure your <em>analysis questions.</em>'
    subtitle = "Pick the goals, visualizations, and statistical tests you want. AutoDS will run them all in one go and show you the results."
else:
    title_html = 'Your <em>EDA results.</em>'
    n_insights = len(st.session_state.get("eda_insights", []))
    n_charts = len(st.session_state.get("eda_charts", []))
    n_stats = len(st.session_state.get("eda_stats", []))
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
    """Triggered when user clicks Run Analysis in the Questions phase."""
    _execute_eda_run({"answers": answers})


def _run_analysis_from_auto(spec: dict) -> None:
    """Triggered when user clicks Run Analysis in Auto mode."""
    _execute_eda_run({"auto_spec": spec})


def _execute_eda_run(payload: dict) -> None:
    """Wrapper around the eda_agent run that updates state, project, and pipeline status."""
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

            # Hydrate session_state with each results bucket
            st.session_state["eda_results"] = results
            st.session_state["eda_charts"] = results.get("charts", [])
            st.session_state["eda_stats"] = results.get("stats", [])
            st.session_state["eda_insights"] = results.get("insights", [])
            st.session_state["eda_quality_flags"] = results.get("quality_flags", {})

            # Track runtime/cost for the action bar
            elapsed = int(time.time() - started)
            m, s = divmod(elapsed, 60)
            st.session_state["ed_run_runtime_str"] = f"{m} min {s:02d} s" if m else f"{s} s"
            st.session_state["ed_run_cost_str"] = results.get("llm_cost_str", "—")

        except Exception as e:
            st.error(f"Analysis failed: {e}. Check that the EDA agent is configured.")
            return

    # Update project status and switch to results
    p.step_status["eda"] = "done"
    p.step_status["features"] = "active"
    project_service.update(p)
    set_phase("results")
    st.rerun()


def _handle_followup(prompt: str) -> None:
    """Triggered when user submits a follow-up via chat composer."""
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

        # Prepend new outputs to the existing buckets so they show up at the top
        if "charts" in new_outputs:
            st.session_state["eda_charts"] = new_outputs["charts"] + st.session_state.get("eda_charts", [])
        if "stats" in new_outputs:
            st.session_state["eda_stats"] = new_outputs["stats"] + st.session_state.get("eda_stats", [])
        if "insights" in new_outputs:
            st.session_state["eda_insights"] = new_outputs["insights"] + st.session_state.get("eda_insights", [])

    except (ImportError, AttributeError):
        # If add_followup_analysis doesn't exist yet, fall back to followup_agent
        try:
            from agents.followup_agent import handle as followup_handle
            followup_handle(prompt, st.session_state.get("eda_results", {}))
            st.success(f"Added: {prompt}")
        except Exception as e:
            st.warning(f"Follow-up not yet wired: {e}")
    except Exception as e:
        st.error(f"Follow-up failed: {e}")


def _handle_continue() -> None:
    """User clicked Continue to Features."""
    st.switch_page("pages/04_feature_engineering.py")


def _handle_reconfigure() -> None:
    """User clicked Reconfigure questions."""
    set_phase("questions")
    st.rerun()


def _handle_export() -> None:
    """User clicked Export EDA report — delegate to report_agent if available."""
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
    # Phase 2: Results dashboard
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
```

## `project_service.py` — add EDA state persistence

Append to the `Project` dataclass:

```python
@dataclass
class Project:
    # ... existing fields ...
    eda_completed: bool = False
    eda_summary: Optional[str] = None  # short text summary for the project card
```

Update `_handle_continue` in the page (or in the EDA run callback) to set `eda_completed = True` and stash a one-line summary like "5 insights · 28 charts · 14 tests".

## Pipeline state flow

| When | What is written |
|---|---|
| User answers question / picks recommendation | `ed_ans_<question_id>` in session_state |
| User clicks Run Analysis | `eda_results`, `eda_charts`, `eda_stats`, `eda_insights`, `eda_quality_flags`, `ed_run_runtime_str`, `ed_run_cost_str` in session_state · `project.step_status["eda"]="done"`, `step_status["features"]="active"` · phase set to "results" |
| User submits chat composer follow-up | New entries prepended to `eda_charts` / `eda_stats` / `eda_insights` |
| User changes filter | `ed_filter_types`, `ed_filter_significance`, `ed_filter_column_kind` in session_state |
| User clicks Reconfigure | phase set to "questions"; answer state preserved |
| User clicks Continue to Features | route to `04_feature_engineering.py` |

## Test plan

1. **Smoke test:** Configure (Guided mode) → EDA → see Phase 1 Questions with 3 general + 2 healthcare-specific cards → tweak answers → Run Analysis → spinner → Phase 2 Results with all 6 sections populated → Continue to Features → land on feature engineering page with sidebar showing EDA ✅ Features ⏳.

2. **Auto mode test:** set Configure mode to Auto → EDA shows recommendations card with Accept all + per-row toggles + custom input → click Run → results render → Reconfigure → returns to recommendations card with Accept state preserved.

3. **Chat composer test:** in Results, type "Show distribution by gender" + Send → spinner → new chart prepended to the charts grid + new insight prepended to the insights summary.

4. **Suggestion pill test:** click "Survival curves by age" pill → triggers the same flow with the canned prompt.

5. **Filter test:** uncheck "Box plots" in filters bar → charts grid hides box plot tiles. Move significance slider to 0.10 → stats table includes weak-significance rows. Pick "Numeric only" → charts grid hides categorical-only ones.

6. **Reconfigure test:** click Reconfigure → flips back to Questions → previous answers still highlighted.

7. **Resume test:** complete EDA, return home, reopen project → phase auto-sets to Results because eda_results exist in the project's session.

8. **Theme test:** swap to light mode in either phase → all components render correctly.

9. **Regression:** `pytest tests/` passes. If `tests/agent/test_eda_decisions.py` breaks because the `run_analyses` signature changed, fix the test fixture (don't change `eda_agent`).

## Final reminder

Do NOT modify:
- `agents/**`, `agents/tools/**`, `domains/**`, `core/**`, `data_connectors/**`
- Any other dashboard page (00, 01, 02, 04–09, app.py)
- Existing components (mode_selector, domain_badge, question_renderer, etc.)

Verify before changing:
- `agents.eda_agent.generate_questions` and `run_analyses` signatures (spec 02 + 07 fall back gracefully if missing)
- `agents.eda_agent.add_followup_analysis` exists; if not, fall through to `followup_agent.handle`
- The exact shape of the results dict (charts / stats / insights / quality_flags) — write `dashboard/components/ed_results_adapter.py` if needed

If those interfaces don't match the assumptions, write a thin adapter — do not modify the agent.
