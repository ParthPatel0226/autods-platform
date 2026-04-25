"""Question Renderer — renders interactive questions in Streamlit UI.

Supports multiple question types:
- single_select: Radio buttons with recommendation highlighting
- multi_select: Checkboxes with domain recommendations
- slider: Numeric slider for thresholds
- per_column_table: Table with per-column dropdown selections
- text_input: Free-text input
- number_input: Numeric input
"""

import logging
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


def render_question(question: dict, key_prefix: str = "") -> Any:
    """Render a single interactive question and return the user's response.
    
    Args:
        question: Question dict with id, question, type, options, etc.
        key_prefix: Prefix for Streamlit widget keys to avoid collisions.
        
    Returns:
        User's selection/input value.
    """
    q_id = f"{key_prefix}_{question['id']}"
    q_text = question["question"]
    q_type = question.get("type", "single_select")
    options = question.get("options", [])
    recommendation = question.get("recommendation_reason", "")

    # Show recommendation badge if present
    if recommendation and question.get("show_recommendation", True):
        st.caption(f"💡 *{recommendation}*")

    if q_type == "single_select":
        return _render_single_select(q_id, q_text, options)

    elif q_type == "multi_select":
        return _render_multi_select(q_id, q_text, options)

    elif q_type == "slider":
        return _render_slider(q_id, q_text, question)

    elif q_type == "per_column_table":
        return _render_per_column_table(q_id, q_text, question)

    elif q_type == "text_input":
        return st.text_input(q_text, key=q_id)

    elif q_type == "number_input":
        return st.number_input(
            q_text,
            min_value=question.get("min", 0),
            max_value=question.get("max", 1000),
            value=question.get("default", 0),
            key=q_id,
        )

    else:
        st.warning(f"Unknown question type: {q_type}")
        return None


def _render_single_select(q_id: str, q_text: str, options: list[dict]) -> str:
    """Render single-select radio buttons with recommendation highlighting."""
    labels = []
    for opt in options:
        label = opt["label"]
        if opt.get("recommended"):
            label += " ⭐ *recommended*"
        labels.append(label)

    # Find default index (recommended option)
    default_idx = 0
    for i, opt in enumerate(options):
        if opt.get("recommended"):
            default_idx = i
            break

    selected_label = st.radio(q_text, labels, index=default_idx, key=q_id)

    # Map label back to value
    for i, label in enumerate(labels):
        if label == selected_label:
            return options[i]["value"]
    return options[0]["value"]


def _render_multi_select(q_id: str, q_text: str, options: list[dict]) -> list[str]:
    """Render multi-select checkboxes."""
    st.write(q_text)
    selected = []
    for opt in options:
        label = opt["label"]
        if opt.get("recommended"):
            label += " ⭐"
        default_checked = opt.get("recommended", False)
        if st.checkbox(label, value=default_checked, key=f"{q_id}_{opt['value']}"):
            selected.append(opt["value"])
    return selected


def _render_slider(q_id: str, q_text: str, question: dict) -> float:
    """Render a numeric slider."""
    return st.slider(
        q_text,
        min_value=question.get("min", 0.0),
        max_value=question.get("max", 1.0),
        value=question.get("default", 0.5),
        step=question.get("step", 0.01),
        key=q_id,
    )


def _render_per_column_table(q_id: str, q_text: str, question: dict) -> dict:
    """Render a per-column decision table with dropdowns.
    
    Used for: missing value strategy, encoding strategy, outlier handling.
    Each row is a column in the dataset, with a dropdown for the strategy.
    """
    st.write(q_text)

    columns = question.get("columns", [])
    strategy_options = question.get("strategy_options", [])
    strategy_labels = [s["label"] for s in strategy_options]
    strategy_values = [s["value"] for s in strategy_options]

    decisions = {}

    # Create a table-like layout
    cols_header = st.columns([3, 2, 2, 3])
    cols_header[0].markdown("**Column**")
    cols_header[1].markdown("**Info**")
    cols_header[2].markdown("**Recommended**")
    cols_header[3].markdown("**Your Choice**")

    for col_info in columns:
        col_name = col_info["name"]
        cols = st.columns([3, 2, 2, 3])
        cols[0].write(col_name)
        cols[1].write(col_info.get("info", ""))
        cols[2].write(col_info.get("recommended", ""))

        # Find default index
        rec_value = col_info.get("recommended_value", strategy_values[0])
        default_idx = strategy_values.index(rec_value) if rec_value in strategy_values else 0

        selected = cols[3].selectbox(
            f"Strategy for {col_name}",
            strategy_labels,
            index=default_idx,
            key=f"{q_id}_{col_name}",
            label_visibility="collapsed",
        )

        # Map label back to value
        idx = strategy_labels.index(selected)
        decisions[col_name] = strategy_values[idx]

    return decisions


def render_question_group(
    questions: list[dict],
    key_prefix: str = "",
    show_step_header: bool = True,
) -> dict[str, Any]:
    """Render a group of questions and collect all responses.
    
    Args:
        questions: List of question dicts.
        key_prefix: Prefix for Streamlit keys.
        show_step_header: Whether to show the step name as a header.
        
    Returns:
        Dict mapping question_id → user response.
    """
    responses = {}

    for i, question in enumerate(questions):
        if i > 0:
            st.divider()

        response = render_question(question, key_prefix=key_prefix)
        responses[question["id"]] = response

    return responses
