# Spec 03 — Mode Flashcards + Auto Unsure Helper

## Goal

Replace the existing analysis mode flashcards with cards that include time + prompt-count estimates. When **Auto** is selected, reveal a dashed-border helper block with quick-goal chips that pre-fill target / problem / goal in one click — because many users picking Auto don't know what they want to analyze.

## File: `dashboard/components/cf_mode_cards.py`

```python
"""Analysis mode flashcards with time + prompt estimates."""
from __future__ import annotations
import streamlit as st


MODE_INFO = [
    {
        "key": "auto", "name": "Auto", "icon": "⚡",
        "tagline": "We pick everything. Hands-off.",
        "time": "~2 min", "prompts": "0 prompts",
        "recommended": False,
    },
    {
        "key": "guided", "name": "Guided", "icon": "🎯",
        "tagline": "Approve key decisions. Steer the pipeline.",
        "time": "~5 min", "prompts": "~7 prompts",
        "recommended": True,
    },
    {
        "key": "expert", "name": "Expert", "icon": "🛠",
        "tagline": "Full control. Tweak every parameter.",
        "time": "~15 min", "prompts": "~20 prompts",
        "recommended": False,
    },
]


def render(default: str = "guided") -> str:
    """Render the 3 mode flashcards. Returns the selected mode key.

    State key: st.session_state["cf_mode"]
    """
    selected = st.session_state.get("cf_mode", default)

    st.markdown('<div class="cf-mode-grid">', unsafe_allow_html=True)
    cols = st.columns(3, gap="medium")
    for col, info in zip(cols, MODE_INFO):
        with col:
            _render_card(info, selected)
    st.markdown('</div>', unsafe_allow_html=True)
    return selected


def _render_card(info: dict, selected: str) -> None:
    is_selected = info["key"] == selected
    classes = ["cf-mode-card"]
    if is_selected:
        classes.append("cf-mode-selected")

    badge = ('<div class="cf-mode-recommended">Recommended</div>'
             if info["recommended"] else "")

    st.markdown(
        f'<div class="{" ".join(classes)}">'
        f'  {badge}'
        f'  <div class="cf-mode-icon">{info["icon"]}</div>'
        f'  <div class="cf-mode-name">{info["name"]}</div>'
        f'  <div class="cf-mode-tagline">{info["tagline"]}</div>'
        f'  <div class="cf-mode-meta">'
        f'    <div class="cf-mode-meta-item">⏱ {info["time"]}</div>'
        f'    <div class="cf-mode-meta-item">✓ {info["prompts"]}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Select {info['name']}", key=f"cf_mode_{info['key']}",
                 use_container_width=True, label_visibility="collapsed"):
        st.session_state["cf_mode"] = info["key"]
        st.rerun()
```

## File: `dashboard/components/cf_unsure_helper.py`

```python
"""Auto-mode 'I'm not sure' helper — quick-goal chips that pre-fill target/problem/goal."""
from __future__ import annotations
import streamlit as st
import pandas as pd


# Each chip pre-fills target column, problem type, and goal text.
# Target is auto-resolved from df by heuristics in _resolve_target().
QUICK_GOALS = [
    {
        "key": "predict",
        "icon": "🎯",
        "label": "Predict something specific",
        "problem_type": "auto",   # auto = pick classification or regression based on target
        "goal": "Build the most accurate model possible for the chosen target.",
        "target_strategy": "boolean_or_categorical_first",
    },
    {
        "key": "groups",
        "icon": "🧩",
        "label": "Find natural groups",
        "problem_type": "clustering",
        "goal": "Discover natural segments in the data without a pre-defined target.",
        "target_strategy": "none",
    },
    {
        "key": "anomaly",
        "icon": "⚠️",
        "label": "Spot what's unusual",
        "problem_type": "anomaly",
        "goal": "Identify outliers and unusual patterns in the data.",
        "target_strategy": "none",
    },
    {
        "key": "forecast",
        "icon": "📈",
        "label": "Forecast over time",
        "problem_type": "timeseries",
        "goal": "Predict future values of a metric over time.",
        "target_strategy": "first_numeric",
    },
    {
        "key": "explore",
        "icon": "🔍",
        "label": "Just explore the data",
        "problem_type": "auto",
        "goal": "Run a comprehensive exploratory analysis with no specific target.",
        "target_strategy": "none",
    },
]


def render(df: pd.DataFrame) -> None:
    """Render the Auto-mode unsure helper. Visible only when cf_mode == 'auto'.

    On chip click, sets:
        st.session_state["cf_target"]
        st.session_state["cf_problem_type"]
        st.session_state["cf_goal"]
    """
    if st.session_state.get("cf_mode") != "auto":
        return

    selected_key = st.session_state.get("cf_unsure_chip")

    st.markdown(
        '<div class="cf-unsure-block">'
        '  <div class="cf-unsure-title">'
        '    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
        '      <circle cx="12" cy="12" r="10"/>'
        '      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
        '      <line x1="12" y1="17" x2="12.01" y2="17"/>'
        '    </svg>'
        "    Not sure what you want?"
        '  </div>'
        '  <div class="cf-unsure-sub">Pick a goal and we\'ll pre-fill the target column and problem type for you.</div>'
        '  <div class="cf-unsure-chips">',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(QUICK_GOALS))
    for col, qg in zip(cols, QUICK_GOALS):
        with col:
            is_selected = qg["key"] == selected_key
            chip_class = "cf-unsure-chip cf-unsure-selected" if is_selected else "cf-unsure-chip"
            st.markdown(
                f'<div class="{chip_class}" data-goalkey="{qg["key"]}">'
                f'  <span class="cf-unsure-chip-icon">{qg["icon"]}</span>'
                f'  {qg["label"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(qg["label"], key=f"cf_qgoal_{qg['key']}",
                         use_container_width=True, label_visibility="collapsed"):
                _apply_quick_goal(qg, df)
                st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)


def _apply_quick_goal(qg: dict, df: pd.DataFrame) -> None:
    """Apply a quick-goal selection to session state."""
    st.session_state["cf_unsure_chip"] = qg["key"]
    st.session_state["cf_problem_type"] = qg["problem_type"]
    st.session_state["cf_goal"] = qg["goal"]
    st.session_state["cf_target"] = _resolve_target(df, qg["target_strategy"])


def _resolve_target(df: pd.DataFrame, strategy: str) -> str:
    """Pick a sensible default target column for the given strategy."""
    if df is None or df.empty or strategy == "none":
        return ""

    if strategy == "boolean_or_categorical_first":
        # Prefer boolean → low-cardinality categorical → first numeric
        for col in df.columns:
            if pd.api.types.is_bool_dtype(df[col]):
                return col
        for col in df.columns:
            if df[col].dtype == "object" and df[col].nunique(dropna=True) <= 10:
                return col
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                return col
        return df.columns[0] if len(df.columns) else ""

    if strategy == "first_numeric":
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                return col
        return ""

    return ""
```

