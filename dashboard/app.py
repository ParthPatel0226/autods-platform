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
# Single CSS injection block
# ---------------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.main .block-container{padding-top:2rem;padding-bottom:3rem;max-width:1200px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0f172a 0%,#1e293b 100%);border-right:1px solid rgba(99,102,241,.18)}
[data-testid="stSidebar"] *{color:#cbd5e1!important}
[data-testid="stSidebar"] .stMarkdown p,[data-testid="stSidebar"] .stMarkdown span{color:#94a3b8!important;font-size:.72rem}
.autods-logo{display:flex;align-items:center;gap:10px;padding:.5rem 0 1.25rem;border-bottom:1px solid rgba(99,102,241,.2);margin-bottom:1.25rem}
.autods-logo-mark{width:36px;height:36px;background:linear-gradient(135deg,#6366f1,#0ea5e9);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;color:#fff!important;flex-shrink:0}
.autods-logo-name{font-size:1.05rem;font-weight:700;color:#f1f5f9!important;letter-spacing:-.3px}
.autods-logo-badge{display:inline-block;font-size:.6rem;font-weight:600;background:rgba(99,102,241,.25);border:1px solid rgba(99,102,241,.4);color:#a5b4fc!important;border-radius:4px;padding:1px 5px}
.mode-section-label,.stepper-label{font-size:.65rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#475569!important;margin-bottom:.55rem}
.mode-pills{display:flex;gap:5px;margin-bottom:1.25rem}
.mode-pill{flex:1;text-align:center;padding:5px 4px;border-radius:6px;font-size:.72rem;font-weight:500;border:1px solid rgba(99,102,241,.2);background:rgba(30,41,59,.6);color:#64748b!important}
.mode-pill.active{background:rgba(99,102,241,.2);border-color:#6366f1;color:#a5b4fc!important;font-weight:600}
.stepper-item{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:6px;margin-bottom:2px}
.stepper-item.is-current{background:rgba(99,102,241,.12);border-left:2px solid #6366f1;padding-left:6px}
.stepper-item.is-done{opacity:.75}
.step-icon{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.6rem;flex-shrink:0}
.step-icon.done{background:rgba(34,197,94,.18);border:1px solid rgba(34,197,94,.4);color:#22c55e!important}
.step-icon.current{background:rgba(99,102,241,.22);border:1px solid rgba(99,102,241,.5);color:#818cf8!important}
.step-icon.pending{background:rgba(51,65,85,.5);border:1px solid rgba(71,85,105,.4);color:#475569!important}
.step-label-text{font-size:.75rem;font-weight:500;flex:1}
.step-status-pill{font-size:.58rem;font-weight:600;padding:1px 6px;border-radius:10px}
.status-done{background:rgba(34,197,94,.12);color:#22c55e!important;border:1px solid rgba(34,197,94,.25)}
.status-active{background:rgba(99,102,241,.15);color:#818cf8!important;border:1px solid rgba(99,102,241,.3)}
.status-pending{background:rgba(51,65,85,.4);color:#475569!important;border:1px solid rgba(71,85,105,.25)}
[data-testid="stSidebar"] .stButton>button{background:transparent;border:1px solid rgba(99,102,241,.15);color:#94a3b8!important;font-size:.75rem;font-weight:500;border-radius:6px;padding:6px 10px;transition:all .15s ease;text-align:left}
[data-testid="stSidebar"] .stButton>button:hover:not(:disabled){background:rgba(99,102,241,.12);border-color:rgba(99,102,241,.4);color:#c7d2fe!important;transform:translateX(2px)}
[data-testid="stSidebar"] .stButton>button:disabled{opacity:.35}
.sidebar-progress-wrap{margin-top:1rem;padding-top:.9rem;border-top:1px solid rgba(99,102,241,.12)}
.sidebar-progress-label{display:flex;justify-content:space-between;font-size:.62rem;color:#475569!important;margin-bottom:5px}
.sidebar-progress-track{height:3px;background:rgba(51,65,85,.6);border-radius:3px;overflow:hidden}
.sidebar-progress-fill{height:100%;background:linear-gradient(90deg,#6366f1,#0ea5e9);border-radius:3px;transition:width .4s ease}
.hero-section{padding:3rem 0 2rem;text-align:center}
.hero-eyebrow{font-size:.75rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6366f1;margin-bottom:1rem}
.hero-title{font-size:clamp(2.4rem,5vw,3.6rem);font-weight:700;line-height:1.1;letter-spacing:-.03em;color:#0f172a;margin-bottom:1.1rem}
.hero-title .gradient-text{background:linear-gradient(135deg,#6366f1 0%,#0ea5e9 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:1.05rem;font-weight:400;color:#475569;max-width:580px;margin:0 auto 2.5rem;line-height:1.65}
.feature-card{background:rgba(248,250,252,.8);border:1px solid rgba(226,232,240,.9);border-radius:12px;padding:1.4rem 1.2rem;height:100%;transition:box-shadow .18s ease,transform .18s ease}
.feature-card:hover{box-shadow:0 8px 30px rgba(99,102,241,.1);transform:translateY(-2px)}
.feature-card-icon{font-size:1.6rem;margin-bottom:.75rem;display:block}
.feature-card-title{font-size:.9rem;font-weight:600;color:#1e293b;margin-bottom:.4rem}
.feature-card-body{font-size:.8rem;color:#64748b;line-height:1.55}
.upload-label{font-size:.9rem;font-weight:600;color:#334155;margin-bottom:.35rem}
.upload-hint{font-size:.75rem;color:#94a3b8;margin-bottom:1rem}
.stats-bar{display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;padding:1.5rem 0 .5rem;border-top:1px solid #e2e8f0;margin-top:2rem}
.stat-item{text-align:center}
.stat-value{font-size:1.35rem;font-weight:700;color:#6366f1;letter-spacing:-.02em;line-height:1.1}
.stat-label{font-size:.7rem;font-weight:500;color:#94a3b8;letter-spacing:.04em;text-transform:uppercase;margin-top:2px}
.sample-card{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:.6rem 1rem;margin:.25rem;font-size:.78rem;font-weight:500;color:#475569}
.sample-card-domain{font-size:.65rem;font-weight:500;color:#94a3b8;margin-left:4px}
.data-success-bar{display:flex;align-items:center;gap:10px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:8px;padding:.75rem 1rem;margin-bottom:1rem;font-size:.82rem;font-weight:500;color:#166534}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366f1,#4f46e5);border:none;color:#fff!important;font-weight:600;border-radius:8px;padding:.55rem 1.4rem;font-size:.85rem;box-shadow:0 2px 8px rgba(99,102,241,.35)}
hr{border:none;border-top:1px solid #e2e8f0;margin:1.5rem 0}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

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

_ICON = {"done": "&#10003;", "current": "&#9679;", "pending": "&#9675;"}


def _sidebar() -> None:
    """Render premium sidebar: logo, mode selector, workflow stepper, session controls."""
    with st.sidebar:
        st.markdown(
            f'<div class="autods-logo">'
            f'<div class="autods-logo-mark">AD</div>'
            f'<div><div class="autods-logo-name">AutoDS</div>'
            f'<span class="autods-logo-badge">v{PLATFORM_VERSION}</span></div></div>',
            unsafe_allow_html=True,
        )

        # Mode selector
        st.markdown('<div class="mode-section-label">Analysis Mode</div>', unsafe_allow_html=True)
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

        # Workflow stepper
        st.markdown('<div class="stepper-label">Workflow</div>', unsafe_allow_html=True)
        completed: list[str] = st.session_state.get("completed_steps", [])
        current_step: str = st.session_state.get("current_step", "upload")
        has_data = "uploaded_data" in st.session_state

        for step in _WORKFLOW_STEPS:
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

        # Session + progress
        st.markdown("<hr style='margin:.75rem 0'>", unsafe_allow_html=True)
        st.markdown('<div class="stepper-label">Session</div>', unsafe_allow_html=True)
        if st.button("New Session", key="new_session_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        pct = int(len(completed) / len(_WORKFLOW_STEPS) * 100)
        st.markdown(
            f'<div class="sidebar-progress-wrap">'
            f'<div class="sidebar-progress-label"><span>Progress</span>'
            f'<span>{len(completed)}/{len(_WORKFLOW_STEPS)} steps</span></div>'
            f'<div class="sidebar-progress-track">'
            f'<div class="sidebar-progress-fill" style="width:{pct}%"></div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


def _landing_page() -> None:
    """Premium landing page rendered when no dataset is loaded."""
    # Hero
    st.markdown(
        '<div class="hero-section">'
        '<div class="hero-eyebrow">Autonomous Data Science Platform</div>'
        '<h1 class="hero-title">From raw data to<br>'
        '<span class="gradient-text">production-ready models</span></h1>'
        '<p class="hero-sub">Upload any dataset. AutoDS detects your domain, generates '
        "analyst-level EDA, engineers features, trains models, and explains every "
        "decision — with full human-in-the-loop control at every step.</p></div>",
        unsafe_allow_html=True,
    )

    # Feature cards
    col1, col2, col3 = st.columns(3, gap="medium")
    _cards = [
        ("&#128202;", "Domain Intelligence",
         "Auto-detects Healthcare, Finance, E-commerce, Manufacturing, HR, and Marketing. "
         "Applies field-specific metrics, charts, and compliance checks out of the box."),
        ("&#129302;", "8 Collaborative Agents",
         "Profiler, EDA, Feature Engineer, Modeler, Explainability, Report, Deployment, "
         "and Chat agents work as a LangGraph state machine with a unified pipeline state."),
        ("&#128296;", "Full Pipeline Control",
         "Auto, Guided, or Expert mode. SHAP explanations, fairness audits, and model cards "
         "included. Export HTML reports, executive PDFs, Jupyter notebooks, and a serving API."),
    ]
    for col, (icon, title, body) in zip([col1, col2, col3], _cards):
        with col:
            st.markdown(
                f'<div class="feature-card"><span class="feature-card-icon">{icon}</span>'
                f'<div class="feature-card-title">{title}</div>'
                f'<div class="feature-card-body">{body}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # Upload zone
    st.markdown(
        '<div class="upload-label">Get started — drop your dataset</div>'
        '<div class="upload-hint">CSV, Excel, Parquet, JSON, TSV supported</div>',
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Upload dataset",
        type=["csv", "xlsx", "xls", "parquet", "json", "tsv"],
        help="Supported: CSV, Excel (.xlsx/.xls), Parquet, JSON, TSV.",
        key="landing_uploader",
        label_visibility="collapsed",
    )
    if uploaded_file is not None:
        _process_upload(uploaded_file)

    # Sample dataset tags
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="stepper-label" style="color:#94a3b8">Try a sample dataset</div>'
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

    # Stats bar
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
        f'<div class="data-success-bar">&#10003;&nbsp;'
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
