# AutoDS Modeling Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_two_phase_layout.md` → `specs/02_problem_recap.md` → `specs/03_algorithm_selection.md` → `specs/04_hyperparameter_cards.md` → `specs/05_validation_strategy.md` → `specs/06_global_chat_composer.md` → `specs/07_training_execution.md` → `specs/08_results_phase.md` → `specs/09_charts_panel.md` → `specs/10_final_recommendations.md` → `specs/11_integration.md` → `reference/modeling_mockup.html` (visual target — already approved).

---

## Goal

Replace `dashboard/pages/05_modeling.py` (current 417 lines, broken — defaults to clustering algos regardless of problem type, hangs at "Connect the Modeling Agent to execute training", never trains anything) with a redesigned Modeling page that:

- Uses a **two-phase split** — **Configure** (sections 01–04 + global chat composer) and **Results** (live race arena, best-model spotlight + DNA radar, insight cards, Pareto frontier, charts panel, final recommendations, training log), toggled in the topbar
- **Section 01 — Problem & algorithm**: problem-type recap card (auto-detected), recommended-algorithm spotlight (with strengths and explanation), and a multi-select dropdown of all available algorithms grouped by family
- **Section 02 — Hyperparameter tuning**: one card per algorithm checked in section 01 — top 4 most important hyperparameters surfaced inline with `★ recommended` markers, "All hyperparameters · N more" expander revealing the full param list, per-algorithm search-strategy dropdown. Cards appear/disappear dynamically driven by section 01's multi-select.
- **Section 03 — Validation strategy**: method dropdown, train/test split slider, random seed input
- **Section 04 — Global modeling chat composer**: open-ended AI request that updates the entire plan via `followup_agent.handle` with `intent="modify_modeling_plan"`
- **Phase 2 — Results** runs **actual model training** (the bug fix) via a background thread, polls progress every 2s, displays live race arena, best-model spotlight + DNA radar, insight cards, Pareto frontier, Spotify-style charts panel with sidebar (16 charts), final recommendations, and streamed training log
- Renders fully in the **cosmic theme** matching previous tabs

This is **UI/UX refactor + bug fix only**. Backend (`agents/modeling_agent.py`, `agents/tools/ml_tools.py`, `agents/tools/tool_registry.py`, `agents/followup_agent.py`, `domains/`, `core/`, `evaluation/`, `validation/`, `explainability/`) is reused. The only "new" backend piece is a thin **streaming wrapper** around existing training functions — see `specs/07_training_execution.md`.

## Prerequisites

