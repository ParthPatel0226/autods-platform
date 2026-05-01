"""Shared CSS design tokens and base styles for all dashboard pages.

Every page should call ``inject_shared_css()`` instead of defining its own
``:root`` / background / sidebar overrides.  Page-specific styles are still
allowed **after** the shared injection.

Supports a dual-theme system: dark (default, cosmic) and light mode.  The
active theme's values are injected directly into ``:root`` so every
``var(--xxx)`` reference works without JS hacks.  The toggle button lives
in the sidebar (rendered by ``app.py``), not in pages.

Design aesthetic matches the AutoDS landing page:
  - Cosmic dark navy background with aurora gradients
  - Inter Tight + Instrument Serif + JetBrains Mono fonts
  - Glass-morphism cards with backdrop blur
  - Violet/indigo gradient buttons & accents
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Theme palettes  (matches landing page index.html exactly)
# ---------------------------------------------------------------------------

_DARK = {
    # Backgrounds (cosmic navy)
    "bg_primary": "#07091A",
    "bg_card": "#0E1230",
    "bg_card_hover": "#151A3D",
    "bg_elevated": "#11173D",
    "bg_inset": "#060815",
    "bg_overlay": "rgba(7,9,26,0.90)",

    # Borders
    "border_subtle": "rgba(255,255,255,0.08)",
    "border_default": "rgba(255,255,255,0.14)",
    "border_active": "rgba(139,92,246,0.40)",

    # Text
    "text_primary": "#F4F5FF",
    "text_secondary": "#C4C7E8",
    "text_muted": "#8B91C1",
    "text_inverse": "#07091A",

    # Shadows
    "shadow_xs": "0 1px 2px rgba(0,0,0,0.3)",
    "shadow_card": "0 1px 3px rgba(0,0,0,0.35), 0 1px 2px rgba(0,0,0,0.2)",
    "shadow_md": "0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.25)",
    "shadow_lg": "0 8px 24px rgba(0,0,0,0.45), 0 4px 8px rgba(0,0,0,0.3)",
    "shadow_glow": "0 0 0 3px rgba(139,92,246,0.20)",
    "shadow_focus": "0 0 0 3px rgba(139,92,246,0.30)",

    # Sidebar
    "sidebar_bg": "linear-gradient(180deg, rgba(11,15,42,0.97), rgba(7,9,26,0.97))",
    "sidebar_border": "rgba(255,255,255,0.08)",

    # Aurora / cosmic
    "aurora_1": "rgba(139,92,246,0.25)",
    "aurora_2": "rgba(34,211,238,0.12)",
    "aurora_3": "rgba(236,72,153,0.12)",
    "star_opacity": "0.35",
    "nav_bg": "rgba(11,15,42,0.7)",
}

_LIGHT = {
    # Backgrounds
    "bg_primary": "#FAFAFC",
    "bg_card": "#FFFFFF",
    "bg_card_hover": "#F4F5F9",
    "bg_elevated": "#EBEDF4",
    "bg_inset": "#E0E3EE",
    "bg_overlay": "rgba(255,255,255,0.85)",

    # Borders
    "border_subtle": "rgba(15,23,42,0.08)",
    "border_default": "rgba(15,23,42,0.14)",
    "border_active": "rgba(124,58,237,0.35)",

    # Text
    "text_primary": "#0F172A",
    "text_secondary": "#334155",
    "text_muted": "#64748B",
    "text_inverse": "#FFFFFF",

    # Shadows
    "shadow_xs": "0 1px 2px rgba(15,23,42,0.06)",
    "shadow_card": "0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.05)",
    "shadow_md": "0 4px 12px rgba(15,23,42,0.10), 0 2px 4px rgba(15,23,42,0.06)",
    "shadow_lg": "0 8px 24px rgba(15,23,42,0.12), 0 4px 8px rgba(15,23,42,0.06)",
    "shadow_glow": "0 0 0 3px rgba(124,58,237,0.12)",
    "shadow_focus": "0 0 0 3px rgba(124,58,237,0.20)",

    # Sidebar
    "sidebar_bg": "#FFFFFF",
    "sidebar_border": "rgba(15,23,42,0.08)",

    # Aurora / cosmic (subtle in light)
    "aurora_1": "rgba(124,58,237,0.08)",
    "aurora_2": "rgba(8,145,178,0.06)",
    "aurora_3": "rgba(219,39,119,0.06)",
    "star_opacity": "0",
    "nav_bg": "rgba(255,255,255,0.75)",
}


def _build_css(t: dict[str, str]) -> str:
    """Build the full shared CSS with the given theme palette baked into :root."""
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">

<style>
/* ===== Design Tokens (cosmic theme) ===== */
:root {{
    /* --- Backgrounds --- */
    --bg-primary: {t["bg_primary"]};
    --bg-card: {t["bg_card"]};
    --bg-card-hover: {t["bg_card_hover"]};
    --bg-elevated: {t["bg_elevated"]};
    --bg-inset: {t["bg_inset"]};
    --bg-overlay: {t["bg_overlay"]};

    /* --- Borders --- */
    --border-subtle: {t["border_subtle"]};
    --border-default: {t["border_default"]};
    --border-active: {t["border_active"]};

    /* --- Text --- */
    --text-primary: {t["text_primary"]};
    --text-secondary: {t["text_secondary"]};
    --text-muted: {t["text_muted"]};
    --text-inverse: {t["text_inverse"]};

    /* --- Accent palette (violet/indigo matching landing page) --- */
    --accent-primary: #8B5CF6;
    --accent-primary-hover: #7C3AED;
    --accent-primary-subtle: rgba(139,92,246,0.10);
    --accent-primary-light: rgba(139,92,246,0.18);
    --accent-secondary: #22D3EE;
    --accent-success: #10B981;
    --accent-success-subtle: rgba(16,185,129,0.10);
    --accent-warning: #F59E0B;
    --accent-warning-subtle: rgba(245,158,11,0.10);
    --accent-danger: #EC4899;
    --accent-danger-subtle: rgba(236,72,153,0.10);
    --accent-info: #22D3EE;
    --accent-info-subtle: rgba(34,211,238,0.10);
    --accent-purple: #A855F7;
    --accent-purple-subtle: rgba(168,85,247,0.10);
    --indigo: #6366F1;
    --violet: #8B5CF6;
    --purple: #A855F7;
    --pink: #EC4899;
    --cyan: #22D3EE;
    --green: #10B981;
    --amber: #F59E0B;

    /* --- Gradients --- */
    --gradient-primary: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%);
    --gradient-hero: linear-gradient(135deg, #6366F1 0%, #A855F7 40%, #22D3EE 100%);
    --gradient-accent: linear-gradient(135deg, #6366F1 0%, #A855F7 100%);
    --gradient-surface: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-elevated) 100%);
    --gradient-text: linear-gradient(135deg, #FFFFFF 0%, #C4B5FD 40%, #818CF8 70%, #22D3EE 100%);

    /* --- Typography (matching landing page) --- */
    --font-display: 'Instrument Serif', Georgia, serif;
    --font-body: 'Inter Tight', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    --text-xs: 0.75rem;
    --text-sm: 0.8125rem;
    --text-base: 0.875rem;
    --text-lg: 1rem;
    --text-xl: 1.125rem;
    --text-2xl: 1.5rem;
    --text-3xl: 1.875rem;
    --text-4xl: 2.25rem;

    --leading-tight: 1.25;
    --leading-normal: 1.5;
    --leading-relaxed: 1.625;

    --tracking-tight: -0.025em;
    --tracking-normal: -0.01em;
    --tracking-wide: 0.05em;

    /* --- Spacing --- */
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-5: 1.25rem;
    --space-6: 1.5rem;
    --space-8: 2rem;
    --space-10: 2.5rem;
    --space-12: 3rem;

    /* --- Radii --- */
    --radius-xs: 4px;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    --radius-2xl: 20px;
    --radius-full: 9999px;

    /* --- Shadows --- */
    --shadow-xs: {t["shadow_xs"]};
    --shadow-card: {t["shadow_card"]};
    --shadow-md: {t["shadow_md"]};
    --shadow-lg: {t["shadow_lg"]};
    --shadow-glow: {t["shadow_glow"]};
    --shadow-focus: {t["shadow_focus"]};

    /* --- Transitions --- */
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
    --duration-fast: 120ms;
    --duration-normal: 200ms;
    --duration-slow: 350ms;
    --transition-colors: color var(--duration-fast) var(--ease-in-out),
                         background-color var(--duration-fast) var(--ease-in-out),
                         border-color var(--duration-fast) var(--ease-in-out);
    --transition-shadow: box-shadow var(--duration-normal) var(--ease-in-out);
    --transition-transform: transform var(--duration-normal) var(--ease-out);
    --transition-all: all var(--duration-normal) var(--ease-in-out);

    /* --- Sidebar --- */
    --sidebar-bg: {t["sidebar_bg"]};
    --sidebar-border: {t["sidebar_border"]};

    /* --- Cosmic effects --- */
    --aurora-1: {t["aurora_1"]};
    --aurora-2: {t["aurora_2"]};
    --aurora-3: {t["aurora_3"]};
    --star-opacity: {t["star_opacity"]};

    /* --- Chart palette (8 colors for Plotly / data viz) --- */
    --chart-1: #8B5CF6;
    --chart-2: #22D3EE;
    --chart-3: #EC4899;
    --chart-4: #10B981;
    --chart-5: #F59E0B;
    --chart-6: #6366F1;
    --chart-7: #A855F7;
    --chart-8: #06B6D4;
}}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }}
}}

/* ===== Base Resets ===== */
html, body, [class*="css"] {{
    font-family: var(--font-body);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    letter-spacing: -0.01em;
}}

/* ===== Cosmic background with aurora gradients ===== */
.stApp,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] {{
    background:
        radial-gradient(ellipse 80% 50% at 50% -10%, var(--aurora-1), transparent),
        radial-gradient(ellipse 60% 50% at 100% 30%, var(--aurora-2), transparent),
        radial-gradient(ellipse 60% 50% at 0% 60%, var(--aurora-3), transparent),
        var(--bg-primary) !important;
    color: var(--text-primary) !important;
    transition: background 0.4s ease, color 0.4s ease;
}}

/* Starfield overlay */
.stApp::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        radial-gradient(1px 1px at 20% 30%, white, transparent),
        radial-gradient(1px 1px at 60% 70%, white, transparent),
        radial-gradient(1px 1px at 50% 50%, rgba(255,255,255,0.6), transparent),
        radial-gradient(1px 1px at 80% 10%, rgba(255,255,255,0.8), transparent),
        radial-gradient(1px 1px at 90% 60%, white, transparent),
        radial-gradient(1px 1px at 33% 95%, rgba(255,255,255,0.7), transparent),
        radial-gradient(1px 1px at 15% 80%, white, transparent);
    background-size: 400px 400px;
    opacity: var(--star-opacity);
    pointer-events: none;
    z-index: 0;
    transition: opacity 0.4s ease;
}}

/* Content above starfield */
.main, .block-container, [data-testid="stSidebar"] {{
    position: relative;
    z-index: 1;
}}

[data-testid="stHeader"] {{
    background: transparent !important;
}}

/* ===== Sidebar (glass surface) ===== */
[data-testid="stSidebar"] {{
    background: var(--sidebar-bg) !important;
    border-right: 1px solid var(--sidebar-border) !important;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
}}
[data-testid="stSidebar"] > div {{
    padding-top: 1rem;
}}
[data-testid="stSidebar"] .stMarkdown p {{
    color: var(--text-secondary);
    font-size: var(--text-sm);
}}

/* ===== Keyframes ===== */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to   {{ opacity: 1; }}
}}
@keyframes slideInRight {{
    from {{ opacity: 0; transform: translateX(12px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
}}
@keyframes shimmer {{
    0%   {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}
@keyframes pulse-soft {{
    0%, 100% {{ opacity: 1; }}
    50%      {{ opacity: 0.7; }}
}}
@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}
@keyframes pulse-ring {{
    0% {{ transform: scale(1); opacity: 1; }}
    100% {{ transform: scale(2.5); opacity: 0; }}
}}

/* ===== Glass Card ===== */
.glass-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    margin-bottom: var(--space-5);
    box-shadow: var(--shadow-card);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    transition: var(--transition-shadow), var(--transition-colors);
}}
.glass-card:hover {{
    border-color: var(--border-default);
    box-shadow: var(--shadow-md);
}}

/* ===== Glass utility ===== */
.glass {{
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid var(--border-subtle);
}}
.glass-strong {{
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid var(--border-default);
}}

/* ===== Page Header (gradient text) ===== */
.page-header h1,
.eda-page-header h1,
.upload-heading {{
    font-family: var(--font-display);
    font-size: var(--text-3xl);
    font-weight: 400;
    background: var(--gradient-text);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: var(--tracking-tight);
    margin: 0 0 var(--space-1);
    line-height: var(--leading-tight);
}}

/* ===== Section Header ===== */
.section-header,
.cfg-section-label {{
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--violet);
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-2);
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.section-header::before,
.cfg-section-label::before {{
    content: '\\2726';
}}

/* ===== Dividers ===== */
hr {{
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-default), transparent) !important;
    margin: var(--space-6) 0 !important;
}}

/* ===== Buttons (gradient glow matching landing page) ===== */
.stButton > button[kind="primary"],
.stDownloadButton > button {{
    background: linear-gradient(135deg, var(--indigo) 0%, var(--violet) 50%, var(--purple) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-full) !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
    font-family: var(--font-body) !important;
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.1) inset,
        0 8px 32px rgba(139,92,246,0.4),
        0 4px 16px rgba(99,102,241,0.3) !important;
    transition: all 0.3s cubic-bezier(0.16,1,0.3,1) !important;
    min-height: 40px;
    letter-spacing: 0.01em;
}}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.2) inset,
        0 12px 48px rgba(139,92,246,0.6),
        0 8px 24px rgba(99,102,241,0.5) !important;
}}

/* Secondary/Default Button (glass) */
.stButton > button:not([kind="primary"]) {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body);
    font-weight: 500;
    border-radius: var(--radius-full);
    font-size: var(--text-sm);
    min-height: 40px;
    backdrop-filter: blur(24px);
    transition: var(--transition-all);
}}
.stButton > button:not([kind="primary"]):hover {{
    background: rgba(255,255,255,0.08) !important;
    border-color: var(--violet) !important;
    transform: translateY(-1px) !important;
}}

/* ===== Streamlit Widget Overrides ===== */
.stSelectbox label,
.stMultiSelect label,
.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stRadio label,
.stCheckbox label,
.stSlider label {{
    color: var(--text-primary) !important;
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 500;
}}

/* ===== Inputs (glass with violet focus) ===== */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stDateInput input {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-lg) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
    backdrop-filter: blur(12px);
}}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {{
    border-color: var(--violet) !important;
    box-shadow: 0 0 0 3px rgba(139,92,246,0.15) !important;
}}

.stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"] {{
    background: var(--bg-card) !important;
    border-color: var(--border-default) !important;
    border-radius: var(--radius-lg) !important;
}}
.stSelectbox [data-baseweb="select"]:focus-within,
.stMultiSelect [data-baseweb="select"]:focus-within {{
    border-color: var(--violet) !important;
    box-shadow: var(--shadow-focus) !important;
}}

/* ===== File uploader (violet dashed border) ===== */
[data-testid="stFileUploader"] section {{
    background: rgba(139,92,246,0.05) !important;
    border: 2px dashed rgba(139,92,246,0.4) !important;
    border-radius: var(--radius-xl) !important;
    padding: 2rem !important;
    transition: all 0.3s !important;
}}
[data-testid="stFileUploader"] section:hover {{
    background: rgba(139,92,246,0.1) !important;
    border-color: rgba(139,92,246,0.7) !important;
}}
[data-testid="stFileUploader"] button {{
    background: linear-gradient(135deg, var(--indigo), var(--violet)) !important;
    color: white !important;
    border-radius: var(--radius-full) !important;
    border: none !important;
    padding: 8px 20px !important;
    font-weight: 500 !important;
}}

/* ===== Data Frames ===== */
[data-testid="stDataFrame"], .stTable {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-xl) !important;
    overflow: hidden;
    backdrop-filter: blur(24px);
}}
[data-testid="stDataFrame"] table thead th {{
    background: var(--bg-elevated) !important;
    color: var(--violet) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* ===== Tabs (pill style matching landing) ===== */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-xl) !important;
    padding: 6px !important;
    gap: 4px !important;
    backdrop-filter: blur(24px);
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: var(--radius-lg) !important;
    padding: 8px 16px !important;
    font-weight: 500 !important;
    font-family: var(--font-body) !important;
    transition: all 0.2s !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
    background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25)) !important;
    color: var(--text-primary) !important;
    border: 1px solid rgba(139,92,246,0.4) !important;
    font-weight: 600;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    display: none !important;
}}

/* ===== Markdown ===== */
.stMarkdown, .stMarkdown p {{
    color: var(--text-primary);
    font-family: var(--font-body);
    line-height: var(--leading-relaxed);
}}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
    font-family: var(--font-display);
    color: var(--text-primary);
    font-weight: 400;
    letter-spacing: -0.02em;
}}
/* Display gradient on h1 */
.stMarkdown h1 {{
    background: var(--gradient-text);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.stMarkdown code {{
    font-family: var(--font-mono);
    font-size: 0.85em;
    background: rgba(0,0,0,0.4);
    padding: 0.15em 0.4em;
    border-radius: var(--radius-xs);
    color: var(--cyan);
    border: 1px solid var(--border-subtle);
}}

/* ===== Metric Cards (glass) ===== */
[data-testid="stMetric"] {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-xl) !important;
    padding: 1.25rem !important;
    backdrop-filter: blur(24px);
    transition: var(--transition-shadow);
}}
[data-testid="stMetric"]:hover {{
    box-shadow: var(--shadow-md);
}}
[data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    font-weight: 500;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}}
[data-testid="stMetricValue"] {{
    font-family: var(--font-display) !important;
    font-size: 2.5rem !important;
    background: linear-gradient(135deg, #FFFFFF 0%, #C4B5FD 40%, #818CF8 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}
[data-testid="stMetricDelta"] {{
    font-family: var(--font-mono) !important;
}}

/* ===== Alerts ===== */
.stAlert,
[data-testid="stNotification"] {{
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border-subtle) !important;
    backdrop-filter: blur(24px);
}}
[data-testid="stNotification"][data-baseweb="notification"][kind="info"] {{
    background: rgba(99,102,241,0.12) !important;
    border-color: rgba(99,102,241,0.3) !important;
}}
[data-testid="stNotification"][kind="success"] {{
    background: rgba(16,185,129,0.12) !important;
    border-color: rgba(16,185,129,0.3) !important;
}}
[data-testid="stNotification"][kind="warning"] {{
    background: rgba(245,158,11,0.12) !important;
    border-color: rgba(245,158,11,0.3) !important;
}}
[data-testid="stNotification"][kind="error"] {{
    background: rgba(236,72,153,0.12) !important;
    border-color: rgba(236,72,153,0.3) !important;
}}

/* ===== Progress bars ===== */
.stProgress > div > div > div {{
    background: linear-gradient(90deg, var(--violet), var(--cyan)) !important;
    border-radius: var(--radius-full) !important;
}}

/* ===== Sliders ===== */
.stSlider [data-baseweb="slider"] [role="slider"] {{
    background: var(--violet) !important;
    border: 2px solid var(--text-primary) !important;
    box-shadow: 0 0 0 4px rgba(139,92,246,0.3) !important;
}}

/* ===== Code blocks ===== */
[data-testid="stCodeBlock"], pre, code {{
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    font-family: var(--font-mono) !important;
}}

/* ===== Plotly chart container ===== */
.js-plotly-plot {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-xl) !important;
    padding: 1rem !important;
}}

/* ===== Expander ===== */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
}}
[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-xl) !important;
    backdrop-filter: blur(24px);
}}

/* ===== Captions ===== */
[data-testid="stCaptionContainer"], .caption {{
    font-family: var(--font-mono) !important;
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
}}

/* ===== Badge utility ===== */
.badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.5rem;
    font-size: var(--text-xs);
    font-weight: 500;
    border-radius: var(--radius-full);
    letter-spacing: 0.02em;
}}
.badge-primary {{
    background: var(--accent-primary-subtle);
    color: var(--violet);
}}
.badge-success {{
    background: var(--accent-success-subtle);
    color: var(--green);
}}
.badge-warning {{
    background: var(--accent-warning-subtle);
    color: var(--amber);
}}
.badge-danger {{
    background: var(--accent-danger-subtle);
    color: var(--pink);
}}

/* ===== Status dot utility ===== */
.status-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: var(--radius-full);
    margin-right: var(--space-2);
}}
.status-dot-success {{ background: var(--green); }}
.status-dot-warning {{ background: var(--amber); }}
.status-dot-danger  {{ background: var(--pink); }}
.status-dot-info    {{ background: var(--cyan); }}

/* ===== Pill tab pattern (shared across pages) ===== */
.pill-tabs {{
    display: flex;
    gap: var(--space-2);
    padding: var(--space-1);
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    margin-bottom: var(--space-6);
    backdrop-filter: blur(24px);
}}
.pill-tab {{
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-lg);
    font-family: var(--font-body);
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--text-muted);
    cursor: pointer;
    transition: var(--transition-all);
    border: none;
    background: transparent;
}}
.pill-tab:hover {{
    color: var(--text-secondary);
    background: rgba(255,255,255,0.04);
}}
.pill-tab.active {{
    color: var(--text-primary);
    background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.25));
    border: 1px solid rgba(139,92,246,0.4);
    box-shadow: 0 4px 20px rgba(139,92,246,0.2);
    font-weight: 600;
}}

/* ===== Glass table (shared across pages) ===== */
.glass-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-family: var(--font-body);
    font-size: var(--text-sm);
}}
.glass-table thead th {{
    background: var(--bg-elevated);
    color: var(--violet);
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: var(--tracking-wide);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-subtle);
    text-align: left;
}}
.glass-table tbody td {{
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-primary);
    vertical-align: middle;
}}
.glass-table tbody tr:hover td {{
    background: var(--bg-card-hover);
}}
.glass-table tbody tr:last-child td {{
    border-bottom: none;
}}

/* ===== Scrollbar styling ===== */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: var(--bg-elevated); }}
::-webkit-scrollbar-thumb {{ background: var(--bg-inset); border-radius: 5px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--violet); }}

/* ===== Hide default Streamlit chrome ===== */
.stDeployButton,
#MainMenu {{
    display: none !important;
}}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 0 !important;
}}

/* ===== Section label helper (matches landing page) ===== */
.autods-section-label {{
    font-family: var(--font-mono);
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--violet);
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.autods-section-label::before {{
    content: '\\2726';
}}

/* ===== Glow text utility ===== */
.glow-text {{
    background: var(--gradient-text);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}

/* ===== Btn glow (matching landing page CTA) ===== */
.btn-glow {{
    position: relative;
    background: linear-gradient(135deg, var(--indigo) 0%, var(--violet) 50%, var(--purple) 100%);
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.1) inset,
        0 8px 32px rgba(139,92,246,0.4),
        0 4px 16px rgba(99,102,241,0.3);
    transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
}}
.btn-glow:hover {{
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.2) inset,
        0 12px 48px rgba(139,92,246,0.6),
        0 8px 24px rgba(99,102,241,0.5);
    transform: translateY(-2px);
}}

/* ===== Card sheen effect ===== */
.card-sheen {{
    position: relative;
    overflow: hidden;
}}
.card-sheen::before {{
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
    transition: left 0.7s;
}}
.card-sheen:hover::before {{
    left: 100%;
}}
</style>"""


