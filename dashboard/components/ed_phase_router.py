"""Two-phase router — Questions vs Results — with optional dev toggle in topbar."""
from __future__ import annotations
from typing import Literal
import streamlit as st

Phase = Literal["questions", "results"]
PHASE_KEY = "ed_phase"


def get_phase() -> Phase:
    return st.session_state.get(PHASE_KEY, "questions")


def set_phase(phase: Phase) -> None:
    st.session_state[PHASE_KEY] = phase


def auto_set_initial_phase() -> None:
    if PHASE_KEY in st.session_state:
        return
    if st.session_state.get("eda_results") and st.session_state.get("eda_charts"):
        set_phase("results")
    else:
        set_phase("questions")


def render_phase_toggle() -> None:
    has_results = bool(st.session_state.get("eda_results"))
    current = get_phase()
    cols = st.columns(2, gap="small")
    with cols[0]:
        if st.button("Questions", key="ed_pt_questions", use_container_width=True,
                     disabled=current == "questions"):
            set_phase("questions"); st.rerun()
    with cols[1]:
        if st.button("Results", key="ed_pt_results", use_container_width=True,
                     disabled=current == "results" or not has_results,
                     help="Run analysis first to view results" if not has_results else None):
            set_phase("results"); st.rerun()