- Home, Upload, Configure, EDA, and Feature Engineering tabs (handoffs #1–5) deployed
- `auth_service.py`, `project_service.py`, `sidebar_nav.py`, `shared_css.py` are in place
- Previous handoffs use `home-*`, `up-*`, `cf-*`, `ed-*`, `fe-*` CSS prefixes — this bundle uses `md-*`
- The Feature Engineering page wrote `project.fe_done = True`, executed `feature_engineer.execute_choices(project)`, and pushed the engineered dataset into `st.session_state["df_engineered"]`
- The Configure page wrote `project.target_column`, `project.confirmed_domain`, `project.analysis_mode`, `project.problem_type`, `project.excluded_columns` into the project record
- `agents/modeling_agent.py` already exists (678 lines). Spec 11 covers the exact function signatures used and adapter wrapping for any mismatches.

## Critical Constraints

1. **Do NOT modify** anything in `agents/`, `agents/tools/`, `domains/`, `core/`, `evaluation/`, `validation/`, `explainability/`, `reports/`, `serving/`, `data_connectors/`. **Period.** All component-side adaptation lives in adapter shims under `dashboard/components/md_*_adapter.py`.
2. **Reuse `agents.modeling_agent`** for algorithm recommendation, problem-type detection, and training orchestration via adapter — no reimplementation.
3. **Reuse `agents.tools.ml_tools`** for the actual sklearn/xgboost/lightgbm training functions. The streaming wrapper in `dashboard/components/md_training_runner.py` only manages threading + progress queue.
4. **Reuse `agents.tools.tool_registry`** to enumerate available algorithms per problem_type. THIS IS the source of truth for which models can be selected — never hardcode the algorithm list anywhere in the dashboard.
5. **Reuse `domains/<domain>.py`'s `model_questions`** list for any domain-specific recommendations.
6. **Reuse `agents.followup_agent.handle`** for the global chat composer with `intent="modify_modeling_plan"`. If the agent doesn't yet know that intent, the adapter falls back gracefully (see spec 06).
7. **Reuse `evaluation/model_comparator.py`, `evaluation/bootstrap_ci.py`, `evaluation/domain_metrics.py`** for the Phase 2 statistical comparison features.
8. **Reuse `validation/model_validator.py`** for the deploy/threshold recommendations in the final recommendations grid.
9. **Reuse `explainability/calibration.py`** for the Calibration chart in the charts panel.
10. **Extend `shared_css.py` additively** with `md-*` prefix. Never remove or modify existing rules. The mockup defines all the styles you need — copy them verbatim.
11. The page must remain **project-aware** — read active project at top, redirect to `app.py` if none, write all selections + trained models + best-model path back to the project.
12. **Reproducibility**: `random_seed` from section 03 must flow into every random operation. Verify by running twice with the same seed → identical leaderboard.
13. **MLflow**: every training run must be logged to MLflow under the project's experiment. Run IDs must be saved into `state["trained_models"]` so Explainability and Predict tabs can load them.

## What "Done" Looks Like

A user can:

1. Land on Modeling after Feature Engineering → see **Phase 1 — Configure** with the breadcrumb topbar (Configure / Results phase toggle in the topbar — Results is disabled until training completes), hero ("Train your *model.*"), eyebrow chip "Step 5 of 7 — Modeling", mode pill ("Guided Mode · Healthcare context · 18 features"), and 4 numbered sections.
2. **Section 01** shows the problem-type recap card (purple `BINARY CLASSIFICATION` pill + `target = Survived` + `891 rows · 18 features · slight imbalance (38.4% positive)` + `Override?` link). Below it, the recommended algorithm spotlight (XGBoost as a glowing card with circular icon, "✦ Recommended for binary classification" tag, *XGBoost* in Instrument Serif gradient italic, brief description, and 5 strength chips). Below that, the multi-select dropdown listing all 22 algorithms grouped into 6 sections.
3. **Section 02** shows one hyperparameter card per checked algorithm in section 01. Each card has top 4 hyperparameters inline (each marked `★ recommended` if AutoDS-suggested), an "All hyperparameters · N more" expander, and a per-algorithm Search strategy dropdown.
4. **Section 03** shows the validation grid: method dropdown, train/test split slider, random seed.
5. **Section 04** shows the global chat composer. Sending routes through `followup_agent.handle(intent="modify_modeling_plan", ...)`.
6. **Sticky action bar**: "4 algorithms queued · Stratified 5-fold · Balanced search · ETA ~12 min" + Back to Features + **Start Training →**
7. Clicking **Start Training** transitions UI to **Phase 2 — Results** AND kicks off training in a background thread. Phase 2 is fully populated even while training is in progress — no blank page bug. The race arena, status pill, and log update live every 2 seconds.
8. **Cancel button** in the training status strip works gracefully.
9. **Failure handling**: failed models turn red in the race arena with status "Failed", the log shows an `ERR` line, the next model in the queue starts.
10. Click **Continue to Explainability** → writes `project.modeling_done = True`, `project.trained_models = {...}`, `project.best_model = "xgboost"`, `project.best_model_path = "mlruns/.../xgboost"`, advances stepper, routes to `06_explainability.py`.
11. Click **Reconfigure** → returns to Phase 1 with all answers preserved.
12. **Mode behavior**:
    - **Auto**: pre-selects recommended + 3 default comparators, balanced Bayesian search, Stratified K-Fold + 80/20 + seed 42. **Auto-runs training on entry to the page.**
    - **Guided**: shows all recommendations + explanations + tip strips. User reviews and clicks Start Training.
    - **Expert**: All defaults still pre-filled, but recommendation text remains visible.
13. Theme toggle (dark ↔ light) works in both phases.

## File Plan

### NEW files to create

```
dashboard/components/md_phase_router.py            # Phase router (Configure / Results)
dashboard/components/md_problem_recap.py           # Problem-type recap card with override link
dashboard/components/md_algo_spotlight.py          # Recommended algorithm spotlight card
dashboard/components/md_algo_multiselect.py        # Multi-select dropdown of all algorithms
dashboard/components/md_hp_card.py                 # Single algorithm HP card
dashboard/components/md_hp_panel.py                # Stack of HP cards driven by md_algo_multiselect
dashboard/components/md_validation_grid.py         # Validation method + split + seed
dashboard/components/md_global_chat.py             # Global modeling chat composer
dashboard/components/md_training_status.py         # Live training status strip + cancel button
dashboard/components/md_race_arena.py              # Live race / leaderboard arena
dashboard/components/md_best_spotlight.py          # Best model spotlight + DNA radar
dashboard/components/md_insight_cards.py           # Forecast + Stack insight cards
dashboard/components/md_pareto_chart.py            # Pareto frontier scatter
dashboard/components/md_charts_panel.py            # Charts container (sidebar + main canvas + caption)
dashboard/components/md_charts/                    # 16 individual chart files
    md_chart_loss_curve.py
    md_chart_auc_per_trial.py
    md_chart_learning_curve.py
    md_chart_per_fold_variance.py
    md_chart_hp_importance.py
    md_chart_training_time.py
    md_chart_roc.py
    md_chart_pr.py
    md_chart_confusion.py
    md_chart_calibration.py
    md_chart_lift.py
    md_chart_threshold.py
    md_chart_proba_dist.py
    md_chart_dna_radar.py
    md_chart_speed_vs_acc.py
    md_chart_metric_comparison.py
    md_chart_prediction_agreement.py
    md_chart_statistical_test.py
dashboard/components/md_final_recs.py              # Final recommendations grid (6 cards)
dashboard/components/md_training_log.py            # Streaming training log component
dashboard/components/md_action_bar.py              # Sticky action bar (per-phase variants)
dashboard/components/md_recommend_adapter.py       # Wraps modeling_agent.recommend_algorithm
dashboard/components/md_algo_registry_adapter.py   # Wraps tool_registry.get_models_for_problem_type
dashboard/components/md_hp_schema_adapter.py       # Extracts param schema from sklearn/xgb/lgb estimators
dashboard/components/md_followup_adapter.py        # Wraps followup_agent.handle with intent fallback
dashboard/components/md_training_runner.py         # Background-thread training driver + progress queue
dashboard/components/md_polling.py                 # Streamlit-safe polling helper
```

### MODIFIED files

```
dashboard/pages/05_modeling.py                    # Full rewrite — wires everything together (was 417 lines, will be ~360)
dashboard/utils/shared_css.py                     # Append md-* CSS rules from mockup
dashboard/services/project_service.py             # Add update_modeling_plan(), update_trained_models(), get_modeling_state() helpers
dashboard/components/sidebar_nav.py               # Pipeline stepper: ensure modeling step has the active state when on this page
```

### NOT TOUCHED

```
agents/modeling_agent.py                          # 678 lines — used as-is via adapter
agents/followup_agent.py                          # 358 lines — used as-is via adapter
agents/tools/ml_tools.py                          # 617 lines — used as-is
agents/tools/tool_registry.py                     # 291 lines — used as-is via adapter
agents/orchestrator.py                            # not touched
domains/*.py                                      # not touched
core/state.py, core/graph.py, core/llm_config.py # not touched
evaluation/model_comparator.py                    # used as-is for paired tests
evaluation/bootstrap_ci.py                        # used as-is for CIs
evaluation/domain_metrics.py                      # used as-is
validation/model_validator.py                     # used as-is
explainability/*.py                               # not touched in this handoff
reports/*.py                                      # not touched
```

## Build Order (recommended)

This is a complex tab. Follow this order to keep things sane:

1. **Read all 11 specs end-to-end first.** Do not start coding before you've read every spec — they reference each other.
2. **Phase A — adapters** (`md_recommend_adapter`, `md_algo_registry_adapter`, `md_hp_schema_adapter`, `md_followup_adapter`). These are pure wrappers around existing backend functions, with defensive try/except + fallbacks. Test each adapter in isolation against the existing modules. Spec 11 has the exact function signatures.
3. **Phase B — Configure phase components** (`md_problem_recap`, `md_algo_spotlight`, `md_algo_multiselect`, `md_hp_card`, `md_hp_panel`, `md_validation_grid`, `md_global_chat`, `md_action_bar`). Wire them to a static project fixture first; verify rendering matches the mockup; then wire the adapters in.
4. **Phase C — training runner** (`md_training_runner`, `md_polling`, `md_training_status`). This is the bug fix — the page must actually train. Spec 07 has the full thread/queue/MLflow plumbing.
5. **Phase D — Results phase components** (`md_race_arena`, `md_best_spotlight`, `md_insight_cards`, `md_pareto_chart`, `md_training_log`). Wire to runner output state.
6. **Phase E — charts panel** (`md_charts_panel` + the 16 individual chart files in `md_charts/`). Spec 09 has the full list with backend wiring.
7. **Phase F — final recommendations** (`md_final_recs`). Spec 10 has the rule logic.
8. **Phase G — page integration** (`05_modeling.py` rewrite). Spec 11 has the full page skeleton.
9. **Phase H — service helpers** (`project_service.update_modeling_plan` etc).
10. **Phase I — smoke test**: full pipeline run end-to-end with `titanic.csv`.

## Hard Rules — keep these in your head while coding

1. **CSS prefix**: every selector for this page starts with `.md-`. Do not introduce un-prefixed classes.
2. **Component prefix**: every Python file in `dashboard/components/` for this page starts with `md_`. Function names follow `render_md_<thing>(...)`.
3. **Adapter rule**: if the backend module doesn't have what you need, write an adapter shim. Never edit the backend.
4. **No backend in the page file**: `05_modeling.py` should only call adapter functions and component renderers. No direct `from agents.modeling_agent import ...` — go through the adapter.
5. **State object**: build the `state` dict once at the top of the page from the active project + session state, then pass everywhere. Don't rebuild it inside components.
6. **Threading**: use Python's `threading.Thread` (not `multiprocessing` — Streamlit doesn't support it well). Never block Streamlit's main thread on training. The runner pushes progress dicts onto a `queue.Queue`.
7. **MLflow**: every training run gets its own MLflow run under the project's experiment. The `run_id` is saved into `state["trained_models"][algo_name]`.
8. **Reproducibility**: every random call must take `seed` from section 03.
9. **Algorithm registry is the source of truth**: never hardcode algorithm lists.
10. **Hyperparameter schema is the source of truth**: 9 templated cards + introspection fallback for everything else.
11. **Mode behavior** must match spec 11 exactly.
12. **Theme**: dark / light both must work.

