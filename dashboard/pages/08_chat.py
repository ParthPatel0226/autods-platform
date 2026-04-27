"""Page 08 -- Follow-Up Chat.

Conversational interface for asking questions about data, results,
and analysis.  Delegates to the follow-up agent.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from dashboard.components.shared_css import inject_shared_css

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
# Design tokens
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* handled by shared_css.py */

/* Page title */
.page-title {
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-bottom: 1.5rem;
}

/* Chat container */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
    max-height: 60vh;
    overflow-y: auto;
}

/* Message bubbles */
.msg-row {
    display: flex;
    width: 100%;
    animation: msgFadeIn 0.3s ease;
}
@keyframes msgFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }

.msg-bubble {
    max-width: 75%;
    padding: 0.875rem 1.125rem;
    border-radius: var(--radius-md);
    font-size: 0.88rem;
    line-height: 1.6;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: var(--shadow-card);
}
.msg-bubble.user {
    background: var(--accent-primary-subtle);
    border: 1px solid var(--accent-primary-light);
    color: var(--text-primary);
    border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    border-bottom-left-radius: 4px;
}

.msg-role {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
}
.msg-role.user { color: var(--accent-primary); }
.msg-role.assistant { color: var(--text-muted); }

/* Suggestion pills */
.suggestion-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.suggestion-pill {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 0.625rem 1rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    text-align: left;
}
.suggestion-pill:hover {
    border-color: var(--border-active);
    color: var(--text-primary);
    background: var(--accent-primary-subtle);
}

/* Input area card */
.input-area {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.75rem;
    margin-top: 1rem;
    box-shadow: var(--shadow-card);
    position: sticky;
    bottom: 0;
}

/* Override Streamlit chat input */
div[data-testid="stChatInput"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
}
div[data-testid="stChatInput"] textarea {
    color: var(--text-primary) !important;
    background: transparent !important;
}

/* Override Streamlit chat message */
div[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* Context sidebar */
.context-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 0.875rem;
    margin-bottom: 0.75rem;
}
.context-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.2rem;
}
.context-value {
    font-size: 0.82rem;
    color: var(--text-primary);
    font-weight: 500;
}

/* Alert overrides */
div[data-testid="stAlert"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    color: var(--text-primary) !important;
}

.glass-caption {
    font-size: 0.78rem;
    color: var(--text-muted);
}
</style>
"""


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.info("Complete the analysis pipeline first to use the chat interface. Ask follow-up questions about your data, request additional analyses, or explore model decisions.")
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
        st.markdown(
            '<div class="section-header">Analysis Context</div>',
            unsafe_allow_html=True,
        )
        domain = st.session_state.get("detected_domain", "generic")
        best = st.session_state.get("best_model_name", "")
        problem = st.session_state.get("problem_type", "")
        n_rows = st.session_state.get("row_count", 0)

        ctx_items = [
            ("Domain", domain),
            ("Problem", problem),
        ]
        if best:
            ctx_items.append(("Model", best))
        if n_rows:
            ctx_items.append(("Rows", f"{n_rows:,}"))

        for label, value in ctx_items:
            st.markdown(
                f'<div class="context-card">'
                f'<div class="context-label">{label}</div>'
                f'<div class="context-value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_suggestions() -> None:
    """Show clickable suggested questions as glass pills."""
    st.markdown(
        '<p class="glass-caption" style="margin-bottom:0.75rem;">Suggested questions to get started:</p>',
        unsafe_allow_html=True,
    )

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
    """Render all messages as styled glass bubbles."""
    messages = st.session_state.get("chat_messages", [])
    if not messages:
        return

    chat_html = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"].replace("\n", "<br>")
        role_label = "You" if role == "user" else "AutoDS"
        chat_html += (
            f'<div class="msg-row {role}">'
            f'<div class="msg-bubble {role}">'
            f'<div class="msg-role {role}">{role_label}</div>'
            f'{content}'
            f'</div></div>'
        )

    st.markdown(
        f'<div class="chat-container">{chat_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    inject_shared_css()
    _guard()
    _init_chat()
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Ask Anything</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Ask questions about your data, models, and analysis results</div>', unsafe_allow_html=True)
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
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1px; background:var(--border-subtle); margin:0.5rem 0 1.5rem;"></div>', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Predictions", use_container_width=True):
            st.switch_page("pages/07_predict.py")
    with col_next:
        if st.button("Proceed to Downloads", type="primary", use_container_width=True):
            st.switch_page("pages/09_download.py")



def _is_streamlit_running() -> bool:
    """Return True only when executing inside a Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _is_streamlit_running():
    _page()
