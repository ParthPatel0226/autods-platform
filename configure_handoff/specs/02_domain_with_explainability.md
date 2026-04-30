# Spec 02 — Domain Cards + Explainability + Compliance

## Goal

Replace the existing "domain confirmation card + override dropdown" with **7 domain cards** rendered from the existing `DOMAIN_REGISTRY`, with the detected one highlighted. Add a **"Why was this detected?"** expander showing top 3 column-name signals. Add an automatic **compliance notice** for sensitive domains.

## Backend reuse

`domains/domain_registry.py` is the source of truth. **Open it first** to confirm the actual API. Expected interfaces (adapt component code if names differ):

```python
# domains/domain_registry.py
DOMAIN_REGISTRY: dict[str, dict]   # keyed by "healthcare", "finance", ...

# Each value is a domain config dict with keys:
#   display_name, icon, detection_keywords (strong/moderate/weak),
#   compliance_notes (list[str]), fairness (dict with required, protected_attributes, metric)

def detect_domain(df: pd.DataFrame) -> dict:
    """Returns { 'domain': str, 'confidence': float, 'signals': list[{'column': str, 'score': float}] }"""
```

If `detect_domain` doesn't return per-signal evidence, **add a sibling helper** in a new file `dashboard/components/cf_domain_signals.py` that re-runs the detection logic locally to extract signals — do NOT modify `domain_registry.py`.

## File: `dashboard/components/cf_domain_cards.py`

```python
"""7 domain cards iterating DOMAIN_REGISTRY — detected one highlighted."""
from __future__ import annotations
import streamlit as st

from domains.domain_registry import DOMAIN_REGISTRY


# Display order — detected first regardless of dict order
DOMAIN_ORDER = ["healthcare", "finance", "ecommerce", "manufacturing", "hr", "marketing", "generic"]


def render(detected_domain: str, on_select) -> str:
    """Render the 7-card grid. Returns the currently selected domain key.

    Args:
        detected_domain: Auto-detected domain key. Highlighted with "Detected" badge.
        on_select: Callable(domain_key) invoked when user picks a different card.
    """
    selected = st.session_state.get("cf_selected_domain", detected_domain)

    st.markdown('<div class="cf-domain-grid">', unsafe_allow_html=True)
    cols = st.columns(7, gap="small")
    for col, key in zip(cols, DOMAIN_ORDER):
        config = DOMAIN_REGISTRY.get(key, {})
        if not config:
            continue
        with col:
            _render_card(key, config, detected_domain, selected, on_select)
    st.markdown('</div>', unsafe_allow_html=True)
    return selected


def _render_card(key: str, config: dict, detected: str, selected: str, on_select) -> None:
    is_detected = key == detected
    is_selected = key == selected

    classes = ["cf-domain-card"]
    if is_detected: classes.append("cf-detected")
    if is_selected: classes.append("cf-selected")

    badge = '<div class="cf-domain-badge">Detected</div>' if is_detected else ""
    icon = config.get("icon", "📊")
    name = config.get("display_name", key.title())

    st.markdown(
        f'<div class="{" ".join(classes)}" data-domain="{key}">'
        f'  {badge}'
        f'  <div class="cf-domain-icon">{icon}</div>'
        f'  <div class="cf-domain-name">{name}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Select {name}", key=f"cf_dom_{key}",
                 use_container_width=True, label_visibility="collapsed"):
        st.session_state["cf_selected_domain"] = key
        on_select(key)
```

## File: `dashboard/components/cf_domain_why.py`

