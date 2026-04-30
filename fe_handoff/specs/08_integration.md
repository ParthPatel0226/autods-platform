# Spec 08 — Page Rewrite & Pipeline Integration

## File: `dashboard/pages/04_feature_engineering.py`

```python
"""Feature Engineering page — full rewrite using fe_* components.

Two-phase architecture:
  Phase 1: Configure  — Sections 01–04 + global chat composer + sticky action bar
  Phase 2: Review     — Output shape, diff table, new features, dropped, AI reasoning, approve

The page is project-aware: redirects to the home page if no active project,
reads project.confirmed_domain / target_column / analysis_mode at the top.
"""
from __future__ import annotations
import streamlit as st

from dashboard.components import (
    auth_service,
    project_service,
    sidebar_nav,
    shared_css,
    fe_phase_router,
    fe_dataset_recap,
    fe_columns_panel,
    fe_domain_features,
    fe_custom_builder,
    fe_interaction_features,
    fe_global_chat,
    fe_action_bar,
    fe_review_shape,
    fe_review_diff,
    fe_review_new_features,
    fe_review_dropped,
    fe_review_action_bar,
)


def main() -> None:
    st.set_page_config(
        page_title="Feature Engineering · AutoDS",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Auth + active project gate
    user = auth_service.require_login()
    project = project_service.get_active()
    if not project:
        st.warning("No active project. Returning to home.")
        try:
            from streamlit import switch_page
            switch_page("app.py")
        except Exception:
            pass
        st.stop()

    # Inject shared cosmic theme + fe-* CSS rules
    shared_css.inject()

    # Sidebar (Pipeline → Features active)
    sidebar_nav.render(active="features")

    # Auto-set initial phase
    fe_phase_router.auto_set_initial_phase()

    # ----- Topbar: breadcrumb + phase toggle + theme -----
    _render_topbar(project)

    # ----- Hero -----
    _render_hero()

    # ----- Recap strip + Mode pill -----
    fe_dataset_recap.render()
    _render_mode_pill(project)

    # ----- Phase content -----
    phase = fe_phase_router.get_phase()
    if phase == "configure":
        _render_configure_phase()
    else:
        _render_review_phase()


def _render_topbar(project) -> None:
    """Breadcrumb + phase toggle + theme toggle. Uses shared topbar styles."""
    cols = st.columns([6, 2, 1])
    with cols[0]:
        st.markdown(
            f'<div class="crumbs">'
            f'  <span>{_html_escape(project.name)}</span>'
            f'  <span class="sep">/</span>'
            f'  <span class="cur">Feature Engineering</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        fe_phase_router.render_phase_toggle()
    with cols[2]:
        # Theme toggle — provided by shared_css module
        shared_css.render_theme_toggle()


def _render_hero() -> None:
    phase = fe_phase_router.get_phase()
    if phase == "configure":
        title = 'Engineer your <em>features.</em>'
        subtitle = "Per-column transformations with domain-aware recommendations. AutoDS suggests, you approve."
    else:
        title = 'Review your <em>plan.</em>'
        subtitle = "Final transformations, new features, and dropped columns. Approve to lock the plan."

    st.markdown(
        f'<section class="hero">'
        f'  <div class="eyebrow">'
        f'    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
        f'      <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
        f'    </svg>'
        f'    Step 4 of 7 — Feature Engineering'
        f'  </div>'
        f'  <h1>{title}</h1>'
        f'  <p>{subtitle}</p>'
        f'</section>',
        unsafe_allow_html=True,
    )


def _render_mode_pill(project) -> None:
    mode = (project.analysis_mode or "auto").capitalize()
    domain = (project.confirmed_domain or "generic").capitalize()
    n_cols = len(st.session_state.get("df", [])) if st.session_state.get("df") is not None else 0
    df = st.session_state.get("df")
    n_cols_str = f"{len(df.columns)} columns" if df is not None else ""
    st.markdown(
        f'<div class="fe-mode-pill">'
        f'  <span class="dot"></span>'
        f'  {mode} Mode · {domain} context · {n_cols_str}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_configure_phase() -> None:
    """Phase 1: 4 sections + global chat composer + action bar."""
    # Section 01
    fe_columns_panel.render()

    # Section 02
    fe_domain_features.render()

    # Section 03
    fe_custom_builder.render()

    # Section 04 — Interaction features + global chat composer
    # The interaction component opens a `<div class="fe-sec">` and leaves
    # it open via a comment; we render the global chat composer next, then
    # close the section.
    fe_interaction_features.render()
    fe_global_chat.render()
    st.markdown('</div>', unsafe_allow_html=True)  # close fe-sec from interactions

    # Sticky action bar
    fe_action_bar.render()


def _render_review_phase() -> None:
    """Phase 2: 4 review sections + action bar."""
    fe_review_shape.render()
    fe_review_diff.render()
    fe_review_new_features.render()
    fe_review_dropped.render()
    fe_review_action_bar.render()


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


if __name__ == "__main__" or True:
    main()
```

