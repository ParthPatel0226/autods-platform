"""Dataset recap strip -- read-only summary shown at the top of Configure."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render() -> None:
    """Render a compact stat strip from the currently loaded df + project."""
    project = project_service.get_active()
    df = st.session_state.get("df")
    if project is None or df is None:
        return

    n_rows, n_cols = df.shape
    n_num = int((df.dtypes.apply(lambda d: d.kind in "biufc")).sum())
    n_dt = int((df.dtypes.apply(lambda d: d.kind == "M")).sum())
    n_cat = n_cols - n_num - n_dt
    total_cells = n_rows * n_cols
    miss_pct = (
        f"{df.isnull().sum().sum() / total_cells * 100:.1f}%" if total_cells else "0%"
    )
    sources = st.session_state.get("multisource", {}).get("files", [])
    n_sources = max(1, len([f for f in sources if f.get("role") in ("primary", "secondary")]))

    fname = project.dataset_name or "dataset"

    st.markdown(
        '<div class="cf-recap-strip">'
        f'  <div class="cf-recap-item">'
        f'    <span class="cf-recap-label">Dataset</span>'
        f'    <span class="cf-recap-value cf-recap-fname">{_html_escape(fname)}</span>'
        f'    <span class="cf-recap-sub">{n_rows:,} rows · {n_cols} cols</span>'
        f'  </div>'
        f'  <div class="cf-recap-item">'
        f'    <span class="cf-recap-label">Rows</span>'
        f'    <span class="cf-recap-value">{n_rows:,}</span>'
        f'  </div>'
        f'  <div class="cf-recap-item">'
        f'    <span class="cf-recap-label">Columns</span>'
        f'    <span class="cf-recap-value">{n_cols}</span>'
        f'    <span class="cf-recap-sub">{n_num} num · {n_cat} cat · {n_dt} dt</span>'
        f'  </div>'
        f'  <div class="cf-recap-item">'
        f'    <span class="cf-recap-label">Missing</span>'
        f'    <span class="cf-recap-value">{miss_pct}</span>'
        f'  </div>'
        f'  <div class="cf-recap-item">'
        f'    <span class="cf-recap-label">Sources</span>'
        f'    <span class="cf-recap-value">{n_sources}</span>'
        f'  </div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
