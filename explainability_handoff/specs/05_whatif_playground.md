# Spec 05 — What-If Playground (Sliders + Animated Gauge)

## Backend reuse

`explainability/what_if.py` — `predict_modified(model, base_instance, modifications: dict) -> float`. **Open first** to confirm. If it returns a dict with `prediction` and `probabilities`, adapt accordingly.

## File: `dashboard/components/ex_whatif_playground.py`

```python
"""What-If playground — sliders for each feature + live prediction gauge."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np

from dashboard.components import project_service


def render(predict_fn, feature_ranges: dict) -> None:
    """Render the What-If tab.

    Args:
        predict_fn: callable(modifications: dict) -> float (probability)
        feature_ranges: dict mapping feature_name -> {"min": float, "max": float,
                        "default": float, "step": float, "dtype": str}
    """
    project = project_service.get_active()
    df = st.session_state.get("df")
    if df is None or not predict_fn or not feature_ranges:
        st.info("What-If analysis requires a trained model and feature data.")
        return

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>What-If <em>playground</em></h3>'
        '<span class="ex-sec-meta">Drag sliders → live prediction update</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Get the baseline instance (first high-risk or first row)
    baseline_idx = st.session_state.get("ex_instance_select", 0)
    baseline_pred = st.session_state.get("ex_baseline_pred", 0.5)

    # Two columns: sliders left, gauge right
    left, right = st.columns([1.5, 1], gap="large")

    modifications = {}

    with left:
        top_features = list(feature_ranges.keys())[:8]  # limit to 8 sliders
        for feature in top_features:
            info = feature_ranges[feature]
            default = info.get("default", info.get("min", 0))
            step = info.get("step", 1.0 if info.get("dtype") == "int" else 0.1)

            cols = st.columns([2, 5, 1])
            with cols[0]:
                st.markdown(
                    f'<div class="ex-slider-label">{_html_escape(feature)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                val = st.slider(
                    feature,
                    min_value=float(info["min"]),
                    max_value=float(info["max"]),
                    value=float(default),
                    step=float(step),
                    key=f"ex_wi_{feature}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                st.markdown(
                    f'<div class="ex-slider-val">{val}</div>',
                    unsafe_allow_html=True,
                )

            if val != default:
                modifications[feature] = val

    with right:
        # Compute prediction with modifications
        try:
            new_pred = predict_fn(modifications) if modifications else baseline_pred
        except Exception:
            new_pred = baseline_pred

        _render_gauge(new_pred, baseline_pred)


def _render_gauge(prediction: float, baseline: float) -> None:
    """Render the animated prediction gauge as an SVG + Streamlit text."""
    pct = int(prediction * 100)
    delta = pct - int(baseline * 100)

    if pct > 60:
        risk_class = "high-risk"
        risk_label = "⚠ High Risk"
        risk_color = "var(--red)"
    elif pct > 35:
        risk_class = "mid-risk"
        risk_label = "⚡ Medium Risk"
        risk_color = "var(--amber)"
    else:
        risk_class = "low-risk"
        risk_label = "✓ Low Risk"
        risk_color = "var(--green)"

    sign = "+" if delta >= 0 else ""
    delta_color = "var(--green)" if delta < 0 else ("var(--red)" if delta > 0 else "var(--text-muted)")

    # SVG gauge — arc from 0% to prediction%
    arc_length = 251  # approximate semicircle circumference for r=80
    filled = arc_length * prediction
    offset = arc_length - filled

    st.markdown(
        f'<div class="ex-gauge-card">'
        f'  <div class="ex-gauge-label">Predicted risk</div>'
        f'  <svg class="ex-gauge-svg" viewBox="0 0 200 120">'
        f'    <defs>'
        f'      <linearGradient id="exGaugeGrad" x1="0" y1="0" x2="1" y2="0">'
        f'        <stop offset="0%" stop-color="#34D399"/>'
        f'        <stop offset="50%" stop-color="#FBBF24"/>'
        f'        <stop offset="100%" stop-color="#F87171"/>'
        f'      </linearGradient>'
        f'    </defs>'
        f'    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" '
        f'      stroke="rgba(139,92,246,0.08)" stroke-width="12" stroke-linecap="round"/>'
        f'    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" '
        f'      stroke="url(#exGaugeGrad)" stroke-width="12" stroke-linecap="round" '
        f'      stroke-dasharray="{arc_length}" stroke-dashoffset="{offset:.0f}"/>'
        f'  </svg>'
        f'  <div class="ex-gauge-value {risk_class}">{pct}%</div>'
        f'  <div class="ex-gauge-class" style="color:{risk_color};">{risk_label}</div>'
        f'  <div class="ex-gauge-delta">'
        f'    Original: {int(baseline * 100)}% · Change: '
        f'    <strong style="color:{delta_color};">{sign}{delta}%</strong>'
        f'  </div>'
        f'  <div class="ex-gauge-comparison">'
        f'    <div class="ex-gauge-comp"><div class="ex-gauge-comp-label">Base rate</div>'
        f'      <div class="ex-gauge-comp-val">14%</div></div>'
        f'    <div class="ex-gauge-comp"><div class="ex-gauge-comp-label">This instance</div>'
        f'      <div class="ex-gauge-comp-val" style="color:{risk_color};">{pct}%</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def build_feature_ranges(df: pd.DataFrame, feature_names: list[str],
                          instance_values: dict = None) -> dict:
    """Build slider range metadata from the dataframe.

    Args:
        df: training dataframe
        feature_names: features to include (typically top SHAP features)
        instance_values: optional dict of default values (from a specific instance)
    """
    ranges = {}
    for feat in feature_names:
        if feat not in df.columns:
            continue
        s = df[feat].dropna()
        if pd.api.types.is_numeric_dtype(s):
            ranges[feat] = {
                "min": float(s.min()),
                "max": float(s.max()),
                "default": float(instance_values.get(feat, s.median())) if instance_values else float(s.median()),
                "step": 1.0 if pd.api.types.is_integer_dtype(s) else round((s.max() - s.min()) / 100, 2),
                "dtype": "int" if pd.api.types.is_integer_dtype(s) else "float",
            }
    return ranges


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ What-If playground ============ */
.ex-slider-label { font-family: var(--font-mono); font-size: 12px;
  color: var(--text-primary); padding-top: 8px; }
.ex-slider-val { font-family: var(--font-mono); font-size: 13px;
  color: var(--violet); font-weight: 600; text-align: right; padding-top: 8px; }

/* Restyle Streamlit sliders in What-If */
[data-testid="stMain"] .stSlider [role="slider"] { background: var(--violet) !important; }
[data-testid="stMain"] .stSlider [data-baseweb="slider"] > div > div:first-child {
  background: rgba(139,92,246,0.15) !important; }

/* Gauge card */
.ex-gauge-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 28px; text-align: center;
  backdrop-filter: blur(14px); position: sticky; top: 28px;
}
.ex-gauge-label { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.ex-gauge-svg { width: 200px; height: 120px; margin: 0 auto 12px; }
.ex-gauge-value { font-family: var(--font-display); font-size: 48px; line-height: 1; }
.ex-gauge-value.high-risk { color: var(--red); }
.ex-gauge-value.mid-risk { color: var(--amber); }
.ex-gauge-value.low-risk { color: var(--green); }
.ex-gauge-class { font-size: 14px; font-weight: 500; margin-top: 8px; }
.ex-gauge-delta { font-family: var(--font-mono); font-size: 12px;
  color: var(--text-muted); margin-top: 6px; }
.ex-gauge-comparison { display: flex; justify-content: space-around; margin-top: 20px;
  padding-top: 16px; border-top: 1px solid var(--border-subtle); }
.ex-gauge-comp { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.ex-gauge-comp-label { font-family: var(--font-mono); font-size: 9px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; }
.ex-gauge-comp-val { font-family: var(--font-display); font-size: 22px; }
```
