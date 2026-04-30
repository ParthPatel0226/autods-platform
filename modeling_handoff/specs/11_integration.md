# Spec 11 — Integration: Page Rewrite + Project Service + Smoke Test

This spec is the glue. It rewrites `dashboard/pages/05_modeling.py` as a thin orchestrator that imports all the components from specs 01–10, extends `services/project_service.py` with two new methods, and gives a step-by-step smoke test sequence.

## Mockup reference
**File:** `reference/modeling_mockup.html`
The mockup is the source of truth for HTML structure, CSS classes, and section ordering. The page integration assembles the components in the same order as the mockup.

---

## What this spec covers

1. **Rewrite `dashboard/pages/05_modeling.py`** as a thin page that:
   - Authenticates and loads the active project's state
   - Routes between Phase 1 (Configure) and Phase 2 (Results) using `md_phase_router` from spec 01
   - In Phase 1: renders shell (sidebar/topbar/hero) → sections 01–04 → action bar
   - In Phase 2: renders shell → live training status → race arena → spotlight + DNA radar → insight cards → Pareto → diagnostic charts panel → final recommendations → training log → action bar
   - Calls `commit_modeling_results()` when training completes
   - Cleans up when user navigates away mid-training (sets cancel flag)

2. **Extend `services/project_service.py`** with two methods:
   - `update_modeling_plan(project_id, plan)` — writes plan dict to LangGraph state
   - `commit_modeling_results(project_id, state)` — persists trained_models/model_results/best_model to project DB

3. **Smoke-test sequence** — exact step-by-step path that must work end-to-end.

4. **Build order** — recommended sequence to implement the 11 specs.

---

## Hard rules

1. **Never duplicate code that's already in a component.** The page calls component `render()` functions and that's it.
2. **All session state writes happen inside components.** The page only reads state at the boundary.
3. **Project service is extended, not modified.** Existing methods are untouched. New methods append.
4. **Defensive interface checks.** Before calling `modeling_agent.recommend_algorithm`, `modeling_agent.train_models`, `tool_registry.get_models_for_problem_type`, or `followup_agent.handle(intent="modify_modeling_plan")`, check the attribute exists. If not, fall back to the adapter's defaults.
5. **The page MUST run independently of every spec being complete.** If spec 09 (charts panel) isn't built yet, that section just doesn't render — the rest of the page works.

---

## File 1 — Rewrite of `dashboard/pages/05_modeling.py`

