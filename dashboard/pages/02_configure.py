"""Page 02 -- Configure.

Lets the user confirm the detected domain, select analysis mode, choose the
target column, problem type, and describe their analysis goal.
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
# Helpers
# ---------------------------------------------------------------------------

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
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()

    df: pd.DataFrame = st.session_state["uploaded_data"]

    st.header("Configure Analysis")
    st.markdown(
        "Review auto-detected settings and customise before starting the pipeline."
    )

    # ---- Domain detection ----
    st.subheader("Domain Detection")

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

    final_domain = render_domain_badge(detected, confidence, allow_override=True)
    st.session_state["detected_domain"] = final_domain

    st.divider()

    # ---- Mode selector ----
    st.subheader("Analysis Mode")
    from dashboard.components.mode_selector import render_mode_selector

    selected_mode = render_mode_selector()

    st.divider()

    # ---- Target column ----
    st.subheader("Target & Problem Type")

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

    # ---- Problem type ----
    inferred = _infer_problem_type(df, target_column)
    problem_labels = {
        PROBLEM_CLASSIFICATION: "Classification",
        PROBLEM_REGRESSION: "Regression",
        PROBLEM_CLUSTERING: "Clustering",
        PROBLEM_TIME_SERIES: "Time Series",
    }
    label_to_key = {v: k for k, v in problem_labels.items()}
    display_options = [problem_labels[pt] for pt in VALID_PROBLEM_TYPES]

    default_idx = display_options.index(problem_labels.get(inferred, "Classification"))

    problem_label = st.selectbox(
        "Problem type",
        options=display_options,
        index=default_idx,
        key="problem_type_select",
        help="Auto-detected from target column. Override if needed.",
    )
    problem_type = label_to_key.get(problem_label, PROBLEM_CLASSIFICATION)
    st.session_state["problem_type"] = problem_type

    # ---- Time column (conditional) ----
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

    # ---- Validation warnings ----
    if target_column is None and problem_type in (PROBLEM_CLASSIFICATION, PROBLEM_REGRESSION):
        st.warning(
            "You selected a supervised problem type but no target column. "
            "Please select a target or switch to Clustering / Time Series."
        )

    st.divider()

    # ---- User goal ----
    st.subheader("Analysis Goal")
    user_goal = st.text_area(
        "Describe your goal in plain language (optional)",
        value=st.session_state.get("user_goal", ""),
        height=100,
        placeholder="e.g. Predict which patients will be readmitted within 30 days...",
        key="user_goal_input",
    )
    st.session_state["user_goal"] = user_goal

    st.divider()

    # ---- Configuration summary ----
    st.subheader("Summary")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Domain", final_domain.title())
    summary_cols[1].metric("Mode", selected_mode.title())
    summary_cols[2].metric("Problem", problem_labels.get(problem_type, problem_type))
    summary_cols[3].metric("Target", target_column or "None")

    # ---- Start pipeline ----
    if st.button("Start Analysis", type="primary", use_container_width=True):
        st.session_state["pipeline_started"] = True
        st.session_state["current_step"] = "data_profiling"
        st.session_state["completed_steps"] = []
        st.session_state["workflow_status"] = "running"
        st.success("Pipeline started. Navigating to EDA...")
        st.switch_page("pages/03_eda_interactive.py")


_page()
