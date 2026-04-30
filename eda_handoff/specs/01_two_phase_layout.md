# Spec 01 — Two-Phase Layout & Router

## Page structure

```
[Sidebar (Pipeline → EDA active)]
[Main content
  ├─ topbar (breadcrumb + phase toggle + theme toggle)
  ├─ hero (eyebrow + Instrument Serif title + subtitle — title/subtitle change per phase)
  └─ phase router renders ONE OF:
      ├─ Phase 1: questions panel (mode pill + question cards + sticky action bar)
      └─ Phase 2: results dashboard (insights → target → featured → grid → stats → flags → chat → filters → actions)
]
```

## File: `dashboard/components/ed_phase_router.py`

```python
"""Two-phase router — Questions vs Results — with optional dev toggle in topbar."""
from __future__ import annotations
from typing import Literal
import streamlit as st


Phase = Literal["questions", "results"]
PHASE_KEY = "ed_phase"


def get_phase() -> Phase:
    """Return current phase. Defaults to 'questions' until results exist."""
    return st.session_state.get(PHASE_KEY, "questions")


def set_phase(phase: Phase) -> None:
    st.session_state[PHASE_KEY] = phase


def auto_set_initial_phase() -> None:
    """If we have eda_results in session_state from a prior run, jump to results.
    Called once at the top of the page."""
    if PHASE_KEY in st.session_state:
        return  # user explicit choice wins
    if st.session_state.get("eda_results") and st.session_state.get("eda_charts"):
        set_phase("results")
    else:
        set_phase("questions")


def render_phase_toggle() -> None:
    """Render the small Questions / Results toggle in the topbar.
    The Results button is disabled when no results are computed yet.
    """
    has_results = bool(st.session_state.get("eda_results"))
    current = get_phase()

    cols = st.columns(2, gap="small")
    with cols[0]:
        if st.button("Questions",
                     key="ed_pt_questions",
                     use_container_width=True,
                     disabled=current == "questions"):
            set_phase("questions")
            st.rerun()
    with cols[1]:
        if st.button("Results",
                     key="ed_pt_results",
                     use_container_width=True,
                     disabled=current == "results" or not has_results,
                     help="Run analysis first to view results" if not has_results else None):
            set_phase("results")
            st.rerun()
```

## CSS additions

Append to `shared_css.py`:

```css
/* ============ EDA — page chrome ============ */
.ed-crumbs {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-muted); letter-spacing: 0.4px;
}
.ed-crumbs .sep { color: var(--text-faint); }
.ed-crumbs .cur { color: var(--text-primary); }

.ed-hero { margin-bottom: 28px; }
.ed-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 8px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 11.5px; color: var(--text-secondary); margin-bottom: 16px;
  backdrop-filter: blur(12px); font-family: var(--font-mono);
  letter-spacing: 0.6px; text-transform: uppercase;
}
.ed-eyebrow svg { width: 14px; height: 14px; color: var(--violet); }
.ed-hero h1 {
  font-family: var(--font-display); font-size: 56px;
  line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px;
  color: var(--text-primary);
}
.ed-hero h1 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ed-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }

/* Phase toggle pill */
.ed-phase-toggle {
  display: inline-flex; gap: 4px; padding: 4px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 999px; backdrop-filter: blur(12px);
}
[data-testid="stMain"] .stButton > button[key^="ed_pt_"] {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: none !important;
  padding: 7px 16px !important;
  border-radius: 999px !important;
  font-size: 12.5px !important; font-weight: 500 !important;
  box-shadow: none !important;
}
[data-testid="stMain"] .stButton > button[key^="ed_pt_"]:hover {
  color: var(--text-primary) !important; background: rgba(139,92,246,0.06) !important;
}
[data-testid="stMain"] .stButton > button[key^="ed_pt_"]:disabled {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important;
  box-shadow: 0 0 18px rgba(139,92,246,0.4) !important;
  opacity: 1 !important;
}

/* Generic phase wrapper */
.ed-phase-wrap {
  animation: ed-fadeUp 0.4s ease;
}
@keyframes ed-fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

## Implementation note

- The phase toggle uses a CSS trick where the **disabled** button is the visually-active one (because the active phase's button isn't clickable). If your Streamlit version doesn't render it cleanly, render two normal buttons and use the active class via a sibling marker div instead.
- `auto_set_initial_phase()` runs once at the top of the page so a user returning to a project mid-pipeline lands on whichever phase makes sense (results if they exist, questions otherwise).
- Phase state lives only in session_state — not the project record — because it's purely transient UI state.