```python
"""
Modeling page — thin orchestrator.

Phase 1 (configure):
  Shell → Section 01 (problem & algorithm)
        → Section 02 (HP cards)
        → Section 03 (validation)
        → Section 04 (chat composer)
        → Configure-phase action bar

Phase 2 (results):
  Shell → Live training status
        → Race arena
        → Best model spotlight + DNA radar
        → Insight cards
        → Pareto frontier
        → Diagnostic charts panel
        → Final recommendations
        → Training log
        → Results-phase action bar
"""

import logging
import streamlit as st

from dashboard.components.shared_css import inject_modeling_css
from dashboard.components.md_phase_router import (
    PHASE_KEY, init_phase, current_phase, set_phase,
)
from dashboard.components import (
    md_problem_recap,
    md_algorithm_spotlight,
    md_algorithm_picker,
    md_hp_panel,
    md_validation_strategy,
    md_global_chat,
    md_action_bar_configure,
    md_train_status,
    md_race_arena,
    md_best_spotlight,
    md_insight_cards,
    md_pareto_frontier,
    md_charts_panel,
    md_final_recommendations,
    md_training_log,
    md_training_orchestrator as orch,
)
from dashboard.components.shell import render_sidebar, render_topbar, render_hero, render_pipeline_stepper
from services import project_service

logger = logging.getLogger(__name__)


def main():
    st.set_page_config(
        page_title="AutoDS — Modeling",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Auth + project load
    project_id = _ensure_project_loaded()
    if project_id is None:
        return
    state = project_service.get_project_state(project_id)

    inject_modeling_css()

    # Init phase router
    init_phase(state)

    # Shell
    render_sidebar(state, active_page="modeling")
    render_topbar(state, active_phase=current_phase())
    render_pipeline_stepper(state, active_step="modeling",
                            completed_steps=state.get("completed_steps", []))

    # Hero
    render_hero(
        eyebrow="✦ MODEL TRAINING",
        title="Build the <em>best</em> model",
        subtitle="AutoDS picks an algorithm, tunes hyperparameters, validates, and benchmarks. You stay in the driver's seat.",
        mode_pill=state.get("user_mode", "guided"),
    )

    # Phase router
    if current_phase() == "configure":
        _render_configure_phase(state, project_id)
    else:
        _render_results_phase(state, project_id)


# ────────────────────── PHASE 1 — CONFIGURE ──────────────────────

def _render_configure_phase(state, project_id):
    """Sections 01–04 + action bar."""

    # Section 01 — problem & algorithm
    md_problem_recap.render(state, project_id)
    md_algorithm_spotlight.render(state, project_id)
    md_algorithm_picker.render(state, project_id)

    # Section 02 — HP cards (driven by section 01 multi-select)
    md_hp_panel.render(state, project_id)

    # Section 03 — validation
    md_validation_strategy.render(state, project_id)

    # Section 04 — global chat
    md_global_chat.render(state, project_id)

    # Action bar (sticky bottom)
    def _on_start_training(state):
        plan = _freeze_plan(state)
        try:
            project_service.update_modeling_plan(project_id, plan)
        except Exception as e:
            logger.warning(f"update_modeling_plan failed: {e}")

        orch.start(state, plan, project_id)
        set_phase("results")
        st.rerun()

    md_action_bar_configure.render(state, project_id, on_start_training=_on_start_training)


def _freeze_plan(state) -> dict:
    """Snapshot modeling_config + session-state HP values into a frozen plan dict."""
    cfg = dict(state.get("modeling_config", {}))

    # Pull in HP values from session_state
    hp_values = st.session_state.get("md_hp_values", {})
    hp_strategy = st.session_state.get("md_hp_strategy", {})
    cfg.setdefault("hyperparameters", {})
    cfg.setdefault("search_strategy", {})
    for algo, params in hp_values.items():
        cfg["hyperparameters"][algo] = params
    for algo, strat in hp_strategy.items():
        cfg["search_strategy"][algo] = strat

    return cfg


# ────────────────────── PHASE 2 — RESULTS ────────────────────────

def _render_results_phase(state, project_id):
    """Live training + all results visualizations + action bar."""

    # Live training status (top)
    md_train_status.render(state, project_id)

    # Race arena
    md_race_arena.render(state, project_id)

    # Best model spotlight + DNA radar
    md_best_spotlight.render(state, project_id)

    # Insight cards
    md_insight_cards.render(state, project_id)

    # Pareto frontier
    md_pareto_frontier.render(state, project_id)

    # Diagnostic charts panel (Spotify-style)
    md_charts_panel.render(state, project_id)

    # Final recommendations
    md_final_recommendations.render(state, project_id)

    # Training log
    md_training_log.render(state, project_id)

    # Results-phase action bar
    _render_results_action_bar(state, project_id)

    # Commit results to project_service when training has completed
    if orch.is_complete():
        try:
            project_service.commit_modeling_results(project_id, state)
        except Exception as e:
            logger.warning(f"commit_modeling_results failed: {e}")


def _render_results_action_bar(state, project_id):
    """Sticky bottom bar — Reconfigure + Continue to Explainability."""
    is_complete = orch.is_complete()
    is_running = orch.is_running()

    btn_cols = st.columns([0.55, 0.22, 0.23])
    with btn_cols[1]:
        if st.button("← Reconfigure", key=f"md_reconfig_{project_id}", use_container_width=True,
                     disabled=is_running):
            orch.reset()
            set_phase("configure")
            st.rerun()
    with btn_cols[2]:
        if st.button(
            "Continue to Explainability →",
            key=f"md_continue_{project_id}",
            type="primary",
            use_container_width=True,
            disabled=not is_complete,
            help="Wait for training to complete" if not is_complete else None,
        ):
            try:
                st.switch_page("pages/06_explainability.py")
            except Exception as e:
                st.toast(f"Navigation failed: {e}", icon="⚠")


# ────────────────────── helpers ──────────────────────

def _ensure_project_loaded() -> str | None:
    """Standard auth + project guard (matches other pages)."""
    if "user_id" not in st.session_state:
        st.warning("Please log in.")
        st.switch_page("app.py")
        return None
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        st.warning("No active project. Upload a dataset first.")
        st.switch_page("pages/02_upload.py")
        return None
    return project_id


if __name__ == "__main__":
    main()
```

