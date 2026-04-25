"""AutoDS Platform -- Main Streamlit Application.

Entry point for the web dashboard.  Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED, PLATFORM_VERSION

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AutoDS -- Autonomous Data Science Platform",
    page_icon="DS",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Single CSS injection block -- dark luxury design system
# ---------------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* --- Keyframes --- */
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulseGlow{0%,100%{box-shadow:0 0 8px rgba(99,102,241,.15)}50%{box-shadow:0 0 20px rgba(99,102,241,.35)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes gradientShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes borderPulse{0%,100%{border-color:rgba(99,102,241,.2)}50%{border-color:rgba(99,102,241,.5)}}
@keyframes ringProgress{from{stroke-dashoffset:251.33}to{stroke-dashoffset:var(--ring-offset)}}
@keyframes meshMove{0%{transform:translate(0,0) scale(1)}33%{transform:translate(30px,-20px) scale(1.05)}66%{transform:translate(-20px,15px) scale(.97)}100%{transform:translate(0,0) scale(1)}}

@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:0.01ms!important;animation-iteration-count:1!important;transition-duration:0.01ms!important}
}

/* --- Base --- */
html,body,[class*="css"]{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  background:#0a0a0f!important;color:#f1f5f9!important;
}
.main .block-container{padding-top:2rem;padding-bottom:3rem;max-width:1200px}
.main{background:#0a0a0f!important}
[data-testid="stAppViewContainer"]{background:#0a0a0f!important}
[data-testid="stHeader"]{background:transparent!important}
hr{border:none;border-top:1px solid rgba(99,102,241,.12);margin:1.5rem 0}

/* --- Sidebar: frosted glass --- */
[data-testid="stSidebar"]{
  background:rgba(18,18,26,.85)!important;
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-right:1px solid rgba(99,102,241,.12);
}
[data-testid="stSidebar"] *{color:#cbd5e1!important}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span{color:#94a3b8!important;font-size:.72rem}

/* Logo */
.autods-logo{display:flex;align-items:center;gap:12px;padding:.5rem 0 1.25rem;border-bottom:1px solid rgba(99,102,241,.15);margin-bottom:1.25rem}
.autods-logo-mark{
  width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;
  background:linear-gradient(135deg,#6366f1,#0ea5e9);position:relative;overflow:hidden;
}
.autods-logo-mark svg{width:20px;height:20px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.autods-logo-name{font-size:1.05rem;font-weight:700;color:#f1f5f9!important;letter-spacing:-.3px}
.autods-logo-badge{
  display:inline-block;font-size:.6rem;font-weight:600;
  background:rgba(99,102,241,.2);border:1px solid rgba(99,102,241,.35);
  color:#a5b4fc!important;border-radius:4px;padding:1px 5px;
}

/* Mode pills with active indicator line */
.mode-section-label,.stepper-label{font-size:.65rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748b!important;margin-bottom:.55rem}
.mode-pills{display:flex;gap:6px;margin-bottom:1.25rem}
.mode-pill{
  flex:1;text-align:center;padding:6px 4px;border-radius:8px;font-size:.72rem;font-weight:500;
  border:1px solid rgba(99,102,241,.12);background:rgba(22,22,31,.6);color:#64748b!important;
  transition:all 150ms cubic-bezier(.4,0,.2,1);position:relative;cursor:default;
}
.mode-pill.active{
  background:rgba(99,102,241,.15);border-color:rgba(99,102,241,.4);color:#a5b4fc!important;font-weight:600;
}
.mode-pill.active::after{
  content:'';position:absolute;bottom:-1px;left:20%;right:20%;height:2px;
  background:linear-gradient(90deg,#6366f1,#0ea5e9);border-radius:2px;
}

/* Stepper with connecting lines */
.stepper-track{position:relative;padding-left:4px}
.stepper-item{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:8px;margin-bottom:0;position:relative;transition:background 150ms cubic-bezier(.4,0,.2,1)}
.stepper-item:hover{background:rgba(99,102,241,.06)}
.stepper-item.is-current{background:rgba(99,102,241,.1);border-left:2px solid #6366f1;padding-left:6px}
.stepper-item.is-done{opacity:.8}
.stepper-connector{width:1px;height:6px;background:rgba(99,102,241,.15);margin-left:17px}
.stepper-connector.done{background:rgba(34,197,94,.3)}
.step-icon{
  width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:.55rem;flex-shrink:0;transition:all 150ms cubic-bezier(.4,0,.2,1);
}
.step-icon.done{background:rgba(34,197,94,.15);border:1.5px solid rgba(34,197,94,.4);color:#22c55e!important}
.step-icon.current{background:rgba(99,102,241,.18);border:1.5px solid rgba(99,102,241,.5);color:#818cf8!important}
.step-icon.pending{background:rgba(51,65,85,.35);border:1.5px solid rgba(71,85,105,.3);color:#475569!important}
.step-label-text{font-size:.75rem;font-weight:500;flex:1}
.step-status-pill{font-size:.55rem;font-weight:600;padding:2px 7px;border-radius:10px}
.status-done{background:rgba(34,197,94,.1);color:#22c55e!important;border:1px solid rgba(34,197,94,.2)}
.status-active{background:rgba(99,102,241,.12);color:#818cf8!important;border:1px solid rgba(99,102,241,.25)}
.status-pending{background:rgba(51,65,85,.3);color:#475569!important;border:1px solid rgba(71,85,105,.2)}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton>button{
  background:transparent;border:1px solid rgba(99,102,241,.12);color:#94a3b8!important;
  font-size:.75rem;font-weight:500;border-radius:8px;padding:6px 10px;
  transition:all 150ms cubic-bezier(.4,0,.2,1);text-align:left;min-height:44px;
}
[data-testid="stSidebar"] .stButton>button:hover:not(:disabled){
  background:rgba(99,102,241,.1);border-color:rgba(99,102,241,.35);color:#c7d2fe!important;
  transform:translateX(2px);
}
[data-testid="stSidebar"] .stButton>button:focus-visible{outline:2px solid #6366f1;outline-offset:2px}
[data-testid="stSidebar"] .stButton>button:disabled{opacity:.3}

/* Progress ring */
.progress-ring-wrap{margin-top:1rem;padding-top:.9rem;border-top:1px solid rgba(99,102,241,.1);display:flex;align-items:center;gap:12px}
.progress-ring-wrap svg{flex-shrink:0}
.progress-ring-bg{stroke:rgba(51,65,85,.5);fill:none;stroke-width:4}
.progress-ring-fill{fill:none;stroke-width:4;stroke-linecap:round;stroke:url(#progressGrad);
  transform:rotate(-90deg);transform-origin:center;animation:ringProgress .8s ease-out forwards;
}
.progress-ring-text{font-size:.62rem;color:#64748b!important;line-height:1.5}
.progress-ring-text strong{color:#f1f5f9!important;font-size:.85rem;display:block;margin-bottom:1px}

/* --- Landing: animated gradient mesh background --- */
.hero-section{
  position:relative;padding:3.5rem 0 2.5rem;text-align:center;overflow:hidden;
  animation:fadeIn .6s ease-out;
}
.hero-mesh{
  position:absolute;inset:0;z-index:0;pointer-events:none;overflow:hidden;opacity:.35;
}
.hero-mesh-orb{position:absolute;border-radius:50%;filter:blur(80px)}
.hero-mesh-orb:nth-child(1){width:350px;height:350px;background:#6366f1;top:-80px;left:10%;animation:meshMove 12s ease-in-out infinite}
.hero-mesh-orb:nth-child(2){width:300px;height:300px;background:#0ea5e9;bottom:-60px;right:15%;animation:meshMove 15s ease-in-out infinite reverse}
.hero-mesh-orb:nth-child(3){width:250px;height:250px;background:#8b5cf6;top:30%;left:50%;animation:meshMove 18s ease-in-out infinite 2s}
.hero-content{position:relative;z-index:1}
.hero-eyebrow{
  font-size:.75rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  color:#6366f1;margin-bottom:1rem;animation:slideUp .5s ease-out;
}
.hero-title{
  font-size:clamp(2.4rem,5vw,3.6rem);font-weight:800;line-height:1.08;
  letter-spacing:-.03em;color:#f1f5f9;margin-bottom:1.1rem;animation:slideUp .5s ease-out .1s both;
}
.hero-title .gradient-text{
  background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#0ea5e9 100%);
  background-size:200% 200%;animation:gradientShift 6s ease infinite;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.hero-sub{
  font-size:1.05rem;font-weight:400;color:#94a3b8;max-width:580px;
  margin:0 auto 2.5rem;line-height:1.65;animation:slideUp .5s ease-out .2s both;
}

/* Feature cards: glassmorphism */
.feature-card{
  background:rgba(18,18,26,.65);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(99,102,241,.12);border-radius:16px;padding:1.5rem 1.25rem;
  height:100%;transition:all 300ms cubic-bezier(.4,0,.2,1);animation:slideUp .5s ease-out .3s both;
}
.feature-card:hover{
  box-shadow:0 4px 24px rgba(0,0,0,.25),0 0 20px rgba(99,102,241,.15);
  transform:translateY(-4px);border-color:rgba(99,102,241,.3);
}
.feature-card-icon{
  width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;
  margin-bottom:.75rem;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.2);
}
.feature-card-icon svg{width:20px;height:20px;stroke-width:1.5}
.feature-card-title{font-size:.9rem;font-weight:600;color:#f1f5f9;margin-bottom:.4rem}
.feature-card-body{font-size:.8rem;color:#94a3b8;line-height:1.6;max-width:75ch}

/* Upload zone */
.upload-label{font-size:.9rem;font-weight:600;color:#f1f5f9;margin-bottom:.35rem}
.upload-hint{font-size:.75rem;color:#64748b;margin-bottom:1rem}
.upload-zone-wrapper [data-testid="stFileUploader"]{
  border:2px dashed rgba(99,102,241,.25)!important;border-radius:16px!important;
  background:rgba(18,18,26,.5)!important;transition:all 300ms cubic-bezier(.4,0,.2,1);
  animation:borderPulse 3s ease-in-out infinite;
}
.upload-zone-wrapper [data-testid="stFileUploader"]:hover{
  border-color:rgba(99,102,241,.5)!important;box-shadow:0 0 20px rgba(99,102,241,.12);
}

/* Stats counter */
.stats-bar{
  display:flex;justify-content:center;gap:2.5rem;flex-wrap:wrap;padding:1.5rem 0 .5rem;
  border-top:1px solid rgba(99,102,241,.1);margin-top:2rem;animation:fadeIn .6s ease-out .5s both;
}
.stat-item{text-align:center}
.stat-value{
  font-size:1.35rem;font-weight:700;letter-spacing:-.02em;line-height:1.1;
  background:linear-gradient(135deg,#6366f1,#0ea5e9);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;background-clip:text;
}
.stat-label{font-size:.65rem;font-weight:500;color:#64748b;letter-spacing:.06em;text-transform:uppercase;margin-top:3px}

/* Sample dataset tags */
.sample-card{
  display:inline-flex;align-items:center;gap:4px;
  background:rgba(18,18,26,.6);backdrop-filter:blur(8px);
  border:1px solid rgba(99,102,241,.1);border-radius:8px;
  padding:.5rem .75rem;margin:.25rem;font-size:.75rem;font-weight:500;color:#94a3b8;
  transition:all 150ms cubic-bezier(.4,0,.2,1);
}
.sample-card:hover{border-color:rgba(99,102,241,.3);background:rgba(22,22,31,.8)}
.sample-card-domain{font-size:.6rem;font-weight:500;color:#64748b;margin-left:2px}

/* Data success bar */
.data-success-bar{
  display:flex;align-items:center;gap:10px;
  background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);
  border-radius:12px;padding:.75rem 1rem;margin-bottom:1rem;
  font-size:.82rem;font-weight:500;color:#22c55e;
}

/* Primary button */
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#6366f1,#4f46e5)!important;border:none;
  color:#fff!important;font-weight:600;border-radius:8px;padding:.55rem 1.4rem;
  font-size:.85rem;box-shadow:0 2px 12px rgba(99,102,241,.3);min-height:44px;
  transition:all 150ms cubic-bezier(.4,0,.2,1);
}
.stButton>button[kind="primary"]:hover{box-shadow:0 4px 20px rgba(99,102,241,.45);transform:translateY(-1px)}
.stButton>button[kind="primary"]:focus-visible{outline:2px solid #6366f1;outline-offset:2px}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SVG icons (no emojis)
# ---------------------------------------------------------------------------

_SVG_LOGO = (
    '<svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z"/>'
    '<path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>'
)

_SVG_CHART = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="12" width="4" height="9" rx="1"/>'
    '<rect x="10" y="7" width="4" height="14" rx="1"/>'
    '<rect x="17" y="3" width="4" height="18" rx="1"/></svg>'
)

_SVG_AGENTS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="8" r="4"/><path d="M5.5 21a6.5 6.5 0 0113 0"/>'
    '<circle cx="19" cy="5" r="2.5"/><circle cx="5" cy="5" r="2.5"/></svg>'
)

_SVG_CONTROLS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06'
    'a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09'
    'a1.65 1.65 0 00-1.08-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83'
    'l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09'
    'a1.65 1.65 0 001.51-1.08 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83'
    'l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09'
    'a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83'
    'l-.06.06a1.65 1.65 0 00-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 010 4'
    'h-.09a1.65 1.65 0 00-1.51 1z"/></svg>'
)

_ICON = {"done": "&#10003;", "current": "&#9679;", "pending": "&#9675;"}

# ---------------------------------------------------------------------------
# Workflow step definitions
# ---------------------------------------------------------------------------

_WORKFLOW_STEPS: list[dict[str, str]] = [
    {"key": "upload", "label": "Upload Data", "page": "pages/01_upload.py"},
    {"key": "configure", "label": "Configure", "page": "pages/02_configure.py"},
    {"key": "eda", "label": "EDA", "page": "pages/03_eda_interactive.py"},
    {"key": "feature_engineering", "label": "Features", "page": "pages/04_feature_engineering.py"},
    {"key": "modeling", "label": "Modeling", "page": "pages/05_modeling.py"},
    {"key": "explainability", "label": "Explain", "page": "pages/06_explainability.py"},
    {"key": "predict", "label": "Predict", "page": "pages/07_predict.py"},
    {"key": "followup", "label": "Chat", "page": "pages/08_chat.py"},
    {"key": "download", "label": "Download", "page": "pages/09_download.py"},
]


def _sidebar() -> None:
    """Render premium sidebar: logo, mode selector, workflow stepper, session controls."""
    with st.sidebar:
        # Logo with SVG icon
        st.markdown(
            f'<div class="autods-logo">'
            f'<div class="autods-logo-mark">{_SVG_LOGO}</div>'
            f'<div><div class="autods-logo-name">AutoDS</div>'
            f'<span class="autods-logo-badge">v{PLATFORM_VERSION}</span></div></div>',
            unsafe_allow_html=True,
        )

        # Mode selector
        st.markdown(
            '<div class="mode-section-label">Analysis Mode</div>',
            unsafe_allow_html=True,
        )
        mode_map = {MODE_AUTO: "Auto", MODE_GUIDED: "Guided", MODE_EXPERT: "Expert"}
        mode_keys, mode_labels = list(mode_map.keys()), list(mode_map.values())
        current_mode = st.session_state.get("user_mode", MODE_GUIDED)

        pills = "".join(
            f'<div class="mode-pill {"active" if k == current_mode else ""}">{v}</div>'
            for k, v in mode_map.items()
        )
        st.markdown(f'<div class="mode-pills">{pills}</div>', unsafe_allow_html=True)

        mode_idx = mode_keys.index(current_mode) if current_mode in mode_keys else 1
        selected = st.radio(
            "Mode",
            mode_labels,
            index=mode_idx,
            key="mode_radio",
            label_visibility="collapsed",
            help="Auto: system decides. Guided: system recommends. Expert: full control.",
        )
        st.session_state["user_mode"] = mode_keys[mode_labels.index(selected)]

        st.markdown("<hr style='margin:.75rem 0'>", unsafe_allow_html=True)

        # LLM provider selector
        from dashboard.components.llm_selector import render_llm_selector
        render_llm_selector()

        st.markdown("<hr style='margin:.75rem 0'>", unsafe_allow_html=True)

        # Workflow stepper with connecting lines
        st.markdown(
            '<div class="stepper-label">Workflow</div>',
            unsafe_allow_html=True,
        )
        completed: list[str] = st.session_state.get("completed_steps", [])
        current_step: str = st.session_state.get("current_step", "upload")
        has_data = "uploaded_data" in st.session_state

        st.markdown('<div class="stepper-track">', unsafe_allow_html=True)
        for i, step in enumerate(_WORKFLOW_STEPS):
            key, label = step["key"], step["label"]
            if key in completed:
                s, ic, pc, pt = "is-done", "done", "status-done", "Done"
            elif key == current_step:
                s, ic, pc, pt = "is-current", "current", "status-active", "Active"
            else:
                s, ic, pc, pt = "", "pending", "status-pending", "Pending"

            st.markdown(
                f'<div class="stepper-item {s}">'
                f'<div class="step-icon {ic}">{_ICON[ic]}</div>'
                f'<span class="step-label-text">{label}</span>'
                f'<span class="step-status-pill {pc}">{pt}</span></div>',
                unsafe_allow_html=True,
            )
            enabled = has_data or key == "upload"
            if st.button(label, key=f"nav_{key}", use_container_width=True, disabled=not enabled):
                st.switch_page(step["page"])

            # Connecting line between steps
            if i < len(_WORKFLOW_STEPS) - 1:
                conn_cls = "done" if key in completed else ""
                st.markdown(
                    f'<div class="stepper-connector {conn_cls}"></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

        # Session + progress ring
        st.markdown("<hr style='margin:.75rem 0'>", unsafe_allow_html=True)
        st.markdown(
            '<div class="stepper-label">Session</div>',
            unsafe_allow_html=True,
        )
        if st.button("New Session", key="new_session_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        pct = int(len(completed) / len(_WORKFLOW_STEPS) * 100)
        circumference = 2 * 3.14159 * 40
        offset = circumference - (pct / 100) * circumference
        st.markdown(
            f'<div class="progress-ring-wrap">'
            f'<svg width="56" height="56" viewBox="0 0 96 96">'
            f'<defs><linearGradient id="progressGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
            f'<stop offset="0%" stop-color="#6366f1"/>'
            f'<stop offset="100%" stop-color="#0ea5e9"/></linearGradient></defs>'
            f'<circle class="progress-ring-bg" cx="48" cy="48" r="40"/>'
            f'<circle class="progress-ring-fill" cx="48" cy="48" r="40" '
            f'stroke-dasharray="{circumference:.2f}" '
            f'style="--ring-offset:{offset:.2f};stroke-dashoffset:{circumference:.2f}"/>'
            f'<text x="48" y="52" text-anchor="middle" fill="#f1f5f9" '
            f'font-size="18" font-weight="700" font-family="Inter">{pct}%</text>'
            f'</svg>'
            f'<div class="progress-ring-text"><strong>{len(completed)}/{len(_WORKFLOW_STEPS)}</strong>'
            f'steps completed</div></div>',
            unsafe_allow_html=True,
        )


def _landing_page() -> None:
    """Premium landing page rendered when no dataset is loaded."""
    # Hero with animated gradient mesh
    st.markdown(
        '<div class="hero-section">'
        '<div class="hero-mesh">'
        '<div class="hero-mesh-orb"></div>'
        '<div class="hero-mesh-orb"></div>'
        '<div class="hero-mesh-orb"></div></div>'
        '<div class="hero-content">'
        '<div class="hero-eyebrow">Autonomous Data Science Platform</div>'
        '<h1 class="hero-title">From raw data to<br>'
        '<span class="gradient-text">production-ready models</span></h1>'
        '<p class="hero-sub">Upload any dataset. AutoDS detects your domain, generates '
        "analyst-level EDA, engineers features, trains models, and explains every "
        "decision -- with full human-in-the-loop control at every step.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Feature cards with glassmorphism
    col1, col2, col3 = st.columns(3, gap="medium")
    _cards = [
        (_SVG_CHART, "Domain Intelligence",
         "Auto-detects Healthcare, Finance, E-commerce, Manufacturing, HR, and Marketing. "
         "Applies field-specific metrics, charts, and compliance checks out of the box."),
        (_SVG_AGENTS, "8 Collaborative Agents",
         "Profiler, EDA, Feature Engineer, Modeler, Explainability, Report, Deployment, "
         "and Chat agents work as a LangGraph state machine with a unified pipeline state."),
        (_SVG_CONTROLS, "Full Pipeline Control",
         "Auto, Guided, or Expert mode. SHAP explanations, fairness audits, and model cards "
         "included. Export HTML reports, executive PDFs, Jupyter notebooks, and a serving API."),
    ]
    for col, (icon, title, body) in zip([col1, col2, col3], _cards):
        with col:
            st.markdown(
                f'<div class="feature-card">'
                f'<div class="feature-card-icon">{icon}</div>'
                f'<div class="feature-card-title">{title}</div>'
                f'<div class="feature-card-body">{body}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # Upload zone with animated dashed border
    st.markdown(
        '<div class="upload-label">Get started -- drop your dataset</div>'
        '<div class="upload-hint">CSV, Excel, Parquet, JSON, TSV supported</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="upload-zone-wrapper">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload dataset",
        type=["csv", "xlsx", "xls", "parquet", "json", "tsv"],
        help="Supported: CSV, Excel (.xlsx/.xls), Parquet, JSON, TSV.",
        key="landing_uploader",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if uploaded_file is not None:
        _process_upload(uploaded_file)

    # Sample dataset tags
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="stepper-label" style="color:#64748b">Try a sample dataset</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:4px">'
        '<span class="sample-card">Titanic<span class="sample-card-domain">Classification</span></span>'
        '<span class="sample-card">Heart Disease<span class="sample-card-domain">Healthcare</span></span>'
        '<span class="sample-card">Credit Risk<span class="sample-card-domain">Finance</span></span>'
        '<span class="sample-card">Online Retail<span class="sample-card-domain">E-commerce</span></span>'
        '<span class="sample-card">Employee Attrition<span class="sample-card-domain">HR</span></span>'
        '<span class="sample-card">Predictive Maint.<span class="sample-card-domain">Manufacturing</span></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Stats counter
    st.markdown(
        '<div class="stats-bar">'
        '<div class="stat-item"><div class="stat-value">7</div><div class="stat-label">Domains</div></div>'
        '<div class="stat-item"><div class="stat-value">25+</div><div class="stat-label">Chart Types</div></div>'
        '<div class="stat-item"><div class="stat-value">16</div><div class="stat-label">Statistical Tests</div></div>'
        '<div class="stat-item"><div class="stat-value">8</div><div class="stat-label">AI Agents</div></div>'
        '<div class="stat-item"><div class="stat-value">30+</div><div class="stat-label">Data Sources</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def _process_upload(uploaded_file: Any) -> None:
    """Process uploaded file into a DataFrame and persist to session state."""
    try:
        name = uploaded_file.name
        if name.endswith(".csv") or name.endswith(".tsv"):
            df = pd.read_csv(uploaded_file, sep="\t" if name.endswith(".tsv") else ",")
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        elif name.endswith(".parquet"):
            df = pd.read_parquet(uploaded_file)
        elif name.endswith(".json"):
            df = pd.read_json(uploaded_file)
        else:
            st.error(f"Unsupported format: {name}")
            return
    except Exception as exc:
        st.error(f"Failed to read file: {exc}")
        logger.exception("Upload processing failed for %s", uploaded_file.name)
        return

    st.session_state["uploaded_data"] = df
    st.session_state["row_count"] = len(df)
    st.session_state["column_count"] = len(df.columns)
    st.session_state["current_step"] = "configure"
    st.session_state["completed_steps"] = st.session_state.get("completed_steps", []) + ["upload"]

    st.markdown(
        f'<div class="data-success-bar">'
        f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" '
        f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        f'<polyline points="20 6 9 17 4 12"/></svg>&nbsp;'
        f"<strong>{name}</strong> loaded &mdash; {len(df):,} rows &times; {len(df.columns)} columns"
        "</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("Continue to Configuration", type="primary", key="continue_to_config_btn"):
        st.switch_page("pages/02_configure.py")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _sidebar()
    if "uploaded_data" not in st.session_state:
        _landing_page()
    else:
        current = st.session_state.get("current_step", "upload")
        step_map = {s["key"]: s["page"] for s in _WORKFLOW_STEPS}
        page = step_map.get(current)
        if page:
            st.switch_page(page)
        else:
            _landing_page()


main()
