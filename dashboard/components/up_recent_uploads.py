"""Recent uploads pill strip — shows last few files for fast re-pick."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render(on_loaded) -> None:
    """Render the recent uploads strip. Hidden if user has no recent files."""
    recent = project_service.get_recent_files(limit=5)
    if not recent:
        return

    st.markdown(
        '<div class="up-recent-strip">'
        '<div class="up-strip-label">Recent uploads</div>'
        '<div class="up-recent-grid">',
        unsafe_allow_html=True,
    )
    for entry in recent:
        filename = entry.get("dataset_name") or entry.get("filename", "file")
        project_id = entry.get("project_id", "")
        btn_key = f"up_recent_{filename}_{project_id[:6]}"
        if st.button(
            f"\U0001f4c4 {filename}",
            key=btn_key,
        ):
            _load_recent(entry, on_loaded)
    st.markdown('</div></div>', unsafe_allow_html=True)


def _load_recent(entry: dict, on_loaded) -> None:
    from data_connectors.universal_loader import smart_load
    path = entry.get("dataset_path") or entry.get("path", "")
    filename = entry.get("dataset_name") or entry.get("filename", "file")
    try:
        with st.spinner(f"Reloading {filename}\u2026"):
            df, meta = smart_load(path)
            meta = {**(meta or {}), "filename": filename,
                    "size_bytes": entry.get("size_bytes", 0),
                    "source_type": "recent",
                    "source_path": path}
            on_loaded(df, meta)
            st.success(f"Reloaded {filename}")
    except FileNotFoundError:
        st.error(f"File no longer exists at {path}")
    except Exception as e:
        st.error(f"Failed to reload: {e}")
