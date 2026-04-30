# Spec 09 — Page Integration & Pipeline Wiring

## File: `dashboard/pages/06_explainability.py` (full rewrite)

```python
"""Explainability tab — SHAP, interactions, local, what-if, fairness, model card, calibration.

Surfaces all 9 explainability modules through a tabbed UI with audience switching.
"""
from __future__ import annotations
import time
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

from dashboard.components.ex_audience_switcher import render as render_audience, get_audience
from dashboard.components.ex_section_tabs import render as render_tabs
from dashboard.components.ex_global_shap import render as render_global_shap, render_plain_english
from dashboard.components.ex_interaction_network import render as render_interactions, compute_interactions_from_shap
from dashboard.components.ex_local_explanations import render as render_local
from dashboard.components.ex_whatif_playground import render as render_whatif, build_feature_ranges
from dashboard.components.ex_fairness_audit import render as render_fairness
from dashboard.components.ex_adverse_action import render as render_adverse
from dashboard.components.ex_model_card import render as render_model_card
from dashboard.components.ex_calibration import render as render_calibration
from dashboard.components.ex_chat_composer import render as render_chat
from dashboard.components.ex_action_bar import render as render_actions


st.set_page_config(page_title="AutoDS — Explainability", page_icon="🔍",
                   layout="wide", initial_sidebar_state="expanded")

inject_shared_css()

# ---- gates ----
if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py")
    st.stop()

render_sidebar()

project = project_service.get_active()
if project is None:
    st.warning("Open a project from the home page to continue.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()

# Check for trained model
best_model = st.session_state.get("best_model") or (project.best_model if hasattr(project, "best_model") else None)
if not best_model:
    st.warning("Train models first. This page requires a trained model to generate explainability outputs.")
    if st.button("← Back to Modeling"):
        st.switch_page("pages/05_modeling.py")
    st.stop()


# ---- topbar ----
st.markdown(
    f'<div class="ex-crumbs">'
    f'  <span>{project.name}</span>'
    f'  <span class="sep">/</span>'
    f'  <span class="cur">Explainability</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ---- hero ----
st.markdown(
    '<section class="ex-hero">'
    '  <div class="ex-eyebrow">🔍 Step 6 of 7 — Model Explainability</div>'
    '  <h1>Understand <em>why your model decides.</em></h1>'
    '  <p>SHAP explanations, counterfactual narratives, what-if analysis, fairness audits, and a '
    '     complete model card — all in one place, tailored to your audience.</p>'
    '</section>',
    unsafe_allow_html=True,
)


# ---- compute explainability (if not cached) ----
if "ex_shap_data" not in st.session_state:
    with st.spinner("Computing explainability suite — SHAP, fairness, calibration, model card..."):
        _compute_all()


# ---- audience switcher ----
audience = render_audience()

# ---- section tabs ----
active_tab = render_tabs()

# ---- tab content ----
st.markdown('<div class="ex-tab-content">', unsafe_allow_html=True)

if active_tab == "global":
    render_global_shap(st.session_state.get("ex_shap_data", {}))
    render_plain_english(st.session_state.get("ex_plain_english_text", ""))

elif active_tab == "interactions":
    render_interactions(st.session_state.get("ex_interaction_data", {}))
    render_plain_english(st.session_state.get("ex_interaction_text", ""))

elif active_tab == "local":
    render_local(
        shap_data=st.session_state.get("ex_shap_data", {}),
        counterfactual_fn=_get_counterfactual,
        plain_english_fn=_get_instance_explanation,
    )

elif active_tab == "whatif":
    render_whatif(
        predict_fn=_predict_modified,
        feature_ranges=st.session_state.get("ex_feature_ranges", {}),
    )

elif active_tab == "fairness":
    render_fairness(
        fairness_data=st.session_state.get("ex_fairness_data", {}),
        summary_text=st.session_state.get("ex_fairness_text", ""),
    )
    render_adverse(st.session_state.get("ex_adverse_data", []))

elif active_tab == "card":
    render_model_card(st.session_state.get("ex_model_card", {}))

elif active_tab == "calibration":
    render_calibration(st.session_state.get("ex_calibration_data", {}))

st.markdown('</div>', unsafe_allow_html=True)

# ---- chat + actions ----
render_chat(on_submit=_handle_chat)
render_actions(
    on_continue=_handle_continue,
    on_export_report=_handle_export_report,
    on_export_card=_handle_export_card,
)


# ================================================================ helpers

def _compute_all() -> None:
    """Compute all explainability outputs and cache in session_state."""
    import time
    started = time.time()
    df = st.session_state.get("df")
    model = st.session_state.get("best_model_object")
    target = project.target_column
    domain = project.confirmed_domain or project.detected_domain or "generic"

    if df is None or model is None:
        return

    X = df.drop(columns=[target], errors="ignore") if target else df
    y = df[target] if target and target in df.columns else None

    # SHAP
    try:
        from explainability.shap_explainer import compute_shap_values
        shap_result = compute_shap_values(model, X, max_samples=500)
        st.session_state["ex_shap_data"] = shap_result
        st.session_state["ex_shap_n_samples"] = min(500, len(X))

        # Interaction network from SHAP values
        if "shap_values" in shap_result:
            interaction_data = compute_interactions_from_shap(
                shap_result["shap_values"],
                shap_result["feature_names"],
            )
            st.session_state["ex_interaction_data"] = interaction_data
            st.session_state["ex_n_interactions"] = len(interaction_data.get("edges", []))
    except Exception as e:
        st.warning(f"SHAP computation failed: {e}")

    # Plain English
    try:
        from explainability.plain_english import generate_explanation
        text = generate_explanation(
            st.session_state.get("ex_shap_data", {}),
            domain=domain, audience="technical",
        )
        st.session_state["ex_plain_english_text"] = text
    except Exception:
        st.session_state["ex_plain_english_text"] = ""

    # Feature ranges for What-If
    feature_names = st.session_state.get("ex_shap_data", {}).get("feature_names", list(X.columns)[:8])
    st.session_state["ex_feature_ranges"] = build_feature_ranges(df, feature_names)

    # Fairness
    try:
        from explainability.fairness_audit import run_fairness_audit
        from domains.domain_registry import DOMAIN_REGISTRY
        domain_cfg = DOMAIN_REGISTRY.get(domain, {})
        protected = domain_cfg.get("fairness", {}).get("protected_attributes", [])
        available = [a for a in protected if a in X.columns]
        if available and y is not None:
            fair_result = run_fairness_audit(model, X, y, available)
            st.session_state["ex_fairness_data"] = fair_result
            st.session_state["ex_n_fair_attrs"] = len(available)
    except Exception as e:
        st.warning(f"Fairness audit failed: {e}")

    # Adverse action (finance only)
    if domain == "finance":
        try:
            from explainability.adverse_action import generate_adverse_action
            adverse = generate_adverse_action(model, X.iloc[0], list(X.columns))
            st.session_state["ex_adverse_data"] = adverse
        except Exception:
            pass

    # Model card
    try:
        from explainability.model_card_generator import generate_model_card
        card = generate_model_card(model, X, y, domain_config=DOMAIN_REGISTRY.get(domain, {}))
        st.session_state["ex_model_card"] = card
    except Exception as e:
        st.warning(f"Model card generation failed: {e}")

    # Calibration
    try:
        from explainability.calibration import compute_calibration
        if y is not None:
            cal = compute_calibration(model, X, y)
            st.session_state["ex_calibration_data"] = cal
    except Exception as e:
        st.warning(f"Calibration failed: {e}")

    # Predictions for instance selector
    try:
        preds = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else model.predict(X)
        st.session_state["ex_predictions"] = preds.tolist()
        st.session_state["ex_baseline_pred"] = float(preds[0])
    except Exception:
        pass

    elapsed = time.time() - started
    m, s = divmod(int(elapsed), 60)
    st.session_state["ex_runtime_str"] = f"{m} min {s:02d} s" if m else f"{s} s"
    st.session_state["ex_cost_str"] = "~$0.12"

    # Update project
    project.step_status["explainability"] = "done"
    project.step_status["predict"] = "active"
    project_service.update(project)


def _get_counterfactual(instance_idx: int) -> dict:
    try:
        from explainability.counterfactual import generate_counterfactual
        model = st.session_state.get("best_model_object")
        df = st.session_state.get("df")
        target = project.target_column
        X = df.drop(columns=[target], errors="ignore") if target else df
        return generate_counterfactual(model, X.iloc[instance_idx], X)
    except Exception as e:
        return {"changes": [], "error": str(e)}


def _get_instance_explanation(instance_idx: int) -> str:
    try:
        from explainability.plain_english import explain_instance
        shap_data = st.session_state.get("ex_shap_data", {})
        return explain_instance(
            shap_data.get("shap_values", [])[instance_idx],
            shap_data.get("feature_names", []),
            domain=project.confirmed_domain or "generic",
        )
    except Exception:
        return ""


def _predict_modified(modifications: dict) -> float:
    try:
        from explainability.what_if import predict_modified
        model = st.session_state.get("best_model_object")
        baseline_idx = st.session_state.get("ex_instance_select", 0)
        df = st.session_state.get("df")
        target = project.target_column
        X = df.drop(columns=[target], errors="ignore") if target else df
        return predict_modified(model, X.iloc[baseline_idx], modifications)
    except Exception:
        return st.session_state.get("ex_baseline_pred", 0.5)


def _handle_chat(prompt: str) -> None:
    try:
        from agents.explainability_agent import handle_followup
        result = handle_followup(prompt, st.session_state.get("ex_shap_data", {}))
        if result:
            st.success(f"Analysis added: {prompt[:60]}")
    except Exception:
        try:
            from agents.followup_agent import handle
            handle(prompt, context="explainability")
        except Exception as e:
            st.warning(f"Follow-up not wired: {e}")


def _handle_continue() -> None:
    st.switch_page("pages/07_predict.py")


def _handle_export_report() -> None:
    try:
        from agents.report_agent import generate_explainability_report
        path = generate_explainability_report(st.session_state)
        st.success(f"Report exported to {path}")
    except Exception as e:
        st.warning(f"Export not wired yet: {e}")


def _handle_export_card() -> None:
    try:
        from explainability.model_card_generator import export_markdown
        md = export_markdown(st.session_state.get("ex_model_card", {}))
        st.download_button("Download model card", md, file_name="model_card.md", mime="text/markdown")
    except Exception as e:
        st.warning(f"Model card export not wired: {e}")
```

