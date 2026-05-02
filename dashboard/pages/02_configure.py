"""Page 02 -- Configure (Phase 2B redesign).

5-section left column + sticky summary right column.
All domain logic via cf_domain_adapter — no direct domain_registry imports.
Follows the same auth + project + sidebar pattern as 01_upload.py.
"""
from __future__ import annotations

import logging

import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

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
# Helpers
# ---------------------------------------------------------------------------

def _infer_problem_type(df, project, domain: str) -> str:
    """Reuse orchestrator heuristic; fall back to local logic."""
    if project and project.problem_type:
        return project.problem_type
    try:
        from agents.orchestrator import infer_problem_type  # type: ignore
        return infer_problem_type(df, domain=domain) or "auto"
    except Exception:
        pass
    try:
        import pandas as pd
        target = (project.target_column if project else "") or ""
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


def _handle_start_analysis(payload: dict) -> None:
    """Persist configuration, advance step status, navigate to EDA."""
    p = project_service.get_active()
    try:
        if p:
            p.confirmed_domain = payload.get("domain", "")
            p.analysis_mode = payload.get("mode", "guided")
            p.problem_type = payload.get("problem_type", "auto")
            p.target_column = payload.get("target_column", "")
            p.goal = payload.get("goal", "")
            p.excluded_columns = payload.get("excluded_columns", [])
            p.step_status["configure"] = "done"
            p.step_status["eda"] = "active"
            project_service.update(p)
    except Exception as exc:
        logger.warning("project_service save failed: %s", exc)

    # Mirror to session_state for downstream pages
    st.session_state["confirmed_domain"] = payload.get("domain", "")
    st.session_state["domain"] = payload.get("domain", "")
    st.session_state["user_mode"] = payload.get("mode", "guided")
    st.session_state["analysis_mode"] = payload.get("mode", "guided")
    st.session_state["problem_type"] = payload.get("problem_type", "auto")
    st.session_state["target_column"] = payload.get("target_column", "")
    st.session_state["user_goal"] = payload.get("goal", "")
    st.session_state["analysis_goal"] = payload.get("goal", "")
    st.session_state["excluded_columns"] = payload.get("excluded_columns", [])
    st.session_state["pipeline_started"] = True
    st.session_state["current_step"] = "eda"

    st.switch_page("pages/03_eda_interactive.py")


