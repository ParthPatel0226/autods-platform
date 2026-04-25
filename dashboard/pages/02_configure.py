"""Page 02 -- Configure.

Lets the user confirm the detected domain, select analysis mode, choose the
target column, problem type, and describe their analysis goal.
Premium dark-luxury redesign with glass card design system.
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
# CSS -- design-system tokens from app.py
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ---- Tokens ---- */
:root {
  --bg-primary: #0a0a0f;
  --bg-card: #12121a;
  --bg-card-hover: #1a1a25;
  --bg-elevated: #16161f;
  --border-subtle: rgba(99,102,241,0.12);
  --border-active: rgba(99,102,241,0.4);
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-primary: #6366f1;
  --accent-secondary: #0ea5e9;
  --accent-success: #22c55e;
  --accent-warning: #f59e0b;
  --gradient-primary: linear-gradient(135deg, #6366f1, #0ea5e9);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-card: 0 4px 24px rgba(0,0,0,0.25);
  --shadow-glow: 0 0 20px rgba(99,102,241,0.15);
}

/* ---- Page base ---- */
[data-testid="stAppViewContainer"] { background: var(--bg-primary); }
[data-testid="stSidebar"] { background: #0d0d14; }

/* ---- Section header ---- */
.cfg-section-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent-primary);
  margin-bottom: 0.15rem;
}
.cfg-section-label::after {
  content: "";
  display: block;
  width: 40px;
  height: 2px;
  margin-top: 6px;
  margin-bottom: 1rem;
  background: var(--gradient-primary);
  border-radius: 1px;
}

/* ---- Glass card ---- */
.glass-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

/* ---- Domain badge ---- */
.domain-badge {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 4px solid var(--domain-color, var(--accent-primary));
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: 0.75rem;
}
.domain-icon-circle {
  width: 48px; height: 48px; min-width: 48px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; font-weight: 800; letter-spacing: 0.04em;
  color: #fff;
  background: var(--domain-color, var(--accent-primary));
  box-shadow: 0 0 14px -2px var(--domain-color, var(--accent-primary));
}
.domain-info { flex: 1; }
.domain-label {
  font-size: 1.1rem; font-weight: 700;
  color: var(--text-primary); margin-bottom: 0.15rem;
}
.domain-confidence-track {
  height: 6px; border-radius: 3px;
  background: rgba(255,255,255,0.06);
  overflow: hidden; margin-top: 0.5rem; max-width: 200px;
}
.domain-confidence-fill {
  height: 100%; border-radius: 3px;
  background: var(--gradient-primary);
  transition: width 0.6s cubic-bezier(0.16,1,0.3,1);
}
.domain-confidence-text {
  font-size: 0.7rem; color: var(--text-muted);
  margin-top: 0.25rem;
}

/* ---- Mode cards ---- */
.mode-row { display: flex; gap: 0.75rem; margin-bottom: 0.5rem; }
.mode-card {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1.15rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s, background 0.2s;
  min-height: 110px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.3rem;
}
.mode-card:hover {
  background: var(--bg-card-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}
.mode-card.active {
  border: 2px solid var(--mode-accent, var(--accent-primary));
  box-shadow: 0 0 20px -4px var(--mode-accent, var(--accent-primary));
  background: color-mix(in srgb, var(--mode-accent, var(--accent-primary)) 8%, var(--bg-card));
}
.mode-dot {
  width: 10px; height: 10px; border-radius: 50%;
  border: 2px solid var(--text-muted);
  margin-bottom: 0.2rem;
  transition: background 0.2s, border-color 0.2s;
}
.mode-card.active .mode-dot {
  background: var(--mode-accent, var(--accent-primary));
  border-color: var(--mode-accent, var(--accent-primary));
}
.mode-name {
  font-size: 0.92rem; font-weight: 700;
  color: var(--text-primary); letter-spacing: 0.03em;
}
.mode-card.active .mode-name { color: var(--mode-accent, var(--accent-primary)); }
.mode-desc {
  font-size: 0.72rem; color: var(--text-muted);
  line-height: 1.35; max-width: 150px;
}

/* ---- Pill badge ---- */
.pill-badge {
  display: inline-block;
  font-size: 0.65rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 0.2rem 0.6rem; border-radius: 4px;
  color: var(--accent-success);
  background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.25);
}

/* ---- Validation alert ---- */
.alert-warn {
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.2);
  border-left: 3px solid var(--accent-warning);
  border-radius: var(--radius-sm);
  padding: 0.7rem 1rem;
  color: var(--accent-warning);
  font-size: 0.84rem;
  margin-top: 0.5rem;
}

/* ---- Summary bar ---- */
.summary-bar {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 1rem 0;
  display: flex; align-items: stretch;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-card);
}
.summary-item {
  flex: 1; text-align: center;
  padding: 0.25rem 0.75rem;
}
.summary-item + .summary-item {
  border-left: 1px solid var(--border-subtle);
}
.summary-label {
  font-size: 0.6rem; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 0.2rem;
}
.summary-value {
  font-size: 0.92rem; font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ---- Start button ---- */
[data-testid="stButton"] > button[kind="primary"] {
  background: var(--gradient-primary);
  border: none;
  border-radius: var(--radius-md);
  color: #fff;
  font-weight: 700; font-size: 1rem;
  letter-spacing: 0.05em;
  padding: 0.8rem 2.5rem;
  min-height: 48px;
  box-shadow: 0 0 22px -4px rgba(99,102,241,0.5);
  transition: box-shadow 0.2s, transform 0.15s;
  animation: pulse-start 2.4s ease-in-out infinite;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  box-shadow: 0 0 32px -2px rgba(99,102,241,0.7);
  transform: translateY(-1px);
}
[data-testid="stButton"] > button[kind="primary"]:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
@keyframes pulse-start {
  0%, 100% { box-shadow: 0 0 18px -4px rgba(99,102,241,0.45); }
  50%      { box-shadow: 0 0 30px -2px rgba(99,102,241,0.65); }
}

/* ---- Streamlit overrides ---- */
[data-testid="stSelectbox"] label { color: var(--text-secondary) !important; font-size: 0.8rem !important; }
[data-testid="stTextArea"] label { color: var(--text-secondary) !important; font-size: 0.8rem !important; }
[data-testid="stRadio"] label { min-height: 44px; display: flex; align-items: center; }
[data-testid="stRadio"] [role="radiogroup"] label { min-height: 44px; }

/* ---- Page header ---- */
.page-header { margin-bottom: 1.75rem; }
.page-title {
  font-size: 1.65rem; font-weight: 800;
  color: var(--text-primary); letter-spacing: -0.01em; margin: 0;
}
.page-subtitle {
  font-size: 0.85rem; color: var(--text-muted); margin-top: 0.3rem;
}

/* ---- Reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
  [data-testid="stButton"] > button[kind="primary"] { animation: none; }
  .mode-card { transition: none; }
  .domain-confidence-fill { transition: none; }
}
</style>
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_META: dict[str, dict[str, str]] = {
    "healthcare":    {"abbr": "HC", "color": "#ef4444", "label": "Healthcare"},
    "finance":       {"abbr": "FN", "color": "#eab308", "label": "Finance"},
    "ecommerce":     {"abbr": "EC", "color": "#22c55e", "label": "E-Commerce"},
    "marketing":     {"abbr": "MK", "color": "#3b82f6", "label": "Marketing"},
    "hr":            {"abbr": "HR", "color": "#8b5cf6", "label": "Human Resources"},
    "manufacturing": {"abbr": "MF", "color": "#f97316", "label": "Manufacturing"},
    "generic":       {"abbr": "GA", "color": "#6b7280", "label": "General Analytics"},
}

_MODE_META: dict[str, dict[str, str]] = {
    "auto":   {"label": "Auto",   "desc": "Fully autonomous -- system makes all decisions.", "color": "#6366f1"},
    "guided": {"label": "Guided", "desc": "Interactive -- system recommends, you approve.",  "color": "#0ea5e9"},
    "expert": {"label": "Expert", "desc": "Full control -- you specify every parameter.",    "color": "#a855f7"},
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
    conf_pct = int(confidence * 100) if confidence > 0 else 0

    st.markdown(
        f'<div class="cfg-section-label">Domain Detection</div>'
        f'<div class="domain-badge" style="--domain-color:{meta["color"]}">'
        f'  <div class="domain-icon-circle" style="background:{meta["color"]};'
        f'       box-shadow:0 0 14px -2px {meta["color"]}">{meta["abbr"]}</div>'
        f'  <div class="domain-info">'
        f'    <div class="domain-label">{meta["label"]}</div>'
        + (
            f'    <div class="domain-confidence-track">'
            f'      <div class="domain-confidence-fill" style="width:{conf_pct}%"></div>'
            f'    </div>'
            f'    <div class="domain-confidence-text">Confidence: {confidence:.0%}</div>'
            if confidence > 0 else ""
        )
        + f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    from core.constants import VALID_DOMAINS
    domain_label_list = [
        _DOMAIN_META.get(d, _DOMAIN_META["generic"])["label"] for d in VALID_DOMAINS
    ]
    label_to_key = dict(zip(domain_label_list, VALID_DOMAINS))
    current_label = meta["label"]

    override = st.selectbox(
        "Override domain (optional)",
        options=domain_label_list,
        index=(
            domain_label_list.index(current_label)
            if current_label in domain_label_list
            else len(domain_label_list) - 1
        ),
        key="domain_override_select",
        help="Change the detected domain if the auto-detection is incorrect.",
    )

    final_domain = label_to_key.get(override, detected)
    st.session_state["detected_domain"] = final_domain
    return final_domain


def _render_mode_section() -> str:
    """Render the mode-card selector and return the chosen mode string."""
    current_mode: str = st.session_state.get("user_mode", MODE_GUIDED)

    st.markdown('<div class="cfg-section-label">Analysis Mode</div>', unsafe_allow_html=True)

    ordered = ["auto", "guided", "expert"]
    cards_html = '<div class="mode-row">'
    for mode_key in ordered:
        meta = _MODE_META[mode_key]
        active = "active" if mode_key == current_mode else ""
        cards_html += (
            f'<div class="mode-card {active}" style="--mode-accent:{meta["color"]}">'
            f'  <div class="mode-dot"></div>'
            f'  <div class="mode-name">{meta["label"]}</div>'
            f'  <div class="mode-desc">{meta["desc"]}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    radio_labels = [_MODE_META[m]["label"] for m in ordered]
    selected_label = st.radio(
        "Mode",
        options=radio_labels,
        index=ordered.index(current_mode),
        horizontal=True,
        label_visibility="collapsed",
        key="mode_selector_radio",
    )

    chosen_mode = {_MODE_META[m]["label"]: m for m in ordered}.get(
        selected_label, MODE_GUIDED
    )
    st.session_state["user_mode"] = chosen_mode
    return chosen_mode


def _render_target_section(df: pd.DataFrame) -> tuple[str | None, str]:
    """Render target + problem type selectors. Return (target_column, problem_type)."""
    st.markdown(
        '<div class="cfg-section-label">Target &amp; Problem Type</div>'
        '<div class="glass-card">',
        unsafe_allow_html=True,
    )

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
    target_column: str | None = (
        None if target_selection.startswith("(none") else target_selection
    )
    st.session_state["target_column"] = target_column

    inferred = _infer_problem_type(df, target_column)
    label_to_key = {v: k for k, v in _PROBLEM_LABELS.items()}
    display_options = [_PROBLEM_LABELS[pt] for pt in VALID_PROBLEM_TYPES]
    default_idx = display_options.index(
        _PROBLEM_LABELS.get(inferred, "Classification")
    )

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
            '<span class="pill-badge">Auto-detected</span>',
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

    if target_column is None and problem_type in (
        PROBLEM_CLASSIFICATION,
        PROBLEM_REGRESSION,
    ):
        st.markdown(
            "<div class='alert-warn'>"
            "Warning: You selected a supervised problem type but no target column. "
            "Please select a target or switch to Clustering / Time Series."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return target_column, problem_type


def _render_goal_section() -> str:
    """Render the analysis goal text area and return the current value."""
    st.markdown(
        '<div class="cfg-section-label">Analysis Goal</div>'
        '<div class="glass-card">',
        unsafe_allow_html=True,
    )
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


def _render_summary_bar(
    final_domain: str,
    selected_mode: str,
    problem_type: str,
    target_column: str | None,
) -> None:
    """Render the 4-metric summary bar above the Start button."""
    domain_meta = _DOMAIN_META.get(final_domain, _DOMAIN_META["generic"])
    mode_meta = _MODE_META.get(selected_mode, _MODE_META["guided"])
    problem_disp = _PROBLEM_LABELS.get(problem_type, problem_type.title())
    target_disp = target_column if target_column else "None"

    items = [
        ("Domain", domain_meta["label"]),
        ("Mode", mode_meta["label"]),
        ("Problem", problem_disp),
        ("Target", target_disp),
    ]

    cells = "".join(
        f'<div class="summary-item">'
        f'  <div class="summary-label">{label}</div>'
        f'  <div class="summary-value">{value}</div>'
        f'</div>'
        for label, value in items
    )

    st.markdown(f'<div class="summary-bar">{cells}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    st.set_page_config(
        page_title="Configure -- AutoDS", layout="wide", page_icon="+"
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()

    df: pd.DataFrame = st.session_state["uploaded_data"]

    # Page header
    st.markdown(
        '<div class="page-header">'
        '  <div class="page-title">Configure Analysis</div>'
        '  <div class="page-subtitle">'
        "    Review auto-detected settings and customise before starting the pipeline."
        "  </div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Sections
    final_domain = _render_domain_section(df)
    selected_mode = _render_mode_section()
    target_column, problem_type = _render_target_section(df)
    _render_goal_section()

    # Summary bar
    _render_summary_bar(final_domain, selected_mode, problem_type, target_column)

    # Start button
    if st.button("Start Analysis", type="primary", use_container_width=True):
        st.session_state["pipeline_started"] = True
        st.session_state["current_step"] = "data_profiling"
        # Bug fix: preserve "upload" in completed_steps, clear everything else
        existing = [
            s
            for s in st.session_state.get("completed_steps", [])
            if s == "upload"
        ]
        st.session_state["completed_steps"] = existing
        st.session_state["workflow_status"] = "running"
        st.success("Pipeline started. Navigating to EDA...")
        st.switch_page("pages/03_eda_interactive.py")


_page()
