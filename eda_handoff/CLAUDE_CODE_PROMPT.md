# Prompt to give Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The `eda_handoff/` folder must be at the project root.

> **Prerequisites:**
> - Home tab restructure (handoff #1) deployed
> - Upload tab restructure (handoff #2) deployed
> - Configure tab restructure (handoff #3) deployed
>
> Assumes `auth_service.py`, `project_service.py`, `sidebar_nav.py`, cosmic theme tokens in `shared_css.py` are in place. Assumes Configure writes `project.confirmed_domain`, `project.analysis_mode`, `project.problem_type`, `project.target_column`, `project.excluded_columns`, `project.goal`.

---

```
Read the AutoDS EDA restructure handoff in `eda_handoff/` thoroughly before writing any code:

1. Start with eda_handoff/00_START_HERE.md — read all of it.
2. Read every spec file in eda_handoff/specs/ in order (01 → 07).
3. Open eda_handoff/reference/eda_mockup.html in a browser as the visual target. Toggle the Questions / Results buttons in the topbar to view both phases.

Then implement the restructure in this exact build order:

1. eda_handoff/specs/01_two_phase_layout.md
   Create:
     - dashboard/components/ed_phase_router.py
   Add CSS (page chrome, hero, phase toggle pill, fade-up animation) to dashboard/components/shared_css.py.

2. eda_handoff/specs/02_questions_phase.md
   Before writing, OPEN:
     - agents/eda_agent.py — confirm generate_questions() exists and its return shape
     - domains/healthcare.py / finance.py — confirm eda_questions list shape
   Create:
     - dashboard/components/ed_question_card.py
     - dashboard/components/ed_questions_panel.py
   Add CSS (mode pill, question cards, options, recommendations badges).

3. eda_handoff/specs/03_auto_mode.md
   Create:
     - dashboard/components/ed_auto_recommendations.py
   Add CSS (auto block head, recommendation list, accept/skip buttons).

4. eda_handoff/specs/04_results_dashboard.md
   Before writing, OPEN:
     - agents/eda_agent.py — confirm run_analyses() return shape (charts, stats, insights, quality_flags)
     - agents/tools/viz_tools.py / stats_tools.py — confirm chart spec shape
   Create:
     - dashboard/components/ed_insights_summary.py
     - dashboard/components/ed_target_callout.py
     - dashboard/components/ed_featured_chart.py
     - dashboard/components/ed_charts_grid.py
     - dashboard/components/ed_stats_findings.py
     - dashboard/components/ed_quality_flags.py
   If the results shape differs from spec assumptions, create dashboard/components/ed_results_adapter.py — do NOT modify the agent.
   Add CSS (insights summary, sections, target callout, featured heatmap, charts grid, stats table, flag cards).

5. eda_handoff/specs/05_chat_composer.md
   Create:
     - dashboard/components/ed_chat_composer.py
   Add CSS (chat composer, suggestions, send button).

6. eda_handoff/specs/06_filters_and_actions.md
   Create:
     - dashboard/components/ed_filters_bar.py
     - dashboard/components/ed_action_bar.py
   Add CSS (filters bar 3-column, action bar 2-column, run summary card).

7. eda_handoff/specs/07_integration.md
   Add to dashboard/components/project_service.py:
     - eda_completed: bool = False
     - eda_summary: Optional[str] = None
   Rewrite dashboard/pages/03_eda_interactive.py end-to-end using all the new components.
   Wire the run_analysis callback to agents.eda_agent.run_analyses() with appropriate state.
   Wire the chat composer callback to agents.eda_agent.add_followup_analysis() with fallback to agents.followup_agent.handle().

8. Smoke test:
   - streamlit run dashboard/app.py
   - Login → Open existing project at configure step → Start Analysis → land on EDA Phase 1.
   - Phase 1: see mode pill (Guided · Healthcare context), 3 general + 2 healthcare-specific question cards labeled with green Healthcare pill, sticky bottom action bar with answered count.
   - Click Run Analysis → spinner → Phase 2 renders all 6 sections.
   - Phase 2 sections (top to bottom): insights summary → target callout (with imbalance pill if applicable) → featured correlation heatmap → charts grid (2-column) → stats table → quality flags grid → chat composer → filters bar → action bar.
   - Click Continue to Features → routes to feature_engineering page, sidebar shows EDA ✅ Features ⏳.

9. Auto mode test:
   - From Configure, set mode to Auto → Start Analysis → EDA shows the recommendations block with N items, Accept all button, Skip/Accept toggles per row, custom text input.
   - Click Skip on one item → that toggle disables Skip, enables Accept.
   - Click Run Analysis → same Phase 2 result.

10. Chat composer test:
    - In Phase 2, type "Show distribution by gender" + Send → spinner → new chart appears at top of charts grid + new insight at top of insights summary.
    - Click suggestion pill "Survival curves by age" → triggers same flow with canned prompt.

11. Reconfigure test:
    - Click Reconfigure questions in action bar → flips back to Questions phase.
    - Previous answers preserved (cards still show green left bar + checkmark).
    - Click Run Analysis again → Results phase re-renders.

12. Filter test:
    - In Filters bar, uncheck Box plots → charts grid hides box plot tiles.
    - Move Significance slider to 0.10 → stats table shows more rows.
    - Switch Column to "Numeric only" → categorical charts hide.

13. Theme test:
    - Toggle to light mode in either phase.
    - All components render correctly.
    - Heatmap colors stay readable; insight cards have adequate contrast.

14. Regression test:
    - pytest tests/
    - Confirm 920+ passing, 0 failing.
    - If tests/agent/test_eda_decisions.py breaks because the agent state shape changed, fix the test fixture (don't change product code).

Hard rules:
- Do NOT modify anything in agents/, agents/tools/, domains/, core/, data_connectors/, validation/, evaluation/, explainability/, reports/, serving/.
- Do NOT modify other dashboard pages (00_login, app.py, 01_upload, 02_configure, 04–09).
- Do NOT remove or rename any existing CSS variable in shared_css.py — additive only.
- All new CSS rules use the `ed-*` prefix.
- All new component files use the `ed_*` prefix.
- All new session_state keys use the `ed_*` prefix.

Quality bar:
- Module docstring on every new file.
- Type hints throughout.
- Light + dark theme parity verified visually.
- Streamlit reruns are idempotent — no side effects on import.

When finished, report back with:
- Files created and modified.
- pytest output (pass/fail counts).
- Any spec assumption mismatches resolved (e.g., "eda_agent.run_analyses returns a tuple, not a dict — adapted via ed_results_adapter.py").
- Any deviations and the reason.
```

---

## Optional: stage-by-stage runs

Run one spec at a time:

```
Read eda_handoff/00_START_HERE.md and eda_handoff/specs/0X_<spec_name>.md.
Implement only that spec. Run the tests it prescribes.
Report files changed and test results.
Do not touch anything outside the scope of this spec.
```

Replace `0X_<spec_name>` with the spec you want (`01_two_phase_layout`, `02_questions_phase`, etc.).
