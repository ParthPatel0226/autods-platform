# Prompt to give Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The `fe_handoff/` folder must be at the project root (next to `handoff/`, `upload_handoff/`, `configure_handoff/`, `eda_handoff/`).

> **Prerequisites:**
> - Home tab restructure (handoff #1) deployed
> - Upload tab restructure (handoff #2) deployed
> - Configure tab restructure (handoff #3) deployed
> - EDA tab restructure (handoff #4) deployed
>
> This bundle assumes `auth_service.py`, `project_service.py`, `sidebar_nav.py`, and the cosmic theme tokens in `shared_css.py` are in place. It also assumes the EDA page wrote `project.eda_done = True` and pushed the working dataset into `st.session_state["df"]`.

---

```
Read the AutoDS Feature Engineering restructure handoff in `fe_handoff/` thoroughly before writing any code:

1. Start with fe_handoff/00_START_HERE.md — read all of it.
2. Read every spec file in fe_handoff/specs/ in order (01 → 08).
3. Open fe_handoff/reference/feature_eng_mockup.html in a browser as the visual target.

Then implement the restructure in this exact build order:

1. fe_handoff/specs/01_two_phase_layout.md
   Create:
     - dashboard/components/fe_phase_router.py
     - dashboard/components/fe_dataset_recap.py
   Add the matching CSS rules from spec 01 to dashboard/components/shared_css.py
   (additive only — do NOT remove or modify any existing rule).

2. fe_handoff/specs/02_per_column_decisions.md
   Before writing the column accordion, OPEN:
     - agents/feature_engineer.py — confirm if `recommend_choices(df, project)` exists
     - agents/tools/feature_tools.py — confirm imputation/encoding/scaling/outlier function names
   If recommend_choices doesn't exist, the local `_fallback_recommendations` covers it.
   Create:
     - dashboard/components/fe_quick_actions.py
     - dashboard/components/fe_filter_bar.py
     - dashboard/components/fe_column_card.py
     - dashboard/components/fe_columns_panel.py
   Add CSS from spec 02.

3. fe_handoff/specs/03_domain_features.md
   Before writing, OPEN:
     - domains/healthcare.py / finance.py / etc. — find the actual attribute name
       (`feature_questions`, `feature_options`, or `FEATURES`)
     - confirm each entry's keys (name, description, required_columns, default_on)
   If the shape differs, write dashboard/components/fe_domain_adapter.py to normalize it.
   Create:
     - dashboard/components/fe_domain_features.py
   Add CSS from spec 03.

4. fe_handoff/specs/04_custom_builder.md
   Create:
     - dashboard/components/fe_custom_builder.py
   Add CSS from spec 04.

5. fe_handoff/specs/05_interaction_features.md
   Before writing, OPEN agents/feature_engineer.py — confirm if `suggest_interactions(df, project)`
   exists. If not, the local `_fallback_suggestions` covers it.
   Create:
     - dashboard/components/fe_interaction_features.py
   No new CSS (reuses .fe-feat from spec 03).

6. fe_handoff/specs/06_global_chat_composer.md
   Before writing, OPEN agents/followup_agent.py — confirm `handle(intent=...)` signature.
   If `intent="modify_fe_plan"` isn't yet supported, the try/except catches it gracefully.
   Create:
     - dashboard/components/fe_global_chat.py
     - dashboard/components/fe_action_bar.py
   Add CSS from spec 06.

7. fe_handoff/specs/07_review_phase.md
   Before writing, OPEN agents/feature_engineer.py — confirm `execute_choices(df, plan, project)`
   exists. If not, write dashboard/components/fe_engineer_adapter.py that iterates the plan
   and calls the right feature_tools functions.
   Create:
     - dashboard/components/fe_review_shape.py
     - dashboard/components/fe_review_diff.py
     - dashboard/components/fe_review_new_features.py
     - dashboard/components/fe_review_dropped.py
     - dashboard/components/fe_review_action_bar.py
   Add CSS from spec 07.

8. fe_handoff/specs/08_integration.md
   Rewrite dashboard/pages/04_feature_engineering.py end-to-end using the new components.
   Add `update_fe_plan` helper to dashboard/components/project_service.py.

After implementation:

- Run `streamlit run dashboard/app.py` and walk through the smoke-test sequence in spec 08.
- Run `pytest tests/` and confirm 920+ tests pass. If a test breaks because it
  doesn't seed an active project, fix the test fixture — NOT the product code.
- Verify visually against fe_handoff/reference/feature_eng_mockup.html.

CRITICAL CONSTRAINTS:
- Do NOT modify anything in agents/, agents/tools/, domains/, core/, data_connectors/,
  validation/, evaluation/, explainability/, reports/, serving/.
- Do NOT modify any existing CSS rule in shared_css.py — only ADD `fe-*` rules.
- Do NOT modify other dashboard pages (00_login, app.py, 01_upload, 02_configure,
  03_eda_interactive, 05_modeling, 06_explainability, 07_predict, 08_chat, 09_download).
- Do NOT modify existing components (mode_selector.py, domain_badge.py, question_renderer.py).
- All new components use the `fe_*` Python prefix and `fe-*` CSS prefix.
- All adapter shims live in dashboard/components/fe_*_adapter.py — never edit the backend.

Verify before changing:
- agents.feature_engineer.recommend_choices / suggest_interactions / execute_choices signatures
- agents.followup_agent.handle intent support
- domains.<domain>.feature_questions shape

If those interfaces don't match, write an adapter — never modify the backend module.
```
