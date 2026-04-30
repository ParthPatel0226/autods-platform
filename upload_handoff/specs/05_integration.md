# Spec 05 — Page Integration & Pipeline Wiring

## Goal

Replace `dashboard/pages/01_upload.py` with a new orchestrator that uses all the components built in specs 01–04.

## File: `dashboard/pages/01_upload.py` (full rewrite)

```python
"""Upload tab — connect or load data from any of 4 source types,
manage multi-source joins, and review the loaded dataset before continuing."""
from __future__ import annotations
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar

from dashboard.components.up_source_tabs import render as render_tabs
from dashboard.components.up_panel_manual import render as render_manual
from dashboard.components.up_panel_cloud import render as render_cloud
from dashboard.components.up_panel_database import render as render_database
from dashboard.components.up_panel_api import render as render_api
from dashboard.components.up_recent_uploads import render as render_recent
from dashboard.components.up_multisource_join import render as render_multisource
from dashboard.components.up_sample_gallery import render as render_samples
from dashboard.components.up_post_preview import render as render_preview


st.set_page_config(
    page_title="AutoDS — Upload",
    page_icon="⬆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_shared_css()

# ---- gates ----
if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py")
    st.stop()

render_sidebar()

project = project_service.get_active()
if project is None:
    st.warning("Open a project from the home page to continue.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()

# ---- breadcrumb + theme toggle area ----
top_cols = st.columns([8, 1])
with top_cols[0]:
    st.markdown(
        f'<div class="up-crumbs">'
        f'  <span>{project.name}</span>'
        f'  <span class="sep">/</span>'
        f'  <span class="cur">Upload</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ---- hero ----
st.markdown(
    '<section class="up-hero">'
    '  <div class="up-hero-eyebrow">⬆ Step 1 of 7 — Data Ingestion</div>'
    '  <h1>Connect your <em>data source.</em></h1>'
    '  <p>Drop a file, connect a database, pull from cloud storage, or fetch from an API.'
    '     AutoDS supports 30+ sources and auto-joins multiple tables when you need them.</p>'
    '</section>',
    unsafe_allow_html=True,
)

# ---- tab switcher ----
active_panel = render_tabs()

# ---- recent uploads (above panels) ----
render_recent(on_loaded=_handle_data_loaded := None)  # placeholder; real callable defined below

# ---- callback: when any source successfully loads data ----
def _handle_data_loaded(df, meta: dict) -> None:
    """Wire the dataframe + metadata into project state and session state."""
    st.session_state["df"] = df
    st.session_state["upload_meta"] = meta

    # If the multi-source manager has built a joined frame, use that as the canonical df instead
    msm_state = st.session_state.get("multisource", {})
    if msm_state.get("joined_df_id"):
        sources_joined = len([f for f in msm_state.get("files", []) if f["role"] in ("primary", "secondary")])
    else:
        sources_joined = 1

    # Update the active project record
    if project is not None:
        project.dataset_name = meta.get("filename", "dataset")
        project.dataset_path = meta.get("source_path") or meta.get("path")
        project.n_rows = len(df)
        project.n_cols = len(df.columns)
        # Mark upload as in-progress (not done until they hit Continue)
        if project.step_status.get("upload") == "pending":
            project.step_status["upload"] = "active"
        project_service.update(project)

# Re-render recent and source panels with the real callback
# (Streamlit doesn't allow forward-referencing inside the callback definition above,
# so we re-call the components below now that _handle_data_loaded is defined.)
# The component calls above this point with `None` are no-ops because they branch
# on whether on_loaded is callable. To keep the flow clean, structure it like:

# Better: just define the callback above the components.
```

Above shows the structural intent — Streamlit doesn't allow the deferred-definition pattern. Use this concrete order instead:

```python
# Define callback FIRST
def _handle_data_loaded(df, meta: dict) -> None:
    st.session_state["df"] = df
    st.session_state["upload_meta"] = meta
    if project is not None:
        project.dataset_name = meta.get("filename", "dataset")
        project.dataset_path = meta.get("source_path") or meta.get("path")
        project.n_rows = len(df)
        project.n_cols = len(df.columns)
        if project.step_status.get("upload") == "pending":
            project.step_status["upload"] = "active"
        project_service.update(project)


# Render in correct order
active_panel = render_tabs()
render_recent(on_loaded=_handle_data_loaded)

if active_panel == "manual":
    render_manual(on_loaded=_handle_data_loaded)
elif active_panel == "cloud":
    render_cloud(on_loaded=_handle_data_loaded)
elif active_panel == "database":
    render_database(on_loaded=_handle_data_loaded)
elif active_panel == "api":
    render_api(on_loaded=_handle_data_loaded)

# Multi-source (always visible, may be empty)
render_multisource()

# Sample gallery
render_samples(on_loaded=_handle_data_loaded)

# Post-upload preview — only if we have data
df = st.session_state.get("df")
meta = st.session_state.get("upload_meta", {})
if df is not None and not df.empty:
    sources_joined = max(1, len([
        f for f in st.session_state.get("multisource", {}).get("files", [])
        if f["role"] in ("primary", "secondary")
    ]))
    render_preview(df, meta, sources_joined=sources_joined)
```