def _get_detected_domain(df, project) -> str:
    """Detect domain; prefer project record, cache in session_state."""
    if "detected_domain" in st.session_state and st.session_state["detected_domain"]:
        return st.session_state["detected_domain"]
    # Use project's detected_domain if set
    if project and project.detected_domain:
        st.session_state["detected_domain"] = project.detected_domain
        return project.detected_domain
    try:
        from domains.domain_registry import detect_domain
        cols = list(df.columns)
        sample = {c: df[c].dropna().astype(str).head(5).tolist() for c in cols[:20]}
        result = detect_domain(cols, sample)
        domain = result[0] if isinstance(result, (tuple, list)) else result
        st.session_state["detected_domain"] = domain or "generic"
    except Exception:
        st.session_state["detected_domain"] = "generic"
    return st.session_state["detected_domain"]


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def _page() -> None:
    st.set_page_config(page_title="AutoDS — Configure", layout="wide", page_icon="⚙️")
    inject_shared_css()

    # ---- auth gate ----
    if not auth_service.is_authenticated():
        st.switch_page("pages/00_login.py")
        st.stop()

    render_sidebar()

    # ---- project gate ----
    project = project_service.get_active()
    if project is None:
        project = project_service.create(name="My Analysis")
        project_service.set_active(project.id)
        project = project_service.get_active()

    # ---- data gate ----
    df = st.session_state.get("df")
    if df is None or (hasattr(df, "empty") and df.empty):
        st.info(
            "**Configure** — No dataset loaded yet. "
            "Upload data first, then return here to configure your analysis."
        )
        if st.button("← Back to Upload"):
            st.switch_page("pages/01_upload.py")
        st.stop()

    # ---- detect domain ----
    detected_domain = _get_detected_domain(df, project)

    # ---- initialise session state from project (first visit) ----
    st.session_state.setdefault("cf_selected_domain", project.confirmed_domain or detected_domain)
    st.session_state.setdefault("cf_mode", project.analysis_mode or "guided")
    detected_pt = _infer_problem_type(df, project, detected_domain)
    st.session_state.setdefault("cf_problem_type", project.problem_type or detected_pt)
    st.session_state.setdefault("cf_target", project.target_column or "")
    st.session_state.setdefault("cf_goal", project.goal or "")
    if project.excluded_columns:
        st.session_state.setdefault("cf_excluded", set(project.excluded_columns))

    # ---- breadcrumb ----
    st.markdown(
        f'<div class="cf-breadcrumb">'
        f'  {project.name}'
        f'  <span class="sep"> / </span>'
        f'  <span class="cur">Configure</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---- hero ----
    st.markdown(
        '<section class="cf-hero">'
        '  <div class="cf-hero-eyebrow">⚙ Step 2 of 7 — Configure</div>'
        '  <h1 class="cf-hero-title">Tell AutoDS how to <em>analyze your data.</em></h1>'
        '  <p class="cf-hero-sub">Confirm the detected domain, choose how much control you want, '
        '     pick a target — and we\'ll build the rest of the pipeline around your decisions.</p>'
        '</section>',
        unsafe_allow_html=True,
    )

    # ---- dataset recap strip ----
    n_rows, n_cols = df.shape
    dataset_name = st.session_state.get("dataset_name") or getattr(project, "dataset_name", "Dataset") or "Dataset"
    st.markdown(
        f'<div class="cf-recap-bar">'
        f'  <span class="cf-recap-item">📂 <b>{dataset_name}</b></span>'
        f'  <span class="cf-recap-sep"> · </span>'
        f'  <span class="cf-recap-item">{n_rows:,} rows</span>'
        f'  <span class="cf-recap-sep"> · </span>'
        f'  <span class="cf-recap-item">{n_cols} columns</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---- two-column layout: left content (1.0) + right sticky summary (0.42) ----
    left, right = st.columns([1.0, 0.42], gap="large")

    with left:

        # ===== Section 01 — Domain =====
        st.markdown(
            '<section class="cf-section">'
            '<div class="cf-sec-header">'
            '  <span class="cf-sec-num">01</span>'
            '  <h2 class="cf-sec-title">Confirm the <em>domain</em></h2>'
            '</div>'
            f'<p class="cf-sec-sub">We auto-detected this dataset as '
            f'<strong>{detected_domain.replace("_", " ").title()}</strong>. '
            f'Override if you disagree.</p>',
            unsafe_allow_html=True,
        )
        selected_domain = cf_domain_cards.render(
            detected_domain=detected_domain,
            on_select=lambda d: st.session_state.update({"cf_selected_domain": d}),
        )
        if not selected_domain:
            selected_domain = detected_domain
        cf_domain_why.render(selected_domain, df)
        cf_compliance_notice.render(selected_domain)
        st.markdown('</section>', unsafe_allow_html=True)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ===== Section 02 — Mode =====
        st.markdown(
            '<section class="cf-section">'
            '<div class="cf-sec-header">'
            '  <span class="cf-sec-num">02</span>'
            '  <h2 class="cf-sec-title">Pick your <em>analysis mode</em></h2>'
            '</div>'
            '<p class="cf-sec-sub">How much control do you want over the pipeline?</p>',
            unsafe_allow_html=True,
        )
        cf_mode_cards.render()
        cf_unsure_helper.render(columns=list(df.columns))
        st.markdown('</section>', unsafe_allow_html=True)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ===== Section 03 — Problem type =====
        current_pt = st.session_state.get("cf_problem_type", detected_pt)
        st.markdown(
            '<section class="cf-section">'
            '<div class="cf-sec-header">'
            '  <span class="cf-sec-num">03</span>'
            '  <h2 class="cf-sec-title">Confirm the <em>problem type</em></h2>'
            '</div>'
            '<p class="cf-sec-sub">We\'ve inferred this from your target column. Override if needed.</p>',
            unsafe_allow_html=True,
        )
        cf_problem_pills.render(detected_type=current_pt)
        st.markdown('</section>', unsafe_allow_html=True)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ===== Section 04 — Target & goal =====
        problem_type = st.session_state.get("cf_problem_type", detected_pt)
        st.markdown(
            '<section class="cf-section">'
            '<div class="cf-sec-header">'
            '  <span class="cf-sec-num">04</span>'
            '  <h2 class="cf-sec-title">Set <em>target &amp; goal</em></h2>'
            '</div>'
            '<p class="cf-sec-sub">Tell us what you want to predict and what success looks like.</p>',
            unsafe_allow_html=True,
        )
        cf_target_goal.render(
            columns=list(df.columns),
            domain_key=selected_domain,
            problem_type=problem_type,
        )
        st.markdown('</section>', unsafe_allow_html=True)

        st.markdown("<hr class='cf-divider'>", unsafe_allow_html=True)

        # ===== Section 05 — Excluded columns =====
        target = st.session_state.get("cf_target", "")
        st.markdown(
            '<section class="cf-section">'
            '<div class="cf-sec-header">'
            '  <span class="cf-sec-num">05</span>'
            '  <h2 class="cf-sec-title">Exclude <em>columns</em>'
            '    <span style="font-family:var(--font-body);font-size:14px;color:var(--text-muted);font-weight:400;font-style:normal;"> (optional)</span>'
            '  </h2>'
            '</div>'
            '<p class="cf-sec-sub">Skip columns that would leak the target, contain PII, or aren\'t useful.</p>',
            unsafe_allow_html=True,
        )
        cf_excluded_columns.render(df=df, target=target)
        st.markdown('</section>', unsafe_allow_html=True)

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
