# Spec 01 — Chat Tab (page 08_chat.py)

## Backend: `agents/followup_agent.py`

**Open first.** Expected interface:
```python
def handle(question: str, context: dict) -> str:
    """Takes a user question + pipeline context, returns an LLM answer."""
```

Context includes: domain, target, problem_type, model_results, eda_insights, feature_list, shap_data.

## File Plan

```
dashboard/components/ch_message_bubble.py     # Renders a single message (user or AI)
dashboard/components/ch_suggestions.py        # 6 clickable suggestion cards
dashboard/components/ch_context_panel.py      # Collapsible analysis context
dashboard/pages/08_chat.py                    # Full rewrite
```

## File: `dashboard/components/ch_message_bubble.py`

```python
"""Chat message bubble — user (right, violet) or AI (left, glass)."""
from __future__ import annotations
import streamlit as st


def render(role: str, content: str, timestamp: str = "") -> None:
    """Render a single message.
    
    Args:
        role: "user" or "assistant"
        content: message text (may contain markdown-safe HTML)
        timestamp: optional display timestamp
    """
    if role == "user":
        st.markdown(
            f'<div class="ch-msg ch-msg-user">'
            f'  <div class="ch-msg-bubble ch-bubble-user">{content}</div>'
            f'  {f"<div class=\"ch-msg-time\">{timestamp}</div>" if timestamp else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="ch-msg ch-msg-ai">'
            f'  <div class="ch-msg-avatar">A</div>'
            f'  <div class="ch-msg-bubble ch-bubble-ai">{content}</div>'
            f'  {f"<div class=\"ch-msg-time\">{timestamp}</div>" if timestamp else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )
```

## File: `dashboard/components/ch_suggestions.py`

```python
"""6 domain-aware suggestion cards for the chat."""
from __future__ import annotations
import streamlit as st
from dashboard.components import project_service
from domains.domain_registry import DOMAIN_REGISTRY


DEFAULT_SUGGESTIONS = [
    {"icon": "🎯", "text": "What are the most important features driving predictions?"},
    {"icon": "⚠", "text": "Are there any data quality issues I should worry about?"},
    {"icon": "📊", "text": "How confident should I be in these results?"},
    {"icon": "🔧", "text": "What would improve model performance?"},
    {"icon": "🔬", "text": "Can you explain the prediction for a specific row?"},
    {"icon": "⚖", "text": "What biases might exist in the model?"},
]

DOMAIN_SUGGESTIONS = {
    "healthcare": [
        {"icon": "🏥", "text": "Which comorbidities drive the highest readmission risk?"},
        {"icon": "👴", "text": "How does age interact with readmission prediction?"},
    ],
    "finance": [
        {"icon": "💳", "text": "What are the top adverse action reasons for denied applicants?"},
        {"icon": "📈", "text": "How does the model handle applicants with thin credit files?"},
    ],
}


def render(on_click) -> None:
    """Render suggestion cards. on_click(text) called when user clicks one."""
    project = project_service.get_active()
    domain = (project.confirmed_domain or "generic") if project else "generic"
    
    suggestions = DEFAULT_SUGGESTIONS.copy()
    if domain in DOMAIN_SUGGESTIONS:
        suggestions = DOMAIN_SUGGESTIONS[domain] + suggestions[:4]

    st.markdown(
        '<div class="ch-suggestions-header">Suggested questions to get started:</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3, gap="small")
    for i, sug in enumerate(suggestions[:6]):
        with cols[i % 3]:
            st.markdown(
                f'<div class="ch-suggestion">'
                f'  <span class="ch-sug-icon">{sug["icon"]}</span>'
                f'  {sug["text"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(sug["text"], key=f"ch_sug_{i}",
                         use_container_width=True, label_visibility="collapsed"):
                on_click(sug["text"])
```

## File: `dashboard/pages/08_chat.py` (full rewrite)

