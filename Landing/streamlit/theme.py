"""
─────────────────────────────────────────────────────────────────────
AutoDS Streamlit Theme Module
─────────────────────────────────────────────────────────────────────
Drop this file in your project (e.g. as `theme.py`), then call
`apply_theme()` at the very top of your Streamlit app, right after
`st.set_page_config(...)`.

This makes your Streamlit app match the AutoDS landing page exactly:
  - Cosmic dark navy background with aurora gradients
  - Inter Tight + Instrument Serif + JetBrains Mono fonts
  - Glass-morphism cards
  - Violet/indigo gradient buttons & accents
  - Matching sidebar styling
─────────────────────────────────────────────────────────────────────
"""

import streamlit as st


def apply_theme():
    """Inject custom CSS to match the AutoDS landing page aesthetic."""
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">

<style>
/* ============================================================
   AUTODS — Cosmic Theme (matches landing page)
   ============================================================ */

:root {
  --bg: #07091A;
  --bg-1: #0B0F2A;
  --bg-2: #11173D;
  --bg-3: #1A2150;
  --surface: rgba(255, 255, 255, 0.04);
  --surface-2: rgba(255, 255, 255, 0.08);
  --border: rgba(255, 255, 255, 0.08);
  --border-2: rgba(255, 255, 255, 0.14);
  --ink: #F4F5FF;
  --ink-2: #C4C7E8;
  --ink-dim: #8B91C1;
  --ink-faint: #5B608A;
  --indigo: #6366F1;
  --violet: #8B5CF6;
  --purple: #A855F7;
  --pink: #EC4899;
  --cyan: #22D3EE;
  --green: #10B981;
  --amber: #F59E0B;
}

/* === Global app background — cosmic aurora === */
.stApp {
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(139, 92, 246, 0.25), transparent),
    radial-gradient(ellipse 60% 50% at 100% 30%, rgba(34, 211, 238, 0.12), transparent),
    radial-gradient(ellipse 60% 50% at 0% 60%, rgba(236, 72, 153, 0.12), transparent),
    var(--bg) !important;
  color: var(--ink) !important;
  font-family: 'Inter Tight', sans-serif !important;
}

/* === Subtle starfield === */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 20% 30%, white, transparent),
    radial-gradient(1px 1px at 60% 70%, white, transparent),
    radial-gradient(1px 1px at 50% 50%, rgba(255,255,255,0.6), transparent),
    radial-gradient(1px 1px at 80% 10%, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 90% 60%, white, transparent),
    radial-gradient(1px 1px at 33% 95%, rgba(255,255,255,0.7), transparent);
  background-size: 400px 400px;
  opacity: 0.3;
  pointer-events: none;
  z-index: 0;
}

/* === Make sure all content sits above the starfield === */
.main, .block-container, [data-testid="stSidebar"] {
  position: relative;
  z-index: 1;
}

/* === Typography === */
html, body, [class*="css"], .stMarkdown, .stText, p, span, div, li {
  font-family: 'Inter Tight', sans-serif !important;
  letter-spacing: -0.01em;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Instrument Serif', serif !important;
  font-weight: 400 !important;
  letter-spacing: -0.02em !important;
  color: var(--ink) !important;
}

/* Display gradient on h1 */
h1 {
  background: linear-gradient(135deg, #FFFFFF 0%, #C4B5FD 40%, #818CF8 70%, #22D3EE 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

code, pre, .stCode, [data-testid="stCodeBlock"] {
  font-family: 'JetBrains Mono', monospace !important;
}

/* === Sidebar — glass surface === */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(11, 15, 42, 0.95), rgba(7, 9, 26, 0.95)) !important;
  border-right: 1px solid var(--border) !important;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}

[data-testid="stSidebar"] > div {
  padding-top: 1rem;
}

