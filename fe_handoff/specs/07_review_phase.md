# Spec 07 — Review & Approve Phase

## Layout

```
[Hero: "Review your *plan.*"]

[Section ✓ — Output shape]
  [3 stat cards: 891 rows · 12 → 18 cols · 0 missing]

[Section ↺ — Column transformations]
  [Diff table — green = new transformation, faint = unchanged]

[Section + — New features created]
  [Green pills with origin tags: domain · extracted · interaction · custom]

[Section − — Columns dropped]
  [Red pills with reasons]
  [Expandable AI reasoning]

[Sticky action bar: "Plan ready · ..." + Modify + Approve & Continue to Modeling →]
```

## File: `dashboard/components/fe_review_shape.py`

```python
"""Output shape: 3 stat cards (rows / cols before→after / missing after)."""
from __future__ import annotations
import streamlit as st
import pandas as pd


def render() -> None:
    df: pd.DataFrame | None = st.session_state.get("df")
    if df is None:
        return

    n_rows = len(df)
    n_cols_before = len(df.columns)

    fe_choices = st.session_state.get("fe_choices", {})
    fe_domain = st.session_state.get("fe_domain_choices", {})
    fe_interact = st.session_state.get("fe_interaction_choices", {})
    fe_custom = st.session_state.get("fe_custom_features", [])

    # Calculate after-shape
    n_dropped = sum(1 for ch in fe_choices.values() if ch.get("action") == "drop")
    n_extracted_drops = sum(1 for ch in fe_choices.values()
                            if ch.get("encoding") in ("extract_title", "extract_deck"))
    n_new = sum(1 for v in fe_domain.values() if v) \
          + sum(1 for v in fe_interact.values() if v) \
          + len(fe_custom) \
          + n_extracted_drops  # extracted features add new cols

    n_cols_after = n_cols_before - n_dropped + n_new
    missing_after = 0  # post-imputation

    st.markdown(
        f'<div class="fe-sec">'
        f'  <div class="fe-sec-head">'
        f'    <div class="fe-sec-num">✓</div>'
        f'    <div style="flex:1;">'
        f'      <div class="fe-sec-title">Output <em>shape</em></div>'
        f'      <div class="fe-sec-meta">Final dataset dimensions after feature engineering</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="fe-review-grid">'
        f'    <div class="fe-review-stat">'
        f'      <div class="fe-review-num">{n_rows:,}</div>'
        f'      <div class="fe-review-label">Rows · unchanged</div>'
        f'    </div>'
        f'    <div class="fe-review-stat">'
        f'      <div class="fe-review-num"><span class="strike">{n_cols_before}</span><em>{n_cols_after}</em></div>'
        f'      <div class="fe-review-label">Columns · {n_cols_before} → {n_cols_after}</div>'
        f'    </div>'
        f'    <div class="fe-review-stat">'
        f'      <div class="fe-review-num"><em>{missing_after}</em></div>'
        f'      <div class="fe-review-label">Missing values · after</div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
```

## File: `dashboard/components/fe_review_diff.py`

