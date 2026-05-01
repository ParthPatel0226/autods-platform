"""Domain-detection explainability panel for the Configure tab."""
from __future__ import annotations

import streamlit as st

from dashboard.components.cf_domain_adapter import DOMAIN_REGISTRY


def _compute_signals(domain_key: str, df, top_n: int = 3) -> list[dict]:
    """Score columns against domain keywords and return top_n signals."""
    cfg = DOMAIN_REGISTRY.get(domain_key, {})
    kw = cfg.get("detection_keywords", {})
    strong = [k.lower() for k in kw.get("strong", [])]
    moderate = [k.lower() for k in kw.get("moderate", [])]
    weak = [k.lower() for k in kw.get("weak", [])]

    scores: list[dict] = []
    cols = list(df.columns) if df is not None else []
    for col in cols:
        col_l = col.lower()
        if any(k in col_l for k in strong):
            scores.append({"col": col, "weight": "strong", "conf": 1.0})
        elif any(k in col_l for k in moderate):
            scores.append({"col": col, "weight": "moderate", "conf": 0.6})
        elif any(k in col_l for k in weak):
            scores.append({"col": col, "weight": "weak", "conf": 0.3})

    scores.sort(key=lambda x: -x["conf"])
    return scores[:top_n]


def render(domain_key: str, df) -> None:
    """Render a collapsible 'Why this domain?' panel.

    State key: cf_why_expanded (bool)
    """
    if not domain_key:
        return

    cfg = DOMAIN_REGISTRY.get(domain_key, {})
    display_name = cfg.get("display_name", domain_key.title())
    icon = cfg.get("icon", "📊")

    expanded = st.session_state.get("cf_why_expanded", False)

    toggle_label = "▾ Why this domain?" if expanded else "▸ Why this domain?"
    if st.button(toggle_label, key="cf_why_toggle"):
        st.session_state["cf_why_expanded"] = not expanded
        st.rerun()

    if not expanded:
        return

    signals = _compute_signals(domain_key, df)
    if not signals:
        st.markdown(
            f'<div class="cf-why-panel">'
            f'Detected as <strong>{icon} {display_name}</strong> based on dataset structure.'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for s in signals:
        pct = int(s["conf"] * 100)
        color = (
            "var(--green)" if s["weight"] == "strong"
            else "var(--amber)" if s["weight"] == "moderate"
            else "var(--text-muted)"
        )
        rows_html += (
            f'<div class="cf-signal-row">'
            f'  <span class="cf-signal-col">{s["col"]}</span>'
            f'  <div class="cf-signal-bar-wrap">'
            f'    <div class="cf-signal-bar" style="width:{pct}%;background:{color}"></div>'
            f'  </div>'
            f'  <span class="cf-signal-label">{s["weight"]}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="cf-why-panel">'
        f'<div class="cf-why-title">Top signals for {icon} {display_name}</div>'
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
