# Claude Code — Implement the AutoDS Modeling Tab

Copy-paste this entire prompt into Claude Code at the AutoDS project root.

---

I'm handing off the **Modeling tab restructure** for AutoDS. Everything you need is in `autods_modeling_handoff/` (unzipped at the project root).

## Read these first, in order

1. `autods_modeling_handoff/00_START_HERE.md` — goals, prerequisites, hard rules, file plan, build order, smoke test
2. `autods_modeling_handoff/specs/01_two_phase_layout.md` — phase router + dataset recap + page chrome
3. `autods_modeling_handoff/specs/02_problem_recap.md` — problem-type recap card
4. `autods_modeling_handoff/specs/03_algorithm_selection.md` — recommended spotlight + multi-select dropdown
5. `autods_modeling_handoff/specs/04_hyperparameter_cards.md` — per-algorithm HP cards (driven by section 01 multi-select)
6. `autods_modeling_handoff/specs/05_validation_strategy.md` — validation method + split + seed
7. `autods_modeling_handoff/specs/06_global_chat_composer.md` — global modeling chat composer
8. `autods_modeling_handoff/specs/07_training_execution.md` — **CRITICAL** — background-thread training + progress queue + MLflow + cancel + the "blank Phase 2" bug fix
9. `autods_modeling_handoff/specs/08_results_phase.md` — race arena, best-model spotlight + DNA radar, insight cards, Pareto frontier, training log
10. `autods_modeling_handoff/specs/09_charts_panel.md` — charts container with sidebar + 16 chart components
11. `autods_modeling_handoff/specs/10_final_recommendations.md` — 6 recommendation cards
12. `autods_modeling_handoff/specs/11_integration.md` — page rewrite, adapters, project_service additions, full smoke test

Then look at `autods_modeling_handoff/reference/modeling_mockup.html` — that's the **approved visual target**. Match it pixel-for-pixel.

## What this is

A **UI/UX refactor + bug fix** of `dashboard/pages/05_modeling.py`. The current page (417 lines) is broken:

- Defaults to clustering algorithms (K-Means, DBSCAN, Hierarchical, Gaussian Mixture) regardless of problem type
- Has a single "Quick search ~5 min" tuning dropdown
- Shows raw HTML code escape bug in the title
- Hangs at "Connect the Modeling Agent to execute training" — never actually trains

The new page is a 2-phase Streamlit page: **Configure** (problem recap → recommended algo + multi-select → per-algorithm HP cards → validation → chat composer → action bar) and **Results** (live race arena → best-model spotlight + DNA radar → insight cards → Pareto frontier → diagnostic charts panel → final recommendations → training log → action bar). The Results phase actually runs training in a background thread and updates live via 2-second polling.

## What you must NOT touch

`agents/`, `agents/tools/`, `domains/`, `core/`, `evaluation/`, `validation/`, `explainability/`, `reports/`, `serving/`, `data_connectors/`. Period.

If a backend function doesn't have what you need, write an **adapter shim** under `dashboard/components/md_*_adapter.py`. The 4 adapters needed are listed in spec 11 with their exact signatures. Each must have try/except fallbacks so the dashboard never crashes if a backend function doesn't exist or changes.

## What you will create

- 30+ new component files under `dashboard/components/` and `dashboard/components/md_charts/`, all prefixed `md_`
- 1 page rewrite: `dashboard/pages/05_modeling.py`
- 1 CSS append to `dashboard/utils/shared_css.py` (~600 lines, all rules prefixed `.md-`, copied verbatim from the mockup's `<style>` block)
- 3 new helpers in `dashboard/services/project_service.py`: `update_modeling_plan(project, plan)`, `update_trained_models(project, results)`, `get_modeling_state(project) -> dict`

## CSS / component prefix

Everything in this tab is prefixed `md_` (Python) and `.md-` (CSS). Do not introduce un-prefixed classes or function names. The mockup's CSS is the source of truth — copy it verbatim into `shared_css.py`.

## Build order (recommended)

1. Read all 11 specs end-to-end. Don't start coding until you've read everything.
2. **Adapters** first (spec 11) — pure wrappers, easy to test in isolation.
3. **Configure-phase components** — wire to a static project fixture, then plug in the adapters.
4. **Training runner** — the bug fix. Spec 07 has the full threading + queue + MLflow plumbing.
5. **Results-phase components** — wire to the runner's output state.
6. **Charts panel** — 16 chart files, each calls into existing `viz_tools` / `evaluation` / `explainability` functions via the adapter.
7. **Final recommendations** — uses `validation/model_validator.py` thresholds + `evaluation/domain_metrics.py` rules.
8. **Page integration** — full rewrite of `05_modeling.py`. Spec 11 has the skeleton.
9. **Smoke test** — exact steps in `00_START_HERE.md` "Smoke Test" section.

## Hard rules

1. CSS prefix `.md-`, Python prefix `md_`. No exceptions.
2. Adapter shims, never backend edits.
3. Algorithm registry is the source of truth — never hardcode algorithm lists.
4. HP schema: 9 templated cards (XGBoost, LogReg, RandomForest, LightGBM, RidgeClassifier, CatBoost, SVM-RBF, KNN, MLP-Tabular) + introspection adapter for everything else (`inspect.signature` on `__init__`).
5. Reproducibility: every random call takes `seed` from section 03. Two runs with seed=42 must produce identical leaderboards.
6. MLflow: every training run gets a `run_id` saved into `state["trained_models"][algo_name]`.
7. Threading: `threading.Thread`, `queue.Queue`, no `multiprocessing`. Polling via `time.sleep(2); st.rerun()`. Never block Streamlit's main thread.
8. Mode behavior: Auto auto-runs on entry. Guided shows recommendations. Expert keeps recommendation text visible.
9. Theme: dark + light both must work. No color leaks.
10. Match the mockup pixel-for-pixel.

## Smoke test (after build)

The detailed list is in `00_START_HERE.md`. Top 5:

1. Land on Modeling after FE → Phase 1 renders fully (recap, spotlight, multi-select, 4 HP cards, validation, chat).
2. Toggle the multi-select; HP cards appear/disappear instantly.
3. Click Start Training → Phase 2 renders fully (no blank placeholder), race arena populates live, MLflow run IDs appear, log streams.
4. Cancel mid-training → completes gracefully with whatever finished.
5. Run twice with seed=42 → leaderboard byte-identical.

If any smoke test fails, do not consider the handoff done. Pause and fix.

## Output

Confirm the smoke test passes with screenshots of:
- Phase 1 rendered with 4 HP cards
- Phase 2 mid-training (race arena live)
- Phase 2 complete (race arena finished + best spotlight + DNA radar + Pareto + a chart selected + final recommendations)

---

Don't paraphrase the specs. Read them, follow them. The mockup HTML is law for visuals. The specs are law for backend wiring. Go.