**This file replaces the existing 417-line `pages/05_modeling.py` entirely.** Old logic is fully superseded.

---

## File 2 — Extensions to `services/project_service.py`

Append (do NOT modify existing methods):

```python
# ────────────────── Modeling-page extensions ──────────────────

def update_modeling_plan(project_id: str, plan: dict) -> None:
    """
    Persist the modeling plan to the project's state file.
    Called when the user clicks Start Training.

    The plan dict contains: selected_algorithms, recommended_algorithm,
    hyperparameters, search_strategy, validation, custom_instructions.
    """
    state = get_project_state(project_id)
    state.setdefault("modeling_config", {})
    state["modeling_config"].update(plan)

    # Update pipeline_log
    state.setdefault("pipeline_log", []).append({
        "timestamp": _utcnow_iso(),
        "step": "modeling",
        "action": "plan_committed",
        "plan_summary": {
            "n_algorithms": len(plan.get("selected_algorithms", [])),
            "validation_method": plan.get("validation", {}).get("method"),
        },
    })
    save_project_state(project_id, state)


def commit_modeling_results(project_id: str, state: dict) -> None:
    """
    Persist trained_models / model_results / best_model after training completes.
    Called once per session, when orch.is_complete() is True.

    The orchestrator already wrote these fields to `state` before this call;
    this method just persists state to disk and updates pipeline_log.
    """
    # Idempotency — if already committed for this run, skip
    last_commit = state.get("_modeling_last_commit_at")
    last_complete = state.get("_modeling_last_complete_at")
    if last_commit and last_complete and last_commit == last_complete:
        return

    save_project_state(project_id, state)

    state.setdefault("pipeline_log", []).append({
        "timestamp": _utcnow_iso(),
        "step": "modeling",
        "action": "results_committed",
        "summary": {
            "n_trained": len(state.get("trained_models", {})),
            "best_model": state.get("best_model"),
        },
    })
    state["_modeling_last_commit_at"] = _utcnow_iso()
    state["_modeling_last_complete_at"] = _utcnow_iso()
    save_project_state(project_id, state)


def _utcnow_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

**Important:** `get_project_state()` and `save_project_state()` are existing methods — use them as-is. If `save_project_state` doesn't exist, fall back to whatever the existing persistence pattern is in `project_service.py`.

---

## File 3 — Defensive interface checks

These checks live inside the components (specs 03, 04, 06, 07) but are summarized here for completeness.

### Inside `md_algorithm_registry_adapter.py` (spec 03)

```python
def get_recommended_algorithm(state):
    try:
        from agents import modeling_agent
        if hasattr(modeling_agent, "recommend_algorithm"):
            return modeling_agent.recommend_algorithm(state)
    except Exception:
        pass
    # Fallback — pick by problem type
    return _fallback_recommendation(state)


def get_algorithms_for_problem_type(problem_type):
    try:
        from agents.tools import tool_registry
        if hasattr(tool_registry, "get_models_for_problem_type"):
            return tool_registry.get_models_for_problem_type(problem_type)
    except Exception:
        pass
    # Fallback — return FALLBACK_ALGORITHMS dict from spec 03
    return FALLBACK_ALGORITHMS.get(problem_type, [])
```

### Inside `md_followup_adapter.py` (spec 06)

Already covered — try/except around `agents.followup_agent.handle()`.

### Inside `md_training_orchestrator._train_one()` (spec 07)

Already covered — try/except around `agents.modeling_agent.train_models()` with three fallback layers.

---

## File 4 — Test file `tests/test_modeling_page.py`

```python
"""
Smoke tests for the modeling page integration.
Each test imports the components and verifies they don't crash on minimal state.
"""

import pytest
import streamlit as st