## Smoke Test (run after build)

```bash
cd dashboard && streamlit run app.py
```

Then in browser:

1. Login → Upload `data/samples/titanic.csv` → Configure (Healthcare domain, target=Survived, Guided mode) → run EDA → Approve & Continue from FE → land on Modeling tab.
2. Verify Phase 1 renders fully: problem-type recap; XGBoost spotlight; multi-select shows 4 pre-checked; 4 HP cards visible (XGBoost open by default); validation tip; chat composer.
3. Open the multi-select; uncheck RandomForest; verify the RandomForest HP card disappears immediately. Check CatBoost; verify a CatBoost HP card appears with all hyperparameters templated.
4. Click "All hyperparameters · 14 more" on XGBoost; verify all extra params render with their default values.
5. Click Start Training. Verify Phase 2 renders fully — no blank "Connect the Modeling Agent" placeholder. Race arena populates as models finish. Training log streams. MLflow run IDs appear.
6. While training, click Cancel; verify training stops gracefully and the rest of Phase 2 still renders with whatever finished.
7. Click Continue to Explainability; verify routing works and `project.modeling_done = True`.
8. Re-run the same dataset with `random_seed = 42` (default) twice; verify the leaderboard is byte-identical.
9. Switch to Auto mode → verify Modeling page lands directly on Phase 2 with training in progress (no Configure step).
10. Switch theme dark↔light in both phases; verify no color leaks.

If any of these fails, do NOT consider the handoff done. Pause and fix.

## Reference

- `reference/modeling_mockup.html` — the visual target (~2000 lines, fully approved)
- The 5 prior handoff bundles for the established shell pattern (sidebar, topbar, hero, sections, action bar, theme toggle).

---

When in doubt, **read the mockup**. The HTML/CSS/JS in `reference/modeling_mockup.html` is the source of truth for visuals. The specs are the source of truth for backend wiring. The two together fully define the feature.
