"""AutoDS Platform -- Main Streamlit Application.

Entry point for the web dashboard.  Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so auth.py / db.py are importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED, PLATFORM_VERSION
from dashboard.components.shared_css import inject_shared_css, render_theme_toggle, section_label

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AutoDS — Autonomous Data Science",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "AutoDS — Autonomous Data Science Platform v1.0.0",
    },
)

# ---------------------------------------------------------------------------
# Auth gate — blocks here if not logged in
# ---------------------------------------------------------------------------
from auth import require_auth, logout as auth_logout
from db import get_current_user

user = require_auth()

# ---------------------------------------------------------------------------
# Inject shared design-token CSS first, then page-specific overrides
# ---------------------------------------------------------------------------
inject_shared_css()

# ---------------------------------------------------------------------------
# Page-specific CSS -- cosmic landing page aesthetic
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* --- Keyframes --- */
@keyframes slideUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes gradientShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes borderPulse{0%,100%{border-color:var(--border-active)}50%{border-color:var(--violet)}}
@keyframes ringProgress{from{stroke-dashoffset:251.33}to{stroke-dashoffset:var(--ring-offset)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes pulse-ring-glow{0%{transform:scale(1);opacity:0.6}100%{transform:scale(2.5);opacity:0}}

/* --- Layout --- */
.main .block-container{padding-top:1rem;padding-bottom:3rem;max-width:1200px;margin-left:auto;margin-right:auto}
.main .block-container [data-testid="stVerticalBlock"]{width:100%}
.main .block-container [data-testid="element-container"]{width:100%!important}
.main .block-container [data-testid="stMarkdown"]{width:100%}

/* --- Sidebar chrome --- */
[data-testid="stSidebar"] *{color:var(--text-secondary)!important}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span{color:var(--text-muted)!important;font-size:var(--text-xs)}

/* Logo */
.autods-logo{display:flex;align-items:center;gap:12px;padding:.5rem 0 1.25rem;border-bottom:1px solid var(--border-subtle);margin-bottom:1.25rem}
.autods-logo-mark{
  width:36px;height:36px;border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;flex-shrink:0;
  background:linear-gradient(135deg, var(--indigo), var(--purple));position:relative;overflow:hidden;
  box-shadow:0 4px 12px rgba(139,92,246,0.4);
}
.autods-logo-mark svg{width:20px;height:20px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.autods-logo-name{font-family:var(--font-body);font-size:1.05rem;font-weight:700;color:var(--text-primary)!important;letter-spacing:-.3px}
.autods-logo-badge{
  display:inline-flex;align-items:center;gap:5px;
  font-size:.58rem;font-weight:600;
  background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.25);
  color:var(--violet)!important;border-radius:var(--radius-full);padding:2px 8px;
}
.autods-logo-badge .status-pulse{
  position:relative;display:inline-flex;width:6px;height:6px;
}
.autods-logo-badge .status-pulse::before{
  content:'';position:absolute;inset:0;border-radius:50%;
  background:var(--green);animation:pulse-ring-glow 2s ease-out infinite;
}
.autods-logo-badge .status-pulse::after{
  content:'';position:absolute;inset:0;border-radius:50%;background:var(--green);
}

/* Mode pills */
.mode-section-label,.stepper-label{font-size:var(--text-xs);font-weight:600;letter-spacing:var(--tracking-wide);text-transform:uppercase;color:var(--text-muted)!important;margin-bottom:.55rem}
.mode-pills{display:flex;gap:6px;margin-bottom:1.25rem}
.mode-pill{
  flex:1;text-align:center;padding:6px 4px;border-radius:var(--radius-lg);font-size:var(--text-xs);font-weight:500;
  border:1px solid var(--border-subtle);background:rgba(255,255,255,0.04);color:var(--text-muted)!important;
  transition:var(--transition-all);position:relative;cursor:default;
}
.mode-pill.active{
  background:linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25));
  border-color:rgba(139,92,246,0.5);color:var(--text-primary)!important;font-weight:600;
  box-shadow:0 4px 20px rgba(139,92,246,0.2);
}

/* Sidebar nav — pill style matching landing page */
[data-testid="stSidebar"] .stButton>button{
  background:transparent!important;border:1px solid transparent!important;color:var(--text-muted)!important;
  font-size:var(--text-xs);font-weight:500;border-radius:var(--radius-lg)!important;padding:10px 14px!important;
  margin-bottom:4px!important;transition:all 0.2s!important;text-align:left;min-height:40px;width:100%!important;
}
[data-testid="stSidebar"] .stButton>button:hover:not(:disabled){
  background:linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15))!important;
  border-color:rgba(139,92,246,0.3)!important;color:var(--text-primary)!important;
  transform:translateX(2px)!important;
}
[data-testid="stSidebar"] .stButton>button:focus{
  background:linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25))!important;
  border-color:rgba(139,92,246,0.5)!important;color:var(--text-primary)!important;
  box-shadow:0 4px 20px rgba(139,92,246,0.2)!important;
}
[data-testid="stSidebar"] .stButton>button:disabled{opacity:.3}

/* Stepper */
.stepper-track{position:relative;padding-left:4px}
.stepper-item{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:var(--radius-lg);margin-bottom:0;position:relative;transition:background var(--duration-fast) var(--ease-in-out)}
.stepper-item:hover{background:rgba(139,92,246,0.08)}
.stepper-item.is-current{background:linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15));border-left:2px solid var(--violet);padding-left:6px}
.stepper-item.is-done{opacity:.8}
.stepper-connector{width:1px;height:6px;background:var(--border-subtle);margin-left:17px}
.stepper-connector.done{background:rgba(16,185,129,0.3)}
.step-icon{
  width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:.55rem;flex-shrink:0;transition:var(--transition-all);
}
.step-icon.done{background:rgba(16,185,129,0.15);border:1.5px solid var(--green);color:var(--green)!important}
.step-icon.current{background:rgba(139,92,246,0.15);border:1.5px solid var(--violet);color:var(--violet)!important}
.step-icon.pending{background:rgba(255,255,255,0.04);border:1.5px solid var(--border-default);color:var(--text-muted)!important}
.step-label-text{font-size:var(--text-xs);font-weight:500;flex:1}
.step-status-pill{font-size:.55rem;font-weight:600;padding:2px 7px;border-radius:var(--radius-full)}
.status-done{background:rgba(16,185,129,0.12);color:var(--green)!important;border:1px solid rgba(16,185,129,0.3)}
.status-active{background:rgba(139,92,246,0.12);color:var(--violet)!important;border:1px solid rgba(139,92,246,0.3)}
.status-pending{background:rgba(255,255,255,0.04);color:var(--text-muted)!important;border:1px solid var(--border-subtle)}

/* Progress ring */
.progress-ring-wrap{margin-top:1rem;padding-top:.9rem;border-top:1px solid var(--border-subtle);display:flex;align-items:center;gap:12px}
.progress-ring-wrap svg{flex-shrink:0}
.progress-ring-bg{stroke:var(--text-muted);opacity:.15;fill:none;stroke-width:4}
.progress-ring-fill{fill:none;stroke-width:4;stroke-linecap:round;stroke:url(#progressGrad);
  transform:rotate(-90deg);transform-origin:center;animation:ringProgress .8s var(--ease-out) forwards;
}
.progress-ring-text{font-size:var(--text-xs);color:var(--text-muted)!important;line-height:1.5}
.progress-ring-text strong{font-family:var(--font-body);font-weight:700;color:var(--text-primary)!important;font-size:var(--text-sm);display:block;margin-bottom:1px}

/* ============================================================
   LANDING PAGE — Cosmic aesthetic matching landing/index.html
   ============================================================ */

/* Hero section — full cosmic background */
.hero-cosmic{
  position:relative;
  padding:4rem 2rem 3.5rem;
  margin-bottom:2rem;
  text-align:center;
  overflow:hidden;
  animation:fadeIn .6s var(--ease-out);
}

/* Status chip */
.hero-chip{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(255,255,255,0.04);backdrop-filter:blur(24px);
  border:1px solid var(--border-subtle);
  border-radius:var(--radius-full);padding:6px 16px 6px 12px;
  font-family:var(--font-mono);font-size:.7rem;font-weight:500;
  color:var(--text-secondary)!important;margin-bottom:1.5rem;
  animation:slideUp .5s var(--ease-out);
}
.hero-chip .pulse{
  position:relative;display:inline-flex;width:8px;height:8px;
}
.hero-chip .pulse::before{
  content:'';position:absolute;inset:0;border-radius:50%;
  background:var(--green);animation:pulse-ring-glow 2s ease-out infinite;
}
.hero-chip .pulse::after{
  content:'';position:absolute;inset:0;border-radius:50%;background:var(--green);
}

/* Hero headline — Instrument Serif */
.hero-title{
  font-family:var(--font-display);font-size:clamp(2.8rem,7vw,5rem);font-weight:400;
  line-height:0.95;letter-spacing:-.03em;
  color:var(--text-primary)!important;margin-bottom:1.25rem;
  animation:slideUp .5s var(--ease-out) .08s both;
}
.hero-title .glow{
  background:var(--gradient-text);background-size:200% 200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  font-style:italic;
}

/* Hero description */
.hero-desc{
  font-family:var(--font-body);font-size:1.05rem;font-weight:400;
  color:var(--text-muted)!important;max-width:580px;margin:0 auto 2rem;
  line-height:1.7;animation:slideUp .5s var(--ease-out) .15s both;
}

/* Floating stat pills */
.hero-stats{
  display:flex;justify-content:center;gap:10px;flex-wrap:wrap;
  animation:slideUp .5s var(--ease-out) .22s both;margin-bottom:1.5rem;
}
.hero-stat{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,0.04);backdrop-filter:blur(12px);
  border:1px solid var(--border-subtle);border-radius:var(--radius-full);
  padding:7px 16px;transition:var(--transition-all);
}
.hero-stat:hover{border-color:rgba(139,92,246,0.3);box-shadow:0 0 20px rgba(139,92,246,0.15)}
.hero-stat-val{font-family:var(--font-body);font-weight:700;font-size:.9rem;color:var(--text-primary)!important}
.hero-stat-label{font-size:.7rem;font-weight:500;color:var(--text-muted)!important}

/* --- Bento feature grid --- */
.bento-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
  margin-bottom:2rem;animation:slideUp .5s var(--ease-out) .3s both;
}
.bento-card{
  position:relative;
  background:var(--bg-card);backdrop-filter:blur(24px);
  border:1px solid var(--border-subtle);border-radius:var(--radius-xl);
  padding:1.5rem 1.25rem 1.25rem;transition:var(--transition-all);overflow:hidden;
}
.bento-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  border-radius:var(--radius-xl) var(--radius-xl) 0 0;
  opacity:0;transition:opacity var(--duration-normal) var(--ease-in-out);
}
.bento-card:hover{
  border-color:rgba(139,92,246,0.3);
  box-shadow:0 0 40px -8px rgba(139,92,246,0.25);
  transform:translateY(-2px);
}
.bento-card:hover::before{opacity:1}
.bento-card:nth-child(1)::before{background:linear-gradient(90deg, var(--indigo), var(--cyan))}
.bento-card:nth-child(2)::before{background:linear-gradient(90deg, var(--violet), var(--pink))}
.bento-card:nth-child(3)::before{background:linear-gradient(90deg, var(--purple), var(--cyan))}

/* Card sheen on hover */
.bento-card::after{
  content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.03),transparent);
  transition:left 0.7s;pointer-events:none;
}
.bento-card:hover::after{left:100%}

.bento-icon{
  width:48px;height:48px;border-radius:var(--radius-lg);
  display:flex;align-items:center;justify-content:center;margin-bottom:.85rem;
}
.bento-icon svg{width:24px;height:24px;stroke-width:1.5;position:relative;z-index:1}
.bento-icon-1{background:linear-gradient(135deg, rgba(99,102,241,0.2), rgba(34,211,238,0.15))}
.bento-icon-2{background:linear-gradient(135deg, rgba(139,92,246,0.2), rgba(236,72,153,0.15))}
.bento-icon-3{background:linear-gradient(135deg, rgba(168,85,247,0.2), rgba(34,211,238,0.15))}

.bento-title{font-family:var(--font-body);font-size:.95rem;font-weight:650;color:var(--text-primary);margin-bottom:.35rem;letter-spacing:-.01em}
.bento-body{font-size:var(--text-sm);color:var(--text-secondary);line-height:1.65}
.bento-tag{
  display:inline-flex;align-items:center;gap:4px;margin-top:.65rem;
  font-family:var(--font-mono);font-size:.6rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;
  color:var(--violet);background:rgba(139,92,246,0.1);
  border-radius:var(--radius-full);padding:3px 10px;
}

/* --- Upload section --- */
.upload-section-title{
  font-family:var(--font-display);font-size:1.4rem;font-weight:400;
  color:var(--text-primary);margin-bottom:.35rem;letter-spacing:-.02em;
  text-align:center;animation:slideUp .5s var(--ease-out) .35s both;
}
.upload-section-hint{
  font-size:var(--text-sm);color:var(--text-muted);margin-bottom:.75rem;text-align:center;
}
.upload-section-hint span{
  display:inline-flex;align-items:center;gap:3px;
  background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);
  border-radius:var(--radius-full);padding:2px 8px;
  font-family:var(--font-mono);font-size:.68rem;color:var(--text-secondary);margin:0 1px;
}

/* File uploader centering */
[data-testid="stFileUploader"]{max-width:560px;margin:0 auto}

/* --- Sample datasets --- */
.samples-row{
  display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:6px;
  margin-top:1.5rem;padding-top:1.25rem;border-top:1px solid var(--border-subtle);
}
.samples-label{
  font-family:var(--font-mono);font-size:.62rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--text-muted);margin-right:4px;
}
.sample-chip{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(255,255,255,0.04);backdrop-filter:blur(12px);
  border:1px solid var(--border-subtle);border-radius:var(--radius-full);
  padding:5px 14px 5px 10px;font-size:.72rem;font-weight:500;color:var(--text-secondary);
  transition:var(--transition-all);cursor:default;
}
.sample-chip:hover{
  border-color:rgba(139,92,246,0.3);background:rgba(139,92,246,0.08);
  box-shadow:0 0 20px rgba(139,92,246,0.12);transform:translateY(-1px);
}
.sample-chip-icon{font-size:.7rem;opacity:.6}
.sample-chip-domain{font-family:var(--font-mono);font-size:.58rem;color:var(--text-muted);font-weight:500}

/* --- Stats strip --- */
.stats-strip{
  display:grid;grid-template-columns:repeat(5,1fr);gap:8px;
  margin-top:2rem;animation:slideUp .5s var(--ease-out) .4s both;
}
.stat-cell{
  background:var(--bg-card);backdrop-filter:blur(24px);
  border:1px solid var(--border-subtle);border-radius:var(--radius-xl);
  padding:1rem .75rem;text-align:center;transition:var(--transition-all);
}
.stat-cell:hover{border-color:rgba(139,92,246,0.3);box-shadow:0 0 30px -8px rgba(139,92,246,0.2)}
.stat-val{
  font-family:var(--font-body);font-size:1.4rem;font-weight:800;
  letter-spacing:-.02em;line-height:1;
  background:var(--gradient-text);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.stat-lbl{
  font-family:var(--font-mono);font-size:.55rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;
  color:var(--text-muted);margin-top:5px;
}

/* Data success bar */
.data-success-bar{
  display:flex;align-items:center;gap:10px;
  background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);
  border-radius:var(--radius-xl);padding:.75rem 1rem;margin-bottom:1rem;
  font-size:var(--text-sm);font-weight:500;color:var(--green);
  backdrop-filter:blur(24px);
}

/* Logo marquee */
@keyframes marquee-scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.marquee-wrap{
  overflow:hidden;padding:1.5rem 0;margin-bottom:2rem;
  border-top:1px solid var(--border-subtle);border-bottom:1px solid var(--border-subtle);
  background:rgba(255,255,255,0.02);
}
.marquee-label{
  text-align:center;margin-bottom:1rem;
  font-family:var(--font-mono);font-size:.65rem;letter-spacing:.15em;
  text-transform:uppercase;color:var(--text-muted);
}
.marquee-track{
  display:flex;width:max-content;
  animation:marquee-scroll 50s linear infinite;
}
.marquee-item{
  padding:0 1.5rem;white-space:nowrap;font-family:var(--font-body);
  font-size:1rem;font-weight:500;color:var(--text-muted);
}
.marquee-dot{
  padding:0 1.5rem;font-family:var(--font-mono);font-size:1rem;color:var(--violet);
}

/* Centering overrides */
.main [data-testid="stVerticalBlock"],
.main [data-testid="element-container"],
.main [data-testid="stMarkdown"],
.main .stMarkdown{width:100%!important;max-width:100%!important}
.main [data-testid="stFileUploader"]{max-width:560px!important;margin-left:auto!important;margin-right:auto!important}
.main [data-testid="stFileUploaderDropzone"]{margin-left:auto!important;margin-right:auto!important}
.hero-cosmic,.hero-chip,.hero-title,.hero-desc,.hero-stats,.upload-section-title,.upload-section-hint,.samples-row,.stats-strip,.stat-cell{text-align:center}
.hero-chip{margin-left:auto;margin-right:auto;display:inline-flex}
.hero-desc{margin-left:auto;margin-right:auto}

/* --- Responsive --- */
@media(max-width:768px){
  .bento-grid{grid-template-columns:1fr}
  .stats-strip{grid-template-columns:repeat(3,1fr)}
  .hero-cosmic{padding:2.5rem 1rem 2rem}
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SVG icons
# ---------------------------------------------------------------------------

_SVG_LOGO = (
    '<svg viewBox="0 0 16 16" fill="none">'
    '<path d="M2 8 L6 4 L10 8 L14 4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M2 12 L6 8 L10 12 L14 8" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
    '</svg>'
)

_SVG_CHART = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="var(--indigo)" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="12" width="4" height="9" rx="1"/>'
    '<rect x="10" y="7" width="4" height="14" rx="1"/>'
    '<rect x="17" y="3" width="4" height="18" rx="1"/></svg>'
)

_SVG_AGENTS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="8" r="4"/><path d="M5.5 21a6.5 6.5 0 0113 0"/>'
    '<circle cx="19" cy="5" r="2.5"/><circle cx="5" cy="5" r="2.5"/></svg>'
)

_SVG_CONTROLS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="1.5" '
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
        # Logged-in user info + logout
        st.write(f"👤 {user.email}")
        if st.button("Logout", key="logout_btn"):
            auth_logout()
            st.rerun()
        st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)

        # Theme toggle (top of sidebar)
        render_theme_toggle()
        st.markdown("<hr style='margin:.5rem 0'>", unsafe_allow_html=True)

        # Logo with matching landing page design
        st.markdown(
            f'<div class="autods-logo">'
            f'<div class="autods-logo-mark">{_SVG_LOGO}</div>'
            f'<div><div class="autods-logo-name">AutoDS</div>'
            f'<span class="autods-logo-badge">'
            f'<span class="status-pulse"></span>v{PLATFORM_VERSION} &middot; 8 agents</span>'
            f'</div></div>',
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

        # Workflow stepper
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
            f'<stop offset="0%" stop-color="#6366F1"/>'
            f'<stop offset="100%" stop-color="#22D3EE"/></linearGradient></defs>'
            f'<circle class="progress-ring-bg" cx="48" cy="48" r="40"/>'
            f'<circle class="progress-ring-fill" cx="48" cy="48" r="40" '
            f'stroke-dasharray="{circumference:.2f}" '
            f'style="--ring-offset:{offset:.2f};stroke-dashoffset:{circumference:.2f}"/>'
            f'<text x="48" y="52" text-anchor="middle" fill="var(--text-primary)" '
            f'font-size="18" font-weight="700" font-family="Inter Tight">{pct}%</text>'
            f'</svg>'
            f'<div class="progress-ring-text"><strong>{len(completed)}/{len(_WORKFLOW_STEPS)}</strong>'
            f'steps completed</div></div>',
            unsafe_allow_html=True,
        )


def _landing_page() -> None:
    """Cosmic landing page rendered when no dataset is loaded."""
    # ── Hero section ──
    st.markdown(
        '<div class="hero-cosmic">'
        #  Status chip with pulse
        '<div class="hero-chip">'
        '<span class="pulse"></span>'
        'v1.0.0 &middot; 8 AI Agents &middot; Production Ready'
        '&nbsp;&nbsp;<span style="color:var(--text-muted)">&rarr;</span></div>'
        #  Title (Instrument Serif)
        '<h1 class="hero-title">From raw data<br>'
        '<span class="glow">to production models.</span></h1>'
        #  Description
        '<p class="hero-desc">Upload any dataset. AutoDS auto-detects your domain, '
        "runs analyst-level EDA, engineers features, trains &amp; explains models "
        "&mdash; with full control at every step.</p>"
        #  Floating stat pills
        '<div class="hero-stats">'
        '<div class="hero-stat"><span class="hero-stat-val" style="color:var(--violet)">7</span>'
        '<span class="hero-stat-label">Domains</span></div>'
        '<div class="hero-stat"><span class="hero-stat-val" style="color:var(--purple)">8</span>'
        '<span class="hero-stat-label">AI Agents</span></div>'
        '<div class="hero-stat"><span class="hero-stat-val" style="color:var(--cyan)">30+</span>'
        '<span class="hero-stat-label">Data Sources</span></div>'
        '<div class="hero-stat"><span class="hero-stat-val" style="color:var(--pink)">25+</span>'
        '<span class="hero-stat-label">Chart Types</span></div>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Logo marquee (tech stack) ──
    items = ['LangGraph', 'XGBoost', 'SHAP', 'DuckDB', 'FastAPI', 'Streamlit',
             'MLflow', 'ChromaDB', 'Plotly', 'Claude', 'scikit-learn']
    marquee_items = ""
    for item in (items + items):  # duplicate for seamless scroll
        marquee_items += f'<span class="marquee-item">{item}</span><span class="marquee-dot">&#10022;</span>'
    st.markdown(
        '<div class="marquee-wrap">'
        '<div class="marquee-label">Built with production-grade tooling</div>'
        f'<div class="marquee-track">{marquee_items}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Bento feature cards ──
    st.markdown(
        '<div class="bento-grid">'
        #  Card 1 — Domain Intelligence
        '<div class="bento-card">'
        f'<div class="bento-icon bento-icon-1">{_SVG_CHART}</div>'
        '<div class="bento-title">Domain Intelligence</div>'
        '<div class="bento-body">Auto-detects Healthcare, Finance, E-commerce, '
        "Manufacturing, HR &amp; Marketing. Applies domain metrics, "
        "compliance checks, and field-specific charts.</div>"
        '<span class="bento-tag">&#10022; 6 domains + generic</span></div>'
        #  Card 2 — 8 Agents
        '<div class="bento-card">'
        f'<div class="bento-icon bento-icon-2">{_SVG_AGENTS}</div>'
        '<div class="bento-title">8 Collaborative Agents</div>'
        '<div class="bento-body">Profiler, EDA, Feature Engineer, Modeler, '
        "Explainability, Report, Deployment &amp; Chat agents orchestrated "
        "via LangGraph state machine.</div>"
        '<span class="bento-tag">&#10022; langgraph pipeline</span></div>'
        #  Card 3 — Pipeline Control
        '<div class="bento-card">'
        f'<div class="bento-icon bento-icon-3">{_SVG_CONTROLS}</div>'
        '<div class="bento-title">Full Pipeline Control</div>'
        '<div class="bento-body">Auto, Guided, or Expert mode. SHAP explanations, '
        "fairness audits, model cards. Export HTML, PDF, notebooks "
        "&amp; a FastAPI serving endpoint.</div>"
        '<span class="bento-tag">&#10022; human-in-the-loop</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Upload section ──
    st.markdown(
        '<div class="upload-section-title">Drop your dataset to begin</div>'
        '<div class="upload-section-hint">'
        "Supports "
        "<span>CSV</span> <span>Excel</span> <span>Parquet</span> "
        "<span>JSON</span> <span>TSV</span>"
        "</div>",
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

    # Sample dataset chips
    st.markdown(
        '<div class="samples-row">'
        '<span class="samples-label">Or try:</span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#10022;</span>Titanic'
        '<span class="sample-chip-domain">Classification</span></span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#9829;</span>Heart Disease'
        '<span class="sample-chip-domain">Healthcare</span></span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#9830;</span>Credit Risk'
        '<span class="sample-chip-domain">Finance</span></span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#9827;</span>Online Retail'
        '<span class="sample-chip-domain">E-commerce</span></span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#9679;</span>Attrition'
        '<span class="sample-chip-domain">HR</span></span>'
        '<span class="sample-chip"><span class="sample-chip-icon">&#9881;</span>Pred. Maint.'
        '<span class="sample-chip-domain">Manufacturing</span></span>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Stats strip ──
    st.markdown(
        '<div class="stats-strip">'
        '<div class="stat-cell"><div class="stat-val">7</div><div class="stat-lbl">Domains</div></div>'
        '<div class="stat-cell"><div class="stat-val">25+</div><div class="stat-lbl">Charts</div></div>'
        '<div class="stat-cell"><div class="stat-val">16</div><div class="stat-lbl">Stat Tests</div></div>'
        '<div class="stat-cell"><div class="stat-val">8</div><div class="stat-lbl">AI Agents</div></div>'
        '<div class="stat-cell"><div class="stat-val">30+</div><div class="stat-lbl">Sources</div></div>'
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
        f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" '
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