## Hero CSS additions

```css
/* ============ Upload hero + crumbs ============ */
.up-crumbs {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-muted); letter-spacing: 0.4px; margin-bottom: 24px;
}
.up-crumbs .sep { color: var(--text-faint); }
.up-crumbs .cur { color: var(--text-primary); }

.up-hero { margin-bottom: 36px; }
.up-hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 8px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 11.5px; color: var(--text-secondary); margin-bottom: 18px;
  backdrop-filter: blur(12px); font-family: var(--font-mono);
  letter-spacing: 0.6px; text-transform: uppercase;
}
.up-hero h1 { font-family: var(--font-display); font-size: 56px;
              line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px;
              color: var(--text-primary); }
.up-hero h1 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.up-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }
```

## Honoring `session_state["upload_panel"]` from home page

The home page sets `st.session_state["upload_panel"]` to one of `"manual"`, `"cloud"`, `"database"`, or `"api"` when the user clicks a data source tile. The new `up_source_tabs.render()` reads this key, so the right panel opens automatically. No extra wiring needed.

## Honoring `session_state["pending_sample_dataset"]`

If set, auto-trigger the sample loader on first render. Add at the top of `01_upload.py` (after the gates):

```python
pending_sample = st.session_state.pop("pending_sample_dataset", None)
if pending_sample:
    try:
        from data_connectors.direct_input import sample_datasets
        df = sample_datasets.get_sample(pending_sample)  # ADAPT to actual fn
        meta = {
            "filename": f"{pending_sample}.csv",
            "format": "csv",
            "encoding": "UTF-8",
            "source_type": "sample",
            "source_provider": "built-in",
        }
        _handle_data_loaded(df, meta)  # define this above the trigger
    except Exception as e:
        st.error(f"Failed to load sample {pending_sample}: {e}")
```

## Pipeline state writes

| When | What is written |
|---|---|
| File loads (any source) | `df`, `upload_meta`, `project.dataset_name`, `project.dataset_path`, `project.n_rows`, `project.n_cols`, `project.step_status['upload'] = 'active'` |
| Multi-source join executes | `df` replaced by joined frame, `multisource.joined_df_id` set |
| Domain detection runs | `project.detected_domain`, `project.metric_summary` (confidence text) |
| User clicks "Continue to Configure" | `project.step_status['upload'] = 'done'`, `project.step_status['configure'] = 'active'` |

These updates make the sidebar tracker (from spec 03 of the home handoff) animate the correct steps.

## Test plan

1. **Smoke test:** boot → home → New Project → click "Manual upload" tile → upload Titanic → see post-preview → click "Continue to Configure" → land on configure page with sidebar showing Upload ✅, Configure ⏳ (pulsing).

2. **Each panel test:** for each of the 4 panels, verify form validation, "Test connection" feedback, and successful load. For panels needing real services (cloud / db / api), use a mock or skip.

3. **Multi-source test:** upload `patients.csv`, expand Multi-source, add `visits.csv`, confirm primary auto-set. Click "Build joined dataset" → verify joined_df_id set, joined frame replaces `df`. Switch primary → secondary roles → re-detect joins.

4. **Sample test:** click "Load Iris" → df loads → preview renders.

5. **Recent test:** upload a file → return home → return to upload → recent strip shows that file.

6. **Theme test:** swap to light mode → all panels (including providers, drop zone, multi-source files, sample cards, preview, schema table) render correctly with no leaked dark colors.

7. **Regression:** `pytest tests/` passes. The integration test `tests/integration/test_full_pipeline.py` may need a fixture update — instead of writing to `st.session_state['df']` directly, it should now go through `_handle_data_loaded` or seed the active project. Coordinate with the test owner if it breaks.

## Sequence diagram (load flow)

```
[user] → click tab          → up_source_tabs sets session_state["upload_panel"] → rerun
[user] → drop CSV           → up_panel_manual.universal_load → _handle_data_loaded
                            → project_service.update(project)
                            → st.session_state["df"] / "upload_meta"
[user] → expand multi-source → up_multisource_join.render → MultiSourceManager.add_source
[user] → click "Build join"  → MultiSourceManager.execute_joins → state["joined_df_id"]
[user] → click "Continue"    → step_status updates → switch_page("02_configure.py")
```

## Final reminder

Do NOT modify:
- `data_connectors/**`
- `domains/**`
- `agents/**`
- pages 02–09

Verify before changing anything in:
- `multi_source_manager.py` interface (spec 02 assumes specific method names)
- `schema_matcher.detect_join_keys` return shape (spec 02)
- `sample_datasets.get_sample` function name (spec 04)
- `domain_registry.detect_domain` return shape (spec 03)

If those interfaces don't match the assumptions, write an adapter shim in `dashboard/components/up_*_adapter.py` rather than editing the backend module.