```python
"""Explainability panel — top 3 column-name signals with confidence bars."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from domains.domain_registry import DOMAIN_REGISTRY


def render(domain_key: str, df: pd.DataFrame) -> None:
    """Render the 'Why [domain]?' expander.

    Args:
        domain_key: Currently selected domain.
        df: The loaded dataframe.
    """
    config = DOMAIN_REGISTRY.get(domain_key)
    if not config:
        return

    name = config.get("display_name", domain_key.title())
    expanded = st.session_state.get("cf_why_expanded", False)

    if st.button(f"  Why {name}?  ", key="cf_why_btn"):
        st.session_state["cf_why_expanded"] = not expanded
        st.rerun()

    if not expanded:
        return

    signals = _compute_signals(domain_key, df, top_n=3)

    st.markdown('<div class="cf-why-panel">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="cf-why-title">'
        f'  <span style="color: var(--green);">✓</span>'
        f'  Top signals from your column names'
        f'</div>'
        f'<div class="cf-why-signals">',
        unsafe_allow_html=True,
    )
    for sig in signals:
        st.markdown(
            f'<div class="cf-why-signal">'
            f'  <div class="cf-why-signal-col">{_html_escape(sig["column"])}</div>'
            f'  <div class="cf-why-signal-bar"><div class="cf-why-signal-fill" style="width:{int(sig["score"] * 100)}%"></div></div>'
            f'  <div class="cf-why-signal-pct">{int(sig["score"] * 100)}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer summary
    if signals:
        avg_conf = sum(s["score"] for s in signals) / len(signals)
        st.markdown(
            f'<div class="cf-why-footer">'
            f'  Combined confidence: <strong style="color: var(--green);">{int(avg_conf * 100)}%</strong>. '
            f'  AutoDS will apply {name.lower()}-specific feature engineering, fairness audits, and report styling.'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def _compute_signals(domain_key: str, df: pd.DataFrame, top_n: int = 3) -> list[dict]:
    """Score each column against the domain's keywords. Return top N."""
    config = DOMAIN_REGISTRY.get(domain_key, {})
    keywords = config.get("detection_keywords", {})
    strong = set(k.lower() for k in keywords.get("strong", []))
    moderate = set(k.lower() for k in keywords.get("moderate", []))
    weak = set(k.lower() for k in keywords.get("weak", []))

    scores = []
    for col in df.columns:
        col_lower = col.lower()
        score = 0.0
        for kw in strong:
            if kw in col_lower:
                score = max(score, 0.95)
        for kw in moderate:
            if kw in col_lower:
                score = max(score, 0.7)
        for kw in weak:
            if kw in col_lower:
                score = max(score, 0.4)
        if score > 0:
            scores.append({"column": col, "score": score})

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top_n]


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/cf_compliance_notice.py`

```python
"""Compliance notice card — auto-shown for Healthcare / Finance / HR."""
from __future__ import annotations
import streamlit as st

from domains.domain_registry import DOMAIN_REGISTRY


# Compliance metadata not always in domain config — supplement here
COMPLIANCE_TAGS = {
    "healthcare": ["HIPAA Aware", "Fairness Audit", "PHI Detection"],
    "finance":    ["Fair Lending", "Adverse Action", "Disparate Impact"],
    "hr":         ["Anonymization", "Compensation Equity", "Diversity Audit"],
}
COMPLIANCE_TITLE = {
    "healthcare": "Healthcare compliance mode will activate",
    "finance":    "Finance compliance mode will activate",
    "hr":         "HR sensitivity mode will activate",
}
COMPLIANCE_TEXT = {
    "healthcare": "PHI-aware processing, demographic fairness audits, and HIPAA-conscious report styling will be applied. AutoDS is not a certified HIPAA system — this is informational guidance only.",
    "finance":    "Fair-lending compliance, adverse action notices, and demographic fairness audits will be enabled. AutoDS is not certified for regulatory submission — verify outputs with your compliance team.",
    "hr":         "Anonymization, sensitivity constraints, and compensation equity audits will be applied. Personal identifiers and protected attributes are auto-flagged for exclusion.",
}


def render(domain_key: str) -> None:
    """Render compliance notice if domain is sensitive."""
    if domain_key not in COMPLIANCE_TAGS:
        return  # Non-sensitive domains: silent

    tags_html = "".join(
        f'<span class="cf-compliance-tag">{t}</span>'
        for t in COMPLIANCE_TAGS[domain_key]
    )

    st.markdown(
        f'<div class="cf-compliance-notice">'
        f'  <div class="cf-compliance-icon">🛡</div>'
        f'  <div>'
        f'    <div class="cf-compliance-title">{COMPLIANCE_TITLE[domain_key]}</div>'
        f'    <div class="cf-compliance-text">{COMPLIANCE_TEXT[domain_key]}</div>'
        f'    <div class="cf-compliance-tags">{tags_html}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
```

## CSS additions

