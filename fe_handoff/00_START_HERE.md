# AutoDS Feature Engineering Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_two_phase_layout.md` → `specs/02_per_column_decisions.md` → `specs/03_domain_features.md` → `specs/04_custom_builder.md` → `specs/05_interaction_features.md` → `specs/06_global_chat_composer.md` → `specs/07_review_phase.md` → `specs/08_integration.md` → `reference/feature_eng_mockup.html` (visual target — already approved).

---

## Goal

Replace `dashboard/pages/04_feature_engineering.py` with a redesigned Feature Engineering page that:

- Uses a **two-phase split** — **Configure** (sections 01–04 + global chat composer) and **Review & Approve** (output shape, diff table, new features, dropped, AI reasoning), toggled in the topbar
- Replaces the flat dropdown-spreadsheet table with a **column accordion** — each column is a clickable card with collapsed pills (imputation / encoding / scaling / outliers) and an expanded detail pane with 4 dropdowns + per-column AI reasoning
- Shows **domain-specific features** as toggle cards with requirement status (green = met, amber = missing) — sourced from `domains/<domain>.py`'s `feature_questions` list
- Adds a **custom feature builder** (name + expression) for user-defined derived columns
- Adds **interaction features** as AI-suggested toggle cards (Age × Pclass, Sex × Pclass, etc.)
- Adds a **global FE chat composer** at the bottom of the Interaction Features section — open-ended AI request that updates the entire plan ("use KNN imputation for all numeric columns", "drop columns with >50% missing")
- Includes the **dataset recap strip** (matches Configure / EDA pattern)
- Renders fully in the **cosmic theme** (Instrument Serif headlines with `<em>` gradient italic, Inter Tight body, JetBrains Mono labels, glass cards, starfield, auroras)

This is **UI/UX refactor only**. Backend (`feature_engineer`, `feature_tools`, `domain_registry`, `followup_agent`) is reused.

## Prerequisites

