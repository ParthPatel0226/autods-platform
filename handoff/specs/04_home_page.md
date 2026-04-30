# Spec 04 — Home Page (`app.py` refactor + state components)

## Goal

Strip the current marketing content from `dashboard/app.py` and replace with a context-aware home that routes between two states:

- **State A — first-time user** (no projects exist): welcome + 5-step onboarding checklist + 4-tile data source launcher + sample dataset chips
- **State B — returning user** (1+ projects): grid of project cards + "New Project" button + collapsible quick-start strip

## File: `dashboard/app.py` (refactored)

```python
"""AutoDS — Streamlit entry point.

Hosts the home page (first-time / returning user states) and acts as the
auth gate. Pipeline pages live in dashboard/pages/.
"""
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar
from dashboard.components.home_first_time import render as render_first_time
from dashboard.components.home_returning import render as render_returning

st.set_page_config(
    page_title="AutoDS — Autonomous Data Science",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_shared_css()

# Auth gate
if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py")
    st.stop()

render_sidebar()

# Determine which home state to render.
# Default: auto by project count. Override via st.session_state["home_view"]:
#   "projects" → force returning view
#   "onboarding" → force first-time view
projects = project_service.list_all(user_id=auth_service.current_user()["id"])
view_override = st.session_state.get("home_view")

if view_override == "projects":
    render_returning(projects)
elif view_override == "onboarding":
    render_first_time()
elif len(projects) == 0:
    render_first_time()
else:
    render_returning(projects)
```

## File: `dashboard/components/onboarding_checklist.py`

```python
"""Onboarding checklist — 5 steps with click-to-navigate."""
from __future__ import annotations
import streamlit as st


STEPS = [
    {"num": "01", "title": "Create your first project",
     "desc": "Name it, give it a purpose, and we'll keep everything organized for you.",
     "action_label": "Start", "action": "new_project"},
    {"num": "02", "title": "Upload a dataset or connect a source",
     "desc": "CSV, Excel, Parquet, S3, BigQuery, Snowflake — 30+ data sources supported.",
     "action_label": "Open", "action": "upload"},
    {"num": "03", "title": "Configure your analysis",
     "desc": "Confirm the auto-detected domain, pick a target, and choose Auto / Guided / Expert mode.",
     "action_label": "Open", "action": "configure"},
    {"num": "04", "title": "Run EDA and feature engineering",
     "desc": "Walk through interactive, domain-aware questions to shape your dataset.",
     "action_label": "Open", "action": "eda"},
    {"num": "05", "title": "Train a model and download your report",
     "desc": "SHAP explanations, fairness audits, and one-click HTML/PDF/Notebook export.",
     "action_label": "Open", "action": "modeling"},
]


def render(completed_steps: list[str] | None = None, current_step: str | None = None,
           on_action) -> None:
    """Render the checklist. on_action is a callable(action_id) -> None."""
    completed_steps = completed_steps or []

    st.markdown('<div class="oc-list">', unsafe_allow_html=True)
    for step in STEPS:
        is_complete = step["action"] in completed_steps
        is_current = step["action"] == current_step and not is_complete
        cls = "oc-item"
        if is_complete:
            cls += " oc-complete"
        elif is_current:
            cls += " oc-current"
        st.markdown(
            f'<div class="{cls}">'
            f'  <div class="oc-bullet">{"✓" if is_complete else step["num"]}</div>'
            f'  <div class="oc-content">'
            f'    <div class="oc-title">{step["title"]}</div>'
            f'    <div class="oc-desc">{step["desc"]}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if is_current or is_complete:
            cols = st.columns([6, 1])
            with cols[1]:
                if st.button(step["action_label"], key=f"oc_action_{step['action']}",
                            use_container_width=True):
                    on_action(step["action"])
    st.markdown('</div>', unsafe_allow_html=True)
```

## File: `dashboard/components/data_source_launcher.py`