/* Sidebar nav items — pills like the landing page tab nav */
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 12px !important;
  color: var(--ink-dim) !important;
  font-weight: 500 !important;
  text-align: left !important;
  padding: 10px 14px !important;
  margin-bottom: 4px !important;
  transition: all 0.2s !important;
  width: 100% !important;
}

[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15)) !important;
  border-color: rgba(139, 92, 246, 0.3) !important;
  color: var(--ink) !important;
  transform: translateX(2px) !important;
}

/* Active sidebar item */
[data-testid="stSidebar"] .stButton > button:focus,
[data-testid="stSidebar"] [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25)) !important;
  border-color: rgba(139, 92, 246, 0.5) !important;
  color: var(--ink) !important;
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.2) !important;
}

/* === Main content area === */
.main .block-container {
  padding-top: 2rem;
  padding-bottom: 4rem;
  max-width: 1280px;
}

/* === Buttons — gradient glow like landing page === */
.stButton > button[kind="primary"],
.stDownloadButton > button {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--violet) 50%, var(--purple) 100%) !important;
  color: white !important;
  border: none !important;
  border-radius: 999px !important;
  padding: 10px 24px !important;
  font-weight: 500 !important;
  font-family: 'Inter Tight', sans-serif !important;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.1) inset,
    0 8px 32px rgba(139, 92, 246, 0.4),
    0 4px 16px rgba(99, 102, 241, 0.3) !important;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stButton > button[kind="primary"]:hover,
.stDownloadButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.2) inset,
    0 12px 48px rgba(139, 92, 246, 0.6),
    0 8px 24px rgba(99, 102, 241, 0.5) !important;
}

/* Secondary buttons — glass */
.stButton > button {
  background: var(--surface) !important;
  color: var(--ink) !important;
  border: 1px solid var(--border-2) !important;
  border-radius: 999px !important;
  padding: 8px 20px !important;
  font-weight: 500 !important;
  font-family: 'Inter Tight', sans-serif !important;
  backdrop-filter: blur(24px);
  transition: all 0.2s !important;
}

.stButton > button:hover {
  background: var(--surface-2) !important;
  border-color: var(--violet) !important;
  transform: translateY(-1px) !important;
}

/* === Inputs === */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stDateInput input {
  background: var(--surface) !important;
  border: 1px solid var(--border-2) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
  font-family: 'Inter Tight', sans-serif !important;
  backdrop-filter: blur(12px);
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15) !important;
}

/* === File uploader — drop zone with violet dashed border === */
[data-testid="stFileUploader"] section {
  background: rgba(139, 92, 246, 0.05) !important;
  border: 2px dashed rgba(139, 92, 246, 0.4) !important;
  border-radius: 16px !important;
  padding: 2rem !important;
  transition: all 0.3s !important;
}

[data-testid="stFileUploader"] section:hover {
  background: rgba(139, 92, 246, 0.1) !important;
  border-color: rgba(139, 92, 246, 0.7) !important;
}

[data-testid="stFileUploader"] button {
  background: linear-gradient(135deg, var(--indigo), var(--violet)) !important;
  color: white !important;
  border-radius: 999px !important;
  border: none !important;
  padding: 8px 20px !important;
  font-weight: 500 !important;
}

/* === Metrics — glass cards === */
[data-testid="stMetric"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  padding: 1.25rem !important;
  backdrop-filter: blur(24px);
}

[data-testid="stMetricValue"] {
  font-family: 'Instrument Serif', serif !important;
  font-size: 2.5rem !important;
  background: linear-gradient(135deg, #FFFFFF 0%, #C4B5FD 40%, #818CF8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

[data-testid="stMetricLabel"] {
  font-family: 'JetBrains Mono', monospace !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  font-size: 0.75rem !important;
  color: var(--ink-faint) !important;
}

[data-testid="stMetricDelta"] {
  font-family: 'JetBrains Mono', monospace !important;
}

/* === Tabs === */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  padding: 6px !important;
  gap: 4px !important;
  backdrop-filter: blur(24px);
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--ink-dim) !important;
  border-radius: 12px !important;
  padding: 8px 16px !important;
  font-weight: 500 !important;
  font-family: 'Inter Tight', sans-serif !important;
  transition: all 0.2s !important;
}