## `project_service.py` additions

```python
@dataclass
class Project:
    # ... existing fields ...
    best_model: Optional[str] = None
    best_model_path: Optional[str] = None
    explainability_completed: bool = False
```

## Pipeline state flow

| When | What is written |
|---|---|
| Page loads + no cached data | `_compute_all()` runs: SHAP, interactions, fairness, calibration, model card, predictions cached in `ex_*` session_state keys |
| User switches audience | `ex_audience` in session_state — components adapt their language |
| User switches tab | `ex_section` in session_state — different tab panel renders |
| User selects instance (Local tab) | `ex_instance_select` — triggers per-instance SHAP + counterfactual |
| User drags What-If slider | Modifications dict → `_predict_modified()` → gauge updates |
| User submits chat | `_handle_chat()` → explainability_agent or followup_agent |
| User clicks Continue | `step_status["explainability"]=done`, `step_status["predict"]=active` → route to predict page |

## Test plan

1. **Smoke test:** Modeling done → navigate to Explainability → spinner ("Computing explainability suite...") → 7 tabs populated.
2. **Audience test:** switch Technical → Business → labels change (SHAP values → importance scores, p-values hidden). Switch to Regulatory → model card tab auto-highlights.
3. **Global SHAP:** bar chart shows ranked features + plain English card.
4. **Interaction network:** SVG nodes with glowing edges. Top features have biggest nodes.
5. **Local:** pick a high-risk patient → waterfall shows per-feature contributions → counterfactual story card appears with narrative + change pills + before/after.
6. **What-If:** drag charlson_score slider down → gauge smoothly drops, class label changes from High to Medium.
7. **Fairness:** 3 metric cards with pass/fail pills. Healthcare shows HIPAA note. Finance shows adverse action reasons.
8. **Model card:** full document renders with Overview / Use / Ethics / Data.
9. **Calibration:** reliability diagram SVG + 4 metric cards (ECE, Brier, MCE, HL).
10. **Chat:** type "Show PDP for age" → sends to agent.
11. **Continue:** routes to Predict, sidebar updates.
12. **Theme:** all 7 tabs render correctly in light mode.
13. **Regression:** `pytest tests/` passes.

## Final reminder

Do NOT modify: `explainability/**`, `agents/**`, `domains/**`, `evaluation/**`, etc.

If backend APIs differ, write adapters in `dashboard/components/ex_*_adapter.py`.
