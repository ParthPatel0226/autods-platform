# AutoDS EDA Interactive Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_two_phase_layout.md` → `specs/02_questions_phase.md` → `specs/03_auto_mode.md` → `specs/04_results_dashboard.md` → `specs/05_chat_composer.md` → `specs/06_filters_and_actions.md` → `specs/07_integration.md` → `reference/eda_mockup.html` (visual target).

---

## Goal

Replace `dashboard/pages/03_eda_interactive.py` with a redesigned EDA page that splits into **two phases**:

- **Phase 1 — Questions:** numbered cards with general + domain-specific questions, custom follow-up inputs, sticky bottom action bar with **Run Analysis**.
- **Phase 2 — Results dashboard:** insights summary at top, target distribution callout, featured correlation heatmap, charts grid, statistical findings table, quality flags, then a **generalized chat composer** for follow-ups, filters bar, and a 2-column action bar at the bottom.

Auto mode shows compact recommendations (accept-as-batch or override) plus a free-text input. Reconfigure button on Results returns to Questions. Step status updates correctly.

This is **UI/UX refactor only**. Backend (eda_agent, viz_tools, stats_tools, domain_registry) is reused.

## Prerequisites

- Home tab (handoff #1) deployed
- Upload tab (handoff #2) deployed
- Configure tab (handoff #3) deployed

This bundle assumes:
- `auth_service.py`, `project_service.py`, `sidebar_nav.py`, `shared_css.py` are in place
- The Configure page wrote `project.confirmed_domain`, `project.analysis_mode`, `project.problem_type`, `project.target_column`, `project.excluded_columns`, `project.goal` into the project record
- The previous handoffs use `home-*`, `up-*`, `cf-*` CSS prefixes — this bundle uses `ed-*` (EDA) prefix

## Critical Constraints

1. **Do NOT modify** anything in `agents/` (especially `eda_agent.py`), `agents/tools/` (`viz_tools.py`, `stats_tools.py`), `domains/`, `core/`, `data_connectors/`, `validation/`, `evaluation/`, `explainability/`, `reports/`, `serving/`.
2. **Reuse `agents.eda_agent`** for question generation and analysis execution. The component layer wraps it — does not reimplement.
3. **Reuse `agents.tools.viz_tools`** chart generators and `agents.tools.stats_tools` test functions. The results dashboard only renders pre-computed outputs.
4. **Reuse `domains/<domain>.py`'s `eda_questions`** list for domain-specific questions. The component layer iterates them.
5. **Extend `shared_css.py` additively** with `ed-*` prefix.
6. The page must remain **project-aware** — read active project at top, redirect home if none, write all selections + results back to the project.

## What "Done" Looks Like

A user can:

1. Land on EDA after Configure → see **Phase 1 — Questions**.
2. See a mode pill ("Guided Mode · Healthcare context") and a stack of numbered question cards (general + healthcare-specific labeled with green pill).
3. Each question card has options (radio for single-select, checkbox for multi-select), an optional inline tip, and an optional free-text "anything else?" input.
4. Sticky bottom action bar shows answered count + estimated runtime + **Run Analysis** button.
5. **Auto mode** swaps the questions list for a compact recommendations block (accept-all-as-batch button + per-recommendation toggle) plus a "Got an idea?" free-text input.
6. Click **Run Analysis** → page transitions to **Phase 2 — Results**.
7. Results page shows (top to bottom):
   - **Insights summary** — gradient card with 5 LLM-generated takeaways, confidence pills, "Drill into this" links
   - **Target distribution callout** — bar visualization with imbalanced/balanced status
   - **Featured chart** — Pearson correlation heatmap with target row highlighted
   - **Charts grid** — 2-column tiles, each with type pill, mini SVG thumbnail, interpretation caption
   - **Statistical findings table** — test name, p-value (color-coded), effect size, plain-English interpretation
   - **Quality flags grid** — outliers (amber) + modeling red flags (red) side-by-side
   - **Generalized chat composer** — gradient card with one large input + Send button + 4 suggestion pills, used to request more charts/analyses
   - **Filters bar** — full-width 3-column horizontal layout (Chart type · Significance · Column)
   - **Action bar** — full-width 2-column (Next steps card + Run summary card)
8. Click **Reconfigure questions** → return to Phase 1 with answers preserved.
9. Click **Continue to Features** → project's `step_status["eda"]=done`, `step_status["features"]=active`, route to `04_feature_engineering.py`.
10. Send a chat composer message → re-runs analysis with the new question added; results render at the top.

## File Plan

### NEW files to create

```
dashboard/components/ed_phase_router.py            # Switches between Questions and Results phases
dashboard/components/ed_question_card.py           # Single numbered question card
dashboard/components/ed_questions_panel.py         # Stack of cards + sticky action bar
dashboard/components/ed_auto_recommendations.py    # Auto mode recommendation cards
dashboard/components/ed_insights_summary.py        # Top insights summary card
dashboard/components/ed_target_callout.py          # Target distribution callout
dashboard/components/ed_featured_chart.py          # Featured correlation heatmap
dashboard/components/ed_charts_grid.py             # 2-column charts grid
dashboard/components/ed_stats_findings.py          # Statistical findings table
dashboard/components/ed_quality_flags.py           # Outliers + red flags grid
dashboard/components/ed_chat_composer.py           # Generalized follow-up chat input
dashboard/components/ed_filters_bar.py             # Bottom filters bar (3-column)
dashboard/components/ed_action_bar.py              # Bottom action bar (Next steps + Run summary)
```

### Files to MODIFY

```
dashboard/pages/03_eda_interactive.py              # Full rewrite using new components
dashboard/components/shared_css.py                 # Add `ed-*` rules (additive only)
dashboard/components/project_service.py            # Add eda_results / eda_state persistence
```

### Files NOT to touch

- `agents/**`, `agents/tools/**`, `domains/**`, `core/**`, `data_connectors/**`
- All other pipeline pages (00_login, app.py, 01_upload, 02_configure, 04–09)
- Existing components: `mode_selector.py`, `domain_badge.py`, `question_renderer.py`, etc.

## Build Order

1. **`ed_phase_router.py`** — phase state in session_state, swap UI. Spec 01.
2. **`ed_question_card.py` + `ed_questions_panel.py`** — questions phase content. Spec 02.
3. **`ed_auto_recommendations.py`** — auto mode variant. Spec 03.
4. **`ed_insights_summary.py`, `ed_target_callout.py`, `ed_featured_chart.py`, `ed_charts_grid.py`, `ed_stats_findings.py`, `ed_quality_flags.py`** — results dashboard sections. Spec 04.
5. **`ed_chat_composer.py`** — generalized chat input + Send. Spec 05.
6. **`ed_filters_bar.py` + `ed_action_bar.py`** — bottom panels. Spec 06.
7. **Rewrite `pages/03_eda_interactive.py`** — orchestrate everything. Spec 07.
8. **Add CSS** to `shared_css.py` — additive only. Each spec lists its CSS section.
9. **Smoke test** — Configure → EDA → answer questions → Run Analysis → results render → click chat composer with "Show distribution by gender" → re-runs and adds result → Reconfigure → answers preserved → Continue to Features.
10. **Run pytest** — confirm 920+ passing.

## Visual Reference

`reference/eda_mockup.html` is a self-contained HTML preview of both phases. Toggle in the top-right switches phases. Use as visual target — **do NOT import** into Streamlit.

## Handoff Checklist

After implementation:

- [ ] `streamlit run dashboard/app.py` boots without errors
- [ ] Navigating from Configure to EDA shows Phase 1 — Questions
- [ ] Mode pill at top reflects the project's analysis_mode (Guided/Expert)
- [ ] General questions and domain-specific (Healthcare) questions render correctly with proper pills
- [ ] Each question card supports radio (single) or checkbox (multi) options + optional free-text follow-up
- [ ] Sticky bottom action bar shows live answered count + Run Analysis button
- [ ] Auto mode swaps in the recommendations block (accept all or override individually + free-text)
- [ ] Click Run Analysis triggers `eda_agent.run_analyses(...)` and transitions to Phase 2
- [ ] Phase 2 sequence: insights → target callout → featured heatmap → charts grid → stats table → quality flags → chat composer → filters bar → action bar
- [ ] Insight cards show confidence pills, p-values, "Drill into this" links
- [ ] Target callout shows imbalance status correctly
- [ ] Correlation heatmap uses cosmic gradient colors, target row highlighted
- [ ] Charts grid renders 2-column on desktop, 1-column on mobile
- [ ] Stats table color-codes p-values (green / amber / muted)
- [ ] Quality flags split: outliers (amber) + red flags (red)
- [ ] **Chat composer** at the bottom renders prominently with title "Ask for more *charts or analyses.*", subtitle, large input + Send button, suggestion pills
- [ ] Sending a chat message calls `eda_agent.add_followup_analysis(...)` and prepends a new chart/insight to the results
- [ ] Filters bar is full-width 3-column horizontal layout
- [ ] Action bar is 2-column (Next steps + Run summary)
- [ ] Reconfigure preserves question answers
- [ ] Continue to Features advances pipeline state
- [ ] Theme toggle works in both phases
- [ ] No light-mode color leaks
- [ ] `pytest tests/` passes