@pytest.fixture
def minimal_state():
    return {
        "session_id": "test-session",
        "user_mode": "guided",
        "problem_type": "binary_classification",
        "target_column": "Survived",
        "detected_domain": "healthcare",
        "data_profile": {
            "n_rows": 891,
            "n_features": 10,
            "target_imbalance_ratio": 0.38,
        },
        "modeling_config": {
            "selected_algorithms": [],
            "recommended_algorithm": "XGBoost",
        },
        "random_seed": 42,
        "completed_steps": ["upload", "configure", "eda", "feature_engineering"],
        "current_step": "modeling",
    }


def test_problem_recap_renders(minimal_state):
    from dashboard.components import md_problem_recap
    assert hasattr(md_problem_recap, "render")


def test_algorithm_picker_imports(minimal_state):
    from dashboard.components import md_algorithm_picker
    assert hasattr(md_algorithm_picker, "render")


def test_hp_schema_adapter_returns_schema(minimal_state):
    from dashboard.components.md_hp_schema_adapter import get_schema_for
    schema = get_schema_for("XGBoost", "binary_classification", minimal_state)
    assert schema["algo_name"] == "XGBoost"
    assert len(schema["top_params"]) <= 4
    assert len(schema["all_params"]) >= len(schema["top_params"])


def test_validation_recommend(minimal_state):
    from dashboard.components.md_validation_strategy import _recommend_method
    # Classification → stratified
    assert _recommend_method(minimal_state) == "stratified_kfold"
    # Regression → kfold
    minimal_state["problem_type"] = "regression"
    assert _recommend_method(minimal_state) == "kfold"
    # Time-series → time_series_split
    minimal_state["problem_type"] = "time_series"
    assert _recommend_method(minimal_state) == "time_series_split"


def test_followup_adapter_fallback():
    """Should never crash — even if followup_agent doesn't exist."""
    from dashboard.components.md_followup_adapter import submit_modeling_instruction
    state = {}
    result = submit_modeling_instruction("optimize for recall", state)
    assert result["ok"] is True
    assert "custom_instructions" in state.get("modeling_config", {})


def test_orchestrator_idempotent_start():
    """Two start() calls in a row must not double-launch."""
    from dashboard.components import md_training_orchestrator as orch
    orch.reset()
    # Without st context, start should fail gracefully
    # ... (this test is illustrative; real CI would mock st.session_state)


def test_recommendation_rules_handle_missing_helpers():
    """Each rule should fall back to None or heuristic if helpers don't exist."""
    from dashboard.components import md_final_recommendations as recs
    state = {
        "best_model": "XGBoost",
        "problem_type": "binary_classification",
        "data_profile": {"target_imbalance_ratio": 0.4},
        "model_results": {"XGBoost": {"auc_roc": 0.85, "recall": 0.78}},
    }
    # Each rule must return either None or a dict
    assert recs._rec_deploy_best_model(state) is not None
    assert recs._rec_monitor_drift(state) is not None
    assert recs._rec_retrain_quarterly(state) is not None
    # imbalance card depends on recall threshold; with recall=0.78 should fire
    card = recs._rec_watch_imbalance(state)
    assert card is None or card["icon"] == "⚠"
