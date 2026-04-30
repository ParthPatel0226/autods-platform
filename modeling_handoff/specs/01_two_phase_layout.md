# Spec 01 — Two-Phase Layout, Dataset Recap, Page Chrome

## Page structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px, sticky)            │  TOPBAR                         │
│ - Brand mark "AutoDS"              │  - Breadcrumb · phase toggle    │
│ - Workspace (Home, Projects)       │  - Theme toggle                 │
│ - Pipeline (Modeling = active)     ├─────────────────────────────────┤
│ - Tools (Chat, Download)           │                                 │
│ - User chip (footer)               │  HERO (eyebrow + h1 + subtitle) │
│                                    │                                 │
│                                    │  MODE PILL                      │
│                                    │                                 │
│                                    │  [PHASE 1: Configure]  OR       │
│                                    │  [PHASE 2: Results]             │
│                                    │                                 │
│                                    │  ACTION BAR (sticky bottom)     │
└─────────────────────────────────────────────────────────────────────┘
```

The two-phase split: a single page with a phase toggle in the topbar. State key `st.session_state["md_phase"]` is `"configure"` or `"results"`. Default is `"configure"` unless training has completed (best_model is set in state) or training is in progress, in which case default to `"results"`.

## Files to create

- `dashboard/pages/05_modeling.py` — page entry point (REWRITE)
- `dashboard/components/md_phase_router.py` — phase logic
- `dashboard/components/md_dataset_recap.py` — small recap block under hero

The action bar is its own spec (06 for Configure, 08 for Results).

## Visual reference

- Mockup lines 1–250 (CSS tokens + sidebar + topbar + hero)
- Mockup lines 1130–1190 (mode pill + section structure)
- Mockup lines 60–95 (.phase containers — `.phase.active` is shown)

The shell is **identical** to the other tabs. Reuse `dashboard/components/shared_sidebar.py` and `dashboard/components/shared_css.py`. Only inject the `md-*` overrides on top.

## Page entry point — `dashboard/pages/05_modeling.py`

```python
"""AutoDS — Modeling page (step 5 of 7).

Two-phase split (Configure / Results) with live training, MLflow integration,
multi-algorithm comparison, 16-chart diagnostic panel, and final recommendations.

This is a thin orchestrator. All logic lives in dashboard/components/md_*.
"""
from __future__ import annotations
import streamlit as st

from dashboard.components import (
    auth_service,
    shared_sidebar,
    shared_css,
    md_phase_router,
)
from services.project_service import get_project_service


