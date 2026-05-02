"""Target distribution callout — highlights class imbalance for classification."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    df = st.session_state.get("df")
    if not project or df is None or df.empty:
        return

    target = project.target_column
    if not target or target not in df.columns:
        return

    s = df[target].dropna()
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > 10:
        # Numeric continuous target — render a brief skewness summary instead
        _render_numeric_callout(target, s)
        return

    # Categorical / boolean target → class balance bar
    counts = s.value_counts()
    total = len(s)
    if len(counts) < 2:
        return
    minority_pct = float(counts.min()) / total * 100
    is_imbalanced = minority_pct < 30

    bars_html = ""
    legend_html = ""
    palette = ["rgba(99,102,241,0.6)", "rgba(236,72,153,0.7)",
               "rgba(168,85,247,0.6)", "rgba(34,211,238,0.6)"]
    for i, (val, count) in enumerate(counts.items()):
        pct = count / total * 100
        color = palette[i % len(palette)]
        bars_html += f'<div class="ed-tc-bar" style="flex: {pct}; background: {color};">{_html_escape(str(val))} ({pct:.1f}%)</div>'
        legend_html += (
            f'<span><span class="ed-tc-dot" style="background: {color};"></span>'
            f'{count:,} {_html_escape(str(val))}</span>'
        )

    pill = ('<span class="ed-tc-pill warn">Imbalanced</span>' if is_imbalanced
            else '<span class="ed-tc-pill">Balanced</span>')
    sub = (f"Class imbalance — minority class is {minority_pct:.1f}% of records. "
           "Consider stratified sampling and class weights." if is_imbalanced
           else "Classes appear well-balanced.")

    st.markdown(
        f'<div class="ed-target-callout">'
        f'  <div class="ed-tc-head">'
        f'    <div>'
        f'      <div class="ed-tc-title">🎯 Target distribution: {_html_escape(target)}</div>'
        f'      <div class="ed-tc-sub">{sub}</div>'
        f'    </div>'
        f'    {pill}'
        f'  </div>'
        f'  <div class="ed-tc-bars">{bars_html}</div>'
        f'  <div class="ed-tc-legend">{legend_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_numeric_callout(target: str, s: pd.Series) -> None:
    skew = s.skew()
    skew_label = "Right-skewed" if skew > 1 else ("Left-skewed" if skew < -1 else "Approximately symmetric")
    st.markdown(
        f'<div class="ed-target-callout">'
        f'  <div class="ed-tc-head">'
        f'    <div>'
        f'      <div class="ed-tc-title">🎯 Target distribution: {_html_escape(target)}</div>'
        f'      <div class="ed-tc-sub">{skew_label} (skew = {skew:.2f}). Mean = {s.mean():.2f}, median = {s.median():.2f}.</div>'
        f'    </div>'
        f'    <span class="ed-tc-pill">Continuous</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
