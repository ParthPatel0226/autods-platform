# Spec 01 — Two-Phase Layout, Dataset Recap, Page Chrome

## Page structure

```
[Sidebar (Pipeline → Features active)]
[Main content
  ├─ topbar (breadcrumb + phase toggle + theme toggle)
  ├─ hero (eyebrow "Step 4 of 7 — Feature Engineering" + Instrument Serif title + subtitle)
  ├─ dataset recap strip (read-only)
  ├─ mode pill ("Guided Mode · Healthcare context · 12 columns")
  └─ phase router renders ONE OF:
      ├─ Phase 1: Configure (sections 01–04 + global chat composer + sticky action bar)
      └─ Phase 2: Review & Approve (output shape, diff table, new features, dropped, AI reasoning, action bar)
]
```

## File: `dashboard/components/fe_phase_router.py`

```python
"""Two-phase router — Configure vs Review — for the FE page."""
from __future__ import annotations
from typing import Literal
import streamlit as st

Phase = Literal["configure", "review"]
PHASE_KEY = "fe_phase"


def get_phase() -> Phase:
    return st.session_state.get(PHASE_KEY, "configure")


def set_phase(phase: Phase) -> None:
    st.session_state[PHASE_KEY] = phase


def auto_set_initial_phase() -> None:
    """Default to Configure unless user has already approved a plan in this session."""
    if PHASE_KEY in st.session_state:
        return
    if st.session_state.get("fe_plan_approved"):
        set_phase("review")
    else:
        set_phase("configure")


def render_phase_toggle() -> None:
    """Render the Configure / Review toggle in the topbar.
    Review is always enabled (the user can preview the plan even without all decisions made)."""
    current = get_phase()
    cols = st.columns(2, gap="small")
    with cols[0]:
        if st.button("Configure",
                     key="fe_pt_configure",
                     use_container_width=True,
                     disabled=current == "configure"):
            set_phase("configure")
            st.rerun()
    with cols[1]:
        if st.button("Review",
                     key="fe_pt_review",
                     use_container_width=True,
                     disabled=current == "review"):
            set_phase("review")
            st.rerun()
```

## File: `dashboard/components/fe_dataset_recap.py`

```python
"""Dataset recap strip — read-only summary at the top of the FE page."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    df: pd.DataFrame | None = st.session_state.get("df")
    if not project or df is None or df.empty:
        return

    domain_icon = {
        "healthcare": "🏥", "finance": "💰", "ecommerce": "🛒",
        "marketing": "📣", "hr": "👥", "manufacturing": "🏭",
        "generic": "✦",
    }.get(project.confirmed_domain, "✦")

    target = project.target_column or "—"
    mode = (project.analysis_mode or "auto").capitalize()

    st.markdown(
        f'<div class="fe-recap">'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Dataset</span><span class="fe-recap-value mono">{_html_escape(project.dataset_name or "—")}</span></div>'
        f'  <div class="fe-recap-sep"></div>'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Domain</span><span class="fe-recap-value" style="color:var(--purple);">{domain_icon} {_html_escape((project.confirmed_domain or "generic").capitalize())}</span></div>'
        f'  <div class="fe-recap-sep"></div>'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Target</span><span class="fe-recap-value mono" style="color:var(--purple);">{_html_escape(target)}</span></div>'
        f'  <div class="fe-recap-sep"></div>'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Rows</span><span class="fe-recap-value mono">{len(df):,}</span></div>'
        f'  <div class="fe-recap-sep"></div>'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Columns</span><span class="fe-recap-value mono">{len(df.columns)}</span></div>'
        f'  <div class="fe-recap-sep"></div>'
        f'  <div class="fe-recap-item"><span class="fe-recap-label">Mode</span><span class="fe-recap-value">{mode}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions (append to `shared_css.py`)

```css
/* ============ FE — page chrome ============ */
.fe-mode-pill {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 5px 14px 5px 10px;
  background: rgba(139,92,246,0.1);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-family: var(--font-mono); font-size: 11px;
  color: var(--violet); letter-spacing: 0.6px;
  text-transform: uppercase; margin-bottom: 22px;
}
.fe-mode-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); }

/* Dataset recap strip */
.fe-recap {
  display: flex; gap: 28px; align-items: center; flex-wrap: wrap;
  padding: 14px 22px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; backdrop-filter: blur(12px);
  margin-bottom: 28px;
}
.fe-recap-item { display: flex; flex-direction: column; gap: 2px; }
.fe-recap-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--text-muted); font-weight: 600;
}
.fe-recap-value { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.fe-recap-value.mono { font-family: var(--font-mono); }
.fe-recap-sep { width: 1px; height: 28px; background: var(--border-default); }

/* Section block (matches ed-q-card pattern) */
.fe-sec {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 26px 28px; margin-bottom: 20px;
  backdrop-filter: blur(14px); transition: all 0.22s ease;
  position: relative; overflow: hidden;
}
.fe-sec:hover { border-color: var(--border-strong); }
.fe-sec-head { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px; }
.fe-sec-num {
  width: 32px; height: 32px; flex-shrink: 0;
  border-radius: 50%; display: grid; place-items: center;
  background: rgba(139,92,246,0.12);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: 12px;
  color: var(--violet); font-weight: 500;
}
.fe-sec-title {
  font-family: var(--font-display); font-size: 24px;
  line-height: 1.1; color: var(--text-primary);
}
.fe-sec-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.fe-sec-meta {
  margin-top: 4px; font-size: 12px; color: var(--text-muted);
  font-family: var(--font-mono); letter-spacing: 0.4px;
}
.fe-sec-tip {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 10px 14px;
  background: rgba(34, 211, 238, 0.06);
  border: 1px solid rgba(34, 211, 238, 0.18);
  border-radius: 10px;
  font-size: 12.5px; color: var(--text-secondary);
  margin-bottom: 18px;
}
.fe-sec-tip svg { width: 14px; height: 14px; color: var(--cyan); flex-shrink: 0; margin-top: 2px; }
```
