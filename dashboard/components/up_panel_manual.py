"""Manual upload panel — drag-drop file uploader + format chips."""
from __future__ import annotations
import streamlit as st

from data_connectors.universal_loader import smart_load


SUPPORTED_FORMATS = ["csv", "tsv", "xlsx", "xls", "parquet", "json", "jsonl", "feather"]


def render(on_loaded) -> None:
    """Render the manual upload panel.
    on_loaded(df, meta) is called when a file successfully loads.
    """
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown(
            '<div class="up-drop-zone">'
            '  <div class="up-drop-icon">'
            '    <svg width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
            '      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '      <polyline points="17 8 12 3 7 8"/>'
            '      <line x1="12" y1="3" x2="12" y2="15"/>'
            '    </svg>'
            '  </div>'
            '  <div class="up-drop-title">Drag and drop, or click to browse</div>'
            '  <div class="up-drop-sub">Up to 200 MB per file</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload file",
            type=SUPPORTED_FORMATS,
            label_visibility="collapsed",
            key="up_manual_uploader",
        )

        chips_html = "".join(
            f'<span class="up-fmt-chip">{f.upper()}</span>' for f in SUPPORTED_FORMATS
        )
        st.markdown(f'<div class="up-fmt-chips">{chips_html}</div>', unsafe_allow_html=True)

        if uploaded is not None:
            file_key = f"_up_manual_loaded_{uploaded.name}_{uploaded.size}"
            if not st.session_state.get(file_key):
                with st.spinner(f"Loading {uploaded.name}..."):
                    try:
                        df, meta = _load_uploaded(uploaded)
                        st.session_state[file_key] = True
                        on_loaded(df, meta)
                        st.success(f"Loaded {uploaded.name} \u2014 {len(df):,} rows \xd7 {len(df.columns)} columns")
                    except Exception as e:
                        st.error(f"Failed to load: {e}")

    with cols[1]:
        _render_info_panels()


def _load_uploaded(uploaded_file) -> tuple:
    """Save the uploaded file to a temp path and call universal_loader."""
    import tempfile
    from pathlib import Path
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    df, meta = smart_load(str(tmp_path))
    meta = {
        **(meta or {}),
        "filename": uploaded_file.name,
        "size_bytes": len(uploaded_file.getvalue()),
        "source_type": "manual",
        "source_path": str(tmp_path),
    }
    return df, meta


def _render_info_panels() -> None:
    st.markdown(
        '<div class="up-info-panel">'
        '  <h4>\U0001f4a1 Tips for best results</h4>'
        '  <ul>'
        '    <li>First row should be column headers</li>'
        '    <li>One row per observation</li>'
        '    <li>Mixed types in a column will be auto-detected and cleaned</li>'
        '    <li>UTF-8 encoding is preferred</li>'
        '  </ul>'
        '</div>'
        '<div class="up-info-panel">'
        '  <h4>\U0001f6e1 Privacy</h4>'
        '  <p>Files stay in your session. Nothing is uploaded to third-party services.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
