# Prompt to give Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The `configure_handoff/` folder must be at the project root.

> **Prerequisites:**
> - Home tab restructure (handoff #1) deployed
> - Upload tab restructure (handoff #2) deployed
>
> This bundle assumes `dashboard/components/auth_service.py`, `project_service.py`, `sidebar_nav.py`, and the cosmic theme tokens in `shared_css.py` are in place. It also assumes the upload page writes `project.dataset_name`, `project.detected_domain`, and `st.session_state["df"]`.

---

```
Read the AutoDS configure restructure handoff in `configure_handoff/` thoroughly before writing any code:

1. Start with configure_handoff/00_START_HERE.md — read all of it.
2. Read every spec file in configure_handoff/specs/ in order (01 → 07).
3. Open configure_handoff/reference/configure_mockup.html in a browser as the visual target.

Then implement the restructure in this exact build order:

1. configure_handoff/specs/01_layout_and_recap.md
   Create:
     - dashboard/components/cf_dataset_recap.py
   Add the matching CSS (hero, crumbs, two-column layout, recap strip, section structure) to dashboard/components/shared_css.py.

2. configure_handoff/specs/02_domain_with_explainability.md
   Before writing, OPEN:
     - domains/domain_registry.py — confirm DOMAIN_REGISTRY shape and detect_domain() return value
     - domains/healthcare.py / finance.py / hr.py — confirm display_name, icon, detection_keywords keys
   If detect_domain() doesn't return per-signal evidence, the why panel re-runs scoring locally — that's fine.
   Create:
     - dashboard/components/cf_domain_cards.py
     - dashboard/components/cf_domain_why.py
     - dashboard/components/cf_compliance_notice.py
   Add CSS (domain cards, why panel, compliance notice).

3. configure_handoff/specs/03_mode_with_unsure_helper.md
   Create:
     - dashboard/components/cf_mode_cards.py
     - dashboard/components/cf_unsure_helper.py
   Add CSS (mode flashcards, unsure block, quick-goal chips).
   Note: Existing dashboard/components/mode_selector.py stays in place — do NOT delete or modify it.

4. configure_handoff/specs/04_problem_target_goal.md
   Create:
     - dashboard/components/cf_problem_pills.py
     - dashboard/components/cf_target_goal.py
   Add CSS (problem pills, form fields, Streamlit selectbox/textinput restyling).

5. configure_handoff/specs/05_excluded_columns.md
   Create:
     - dashboard/components/cf_excluded_columns.py
   Add CSS (column grid, checkboxes, tags, footer).

6. configure_handoff/specs/06_summary_panel.md
   Create:
     - dashboard/components/cf_pipeline_estimator.py
     - dashboard/components/cf_summary_panel.py
   Add CSS (summary panel, estimate block, blocker, Start Analysis button).

7. configure_handoff/specs/07_integration.md
   Add to dashboard/components/project_service.py the new fields:
     - excluded_columns: list[str] = field(default_factory=list)
     - goal: Optional[str] = None
   Rewrite dashboard/pages/02_configure.py end-to-end using all the new components in the two-column layout.

8. Smoke test:
   - streamlit run dashboard/app.py
   - Login → Open existing project at upload step → click Continue to Configure.
   - Verify: dataset recap strip with correct values, 7 domain cards (detected glowing), Why panel toggles, compliance notice for Healthcare/Finance/HR, 3 mode flashcards, problem pills, target/goal, excluded columns with auto-suggestions, sticky right-side summary with live updates and pipeline estimate.
   - Click Start Analysis → routes to EDA page, sidebar shows Configure ✅, EDA ⏳.

9. Auto-unsure test:
   - Click Auto mode → unsure block reveals with 5 quick-goal chips.
   - Click "Predict something specific" → target dropdown selects a boolean column, problem pill jumps to Classification, goal fills in.
   - Click "Find natural groups" → target clears, problem jumps to Clustering.
   - Switch to Guided → unsure block hides cleanly.

10. Resume test:
    - Complete configure, click Start Analysis.
    - Return to home, click the project card.
    - Routes to EDA. Navigate back to Configure.
    - All selections restored from project record (domain, mode, problem, target, goal, excluded).

11. Theme test:
    - Toggle to light mode.
    - All sections render correctly.
    - Domain cards, mode flashcards, problem pills, excluded grid, summary panel — none should have hardcoded dark colors.

12. Regression test:
    - pytest tests/
    - Confirm 920+ passing, 0 failing.
    - If tests/agent/test_profiler_decisions.py or any orchestrator-related test breaks, fix the test fixture (don't change product code).

Hard rules:
- Do NOT modify anything in agents/, domains/, core/, data_connectors/, validation/, evaluation/, explainability/, reports/, serving/.
- Do NOT modify other dashboard pages (00_login, app.py, 01_upload, 03–09).
- Do NOT modify or delete existing components: mode_selector.py, domain_badge.py, approval_widget.py, question_renderer.py, etc. (legacy stays in place for backward compat with other pages).
- Do NOT remove or rename any existing CSS variable in shared_css.py — additive only.
- All new CSS rules use the `cf-*` prefix.
- All new component files use the `cf_*` prefix.
- All new session_state keys use the `cf_*` prefix.

Quality bar:
- Module docstring on every new file.
- Type hints throughout.
- Light + dark theme parity verified visually.
- Streamlit reruns are idempotent — no side effects on import.

When finished, report back with:
- Files created and modified.
- pytest output (pass/fail counts).
- Any spec assumption mismatches resolved (e.g., "DOMAIN_REGISTRY uses 'name' not 'display_name' — adapted").
- Any deviations and the reason.
```

---

## Optional: stage-by-stage

Run one spec at a time:

```
Read configure_handoff/00_START_HERE.md and configure_handoff/specs/0X_<spec_name>.md.
Implement only that spec. Run the tests it prescribes.
Report files changed and test results.
Do not touch anything outside the scope of this spec.
```

Replace `0X_<spec_name>` with the spec you want (`01_layout_and_recap`, `02_domain_with_explainability`, etc.).
