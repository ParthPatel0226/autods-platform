"""4-tab source switcher for the upload page."""
from __future__ import annotations
import streamlit as st


TABS = [
    ("manual",   "Manual upload",  "\U0001f4c1"),
    ("cloud",    "Cloud storage",  "\u2601\ufe0f"),
    ("database", "Database",       "\U0001f5c4\ufe0f"),
    ("api",      "API & Web",      "\U0001f310"),
]


def render() -> str:
    """Render the source tabs. Returns the active panel key.
    State is persisted in st.session_state["upload_panel"].
    """
    active = st.session_state.get("upload_panel", "manual")

    st.markdown('<div class="up-tabs">', unsafe_allow_html=True)
    cols = st.columns(len(TABS), gap="small")
    for col, (key, label, icon) in zip(cols, TABS):
        with col:
            if st.button(f"{icon}  {label}", key=f"up_tab_{key}",
                         use_container_width=True):
                st.session_state["upload_panel"] = key
                st.rerun()
            st.markdown(
                f'<div data-up-tab="{key}" data-active="{1 if key == active else 0}"></div>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)
    return active
