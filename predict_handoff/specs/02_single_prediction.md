# Spec 02 — Single Prediction Form + Result Card

## Backend reuse

- `serving/model_loader.py` — `load_model(path)` returns sklearn-compatible model. **Open first.**
- `explainability/shap_explainer.py` — per-instance SHAP values
- `explainability/plain_english.py` — `explain_instance()` for natural language
- `explainability/counterfactual.py` — `generate_counterfactual()` for "what would change this"
- `validation/schema_validator.py` — validates feature dict matches training schema

## File: `dashboard/components/pr_single_form.py`

```python
"""Single prediction form — one input per feature, auto-populated with defaults."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render(feature_info: list[dict]) -> dict | None:
    """Render the input form. Returns feature dict when user clicks Predict, else None.

    Args:
        feature_info: list[{"name": str, "dtype": str, "min": float, "max": float,
                            "median": float, "categories": list[str] | None}]
    """
    st.markdown(
        '<div class="pr-form-header">'
        '<h3 class="pr-form-title">Enter feature values</h3>'
        '<p class="pr-form-sub">Fill in the patient/record details below. Pre-populated with median values.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    values = {}
    # Render in 2-column grid
    cols_per_row = 2
    for i in range(0, len(feature_info), cols_per_row):
        row = feature_info[i:i + cols_per_row]
        st_cols = st.columns(cols_per_row, gap="medium")
        for col, feat in zip(st_cols, row):
            with col:
                if feat.get("categories"):
                    values[feat["name"]] = st.selectbox(
                        feat["name"],
                        options=feat["categories"],
                        index=0,
                        key=f"pr_f_{feat['name']}",
                    )
                elif feat["dtype"] in ("int", "int64"):
                    values[feat["name"]] = st.number_input(
                        feat["name"],
                        min_value=int(feat.get("min", 0)),
                        max_value=int(feat.get("max", 100)),
                        value=int(feat.get("median", feat.get("min", 0))),
                        step=1,
                        key=f"pr_f_{feat['name']}",
                    )
                elif feat["dtype"] in ("float", "float64"):
                    values[feat["name"]] = st.number_input(
                        feat["name"],
                        min_value=float(feat.get("min", 0)),
                        max_value=float(feat.get("max", 100)),
                        value=float(feat.get("median", 0)),
                        step=round((feat.get("max", 100) - feat.get("min", 0)) / 100, 2),
                        key=f"pr_f_{feat['name']}",
                    )
                else:
                    values[feat["name"]] = st.text_input(
                        feat["name"],
                        value=str(feat.get("median", "")),
                        key=f"pr_f_{feat['name']}",
                    )

    # Quick-fill buttons
    quick_cols = st.columns(3)
    with quick_cols[0]:
        if st.button("📋 Fill with medians", key="pr_fill_median", use_container_width=True):
            for feat in feature_info:
                st.session_state[f"pr_f_{feat['name']}"] = feat.get("median", 0)
            st.rerun()
    with quick_cols[1]:
        if st.button("⚠ High-risk example", key="pr_fill_high", use_container_width=True):
            st.session_state["pr_fill_preset"] = "high_risk"
            st.rerun()
    with quick_cols[2]:
        if st.button("✓ Low-risk example", key="pr_fill_low", use_container_width=True):
            st.session_state["pr_fill_preset"] = "low_risk"
            st.rerun()

    # Predict button
    if st.button("🎯 Predict", key="pr_predict_single", type="primary", use_container_width=True):
        return values
    return None


def build_feature_info(df: pd.DataFrame, target: str, excluded: list[str]) -> list[dict]:
    """Build feature metadata from the training dataframe."""
    info = []
    cols = [c for c in df.columns if c != target and c not in (excluded or [])]
    for col in cols:
        s = df[col].dropna()
        entry = {"name": col, "dtype": str(s.dtype)}
        if pd.api.types.is_numeric_dtype(s):
            entry.update({"min": float(s.min()), "max": float(s.max()), "median": float(s.median())})
        elif s.dtype == "object" or pd.api.types.is_categorical_dtype(s):
            cats = s.unique().tolist()
            entry["categories"] = cats[:50]  # limit for UI
            entry["median"] = cats[0] if cats else ""
        else:
            entry["median"] = ""
        info.append(entry)
    return info
```

## File: `dashboard/components/pr_result_card.py`

