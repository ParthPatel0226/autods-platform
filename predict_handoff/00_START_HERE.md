# AutoDS Predict Tab — Implementation Handoff for Claude Code

> **Read order:** This file → specs 01–05 → `reference/predict_mockup.html`

---

## Goal

Replace the stub `dashboard/pages/07_predict.py` (currently "Train a model first") with a full prediction interface featuring:

- **Two tabs:** Single Prediction (interactive form + instant result) / Batch Prediction (CSV upload + results table)
- **Single prediction:** per-feature form → animated result card with risk gauge + SHAP waterfall + plain English + counterfactual
- **Batch prediction:** file upload → schema validation → results table with download + risk stratification chart
- **Prediction history:** strip of recent single predictions
- **API deployment snippet:** curl/Python code for the FastAPI endpoint (reuse `serving/api.py`)
- **Domain-aware result formatting** (healthcare = clinical risk, finance = adverse action)

CSS prefix: `pr-*`. Backend reuse: `serving/model_loader`, `serving/schemas`, `validation/schema_validator`, `explainability/shap_explainer`, `explainability/plain_english`, `explainability/counterfactual`.

## Prerequisites

Handoffs #1–7 deployed. A trained model exists. `project.step_status["explainability"] == "done"`.

## Critical Constraints

1. **Do NOT modify** `serving/`, `explainability/`, `agents/`, `domains/`, `validation/`, etc.
2. **Reuse `serving/model_loader.load_model()`** for getting the trained model.
3. **Reuse `validation/schema_validator`** for checking prediction input matches training schema.
4. **Reuse `explainability/shap_explainer`** for per-instance explanations on single predictions.
5. **Extend `shared_css.py` additively** with `pr-*` prefix.
6. If backend APIs differ, write adapter shims in `dashboard/components/pr_*_adapter.py`.

## File Plan

### NEW files

```
dashboard/components/pr_mode_tabs.py              # Single / Batch tab switcher
dashboard/components/pr_single_form.py            # Per-feature input form
dashboard/components/pr_result_card.py            # Animated result card (gauge + SHAP + plain English + CF)
dashboard/components/pr_batch_upload.py           # CSV upload + schema validation + run
dashboard/components/pr_batch_results.py          # Results table + download + risk stratification
dashboard/components/pr_prediction_history.py     # Recent predictions strip
dashboard/components/pr_api_snippet.py            # curl/Python deployment code card
dashboard/components/pr_chat_composer.py          # Bottom chat
dashboard/components/pr_action_bar.py             # Bottom actions (Continue to Chat + summary)
```

### Files to MODIFY

```
dashboard/pages/07_predict.py                     # Full rewrite
dashboard/components/shared_css.py                # Add pr-* rules
dashboard/components/project_service.py           # Add prediction_count field
```

## Build Order

1. `pr_mode_tabs.py` — Single / Batch tab switcher (spec 01)
2. `pr_single_form.py` + `pr_result_card.py` — single prediction form + animated result (spec 02)
3. `pr_batch_upload.py` + `pr_batch_results.py` — batch upload + results (spec 03)
4. `pr_prediction_history.py` + `pr_api_snippet.py` — history + API (spec 04)
5. Rewrite `pages/07_predict.py` + chat/actions (spec 05)

## Visual Reference

`reference/predict_mockup.html` — visual target.