```python
"""4-tile data source launcher — Manual / Cloud / Database / API & Web."""
from __future__ import annotations
import streamlit as st


TILES = [
    {"key": "manual", "title": "Manual upload",
     "desc": "Drag a file from your computer — CSV, Excel, Parquet, JSON, or TSV.",
     "tags": ["CSV", "XLSX", "PARQUET", "JSON"],
     "icon": "📁",
     "target_panel": "manual"},
    {"key": "cloud", "title": "Cloud storage",
     "desc": "Pull data directly from object storage — bucket-level or file-level.",
     "tags": ["S3", "GCS", "AZURE"],
     "icon": "☁️",
     "target_panel": "cloud"},
    {"key": "database", "title": "Database",
     "desc": "Connect a warehouse with read-only credentials and run queries directly.",
     "tags": ["POSTGRES", "BIGQUERY", "SNOWFLAKE", "+4"],
     "icon": "🗄️",
     "target_panel": "database"},
    {"key": "api", "title": "API & Web",
     "desc": "REST APIs, public data portals, Kaggle, HuggingFace, or scrape a URL.",
     "tags": ["REST", "KAGGLE", "FRED", "+5"],
     "icon": "🌐",
     "target_panel": "api"},
]

SAMPLE_DATASETS = [
    ("Titanic",            "CLASSIFICATION", "titanic"),
    ("Heart Disease",      "HEALTHCARE",     "heart_disease"),
    ("Credit Risk",        "FINANCE",        "credit_risk"),
    ("Online Retail",      "E-COMMERCE",     "online_retail"),
    ("Attrition",          "HR",             "attrition"),
    ("Pred. Maintenance",  "MANUFACTURING",  "predictive_maintenance"),
]


def render(on_tile_click, on_sample_click, *, require_project: bool = True) -> None:
    """on_tile_click(panel_key) and on_sample_click(dataset_key) are callables."""
    cols = st.columns(4, gap="medium")
    for i, tile in enumerate(TILES):
        with cols[i]:
            st.markdown(
                f'<div class="ds-card">'
                f'  <div class="ds-icon">{tile["icon"]}</div>'
                f'  <div class="ds-title">{tile["title"]}</div>'
                f'  <div class="ds-desc">{tile["desc"]}</div>'
                f'  <div class="ds-tags">'
                + "".join(f'<span class="ds-tag">{t}</span>' for t in tile["tags"])
                + '  </div>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"ds_open_{tile['key']}", use_container_width=True):
                on_tile_click(tile["target_panel"])

    st.markdown('<div class="ds-sample-strip-label">Or try a sample dataset</div>',
                unsafe_allow_html=True)
    sample_cols = st.columns(len(SAMPLE_DATASETS), gap="small")
    for i, (label, tag, key) in enumerate(SAMPLE_DATASETS):
        with sample_cols[i]:
            if st.button(f"{label}\n{tag}", key=f"sample_{key}", use_container_width=True):
                on_sample_click(key)
```

## File: `dashboard/components/home_first_time.py`

```python
"""First-time user home view — welcome + checklist + data sources."""
from __future__ import annotations
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.onboarding_checklist import render as render_checklist
from dashboard.components.data_source_launcher import render as render_launcher


def render() -> None:
    user = auth_service.current_user()
    name = user.get("name", "there") if user else "there"

    # Hero
    st.markdown(
        '<div class="home-hero">'
        '  <div class="home-status-chip">'
        '    <span class="home-status-dot"></span>'
        f'    <span>Welcome, {_html_escape(name)} — let\'s get you started</span>'
        '  </div>'
        '  <h1 class="home-title">Build your first<br/><em>analysis project.</em></h1>'
        '  <p class="home-subtitle">Five quick steps from raw data to a trained model with explainable insights. Pick up where you leave off — every project is saved automatically.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Checklist
    st.markdown('<h2 class="home-section-title">Onboarding <em>checklist</em></h2>'
                '<p class="home-section-subtitle">Complete each step to unlock the next stage of your pipeline.</p>',
                unsafe_allow_html=True)
    render_checklist(
        completed_steps=[],
        current_step="new_project",
        on_action=_handle_checklist_action,
    )

    # Data sources
    st.markdown('<h2 class="home-section-title">Start with your <em>data</em></h2>'
                '<p class="home-section-subtitle">Upload from your machine, connect a database, or pull from cloud storage.</p>',
                unsafe_allow_html=True)
    render_launcher(
        on_tile_click=_handle_source_click,
        on_sample_click=_handle_sample_click,
    )


def _handle_checklist_action(action: str) -> None:
    if action == "new_project":
        _open_new_project_modal()
    elif action == "upload":
        _ensure_project_then_go("pages/01_upload.py")
    elif action == "configure":
        _ensure_project_then_go("pages/02_configure.py")
    elif action == "eda":
        _ensure_project_then_go("pages/03_eda_interactive.py")
    elif action == "modeling":
        _ensure_project_then_go("pages/05_modeling.py")


def _handle_source_click(panel: str) -> None:
    # Stash which panel to open on the upload page, then navigate.
    st.session_state["upload_panel"] = panel
    _ensure_project_then_go("pages/01_upload.py")


def _handle_sample_click(dataset_key: str) -> None:
    st.session_state["pending_sample_dataset"] = dataset_key
    _ensure_project_then_go("pages/01_upload.py")


def _ensure_project_then_go(page_path: str) -> None:
    if not project_service.get_active():
        _open_new_project_modal(then_go=page_path)
        return
    st.switch_page(page_path)


def _open_new_project_modal(then_go: str | None = None) -> None:
    """Use st.dialog if available (Streamlit 1.30+), else inline form."""
    st.session_state["_new_project_modal"] = True
    st.session_state["_new_project_target"] = then_go or "pages/01_upload.py"
    st.rerun()


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/home_returning.py`

