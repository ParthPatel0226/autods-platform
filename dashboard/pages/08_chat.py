"""Page 08 -- Follow-Up Chat.

Conversational interface for asking questions about data, results,
and analysis.  Delegates to the follow-up agent.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)

_SUGGESTED_QUESTIONS: list[str] = [
    "What are the most important features driving predictions?",
    "Are there any data quality issues I should worry about?",
    "How confident should I be in these results?",
    "What would improve model performance?",
    "Can you explain the prediction for row X?",
    "What biases might exist in the model?",
]


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()


# ---------------------------------------------------------------------------
# Chat logic
# ---------------------------------------------------------------------------

def _init_chat() -> None:
    """Initialize chat history in session state."""
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []


def _render_progress() -> None:
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "followup"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_context_summary() -> None:
    """Show a collapsible summary of available context."""
    with st.sidebar:
        st.markdown("##### Analysis Context")
        domain = st.session_state.get("detected_domain", "generic")
        best = st.session_state.get("best_model_name", "")
        problem = st.session_state.get("problem_type", "")
        n_rows = st.session_state.get("row_count", 0)

        st.caption(f"Domain: {domain}")
        st.caption(f"Problem: {problem}")
        if best:
            st.caption(f"Model: {best}")
        if n_rows:
            st.caption(f"Rows: {n_rows:,}")


def _render_suggestions() -> None:
    """Show clickable suggested questions."""
    st.caption("Suggested questions:")
    cols = st.columns(3)
    for i, q in enumerate(_SUGGESTED_QUESTIONS):
        col = cols[i % 3]
        if col.button(q, key=f"suggest_{i}", use_container_width=True):
            _add_user_message(q)
            st.rerun()


def _add_user_message(content: str) -> None:
    """Append a user message to chat history."""
    st.session_state["chat_messages"].append({"role": "user", "content": content})

    # Generate placeholder response (follow-up agent integration point)
    response = _generate_response(content)
    st.session_state["chat_messages"].append({"role": "assistant", "content": response})


def _generate_response(question: str) -> str:
    """Generate a response using available context.

    When the follow-up agent is connected, this delegates to it.
    Otherwise returns a context-aware placeholder.
    """
    # Check if follow-up agent callback is registered
    agent_fn = st.session_state.get("followup_agent_fn")
    if agent_fn is not None:
        try:
            return agent_fn(question, _build_context())
        except Exception as exc:
            logger.error("Follow-up agent error: %s", exc)
            return f"Error processing question: {exc}"

    # Placeholder response using local context
    return _local_response(question)


def _build_context() -> dict[str, Any]:
    """Assemble analysis context for the follow-up agent."""
    return {
        "domain": st.session_state.get("detected_domain", "generic"),
        "problem_type": st.session_state.get("problem_type", ""),
        "best_model": st.session_state.get("best_model_name", ""),
        "best_metrics": st.session_state.get("best_model_metrics", {}),
        "feature_importance": st.session_state.get("feature_importance", {}),
        "eda_insights": st.session_state.get("eda_insights", []),
        "fairness_report": st.session_state.get("fairness_report"),
        "quality_issues": st.session_state.get("quality_issues", []),
    }


def _local_response(question: str) -> str:
    """Build a basic response from session state context."""
    ctx = _build_context()
    parts: list[str] = []

    q_lower = question.lower()

    if "important" in q_lower or "feature" in q_lower:
        imp = ctx.get("feature_importance", {})
        if imp:
            top = sorted(imp.items(), key=lambda x: x[1], reverse=True)[:5]
            parts.append("Top features by importance:")
            for name, val in top:
                parts.append(f"  - {name}: {val:.4f}")
        else:
            parts.append("Feature importance not yet computed. Run explainability first.")

    elif "quality" in q_lower or "issue" in q_lower:
        issues = ctx.get("quality_issues", [])
        if issues:
            parts.append(f"Found {len(issues)} data quality issue(s):")
            for issue in issues[:5]:
                desc = issue.get("description", str(issue))
                parts.append(f"  - {desc}")
        else:
            parts.append("No data quality issues detected.")

    elif "confidence" in q_lower or "reliable" in q_lower:
        metrics = ctx.get("best_metrics", {})
        model = ctx.get("best_model")
        if metrics:
            parts.append(f"Model '{model}' metrics:")
            for k, v in list(metrics.items())[:5]:
                parts.append(f"  - {k}: {v}")
        else:
            parts.append("Model metrics not available yet.")

    elif "bias" in q_lower or "fair" in q_lower:
        fairness = ctx.get("fairness_report")
        if fairness:
            overall = fairness.get("overall_assessment", "See fairness tab for details.")
            parts.append(f"Fairness assessment: {overall}")
        else:
            parts.append("Fairness audit not yet run. Check the Explainability tab.")

    else:
        parts.append(
            "The follow-up agent is not yet connected. "
            "Once connected, it will answer questions using your full analysis context. "
            "For now, try questions about features, data quality, confidence, or fairness."
        )

    return "\n".join(parts)


def _render_chat_history() -> None:
    """Render all messages in chat history."""
    for msg in st.session_state.get("chat_messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    _init_chat()
    st.header("Ask Anything")
    _render_progress()
    _render_context_summary()

    if not st.session_state["chat_messages"]:
        _render_suggestions()

    _render_chat_history()

    user_input = st.chat_input("Ask a question about your data or analysis...")
    if user_input:
        _add_user_message(user_input)
        st.rerun()

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Predictions", use_container_width=True):
            st.switch_page("pages/07_predict.py")
    with col_next:
        if st.button("Proceed to Downloads", type="primary", use_container_width=True):
            st.switch_page("pages/09_download.py")


_page()