```python
"""Column transformations diff table."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    df: pd.DataFrame | None = st.session_state.get("df")
    project = project_service.get_active()
    if df is None or not project:
        return

    fe_choices = st.session_state.get("fe_choices", {})
    target = project.target_column

    rows_html = []
    for col in df.columns:
        ch = fe_choices.get(col, {})
        rows_html.append(_render_row(col, ch, target))

    st.markdown(
        f'<div class="fe-sec">'
        f'  <div class="fe-sec-head">'
        f'    <div class="fe-sec-num">↺</div>'
        f'    <div style="flex:1;">'
        f'      <div class="fe-sec-title">Column <em>transformations</em></div>'
        f'      <div class="fe-sec-meta">Per-column plan — green = new transformation applied</div>'
        f'    </div>'
        f'  </div>'
        f'  <table class="fe-table">'
        f'    <thead><tr>'
        f'      <th>Column</th><th>Imputation</th><th>Encoding</th>'
        f'      <th>Scaling</th><th>Outliers</th><th>Action</th>'
        f'    </tr></thead>'
        f'    <tbody>{"".join(rows_html)}</tbody>'
        f'  </table>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_row(col: str, ch: dict, target: str | None) -> str:
    is_target = (col == target)
    if is_target:
        return (f'<tr>'
                f'  <td><span class="fe-cell-mono tgt">{_html_escape(col)} ★</span></td>'
                f'  <td colspan="4"><span class="fe-same">no transform — target</span></td>'
                f'  <td><span class="fe-pill tgt">Target</span></td>'
                f'</tr>')
    if ch.get("action") == "drop":
        reason = ch.get("reason", "drop")
        return (f'<tr>'
                f'  <td><span class="fe-cell-mono">{_html_escape(col)}</span></td>'
                f'  <td colspan="4"><span class="fe-same">—</span></td>'
                f'  <td><span class="fe-pill drop">Drop · {_html_escape(reason)}</span></td>'
                f'</tr>')
    cells = [
        _cell(ch.get("imputation")),
        _cell(ch.get("encoding")),
        _cell(ch.get("scaling")),
        _cell(ch.get("outliers")),
    ]
    return (f'<tr>'
            f'  <td><span class="fe-cell-mono">{_html_escape(col)}</span></td>'
            + "".join(f'<td>{c}</td>' for c in cells)
            + f'  <td></td>'
            f'</tr>')


def _cell(value: str | None) -> str:
    if not value or value in ("none", "keep"):
        return '<span class="fe-same">—</span>'
    return f'<span class="fe-after">{_html_escape(value).title()}</span>'


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/fe_review_new_features.py`

```python
"""Green pills showing all new features being created."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    pills = []

    # Domain
    fe_domain = st.session_state.get("fe_domain_choices", {})
    for name, on in fe_domain.items():
        if on:
            pills.append(("domain", name))

    # Interactions
    fe_interact = st.session_state.get("fe_interaction_choices", {})
    for name, on in fe_interact.items():
        if on:
            pills.append(("interaction", name))

    # Custom
    fe_custom = st.session_state.get("fe_custom_features", [])
    for f in fe_custom:
        pills.append(("custom", f.get("name", "")))

    # Extracted (from per-column choices)
    fe_choices = st.session_state.get("fe_choices", {})
    for col, ch in fe_choices.items():
        if ch.get("encoding") == "extract_title":
            pills.append(("extracted", f"{col}_title"))
        elif ch.get("encoding") == "extract_deck":
            pills.append(("extracted", f"{col}_deck"))
        if ch.get("imputation") == "flag_missing":
            pills.append(("extracted", f"{col}_missing_flag"))

    pills_html = "".join(
        f'<span class="fe-pill new">{name} <small>{origin}</small></span>'
        for origin, name in pills
    )
    if not pills_html:
        pills_html = '<span class="fe-same">No new features yet — toggle some on or add custom expressions.</span>'

    st.markdown(
        f'<div class="fe-sec">'
        f'  <div class="fe-sec-head">'
        f'    <div class="fe-sec-num">+</div>'
        f'    <div style="flex:1;">'
        f'      <div class="fe-sec-title">New <em>features created</em></div>'
        f'      <div class="fe-sec-meta">{len(pills)} new columns from domain knowledge, extraction, and interactions</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="fe-tag-grid">{pills_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
```

## File: `dashboard/components/fe_review_dropped.py`

