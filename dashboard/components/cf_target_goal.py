"""Target column and goal text selectors for the Configure tab."""
from __future__ import annotations

import streamlit as st

from dashboard.components.cf_domain_adapter import DOMAIN_REGISTRY

# PHI column patterns — filter out for sensitive domains
_PHI_PATTERNS = ["ssn", "social_security", "dob", "date_of_birth", "mrn", "patient_id"]
_SENSITIVE_DOMAINS = {"healthcare", "hr", "finance"}

GOAL_TEMPLATES: dict[str, list[str]] = {
    "classification": [
        "Predict which records will be positive",
        "Identify high-risk cases",
        "Classify into categories",
        "Detect fraud or anomalous events",
    ],
    "regression": [
        "Estimate a continuous numeric value",
        "Forecast future values",
        "Score records on a scale",
        "Predict revenue or cost",
    ],
    "clustering": [
        "Discover natural customer segments",
        "Group similar records together",
        "Find patterns in unlabelled data",
    ],
    "time_series": [
        "Forecast values over time",
        "Detect seasonal patterns",
        "Predict next period value",
    ],
    "anomaly_detection": [
        "Flag unusual records for review",
        "Detect outliers and errors",
        "Identify fraud signals",
    ],
    "auto": [
        "Understand what drives the outcome",
        "Find actionable insights",
        "Build a predictive model",
    ],
}


def _filter_phi(columns: list[str], domain_key: str) -> list[str]:
    if domain_key not in _SENSITIVE_DOMAINS:
        return columns
    return [c for c in columns if not any(p in c.lower() for p in _PHI_PATTERNS)]


def render(columns: list[str], domain_key: str, problem_type: str) -> tuple[str, str]:
    """Render target column selectbox + goal dropdown.

    Returns (target_column, goal_text).
    """
    safe_cols = _filter_phi(columns, domain_key)

    # ---- Target column ----
    prev_target = st.session_state.get("cf_target", "")
    default_idx = safe_cols.index(prev_target) if prev_target in safe_cols else 0

    cfg = DOMAIN_REGISTRY.get(domain_key, {})
    target_hint = cfg.get("target_column_hint", "")
    hint_html = f'<div class="cf-target-hint">Suggested: {target_hint}</div>' if target_hint else ""
    st.markdown(hint_html, unsafe_allow_html=True)

    target = st.selectbox(
        "Target column",
        options=["(none — unsupervised)"] + safe_cols,
        index=default_idx + 1 if safe_cols else 0,
        key="cf_target_selectbox",
    )
    if target == "(none — unsupervised)":
        target = ""
    st.session_state["cf_target"] = target

    # ---- Goal text ----
    templates = GOAL_TEMPLATES.get(problem_type, GOAL_TEMPLATES["auto"])
    prev_goal = st.session_state.get("cf_goal", "")

    goal_choice = st.selectbox(
        "Analysis goal",
        options=templates + ["Custom…"],
        index=0,
        key="cf_goal_selectbox",
    )
    if goal_choice == "Custom…":
        goal = st.text_input(
            "Describe your goal",
            value=prev_goal if prev_goal not in templates else "",
            key="cf_goal_custom",
        )
    else:
        goal = goal_choice

    st.session_state["cf_goal"] = goal
    return target, goal
