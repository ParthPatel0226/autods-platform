"""Generalized chat composer — request more charts/analyses via free text."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


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
                         use_container_width=True):
                st.session_state[INPUT_KEY] = sug["prompt"]
                _trigger_submit(sug["prompt"], on_submit)
    st.markdown('</div>', unsafe_allow_html=True)

    if send_clicked and prompt.strip():
        _trigger_submit(prompt.strip(), on_submit)


def _trigger_submit(prompt: str, on_submit) -> None:
    with st.spinner(f"Running: {prompt[:60]}..."):
        on_submit(prompt)
    st.session_state[INPUT_KEY] = ""
    st.rerun()
