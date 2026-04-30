# Spec 06 — Fairness Audit + Adverse Action

## Backend reuse

- `explainability/fairness_audit.py` — `run_fairness_audit(model, X, y, protected_attrs, metric)` returns fairness metrics per group. **Open first.**
- `explainability/adverse_action.py` — `generate_adverse_action(model, instance, feature_names, top_n=5)` returns ranked reasons. Finance-domain only.
- `domains/<domain>.py` — `fairness.protected_attributes` and `fairness.metric` fields in each domain config.

## File: `dashboard/components/ex_fairness_audit.py`

```python
"""Fairness audit — 3 metric cards + group bars + domain-aware compliance + summary."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service
from dashboard.components.ex_audience_switcher import get_audience
from domains.domain_registry import DOMAIN_REGISTRY


METRIC_THRESHOLDS = {
    "disparate_impact": {"pass": 0.80, "label": "Disparate Impact Ratio", "direction": "higher_is_better"},
    "equal_opportunity": {"pass": 0.10, "label": "Equal Opportunity Diff", "direction": "lower_is_better"},
    "predictive_parity": {"pass": 0.05, "label": "Predictive Parity Diff", "direction": "lower_is_better"},
}

COMPLIANCE_CONTEXT = {
    "healthcare": ("HIPAA-aware fairness thresholds", "🏥"),
    "finance": ("Fair lending compliance (ECOA / Reg B)", "💳"),
    "hr": ("Employment discrimination monitoring (EEOC)", "👥"),
}


def render(fairness_data: dict, summary_text: str = "") -> None:
    """Render the Fairness Audit tab.

    Args:
        fairness_data: dict with:
            metrics: list[{"name": str, "value": float, "groups": list[{"label": str, "rate": float}]}]
            protected_attributes: list[str]
        summary_text: LLM-generated fairness summary
    """
    project = project_service.get_active()
    domain = (project.confirmed_domain or project.detected_domain or "generic") if project else "generic"

    if not fairness_data or not fairness_data.get("metrics"):
        st.info("Fairness audit not run. Requires protected attribute columns in the dataset.")
        return

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Fairness <em>audit</em></h3>'
        f'<span class="ex-sec-meta">{COMPLIANCE_CONTEXT.get(domain, ("Standard fairness metrics", "⚖"))[0]} · '
        f'{len(fairness_data.get("protected_attributes", []))} protected attributes</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Metric cards grid
    metrics = fairness_data["metrics"]
    cols = st.columns(min(3, len(metrics)), gap="medium")

    for col, metric in zip(cols, metrics[:3]):
        with col:
            _render_metric_card(metric, domain)

    # Domain-specific compliance note
    if domain in COMPLIANCE_CONTEXT:
        label, icon = COMPLIANCE_CONTEXT[domain]
        st.markdown(
            f'<div class="ex-compliance-note">'
            f'  <span>{icon}</span> {label}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Plain English summary
    if summary_text:
        st.markdown(
            f'<div class="ex-plain-english">'
            f'  <h3>⚖ Fairness <em>summary</em></h3>'
            f'  <p>{summary_text}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_metric_card(metric: dict, domain: str) -> None:
    name = metric["name"]
    value = metric["value"]
    groups = metric.get("groups", [])

    threshold_info = METRIC_THRESHOLDS.get(name, {})
    threshold = threshold_info.get("pass", 0.80)
    direction = threshold_info.get("direction", "higher_is_better")
    label = threshold_info.get("label", name.replace("_", " ").title())

    if direction == "higher_is_better":
        passed = value >= threshold
        status_text = f"✓ Pass (> {threshold})" if passed else f"✗ Fail (< {threshold})"
    else:
        passed = value <= threshold
        status_text = f"✓ Pass (< {threshold})" if passed else f"✗ Fail (> {threshold})"

    if passed:
        status_class = "ex-fairness-pass"
        value_color = "var(--green)"
    elif direction == "lower_is_better" and value <= threshold * 2:
        status_class = "ex-fairness-warn"
        value_color = "var(--amber)"
        status_text = f"⚠ Marginal (< {threshold * 2})"
    else:
        status_class = "ex-fairness-fail"
        value_color = "var(--red)"

    # Group bars
    palette = ["var(--indigo)", "var(--pink)", "var(--cyan)", "var(--amber)", "var(--green)"]
    bars_html = ""
    for i, g in enumerate(groups):
        color = palette[i % len(palette)]
        bar_pct = g["rate"] * 100
        bars_html += (
            f'<div class="ex-fb-row">'
            f'  <div class="ex-fb-label">{_html_escape(g["label"])}</div>'
            f'  <div class="ex-fb-track"><div class="ex-fb-fill" style="width:{bar_pct:.0f}%;background:{color};"></div></div>'
            f'  <div class="ex-fb-val">{bar_pct:.1f}%</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="ex-fairness-card">'
        f'  <div class="ex-fairness-metric-label">{label}</div>'
        f'  <div class="ex-fairness-metric-value" style="color:{value_color};">{value:.2f}</div>'
        f'  <span class="ex-fairness-status {status_class}">{status_text}</span>'
        f'  <div class="ex-fairness-bar-group">{bars_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ex_adverse_action.py`

