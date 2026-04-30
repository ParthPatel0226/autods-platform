# AutoDS Explainability Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_layout_and_audience.md` → `specs/02_global_shap.md` → `specs/03_interaction_network.md` → `specs/04_local_explanations.md` → `specs/05_whatif_playground.md` → `specs/06_fairness_audit.md` → `specs/07_model_card_calibration.md` → `specs/08_chat_and_actions.md` → `specs/09_integration.md` → `reference/explainability_mockup.html` (visual target).

---

## Goal

Replace the stub `dashboard/pages/06_explainability.py` (currently just shows "Train models first") with the most visually impressive page in the entire app — a full explainability suite with:

- **Audience Switcher** — toggle between Technical / Business / Regulatory views (same data, different language + charts)
- **7 horizontal section tabs:** Global SHAP · Interactions (force-directed network graph) · Local (waterfall + counterfactual story cards) · What-If Playground (live sliders + animated gauge) · Fairness Audit · Model Card · Calibration
- **Generalized chat composer** + bottom action bar

This surfaces all 9 backend explainability modules (`shap_explainer`, `pdp_ice`, `counterfactual`, `fairness_audit`, `model_card_generator`, `plain_english`, `what_if`, `adverse_action`, `calibration`) through a polished UI.

## Prerequisites

- Handoffs #1–6 (Home, Upload, Configure, EDA, Feature Engineering, Modeling) deployed
- A trained model exists in the project (Modeling tab writes `project.best_model`, `project.best_model_path`, `project.model_results`)
- `auth_service.py`, `project_service.py`, `sidebar_nav.py`, `shared_css.py` in place
- Previous handoffs use `home-*`, `up-*`, `cf-*`, `ed-*`, `fe-*`, `md-*` CSS prefixes — this bundle uses `ex-*` (explainability)

## Critical Constraints

1. **Do NOT modify** anything in `explainability/`, `agents/`, `evaluation/`, `domains/`, `core/`, `data_connectors/`, `validation/`, `reports/`, `serving/`.
2. **Reuse all 9 explainability modules:**
   - `explainability/shap_explainer.py` (269 lines) — SHAP global + local
   - `explainability/pdp_ice.py` (251 lines) — PDP + ICE plots
   - `explainability/counterfactual.py` (210 lines) — counterfactual explanations
   - `explainability/fairness_audit.py` (255 lines) — disparate impact, demographic parity
   - `explainability/model_card_generator.py` (364 lines) — Google model card format
   - `explainability/plain_english.py` (211 lines) — natural language explanations
   - `explainability/what_if.py` (147 lines) — interactive what-if analysis
   - `explainability/adverse_action.py` (163 lines) — finance adverse action notices
   - `explainability/calibration.py` (220 lines) — calibration curves + reliability
3. **Reuse `agents/explainability_agent.py`** for orchestrating the explainability pipeline.
4. **Extend `shared_css.py` additively** with `ex-*` prefix.
5. The page must remain **project-aware** — read active project at top, redirect if no trained model, write explainability results back to project.
6. If any backend module has a different API shape than assumed, write an **adapter shim** in `dashboard/components/ex_*_adapter.py` — never modify backend code.

## What "Done" Looks Like

A user can:

1. Land on Explainability after Modeling → see hero + audience switcher + 7 section tabs.
2. Switch audience between Technical / Business / Regulatory — chart labels, summary language, and visible sections adapt.
3. **Global SHAP:** see top-15 SHAP bar chart + plain English summary card.
4. **Interactions:** see a force-directed network graph of feature interactions (nodes sized by importance, edges by interaction strength) + plain English interaction summary.
5. **Local:** pick an instance from a dropdown → see SHAP waterfall chart + counterfactual story card with narrative + change pills + before/after prediction.
6. **What-If:** drag 7 feature sliders → watch an animated prediction gauge smoothly update in real time with class label + delta + percentile.
7. **Fairness:** see 3 fairness metric cards (Disparate Impact, Equal Opportunity, Predictive Parity) with group-level bars + pass/fail pills + domain-aware compliance (HIPAA for healthcare, Fair Lending for finance) + plain English summary.
8. **Model Card:** see auto-generated Google model card rendered as a styled document with Overview / Intended Use / Ethical Considerations / Training Data.
9. **Calibration:** see reliability diagram SVG + 4 calibration metric cards (ECE, Brier, MCE, Hosmer-Lemeshow).
10. Chat composer at bottom for follow-up requests.
11. **Continue to Predict** → `step_status["explainability"]=done`, `step_status["predict"]=active`.

