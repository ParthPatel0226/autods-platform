"""Featured chart — correlation heatmap with target row highlighted."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    df = st.session_state.get("df")
    project = project_service.get_active()
    if df is None or df.empty:
        return

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return

    # Limit to top N most variant columns + target
    n_cols = min(7, numeric_df.shape[1])
    top_cols = list(numeric_df.var().sort_values(ascending=False).index[:n_cols])
    target = project.target_column if project else None
    if target and target in numeric_df.columns and target not in top_cols:
        top_cols = top_cols[:-1] + [target]

    corr = numeric_df[top_cols].corr().round(2)
    actual_n = len(top_cols)

    # Render as HTML grid
    cells_html = f'<div class="ed-heatmap" style="grid-template-columns: 100px repeat({actual_n}, 1fr);">'
    cells_html += '<div></div>'  # corner
    for c in top_cols:
        is_target = c == target
        label_style = ' style="color: var(--violet);"' if is_target else ""
        cells_html += f'<div class="ed-hm-label"{label_style}>{_short(c)}</div>'

    for row in top_cols:
        cells_html += f'<div class="ed-hm-label">{_short(row)}</div>'
        for col in top_cols:
            v = float(corr.loc[row, col])
            klass = _bucket(v)
            cells_html += f'<div class="ed-hm-cell {klass}">{v:.1f}</div>'
    cells_html += '</div>'

    st.markdown(
        '<section>'
        '  <div class="ed-sec">'
        '    <h3>Featured <em>chart</em></h3>'
        '    <span class="ed-sec-meta">Correlation heatmap · numeric columns</span>'
        '  </div>'
        '  <div class="ed-featured">'
        '    <div class="ed-featured-head">'
        '      <div>'
        '        <div class="ed-featured-title">Pearson correlation matrix</div>'
        f'        <div class="ed-chart-sub" style="margin-top:4px;">{actual_n} numeric columns · target highlighted</div>'
        '      </div>'
        '      <span class="ed-featured-tag">Featured</span>'
        '    </div>'
        f'    {cells_html}'
        '  </div>'
        '</section>',
        unsafe_allow_html=True,
    )


def _short(name: str) -> str:
    return name if len(name) <= 8 else name[:6] + "…"


def _bucket(v: float) -> str:
    """Map -1..1 correlation to a color-bucket CSS class."""
    if v >= 0.95: return "h-100"
    if v >= 0.7:  return "h-80"
    if v >= 0.5:  return "h-60"
    if v >= 0.3:  return "h-40"
    if v >= 0.1:  return "h-20"
    if v >= -0.1: return "h-0"
    if v >= -0.5: return "h-n20"
    return "h-n60"
