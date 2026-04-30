# Spec 01 — Mode Tabs + Page Layout

## Page structure

```
[Sidebar (Pipeline → Predict active)]
[Main
  ├─ topbar + crumbs
  ├─ hero ("Make predictions with your trained model.")
  ├─ Mode tabs: Single Prediction | Batch Prediction
  ├─ Active tab content
  ├─ Prediction history strip (below both tabs)
  ├─ API deployment snippet card
  ├─ Chat composer
  └─ Action bar
]
```

## File: `dashboard/components/pr_mode_tabs.py`

```python
"""Single / Batch prediction tab switcher."""
from __future__ import annotations
from typing import Literal
import streamlit as st

PredictMode = Literal["single", "batch"]
KEY = "pr_mode"

TABS = [
    {"key": "single", "label": "🎯 Single Prediction", "desc": "Fill in feature values → instant result with explanation"},
    {"key": "batch",  "label": "📊 Batch Prediction",  "desc": "Upload a CSV/Excel file → predictions for all rows"},
]


def render() -> PredictMode:
    current = st.session_state.get(KEY, "single")
    cols = st.columns(len(TABS), gap="small")
    for col, tab in zip(cols, TABS):
        with col:
            is_active = tab["key"] == current
            st.markdown(
                f'<div class="pr-mode-tab{" pr-mode-active" if is_active else ""}">'
                f'  <div class="pr-mode-label">{tab["label"]}</div>'
                f'  <div class="pr-mode-desc">{tab["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(tab["label"], key=f"pr_tab_{tab['key']}",
                         use_container_width=True, label_visibility="collapsed"):
                st.session_state[KEY] = tab["key"]
                st.rerun()
    return current
```

## CSS additions

```css
/* ============ Predict — page chrome ============ */
.pr-crumbs { display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px; color: var(--text-muted); letter-spacing: 0.4px; }
.pr-crumbs .sep { color: var(--text-faint); }
.pr-crumbs .cur { color: var(--text-primary); }

.pr-hero { margin-bottom: 28px; }
.pr-eyebrow { display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 8px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 11.5px; color: var(--text-secondary); margin-bottom: 16px;
  backdrop-filter: blur(12px); font-family: var(--font-mono);
  letter-spacing: 0.6px; text-transform: uppercase; }
.pr-hero h1 { font-family: var(--font-display); font-size: 56px;
  line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px; color: var(--text-primary); }
.pr-hero h1 em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.pr-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }

/* Mode tabs */
.pr-mode-tab {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px 20px; cursor: pointer;
  transition: all 0.22s ease; backdrop-filter: blur(14px); text-align: center;
}
.pr-mode-tab:hover { border-color: var(--border-strong); transform: translateY(-2px); }
.pr-mode-active {
  background: rgba(139,92,246,0.12) !important;
  border-color: var(--violet) !important;
  box-shadow: 0 0 24px -4px var(--violet);
}
.pr-mode-active::before { content: ""; display: block; height: 2px; margin: -18px -20px 14px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-radius: 14px 14px 0 0; }
.pr-mode-label { font-size: 15px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
.pr-mode-desc { font-size: 12px; color: var(--text-muted); }
```
