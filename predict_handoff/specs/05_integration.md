# Spec 05 — Page Integration

## File: `dashboard/pages/07_predict.py` (full rewrite)

```python
"""Predict tab — Single + Batch prediction with SHAP explanations."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

from dashboard.components.pr_mode_tabs import render as render_tabs
from dashboard.components.pr_single_form import render as render_form, build_feature_info
from dashboard.components.pr_result_card import render as render_result
from dashboard.components.pr_batch_upload import render as render_batch_upload
from dashboard.components.pr_batch_results import render as render_batch_results
from dashboard.components.pr_prediction_history import render as render_history, add_to_history
from dashboard.components.pr_api_snippet import render as render_api

st.set_page_config(page_title="AutoDS — Predict", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")
inject_shared_css()

# Gates
if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py"); st.stop()
render_sidebar()
project = project_service.get_active()
if not project:
    st.warning("Open a project first.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

model = st.session_state.get("best_model_object")
if not model:
    st.warning("Train a model first. This page supports batch and single-row predictions with real-time SHAP explanations.")
    if st.button("← Back to Modeling"): st.switch_page("pages/05_modeling.py")
    st.stop()

df = st.session_state.get("df")
target = project.target_column
excluded = project.excluded_columns or []
X_cols = [c for c in df.columns if c != target and c not in excluded] if df is not None else []

# Hero
st.markdown(
    '<section class="pr-hero">'
    '  <div class="pr-eyebrow">🎯 Step 7 of 7 — Predict</div>'
    '  <h1>Make <em>predictions</em> with your model.</h1>'
    '  <p>Single interactive predictions with real-time explanations, or batch predictions from uploaded files.</p>'
    '</section>',
    unsafe_allow_html=True,
)

# Mode tabs
mode = render_tabs()

if mode == "single":
    feature_info = build_feature_info(df, target, excluded)
    values = render_form(feature_info)

    if values:
        with st.spinner("Computing prediction + explanation..."):
            input_df = pd.DataFrame([values])

            # Predict
            try:
                if hasattr(model, "predict_proba"):
                    pred = float(model.predict_proba(input_df[X_cols])[:, 1][0])
                else:
                    pred = float(model.predict(input_df[X_cols])[0])
            except Exception as e:
                st.error(f"Prediction failed: {e}")
                st.stop()

            # SHAP
            shap_vals, feat_names = None, X_cols
            try:
                from explainability.shap_explainer import compute_shap_values
                shap_result = compute_shap_values(model, input_df[X_cols], max_samples=1)
                shap_vals = shap_result.get("shap_values", [None])[0]
                feat_names = shap_result.get("feature_names", X_cols)
            except Exception:
                pass

            # Plain English
            plain = ""
            try:
                from explainability.plain_english import explain_instance
                if shap_vals is not None:
                    plain = explain_instance(shap_vals, feat_names, domain=project.confirmed_domain or "generic")
            except Exception:
                pass

            # Counterfactual
            cf = None
            try:
                from explainability.counterfactual import generate_counterfactual
                cf = generate_counterfactual(model, input_df[X_cols].iloc[0], df[X_cols])
            except Exception:
                pass

            render_result(pred, shap_vals, feat_names, values, plain, cf)

            # Add to history
            summary_parts = [f"{k}={v}" for k, v in list(values.items())[:3]]
            add_to_history(pred, "single", ", ".join(summary_parts))

elif mode == "batch":
    def _run_batch(batch_df):
        with st.spinner(f"Running predictions on {len(batch_df):,} rows..."):
            try:
                if hasattr(model, "predict_proba"):
                    preds = model.predict_proba(batch_df)[:, 1]
                else:
                    preds = model.predict(batch_df)
                result_df = batch_df.copy()
                result_df["prediction"] = preds
                st.session_state["pr_batch_results"] = result_df
            except Exception as e:
                st.error(f"Batch prediction failed: {e}")

    render_batch_upload(X_cols, on_predict=_run_batch)

    if "pr_batch_results" in st.session_state:
        render_batch_results(st.session_state["pr_batch_results"])

# History + API
render_history()
render_api(X_cols)

# Bottom actions
cols = st.columns([1, 1], gap="medium")
with cols[0]:
    if st.button("Continue to Chat →", key="pr_to_chat", type="primary", use_container_width=True):
        project.step_status["predict"] = "done"
        project.step_status["chat"] = "active"
        project_service.update(project)
        st.switch_page("pages/08_chat.py")
with cols[1]:
    if st.button("⬇ Export predictions", key="pr_export", use_container_width=True):
        st.info("Use the CSV download button above for batch results.")
```

## CLAUDE_CODE_PROMPT.md

```
Read predict_handoff/00_START_HERE.md and all specs (01–05) in order.
Open reference/predict_mockup.html as visual target.

BEFORE writing, OPEN: serving/model_loader.py, serving/schemas.py, 
validation/schema_validator.py, explainability/shap_explainer.py,
explainability/plain_english.py, explainability/counterfactual.py.
Adapt component calls if signatures differ.

Build order: spec 01 → 02 → 03 → 04 → 05.

Hard rules: Do NOT modify serving/, explainability/, agents/, etc.
All CSS: pr-* prefix. All components: pr_* prefix. All session keys: pr_*.
Additive CSS only in shared_css.py.

Test: Login → project with model → Predict → Single tab → fill form → Predict button → 
result card with gauge + SHAP + plain English + counterfactual.
Batch tab → upload CSV → validate → Run → results table + risk stratification + download.
History strip shows recent predictions. API snippet shows curl/Python/Docker.
Theme toggle works. pytest passes.
```
