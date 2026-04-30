# Spec 05 — Interaction Features (Section 04, top half)

## Layout

```
[Section header: "04 · Interaction features"]
[Stack of interaction toggle cards — Age × Pclass, Sex × Pclass, is_alone, ...]
[Global FE chat composer at the bottom — see Spec 06]
```

This section uses the same card style as Section 02 domain features (see Spec 03 CSS — `.fe-feat`).

## File: `dashboard/components/fe_interaction_features.py`

```python
"""AI-suggested interaction features.

Pulls suggestions from `agents.feature_engineer.suggest_interactions(df, project)`
or, if unavailable, falls back to a simple heuristic that proposes:
  - target_correlated × cat (for top-2 correlated numeric × top-2 cardinality cats)
  - is_alone-style binary indicators from already-toggled domain features
"""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    df: pd.DataFrame | None = st.session_state.get("df")
    if not project or df is None:
        return

    suggestions = _load_suggestions(df, project)
    fe_interactions = st.session_state.setdefault("fe_interaction_choices", {})

    st.markdown(
        '<div class="fe-sec">'
        '  <div class="fe-sec-head">'
        '    <div class="fe-sec-num">04</div>'
        '    <div style="flex:1;">'
        '      <div class="fe-sec-title">Interaction <em>features</em></div>'
        '      <div class="fe-sec-meta">AI-suggested feature crosses based on importance signals</div>'
        '    </div>'
        '  </div>',
        unsafe_allow_html=True,
    )

    if not suggestions:
        st.markdown(
            '<div class="fe-reasoning">No interaction features suggested. The dataset may be too small or the feature engineer has no high-confidence picks.</div>',
            unsafe_allow_html=True,
        )
    else:
        for s in suggestions:
            _render_interaction_card(s, fe_interactions)

    # Global chat composer is rendered AFTER this section (see Spec 06 + 08)
    # but stays inside the same `.fe-sec` block. The page wires it up.
    st.markdown('<!-- global chat composer slot -->', unsafe_allow_html=True)
    # Note: closing </div> for fe-sec is rendered in the page after the global chat.


def _load_suggestions(df: pd.DataFrame, project) -> list[dict]:
    """Returns a list of dicts: {name, description, reason, default_on}."""
    try:
        from agents.feature_engineer import suggest_interactions
        return suggest_interactions(df, project) or []
    except Exception:
        return _fallback_suggestions(df, project)


def _fallback_suggestions(df: pd.DataFrame, project) -> list[dict]:
    out = []
    target = getattr(project, "target_column", None)
    numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != target]
    cat_cols = [c for c in df.columns
                if pd.api.types.is_object_dtype(df[c]) and df[c].nunique() <= 10]

    if target and numeric_cols and cat_cols:
        out.append({
            "name": f"{numeric_cols[0]}_x_{cat_cols[0]}",
            "description": f"Multiplicative interaction — captures whether the {numeric_cols[0]} effect differs by {cat_cols[0]}.",
            "reason": "★ suggested · high importance in similar datasets",
            "default_on": True,
        })
    if "SibSp" in df.columns and "Parch" in df.columns:
        out.append({
            "name": "is_alone",
            "description": "Binary indicator: 1 if family_size == 1, else 0.",
            "reason": "★ suggested · derived from family_size",
            "default_on": False,
        })
    return out


def _render_interaction_card(s: dict, choices: dict) -> None:
    name = s.get("name", "interaction")
    desc = s.get("description", "")
    reason = s.get("reason", "")
    default_on = s.get("default_on", False)

    if name not in choices:
        choices[name] = default_on

    is_on = choices[name]

    st.markdown(
        f'<div class="fe-feat">'
        f'  <div class="fe-feat-left">'
        f'    <div class="fe-feat-name">{_html_escape(name)}</div>'
        f'    <div class="fe-feat-desc">{_html_escape(desc)}</div>'
        f'    <div class="fe-feat-req met">{_html_escape(reason)}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([10, 1])
    with cols[1]:
        new_state = st.checkbox(
            "Enable",
            value=is_on,
            key=f"fe_int_{name}",
            label_visibility="collapsed",
        )
        if new_state != is_on:
            choices[name] = new_state
            st.rerun()


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS

Reuses `.fe-feat` and `.fe-feat-req` from Spec 03. No new CSS required.

## Adapter note

If `agents.feature_engineer.suggest_interactions` doesn't exist or has a different signature, the fallback heuristic kicks in. Do **not** modify the agent.