```python
"""Returning user home view — project grid + new project + quick start."""
from __future__ import annotations
from datetime import datetime, timezone
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.project_service import Project, PIPELINE_STEPS, PIPELINE_LABELS_DISPLAY
from dashboard.components.data_source_launcher import render as render_launcher


DOMAIN_BADGES = {
    "healthcare":     ("🏥 Healthcare",     "ds-badge-healthcare"),
    "finance":        ("💳 Finance",        "ds-badge-finance"),
    "ecommerce":      ("🛒 E-commerce",     "ds-badge-ecommerce"),
    "hr":             ("👥 HR",             "ds-badge-hr"),
    "marketing":      ("📣 Marketing",      "ds-badge-generic"),
    "manufacturing":  ("⚙️ Manufacturing",  "ds-badge-generic"),
    "generic":        ("📊 Generic",        "ds-badge-generic"),
}


def render(projects: list[Project]) -> None:
    user = auth_service.current_user()
    name = user.get("name", "there") if user else "there"

    # Header
    cols = st.columns([5, 1])
    with cols[0]:
        st.markdown(
            f'<div class="home-returning-header">'
            f'  <h1 class="home-title">Your <em>projects.</em></h1>'
            f'  <p class="home-subtitle">Welcome back, {_html_escape(name)} — pick up where you left off.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        if st.button("＋ New Project", key="new_project_btn", type="primary", use_container_width=True):
            _open_new_project_modal()

    _render_new_project_modal_if_open()

    # Filter bar
    filter_cols = st.columns([2, 1])
    with filter_cols[0]:
        search = st.text_input("Search", placeholder="Search projects…", label_visibility="collapsed")
    with filter_cols[1]:
        sort = st.selectbox("Sort", ["Last updated", "Recently created", "Alphabetical", "Status"],
                            label_visibility="collapsed")

    # Apply search/sort
    items = [p for p in projects if not search or search.lower() in p.name.lower()]
    if sort == "Recently created":
        items.sort(key=lambda p: p.created_at, reverse=True)
    elif sort == "Alphabetical":
        items.sort(key=lambda p: p.name.lower())
    elif sort == "Status":
        order = {"in_progress": 0, "new": 1, "complete": 2}
        items.sort(key=lambda p: order.get(p.status, 3))

    if not items:
        st.info("No projects match your search. Try a different query or start a new project.")
    else:
        _render_project_grid(items)

    # Quick start strip
    st.markdown('<div class="home-quickstart">'
                '<h2 class="home-section-title" style="font-size:22px;">Or start something <em>new</em></h2>'
                '</div>',
                unsafe_allow_html=True)
    render_launcher(
        on_tile_click=lambda panel: _new_project_with_panel(panel),
        on_sample_click=lambda key: _new_project_with_sample(key),
    )


def _render_project_grid(projects: list[Project]) -> None:
    # 3 columns desktop
    cols_per_row = 3
    for i in range(0, len(projects), cols_per_row):
        row_projects = projects[i:i + cols_per_row]
        cols = st.columns(cols_per_row, gap="medium")
        for col, p in zip(cols, row_projects):
            with col:
                _render_project_card(p)


def _render_project_card(p: Project) -> None:
    domain_key = (p.confirmed_domain or p.detected_domain or "generic").lower()
    badge_label, badge_cls = DOMAIN_BADGES.get(domain_key, DOMAIN_BADGES["generic"])
    status_label, status_cls = _status_pill(p)
    rel_time = _relative_time(p.updated_at)

    st.markdown(
        f'<div class="proj-card">'
        f'  <div class="proj-head">'
        f'    <div>'
        f'      <div class="proj-name">{_html_escape(p.name)}</div>'
        f'      <div class="proj-dataset">{_html_escape(p.dataset_name or "—")}'
        f'      {"· " + format(p.n_rows or 0, ",") + " rows" if p.n_rows else ""}</div>'
        f'    </div>'
        f'    <div class="proj-badge {badge_cls}">{badge_label}</div>'
        f'  </div>'
        f'  <div class="proj-status"><span class="proj-status-pill {status_cls}">{status_label}</span></div>'
        f'  <div class="proj-progress"><div class="proj-progress-fill" style="width:{p.progress_pct}%"></div></div>'
        f'  <div class="proj-progress-meta"><span>{p.steps_done} / {len(PIPELINE_STEPS)} steps</span><span>{p.progress_pct}%</span></div>'
        f'  <div class="proj-footer"><div class="proj-time">Updated {rel_time}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([2, 1, 1])
    with btn_cols[0]:
        if st.button("Open", key=f"proj_open_{p.id}", use_container_width=True, type="primary"):
            project_service.set_active(p.id)
            target = _resume_target(p)
            st.switch_page(target)
    with btn_cols[1]:
        if st.button("⋯", key=f"proj_menu_{p.id}", use_container_width=True,
                     help="More actions"):
            st.session_state[f"_show_actions_{p.id}"] = not st.session_state.get(f"_show_actions_{p.id}", False)
    with btn_cols[2]:
        if st.button("🗑", key=f"proj_del_{p.id}", use_container_width=True,
                     help="Delete project"):
            st.session_state[f"_confirm_delete_{p.id}"] = True
    if st.session_state.get(f"_confirm_delete_{p.id}"):
        st.warning(f"Delete '{p.name}'? This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm delete", key=f"confirm_yes_{p.id}", use_container_width=True):
                project_service.delete(p.id)
                st.session_state.pop(f"_confirm_delete_{p.id}", None)
                st.rerun()
        with c2:
            if st.button("Cancel", key=f"confirm_no_{p.id}", use_container_width=True):
                st.session_state.pop(f"_confirm_delete_{p.id}", None)
                st.rerun()


def _resume_target(p: Project) -> str:
    """Where to send the user when they open a project."""
    page_for_step = {
        "upload":         "pages/01_upload.py",
        "configure":      "pages/02_configure.py",
        "eda":            "pages/03_eda_interactive.py",
        "features":       "pages/04_feature_engineering.py",
        "modeling":       "pages/05_modeling.py",
        "explainability": "pages/06_explainability.py",
        "predict":        "pages/07_predict.py",
    }
    step = p.current_step or "upload"
    return page_for_step.get(step, "pages/01_upload.py")


def _status_pill(p: Project) -> tuple[str, str]:
    if p.status == "complete":
        label = f"Complete{' · ' + p.metric_summary if p.metric_summary else ''}"
        return label, "proj-status-complete"
    if p.status == "new":
        return "Just started", "proj-status-new"
    # Map current step to a friendly verb
    step = p.current_step or "configure"
    verb = {
        "upload":         "Uploading",
        "configure":      "Configuring",
        "eda":            "EDA In Progress",
        "features":       "Engineering Features",
        "modeling":       "Training Models",
        "explainability": "Generating Explanations",
        "predict":        "Predicting",
    }.get(step, "In Progress")
    return verb, "proj-status-in-progress"


def _relative_time(iso: str) -> str:
    try:
        t = datetime.fromisoformat(iso.replace("Z", ""))
    except ValueError:
        return "recently"
    delta = datetime.utcnow() - t
    s = int(delta.total_seconds())
    if s < 60: return "just now"
    if s < 3600: return f"{s // 60} min ago"
    if s < 86400: return f"{s // 3600} hr ago"
    if s < 604800: return f"{s // 86400} day{'s' if s // 86400 != 1 else ''} ago"
    if s < 2592000: return f"{s // 604800} week{'s' if s // 604800 != 1 else ''} ago"
    return f"{s // 2592000} month{'s' if s // 2592000 != 1 else ''} ago"


def _open_new_project_modal() -> None:
    st.session_state["_new_project_modal"] = True
    st.session_state["_new_project_target"] = "pages/01_upload.py"
    st.rerun()


def _new_project_with_panel(panel: str) -> None:
    st.session_state["upload_panel"] = panel
    _open_new_project_modal()


def _new_project_with_sample(key: str) -> None:
    st.session_state["pending_sample_dataset"] = key
    _open_new_project_modal()


def _render_new_project_modal_if_open() -> None:
    if not st.session_state.get("_new_project_modal"):
        return
    # Use st.dialog if available, else inline expander
    @st.dialog("Create a new project")
    def _modal():
        st.write("Give your project a name. You can always rename it later.")
        name = st.text_input("Project name", placeholder="e.g., Q4 customer churn")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Cancel", use_container_width=True):
                st.session_state.pop("_new_project_modal", None)
                st.rerun()
        with c2:
            if st.button("Create", type="primary", use_container_width=True, disabled=not name.strip()):
                user = auth_service.current_user()
                p = project_service.create(name.strip(), user_id=user["id"] if user else "local")
                target = st.session_state.pop("_new_project_target", "pages/01_upload.py")
                st.session_state.pop("_new_project_modal", None)
                st.switch_page(target)
    try:
        _modal()
    except Exception:
        # Fallback for Streamlit versions without st.dialog
        with st.expander("Create a new project", expanded=True):
            name = st.text_input("Project name", placeholder="e.g., Q4 customer churn",
                                 key="_inline_new_proj_name")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Cancel", key="_inline_cancel"):
                    st.session_state.pop("_new_project_modal", None)
                    st.rerun()
            with c2:
                if st.button("Create", key="_inline_create", type="primary",
                             disabled=not name.strip()):
                    user = auth_service.current_user()
                    p = project_service.create(name.strip(), user_id=user["id"] if user else "local")
                    target = st.session_state.pop("_new_project_target", "pages/01_upload.py")
                    st.session_state.pop("_new_project_modal", None)
                    st.switch_page(target)


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions to `shared_css.py`

```css
/* ============ Home — shared ============ */
.home-hero { padding: 8px 0 40px; }
.home-status-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 5px 14px 5px 10px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 999px; font-size: 12px; color: var(--text-secondary);
  backdrop-filter: blur(12px); margin-bottom: 22px;
}
.home-status-dot {
  width: 7px; height: 7px; background: var(--green); border-radius: 50%;
  box-shadow: 0 0 8px rgba(52,211,153,0.7); animation: sn-pulse 2s ease-in-out infinite;
}
.home-title {
  font-family: var(--font-display); font-size: 64px; line-height: 1;
  letter-spacing: -1px; margin-bottom: 14px; color: var(--text-primary);
}
.home-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.home-subtitle {
  font-size: 17px; color: var(--text-muted); max-width: 640px; line-height: 1.55;
}
.home-section-title {
  font-family: var(--font-display); font-size: 32px;
  margin: 36px 0 6px; color: var(--text-primary);
}
.home-section-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.home-section-subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: 24px; }

