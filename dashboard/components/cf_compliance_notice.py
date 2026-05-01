"""Compliance notice banner for regulated domains in the Configure tab."""
from __future__ import annotations

import streamlit as st

COMPLIANCE_TAGS: dict[str, list[str]] = {
    "healthcare": [
        "HIPAA — check for Protected Health Information (PHI) in your columns.",
        "Clinical model decisions should be explainable.",
        "Fairness audit is required before production deployment.",
    ],
    "finance": [
        "Fair Lending (ECOA/FHA) — adverse action notices may be required.",
        "Model risk management guidelines apply (SR 11-7).",
        "KS statistic and Gini coefficient will be computed.",
    ],
    "hr": [
        "EEOC guidelines apply — protected attributes need careful handling.",
        "Compensation equity analysis may surface sensitive disparities.",
        "Anonymisation recommended for employee identifiers.",
    ],
}


def render(domain_key: str) -> None:
    """Render a compliance notice for regulated domains.

    No-ops silently for non-regulated domains.
    """
    tags = COMPLIANCE_TAGS.get(domain_key)
    if not tags:
        return

    items_html = "".join(f"<li>{t}</li>" for t in tags)
    st.markdown(
        f'<div class="cf-compliance-notice">'
        f'  <div class="cf-compliance-title">⚠ Compliance considerations</div>'
        f'  <ul class="cf-compliance-list">{items_html}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )
