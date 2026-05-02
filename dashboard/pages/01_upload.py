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


def _is_streamlit_running() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if not _is_streamlit_running():
    pass
else:
    st.set_page_config(
        page_title="AutoDS — Upload",
        page_icon="⬆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_shared_css()

    # ---- auth gate ----
    if not auth_service.is_authenticated():
        st.switch_page("pages/00_login.py")
        st.stop()

    render_sidebar()

    project = project_service.get_active()
    if project is None:
        project = project_service.create(name="My Analysis")
        project_service.set_active(project.id)
        project = project_service.get_active()

    # ---- callback: when any source successfully loads data ----
    def _handle_data_loaded(df, meta: dict) -> None:
        """Wire the dataframe + metadata into project state and session state."""
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

    # ---- honor pending_sample_dataset set by home page ----
    pending_sample = st.session_state.pop("pending_sample_dataset", None)
    if pending_sample:
        try:
            from data_connectors.direct_input.sample_datasets import SampleDatasetConnector
            connector = SampleDatasetConnector()
            df_sample = connector.load({"dataset_name": pending_sample})
            meta_sample = {
                "filename": f"{pending_sample}.csv",
                "format": "csv",
                "encoding": "UTF-8",
                "source_type": "sample",
                "source_provider": "built-in",
            }
            _handle_data_loaded(df_sample, meta_sample)
        except Exception as e:
            st.error(f"Failed to auto-load sample {pending_sample}: {e}")

    # ---- breadcrumb ----
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
        '  <p>Drop a file, connect a database, pull from cloud storage, or fetch from an API. '
        '     AutoDS supports 30+ sources and auto-joins multiple tables when you need them.</p>'
        '</section>',
        unsafe_allow_html=True,
    )

    # ---- tab switcher ----
    active_panel = render_tabs()

    # ---- recent uploads ----
    render_recent(on_loaded=_handle_data_loaded)

    # ---- active source panel ----
    if active_panel == "manual":
        render_manual(on_loaded=_handle_data_loaded)
    elif active_panel == "cloud":
        render_cloud(on_loaded=_handle_data_loaded)
    elif active_panel == "database":
        render_database(on_loaded=_handle_data_loaded)
    elif active_panel == "api":
        render_api(on_loaded=_handle_data_loaded)

    # ---- multi-source join (always visible) ----
    render_multisource()

    # ---- sample gallery ----
    render_samples(on_loaded=_handle_data_loaded)

    # ---- post-upload preview ----
    df = st.session_state.get("df")
    meta = st.session_state.get("upload_meta", {})
    if df is not None and not df.empty:
        sources_joined = max(1, len([
            f for f in st.session_state.get("multisource", {}).get("files", [])
            if f["role"] in ("primary", "secondary")
        ]))
        render_preview(df, meta, sources_joined=sources_joined)