```python
"""Red pills + AI reasoning for dropped columns."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    fe_choices = st.session_state.get("fe_choices", {})
    dropped = [(col, ch.get("reason", "drop"))
               for col, ch in fe_choices.items()
               if ch.get("action") == "drop"]

    pills_html = "".join(
        f'<span class="fe-pill drop">{col} · {reason.replace("_", " ")}</span>'
        for col, reason in dropped
    )
    if not pills_html:
        pills_html = '<span class="fe-same">No columns dropped.</span>'

    reasoning = _aggregate_reasoning()

    st.markdown(
        f'<div class="fe-sec">'
        f'  <div class="fe-sec-head">'
        f'    <div class="fe-sec-num">−</div>'
        f'    <div style="flex:1;">'
        f'      <div class="fe-sec-title">Columns <em>dropped</em></div>'
        f'      <div class="fe-sec-meta">{len(dropped)} removed — reasons listed</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="fe-tag-grid">{pills_html}</div>'
        f'  <details class="fe-ai-reason">'
        f'    <summary>View AI reasoning</summary>'
        f'    {reasoning}'
        f'  </details>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _aggregate_reasoning() -> str:
    """Build a short summary of the FE plan's rationale."""
    parts = []
    fe_choices = st.session_state.get("fe_choices", {})

    impute_methods = {ch.get("imputation") for ch in fe_choices.values()
                      if ch.get("imputation") and ch.get("imputation") != "none"}
    if impute_methods:
        parts.append(
            f"<p><strong>Imputation:</strong> {', '.join(sorted(impute_methods))}. "
            "Methods chosen based on column distribution skew, missingness, and "
            "downstream model assumptions.</p>"
        )

    encoding_methods = {ch.get("encoding") for ch in fe_choices.values()
                        if ch.get("encoding") and ch.get("encoding") != "none"}
    if encoding_methods:
        parts.append(
            f"<p><strong>Encoding:</strong> {', '.join(sorted(encoding_methods))}. "
            "Label encoding for binary or naturally ordered categories; one-hot for "
            "low-cardinality unordered; ordinal for explicit ranks.</p>"
        )

    fe_domain = st.session_state.get("fe_domain_choices", {})
    enabled_domain = [n for n, v in fe_domain.items() if v]
    if enabled_domain:
        parts.append(
            f"<p><strong>Domain features:</strong> {', '.join(enabled_domain)}. "
            "Pulled from the active domain config — validated for the detected "
            "problem class.</p>"
        )

    fe_interact = st.session_state.get("fe_interaction_choices", {})
    enabled_int = [n for n, v in fe_interact.items() if v]
    if enabled_int:
        parts.append(
            f"<p><strong>Interactions:</strong> {', '.join(enabled_int)}. "
            "Suggested by the feature engineer based on importance signals from "
            "similar datasets.</p>"
        )

    if not parts:
        parts.append("<p>No transformations applied — plan is empty.</p>")
    return "".join(parts)
```

## File: `dashboard/components/fe_review_action_bar.py`

```python
"""Sticky action bar for the Review phase — Modify + Approve & Continue."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service, fe_phase_router


def render() -> None:
    fe_choices = st.session_state.get("fe_choices", {})
    fe_domain = st.session_state.get("fe_domain_choices", {})
    fe_interact = st.session_state.get("fe_interaction_choices", {})
    fe_custom = st.session_state.get("fe_custom_features", [])

    n_dropped = sum(1 for ch in fe_choices.values() if ch.get("action") == "drop")
    n_transformed = sum(1 for ch in fe_choices.values()
                        if not ch.get("action") and any(
                            ch.get(k) and ch.get(k) not in ("none", "keep")
                            for k in ("imputation", "encoding", "scaling", "outliers")))
    n_new = sum(1 for v in fe_domain.values() if v) \
          + sum(1 for v in fe_interact.values() if v) \
          + len(fe_custom)

    st.markdown(
        f'<div class="fe-action-bar">'
        f'  <div class="fe-action-status">'
        f'    <strong>Plan ready</strong> · '
        f'{n_transformed} transformed · {n_dropped} dropped · {n_new} new · 0 missing values after'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([6, 1, 1.6])
    with cols[1]:
        if st.button("← Modify", key="fe_review_modify", use_container_width=True):
            fe_phase_router.set_phase("configure")
            st.rerun()
    with cols[2]:
        if st.button("Approve & Continue to Modeling →",
                     key="fe_review_approve",
                     type="primary",
                     use_container_width=True):
            _approve_and_continue()


def _approve_and_continue() -> None:
    project = project_service.get_active()
    if not project:
        st.error("No active project.")
        return

    # Persist plan to project
    plan = {
        "per_column": st.session_state.get("fe_choices", {}),
        "domain": st.session_state.get("fe_domain_choices", {}),
        "interactions": st.session_state.get("fe_interaction_choices", {}),
        "custom": st.session_state.get("fe_custom_features", []),
    }
    setattr(project, "fe_plan", plan)

    # Execute the plan via feature_engineer
    try:
        from agents.feature_engineer import execute_choices
        df = st.session_state.get("df")
        engineered_df = execute_choices(df, plan, project)
        st.session_state["df_engineered"] = engineered_df
        st.session_state["fe_plan_approved"] = True
    except Exception as e:
        st.error(f"Feature engineering execution failed: {e}")
        return

    # Advance pipeline state
    step_status = getattr(project, "step_status", {})
    step_status["features"] = "done"
    step_status["modeling"] = "active"
    setattr(project, "step_status", step_status)
    project_service.update(project)

    # Route to Modeling
    try:
        from streamlit import switch_page
        switch_page("pages/05_modeling.py")
    except Exception:
        st.success("Plan approved. Proceed to Modeling.")
```

