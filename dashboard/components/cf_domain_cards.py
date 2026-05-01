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

    cols = st.columns(len(DOMAIN_ORDER), gap="small")
    for col, key in zip(cols, DOMAIN_ORDER):
        cfg = DOMAIN_REGISTRY.get(key, {})
        icon = cfg.get("icon", "📊")
        label = cfg.get("display_name", key.title())

        is_selected = key == selected
        is_detected = key == detected_domain

        classes = ["cf-domain-card"]
        if is_detected:
            classes.append("cf-detected")
        if is_selected:
            classes.append("cf-selected")

        detected_badge = (
            '<span class="cf-domain-badge">Auto</span>' if is_detected else ""
        )

        with col:
            st.markdown(
                f'<div class="{" ".join(classes)}">'
                f'  {detected_badge}'
                f'  <div class="cf-domain-icon">{icon}</div>'
                f'  <div class="cf-domain-name">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                label,
                key=f"cf_domain_btn_{key}",
                use_container_width=True,
                label_visibility="collapsed",
            ):
                st.session_state["cf_selected_domain"] = key
                on_select(key)
                st.rerun()

    return st.session_state.get("cf_selected_domain", detected_domain)
