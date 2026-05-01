"""Analysis mode selection cards for the Configure tab."""
from __future__ import annotations

import streamlit as st

MODE_INFO: list[dict] = [
    {
        "key": "auto",
        "label": "Auto",
        "icon": "⚡",
        "desc": "Let the AI decide everything. Fastest path to results.",
        "recommended": False,
    },
    {
        "key": "guided",
        "label": "Guided",
        "icon": "🧭",
        "desc": "Answer a few smart questions. Best balance of control and speed.",
        "recommended": True,
    },
    {
        "key": "expert",
        "label": "Expert",
        "icon": "🔬",
        "desc": "Full control over every decision. For experienced practitioners.",
        "recommended": False,
    },
]


def render(on_change=None) -> str:
    """Render 3 mode cards.

    State key: cf_mode (default 'guided')
    Returns selected mode key.
    """
    selected = st.session_state.get("cf_mode", "guided")
    cols = st.columns(len(MODE_INFO), gap="small")

    for col, info in zip(cols, MODE_INFO):
        key = info["key"]
        is_sel = key == selected
        classes = "cf-mode-card" + (" cf-mode-selected" if is_sel else "")
        rec_badge = '<span class="cf-mode-recommended">Recommended</span>' if info["recommended"] else ""

        with col:
            st.markdown(
                f'<div class="{classes}">'
                f'  {rec_badge}'
                f'  <div class="cf-mode-icon">{info["icon"]}</div>'
                f'  <div class="cf-mode-label">{info["label"]}</div>'
                f'  <div class="cf-mode-desc">{info["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(info["label"], key=f"cf_mode_btn_{key}", use_container_width=True, label_visibility="collapsed"):
                st.session_state["cf_mode"] = key
                if on_change:
                    on_change(key)
                st.rerun()

    return st.session_state.get("cf_mode", "guided")