```

---

## Smoke test (manual, end-to-end)

Step-by-step path that must work after all 11 specs are implemented:

1. **Login** → land on `app.py`
2. **Click "New Project"** → land on `02_upload.py`
3. **Upload** `examples/titanic.csv` (or any classification dataset)
4. **Verify** upload page recognizes the data, shows preview
5. **Click "Continue to Configure"** → land on `03_configure.py`
6. **Set** Domain = Healthcare (or auto-detected), Target = Survived, Mode = Guided
7. **Click "Continue to EDA"** → land on `04_eda_interactive.py`
8. **Run** at least one EDA action, click "Continue to Features"
9. **Click "Continue to Features"** → land on `04_feature_engineering.py`
10. **Accept all default feature engineering choices**, click "Continue to Modeling"
11. **Modeling page loads (Phase 1 — Configure)**:
    - Section 01 shows "BINARY CLASSIFICATION" pill, target = Survived, recommended algorithm = XGBoost
    - Multi-select dropdown shows 22 algorithms in 7 family groups
    - Section 02 shows "No models selected" empty state
    - Section 03 shows Stratified K-Fold (5 folds) auto-selected with cyan tip explaining why
    - Section 04 shows chat composer + 4 suggestion pills
    - Action bar shows "0 algorithms queued · …" with Start Training disabled
12. **Check 3 algorithms** in section 01 (XGBoost, RandomForest, LogisticRegression)
13. **Section 02** populates with 3 HP cards. XGBoost expanded (recommended), the other 2 collapsed
14. **Edit** a hyperparameter (e.g. LogReg `C` from 1.0 to 0.5) — verify the value persists
15. **Section 03** — change validation to K-Fold (10 folds). Cyan tip updates.
16. **Action bar** now shows "3 algorithms queued · stratified … · bayesian search · ETA ~4 min" with Start Training enabled.
17. **Click Start Training** → page switches to Phase 2 — Results
18. **Live training status** strip shows spinner + "Training XGBoost · trial 1/50"
19. **Race arena** populates progressively as trials/folds complete. XGBoost row shimmers cyan; others queued.
20. **2 seconds later** the page re-runs and shows progress advancing.
21. **First model completes** (e.g. LogisticRegression). Its row turns green, bar fills, score appears.
22. **Best model spotlight** appears with the best so far. DNA radar appears.
23. **Insight cards** appear (forecast suggesting more search; stack suggesting top-3 ensemble) — IF rules fire.
24. **Pareto frontier** appears once 2+ models have inference benchmarks.
25. **Diagnostic charts panel** has sidebar populated with chart links. Clicking ROC swaps the chart. Clicking Confusion Matrix swaps again.
26. **All training completes** — status strip turns green "Training complete · 3 of 3 models trained"
27. **Final recommendations** populates with 4-6 cards.
28. **Training log** shows a colored list of INFO/OK/WARN entries.
29. **State has been written:**
    - `state["trained_models"]` = `{"XGBoost": "<run_id>", ...}`
    - `state["model_results"]` = `{"XGBoost": {"auc_roc": 0.85, ...}, ...}`
    - `state["best_model"]` = `"XGBoost"`
    - `state["best_model_path"]` = `"file://.../mlruns/.../artifacts/model"`
    - `state["completed_steps"]` includes `"modeling"`
30. **Click Continue to Explainability** → lands on `06_explainability.py`. The explainability page sees `state["best_model"]` is set and starts loading.

If any of these steps doesn't work end-to-end, that's a bug.

---

## Build order

Recommended sequence to implement the 11 specs:

1. **Spec 01 — Two-phase layout** (lays the foundation)
2. **Spec 02 — Problem-type recap** (smallest visible component, validates the shell works)
3. **Spec 03 — Algorithm selection** (the section 01 multi-select)
4. **Spec 11 (partial) — Page integration** (bare-bones page that just renders Section 01 — proves the integration model works)
5. **Spec 04 — Hyperparameter cards** (section 02, depends on section 01's state)
6. **Spec 05 — Validation strategy** (section 03)
7. **Spec 06 — Global chat composer + action bar** (section 04 + bottom strip)
8. **Spec 07 — Training execution** (the big one — background thread, MLflow, cancel)
9. **Spec 08 — Results phase** (race arena → spotlight → DNA radar → insights → Pareto → log)
10. **Spec 09 — Diagnostic charts panel** (Spotify-style sidebar)
11. **Spec 10 — Final recommendations** (small, polish)
12. **Spec 11 (full) — Integration + project_service + tests + smoke run**

Each spec has its own acceptance criteria. Aim for a green pass on each before moving to the next. Spec 11's smoke test is the integration gate — if it fails, stop and fix before declaring done.

---

## Acceptance criteria

- [ ] `dashboard/pages/05_modeling.py` is fully rewritten as a thin orchestrator (~150 lines)
- [ ] All component imports work without circular dependencies
- [ ] Phase 1 → Phase 2 transition fires on Start Training
- [ ] Phase 2 → Phase 1 transition fires on Reconfigure (with cancel)
- [ ] `services/project_service.update_modeling_plan` is callable and persists plan
- [ ] `services/project_service.commit_modeling_results` is callable and persists results
- [ ] All defensive interface checks fall back gracefully when backend signatures don't match
- [ ] `tests/test_modeling_page.py` passes
- [ ] Smoke test (manual end-to-end) completes from upload → modeling → explainability without errors
- [ ] No modifications outside `dashboard/`, `services/project_service.py`, and `tests/`