```python
"""Chat tab — conversational follow-up with the pipeline."""
from __future__ import annotations
from datetime import datetime
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar
from dashboard.components.ch_message_bubble import render as render_message
from dashboard.components.ch_suggestions import render as render_suggestions

st.set_page_config(page_title="AutoDS — Chat", page_icon="💬",
                   layout="wide", initial_sidebar_state="expanded")
inject_shared_css()

if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py"); st.stop()
render_sidebar()
project = project_service.get_active()
if not project:
    st.warning("Open a project first.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

# Hero
st.markdown(
    '<section class="ch-hero">'
    '  <h1 style="font-family:var(--font-display);font-size:48px;margin-bottom:8px;">'
    '    Ask <em style="font-style:italic;background:var(--gradient-text);'
    '    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">'
    '    anything.</em></h1>'
    '  <p style="color:var(--text-muted);font-size:15px;">Ask questions about your data, models, and analysis results.</p>'
    '</section>',
    unsafe_allow_html=True,
)

# Init messages
if "ch_messages" not in st.session_state:
    st.session_state["ch_messages"] = []

messages = st.session_state["ch_messages"]

# Show suggestions if no messages yet
if not messages:
    render_suggestions(on_click=_submit_message)

# Render message history
for msg in messages:
    render_message(msg["role"], msg["content"], msg.get("time", ""))

# Input
prompt = st.chat_input("Ask a question about your data or analysis...", key="ch_input")
if prompt:
    _submit_message(prompt)


def _submit_message(text: str) -> None:
    """Submit a message, get AI response, update history."""
    now = datetime.now().strftime("%H:%M")
    st.session_state["ch_messages"].append({"role": "user", "content": text, "time": now})

    with st.spinner("Thinking..."):
        response = _get_response(text)

    st.session_state["ch_messages"].append({"role": "assistant", "content": response, "time": now})
    st.rerun()


def _get_response(question: str) -> str:
    """Get response from followup_agent."""
    try:
        from agents.followup_agent import handle
        context = {
            "domain": project.confirmed_domain or project.detected_domain,
            "target_column": project.target_column,
            "problem_type": project.problem_type,
            "model_results": st.session_state.get("model_results"),
            "eda_insights": st.session_state.get("eda_insights"),
            "shap_data": st.session_state.get("ex_shap_data"),
        }
        return handle(question, context)
    except Exception as e:
        return f"I encountered an issue: {e}. The follow-up agent may not be fully wired yet."


# Bottom nav
cols = st.columns([1, 1])
with cols[0]:
    if st.button("← Back to Predictions", key="ch_back", use_container_width=True):
        st.switch_page("pages/07_predict.py")
with cols[1]:
    if st.button("Proceed to Downloads →", key="ch_forward", type="primary", use_container_width=True):
        project.step_status["chat"] = "done"
        project.step_status["download"] = "active"
        project_service.update(project)
        st.switch_page("pages/09_download.py")
```

## CSS additions

```css
/* ============ Chat ============ */
.ch-hero { margin-bottom: 28px; }
.ch-suggestions-header { font-size: 15px; font-weight: 500; margin-bottom: 14px; }
.ch-suggestion {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 14px;
  font-size: 13.5px; color: var(--text-secondary); cursor: pointer;
  transition: all 0.2s ease; backdrop-filter: blur(14px); margin-bottom: 10px;
  min-height: 64px;
}
.ch-suggestion:hover { border-color: var(--border-strong); transform: translateY(-2px);
  box-shadow: 0 4px 18px -6px rgba(139,92,246,0.3); }
.ch-sug-icon { font-size: 18px; }

.ch-msg { display: flex; gap: 12px; margin-bottom: 16px; max-width: 80%; }
.ch-msg-user { margin-left: auto; flex-direction: row-reverse; }
.ch-msg-ai { margin-right: auto; }
.ch-msg-avatar { width: 32px; height: 32px; border-radius: 50%;
  background: var(--gradient-button); display: grid; place-items: center;
  font-family: var(--font-display); font-size: 14px; color: white; font-style: italic;
  flex-shrink: 0; }
.ch-msg-bubble { padding: 14px 18px; border-radius: 16px;
  font-size: 14px; line-height: 1.6; }
.ch-bubble-user { background: linear-gradient(135deg, var(--indigo), var(--violet));
  color: white; border-bottom-right-radius: 4px; }
.ch-bubble-ai { background: var(--bg-card); border: 1px solid var(--border-default);
  color: var(--text-secondary); border-bottom-left-radius: 4px;
  backdrop-filter: blur(14px); }
.ch-msg-time { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  margin-top: 4px; }
.ch-msg-user .ch-msg-time { text-align: right; }
```