/* ============ Onboarding checklist ============ */
.oc-list {
  display: flex; flex-direction: column;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 8px; backdrop-filter: blur(20px);
  margin-bottom: 28px;
}
.oc-item {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 18px 20px; border-radius: 14px;
  transition: all 0.2s ease;
}
.oc-item + .oc-item { border-top: 1px solid var(--border-subtle); margin-top: 0; padding-top: 18px; }
.oc-item:hover { background: rgba(139,92,246,0.06); }
.oc-bullet {
  width: 28px; height: 28px; border-radius: 50%;
  border: 1.5px solid var(--text-faint);
  display: grid; place-items: center; flex-shrink: 0; margin-top: 2px;
  font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);
  background: var(--bg-elev);
}
.oc-current .oc-bullet {
  border-color: var(--violet); background: rgba(139,92,246,0.16);
  box-shadow: 0 0 0 4px rgba(139,92,246,0.15);
}
.oc-complete .oc-bullet {
  background: var(--green); border-color: var(--green); color: white;
  box-shadow: 0 0 14px rgba(52,211,153,0.35);
  font-size: 14px; font-weight: 700;
}
.oc-content { flex: 1; }
.oc-title { font-size: 15px; font-weight: 500; color: var(--text-primary); margin-bottom: 3px; }
.oc-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; }
.oc-complete .oc-title {
  color: var(--text-muted);
  text-decoration: line-through;
  text-decoration-color: rgba(132,137,174,0.4);
}