## CSS additions

```css
/* ============ Mode flashcards ============ */
.cf-mode-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 14px; margin-bottom: 16px;
}
@media (max-width: 700px) {
  .cf-mode-grid { grid-template-columns: 1fr; }
}
.cf-mode-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px 20px;
  cursor: pointer; transition: all 0.25s ease;
  backdrop-filter: blur(14px); position: relative; overflow: hidden;
  min-height: 175px;
}
.cf-mode-card:hover {
  transform: translateY(-3px); border-color: var(--border-strong);
}
.cf-mode-selected {
  background: rgba(139,92,246,0.15) !important;
  border-color: var(--violet) !important;
  box-shadow: 0 0 28px -4px var(--violet);
}
.cf-mode-selected::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
}
.cf-mode-recommended {
  position: absolute; top: -10px; left: 50%; transform: translateX(-50%);
  font-family: var(--font-mono); font-size: 10px;
  padding: 3px 12px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  color: white; border-radius: 999px;
  letter-spacing: 0.6px; text-transform: uppercase;
  box-shadow: 0 4px 12px -2px var(--violet);
}
.cf-mode-icon { font-size: 28px; margin-bottom: 12px; }
.cf-mode-name { font-family: var(--font-display); font-size: 22px; margin-bottom: 4px; }
.cf-mode-tagline { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.cf-mode-meta {
  display: flex; gap: 12px; padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary);
}
.cf-mode-meta-item { display: flex; align-items: center; gap: 5px; }

/* ============ Auto unsure helper ============ */
.cf-unsure-block {
  margin-top: 18px; padding: 22px;
  background: rgba(139,92,246,0.04);
  border: 1px dashed var(--border-default);
  border-radius: 16px;
  animation: cf-fadeUp 0.25s ease;
}
.cf-unsure-title {
  display: flex; align-items: center; gap: 10px;
  font-size: 14px; font-weight: 600;
  color: var(--text-primary); margin-bottom: 6px;
}
.cf-unsure-title svg { width: 16px; height: 16px; color: var(--violet); }
.cf-unsure-sub {
  font-size: 12.5px; color: var(--text-muted); margin-bottom: 14px;
}
.cf-unsure-chips {
  display: flex; flex-wrap: wrap; gap: 8px;
}
.cf-unsure-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 14px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 12.5px; color: var(--text-secondary); cursor: pointer;
  backdrop-filter: blur(8px); transition: all 0.2s ease;
}
.cf-unsure-chip:hover {
  border-color: var(--violet); color: var(--text-primary); transform: translateY(-1px);
}
.cf-unsure-selected {
  background: rgba(139,92,246,0.15) !important;
  border-color: var(--violet) !important;
  color: var(--text-primary);
  box-shadow: 0 0 14px -4px var(--violet);
}
.cf-unsure-chip-icon { font-size: 15px; }
```

## Implementation notes

- The pattern of "render visual card via markdown + sibling Streamlit button to handle click" is reused from spec 02. Same caveats apply — if the absolute-positioned button trick doesn't render cleanly, fall back to a normal "Select" button below each card.
- `_resolve_target` heuristics are deliberately simple. The orchestrator already has more sophisticated target detection — if you want to use it, import `agents.orchestrator` and call its target-detection helper instead of re-implementing here.
- The `cf_unsure_helper` only renders when `cf_mode == "auto"`. Switching to Guided/Expert hides it cleanly because Streamlit re-renders.
