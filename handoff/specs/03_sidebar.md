# Spec 03 — Sidebar (`sidebar_nav.py`)

## Goal

Replace Streamlit's default page nav (which currently shows "app / upload / configure / eda interactive / feature engineering / modeling / explainability / predict / chat / download" as a flat workflow list) with a **slim, grouped sidebar** that:

- Idle state: Workspace · Pipeline (muted) · Tools — like Notion/Linear/Vercel
- Active state (when inside a project): Pipeline section transforms into a live workflow tracker with status dots + violet pulse on active step

## Step 1 — Hide the default Streamlit page navigation

In `.streamlit/config.toml`, add or update:

```toml
[client]
showSidebarNavigation = false
```

This hides the auto-generated page list in the sidebar across the entire app. Our custom `sidebar_nav` then renders the only nav.

## Step 2 — `dashboard/components/sidebar_nav.py`

```python
"""
sidebar_nav.py — Custom grouped sidebar with idle / active-project states.

Idle state:        Workspace · Pipeline (muted) · Tools
Active state:      Workspace · Pipeline (live workflow tracker) · Tools
"""
from __future__ import annotations
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.project_service import PIPELINE_STEPS

# Each item: (label, page_path, icon_svg_path_data, requires_project)
WORKSPACE = [
    ("Home",     "app.py",                None, False),
    ("Projects", "app.py?view=projects",  None, False),  # routed via query param
    ("Settings", None,                    None, False),  # placeholder
]
TOOLS = [
    ("Chat",     "pages/08_chat.py",      None, True),
    ("Download", "pages/09_download.py",  None, True),
    ("Docs",     None,                    None, False),
]
PIPELINE_PAGES = [
    ("upload",         "pages/01_upload.py"),
    ("configure",      "pages/02_configure.py"),
    ("eda",            "pages/03_eda_interactive.py"),
    ("features",       "pages/04_feature_engineering.py"),
    ("modeling",       "pages/05_modeling.py"),
    ("explainability", "pages/06_explainability.py"),
    ("predict",        "pages/07_predict.py"),
]
PIPELINE_LABELS = {
    "upload": "Upload",
    "configure": "Configure",
    "eda": "EDA",
    "features": "Features",
    "modeling": "Modeling",
    "explainability": "Explainability",
    "predict": "Predict",
}


def render() -> None:
    """Render the custom sidebar. Call once near the top of every page."""
    with st.sidebar:
        _render_brand()
        _render_workspace()
        _render_pipeline()
        _render_tools()
        _render_footer()


def _render_brand() -> None:
    st.markdown(
        '<div class="sn-brand">'
        '<div class="sn-mark">A</div>'
        '<div class="sn-name">AutoDS</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_workspace() -> None:
    st.markdown('<div class="sn-label">Workspace</div>', unsafe_allow_html=True)
    if st.button("🏠  Home", key="nav_home", use_container_width=True):
        st.session_state.pop("home_view", None)
        st.switch_page("app.py")
    if st.button("📂  Projects", key="nav_projects", use_container_width=True):
        st.session_state["home_view"] = "projects"
        st.switch_page("app.py")
    st.button("⚙️  Settings", key="nav_settings", use_container_width=True, disabled=True)


def _render_pipeline() -> None:
    active = project_service.get_active()
    st.markdown('<div class="sn-label">Pipeline</div>', unsafe_allow_html=True)

    if active is None:
        # Muted state
        st.markdown(
            '<div class="sn-pipeline-muted">'
            '<div class="sn-muted-text">Start a project to access the pipeline</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Active project tracker
    st.markdown(
        f'<div class="sn-project-context">'
        f'<div class="sn-context-label">Active Project</div>'
        f'<div class="sn-context-name">{_html_escape(active.name)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for step, page_path in PIPELINE_PAGES:
        status = active.step_status.get(step, "pending")
        label = PIPELINE_LABELS[step]
        css_class = f"sn-step sn-step-{status}"
        # Render step as a button that switches pages
        if st.button(label, key=f"nav_step_{step}", use_container_width=True):
            st.switch_page(page_path)
        # Inject status indicator with custom HTML+CSS — Streamlit doesn't allow markup
        # inside button labels, so we use a sibling marker via JavaScript-free CSS:
        # see shared_css.py addition for sn-step-* selectors that style the *previous* button.
        st.markdown(
            f'<div class="{css_class}-marker" data-step="{step}" data-status="{status}"></div>',
            unsafe_allow_html=True,
        )


def _render_tools() -> None:
    st.markdown('<div class="sn-label">Tools</div>', unsafe_allow_html=True)
    active_id = project_service.get_active_id()
    if st.button("💬  Chat", key="nav_chat", use_container_width=True, disabled=active_id is None):
        st.switch_page("pages/08_chat.py")
    if st.button("⬇  Download", key="nav_download", use_container_width=True, disabled=active_id is None):
        st.switch_page("pages/09_download.py")
    st.button("📚  Docs", key="nav_docs", use_container_width=True, disabled=True)


def _render_footer() -> None:
    user = auth_service.current_user()
    if not user:
        return
    initial = (user.get("name") or "?")[:1].upper()
    st.markdown(
        f'<div class="sn-footer">'
        f'  <div class="sn-user-chip">'
        f'    <div class="sn-user-avatar">{_html_escape(initial)}</div>'
        f'    <div>'
        f'      <div class="sn-user-name">{_html_escape(user.get("name",""))}</div>'
        f'      <div class="sn-user-email">{_html_escape(user.get("email",""))}</div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign out", key="nav_logout", use_container_width=True):
        auth_service.logout()
        st.switch_page("pages/00_login.py")


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## Step 3 — Sidebar CSS additions to `shared_css.py`

Add to the existing CSS string in `inject_shared_css()`. Variables `--violet`, `--bg-card`, `--border-default`, `--text-*`, `--font-display` already exist in the cosmic theme.

```css
/* ============ Sidebar (sidebar_nav) ============ */
[data-testid="stSidebar"] {
  width: 240px !important;
  min-width: 240px !important;
  background: var(--bg-card-strong, rgba(7,9,26,0.85)) !important;
  backdrop-filter: blur(18px) !important;
  border-right: 1px solid var(--border-subtle) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 16px 12px; }