/* ============ Data source tiles ============ */
.ds-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 24px; transition: all 0.25s ease;
  backdrop-filter: blur(14px); height: 100%;
}
.ds-card:hover { transform: translateY(-3px); border-color: var(--border-strong);
                box-shadow: var(--shadow-glow); }
.ds-icon {
  width: 44px; height: 44px;
  background: rgba(139,92,246,0.12); border: 1px solid var(--border-default);
  border-radius: 12px; display: grid; place-items: center;
  font-size: 22px; margin-bottom: 16px;
}
.ds-title { font-size: 16px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; }
.ds-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 14px;
          min-height: 40px; }
.ds-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.ds-tag {
  font-family: var(--font-mono); font-size: 10px;
  padding: 3px 8px; background: rgba(139,92,246,0.08);
  border: 1px solid var(--border-subtle); border-radius: 999px; color: var(--text-secondary);
}
.ds-sample-strip-label {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-faint); margin: 30px 0 12px;
}

/* ============ Project cards (returning home) ============ */
.proj-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 22px;
  backdrop-filter: blur(14px); height: 100%;
  transition: all 0.25s ease;
}
.proj-card:hover { transform: translateY(-3px); border-color: var(--border-strong);
                  box-shadow: var(--shadow-glow); }
.proj-head { display: flex; justify-content: space-between; align-items: flex-start;
            margin-bottom: 12px; gap: 10px; }