## CSS additions

```css
/* Review — output shape stat cards */
.fe-review-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  margin-top: 4px;
}
.fe-review-stat {
  text-align: center;
  padding: 18px 16px;
  background: rgba(7,9,26,0.4);
  border: 1px solid var(--border-subtle); border-radius: 12px;
}
[data-theme="light"] .fe-review-stat { background: rgba(255,255,255,0.55); }
.fe-review-num {
  font-family: var(--font-display); font-size: 36px;
  color: var(--text-primary); line-height: 1; margin-bottom: 6px;
}
.fe-review-num em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.fe-review-num .strike {
  text-decoration: line-through; color: var(--text-muted);
  font-size: 22px; margin-right: 6px;
}
.fe-review-label {
  font-family: var(--font-mono); font-size: 10.5px;
  text-transform: uppercase; letter-spacing: 0.8px;
  color: var(--text-muted);
}

/* Diff table */
.fe-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.fe-table th {
  text-align: left; padding: 10px 12px;
  font-family: var(--font-mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.8px;
  color: var(--text-muted); font-weight: 500;
  border-bottom: 1px solid var(--border-subtle);
}
.fe-table td {
  padding: 12px;
  font-size: 13px; border-bottom: 1px solid rgba(139,92,246,0.06);
}
.fe-table tr:hover td { background: rgba(139,92,246,0.04); }
.fe-table tr:last-child td { border-bottom: 0; }
.fe-cell-mono { font-family: var(--font-mono); font-size: 12px; font-weight: 500; }
.fe-cell-mono.tgt { color: var(--purple); }
.fe-after { font-family: var(--font-mono); font-size: 11.5px; color: var(--green); font-weight: 500; }
.fe-same { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-faint); }

/* Tag grid + small origin tags */
.fe-tag-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.fe-tag-grid .fe-pill { font-size: 11px; padding: 5px 12px; }
.fe-tag-grid .fe-pill small { opacity: 0.6; margin-left: 5px; font-size: 9.5px; }

/* AI reasoning expandable */
details.fe-ai-reason {
  margin-top: 18px;
  padding: 14px 18px;
  background: rgba(139,92,246,0.06);
  border: 1px solid rgba(139,92,246,0.18); border-radius: 12px;
}
details.fe-ai-reason summary {
  list-style: none; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 11.5px;
  color: var(--violet); letter-spacing: 0.4px;
}
details.fe-ai-reason summary::-webkit-details-marker { display: none; }
details.fe-ai-reason summary::before { content: "✦"; }
details.fe-ai-reason summary::after {
  content: "▸"; margin-left: auto; color: var(--text-muted);
  transition: transform 0.18s;
}
details.fe-ai-reason[open] summary::after { transform: rotate(90deg); }
details.fe-ai-reason[open] summary { margin-bottom: 12px; }
details.fe-ai-reason p {
  margin: 6px 0; font-size: 13px; color: var(--text-secondary); line-height: 1.65;
}
details.fe-ai-reason p strong { color: var(--text-primary); font-weight: 500; }
```