```python
"""Adverse action reasons — Finance domain only."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render(adverse_data: list[dict]) -> None:
    """Render adverse action reasons. Only shown for Finance domain.

    Args:
        adverse_data: list[{"reason": str, "feature": str, "value": str, "threshold": str}]
    """
    project = project_service.get_active()
    domain = (project.confirmed_domain or project.detected_domain or "generic") if project else "generic"

    if domain != "finance" or not adverse_data:
        return  # silent — only renders for finance

    st.markdown(
        '<div class="ex-adverse-card">'
        '  <div class="ex-adverse-title">⚠ Adverse action reason codes</div>',
        unsafe_allow_html=True,
    )

    for i, reason in enumerate(adverse_data[:5], start=1):
        st.markdown(
            f'<div class="ex-adverse-reason">'
            f'  <div class="ex-adverse-num">{i}</div>'
            f'  <div class="ex-adverse-text">'
            f'    <strong>{_html_escape(reason.get("feature", ""))}</strong>: '
            f'    {_html_escape(reason.get("reason", ""))}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Fairness ============ */
.ex-fairness-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 20px; backdrop-filter: blur(14px); height: 100%; }
.ex-fairness-metric-label { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.ex-fairness-metric-value { font-family: var(--font-display); font-size: 36px; line-height: 1; margin-bottom: 6px; }
.ex-fairness-status { display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px; font-family: var(--font-mono);
  font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; }
.ex-fairness-pass { color: var(--green); background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.ex-fairness-fail { color: var(--red); background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3); }
.ex-fairness-warn { color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.ex-fairness-bar-group { margin-top: 14px; }
.ex-fb-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
.ex-fb-label { font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); width: 80px; }
.ex-fb-track { flex: 1; height: 8px; background: rgba(139,92,246,0.08); border-radius: 4px; overflow: hidden; }
.ex-fb-fill { height: 100%; border-radius: 4px; }
.ex-fb-val { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); width: 45px; text-align: right; }

.ex-compliance-note { display: flex; align-items: center; gap: 8px;
  padding: 12px 18px; margin: 14px 0;
  background: rgba(34,211,238,0.04); border: 1px solid rgba(34,211,238,0.2);
  border-radius: 10px; font-size: 12.5px; color: var(--text-secondary); }

/* ============ Adverse action ============ */
.ex-adverse-card { background: linear-gradient(135deg, rgba(251,191,36,0.06), rgba(248,113,113,0.04));
  border: 1px solid rgba(251,191,36,0.3); border-radius: 16px; padding: 22px; margin-bottom: 24px; }
.ex-adverse-title { font-size: 15px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
.ex-adverse-reason { display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 14px; background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 10px; margin-bottom: 8px; }
.ex-adverse-num { width: 24px; height: 24px; border-radius: 50%;
  background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3);
  display: grid; place-items: center; font-family: var(--font-mono); font-size: 11px;
  color: var(--amber); flex-shrink: 0; }
.ex-adverse-text { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
.ex-adverse-text strong { color: var(--text-primary); }
```