- Home tab (handoff #1) deployed
- Upload tab (handoff #2) deployed
- Configure tab (handoff #3) deployed
- EDA tab (handoff #4) deployed

This bundle assumes:

- `auth_service.py`, `project_service.py`, `sidebar_nav.py`, `shared_css.py` are in place
- The previous handoffs use `home-*`, `up-*`, `cf-*`, `ed-*` CSS prefixes — this bundle uses `fe-*`
- The EDA page wrote `project.eda_done = True` and pushed the working dataset into `st.session_state["df"]`
- The Configure page wrote `project.target_column`, `project.confirmed_domain`, `project.analysis_mode`, `project.problem_type`, `project.excluded_columns` into the project record

## Critical Constraints

1. **Do NOT modify** anything in `agents/` (especially `feature_engineer.py`), `agents/tools/feature_tools.py`, `agents/followup_agent.py`, `domains/`, `core/`, `data_connectors/`, `validation/`, `evaluation/`, `explainability/`, `reports/`, `serving/`.
2. **Reuse `agents.feature_engineer`** for question generation and decision execution. The component layer wraps it — does not reimplement the per-column decision logic.
3. **Reuse `agents.tools.feature_tools`** for the actual transformation functions. The component layer only renders the choices; execution stays in the agent.
4. **Reuse `domains/<domain>.py`'s `feature_questions`** list for domain-specific feature toggle cards. Each entry should have `name`, `description`, `required_columns`, and (optionally) `display_only` to skip showing the user.
5. **Reuse `agents.followup_agent.handle`** for the global chat composer's AI requests — same pattern as the EDA tab.
6. **Extend `shared_css.py` additively** with `fe-*` prefix. Never remove or modify existing rules.
7. The page must remain **project-aware** — read active project at top, redirect to `app.py` if none, write all selections + plan back to the project.

## What "Done" Looks Like

A user can:

1. Land on Feature Engineering after EDA → see **Phase 1 — Configure** with the dataset recap strip + mode pill at the top.
2. See **Section 01 — Per-column transformations**: quick-action mono pills (★ Auto-fill all / ↻ Reset / ◉ Show only missing / ⊘ Mark IDs for drop), search input, filter chips, a list of column accordion cards.
3. Each column accordion shows: column name, type badge (color-coded by dtype), missing %, decision pills. The target column is marked with a purple left border + `★ TARGET` badge.
4. Click a column card → expands to reveal 4 dropdowns (imputation / encoding / scaling / outliers) with "★ Recommended" hints and a column-level AI reasoning box.
5. **Section 02 — Domain-specific features**: cards with toggle switches, green "requirements met" or amber "not found" indicators, descriptions explaining the feature's clinical/financial/etc. value. Includes a scoped AI composer at the bottom for adding domain features.
6. **Section 03 — Custom derived features**: dashed-border builder card with name + expression form (e.g., `Fare / (SibSp + Parch + 1)`).
7. **Section 04 — Interaction features**: AI-suggested feature crosses (Age × Pclass, Sex × Pclass, is_alone) with toggle switches.
8. **Section 04 → bottom**: Global chat composer ("Anything else for *feature engineering?*") with subtitle, input + Send, and 4 suggestion pills. Sending a message routes through `followup_agent.handle` and updates the plan.
9. **Sticky action bar** at the bottom: "11 of 12 columns configured · 6 new features queued · est ~30s" + Back to EDA + Review & Approve.
10. Clicking **Review & Approve** transitions to **Phase 2 — Review** without re-running anything yet.
11. Phase 2 sequence: Output shape stat cards → Column transformations diff table → New features (green pills with origin tags) → Columns dropped (red pills with reasons) → AI reasoning expandable → action bar.
12. Click **Modify** → returns to Phase 1 with answers preserved.
13. Click **Approve & Continue to Modeling** → executes `feature_engineer.execute_choices(project)`, advances `step_status["features"]=done`, `step_status["modeling"]=active`, routes to `05_modeling.py`.
14. Auto mode pre-fills all decisions and shows "Approve all" prominently. Guided mode highlights AI recommendations. Expert mode leaves dropdowns blank.
15. Theme toggle (dark ↔ light) works in both phases. No light-mode color leaks.

## File Plan

### NEW files to create

```
dashboard/components/fe_phase_router.py            # Phase router (Configure / Review)
dashboard/components/fe_dataset_recap.py           # Dataset recap strip (reuse pattern from cf_dataset_recap)
dashboard/components/fe_quick_actions.py           # Auto-fill / Reset / Show only missing / Mark IDs
dashboard/components/fe_filter_bar.py              # Search input + filter chips
dashboard/components/fe_column_card.py             # Single column accordion card
dashboard/components/fe_columns_panel.py           # Stack of column cards + quick actions + filter
dashboard/components/fe_domain_features.py         # Domain feature toggle cards + scoped AI composer
dashboard/components/fe_custom_builder.py          # Custom derived feature form
dashboard/components/fe_interaction_features.py    # AI-suggested interaction toggle cards
dashboard/components/fe_global_chat.py             # Global FE chat composer (the new one at bottom of section 04)
dashboard/components/fe_action_bar.py              # Sticky bottom action bar (configure phase)
dashboard/components/fe_review_shape.py            # Output shape stat cards
dashboard/components/fe_review_diff.py             # Column transformations diff table
dashboard/components/fe_review_new_features.py     # New features green pills
dashboard/components/fe_review_dropped.py          # Dropped columns red pills + AI reasoning
dashboard/components/fe_review_action_bar.py       # Sticky bottom action bar (review phase)
```

### Files to MODIFY

```
dashboard/pages/04_feature_engineering.py          # Full rewrite using new components
dashboard/components/shared_css.py                 # Add `fe-*` rules (additive only)
dashboard/components/project_service.py            # Add fe_choices / fe_state persistence
```

### Files NOT to touch

- `agents/**`, `agents/tools/**`, `domains/**`, `core/**`, `data_connectors/**`
- All other pipeline pages (00_login, app.py, 01_upload, 02_configure, 03_eda_interactive, 05_modeling, 06_explainability, 07_predict, 08_chat, 09_download)
- Existing components: `mode_selector.py`, `domain_badge.py`, `question_renderer.py`, etc.

## Build Order

1. **`fe_phase_router.py`** — phase state in session_state, swap UI. Spec 01.
2. **`fe_dataset_recap.py`** — dataset recap strip. Spec 01.
3. **`fe_quick_actions.py` + `fe_filter_bar.py` + `fe_column_card.py` + `fe_columns_panel.py`** — Section 01 components. Spec 02.
4. **`fe_domain_features.py`** — Section 02 with scoped AI composer. Spec 03.
5. **`fe_custom_builder.py`** — Section 03 custom builder. Spec 04.
6. **`fe_interaction_features.py`** — Section 04 interaction toggles. Spec 05.
7. **`fe_global_chat.py`** — global chat composer at bottom of Section 04. Spec 06.
8. **`fe_action_bar.py`** — sticky bottom action bar (Configure phase). Spec 06.
9. **`fe_review_shape.py`, `fe_review_diff.py`, `fe_review_new_features.py`, `fe_review_dropped.py`, `fe_review_action_bar.py`** — Phase 2 components. Spec 07.
10. **Rewrite `pages/04_feature_engineering.py`** — orchestrate everything. Spec 08.
11. **Add CSS** to `shared_css.py` — additive only. Each spec lists its CSS section.
12. **Smoke test** — Configure → EDA → Run analysis → Continue to Features → expand a column → toggle a domain feature → type into the global chat → Review → Modify → Approve & Continue to Modeling.
13. **Run pytest** — confirm 920+ passing.

## Visual Reference

`reference/feature_eng_mockup.html` is a self-contained HTML preview of both phases with the topbar phase toggle. Use as visual target — **do NOT import** into Streamlit.

## Handoff Checklist

After implementation:

- [ ] `streamlit run dashboard/app.py` boots without errors
- [ ] Navigating from EDA → Features shows Phase 1 — Configure
- [ ] Sidebar pipeline stepper shows Upload ✓ Configure ✓ EDA ✓ Features active
- [ ] Dataset recap strip shows correct values from current project + df
- [ ] Mode pill reflects the project's analysis_mode (Auto / Guided / Expert)
- [ ] Section 01 column accordion: Survived has purple left border + ★ TARGET badge; PassengerId shows "Drop · ID column"; Cabin shows 77.1% missing in red; Age expanded shows 4 dropdowns + reasoning box
- [ ] Quick-action buttons work: Auto-fill, Reset, Show only missing, Mark IDs
- [ ] Filter chips work: All / Numeric / Categorical / Has missing
- [ ] Section 02 domain features: cards rendered from `domains/<domain>.py.feature_questions`; bmi_category disabled with amber missing-columns indicator
- [ ] Section 02 scoped AI composer routes through `followup_agent.handle(intent="add_domain_feature")`
- [ ] Section 03 custom builder validates expression and adds to plan
- [ ] Section 04 interaction features: 3 AI-suggested cards with toggles; "is_alone" off by default
- [ ] **Section 04 → bottom: Global chat composer** renders prominently, has eyebrow + Instrument Serif headline + subtitle + input + Send + 4 suggestion pills
- [ ] Sending a global chat message routes through `followup_agent.handle(intent="modify_fe_plan")` and updates the plan
- [ ] Sticky action bar shows live answered count + estimated runtime + buttons
- [ ] Click Review & Approve → transitions to Phase 2
- [ ] Phase 2 renders: shape cards (891 / 12→18 / 0 missing) → diff table → new features pills → dropped pills → AI reasoning expandable → action bar
- [ ] Click Modify → back to Phase 1 with answers preserved
- [ ] Click Approve & Continue → executes `feature_engineer.execute_choices`, advances pipeline state, routes to Modeling
- [ ] Auto / Guided / Expert mode behavior matches spec 02
- [ ] Theme toggle works in both phases
- [ ] No light-mode color leaks
- [ ] `pytest tests/` passes