.proj-name { font-size: 17px; font-weight: 500; color: var(--text-primary);
            line-height: 1.3; margin-bottom: 4px; }
.proj-dataset { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

.proj-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 999px;
  font-size: 11px; font-weight: 500; border: 1px solid; flex-shrink: 0;
}
.ds-badge-healthcare { color: #34D399; border-color: rgba(52,211,153,0.4); background: rgba(52,211,153,0.1); }
.ds-badge-finance    { color: #22D3EE; border-color: rgba(34,211,238,0.4); background: rgba(34,211,238,0.1); }
.ds-badge-ecommerce  { color: #FBBF24; border-color: rgba(251,191,36,0.4); background: rgba(251,191,36,0.1); }
.ds-badge-hr         { color: #EC4899; border-color: rgba(236,72,153,0.4); background: rgba(236,72,153,0.1); }
.ds-badge-generic    { color: #A855F7; border-color: rgba(168,85,247,0.4); background: rgba(168,85,247,0.1); }

.proj-status { margin: 14px 0 10px; }
.proj-status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 0.7px; text-transform: uppercase;
}
.proj-status-in-progress {
  color: var(--violet); background: rgba(139,92,246,0.1);
  border: 1px solid var(--border-default);
}
.proj-status-in-progress::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: var(--violet); animation: sn-pulse 1.6s ease-in-out infinite;
}
.proj-status-complete {
  color: var(--green); border: 1px solid rgba(52,211,153,0.4); background: rgba(52,211,153,0.08);
}
.proj-status-new {
  color: var(--text-muted); border: 1px solid var(--border-subtle); background: rgba(139,92,246,0.04);
}

.proj-progress {
  height: 4px; background: rgba(139,92,246,0.1);
  border-radius: 2px; overflow: hidden; margin-top: 14px;
}
.proj-progress-fill {
  height: 100%;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-radius: 2px; box-shadow: 0 0 8px rgba(139,92,246,0.5);
}
.proj-progress-meta {
  display: flex; justify-content: space-between;
  margin-top: 8px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted);
}
.proj-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border-subtle);
}
.proj-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

.home-quickstart { margin-top: 56px; padding-top: 32px; border-top: 1px solid var(--border-subtle); }
.home-returning-header { margin-bottom: 8px; }

/* Responsive */
@media (max-width: 900px) {
  .home-title { font-size: 44px !important; }
}
```

## Note on `PIPELINE_LABELS_DISPLAY`

In `project_service.py`, also export:

```python
PIPELINE_LABELS_DISPLAY = {
    "upload": "Upload", "configure": "Configure", "eda": "EDA",
    "features": "Features", "modeling": "Modeling",
    "explainability": "Explainability", "predict": "Predict",
}
```

So home_returning can import it without circular imports.
