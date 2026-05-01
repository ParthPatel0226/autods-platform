"""Page 02 -- Configure (Phase 2B redesign).

5-section left column + sticky summary right column.
All domain logic via cf_domain_adapter — no direct domain_registry imports.
"""
from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from dashboard.components.shared_css import inject_shared_css
from dashboard.components import cf_domain_cards
from dashboard.components import cf_domain_why
from dashboard.components import cf_compliance_notice
from dashboard.components import cf_mode_cards
from dashboard.components import cf_unsure_helper
from dashboard.components import cf_problem_pills
from dashboard.components import cf_target_goal
from dashboard.components import cf_excluded_columns
from dashboard.components import cf_summary_panel
from dashboard.components.cf_pipeline_estimator import estimate as estimate_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions (defined BEFORE any call sites)
# ---------------------------------------------------------------------------

def _infer_problem_type(df, target: str) -> str:
    """Try orchestrator heuristic; fall back to 'auto' on any error."""
    try:
        from agents.orchestrator import infer_problem_type  # type: ignore
        return infer_problem_type(df, target) or "auto"
    except Exception:
        pass
    # Local heuristic fallback
    try:
        import pandas as pd
        if not target or target not in df.columns:
            return "clustering"
        s = df[target]
        if pd.api.types.is_float_dtype(s) and s.nunique() > 20:
            return "regression"
        if s.nunique() <= 20:
            return "classification"
    except Exception:
        pass
    return "auto"


def _handle_start_analysis(payload: dict[str, Any]) -> None:
    """Persist configuration and navigate to EDA."""
    try:
        from dashboard.components.project_service import ProjectService
        svc = ProjectService()
        proj = svc.get_or_create_current()
        proj.confirmed_domain = payload.get("domain", "")
        proj.analysis_mode = payload.get("mode", "guided")
        proj.problem_type = payload.get("problem_type", "auto")
        proj.target_column = payload.get("target_column", "")
        proj.goal = payload.get("goal", "")
        proj.excluded_columns = payload.get("excluded_columns", [])
        proj.step_status["configure"] = "done"
        proj.step_status["eda"] = "active"
        svc.save(proj)
    except Exception as exc:
        logger.warning("project_service save failed: %s", exc)

    # Mirror key values into session_state for EDA page
    st.session_state["confirmed_domain"] = payload.get("domain", "")
    st.session_state["user_mode"] = payload.get("mode", "guided")
    st.session_state["problem_type"] = payload.get("problem_type", "auto")
    st.session_state["target_column"] = payload.get("target_column", "")
    st.session_state["user_goal"] = payload.get("goal", "")
    st.session_state["excluded_columns"] = payload.get("excluded_columns", [])
    st.session_state["pipeline_started"] = True
    st.session_state["current_step"] = "eda"

    st.switch_page("pages/03_eda_interactive.py")


def _get_detected_domain(df) -> str:
    """Detect domain from df columns; cache result in session_state."""
    if "detected_domain" in st.session_state and st.session_state["detected_domain"]:
        return st.session_state["detected_domain"]
    try:
        from domains.domain_registry import detect_domain
        cols = list(df.columns)
        sample = {c: df[c].dropna().astype(str).head(5).tolist() for c in cols[:20]}
        result = detect_domain(cols, sample)
        # detect_domain may return (domain, confidence, cfg) or just domain
        domain = result[0] if isinstance(result, (tuple, list)) else result
        st.session_state["detected_domain"] = domain or "generic"
    except Exception:
        st.session_state["detected_domain"] = "generic"
    return st.session_state["detected_domain"]


def _render_recap(df) -> None:
    """Render a compact dataset recap row."""
    n_rows, n_cols = df.shape
    st.markdown(
        f'<div class="cf-recap-bar">'
        f'  <span class="cf-recap-item">📂 <b>{st.session_state.get("dataset_name","Dataset")}</b></span>'
        f'  <span class="cf-recap-sep">·</span>'
        f'  <span class="cf-recap-item">{n_rows:,} rows</span>'
        f'  <span class="cf-recap-sep">·</span>'
        f'  <span class="cf-recap-item">{n_cols} columns</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def _page() -> None:
    st.set_page_config(page_title="Configure — AutoDS", layout="wide", page_icon="⚙️")
    inject_shared_css()

    if "uploaded_data" not in st.session_state:
        st.info(
            "No dataset loaded yet. Upload a dataset first. "
            "Configure sets the domain, mode, target, and analysis goals."
        )
        st.stop()

    df = st.session_state["uploaded_data"]

    # Breadcrumb
    st.markdown(
        '<div class="cf-breadcrumb">AutoDS → <b>Configure</b></div>',
        unsafe_allow_html=True,
    )

    # Hero
    st.markdown(
        '<div class="cf-hero">'
        '  <h1 class="cf-hero-title">Configure Your Analysis</h1>'
        '  <p class="cf-hero-sub">Confirm the domain, choose your mode, and define what you want to discover.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    _render_recap(df)

    # Two-column layout: left content (1.0) + right sticky summary (0.42)
    left, right = st.columns([1.0, 0.42], gap="large")

    with left:
        # ---- Section 1: Domain ----
        st.markdown('<div class="cf-section-header">1 · Domain</div>', unsafe_allow_html=True)
        detected_domain = _get_detected_domain(df)
        selected_domain = cf_domain_cards.render(
            detected_domain=detected_domain,
            on_select=lambda d: st.session_state.update({"cf_selected_domain": d}),
        )
        if not selected_domain:
            selected_domain = detected_domain

        cf_domain_why.render(selected_domain, df)
        cf_compliance_notice.render(selected_domain)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ---- Section 2: Mode ----
        st.markdown('<div class="cf-section-header">2 · Analysis Mode</div>', unsafe_allow_html=True)
        cf_mode_cards.render()
        cf_unsure_helper.render(columns=list(df.columns))

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ---- Section 3: Problem Type ----
        st.markdown('<div class="cf-section-header">3 · Problem Type</div>', unsafe_allow_html=True)
        detected_pt = _infer_problem_type(df, st.session_state.get("cf_target", ""))
        cf_problem_pills.render(detected_type=detected_pt)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ---- Section 4: Target & Goal ----
        st.markdown('<div class="cf-section-header">4 · Target Column & Goal</div>', unsafe_allow_html=True)
        problem_type = st.session_state.get("cf_problem_type", detected_pt)
        cf_target_goal.render(
            columns=list(df.columns),
            domain_key=selected_domain,
            problem_type=problem_type,
        )

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ---- Section 5: Excluded Columns ----
        st.markdown('<div class="cf-section-header">5 · Excluded Columns</div>', unsafe_allow_html=True)
        target = st.session_state.get("cf_target", "")
        cf_excluded_columns.render(df=df, target=target)

    with right:
        # Build estimate for summary panel
        n_cols_kept = len(df.columns) - len(st.session_state.get("cf_excluded", set()))
        est = estimate_pipeline(
            n_rows=len(df),
            n_cols_kept=max(n_cols_kept, 1),
            mode=st.session_state.get("cf_mode", "guided"),
            problem_type=st.session_state.get("cf_problem_type", "auto"),
            domain_key=st.session_state.get("cf_selected_domain", "generic"),
        )
        cf_summary_panel.render(on_start=_handle_start_analysis, estimate=est)


def _is_streamlit_running() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _is_streamlit_running():
    _page()
