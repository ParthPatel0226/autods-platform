"""Quality flags grid — outliers (amber) + modeling red flags (red)."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    flags = st.session_state.get("eda_quality_flags", {})
    outliers = flags.get("outliers", [])
    red_flags = flags.get("red_flags", [])
    if not outliers and not red_flags:
        return

    st.markdown(
        '<section>'
        '  <div class="ed-sec">'
        '    <h3>Quality <em>flags</em></h3>'
        '    <span class="ed-sec-meta">Issues to address before modeling</span>'
        '  </div>'
        '</section>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2, gap="medium")
    with cols[0]:
        _render_flag_card(
            kind="outliers",
            title="Outliers detected",
            count_label=f"{len(outliers)} columns",
            items=outliers,
            icon_svg='<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        )
    with cols[1]:
        _render_flag_card(
            kind="redflags",
            title="Modeling red flags",
            count_label=f"{len(red_flags)} issues",
            items=red_flags,
            icon_svg='<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
        )


def _render_flag_card(kind: str, title: str, count_label: str, items: list[dict], icon_svg: str) -> None:
    items_html = ""
    for it in items:
        col = _html_escape(str(it.get("column", "—")))
        stat = _html_escape(str(it.get("description", "")))
        items_html += (
            f'<div class="ed-flag-item">'
            f'  <span class="ed-flag-col">{col}</span>'
            f'  <span class="ed-flag-stat">{stat}</span>'
            f'  <span class="ed-flag-action">{"Investigate →" if kind == "outliers" else "Review →"}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="ed-flag-card {kind}">'
        f'  <div class="ed-flag-head">'
        f'    {icon_svg}'
        f'    <div class="ed-flag-title">{title}</div>'
        f'    <span class="ed-flag-count">{count_label}</span>'
        f'  </div>'
        f'  <div class="ed-flag-list">{items_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
