"""Sticky right-column summary panel + Start Analysis button for the Configure tab."""
from __future__ import annotations

import streamlit as st

from dashboard.components.cf_domain_adapter import DOMAIN_REGISTRY
from dashboard.components.cf_compliance_notice import COMPLIANCE_TAGS


def _validate_ready() -> list[str]:
    """Return list of blocking issues, empty = ready to start."""
    issues: list[str] = []
    domain = st.session_state.get("cf_selected_domain", "")
    if not domain:
        issues.append("Select a domain")
    mode = st.session_state.get("cf_mode", "")
    if not mode:
        issues.append("Select an analysis mode")
    problem_type = st.session_state.get("cf_problem_type", "")
    if not problem_type:
        issues.append("Select a problem type")
    # target required only for supervised problem types
    supervised = {"classification", "regression", "time_series", "anomaly_detection"}
    if problem_type in supervised and not st.session_state.get("cf_target", ""):
        issues.append("Select a target column")
    return issues


def render(on_start, estimate=None) -> None:
    """Render sticky summary panel.

    Args:
        on_start: Callable receiving a payload dict when Start Analysis clicked.
        estimate: Optional PipelineEstimate instance.
    """
    domain_key = st.session_state.get("cf_selected_domain", "")
    mode = st.session_state.get("cf_mode", "guided")
    problem_type = st.session_state.get("cf_problem_type", "")
    target = st.session_state.get("cf_target", "")
    goal = st.session_state.get("cf_goal", "")
    excluded: set = st.session_state.get("cf_excluded", set())

    cfg = DOMAIN_REGISTRY.get(domain_key, {})
    domain_label = cfg.get("display_name", domain_key.title() if domain_key else "—")
    domain_icon = cfg.get("icon", "📊")

    compliance = COMPLIANCE_TAGS.get(domain_key, [])

    def _row(label: str, value: str, warn: bool = False) -> str:
        cls = "cf-summary-warn" if warn else ""
        return (
            f'<div class="cf-summary-row {cls}">'
            f'  <span class="cf-summary-label">{label}</span>'
            f'  <span class="cf-summary-value">{value or "—"}</span>'
            f'</div>'
        )

    rows = (
        _row("Domain", f"{domain_icon} {domain_label}", warn=not domain_key)
        + _row("Mode", mode.title(), warn=not mode)
        + _row("Problem", problem_type.replace("_", " ").title(), warn=not problem_type)
        + _row("Target", target or "(unsupervised)", warn=False)
        + _row("Goal", (goal[:60] + "…") if len(goal) > 60 else goal)
        + _row("Excluded", f"{len(excluded)} column(s)" if excluded else "None")
    )

    compliance_html = ""
    if compliance:
        compliance_html = '<div class="cf-summary-compliance">⚠ Compliance checks active</div>'

    est_html = ""
    if estimate is not None:
        est_html = (
            f'<div class="cf-estimate-block">'
            f'  <div class="cf-estimate-title">Pipeline estimate</div>'
            f'  <div class="cf-estimate-row">'
            f'    <span>⏱ Runtime</span><span>{estimate.runtime_str}</span>'
            f'  </div>'
            f'  <div class="cf-estimate-row">'
            f'    <span>💰 LLM cost</span><span>{estimate.cost_str}</span>'
            f'  </div>'
            f'  <div class="cf-estimate-row">'
            f'    <span>📊 Charts</span><span>~{estimate.n_charts}</span>'
            f'  </div>'
            f'  <div class="cf-estimate-row">'
            f'    <span>🤖 Models</span><span>{estimate.n_models}</span>'
            f'  </div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="cf-summary-panel">'
        f'  <div class="cf-summary-title">Configuration Summary</div>'
        f'  {rows}'
        f'  {compliance_html}'
        f'  {est_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    issues = _validate_ready()
    if issues:
        for issue in issues:
            st.markdown(
                f'<div class="cf-validation-issue">✗ {issue}</div>',
                unsafe_allow_html=True,
            )

    btn_disabled = bool(issues)
    if st.button(
        "🚀 Start Analysis",
        key="cf_start_analysis",
        disabled=btn_disabled,
        use_container_width=True,
        type="primary",
    ):
        payload = {
            "domain": domain_key,
            "mode": mode,
            "problem_type": problem_type,
            "target_column": target,
            "goal": goal,
            "excluded_columns": list(excluded),
        }
        on_start(payload)