```python
"""Animated prediction result card — gauge + SHAP + plain English + counterfactual."""
from __future__ import annotations
import streamlit as st
import numpy as np

from dashboard.components import project_service
from domains.domain_registry import DOMAIN_REGISTRY


DOMAIN_RESULT_LABELS = {
    "healthcare": {"high": "⚠ High Clinical Risk", "medium": "⚡ Moderate Risk", "low": "✓ Low Risk"},
    "finance":    {"high": "⚠ High Default Risk",  "medium": "⚡ Moderate Risk", "low": "✓ Low Risk"},
    "hr":         {"high": "⚠ High Attrition Risk", "medium": "⚡ Watch",        "low": "✓ Likely to Stay"},
    "generic":    {"high": "⚠ High Risk",          "medium": "⚡ Medium",        "low": "✓ Low Risk"},
}


def render(prediction: float, shap_values: list | None, feature_names: list[str],
           feature_values: dict, plain_english: str, counterfactual: dict | None) -> None:
    """Render the full result card."""
    project = project_service.get_active()
    domain = (project.confirmed_domain or project.detected_domain or "generic") if project else "generic"
    problem_type = project.problem_type if project else "classification"

    pct = int(prediction * 100) if problem_type == "classification" else None

    st.markdown('<div class="pr-result-card">', unsafe_allow_html=True)

    # ---- Top: prediction + gauge ----
    if pct is not None:
        _render_classification_result(pct, domain)
    else:
        _render_regression_result(prediction, domain)

    # ---- Middle: SHAP waterfall (top 8) ----
    if shap_values is not None and len(shap_values) > 0:
        st.markdown('<div class="pr-result-section">', unsafe_allow_html=True)
        st.markdown('<h4 class="pr-result-section-title">What drove this prediction</h4>', unsafe_allow_html=True)

        sorted_indices = np.argsort(np.abs(shap_values))[::-1][:8]
        max_abs = max(np.abs(shap_values[sorted_indices])) if len(sorted_indices) else 1.0

        for idx in sorted_indices:
            val = float(shap_values[idx])
            pct_bar = abs(val) / max_abs * 40
            is_neg = val < 0
            bar_class = "neg" if is_neg else "pos"
            color = "var(--green)" if is_neg else "var(--red)"
            sign = "−" if is_neg else "+"
            fname = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
            fval = feature_values.get(fname, "—")

            st.markdown(
                f'<div class="pr-wf-row">'
                f'  <div class="pr-wf-feature">{_html_escape(fname)}<span class="pr-wf-val">= {fval}</span></div>'
                f'  <div class="pr-wf-bar-area"><div class="pr-wf-center"></div>'
                f'    <div class="pr-wf-bar {bar_class}" style="width:{pct_bar:.0f}%;"></div></div>'
                f'  <div class="pr-wf-shap" style="color:{color};">{sign}{abs(val):.3f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Plain English ----
    if plain_english:
        st.markdown(
            f'<div class="pr-plain-english">'
            f'  <h4>🧠 In plain English</h4>'
            f'  <p>{plain_english}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---- Counterfactual ----
    if counterfactual and counterfactual.get("changes"):
        changes = counterfactual["changes"]
        orig = counterfactual.get("original_prediction", prediction)
        new = counterfactual.get("new_prediction", 0.0)
        changes_html = " ".join(
            f'<span class="pr-cf-pill">'
            f'<span class="pr-cf-feat">{_html_escape(c["feature"])}</span> '
            f'<span class="pr-cf-from">{c["from"]}</span> → '
            f'<span class="pr-cf-to">{c["to"]}</span></span>'
            for c in changes[:3]
        )
        st.markdown(
            f'<div class="pr-counterfactual">'
            f'  <h4>💡 How to change this outcome</h4>'
            f'  <p>Minimum changes to flip the prediction:</p>'
            f'  <div class="pr-cf-pills">{changes_html}</div>'
            f'  <div class="pr-cf-shift">{orig:.0%} → <strong style="color:var(--green);">{new:.0%}</strong></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def _render_classification_result(pct: int, domain: str) -> None:
    labels = DOMAIN_RESULT_LABELS.get(domain, DOMAIN_RESULT_LABELS["generic"])
    if pct > 60:
        risk_class, risk_color, label = "high", "var(--red)", labels["high"]
    elif pct > 35:
        risk_class, risk_color, label = "medium", "var(--amber)", labels["medium"]
    else:
        risk_class, risk_color, label = "low", "var(--green)", labels["low"]

    arc_length = 251
    offset = arc_length - (pct / 100 * arc_length * 0.84)

    st.markdown(
        f'<div class="pr-result-top">'
        f'  <svg class="pr-gauge" viewBox="0 0 200 120">'
        f'    <defs><linearGradient id="prGaugeG" x1="0" y1="0" x2="1" y2="0">'
        f'      <stop offset="0%" stop-color="#34D399"/><stop offset="50%" stop-color="#FBBF24"/>'
        f'      <stop offset="100%" stop-color="#F87171"/></linearGradient></defs>'
        f'    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(139,92,246,0.08)" stroke-width="12" stroke-linecap="round"/>'
        f'    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#prGaugeG)" stroke-width="12" stroke-linecap="round" '
        f'      stroke-dasharray="{arc_length}" stroke-dashoffset="{offset:.0f}"/>'
        f'  </svg>'
        f'  <div class="pr-result-pct" style="color:{risk_color};">{pct}%</div>'
        f'  <div class="pr-result-label" style="color:{risk_color};">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_regression_result(prediction: float, domain: str) -> None:
    st.markdown(
        f'<div class="pr-result-top">'
        f'  <div class="pr-result-pct" style="color:var(--violet);font-size:52px;">{prediction:.2f}</div>'
        f'  <div class="pr-result-label" style="color:var(--text-muted);">Predicted value</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Single prediction form ============ */
.pr-form-header { margin-bottom: 20px; }
.pr-form-title { font-family: var(--font-display); font-size: 24px; margin-bottom: 4px; }
.pr-form-sub { font-size: 13px; color: var(--text-muted); }

/* ============ Result card ============ */
.pr-result-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 28px; margin-top: 24px;
  backdrop-filter: blur(14px); animation: ex-fadeUp 0.5s ease;
}
.pr-result-top { text-align: center; margin-bottom: 24px; }
.pr-gauge { width: 200px; height: 120px; margin: 0 auto 8px; }
.pr-result-pct { font-family: var(--font-display); font-size: 56px; line-height: 1; }
.pr-result-label { font-size: 16px; font-weight: 500; margin-top: 6px; }

.pr-result-section { margin: 22px 0; padding-top: 20px; border-top: 1px solid var(--border-subtle); }
.pr-result-section-title { font-size: 14px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); }

/* Waterfall rows */
.pr-wf-row { display: grid; grid-template-columns: 180px 1fr 60px; gap: 10px;
  align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); }
.pr-wf-row:last-child { border-bottom: none; }
.pr-wf-feature { font-family: var(--font-mono); font-size: 12px; color: var(--text-primary); }
.pr-wf-val { color: var(--text-muted); margin-left: 6px; font-size: 10.5px; }
.pr-wf-bar-area { height: 14px; position: relative; }
.pr-wf-center { position: absolute; left: 50%; top: -2px; bottom: -2px;
  width: 1px; background: var(--text-faint); }
.pr-wf-bar { position: absolute; top: 0; height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.pr-wf-bar.pos { background: linear-gradient(90deg, rgba(99,102,241,0.7), var(--violet)); left: 50%; }
.pr-wf-bar.neg { background: linear-gradient(90deg, var(--pink), rgba(236,72,153,0.7)); right: 50%; }
.pr-wf-shap { font-family: var(--font-mono); font-size: 11px; text-align: right; }

/* Plain English */
.pr-plain-english { margin: 18px 0; padding: 18px 20px;
  background: rgba(139,92,246,0.04); border: 1px solid var(--border-subtle); border-radius: 12px; }
.pr-plain-english h4 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.pr-plain-english p { font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; }

/* Counterfactual */
.pr-counterfactual { margin: 18px 0; padding: 18px 20px;
  background: rgba(34,211,238,0.04); border: 1px solid rgba(34,211,238,0.2); border-radius: 12px; }
.pr-counterfactual h4 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.pr-cf-pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.pr-cf-pill { padding: 6px 12px; background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 8px; font-size: 12px; }
.pr-cf-feat { font-family: var(--font-mono); color: var(--violet); }
.pr-cf-from { color: var(--pink); text-decoration: line-through; font-family: var(--font-mono); }
.pr-cf-to { color: var(--green); font-weight: 600; font-family: var(--font-mono); }
.pr-cf-shift { font-family: var(--font-display); font-size: 22px; margin-top: 10px; color: var(--text-muted); }
```
