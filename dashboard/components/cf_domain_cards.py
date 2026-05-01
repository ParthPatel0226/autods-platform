"""Domain confirmation card grid for the Configure tab."""
from __future__ import annotations
import streamlit as st

from dashboard.components.cf_domain_adapter import DOMAIN_REGISTRY

DOMAIN_ORDER = ["healthcare", "finance", "ecommerce", "manufacturing", "hr", "marketing", "generic"]


def render(detected_domain: str, on_select) -> str:
    """Render 7 domain cards. Returns the currently selected domain key.

    State key: st.session_state["cf_selected_domain"]
    """
    selected = st.session_state.get("cf_selected_domain", detected_domain)

    # Build HTML grid — cards are visual only; invisible buttons overlay for click
    cards_html = '<div class="cf-domain-grid">'
    for key in DOMAIN_ORDER:
        cfg = DOMAIN_REGISTRY.get(key, {})
        icon = cfg.get("icon", "📊")
        label = cfg.get("display_name", key.title())

        is_selected = key == selected
        is_detected = key == detected_domain

        classes = "cf-domain-card"
        if is_detected:
            classes += " cf-detected"
        if is_selected:
            classes += " cf-selected"

        detected_badge = '<span class="cf-domain-badge">Auto</span>' if is_detected else ""

        cards_html += (
            f'<div class="{classes}">'
            f'  {detected_badge}'
            f'  <div class="cf-domain-icon">{icon}</div>'
            f'  <div class="cf-domain-name">{label}</div>'
            f'</div>'
        )
    cards_html += "</div>"

    # CSS: push the st.columns button row on top of the grid, make it invisible
    overlay_css = (
        "<style>"
        ".stMarkdown:has(.cf-domain-grid) + [data-testid=\"stHorizontalBlock\"] {"
        "  margin-top: -88px !important;"
        "  opacity: 0 !important;"
        "  position: relative !important;"
        "  z-index: 5 !important;"
        "  height: 88px !important;"
        "  overflow: hidden !important;"
        "}"
        "</style>"
    )

    st.markdown(cards_html + overlay_css, unsafe_allow_html=True)

    # Invisible but clickable buttons — same order as grid cells
    cols = st.columns(len(DOMAIN_ORDER))
    for col, key in zip(cols, DOMAIN_ORDER):
        cfg = DOMAIN_REGISTRY.get(key, {})
        label = cfg.get("display_name", key.title())
        with col:
            if st.button(label, key=f"cf_domain_btn_{key}", use_container_width=True):
                st.session_state["cf_selected_domain"] = key
                on_select(key)
                st.rerun()

    return st.session_state.get("cf_selected_domain", detected_domain)