[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25)) !important;
  color: var(--ink) !important;
  border: 1px solid rgba(139, 92, 246, 0.4) !important;
}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  display: none !important;
}

/* === Expanders === */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
  font-family: 'Inter Tight', sans-serif !important;
  font-weight: 500 !important;
}

[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  backdrop-filter: blur(24px);
}

/* === DataFrames & tables === */
[data-testid="stDataFrame"], .stTable {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  overflow: hidden;
  backdrop-filter: blur(24px);
}

[data-testid="stDataFrame"] table thead th {
  background: var(--bg-2) !important;
  color: var(--violet) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.75rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

/* === Alerts === */
.stAlert,
[data-testid="stNotification"] {
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
  backdrop-filter: blur(24px);
}

[data-testid="stNotification"][data-baseweb="notification"][kind="info"] {
  background: rgba(99, 102, 241, 0.12) !important;
  border-color: rgba(99, 102, 241, 0.3) !important;
}

[data-testid="stNotification"][kind="success"] {
  background: rgba(16, 185, 129, 0.12) !important;
  border-color: rgba(16, 185, 129, 0.3) !important;
}

[data-testid="stNotification"][kind="warning"] {
  background: rgba(245, 158, 11, 0.12) !important;
  border-color: rgba(245, 158, 11, 0.3) !important;
}

[data-testid="stNotification"][kind="error"] {
  background: rgba(236, 72, 153, 0.12) !important;
  border-color: rgba(236, 72, 153, 0.3) !important;
}

/* === Progress bars === */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--violet), var(--cyan)) !important;
  border-radius: 999px !important;
}

/* === Sliders === */
.stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--violet) !important;
  border: 2px solid var(--ink) !important;
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.3) !important;
}

/* === Code blocks === */
[data-testid="stCodeBlock"], pre, code {
  background: rgba(0, 0, 0, 0.4) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  font-family: 'JetBrains Mono', monospace !important;
}

/* === Plotly chart container === */
.js-plotly-plot {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  padding: 1rem !important;
}

/* === Captions & helper text === */
[data-testid="stCaptionContainer"], .caption {
  font-family: 'JetBrains Mono', monospace !important;
  color: var(--ink-faint) !important;
  font-size: 0.75rem !important;
  letter-spacing: 0.05em !important;
}

/* === Dividers === */
hr {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(90deg, transparent, var(--border-2), transparent) !important;
  margin: 2rem 0 !important;
}

/* === Hide Streamlit branding === */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
  background: transparent !important;
  height: 0 !important;
}

/* === Scrollbar === */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-1); }
::-webkit-scrollbar-thumb { background: var(--bg-3); border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: var(--violet); }

/* === "Back to Landing" link styling helper === */
.autods-back-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--surface);
  border: 1px solid var(--border-2);
  border-radius: 999px;
  color: var(--ink-2);
  text-decoration: none !important;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  backdrop-filter: blur(24px);
}

.autods-back-link:hover {
  background: var(--surface-2);
  border-color: var(--violet);
  color: var(--ink);
  transform: translateX(-2px);
}

/* === Section header — matches landing page === */
.autods-section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--violet);
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.autods-section-label::before {
  content: '✦';
}
</style>
        """,
        unsafe_allow_html=True,
    )


def back_to_landing(landing_url: str = "/"):
    """Render a 'Back to landing page' link in the sidebar or top of page."""
    st.markdown(
        f"""
        <a href="{landing_url}" class="autods-back-link" target="_self">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M11 7H3m0 0l4-4m-4 4l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Back to landing
        </a>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str):
    """Render a small uppercase mono label like the landing page section headers."""
    st.markdown(
        f'<div class="autods-section-label">{text}</div>',
        unsafe_allow_html=True,
    )
