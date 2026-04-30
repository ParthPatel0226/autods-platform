# Spec 05 — Excluded Columns with Auto-Suggestions

## Goal

Multi-select grid where users mark columns to exclude from analysis. Pre-checks columns auto-detected as **PII**, **high-cardinality IDs**, **constant**, or **leakage risks**. Each suggestion shows a reason tag.

## File: `dashboard/components/cf_excluded_columns.py`

```python
"""Excluded columns multi-select with auto-suggestions."""
from __future__ import annotations
import streamlit as st
import pandas as pd


# Heuristic patterns for auto-suggesting columns to exclude
PII_KEYWORDS = ["name", "email", "phone", "address", "ssn", "passport", "license"]
ID_KEYWORDS  = ["_id", "id_", "uuid", "guid"]


def render(df: pd.DataFrame, target: str, domain_key: str) -> set[str]:
    """Render the excluded columns grid. Returns the set of excluded column names.

    State key: st.session_state["cf_excluded"] — set[str]
    Suggestions are computed once per df + target combo and pre-checked,
    but the user may toggle any column.
    """
    if df is None or df.empty:
        return set()

    suggestions = _compute_suggestions(df, target, domain_key)

    # Initialize from suggestions on first render or when df changes
    init_key = f"cf_excl_initkey_{id(df)}_{target}"
    if not st.session_state.get(init_key):
        st.session_state["cf_excluded"] = set(suggestions.keys())
        st.session_state[init_key] = True

    excluded = st.session_state.get("cf_excluded", set())

    # Helper line above the grid
    n_suggested = len(suggestions)
    suggest_tags = list({reason for reason in suggestions.values()})
    tags_html = " ".join(
        f'<span class="cf-excl-suggest-tag">{r}</span>' for r in suggest_tags
    )

    if n_suggested:
        st.markdown(
            f'<div class="cf-excl-helper">'
            f'  <span style="color: var(--text-secondary);">{n_suggested} auto-suggestion{"s" if n_suggested != 1 else ""} detected:</span>'
            f'  {tags_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Column grid
    st.markdown('<div class="cf-col-grid">', unsafe_allow_html=True)
    cols_per_row = 4
    columns = list(df.columns)

    # Render in rows of 4
    for i in range(0, len(columns), cols_per_row):
        row = columns[i:i + cols_per_row]
        st_cols = st.columns(cols_per_row, gap="small")
        for st_col, col in zip(st_cols, row):
            with st_col:
                _render_checkbox(col, excluded, suggestions.get(col), target)
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer count
    n_total = len(columns)
    n_excl = len(excluded)
    n_remaining = n_total - n_excl
    st.markdown(
        f'<div class="cf-excl-footer">'
        f'  <span>{n_excl} columns excluded · {n_remaining} will be analyzed</span>'
        f'  <span class="cf-excl-clear" data-action="clear-suggestions">Clear all suggestions</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("Clear all suggestions", key="cf_excl_clear",
                 use_container_width=False):
        st.session_state["cf_excluded"] = set()
        st.rerun()

    return excluded


def _render_checkbox(col: str, excluded: set, reason: str | None, target: str) -> None:
    is_excluded = col in excluded
    is_suggested = reason is not None
    is_target = col == target

    classes = ["cf-col-checkbox"]
    if is_excluded:  classes.append("cf-col-checked")
    if is_suggested: classes.append("cf-col-suggested")
    if is_target:    classes.append("cf-col-target")

    reason_tag = f'<span class="cf-col-name-tag">{reason}</span>' if reason else ""
    target_tag = '<span class="cf-col-name-tag" style="color: var(--green); border-color: rgba(52,211,153,0.4); background: rgba(52,211,153,0.1);">TARGET</span>' if is_target else ""

    st.markdown(
        f'<div class="{" ".join(classes)}">'
        f'  <div class="cf-col-checkbox-box"></div>'
        f'  <span class="cf-col-name">{_html_escape(col)}</span>'
        f'  {target_tag}'
        f'  {reason_tag}'
        f'</div>',
        unsafe_allow_html=True,
    )
    btn_key = f"cf_excl_btn_{col}"
    if st.button("Toggle", key=btn_key, use_container_width=True,
                 label_visibility="collapsed", disabled=is_target):
        excl = st.session_state.get("cf_excluded", set())
        if col in excl:
            excl.remove(col)
        else:
            excl.add(col)
        st.session_state["cf_excluded"] = excl
        st.rerun()


def _compute_suggestions(df: pd.DataFrame, target: str, domain_key: str) -> dict[str, str]:
    """Return {column: reason} for columns that should be auto-excluded.

    Reason codes (one per column, picked in priority order):
        PII, ID, CONST, LEAK, HIGH-CARD
    """
    suggestions: dict[str, str] = {}

    for col in df.columns:
        if col == target:
            continue  # never suggest the target

        col_lower = col.lower()

        # PII detection (especially for sensitive domains)
        if domain_key in {"healthcare", "hr", "finance"}:
            if any(kw in col_lower for kw in PII_KEYWORDS):
                suggestions[col] = "PII"
                continue

        # ID detection
        if any(kw in col_lower for kw in ID_KEYWORDS) or col_lower == "id":
            unique_ratio = df[col].nunique(dropna=False) / max(len(df), 1)
            if unique_ratio > 0.95:
                suggestions[col] = "ID"
                continue

        # Constant column
        if df[col].nunique(dropna=False) <= 1:
            suggestions[col] = "CONST"
            continue

        # Leakage risk: column name suggests it could be a future-leak (post-target columns)
        if target and col_lower in {f"{target.lower()}_after",
                                     f"post_{target.lower()}",
                                     f"{target.lower()}_outcome"}:
            suggestions[col] = "LEAK"
            continue

        # High-cardinality categorical (object with too many unique values)
        if df[col].dtype == "object":
            unique = df[col].nunique(dropna=False)
            if unique > min(1000, len(df) * 0.5):
                suggestions[col] = "HIGH-CARD"
                continue

    return suggestions


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Excluded columns ============ */
.cf-excl-helper {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
  font-size: 12px; color: var(--text-muted); flex-wrap: wrap;
}
.cf-excl-suggest-tag {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 2px 7px; background: rgba(251,191,36,0.1);
  border: 1px solid rgba(251,191,36,0.3); border-radius: 999px;
  color: var(--amber); letter-spacing: 0.5px; text-transform: uppercase;
}

.cf-col-grid {
  padding: 14px; background: rgba(7,9,26,0.25);
  border: 1px solid var(--border-subtle); border-radius: 12px;
  margin-bottom: 10px;
}
[data-theme="light"] .cf-col-grid { background: rgba(255,255,255,0.4); }

.cf-col-checkbox {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 8px; margin-bottom: 6px;
  font-size: 13px; cursor: pointer; transition: all 0.15s ease;
  user-select: none; background: transparent;
  border: 1px solid transparent; min-height: 38px;
}
.cf-col-checkbox:hover { background: rgba(139,92,246,0.06); }
.cf-col-checked {
  background: rgba(248,113,113,0.06);
  border-color: rgba(248,113,113,0.3);
  color: var(--text-muted);
}
.cf-col-checked .cf-col-name { text-decoration: line-through; }
.cf-col-suggested { border-color: rgba(251,191,36,0.25); }
.cf-col-target {
  background: rgba(52,211,153,0.08) !important;
  border-color: rgba(52,211,153,0.3) !important;
  cursor: not-allowed;
}
.cf-col-checkbox-box {
  width: 16px; height: 16px; border-radius: 4px;
  border: 1.5px solid var(--text-faint);
  display: grid; place-items: center; flex-shrink: 0;
  transition: all 0.15s ease;
}
.cf-col-checked .cf-col-checkbox-box {
  background: var(--red); border-color: var(--red);
}
.cf-col-checked .cf-col-checkbox-box::after {
  content: "✕"; color: white; font-size: 10px; font-weight: 700;
}
.cf-col-name {
  font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis;
}
.cf-col-name-tag {
  font-family: var(--font-mono); font-size: 9px;
  padding: 1px 5px; background: rgba(251,191,36,0.1);
  border: 1px solid rgba(251,191,36,0.25); border-radius: 4px;
  color: var(--amber); margin-left: 4px;
}

.cf-excl-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 10px;
  font-family: var(--font-mono); font-size: 11px; color: var(--text-faint);
}
.cf-excl-clear {
  color: var(--violet); cursor: pointer;
}
.cf-excl-clear:hover { opacity: 0.8; }
```

## Implementation note

- Suggestions are computed **once** per `(df, target)` combination using a hashable init-key, so changing the target re-computes them. This avoids losing user toggles every rerun.
- Target column is **disabled** in the grid (highlighted green with TARGET tag) — can't exclude what you're trying to predict.
- The footer count (`X excluded · Y will be analyzed`) updates live on every rerender.
