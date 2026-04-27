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

from dashboard.components.shared_css import inject_shared_css
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
  box-shadow: var(--shadow-glow);
}
.domain-info { flex: 1; }
.domain-label {
  font-size: 1.1rem; font-weight: 700;
  color: var(--text-primary); margin-bottom: 0.15rem;
}
.domain-confidence-track {
  height: 6px; border-radius: 3px;
  background: var(--bg-elevated);
  overflow: hidden; margin-top: 0.5rem; max-width: 200px;
}
.domain-confidence-fill {
  height: 100%; border-radius: 3px;
  background: var(--gradient-primary);
  transition: width var(--duration-slow) var(--ease-out);
}
.domain-confidence-text {
  font-size: 0.7rem; color: var(--text-muted);
  margin-top: 0.25rem;
}

/* ---- Mode cards ---- */
.mode-row { display: flex; gap: 0.75rem; margin-bottom: 0.5rem; }
.mode-card-wrap { flex: 1; position: relative; }
.mode-rec-tag {
  position: absolute; top: -10px; left: 50%; transform: translateX(-50%);
  font-size: 0.58rem; font-weight: 800;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: #fff; background: var(--gradient-primary);
  padding: 2px 10px; border-radius: 4px;
  white-space: nowrap; z-index: 2;
  box-shadow: var(--shadow-card);
}
.mode-card {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1.15rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast), transform var(--duration-fast), background var(--duration-fast);
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
  box-shadow: var(--shadow-glow);
  background: color-mix(in srgb, var(--mode-accent, var(--accent-primary)) 8%, var(--bg-card));
}
.mode-dot {
  width: 10px; height: 10px; border-radius: 50%;
  border: 2px solid var(--text-muted);
  margin-bottom: 0.2rem;
  transition: background var(--duration-fast), border-color var(--duration-fast);
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
/* Hide mode button container label/chrome */
.mode-btn-row [data-testid="stButton"] button {
  background: transparent !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-secondary) !important;
  font-size: 0.75rem !important;
  padding: 0.35rem 0.5rem !important;
  min-height: 32px !important;
  border-radius: 6px !important;
  opacity: 0.6;
  transition: opacity var(--duration-fast);
}
.mode-btn-row [data-testid="stButton"] button:hover {
  opacity: 1;
  border-color: var(--accent-primary) !important;
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
  box-shadow: var(--shadow-glow);
  transition: box-shadow var(--duration-fast), transform var(--duration-fast);
  animation: pulse-start 2.4s ease-in-out infinite;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}
[data-testid="stButton"] > button[kind="primary"]:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
@keyframes pulse-start {
  0%, 100% { box-shadow: var(--shadow-glow); }
  50%      { box-shadow: var(--shadow-lg); }
}

/* ---- Streamlit overrides ---- */
[data-testid="stSelectbox"] label { color: var(--text-secondary) !important; font-size: 0.8rem !important; }

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
    "auto":   {"label": "Auto",   "desc": "Fully autonomous -- system makes all decisions.", "color": "#2563eb"},
    "guided": {"label": "Guided", "desc": "Interactive -- system recommends, you approve.",  "color": "#0891b2"},
    "expert": {"label": "Expert", "desc": "Full control -- you specify every parameter.",    "color": "#7c3aed"},
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
    recommended = "guided"

    # Render visual flashcards
    cards_html = '<div class="mode-row">'
    for mode_key in ordered:
        meta = _MODE_META[mode_key]
        active = "active" if mode_key == current_mode else ""
        rec_tag = (
            '<div class="mode-rec-tag">Recommended</div>'
            if mode_key == recommended else ""
        )
        cards_html += (
            f'<div class="mode-card-wrap">'
            f'  {rec_tag}'
            f'  <div class="mode-card {active}" style="--mode-accent:{meta["color"]}">'
            f'    <div class="mode-dot"></div>'
            f'    <div class="mode-name">{meta["label"]}</div>'
            f'    <div class="mode-desc">{meta["desc"]}</div>'
            f'  </div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # Buttons for interaction (one per card)
    st.markdown('<div class="mode-btn-row">', unsafe_allow_html=True)
    cols = st.columns(len(ordered))
    chosen_mode = current_mode
    for col, mode_key in zip(cols, ordered):
        meta = _MODE_META[mode_key]
        with col:
            if st.button(
                f"Select {meta['label']}",
                key=f"mode_btn_{mode_key}",
                use_container_width=True,
            ):
                chosen_mode = mode_key
    st.markdown('</div>', unsafe_allow_html=True)

    st.session_state["user_mode"] = chosen_mode
    return chosen_mode


def _render_target_section(df: pd.DataFrame) -> tuple[str | None, str]:
    """Render target + problem type selectors. Return (target_column, problem_type)."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

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

    problem_label = st.selectbox(
        "Problem type (auto-detected)",
        options=display_options,
        index=default_idx,
        key="problem_type_select",
        help="Auto-detected from target column. Override if needed.",
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


_GOAL_OPTIONS: dict[str, list[str]] = {
    PROBLEM_CLASSIFICATION: [
        "Predict the target class with highest accuracy",
        "Identify key drivers of the target variable",
        "Build an interpretable model for decision support",
        "Minimize false negatives (catch all positives)",
        "Minimize false positives (high precision)",
        "Comprehensive EDA + modeling pipeline",
    ],
    PROBLEM_REGRESSION: [
        "Predict the target value as accurately as possible",
        "Identify features with strongest impact on the target",
        "Build an interpretable regression model",
        "Forecast future values with confidence intervals",
        "Comprehensive EDA + modeling pipeline",
    ],
    PROBLEM_CLUSTERING: [
        "Discover natural segments in the data",
        "Identify anomalies and outliers",
        "Understand data structure and distributions",
        "Comprehensive exploratory analysis only",
    ],
    PROBLEM_TIME_SERIES: [
        "Forecast future values",
        "Detect trends and seasonality patterns",
        "Identify anomalies in time series",
        "Comprehensive time series analysis",
    ],
}


def _render_goal_section(problem_type: str) -> str:
    """Render the analysis goal dropdown and return the current value."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    goals = _GOAL_OPTIONS.get(problem_type, _GOAL_OPTIONS[PROBLEM_CLASSIFICATION])
    prev_goal = st.session_state.get("user_goal", "")
    default_idx = goals.index(prev_goal) if prev_goal in goals else 0

    user_goal = st.selectbox(
        "What do you want to achieve?",
        options=goals,
        index=default_idx,
        key="user_goal_select",
        help="Select a common objective, or type your own below.",
    )

    custom_goal = st.text_input(
        "Or describe your goal manually",
        value="",
        key="user_goal_custom",
        placeholder="e.g. Find top 5 churn predictors with AUC > 0.85",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    final_goal = custom_goal.strip() if custom_goal.strip() else user_goal
    st.session_state["user_goal"] = final_goal
    return final_goal


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
    inject_shared_css()
    st.markdown(_CSS, unsafe_allow_html=True)

    if "uploaded_data" not in st.session_state:
        st.info(
            "Upload a dataset to configure analysis settings. "
            "Supported: CSV, Excel, Parquet, JSON, and 30+ other sources."
        )
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
    _render_goal_section(problem_type)

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



def _is_streamlit_running() -> bool:
    """Return True only when executing inside a Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _is_streamlit_running():
    _page()
