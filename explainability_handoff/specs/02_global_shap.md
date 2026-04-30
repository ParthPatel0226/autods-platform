# Spec 02 — Global SHAP + Plain English Summary

## Backend reuse

- `explainability/shap_explainer.py` — `compute_shap_values(model, X, max_samples=500)` returns SHAP values + feature names + base_value. **Open file first** to confirm API.
- `explainability/plain_english.py` — `generate_explanation(shap_values, feature_names, domain, audience)` returns a natural language summary. **Confirm API.**

## File: `dashboard/components/ex_global_shap.py`

```python
"""Global SHAP importance bar chart + plain English summary."""
from __future__ import annotations
import streamlit as st
import numpy as np

from dashboard.components.ex_audience_switcher import get_audience


def render(shap_data: dict) -> None:
    """Render the Global SHAP tab.

    Args:
        shap_data: dict with keys:
            feature_names: list[str]
            mean_abs_shap: list[float]  — mean |SHAP| per feature, sorted desc
            directions: list[str]       — "↑ risk" / "↓ risk" / "mixed"
            base_value: float
    """
    if not shap_data:
        st.info("SHAP values not computed yet. Click 'Run Explainability' to generate.")
        return

    features = shap_data["feature_names"]
    values = shap_data["mean_abs_shap"]
    directions = shap_data.get("directions", ["mixed"] * len(features))
    max_val = max(values) if values else 1.0
    top_n = min(15, len(features))

    audience = get_audience()

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Feature <em>importance</em></h3>'
        f'<span class="ex-sec-meta">SHAP · top {top_n} of {len(features)} features</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # SHAP bar chart
    st.markdown('<div class="ex-shap-summary">', unsafe_allow_html=True)
    for i in range(top_n):
        pct = values[i] / max_val * 100
        is_neg = directions[i].startswith("↓")
        fill_class = "neg" if is_neg else "pos"
        value_str = f"{values[i]:.3f}" if audience == "technical" else f"{values[i]:.2f}"
        direction = directions[i] if audience == "technical" else ("lowers risk" if is_neg else "raises risk")

        st.markdown(
            f'<div class="ex-shap-row">'
            f'  <div class="ex-shap-rank">{i + 1}</div>'
            f'  <div class="ex-shap-feature">{_html_escape(features[i])}</div>'
            f'  <div class="ex-shap-track"><div class="ex-shap-fill {fill_class}" style="width:{pct:.0f}%;">{value_str}</div></div>'
            f'  <div class="ex-shap-direction">{direction}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_plain_english(summary_text: str) -> None:
    """Render the LLM-generated plain English explanation card."""
    if not summary_text:
        return

    st.markdown(
        f'<div class="ex-plain-english">'
        f'  <h3>🧠 In <em>plain English</em></h3>'
        f'  <p>{summary_text}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Global SHAP ============ */
.ex-shap-summary { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 24px; backdrop-filter: blur(14px); margin-bottom: 24px; }
.ex-shap-row { display: flex; align-items: center; gap: 14px; padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle); }
.ex-shap-row:last-child { border-bottom: none; }
.ex-shap-rank { width: 24px; font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); text-align: right; }
.ex-shap-feature { width: 160px; font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ex-shap-track { flex: 1; height: 22px; background: rgba(139,92,246,0.06);
  border-radius: 4px; overflow: hidden; }
.ex-shap-fill { height: 100%; border-radius: 4px; display: flex; align-items: center;
  justify-content: flex-end; padding-right: 8px;
  font-family: var(--font-mono); font-size: 10px; color: white;
  transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
.ex-shap-fill.pos { background: linear-gradient(135deg, var(--indigo), var(--violet)); }
.ex-shap-fill.neg { background: linear-gradient(135deg, var(--pink), var(--red)); }
.ex-shap-direction { font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); width: 70px; text-align: right; }

/* Plain English card */
.ex-plain-english {
  background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(168,85,247,0.04));
  border: 1px solid var(--border-default); border-radius: 18px;
  padding: 24px 26px; margin-bottom: 28px;
  backdrop-filter: blur(14px); position: relative; overflow: hidden;
}
.ex-plain-english::before { content: ""; position: absolute; right: -40px; top: -40px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(168,85,247,0.18), transparent 60%);
  pointer-events: none; }
.ex-plain-english h3 { font-family: var(--font-display); font-size: 22px;
  margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
.ex-plain-english h3 em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.ex-plain-english p { font-size: 14px; color: var(--text-secondary); line-height: 1.7; }
.ex-plain-english strong { color: var(--text-primary); }
```
