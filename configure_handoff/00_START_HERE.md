# AutoDS Configure Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_layout_and_recap.md` → `specs/02_domain_with_explainability.md` → `specs/03_mode_with_unsure_helper.md` → `specs/04_problem_target_goal.md` → `specs/05_excluded_columns.md` → `specs/06_summary_panel.md` → `specs/07_integration.md` → `reference/configure_mockup.html` (visual target).

---

## Goal

Replace `dashboard/pages/02_configure.py` with a redesigned Configure page that:

- Uses a **two-column layout** — main scrolling form on the left, sticky **Analysis Plan** summary card on the right that updates live
- Shows **domain cards** (7 cards instead of dropdown) with **explainability** ("Why was Healthcare detected?" — top 3 column-name signals with confidence bars)
- Auto-shows **compliance notice** for sensitive domains (Healthcare / Finance / HR)
- Replaces the analysis mode flashcards with cards that **explain what each does + estimated time + estimated prompts**
- For **Auto mode**, reveals an **"I'm not sure"** quick-goal chip group that pre-fills target + problem type + goal in one click (because many users picking Auto don't know what they want)
- Replaces problem-type dropdown with **6 pills** (Classification / Regression / Clustering / Time Series / Survival / Anomaly Detection)
- Adds a **dataset recap strip** so user has context without flipping to upload
- Adds an **excluded columns** multi-select with **auto-suggestions** (PII / IDs / constants / leakage) pre-checked
- Adds a **live pipeline cost/time estimate** in the right-side summary card
- Stays project-aware — reads/writes to active project record

This is **UI/UX refactor only**. All backend code (domain_registry, orchestrator, agents) is reused.

## Prerequisites

- Home tab restructure (handoff #1) **must already be deployed**
- Upload tab restructure (handoff #2) **must already be deployed**

This bundle assumes:
- `dashboard/components/auth_service.py`, `project_service.py`, `sidebar_nav.py` exist
- `shared_css.py` has cosmic theme tokens (`--violet`, `--bg-card`, `--gradient-text`, etc.)
- The previous handoffs added `home-*` and `up-*` CSS prefixes — this bundle uses `cf-*` (configure) prefix to avoid collisions

## Critical Constraints

1. **Do NOT modify** anything in `domains/`, `agents/`, `core/`, `data_connectors/`, `validation/`, `evaluation/`, `explainability/`, `reports/`, `serving/`.
2. **Reuse `domains.domain_registry`** for detection. Iterate through `DOMAIN_REGISTRY` for the 7 domain cards.
3. **Reuse each domain config's metadata** (`display_name`, `icon`, `compliance_notes`, `fairness.required`, etc.) for card labels and the compliance notice.
4. **Reuse `agents.orchestrator`** target detection / problem type inference logic — do not reimplement.
5. **Reuse `dashboard/components/mode_selector.py`** patterns OR replace it; if replacing, keep the old file in place to avoid breaking other potential callers.
6. **Extend `shared_css.py` additively** — all new rules use the `cf-*` prefix.
7. The page must remain **project-aware** — read `project_service.get_active()` at top, redirect home if none, write all selections back to the project on Start.

## What "Done" Looks Like

A user can:

1. Navigate from upload to configure (sidebar Pipeline → Configure with the project active).
2. See a **dataset recap strip** showing filename, rows, cols, missing %, sources joined.
3. See **7 domain cards** with detected domain glowing + a "Detected" badge. Click any to override.
4. Click **"Why [domain]?"** → expander shows top 3 column-name signals with confidence bars.
5. See an auto-revealed **compliance notice** when domain is Healthcare / Finance / HR (cyan card with compliance tags).
6. See **3 mode flashcards** (Auto / Guided "Recommended" / Expert) showing time estimate and prompt count.
7. Click **Auto** → see an **"I'm not sure"** dashed-border block appear with 5 quick-goal chips. Click a chip → target/problem/goal auto-fill.
8. See **6 problem-type pills** with the orchestrator-detected one badged.
9. See target column dropdown (with PHI-flagged columns hidden when domain is sensitive).
10. See goal dropdown (problem-type-aware) + free-text input for custom goals.
11. See **excluded columns** grid with auto-suggested PII / IDs / constants pre-checked. Reasons (PII / ID / CONST) shown as tags.
12. See live **Analysis Plan** card on the right with: domain · mode · problem · target · goal · excluded · compliance — plus a **pipeline estimate** block (charts ~28, models ~7, runtime ~4 min, cost ~$0.18) — and a **Start Analysis** primary CTA.
13. Click "Start Analysis" → project's `step_status["configure"]` becomes `done`, `step_status["eda"]` becomes `active`, page advances to `03_eda_interactive.py`.

## File Plan

### NEW files to create

```
dashboard/components/cf_dataset_recap.py         # Read-only recap strip (rows, cols, missing %, etc.)
dashboard/components/cf_domain_cards.py          # 7 domain cards with detected + override
dashboard/components/cf_domain_why.py            # Explainability panel (top 3 signals)
dashboard/components/cf_compliance_notice.py     # Healthcare/Finance/HR compliance card
dashboard/components/cf_mode_cards.py            # Mode flashcards with time + prompt estimates
dashboard/components/cf_unsure_helper.py         # Auto-mode "I'm not sure" quick-goal chips
dashboard/components/cf_problem_pills.py         # 6 problem-type pills
dashboard/components/cf_target_goal.py           # Target dropdown + goal dropdown + manual input
dashboard/components/cf_excluded_columns.py      # Multi-select with auto-suggestions
dashboard/components/cf_summary_panel.py         # Sticky right-side Analysis Plan card
dashboard/components/cf_pipeline_estimator.py    # Computes charts/models/runtime/cost estimates
```

### Files to MODIFY

```
dashboard/pages/02_configure.py                  # Full rewrite using new components
dashboard/components/shared_css.py               # Add `cf-*` rules (additive only)
dashboard/components/project_service.py          # Add config field setters (excluded_columns, etc.)
```

### Files NOT to touch

- `agents/**`, `domains/**`, `core/**`, `data_connectors/**`
- All other pipeline pages (00_login, app.py, 01_upload, 03–09)
- Existing components: `mode_selector.py`, `domain_badge.py`, `approval_widget.py`, `question_renderer.py` etc. (left as-is for backward compatibility)
- Tests

## Build Order

Each step is independently shippable. Test after each.

1. **`cf_dataset_recap.py`** — read-only recap strip from `project.dataset_*` and `df` shape. Spec 01.
2. **`cf_domain_cards.py` + `cf_domain_why.py`** — 7 cards iterating `DOMAIN_REGISTRY`, with the explainability panel. Spec 02.
3. **`cf_compliance_notice.py`** — auto-shown if domain config has `compliance_notes` or `fairness.required`. Spec 02.
4. **`cf_mode_cards.py`** — 3 flashcards with `mode_estimates` dict (time / prompts). Spec 03.
5. **`cf_unsure_helper.py`** — Auto-mode reveal block with quick-goal chips. Spec 03.
6. **`cf_problem_pills.py` + `cf_target_goal.py`** — replace dropdowns. Spec 04.
7. **`cf_excluded_columns.py`** — auto-detect PII/ID/constant columns + checkbox grid. Spec 05.
8. **`cf_pipeline_estimator.py`** — pure-Python estimator for charts/models/runtime. Spec 06.
9. **`cf_summary_panel.py`** — sticky right-side summary using all the above state. Spec 06.
10. **Rewrite `pages/02_configure.py`** — orchestrate all components in two-column layout. Spec 07.
11. **Add CSS** to `shared_css.py` (additive only). Each spec lists its CSS section.
12. **Smoke test** — login → existing project at upload step → click Continue to Configure → run through all sections → click Start Analysis → land on EDA page.
13. **Run pytest** — confirm 920+ passing.

## Visual Reference

`reference/configure_mockup.html` is a self-contained HTML preview of the entire Configure page. Use it as the visual target. **Do NOT import** it into Streamlit.

## Handoff Checklist

After implementation:

- [ ] `streamlit run dashboard/app.py` boots without errors
- [ ] Configure page renders in two columns at desktop, single column at <1100px
- [ ] Dataset recap strip shows correct values from current project + df
- [ ] All 7 domain cards render. Detected domain has the badge + glow
- [ ] Clicking a domain card updates the right-side Analysis Plan panel immediately
- [ ] "Why [domain]?" expander shows top 3 column-name signals with confidence bars
- [ ] Compliance notice appears only for Healthcare / Finance / HR (sourced from each domain config's `compliance_notes`)
- [ ] Mode flashcards show correct estimates (Auto: ~2 min/0 prompts, Guided: ~5 min/~7 prompts, Expert: ~15 min/~20 prompts)
- [ ] Selecting Auto reveals the "I'm not sure" block; selecting any other mode hides it
- [ ] Quick-goal chips, when clicked, auto-fill target + problem + goal
- [ ] Problem-type pills show 6 options with detected one badged
- [ ] Target dropdown excludes PHI-flagged columns when domain is sensitive
- [ ] Excluded columns grid pre-checks PII/ID/constant columns; "X of Y will be analyzed" updates live
- [ ] Right-side Analysis Plan updates live as user changes any selection
- [ ] Pipeline estimate updates correctly (model count, runtime, cost) based on mode + excluded columns
- [ ] "Start Analysis" disabled until target+problem are valid; on click, project step_status updates and routes to EDA
- [ ] Theme toggle (dark ↔ light) works; all components render correctly in both
- [ ] No light-mode color leaks
- [ ] `pytest tests/` passes