## File Plan

### NEW files to create

```
dashboard/components/ex_audience_switcher.py      # Technical / Business / Regulatory toggle
dashboard/components/ex_section_tabs.py           # 7 horizontal section tab router
dashboard/components/ex_global_shap.py            # SHAP bar chart + plain English
dashboard/components/ex_interaction_network.py    # Force-directed SVG graph (THE CRAZY ONE)
dashboard/components/ex_local_explanations.py     # Instance selector + waterfall + counterfactual story
dashboard/components/ex_whatif_playground.py       # Sliders + animated gauge
dashboard/components/ex_fairness_audit.py         # 3 metric cards + group bars + summary
dashboard/components/ex_adverse_action.py         # Finance-only adverse action reasons
dashboard/components/ex_model_card.py             # Rendered model card document
dashboard/components/ex_calibration.py            # Reliability diagram + metrics
dashboard/components/ex_chat_composer.py          # Generalized chat for explainability
dashboard/components/ex_action_bar.py             # Bottom action bar (Next + summary)
dashboard/components/ex_plain_english.py          # Audience-aware LLM summary renderer
```

### Files to MODIFY

```
dashboard/pages/06_explainability.py              # Full rewrite
dashboard/components/shared_css.py                # Add `ex-*` rules (additive only)
dashboard/components/project_service.py           # Add explainability state fields
```

### Files NOT to touch

- `explainability/**` (all 9 modules)
- `agents/**`, `domains/**`, `core/**`, `data_connectors/**`, `evaluation/**`, `validation/**`, `reports/**`, `serving/**`
- All other dashboard pages
- Existing components

## Build Order

1. **`ex_audience_switcher.py` + `ex_section_tabs.py`** — page chrome. Spec 01.
2. **`ex_global_shap.py` + `ex_plain_english.py`** — Tab 1. Spec 02.
3. **`ex_interaction_network.py`** — Tab 2 (the crazy one). Spec 03.
4. **`ex_local_explanations.py`** — Tab 3 (waterfall + counterfactual stories). Spec 04.
5. **`ex_whatif_playground.py`** — Tab 4 (sliders + gauge). Spec 05.
6. **`ex_fairness_audit.py` + `ex_adverse_action.py`** — Tab 5. Spec 06.
7. **`ex_model_card.py` + `ex_calibration.py`** — Tabs 6-7. Spec 07.
8. **`ex_chat_composer.py` + `ex_action_bar.py`** — bottom. Spec 08.
9. **Rewrite `pages/06_explainability.py`** — orchestrate everything. Spec 09.
10. **Add CSS** to `shared_css.py`. Each spec lists its CSS.
11. **Smoke test** + **pytest**.

## Visual Reference

`reference/explainability_mockup.html` — self-contained HTML with all 7 tabs, audience switcher, interactive What-If sliders + gauge. **Do NOT import** into Streamlit. Visual target only.

## Handoff Checklist

- [ ] Page loads without errors when a trained model exists
- [ ] "Train models first" warning shown gracefully when no model exists
- [ ] Audience switcher toggles between Technical / Business / Regulatory
- [ ] All 7 section tabs switch correctly
- [ ] Global SHAP: bar chart renders from `shap_explainer` data, plain English from `plain_english`
- [ ] Interactions: SVG network graph renders from SHAP interaction values
- [ ] Local: instance selector populates from df rows, waterfall renders per-instance SHAP, counterfactual story from `counterfactual` module
- [ ] What-If: sliders drive `what_if.predict_modified()`, gauge updates smoothly
- [ ] Fairness: metrics from `fairness_audit`, domain-aware (HIPAA/Fair Lending/HR), pass/fail pills correct
- [ ] Adverse action card appears ONLY for Finance domain
- [ ] Model Card: auto-generated from `model_card_generator`, renders as styled document
- [ ] Calibration: reliability diagram + 4 metrics from `calibration` module
- [ ] Chat composer renders with relevant suggestions
- [ ] Continue to Predict advances pipeline state
- [ ] Theme toggle works in all 7 tabs
- [ ] `pytest tests/` passes
