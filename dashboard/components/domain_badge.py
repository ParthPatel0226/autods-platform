"""Domain Badge -- displays the detected industry domain with icon and confidence.

Optionally allows the user to override the detected domain via a selectbox.
"""

from typing import Final

import streamlit as st

from core.constants import VALID_DOMAINS

_DOMAIN_DISPLAY: Final[dict[str, dict[str, str]]] = {
    "healthcare":    {"icon": "hospital", "color": "#ef4444", "label": "Healthcare"},
    "finance":       {"icon": "bank",     "color": "#eab308", "label": "Finance"},
    "ecommerce":     {"icon": "shopping_trolley", "color": "#22c55e", "label": "E-Commerce"},
    "marketing":     {"icon": "bar_chart", "color": "#3b82f6", "label": "Marketing"},
    "hr":            {"icon": "people",   "color": "#8b5cf6", "label": "Human Resources"},
    "manufacturing": {"icon": "factory",  "color": "#f97316", "label": "Manufacturing"},
    "generic":       {"icon": "trending_up", "color": "#6b7280", "label": "General Analytics"},
}


def render_domain_badge(
    domain: str,
    confidence: float = 0.0,
    allow_override: bool = True,
) -> str:
    """Show the detected domain badge with confidence and optional override.

    Args:
        domain: Detected domain key (e.g. ``"healthcare"``).
        confidence: Detection confidence between 0.0 and 1.0.
        allow_override: Whether to show a selectbox for manual override.

    Returns:
        The final domain string (original or overridden).
    """
    info = _DOMAIN_DISPLAY.get(domain, _DOMAIN_DISPLAY["generic"])

    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 0.5rem;
                    padding: 0.5rem 1rem; border-radius: 2rem;
                    border: 2px solid {info['color']}; background: {info['color']}15;">
            <span style="font-weight: 600; color: {info['color']};">
                :{info['icon']}: {info['label']}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if confidence > 0:
        st.progress(confidence, text=f"Detection confidence: {confidence:.0%}")

    final_domain = domain

    if allow_override:
        domain_labels = [
            _DOMAIN_DISPLAY.get(d, _DOMAIN_DISPLAY["generic"])["label"]
            for d in VALID_DOMAINS
        ]
        label_to_key = dict(zip(domain_labels, VALID_DOMAINS))
        current_label = info["label"]

        override = st.selectbox(
            "Override domain",
            options=domain_labels,
            index=domain_labels.index(current_label) if current_label in domain_labels else len(domain_labels) - 1,
            key="domain_override_select",
            help="Change the detected domain if the auto-detection is incorrect.",
        )
        final_domain = label_to_key.get(override, domain)

    return final_domain