def render():
    st.set_page_config(
        page_title="AutoDS — Modeling",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Inject the cosmic theme
    shared_css.inject()

    # Auth gate
    auth_service.require_login()

    svc = get_project_service()
    project = svc.get_active_project()
    if project is None:
        st.error("No active project. Return to the project list.")
        if st.button("Go to projects"):
            st.switch_page("dashboard/pages/00_home.py")
        return

    state = svc.get_state(project.id)

    # Update pipeline stepper: features=done, modeling=active
    svc.update_pipeline_step(project.id, "features", "done")
    svc.update_pipeline_step(project.id, "modeling", "active")

    # Sidebar
    shared_sidebar.render(project, active="modeling")

    # The router renders topbar + hero + mode pill + the active phase + action bar
    md_phase_router.render(project, state)


# Entry
render()
```

## Phase router — `dashboard/components/md_phase_router.py`

```python
"""Phase router — handles Configure ↔ Results swap.

Public API:
- render(project, state): render topbar, hero, mode pill, and the active phase
- get_phase() -> str: read current phase
- set_phase(phase: str): set phase + rerun
"""
from __future__ import annotations
import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.project_service import Project

PHASE_KEY = "md_phase"  # "configure" | "results"


def get_phase() -> str:
    return st.session_state.get(PHASE_KEY, "configure")


def set_phase(phase: str):
    st.session_state[PHASE_KEY] = phase
    st.rerun()


def _init_phase(state):
    """Initial phase decision based on mode + training status."""
    if PHASE_KEY in st.session_state:
        return

    mode = state.get("user_mode", "guided")
    is_training = st.session_state.get("md_training_in_progress", False)
    has_results = bool(state.get("trained_models"))

    if mode == "auto":
        # Auto mode: jump straight to results, kick off training if not already
        st.session_state[PHASE_KEY] = "results"
        if not is_training and not has_results:
            from dashboard.components import md_training_orchestrator
            md_training_orchestrator.start_auto(state)
    else:
        # Guided / Expert: configure first unless results exist
        st.session_state[PHASE_KEY] = "results" if (has_results or is_training) else "configure"


def render(project, state):
    _init_phase(state)

    _render_topbar(project)
    _render_hero()
    _render_mode_pill(state)

    phase = get_phase()
    if phase == "configure":
        _render_configure(project, state)
    else:
        _render_results(project, state)


def _render_topbar(project):
    """Breadcrumb + Configure/Results toggle + theme toggle."""
    phase = get_phase()

    # Use Streamlit columns since custom <button onclick> doesn't fire Streamlit callbacks
    col_crumb, col_toggle, col_theme = st.columns([0.5, 0.3, 0.2])

    with col_crumb:
        st.markdown(f"""
        <div class="crumbs">
          <span>{project.name}</span>
          <span class="sep">/</span>
          <span class="cur">Modeling</span>
        </div>
        """, unsafe_allow_html=True)

    with col_toggle:
        sub_cfg, sub_res = st.columns(2)
        with sub_cfg:
            if st.button(
                "Configure",
                key="md_phase_btn_configure",
                type=("primary" if phase == "configure" else "secondary"),
                use_container_width=True,
            ):
                set_phase("configure")
        with sub_res:
            if st.button(
                "Results",
                key="md_phase_btn_results",
                type=("primary" if phase == "results" else "secondary"),
                use_container_width=True,
            ):
                set_phase("results")

    with col_theme:
        # Theme toggle is global; defer to shared component
        from dashboard.components import shared_theme_toggle
        shared_theme_toggle.render()


def _render_hero():
    phase = get_phase()
    if phase == "configure":
        title = 'Train your <em>model.</em>'
        sub = ("Algorithm selection, validation strategy, and live training. "
               "AutoDS recommends the best fit for your problem; you stay in control.")
    else:
        title = 'Watch them <em>compete.</em>'
        sub = ("Models racing on cross-validated metrics. Best model auto-promoted. "
               "Stack & extend recommendations on the right.")

    st.markdown(f"""
    <section class="hero">
      <div class="eyebrow">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
        </svg>
        Step 5 of 7 — Modeling
      </div>
      <h1>{title}</h1>
      <p>{sub}</p>
    </section>
    """, unsafe_allow_html=True)


def _render_mode_pill(state):
    """Switches between violet 'Guided Mode...' and cyan 'Training in progress...'."""
    is_training = st.session_state.get("md_training_in_progress", False)

    if is_training:
        n_done = len(state.get("trained_models", {}))
        n_total = st.session_state.get("md_n_total", n_done)
        run_id = st.session_state.get("md_mlflow_run_id", "—")[:8]
        st.markdown(f"""
        <div class="md-mode-pill" style="background:rgba(34,211,238,0.10); color:var(--cyan); border-color:rgba(34,211,238,0.30);">
          <span class="dot" style="background:var(--cyan);"></span>
          Training in progress · {n_done} of {n_total} done · MLflow run {run_id}
        </div>
        """, unsafe_allow_html=True)
        return

    mode = state.get("user_mode", "guided").capitalize()
    domain = state.get("detected_domain", "generic").capitalize()
    n_features = len(state.get("feature_list", []))
    st.markdown(f"""
    <div class="md-mode-pill">
      <span class="dot"></span>
      {mode} Mode · {domain} context · {n_features} features
    </div>
    """, unsafe_allow_html=True)


def _render_configure(project, state):
    from dashboard.components import (
        md_problem_recap,
        md_algorithm_spotlight,
        md_algorithm_picker,
        md_hp_panel,
        md_validation_strategy,
        md_global_chat,
        md_action_bar_configure,
    )
    md_problem_recap.render(state)
    md_algorithm_spotlight.render(state)
    md_algorithm_picker.render(state)
    md_hp_panel.render(state)
    md_validation_strategy.render(state)
    md_global_chat.render(project, state)
    md_action_bar_configure.render(project, state)


def _render_results(project, state):
    from dashboard.components import (
        md_train_status,
        md_race_arena,
        md_best_spotlight,
        md_insight_cards,
        md_pareto_frontier,
        md_charts_panel,
        md_final_recommendations,
        md_training_log,
        md_action_bar_results,
    )
    md_train_status.render(state)
    md_race_arena.render(state)
    md_best_spotlight.render(state)
    md_insight_cards.render(project, state)
    md_pareto_frontier.render(state)
    md_charts_panel.render(state)
    md_final_recommendations.render(state)
    md_training_log.render(state)
    md_action_bar_results.render(project, state)

    # Schedule a poll if training is still going
    if st.session_state.get("md_training_in_progress", False):
        import time
        time.sleep(2)
        st.rerun()
```

## Dataset recap (optional — slim version)

The mockup doesn't show a dataset recap (the FE tab does); but since users may have arrived from FE, we might want a 1-line breadcrumb. **Skip for now** — the mode pill and problem-type recap (spec 02) cover the same ground. Don't create `md_dataset_recap.py` unless explicitly requested.

## CSS additions

Append the following blocks to `dashboard/components/shared_css.py` (search for `# === MODELING (md-*) ===` to insert at the right spot, or append at the end). **Copy the full contents from `reference/modeling_mockup.html`'s `<style>` block** — every `.md-*` rule, every keyframe, every responsive media query.

CSS class blocks to add (verify all are present in the mockup):

- Tokens (already in shared theme — skip if present)
- Mode pill (`.md-mode-pill`)
- Section blocks (`.md-sec`, `.md-sec-head`, `.md-sec-num`, `.md-sec-title`, `.md-sec-meta`, `.md-sec-tip`)
- Problem-type recap (`.md-problem`, `.md-problem-pill`, `.md-problem-target`, `.md-problem-meta`, `.md-override`)
- Algorithm spotlight (`.md-algo-spot`, `.md-algo-icon`, `.md-algo-body`, `.md-algo-name`, `.md-algo-tag`, `.md-algo-desc`, `.md-algo-strengths`, `.md-algo-strength`)
- Multi-select (`.md-multiselect`, `.md-multiselect-trigger`, `.md-multiselect-summary`, `.md-multiselect-panel`, `.md-multiselect-search`, `.md-multiselect-group`, `.md-multiselect-group-label`, `.md-ms-opt`)
- HP cards (`.md-hp-card`, `.md-hp-head`, `.md-hp-name`, `.md-hp-tag`, `.md-hp-arrow`, `.md-hp-body`, `.md-hp-grid`, `.md-rec-hint`, `.md-hp-all`, `.md-hp-search`, `.md-hp-search-label`, `.md-hp-empty`)
- Validation grid (`.md-val-grid`, `.md-field`, `.md-select`, `.md-input`, `.md-slider-row`, `.md-slider-val`)
- Chat composer (`.md-ai-composer`, `.md-ai-head`, `.md-ai-title`, `.md-ai-sub`, `.md-ai-row`, `.md-ai-input`, `.md-ai-send`, `.md-suggestion-row`, `.md-sug`)
- Action bar (`.md-action-bar`, `.md-action-status`, `.btn-ghost`, `.btn-primary`)
- Training status (`.md-train-status`, `.md-train-spinner`, `.md-train-text`, `.md-train-eta`)
- Race arena (`.md-arena`, `.md-race`, `.md-race-rank`, `.md-race-name`, `.md-race-bar`, `.md-race-fill`, `.md-race-score`, `.md-race-status`)
- Best spotlight (`.md-best`, `.md-best-tag`, `.md-best-name`, `.md-best-sub`, `.md-best-metrics`, `.md-metric`, `.md-metric-val`, `.md-metric-label`)
- DNA radar (`.md-dna`)
- Pareto (`.md-pareto-grid`, `.md-pareto-chart`, `.md-pareto-side`, `.md-pareto-tag`)
- Insight cards (`.md-insight`, `.md-insight-icon`, `.md-insight-body`, `.md-insight-title`, `.md-insight-desc`, `.md-insight-cta`)
- Charts panel (`.md-charts-shell`, `.md-charts-side`, `.md-charts-side-group`, `.md-chart-tab`, `.md-chart-tab-icon`, `.md-chart-main`, `.md-chart-main-head`, `.md-chart-main-title`, `.md-chart-main-sub`, `.md-chart-model-switch`, `.md-chart-canvas`, `.md-chart-caption`)
- Final recommendations (`.md-rec-grid`, `.md-rec-card`, `.md-rec-icon`, `.md-rec-body`, `.md-rec-title`, `.md-rec-desc`)
- Training log (`.md-log`, `.md-log-line`, `.md-log-time`, `.md-log-level`)

CSS extraction shortcut: open `reference/modeling_mockup.html`, copy the entire `<style>` block from line ~25 to ~925, paste at the end of `shared_css.py`. Do not edit colors or sizes — they are already correct.

## Smoke test for spec 01

After this spec is implemented:

1. Run `streamlit run dashboard/app.py`
2. Navigate to a project that has features completed
3. Click **Modeling** in the sidebar
4. ✅ Sidebar renders with Modeling highlighted (dot pulsing)
5. ✅ Hero shows "Train your *model*." with gradient italic
6. ✅ Mode pill says e.g. "Guided Mode · Healthcare context · 18 features"
7. ✅ Phase toggle in topbar shows Configure | Results
8. ✅ Clicking Results swaps the body (will be empty until other specs are built)
9. ✅ Action bar at bottom is sticky, shows "0 algorithms queued"
10. ✅ No console errors, no raw HTML rendered as text

If any of these fail, fix them before moving to spec 02.

## Edge cases to handle

- **No project loaded:** show error, link back to project list
- **State has `best_model` already (re-entry):** start in Results phase, not Configure
- **State has `trained_models` partially populated (mid-training crash):** start in Results phase showing what trained, with a "Resume training" hint in the action bar
- **Auto mode + already trained:** start in Results phase, do NOT re-trigger training
- **Theme toggle clicked:** light theme works (CSS already supports it via `[data-theme="light"]`)
- **Direct URL navigation to /modeling without going through pipeline:** verify state has `df_engineered` (or its equivalent); if not, redirect to feature_engineering page with a toast "Complete feature engineering first"