.sn-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 8px 14px; margin-bottom: 6px;
  border-bottom: 1px solid var(--border-subtle);
}
.sn-mark {
  width: 30px; height: 30px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-radius: 8px; box-shadow: 0 0 18px rgba(139,92,246,0.5);
  display: grid; place-items: center;
  font-family: var(--font-display); font-size: 18px; font-style: italic; color: white;
}
.sn-name { font-family: var(--font-display); font-size: 21px; letter-spacing: 0.5px; }

.sn-label {
  font-family: var(--font-body); font-size: 10.5px;
  font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text-faint); padding: 14px 10px 6px;
}

/* Streamlit buttons in sidebar — restyle as nav items */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--text-secondary) !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 8px 10px !important;
  font-size: 13.5px !important;
  font-weight: 400 !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  transition: all 0.18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(139,92,246,0.08) !important;
  color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stButton > button:disabled {
  opacity: 0.45 !important; cursor: not-allowed !important;
}

/* Pipeline muted block */
.sn-pipeline-muted {
  margin: 4px 10px;
  padding: 14px 12px;
  background: rgba(139,92,246,0.04);
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
}
.sn-muted-text {
  font-size: 11.5px; line-height: 1.4; color: var(--text-muted); text-align: center;
}

/* Active project context card */
.sn-project-context {
  margin: 4px 6px 8px;
  padding: 10px 12px;
  background: rgba(139,92,246,0.08);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}
.sn-context-label {
  font-size: 9.5px; color: var(--text-faint);
  letter-spacing: 1.2px; text-transform: uppercase;
  font-family: var(--font-mono);
}
.sn-context-name {
  font-size: 13px; color: var(--text-primary); font-weight: 500; margin-top: 3px;
}

/* Pipeline step markers — visually attach status dot to the button BEFORE this marker.
   Streamlit renders our markdown after the button, so we use sibling selectors. */
[data-testid="stSidebar"] .stButton:has(+ div[data-step]) > button { padding-left: 30px !important; position: relative; }
[data-testid="stSidebar"] div[data-step] {
  position: relative; height: 0; overflow: visible;
  margin-top: -34px; margin-bottom: 30px; pointer-events: none;
}
[data-testid="stSidebar"] div[data-step]::before {
  content: "";
  position: absolute; left: 14px; top: 16px;
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--bg-elev); border: 1.5px solid var(--text-faint);
  z-index: 5;
}
[data-testid="stSidebar"] div[data-status="done"]::before {
  background: var(--green); border-color: var(--green);
  box-shadow: 0 0 10px rgba(52,211,153,0.5);
}
[data-testid="stSidebar"] div[data-status="active"]::before {
  background: var(--violet); border-color: var(--violet);
  box-shadow: 0 0 0 3px rgba(139,92,246,0.25), 0 0 16px rgba(139,92,246,0.6);
  animation: sn-pulse 1.8s ease-in-out infinite;
}
@keyframes sn-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(139,92,246,0.25), 0 0 16px rgba(139,92,246,0.6); }
  50%      { box-shadow: 0 0 0 6px rgba(139,92,246,0.12), 0 0 22px rgba(139,92,246,0.8); }
}

/* Footer / user chip */
.sn-footer { padding: 14px 6px 4px; border-top: 1px solid var(--border-subtle); margin-top: 12px; }
.sn-user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 10px;
  background: rgba(139,92,246,0.06); border: 1px solid var(--border-subtle);
}
.sn-user-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, var(--indigo), var(--purple));
  display: grid; place-items: center;
  font-size: 12px; font-weight: 600; color: white;
}
.sn-user-name { font-size: 13px; color: var(--text-primary); }
.sn-user-email { font-size: 10.5px; color: var(--text-muted); }
```

## Step 4 — Render in every page

Each page must call `sidebar_nav.render()` at the top after `inject_shared_css()`.

In `dashboard/app.py`:

```python
from dashboard.components.sidebar_nav import render as render_sidebar
# … after inject_shared_css() …
render_sidebar()
```

Same pattern in pages 01–09 (one line addition each).

## Implementation notes

- The `:has(+ ...)` selector is supported in modern Chromium and Firefox. If older browsers must work, replace with a simpler approach: render the dot inline in the button label using emoji (`✅ Upload`, `⏳ EDA`, `⚪ Features`) — this is the fallback if CSS sibling selectors get tricky in Streamlit's DOM.
- Streamlit re-renders the entire sidebar on every interaction, so all state lives in `st.session_state` / project_service — no local mutable state in this module.
- `st.switch_page()` is required for the navigation to work with Streamlit's multipage app system.
