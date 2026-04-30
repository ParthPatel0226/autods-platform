# Spec 05 — Generalized Chat Composer

## Goal

Below the quality flags, render a single prominent chat composer that lets the user type any follow-up — request a new chart, drill into a column, compare segments. This replaces both the per-card "Ask a follow-up" input and the "Chat with these results" button (which were redundant).

When the user submits, the page calls `eda_agent.add_followup_analysis(state, request)` (or equivalent), gets back a new chart/insight/stat, and prepends it to the relevant section.

## File: `dashboard/components/ed_chat_composer.py`

```python
"""Generalized chat composer — request more charts/analyses via free text."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


# Curated suggestion pills — keep them short and actionable
SUGGESTIONS = [
    {"icon": "📈", "label": "Survival curves by age",
     "prompt": "Show survival curves split by age group with log-rank test"},
    {"icon": "📊", "label": "LOS by admission type",
     "prompt": "Compare length_of_stay across admission_type with ANOVA"},
    {"icon": "🔍", "label": "Missingness drill-in",
     "prompt": "Investigate missing value patterns and run Little's MCAR test"},
    {"icon": "📉", "label": "Time-to-event trend",
     "prompt": "Plot time-to-readmission distribution for the positive class"},
]

INPUT_KEY = "ed_chat_input"


def render(on_submit) -> None:
    """Render the chat composer.

    Args:
        on_submit(prompt_text) — called when user clicks Send or picks a suggestion.
            The page integration wires this to eda_agent.add_followup_analysis.
    """
    project = project_service.get_active()
    if not project:
        return

    st.markdown(
        '<section class="ed-chat-composer">'
        '  <div class="ed-chat-head">'
        '    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>'
        '    <h3 class="ed-chat-title">Ask for more <em>charts or analyses.</em></h3>'
        '  </div>'
        '  <p class="ed-chat-sub">Type any follow-up question — request a new visualization, drill into a specific column, or compare segments. AutoDS will run it and add the results above.</p>'
        '</section>',
        unsafe_allow_html=True,
    )

    # Input row — Streamlit native widgets inside a styled wrapper
    cols = st.columns([5, 1], gap="small")
    with cols[0]:
        prompt = st.text_input(
            "Follow-up question",
            value=st.session_state.get(INPUT_KEY, ""),
            placeholder="e.g., Show length_of_stay distribution split by gender, with a KS-test p-value",
            key=INPUT_KEY,
            label_visibility="collapsed",
        )
    with cols[1]:
        send_clicked = st.button("Send ▸", key="ed_chat_send",
                                 type="primary", use_container_width=True)

    # Suggestion pills
    st.markdown('<div class="ed-chat-suggestions">', unsafe_allow_html=True)
    st.markdown('<span class="ed-chat-suggestion-label">Try:</span>', unsafe_allow_html=True)
    pill_cols = st.columns(len(SUGGESTIONS))
    for col, sug in zip(pill_cols, SUGGESTIONS):
        with col:
            st.markdown(
                f'<div class="ed-chat-suggestion">'
                f'  <span style="font-size:12px;">{sug["icon"]}</span>'
                f'  {sug["label"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(sug["label"], key=f"ed_chat_sug_{sug['label']}",
                         use_container_width=True, label_visibility="collapsed"):
                st.session_state[INPUT_KEY] = sug["prompt"]
                _trigger_submit(sug["prompt"], on_submit)
    st.markdown('</div>', unsafe_allow_html=True)

    if send_clicked and prompt.strip():
        _trigger_submit(prompt.strip(), on_submit)


def _trigger_submit(prompt: str, on_submit) -> None:
    with st.spinner(f"Running: {prompt[:60]}..."):
        on_submit(prompt)
    # Clear the input after submission
    st.session_state[INPUT_KEY] = ""
    st.rerun()
```

## CSS additions

```css
/* ============ Generalized chat composer ============ */
.ed-chat-composer {
  background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(168,85,247,0.04));
  border: 1px solid var(--border-default); border-radius: 18px;
  padding: 22px 24px; margin: 28px 0 18px;
  backdrop-filter: blur(14px);
  position: relative; overflow: hidden;
}
.ed-chat-composer::before {
  content: ""; position: absolute; left: -30px; top: -30px;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(168,85,247,0.18), transparent 60%);
  pointer-events: none;
}
.ed-chat-head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.ed-chat-head svg { width: 18px; height: 18px; color: var(--violet); flex-shrink: 0; }
.ed-chat-title {
  font-family: var(--font-display); font-size: 22px;
  color: var(--text-primary);
}
.ed-chat-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ed-chat-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }

/* Restyle the input + Send button inside the composer */
[data-testid="stMain"] .stTextInput:has(+ * [key="ed_chat_send"]) > div > div > input,
[data-testid="stMain"] .stTextInput[data-key*="ed_chat_input"] > div > div > input {
  padding: 12px 16px !important;
  background: rgba(7,9,26,0.4) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 12px !important;
  color: var(--text-primary) !important;
  font-size: 14px !important;
}
[data-theme="light"] [data-testid="stMain"] .stTextInput[data-key*="ed_chat_input"] > div > div > input {
  background: rgba(255,255,255,0.6) !important;
}

[data-testid="stMain"] .stButton > button[key="ed_chat_send"] {
  padding: 12px 22px !important;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 12px !important;
  font-size: 13.5px !important; font-weight: 500 !important;
  box-shadow: 0 0 18px rgba(139,92,246,0.4) !important;
}
[data-testid="stMain"] .stButton > button[key="ed_chat_send"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 28px rgba(139,92,246,0.6) !important;
}

/* Suggestion pills */
.ed-chat-suggestions {
  display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;
  align-items: center;
}
.ed-chat-suggestion-label {
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 1px; text-transform: uppercase;
  color: var(--text-faint); padding: 4px 0; margin-right: 4px;
}
.ed-chat-suggestion {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; background: var(--bg-card);
  border: 1px solid var(--border-subtle); border-radius: 999px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  backdrop-filter: blur(8px); transition: all 0.18s ease;
}
.ed-chat-suggestion:hover {
  border-color: var(--violet); color: var(--text-primary); transform: translateY(-1px);
}

/* Hide the underlying suggestion buttons */
[data-testid="stMain"] .stButton > button[key^="ed_chat_sug_"] {
  background: transparent !important; border: 1px solid transparent !important;
  color: transparent !important;
  padding: 0 !important; height: 32px;
  position: absolute; inset: 0; cursor: pointer;
  box-shadow: none !important;
}
```

## Implementation note

- The composer is a single canonical chat surface for the page. All other follow-up inputs (per-card "anything else?" inputs in the Questions phase still exist for question-time customization, but the global Results-page chat is the primary ongoing dialogue surface).
- When the user submits, the page calls `eda_agent.add_followup_analysis(state, prompt)` (or wraps the existing `agents.followup_agent.handle(...)` if that's what the codebase exposes). The result is appended to `eda_charts` / `eda_insights` / `eda_stats` so it shows up at the top of the relevant section.
- The suggestion pills are curated; for a smarter version, generate them dynamically from the project's domain (`domains/<domain>.py`'s `eda_questions` could supply the pool).
