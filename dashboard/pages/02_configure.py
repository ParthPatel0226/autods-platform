"""Page 02 -- Configure.

Lets the user confirm the detected domain, select analysis mode, choose the
target column, problem type, and describe their analysis goal.
Premium dark-luxury redesign for the AutoDS platform.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import (
    MODE_GUIDED,
    PROBLEM_CLASSIFICATION,
    PROBLEM_CLUSTERING,
    PROBLEM_REGRESSION,
    PROBLEM_TIME_SERIES,
    VALID_PROBLEM_TYPES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ---- Page base ---- */
[data-testid="stAppViewContainer"] {
    background: #0f0f14;
}
[data-testid="stSidebar"] {
    background: #13131a;
}

/* ---- Section card ---- */
.cfg-card {
    background: #16161f;
    border: 1px solid #2a2a3a;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
}
.cfg-card-title {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6366f1;
    margin-bottom: 1rem;
}

/* ---- Domain badge ---- */
.domain-badge-wrap {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 1.25rem;
    border-radius: 2rem;
    border: 2px solid var(--badge-color, #6366f1);
    box-shadow: 0 0 14px -2px var(--badge-color, #6366f1);
    background: color-mix(in srgb, var(--badge-color, #6366f1) 12%, transparent);
    margin-bottom: 0.75rem;
}
.domain-badge-label {
    font-size: 1rem;
    font-weight: 700;
    color: var(--badge-color, #6366f1);
    letter-spacing: 0.02em;
}

/* ---- Mode cards ---- */
.mode-card {
    background: #1c1c28;
    border: 1px solid #2e2e42;
    border-radius: 12px;
    padding: 1.1rem 1rem;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
    height: 100%;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
}
.mode-card.selected {
    border: 2px solid var(--mode-color, #6366f1);
    box-shadow: 0 0 18px -4px var(--mode-color, #6366f1);
    background: color-mix(in srgb, var(--mode-color, #6366f1) 10%, #1c1c28);
}
.mode-card-icon {
    font-size: 1.5rem;
    line-height: 1;
}
.mode-card-name {
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--mode-color, #6366f1);
    letter-spacing: 0.04em;
}
.mode-card-desc {
    font-size: 0.72rem;
    color: #8888aa;
    line-height: 1.35;
    max-width: 130px;
}

/* ---- Validation alert ---- */
.alert-warn {
    background: #2a1f0a;
    border: 1px solid #f59e0b55;
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    color: #f59e0b;
    font-size: 0.84rem;
    margin-top: 0.5rem;
}

/* ---- Summary bar ---- */
.summary-bar {
    background: #16161f;
    border: 1px solid #2a2a3a;
    border-radius: 14px;
    padding: 1rem 1.5rem;
    display: flex;
    align-items: stretch;
    margin-bottom: 1.25rem;
}
.summary-item {
    flex: 1;
    text-align: center;
    padding: 0.25rem 0.5rem;
}
.summary-item + .summary-item {
    border-left: 1px solid #2a2a3a;
}
.summary-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #55556a;
    margin-bottom: 0.2rem;
}
.summary-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: #e2e2f0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ---- Start button ---- */
.start-btn-wrap {
    display: flex;
    justify-content: center;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.05em;
    padding: 0.75rem 2.5rem;
    box-shadow: 0 0 22px -4px #6366f188;
    transition: box-shadow 0.2s, transform 0.15s;
    animation: pulse-btn 2.4s ease-in-out infinite;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 0 32px -2px #6366f1cc;
    transform: translateY(-1px);
}
@keyframes pulse-btn {
    0%, 100% { box-shadow: 0 0 18px -4px #6366f188; }
    50%       { box-shadow: 0 0 30px -2px #8b5cf6bb; }
}

/* ---- Streamlit selectbox tweaks ---- */
[data-testid="stSelectbox"] label {
    color: #9999bb !important;
    font-size: 0.8rem !important;
}
[data-testid="stTextArea"] label {
    color: #9999bb !important;
    font-size: 0.8rem !important;
}

/* ---- Progress bar ---- */
[data-testid="stProgressBar"] > div {
    background: #6366f1 !important;
}

/* ---- Page header ---- */
.page-header {
    margin-bottom: 1.75rem;
}
.page-title {
    font-size: 1.65rem;
    font-weight: 800;
    color: #e8e8f8;
    letter-spacing: -0.01em;
    margin: 0;
}
.page-subtitle {
    font-size: 0.85rem;
    color: #66667a;
    margin-top: 0.3rem;
}
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_META: dict[str, dict[str, str]] = {
    "healthcare":    {"icon": "🏥", "color": "#ef4444", "label": "Healthcare"},
    "finance":       {"icon": "🏦", "color": "#eab308", "label": "Finance"},
    "ecommerce":     {"icon": "🛒", "color": "#22c55e", "label": "E-Commerce"},
    "marketing":     {"icon": "📊", "color": "#3b82f6", "label": "Marketing"},
    "hr":            {"icon": "👥", "color": "#8b5cf6", "label": "Human Resources"},
    "manufacturing": {"icon": "🏭", "color": "#f97316", "label": "Manufacturing"},
    "generic":       {"icon": "📈", "color": "#6b7280", "label": "General Analytics"},
}

_MODE_META: dict[str, dict[str, str]] = {
    "auto":    {"icon": "⚡", "label": "Auto",    "desc": "Fully autonomous — system makes all decisions.", "color": "#6366f1"},
    "guided":  {"icon": "🎚️", "label": "Guided",  "desc": "Interactive — system recommends, you approve.",   "color": "#0ea5e9"},
    "expert":  {"icon": "🔧", "label": "Expert",  "desc": "Full control — you specify every parameter.",     "color": "#f59e0b"},
}

_PROBLEM_LABELS: dict[str, str] = {
    PROBLEM_CLASSIFICATION: "Classification",
    PROBLEM_REGRESSION:     "Regression",
    PROBLEM_CLUSTERING:     "Clustering",
    PROBLEM_TIME_SERIES:    "Time Series",
}


def _infer_problem_type(df: pd.DataFrame, target: str | None) -> str:
    """Heuristic to guess the problem type from the target column."""
    if target is None or target == "":
        return PROBLEM_CLUSTERING

    series = df[target]
    nunique = series.nunique()

    if pd.api.types.is_float_dtype(series) and nunique > 20:
        return PROBLEM_REGRESSION
    if nunique <= 20:
        return PROBLEM_CLASSIFICATION
    return PROBLEM_REGRESSION


def _detect_time_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that look like datetime."""
    candidates: list[str] = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            candidates.append(col)
            continue
        if df[col].dtype == "object":
            sample = df[col].dropna().head(20)
            try:
                pd.to_datetime(sample, format="mixed")
                candidates.append(col)
            except (ValueError, TypeError):
                pass
    return candidates


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _render_domain_section(df: pd.DataFrame) -> str:
    """Render domain detection card and return the final domain string."""
    from dashboard.components.domain_badge import render_domain_badge
    from domains.domain_registry import detect_domain

    col_names = list(df.columns)
    cached_domain = st.session_state.get("detected_domain")

    if cached_domain is None:
        detected, confidence, domain_cfg = detect_domain(col_names)
        st.session_state["detected_domain"] = detected
        st.session_state["domain_detection_confidence"] = confidence
        st.session_state["domain_config"] = domain_cfg
    else:
        detected = cached_domain
        confidence = st.session_state.get("domain_detection_confidence", 0.0)

    meta = _DOMAIN_META.get(detected, _DOMAIN_META["generic"])

    st.markdown(
        f"""
        <div class="cfg-card">
            <div class="cfg-card-title">Domain Detection</div>
            <div class="domain-badge-wrap" style="--badge-color:{meta['color']}">
                <span style="font-size:1.3rem">{meta['icon']}</span>
                <span class="domain-badge-label">{meta['label']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if confidence > 0:
        st.progress(confidence, text=f"Detection confidence: {confidence:.0%}")

    from core.constants import VALID_DOMAINS
    domain_label_list = [_DOMAIN_META.get(d, _DOMAIN_META["generic"])["label"] for d in VALID_DOMAINS]
    label_to_key = dict(zip(domain_label_list, VALID_DOMAINS))
    current_label = meta["label"]

    override = st.selectbox(
        "Override domain (optional)",
        options=domain_label_list,
        index=domain_label_list.index(current_label) if current_label in domain_label_list else len(domain_label_list) - 1,
        key="domain_override_select",
        help="Change the detected domain if the auto-detection is incorrect.",
    )

    final_domain = label_to_key.get(override, detected)
    st.session_state["detected_domain"] = final_domain
    return final_domain


def _render_mode_section() -> str:
    """Render the premium mode-card selector and return the chosen mode string."""
    current_mode: str = st.session_state.get("user_mode", MODE_GUIDED)

    st.markdown('<div class="cfg-card"><div class="cfg-card-title">Analysis Mode</div>', unsafe_allow_html=True)

    ordered = ["auto", "guided", "expert"]
    cols = st.columns(3, gap="small")

    for col, mode_key in zip(cols, ordered):
        meta = _MODE_META[mode_key]
        is_selected = mode_key == current_mode
        selected_class = "selected" if is_selected else ""
        with col:
            st.markdown(
                f"""
                <div class="mode-card {selected_class}" style="--mode-color:{meta['color']}">
                    <div class="mode-card-icon">{meta['icon']}</div>
                    <div class="mode-card-name">{meta['label']}</div>
                    <div class="mode-card-desc">{meta['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    radio_labels = [_MODE_META[m]["label"] for m in ordered]
    selected_label = st.radio(
        "Mode",
        options=radio_labels,
        index=ordered.index(current_mode),
        horizontal=True,
        label_visibility="collapsed",
        key="mode_selector_radio",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    chosen_mode = {_MODE_META[m]["label"]: m for m in ordered}.get(selected_label, MODE_GUIDED)
    st.session_state["user_mode"] = chosen_mode
    return chosen_mode


def _render_target_section(df: pd.DataFrame) -> tuple[str | None, str]:
    """Render target + problem type selectors. Return (target_column, problem_type)."""
    st.markdown('<div class="cfg-card"><div class="cfg-card-title">Target & Problem Type</div>', unsafe_allow_html=True)

    col_options = ["(none -- unsupervised)"] + list(df.columns)
    target_idx = 0
    if st.session_state.get("target_column") in df.columns:
        target_idx = col_options.index(st.session_state["target_column"])

    target_selection = st.selectbox(
        "Target column",
        options=col_options,
        index=target_idx,
        help="Select the column you want to predict. Leave as 'none' for clustering or EDA-only.",
        key="target_col_select",
    )
    target_column: str | None = None if target_selection.startswith("(none") else target_selection
    st.session_state["target_column"] = target_column

    inferred = _infer_problem_type(df, target_column)
    label_to_key = {v: k for k, v in _PROBLEM_LABELS.items()}
    display_options = [_PROBLEM_LABELS[pt] for pt in VALID_PROBLEM_TYPES]
    default_idx = display_options.index(_PROBLEM_LABELS.get(inferred, "Classification"))

    left, right = st.columns([3, 1])
    with left:
        problem_label = st.selectbox(
            "Problem type",
            options=display_options,
            index=default_idx,
            key="problem_type_select",
            help="Auto-detected from target column. Override if needed.",
        )
    with right:
        st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
        st.markdown(
            "<span style='font-size:0.68rem;font-weight:700;letter-spacing:0.1em;"
            "text-transform:uppercase;color:#22c55e;padding:0.25rem 0.6rem;"
            "background:#22c55e1a;border-radius:4px;border:1px solid #22c55e44'>Auto-detected</span>",
            unsafe_allow_html=True,
        )

    problem_type = label_to_key.get(problem_label, PROBLEM_CLASSIFICATION)
    st.session_state["problem_type"] = problem_type

    if problem_type == PROBLEM_TIME_SERIES:
        time_cols = _detect_time_columns(df)
        all_cols = time_cols + [c for c in df.columns if c not in time_cols]
        time_col = st.selectbox(
            "Time column",
            options=all_cols,
            key="time_col_select",
            help="Select the datetime column for time-series analysis.",
        )
        st.session_state["time_column"] = time_col
    else:
        st.session_state["time_column"] = None

    if target_column is None and problem_type in (PROBLEM_CLASSIFICATION, PROBLEM_REGRESSION):
        st.markdown(
            "<div class='alert-warn'>"
            "⚠ You selected a supervised problem type but no target column. "
            "Please select a target or switch to Clustering / Time Series."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return target_column, problem_type


def _render_goal_section() -> str:
    """Render the analysis goal text area and return the current value."""
    st.markdown('<div class="cfg-card"><div class="cfg-card-title">Analysis Goal</div>', unsafe_allow_html=True)
    user_goal = st.text_area(
        "Describe your goal in plain language (optional)",
        value=st.session_state.get("user_goal", ""),
        height=90,
        placeholder="e.g. Predict which patients will be readmitted within 30 days...",
        key="user_goal_input",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state["user_goal"] = user_goal
    return user_goal


def _render_summary_bar(final_domain: str, selected_mode: str, problem_type: str, target_column: str | None) -> None:
    """Render the 4-metric summary bar above the Start button."""
    domain_meta = _DOMAIN_META.get(final_domain, _DOMAIN_META["generic"])
    mode_meta   = _MODE_META.get(selected_mode, _MODE_META["guided"])
    problem_disp = _PROBLEM_LABELS.get(problem_type, problem_type.title())
    target_disp  = target_column if target_column else "None"

    items = [
        ("Domain",  f"{domain_meta['icon']} {domain_meta['label']}"),
        ("Mode",    f"{mode_meta['icon']} {mode_meta['label']}"),
        ("Problem", problem_disp),
        ("Target",  target_disp),
    ]

    cells = "".join(
        f"""
        <div class="summary-item">
            <div class="summary-label">{label}</div>
            <div class="summary-value">{value}</div>
        </div>
        """
        for label, value in items
    )

    st.markdown(f'<div class="summary-bar">{cells}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    st.set_page_config(page_title="Configure — AutoDS", layout="wide", page_icon="⚙️")
    st.markdown(_CSS, unsafe_allow_html=True)

    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()

    df: pd.DataFrame = st.session_state["uploaded_data"]

    # Page header
    st.markdown(
        """
        <div class="page-header">
            <div class="page-title">⚙️ Configure Analysis</div>
            <div class="page-subtitle">
                Review auto-detected settings and customise before starting the pipeline.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sections
    final_domain   = _render_domain_section(df)
    selected_mode  = _render_mode_section()
    target_column, problem_type = _render_target_section(df)
    _render_goal_section()

    # Summary bar
    _render_summary_bar(final_domain, selected_mode, problem_type, target_column)

    # Start button
    if st.button("Start Analysis →", type="primary", use_container_width=True):
        st.session_state["pipeline_started"] = True
        st.session_state["current_step"]     = "data_profiling"
        # Bug fix: preserve "upload" in completed_steps, clear everything else
        existing = [s for s in st.session_state.get("completed_steps", []) if s == "upload"]
        st.session_state["completed_steps"]  = existing
        st.session_state["workflow_status"]  = "running"
        st.success("Pipeline started. Navigating to EDA...")
        st.switch_page("pages/03_eda_interactive.py")


_page()