# ---------------------------------------------------------------------------
# Plotly theme helper
# ---------------------------------------------------------------------------

PLOTLY_CHART_COLORS = [
    "#8B5CF6", "#22D3EE", "#EC4899", "#10B981",
    "#F59E0B", "#6366F1", "#A855F7", "#06B6D4",
]


def get_plotly_layout(is_dark: bool = True) -> dict:
    """Return a Plotly layout dict matching the current theme.

    Use as: ``fig.update_layout(**get_plotly_layout(is_dark))``
    """
    t = _DARK if is_dark else _LIGHT
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "Inter Tight, -apple-system, sans-serif",
            "color": t["text_secondary"],
            "size": 12,
        },
        "title": {
            "font": {
                "family": "Instrument Serif, Georgia, serif",
                "size": 16,
                "color": t["text_primary"],
            }
        },
        "colorway": PLOTLY_CHART_COLORS,
        "xaxis": {
            "gridcolor": t["border_subtle"],
            "zerolinecolor": t["border_default"],
            "tickfont": {"size": 11, "color": t["text_muted"]},
        },
        "yaxis": {
            "gridcolor": t["border_subtle"],
            "zerolinecolor": t["border_default"],
            "tickfont": {"size": 11, "color": t["text_muted"]},
        },
        "legend": {
            "font": {"size": 11, "color": t["text_secondary"]},
            "bgcolor": "rgba(0,0,0,0)",
        },
        "margin": {"l": 48, "r": 24, "t": 48, "b": 40},
    }


