"""Single numbered question card with options + optional follow-up input."""
from __future__ import annotations
import streamlit as st


def render(question: dict, index: int, domain_label: str, answered: bool) -> dict:
    q_id = question["id"]
    q_type = question.get("type", "single_select")
    is_domain = bool(question.get("domain_specific"))
    classes = ["ed-q-card"]
    if answered:
        classes.append("ed-q-answered")
    domain_pill_html = (
        f"<span class='ed-domain-pill ed-domain-{_pill_class(domain_label)}'>{domain_label}</span>"
        if is_domain and domain_label
        else "<span class='ed-domain-pill ed-domain-general'>General</span>"
    )
    num_inner = "&#10003;" if answered else f"<span>{index:02d}</span>"
    st.markdown(
        f"<div class='{' '.join(classes)}'>"
        f"  <div class='ed-q-head'>"
        f"    <div class='ed-q-num'>{num_inner}</div>"
        f"    <div style='flex:1;'>"
        f"      <div class='ed-q-meta'>{domain_pill_html}</div>"
        f"      <div class='ed-q-title'>{_html_escape(question['question'])}</div>"
        f"    </div>"
        f"  </div>",
        unsafe_allow_html=True,
    )
    if question.get("recommendation_reason"):
        st.markdown(
            f"<div class='ed-q-tip'>"
            f"  <svg width='14' height='14' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><line x1='12' y1='2' x2='12' y2='6'/><circle cx='12' cy='12' r='4'/><line x1='12' y1='18' x2='12' y2='22'/></svg>"
            f"  {_html_escape(question['recommendation_reason'])}"
            f"</div>",
            unsafe_allow_html=True,
        )
    answer_value = None
    if q_type == "single_select":
        answer_value = _render_single_select(question, q_id)
    elif q_type == "multi_select":
        answer_value = _render_multi_select(question, q_id)
    else:
        answer_value = st.text_input("Your answer", key=f"ed_ans_{q_id}", label_visibility="collapsed")
    followup = ""
    if question.get("allow_followup", q_type == "multi_select"):
        st.markdown("<div class='ed-q-followup'><label>Anything else? Add a custom request:</label></div>", unsafe_allow_html=True)
        followup = st.text_input("Custom follow-up", key=f"ed_followup_{q_id}",
                                  placeholder="e.g., distribution of length_of_stay split by gender",
                                  label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"id": q_id, "value": answer_value, "followup": followup}


def _render_single_select(question: dict, q_id: str) -> str:
    options = question.get("options", [])
    selected = st.session_state.get(f"ed_ans_{q_id}", _default_value(options))
    st.markdown("<div class='ed-options'>", unsafe_allow_html=True)
    for opt in options:
        val = opt["value"]
        is_sel = val == selected
        rec_html = "<div class='ed-option-rec'>&#9733; Recommended</div>" if opt.get("recommended") else ""
        st.markdown(
            f"<div class='ed-option{' ed-option-selected' if is_sel else ''}'>"
            f"  <div class='ed-option-radio'></div>"
            f"  <div class='ed-option-label'>{_html_escape(opt['label'])}</div>"
            f"  {rec_html}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(opt["label"], key=f"ed_opt_{q_id}_{val}", use_container_width=True, label_visibility="collapsed"):
            st.session_state[f"ed_ans_{q_id}"] = val
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    return selected


def _render_multi_select(question: dict, q_id: str) -> list:
    options = question.get("options", [])
    state_key = f"ed_ans_{q_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = [o["value"] for o in options if o.get("recommended")]
    selected = st.session_state[state_key]
    st.markdown("<div class='ed-options'>", unsafe_allow_html=True)
    for opt in options:
        val = opt["value"]
        is_sel = val in selected
        rec_html = "<div class='ed-option-rec'>&#9733; Recommended</div>" if opt.get("recommended") else ""
        st.markdown(
            f"<div class='ed-option{' ed-option-selected' if is_sel else ''}'>"
            f"  <div class='ed-option-checkbox'></div>"
            f"  <div class='ed-option-label'>{_html_escape(opt['label'])}</div>"
            f"  {rec_html}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(opt["label"], key=f"ed_opt_{q_id}_{val}", use_container_width=True, label_visibility="collapsed"):
            cur = st.session_state[state_key]
            st.session_state[state_key] = [v for v in cur if v != val] if val in cur else [*cur, val]
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    return selected


def _default_value(options: list) -> str:
    for o in options:
        if o.get("recommended"):
            return o["value"]
    return options[0]["value"] if options else ""


def _pill_class(label: str) -> str:
    label_lower = (label or "").lower()
    for key in ("healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing"):
        if key in label_lower:
            return key
    return "general"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