## Required `project_service` additions

Append to `dashboard/components/project_service.py`:

```python
def update_fe_plan(project, plan: dict) -> None:
    """Persist the FE plan to the active project record."""
    project.fe_plan = plan
    update(project)
```

## Mode-specific behavior at page entry

Add a helper at the top of `_render_configure_phase` to apply mode-specific defaults on first render:

```python
def _apply_mode_defaults() -> None:
    if st.session_state.get("fe_mode_initialized"):
        return
    project = project_service.get_active()
    mode = project.analysis_mode or "auto"

    if mode == "auto":
        # Auto-fill all decisions immediately
        from agents.feature_engineer import recommend_choices
        df = st.session_state.get("df")
        try:
            st.session_state["fe_choices"] = recommend_choices(df, project)
        except Exception:
            from dashboard.components.fe_quick_actions import _fallback_recommendations
            st.session_state["fe_choices"] = _fallback_recommendations(df, project)
        # Domain features: enable all with met requirements
        # (already handled by `default_on=True` in domain configs)

    elif mode == "guided":
        # Pre-fill but mark for review (not used yet — UI just shows recommendations)
        pass

    elif mode == "expert":
        # Leave fe_choices empty
        st.session_state.setdefault("fe_choices", {})

    st.session_state["fe_mode_initialized"] = True


# Call at top of _render_configure_phase
_apply_mode_defaults()
```

## Smoke-test sequence

```
1. Login → Home → New Project → Upload titanic.csv
2. Configure → confirm Healthcare, target=Survived, mode=Guided → Continue
3. EDA → answer questions → Run analysis → results render → Continue to Features
4. Features (configure phase):
   a. Recap strip shows: titanic.csv · 🏥 Healthcare · Survived · 891 · 12 · Guided
   b. Mode pill: "Guided Mode · Healthcare context · 12 columns"
   c. Section 01: 12 column cards. Survived has purple ★ TARGET badge.
      Click Age → expands with 4 selectboxes + reasoning box.
   d. Section 02: 4 healthcare cards. bmi_category disabled (missing cols).
      Type "flag first-class women" in scoped composer → Generate
   e. Section 03: Type name="fare_per_person", expr="Fare / (SibSp + Parch + 1)" → Add
   f. Section 04: Toggle "is_alone" on
   g. Global composer at bottom of Section 04: type "use KNN imputation for all numeric columns" → Send
   h. Action bar: "11 of 12 columns configured · 6 new features queued · ~32s"
   i. Click "Review & Approve →"
5. Features (review phase):
   - Shape: 891 / 12 → 18 / 0
   - Diff table: green Robust/Median/IQR pills on Age row; Drop pill on PassengerId
   - New features: green pills tagged domain · extracted · interaction · custom
   - Dropped: red pills with reasons
   - Click "View AI reasoning" → expands paragraphs
6. Click "Approve & Continue to Modeling →"
   - feature_engineer.execute_choices runs
   - df_engineered written to session_state
   - step_status["features"]="done", ["modeling"]="active"
   - Routes to 05_modeling.py
```

## Defensive interface checks

Before writing each component, confirm the actual interfaces:

- `agents.feature_engineer.recommend_choices(df, project)` — if missing, use `_fallback_recommendations`
- `agents.feature_engineer.suggest_interactions(df, project)` — if missing, use `_fallback_suggestions`
- `agents.feature_engineer.execute_choices(df, plan, project)` — if missing, write a thin wrapper at `dashboard/components/fe_engineer_adapter.py` that calls existing `feature_tools` functions in the right order
- `agents.followup_agent.handle(intent="modify_fe_plan", ...)` — if the intent isn't supported, the try/except catches it; coordinate with backend separately
- `domains/<domain>.feature_questions` — if shape differs, write `fe_domain_adapter.py` to normalize

Do **not** modify `agents/`, `domains/`, or `agents/tools/` — write adapter shims in `dashboard/components/` instead.

## Test expectations

- Existing `pytest tests/` should continue to pass (920+ tests).
- The integration test for the FE pipeline may need a fixture update — instead of writing to `st.session_state["df"]` directly, it should now go through `project_service` and seed an active project.
- If a test breaks because it doesn't seed an active project, **fix the test fixture, not the product code**.