# ---------------------------------------------------------------------------
# Helper functions (from landing page theme)
# ---------------------------------------------------------------------------


def section_label(text: str) -> None:
    """Render a small uppercase mono label like the landing page section headers."""
    st.markdown(
        f'<div class="autods-section-label">{text}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_shared_css() -> bool:
    """Inject shared CSS with the active theme baked into ``:root``.

    Call this at the top of every dashboard page.  The toggle button is NOT
    rendered here -- it lives in ``app.py``'s sidebar so it only exists once.

    Returns:
        ``True`` if dark mode is currently active, ``False`` otherwise.
    """
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = True  # Dark mode default (cosmic)

    is_dark: bool = st.session_state["dark_mode"]
    palette = _DARK if is_dark else _LIGHT

    st.markdown(_build_css(palette), unsafe_allow_html=True)
    st.markdown(_SNAV_CSS, unsafe_allow_html=True)
    st.markdown(_UPLOAD_CSS, unsafe_allow_html=True)

    return is_dark


# ---------------------------------------------------------------------------
# Sidebar-nav component CSS  (injected by inject_shared_css)
# ---------------------------------------------------------------------------

_SNAV_CSS = """
<style>
/* ===== Sidebar Navigation (snav-*) ===== */
.snav-brand {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) 0 var(--space-2);
}
.snav-logo-mark {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    background: var(--gradient-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(139,92,246,0.40);
}
.snav-logo-name {
    font-family: var(--font-body);
    font-size: var(--text-lg);
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}
.snav-logo-sub {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-top: 1px;
}
.snav-section-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: var(--space-3) 0 var(--space-2);
}
.snav-workspace-card {
    font-family: var(--font-body);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: var(--space-2) var(--space-3);
    margin-bottom: var(--space-2);
}
.snav-status-ok   { color: var(--accent-success); }
.snav-status-idle { color: var(--text-muted); }
.snav-pipeline { display: flex; flex-direction: column; gap: 2px; }
.snav-step-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}
.snav-dot {
    width: 8px;
    height: 8px;
    border-radius: var(--radius-full);
    flex-shrink: 0;
}
.snav-dot-done    { background: var(--accent-success); }
.snav-dot-current { background: var(--accent-primary); box-shadow: 0 0 6px var(--accent-primary); }
.snav-dot-pending { background: var(--border-default); }
</style>
"""


def render_theme_toggle() -> None:
    """Render the dark/light toggle button.  Call ONCE from ``app.py`` sidebar."""
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = True  # Dark mode default (cosmic)

    is_dark: bool = st.session_state["dark_mode"]
    label = "\u2600 Light" if is_dark else "\u263e Dark"

    if st.button(label, key="_theme_toggle_btn", use_container_width=True):
        st.session_state["dark_mode"] = not is_dark
        st.rerun()


# ---------------------------------------------------------------------------
# Upload page component CSS  (injected by inject_shared_css)
# ---------------------------------------------------------------------------

_UPLOAD_CSS = """
.up-crumbs { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 12.5px; color: var(--text-muted); letter-spacing: 0.4px; margin-bottom: 24px; }
.up-crumbs .sep { color: var(--text-faint); }
.up-crumbs .cur { color: var(--text-primary); }
.up-hero { margin-bottom: 36px; }
.up-hero-eyebrow { display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px 4px 8px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 999px; font-size: 11.5px; color: var(--text-secondary); margin-bottom: 18px; backdrop-filter: blur(12px); font-family: var(--font-mono); letter-spacing: 0.6px; text-transform: uppercase; }
.up-hero h1 { font-family: var(--font-display); font-size: 56px; line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px; color: var(--text-primary); }
.up-hero h1 em { font-style: italic; background: var(--gradient-text); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.up-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }
.up-tabs { display: flex; gap: 6px; margin-bottom: 24px; padding: 6px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 14px; backdrop-filter: blur(14px); width: fit-content; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="1"]) { background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important; color: white !important; box-shadow: 0 0 18px rgba(139,92,246,0.4) !important; border: none !important; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="0"]) { background: transparent !important; color: var(--text-muted) !important; border: none !important; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="0"]):hover { color: var(--text-primary) !important; background: rgba(139,92,246,0.06) !important; }
.up-drop-zone { background: var(--bg-card); border: 2px dashed var(--border-default); border-radius: 20px; padding: 48px 32px 28px; text-align: center; backdrop-filter: blur(14px); transition: all 0.25s ease; margin-bottom: 14px; }
.up-drop-zone:hover { border-color: var(--violet); background: rgba(139,92,246,0.06); box-shadow: var(--shadow-glow); }
.up-drop-icon { width: 64px; height: 64px; margin: 0 auto 18px; border-radius: 50%; background: rgba(139,92,246,0.12); border: 1px solid var(--border-default); display: grid; place-items: center; color: var(--violet); }
.up-drop-title { font-size: 18px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
.up-drop-sub { font-size: 13px; color: var(--text-muted); }
.up-fmt-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 18px; padding: 0 12px; }
.up-fmt-chip { padding: 4px 10px; background: rgba(139,92,246,0.06); border: 1px solid var(--border-subtle); border-radius: 999px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary); letter-spacing: 0.5px; }
.up-conn-card { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 20px; padding: 28px; backdrop-filter: blur(14px); }
.up-conn-title { font-family: var(--font-display); font-size: 22px; margin-bottom: 6px; }
.up-conn-title em { font-style: italic; background: var(--gradient-text); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.up-conn-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 24px; }
.up-providers { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; margin-bottom: 22px; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-prov][data-selected="1"]) { background: rgba(139,92,246,0.15) !important; border: 1px solid var(--violet) !important; box-shadow: 0 0 14px -4px var(--violet) !important; color: var(--text-primary) !important; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-prov][data-selected="0"]) { background: rgba(139,92,246,0.06) !important; border: 1px solid var(--border-subtle) !important; color: var(--text-secondary) !important; }
.up-info-panel { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 18px 20px; backdrop-filter: blur(14px); margin-bottom: 16px; }
.up-info-panel h4 { font-size: 13px; font-weight: 600; margin-bottom: 10px; color: var(--text-primary); }
.up-info-panel p { font-size: 12.5px; color: var(--text-muted); line-height: 1.55; }
.up-info-panel ul { list-style: none; padding: 0; margin: 0; }
.up-info-panel li { font-size: 12.5px; color: var(--text-secondary); padding: 4px 0; padding-left: 14px; position: relative; }
.up-info-panel li::before { content: "\u2022"; position: absolute; left: 4px; color: var(--violet); }
.up-ms-icon { font-size: 22px; color: var(--violet); padding-top: 6px; }
.up-ms-header-text h3 { font-family: var(--font-display); font-size: 22px; margin-bottom: 2px; }
.up-ms-header-text p { font-size: 13px; color: var(--text-muted); }
.up-ms-tag { font-family: var(--font-mono); font-size: 9.5px; padding: 3px 8px; background: rgba(139,92,246,0.1); border: 1px solid var(--border-subtle); border-radius: 999px; color: var(--violet); letter-spacing: 0.6px; text-transform: uppercase; vertical-align: middle; margin-left: 8px; }
.up-ms-body { padding: 0 24px 24px; }
.up-ms-help { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.up-ms-file { display: grid; grid-template-columns: auto 1fr auto auto auto; gap: 14px; align-items: center; padding: 12px 16px; background: rgba(139,92,246,0.04); border: 1px solid var(--border-subtle); border-radius: 12px; margin-bottom: 10px; transition: all 0.2s ease; }
.up-ms-primary { background: rgba(139,92,246,0.1) !important; border-color: var(--border-strong) !important; box-shadow: 0 0 14px -4px var(--violet); }
.up-ms-fileicon { width: 36px; height: 36px; border-radius: 9px; background: rgba(139,92,246,0.12); display: grid; place-items: center; color: var(--violet); font-size: 16px; }
.up-ms-fname { font-size: 13.5px; font-weight: 500; color: var(--text-primary); }
.up-ms-fmeta { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); }
.up-ms-rows { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary); padding: 4px 8px; background: rgba(139,92,246,0.04); border-radius: 6px; }
.up-ms-arrow { color: var(--text-faint); text-align: center; }
.up-ms-join-config { background: rgba(139,92,246,0.04); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 18px; margin-top: 22px; }
.up-ms-join-title { font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--text-primary); }
.up-detected { display: inline-flex; align-items: center; font-family: var(--font-mono); font-size: 9.5px; padding: 2px 8px; border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase; margin-top: 4px; }
.up-detected-exact { color: var(--green); background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.3); }
.up-detected-fuzzy { color: var(--amber); background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.3); }
.up-recent-strip { margin: 0 0 32px; }
.up-strip-label { font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-faint); margin-bottom: 12px; }
.up-recent-grid { display: flex; gap: 10px; flex-wrap: wrap; }
.up-sec-divider { display: flex; align-items: center; gap: 14px; margin: 56px 0 24px; }
.up-sec-label { font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--violet); padding: 4px 12px; background: rgba(139,92,246,0.08); border-radius: 999px; border: 1px solid var(--border-subtle); white-space: nowrap; }
.up-sec-line { height: 1px; flex: 1; background: var(--border-subtle); }
.up-sec-title { font-family: var(--font-display); font-size: 32px; margin-bottom: 6px; }
.up-sec-title em { font-style: italic; background: var(--gradient-text); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.up-sec-sub { font-size: 14px; color: var(--text-muted); margin-bottom: 22px; }
.up-sample-card { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 16px; padding: 20px; cursor: pointer; transition: all 0.25s ease; backdrop-filter: blur(14px); position: relative; overflow: hidden; }
.up-sample-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%); opacity: 0; transition: opacity 0.25s; }
.up-sample-card:hover { transform: translateY(-3px); border-color: var(--border-strong); box-shadow: var(--shadow-glow); }
.up-sample-card:hover::before { opacity: 1; }
.up-sample-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 8px; }
.up-sample-name { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.up-sample-domain { font-family: var(--font-mono); font-size: 9.5px; padding: 3px 8px; border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase; flex-shrink: 0; }
.up-dom-classification { color: var(--violet); border: 1px solid rgba(168,85,247,0.4); background: rgba(168,85,247,0.1); }
.up-dom-regression { color: var(--cyan); border: 1px solid rgba(34,211,238,0.4); background: rgba(34,211,238,0.1); }
.up-dom-healthcare { color: var(--green); border: 1px solid rgba(52,211,153,0.4); background: rgba(52,211,153,0.1); }
.up-dom-finance { color: var(--cyan); border: 1px solid rgba(34,211,238,0.4); background: rgba(34,211,238,0.1); }
.up-dom-ecommerce { color: var(--amber); border: 1px solid rgba(251,191,36,0.4); background: rgba(251,191,36,0.1); }
.up-dom-hr { color: var(--pink); border: 1px solid rgba(236,72,153,0.4); background: rgba(236,72,153,0.1); }
.up-sample-desc { font-size: 12.5px; color: var(--text-muted); line-height: 1.5; margin-bottom: 14px; min-height: 36px; }
.up-sample-stats { display: flex; gap: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }
.up-sample-stat { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary); }
.up-sample-stat .v { color: var(--text-primary); font-weight: 500; padding-right: 4px; }
.up-result-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; gap: 24px; flex-wrap: wrap; }
.up-result-title h2 { font-family: var(--font-display); font-size: 30px; line-height: 1.1; }
.up-result-title h2 em { font-style: italic; background: var(--gradient-text); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.up-result-title p { font-size: 13px; color: var(--text-muted); margin-top: 4px; font-family: var(--font-mono); letter-spacing: 0.4px; }
.up-domain-detected { display: flex; align-items: center; gap: 14px; padding: 12px 20px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 14px; backdrop-filter: blur(14px); }
.up-dd-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-faint); }
.up-dd-value { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 500; }
.up-dd-conf { font-family: var(--font-mono); font-size: 11px; color: var(--green); padding: 3px 8px; background: rgba(52,211,153,0.1); border-radius: 999px; border: 1px solid rgba(52,211,153,0.3); }
.up-file-meta { display: flex; flex-wrap: wrap; gap: 22px; padding: 16px 22px; background: rgba(139,92,246,0.03); border: 1px solid var(--border-subtle); border-radius: 12px; margin-bottom: 28px; backdrop-filter: blur(8px); }
.up-fm-item { display: flex; flex-direction: column; gap: 2px; }
.up-fm-label { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-faint); letter-spacing: 1px; text-transform: uppercase; }
.up-fm-value { font-size: 12.5px; color: var(--text-secondary); font-family: var(--font-mono); }
.up-metric-card { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 14px; padding: 20px; backdrop-filter: blur(14px); position: relative; overflow: hidden; }
.up-metric-card::after { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%); opacity: 0.7; }
.up-metric-label { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 1px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.up-metric-value { font-family: var(--font-display); font-size: 36px; line-height: 1; }
.up-metric-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px; font-family: var(--font-mono); }
.up-quality { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 16px; padding: 22px; margin: 28px 0; backdrop-filter: blur(14px); }
.up-quality-title { font-size: 14px; font-weight: 600; margin-bottom: 18px; color: var(--text-primary); }
.up-quality-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.up-qg-item { display: flex; flex-direction: column; gap: 6px; }
.up-qg-label { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.up-qg-value { display: flex; justify-content: space-between; align-items: baseline; }
.up-qg-num { font-family: var(--font-display); font-size: 22px; }
.up-qg-tag { font-family: var(--font-mono); font-size: 9.5px; padding: 2px 7px; border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase; }
.up-qg-good { color: var(--green); background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.up-qg-warn { color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.up-qg-bad  { color: var(--red);   background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3); }
.up-qg-bar { height: 6px; background: rgba(139,92,246,0.1); border-radius: 3px; overflow: hidden; }
.up-qg-fill { height: 100%; border-radius: 3px; box-shadow: 0 0 6px rgba(139,92,246,0.5); }
.up-qg-fill-good { background: linear-gradient(135deg, var(--green), var(--cyan)); }
.up-qg-fill-warn { background: linear-gradient(135deg, var(--amber), var(--red)); }
.up-qg-fill-bad  { background: linear-gradient(135deg, var(--red), var(--pink)); }
.up-schema-title { font-size: 14px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); margin-top: 28px; }
.up-schema-wrap { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 14px; overflow: hidden; backdrop-filter: blur(14px); margin-bottom: 14px; }
.up-schema { width: 100%; border-collapse: collapse; font-size: 13px; }
.up-schema thead { background: rgba(139,92,246,0.06); border-bottom: 1px solid var(--border-subtle); }
.up-schema th { text-align: left; padding: 12px 18px; font-family: var(--font-mono); font-size: 10px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted); }
.up-schema td { padding: 12px 18px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); }
.up-schema tr:last-child td { border-bottom: none; }
.up-schema tr:hover { background: rgba(139,92,246,0.04); }
.up-col-name { color: var(--text-primary); font-weight: 500; }
.up-dtype-pill { font-family: var(--font-mono); font-size: 10px; padding: 2px 8px; border-radius: 6px; letter-spacing: 0.4px; }
.up-dtype-int   { color: var(--cyan);   background: rgba(34,211,238,0.1);  border: 1px solid rgba(34,211,238,0.3); }
.up-dtype-float { color: var(--violet); background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); }
.up-dtype-object{ color: var(--amber);  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.up-dtype-bool  { color: var(--green);  background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.up-miss-bar { display: inline-flex; align-items: center; gap: 8px; }
.up-miss-track { width: 60px; height: 4px; background: rgba(139,92,246,0.08); border-radius: 2px; overflow: hidden; }
.up-miss-fill { height: 100%; border-radius: 2px; background: var(--violet); }
.up-miss-zero { background: rgba(139,92,246,0.2); }
.up-miss-mid  { background: var(--violet); }
.up-miss-high { background: var(--pink); }
.up-miss-pct { font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); }
.up-sample-vals { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); }
.up-cta-text { display: flex; flex-direction: column; }
.up-cta-text strong { font-size: 15px; color: var(--text-primary); }
.up-cta-text span { font-size: 12px; color: var(--text-muted); }
"""
