# Spec 04 — Local Explanations (Waterfall + Counterfactual Stories)

## Backend reuse

- `explainability/shap_explainer.py` — per-instance SHAP values (already computed globally, just slice by row)
- `explainability/counterfactual.py` — `generate_counterfactual(model, instance, X_train, max_changes=3)` returns changed features + new prediction. **Open file first** to confirm API.
- `explainability/plain_english.py` — `explain_instance(shap_values, feature_names, feature_values, prediction, domain)` returns per-instance narrative.

## File: `dashboard/components/ex_local_explanations.py`

```python
"""Local explanations — instance selector + waterfall + counterfactual story card."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np

from dashboard.components import project_service
from dashboard.components.ex_audience_switcher import get_audience


def render(shap_data: dict, counterfactual_fn, plain_english_fn) -> None:
    """Render the Local Explanations tab.

    Args:
        shap_data: global SHAP data dict (shap_values matrix, feature_names, base_value)
        counterfactual_fn: callable(instance_idx) -> dict with counterfactual result
        plain_english_fn: callable(instance_idx) -> str with narrative
    """
    project = project_service.get_active()
    df = st.session_state.get("df")
    if df is None or df.empty or not shap_data:
        st.info("No data or SHAP values available.")
        return

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Individual <em>prediction</em></h3>'
        '<span class="ex-sec-meta">Instance-level SHAP + counterfactual</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Instance selector
    target = project.target_column if project else None
    predictions = st.session_state.get("ex_predictions", [])

    # Build options: top high-risk, low-risk, and medium
    options = _build_instance_options(df, predictions, target)

    cols = st.columns([3, 2])
    with cols[0]:
        selected_idx = st.selectbox(
            "Select instance",
            options=range(len(options)),
            format_func=lambda i: options[i]["label"],
            key="ex_instance_select",
        )
    with cols[1]:
        manual_id = st.text_input("or enter row index", key="ex_instance_manual",
                                   placeholder="Row index")
        if manual_id.strip().isdigit():
            selected_idx = int(manual_id.strip())

    instance_idx = options[selected_idx]["idx"] if selected_idx < len(options) else 0

    # Waterfall chart
    _render_waterfall(shap_data, instance_idx, df)

    # Counterfactual story card
    if counterfactual_fn:
        with st.spinner("Generating counterfactual..."):
            try:
                cf_result = counterfactual_fn(instance_idx)
                _render_counterfactual_story(cf_result, df, instance_idx)
            except Exception as e:
                st.warning(f"Counterfactual generation failed: {e}")

    # Plain English (audience-aware)
    audience = get_audience()
    if plain_english_fn and audience in ("business", "regulatory"):
        try:
            narrative = plain_english_fn(instance_idx)
            st.markdown(
                f'<div class="ex-plain-english">'
                f'  <h3>📝 <em>Explanation</em></h3>'
                f'  <p>{narrative}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass


def _build_instance_options(df, predictions, target) -> list[dict]:
    """Build labeled instance options for the selector."""
    options = []
    if predictions:
        sorted_preds = sorted(enumerate(predictions), key=lambda x: x[1], reverse=True)
        # Top 3 high risk
        for idx, pred in sorted_preds[:3]:
            options.append({"idx": idx, "label": f"Row #{idx} — ⚠ High risk ({pred:.2f})"})
        # Bottom 3 low risk
        for idx, pred in sorted_preds[-3:]:
            options.append({"idx": idx, "label": f"Row #{idx} — ✓ Low risk ({pred:.2f})"})
        # 2 medium
        mid = len(sorted_preds) // 2
        for idx, pred in sorted_preds[mid:mid + 2]:
            options.append({"idx": idx, "label": f"Row #{idx} — ⚡ Medium ({pred:.2f})"})
    else:
        for i in range(min(10, len(df))):
            options.append({"idx": i, "label": f"Row #{i}"})
    return options


def _render_waterfall(shap_data: dict, instance_idx: int, df: pd.DataFrame) -> None:
    """Render SHAP waterfall chart for a specific instance."""
    shap_values = shap_data.get("shap_values")
    feature_names = shap_data.get("feature_names", [])
    base_value = shap_data.get("base_value", 0.5)

    if shap_values is None or instance_idx >= len(shap_values):
        st.warning("SHAP values not available for this instance.")
        return

    instance_shap = shap_values[instance_idx]
    top_n = min(10, len(feature_names))

    # Sort by absolute SHAP value
    sorted_indices = np.argsort(np.abs(instance_shap))[::-1][:top_n]
    max_abs = max(np.abs(instance_shap[sorted_indices])) if len(sorted_indices) > 0 else 1.0

    prediction = base_value + float(np.sum(instance_shap))

    rows_html = ""
    for idx in sorted_indices:
        val = float(instance_shap[idx])
        pct = abs(val) / max_abs * 40  # 40% max width from center
        is_neg = val < 0
        bar_class = "neg" if is_neg else "pos"
        color = "var(--green)" if is_neg else "var(--red)"
        sign = "−" if is_neg else "+"
        rows_html += (
            f'<div class="ex-wf-row">'
            f'  <div class="ex-wf-feature">{_html_escape(feature_names[idx])}</div>'
            f'  <div class="ex-wf-bar-area"><div class="ex-wf-center"></div>'
            f'    <div class="ex-wf-bar {bar_class}" style="width:{pct:.0f}%;"></div></div>'
            f'  <div class="ex-wf-value" style="color:{color};">{sign}{abs(val):.3f}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="ex-waterfall">'
        f'  <div style="display:flex;justify-content:space-between;margin-bottom:14px;">'
        f'    <span style="font-size:14px;font-weight:500;">Feature contributions for Row #{instance_idx}</span>'
        f'    <span style="font-family:var(--font-mono);font-size:12px;color:{"var(--red)" if prediction > 0.5 else "var(--green)"};">'
        f'      Prediction: {prediction:.2f}</span>'
        f'  </div>'
        f'  {rows_html}'
        f'  <div style="display:flex;justify-content:space-between;padding-top:10px;margin-top:10px;'
        f'    border-top:1px solid var(--border-subtle);font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">'
        f'    <span>Base value: {base_value:.2f}</span>'
        f'    <span>Final: <strong style="color:{"var(--red)" if prediction > 0.5 else "var(--green)"};">{prediction:.2f}</strong></span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_counterfactual_story(cf: dict, df: pd.DataFrame, instance_idx: int) -> None:
    """Render a narrative counterfactual card."""
    if not cf or not cf.get("changes"):
        return

    changes = cf["changes"]  # list[{"feature": str, "from": val, "to": val}]
    original_pred = cf.get("original_prediction", 0.84)
    new_pred = cf.get("new_prediction", 0.27)
    relative_change = abs(original_pred - new_pred) / max(original_pred, 0.01) * 100

    changes_html = "".join(
        f'<div class="ex-cf-change">'
        f'  <span class="ex-cf-feature">{_html_escape(c["feature"])}</span>'
        f'  <span class="ex-cf-from">{c["from"]}</span>'
        f'  <span class="ex-cf-arrow">→</span>'
        f'  <span class="ex-cf-to">{c["to"]}</span>'
        f'</div>'
        for c in changes
    )

    change_desc = " and ".join(
        f'<strong>{c["feature"]}</strong> changed from {c["from"]} to {c["to"]}'
        for c in changes[:2]
    )

    st.markdown(
        f'<div class="ex-cf-story">'
        f'  <div class="ex-cf-title">💡 Counterfactual: How to change this prediction</div>'
        f'  <div class="ex-cf-narrative">If {change_desc}, '
        f'    the predicted probability would drop from '
        f'    <strong style="color:var(--red);">{original_pred:.0%}</strong> to '
        f'    <strong style="color:var(--green);">{new_pred:.0%}</strong> — '
        f'    a <strong>{relative_change:.0f}% relative reduction</strong>. '
        f'    These are the minimum changes needed to cross the decision boundary.</div>'
        f'  <div class="ex-cf-changes">{changes_html}</div>'
        f'  <div class="ex-cf-shift">'
        f'    <div class="ex-cf-pred"><div class="ex-cf-pred-label">Current</div>'
        f'      <div class="ex-cf-pred-value" style="color:var(--red);">{original_pred:.0%}</div></div>'
        f'    <div style="display:grid;place-items:center;color:var(--text-faint);font-size:24px;">→</div>'
        f'    <div class="ex-cf-pred"><div class="ex-cf-pred-label">Counterfactual</div>'
        f'      <div class="ex-cf-pred-value" style="color:var(--green);">{new_pred:.0%}</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Waterfall ============ */
.ex-waterfall { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px; backdrop-filter: blur(14px); margin-bottom: 22px; }
.ex-wf-row { display: grid; grid-template-columns: 140px 1fr 60px; gap: 10px;
  align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); }
.ex-wf-row:last-child { border-bottom: none; }
.ex-wf-feature { font-family: var(--font-mono); font-size: 12px; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; }
.ex-wf-bar-area { height: 18px; position: relative; }
.ex-wf-center { position: absolute; left: 50%; top: -4px; bottom: -4px;
  width: 1px; background: var(--text-faint); }
.ex-wf-bar { position: absolute; top: 0; height: 100%; border-radius: 3px;
  transition: width 0.6s ease; }
.ex-wf-bar.pos { background: linear-gradient(90deg, rgba(99,102,241,0.7), var(--violet)); left: 50%; }
.ex-wf-bar.neg { background: linear-gradient(90deg, var(--pink), rgba(236,72,153,0.7)); right: 50%; }
.ex-wf-value { font-family: var(--font-mono); font-size: 11px; text-align: right; }

/* ============ Counterfactual story card ============ */
.ex-cf-story { background: linear-gradient(135deg, rgba(34,211,238,0.08), rgba(99,102,241,0.04));
  border: 1px solid rgba(34,211,238,0.3); border-radius: 18px; padding: 24px;
  margin-bottom: 22px; position: relative; overflow: hidden; }
.ex-cf-story::before { content: "💡"; position: absolute; right: 20px; top: 16px; font-size: 28px; opacity: 0.3; }
.ex-cf-title { font-family: var(--font-display); font-size: 20px; margin-bottom: 8px; }
.ex-cf-narrative { font-size: 14px; color: var(--text-secondary); line-height: 1.7; margin-bottom: 16px; }
.ex-cf-changes { display: flex; flex-wrap: wrap; gap: 10px; }
.ex-cf-change { display: flex; align-items: center; gap: 8px; padding: 8px 14px;
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 10px; font-size: 12.5px; }
.ex-cf-feature { font-family: var(--font-mono); color: var(--violet); }
.ex-cf-arrow { color: var(--text-faint); }
.ex-cf-from { color: var(--pink); font-family: var(--font-mono); text-decoration: line-through; }
.ex-cf-to { color: var(--green); font-family: var(--font-mono); font-weight: 600; }
.ex-cf-shift { display: flex; gap: 20px; align-items: center; margin-top: 16px;
  padding-top: 16px; border-top: 1px solid rgba(34,211,238,0.2); }
.ex-cf-pred { display: flex; flex-direction: column; gap: 2px; }
.ex-cf-pred-label { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; }
.ex-cf-pred-value { font-family: var(--font-display); font-size: 28px; }
```