```css
/* ============ Domain cards ============ */
.cf-domain-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.cf-domain-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 16px; text-align: center; cursor: pointer;
  transition: all 0.2s ease; backdrop-filter: blur(14px);
  position: relative; overflow: hidden; min-height: 100px;
}
.cf-domain-card:hover { transform: translateY(-2px); border-color: var(--border-strong); }
.cf-domain-card.cf-detected {
  background: rgba(139,92,246,0.12);
  border-color: var(--violet);
  box-shadow: 0 0 20px -4px var(--violet);
}
.cf-domain-card.cf-selected {
  background: rgba(139,92,246,0.18);
  border-color: var(--violet);
  box-shadow: 0 0 24px -4px var(--violet);
}
.cf-domain-card.cf-detected.cf-selected { box-shadow: 0 0 28px -3px var(--violet); }
.cf-domain-badge {
  position: absolute; top: 6px; right: 6px;
  font-family: var(--font-mono); font-size: 9px;
  padding: 2px 6px; background: var(--gradient-button); color: white;
  border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase;
}
.cf-domain-icon { font-size: 26px; margin-bottom: 8px; }
.cf-domain-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }

/* Hide the underlying Streamlit button that drives card click */
.cf-domain-grid + div [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
  position: absolute !important; opacity: 0; pointer-events: auto;
  inset: 0; width: 100%; height: 100%; cursor: pointer;
}

/* ============ Why? expander ============ */
[data-testid="stMain"] .stButton > button[key="cf_why_btn"] {
  display: inline-flex !important; align-items: center; gap: 6px;
  background: transparent !important; border: none !important;
  color: var(--violet) !important;
  font-family: var(--font-body) !important; font-size: 12.5px !important;
  cursor: pointer; padding: 6px 0 !important;
  box-shadow: none !important;
}
[data-testid="stMain"] .stButton > button[key="cf_why_btn"]:hover { opacity: 0.8; }

.cf-why-panel {
  background: rgba(139,92,246,0.04);
  border: 1px solid var(--border-subtle);
  border-radius: 12px; padding: 16px 18px; margin-top: 8px;
  animation: cf-fadeUp 0.25s ease;
}
@keyframes cf-fadeUp {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
.cf-why-title {
  font-size: 12px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
}
.cf-why-signals { display: flex; flex-direction: column; gap: 6px; }
.cf-why-signal {
  display: flex; align-items: center; gap: 10px;
  font-size: 12.5px; color: var(--text-secondary);
}
.cf-why-signal-bar {
  flex: 1; height: 4px; background: rgba(139,92,246,0.1);
  border-radius: 2px; overflow: hidden;
}
.cf-why-signal-fill {
  height: 100%;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-radius: 2px;
}
.cf-why-signal-col {
  font-family: var(--font-mono); font-size: 11px; color: var(--violet);
  padding: 2px 8px; background: rgba(139,92,246,0.08);
  border-radius: 6px; min-width: 110px; text-align: center;
}
.cf-why-signal-pct {
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); min-width: 36px;
}
.cf-why-footer {
  font-size: 12px; color: var(--text-muted); margin-top: 12px;
}

/* ============ Compliance notice ============ */
.cf-compliance-notice {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 16px 20px; margin-top: 16px;
  background: rgba(34,211,238,0.06);
  border: 1px solid rgba(34,211,238,0.3);
  border-radius: 12px;
}
.cf-compliance-icon {
  width: 32px; height: 32px; flex-shrink: 0;
  background: rgba(34,211,238,0.12); border-radius: 50%;
  display: grid; place-items: center; color: var(--cyan);
  font-size: 16px;
}
.cf-compliance-title {
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 4px;
}
.cf-compliance-text {
  font-size: 12.5px; color: var(--text-muted); line-height: 1.5;
}
.cf-compliance-tags {
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
}
.cf-compliance-tag {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 2px 8px; background: rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.3);
  border-radius: 999px; color: var(--cyan);
  letter-spacing: 0.5px; text-transform: uppercase;
}
```

## Implementation notes

- Streamlit doesn't natively support clicking arbitrary HTML divs, so the pattern is: render the visual card with `st.markdown`, then render an invisible full-card button right after that handles the click. The CSS above positions the button absolutely over the card. If your Streamlit version doesn't render this cleanly, fall back to: render the markdown card, then render a normal "Select [Name]" button below it (the mockup shows the visual; the implementation can adapt).
- The `cf_domain_why.py` component re-implements signal scoring locally so it doesn't need a new function in `domain_registry.py`. If `detect_domain()` already returns signals, prefer that path.
- Compliance metadata is **supplemented** in `cf_compliance_notice.py` rather than reading from `domain_config.compliance_notes` because the existing notes are oriented toward developers, not user-facing. If you'd rather use the in-config notes, swap to read from `DOMAIN_REGISTRY[key].get("compliance_notes", [])` and render those instead.
