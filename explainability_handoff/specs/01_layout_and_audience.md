# Spec 01 — Layout, Audience Switcher & Section Tabs

## Page structure

```
[Sidebar (Pipeline → Explainability active)]
[Main
  ├─ topbar (breadcrumb + theme toggle)
  ├─ hero (eyebrow "Step 6 of 7" + Instrument Serif title + subtitle)
  ├─ Audience Switcher (Technical / Business / Regulatory)
  ├─ Section tabs (7 horizontal tabs)
  ├─ Active tab content
  ├─ Chat composer
  └─ Action bar (Continue to Predict + summary)
]
```

## File: `dashboard/components/ex_audience_switcher.py`

```python
"""Audience switcher — Technical / Business / Regulatory views."""
from __future__ import annotations
from typing import Literal
import streamlit as st

Audience = Literal["technical", "business", "regulatory"]
KEY = "ex_audience"

AUDIENCES = [
    {"key": "technical",  "label": "Technical",  "icon": "💻",
     "desc": "SHAP values, p-values, full statistical detail"},
    {"key": "business",   "label": "Business",   "icon": "👥",
     "desc": "Plain English, dollar impact, executive-ready"},
    {"key": "regulatory", "label": "Regulatory",  "icon": "🛡",
     "desc": "Model card, fairness audit, compliance trail"},
]


def render() -> Audience:
    """Render the 3-button audience toggle. Returns current audience."""
    current = st.session_state.get(KEY, "technical")

    cols = st.columns(len(AUDIENCES), gap="small")
    for col, aud in zip(cols, AUDIENCES):
        with col:
            is_active = aud["key"] == current
            st.markdown(
                f'<div class="ex-audience-btn{"  ex-audience-active" if is_active else ""}" '
                f'data-aud="{aud["key"]}">'
                f'  <span>{aud["icon"]}</span> {aud["label"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(aud["label"], key=f"ex_aud_{aud['key']}",
                         use_container_width=True, label_visibility="collapsed"):
                st.session_state[KEY] = aud["key"]
                st.rerun()
    return current


def get_audience() -> Audience:
    return st.session_state.get(KEY, "technical")
```

## File: `dashboard/components/ex_section_tabs.py`

```python
"""7 horizontal section tabs for explainability sub-sections."""
from __future__ import annotations
from typing import Literal
import streamlit as st

Section = Literal["global", "interactions", "local", "whatif", "fairness", "card", "calibration"]
KEY = "ex_section"

SECTIONS = [
    {"key": "global",       "label": "🎯 Global SHAP",    "badge": None},
    {"key": "interactions", "label": "🕸 Interactions",   "badge": "New"},
    {"key": "local",        "label": "🔬 Local",          "badge": None},
    {"key": "whatif",       "label": "🎮 What-If",        "badge": None},
    {"key": "fairness",     "label": "⚖ Fairness",       "badge": None},
    {"key": "card",         "label": "📋 Model Card",     "badge": None},
    {"key": "calibration",  "label": "📐 Calibration",    "badge": None},
]


def render() -> Section:
    """Render the horizontal section tabs. Returns the active section key."""
    current = st.session_state.get(KEY, "global")

    cols = st.columns(len(SECTIONS))
    for col, sec in zip(cols, SECTIONS):
        with col:
            is_active = sec["key"] == current
            badge_html = (f'<span class="ex-tab-badge">{sec["badge"]}</span>'
                         if sec["badge"] else "")
            st.markdown(
                f'<div class="ex-sec-tab{" ex-tab-active" if is_active else ""}">'
                f'  {sec["label"]}{badge_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(sec["label"], key=f"ex_tab_{sec['key']}",
                         use_container_width=True, label_visibility="collapsed"):
                st.session_state[KEY] = sec["key"]
                st.rerun()
    return current
```

## CSS additions

```css
/* ============ Explainability — page chrome ============ */
.ex-crumbs { display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px; color: var(--text-muted); letter-spacing: 0.4px; }
.ex-crumbs .sep { color: var(--text-faint); }
.ex-crumbs .cur { color: var(--text-primary); }

.ex-hero { margin-bottom: 28px; }
.ex-eyebrow { display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 8px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 11.5px; color: var(--text-secondary); margin-bottom: 16px;
  backdrop-filter: blur(12px); font-family: var(--font-mono);
  letter-spacing: 0.6px; text-transform: uppercase; }
.ex-hero h1 { font-family: var(--font-display); font-size: 56px;
  line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px; color: var(--text-primary); }
.ex-hero h1 em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.ex-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }

/* Audience switcher */
.ex-audience-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 10px 18px; border-radius: 10px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  color: var(--text-muted); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.2s ease; backdrop-filter: blur(14px);
  text-align: center;
}
.ex-audience-btn:hover { color: var(--text-primary); border-color: var(--border-strong); }
.ex-audience-active {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important;
  border-color: var(--violet) !important;
  box-shadow: 0 0 18px rgba(139,92,246,0.4);
}

/* Section tabs */
.ex-sec-tab {
  padding: 12px 8px; text-align: center;
  color: var(--text-muted); font-size: 12.5px; font-weight: 500;
  cursor: pointer; position: relative; transition: color 0.2s ease;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.ex-sec-tab:hover { color: var(--text-primary); }
.ex-tab-active {
  color: var(--text-primary) !important;
  border-bottom-color: var(--violet) !important;
}
.ex-tab-badge {
  font-family: var(--font-mono); font-size: 8px;
  padding: 1px 5px; background: rgba(139,92,246,0.1);
  border: 1px solid var(--border-subtle); border-radius: 999px;
  color: var(--violet); letter-spacing: 0.5px; text-transform: uppercase;
  margin-left: 4px; vertical-align: super;
}

/* Section headers */
.ex-sec-header { display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin: 28px 0 18px; }
.ex-sec-header h3 { font-family: var(--font-display); font-size: 26px; line-height: 1.1; }
.ex-sec-header h3 em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.ex-sec-meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

/* Phase animation */
.ex-tab-content { animation: ex-fadeUp 0.4s ease; }
@keyframes ex-fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
```
