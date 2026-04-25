"""Download Buttons -- renders download buttons for available report formats.

Shows one button per generated report format with MIME type and file size.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import streamlit as st

_ALLOWED_OUTPUTS_DIR = Path(os.path.abspath("outputs"))

_FORMAT_META: Final[dict[str, dict[str, str]]] = {
    "html": {
        "label": "HTML Report",
        "mime": "text/html",
        "icon": "globe",
    },
    "pdf": {
        "label": "PDF Report",
        "mime": "application/pdf",
        "icon": "file-pdf",
    },
    "executive_summary": {
        "label": "Executive Summary",
        "mime": "application/pdf",
        "icon": "file-text",
    },
    "notebook": {
        "label": "Jupyter Notebook",
        "mime": "application/x-ipynb+json",
        "icon": "journal-code",
    },
    "zip": {
        "label": "Full Package (ZIP)",
        "mime": "application/zip",
        "icon": "file-zip",
    },
}


def _human_size(size_bytes: int) -> str:
    """Format byte count as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


def render_download_buttons(
    report_paths: dict[str, str],
    columns: int = 3,
) -> None:
    """Render download buttons for all available report formats.

    Args:
        report_paths: Mapping of format key (e.g. ``"html"``) to file path.
        columns: Number of button columns in the grid.
    """
    if not report_paths:
        st.info("No reports generated yet. Complete the analysis pipeline first.")
        return

    st.markdown("##### Download Reports")

    available = [
        (fmt, path)
        for fmt, path in report_paths.items()
        if Path(path).is_file()
    ]

    if not available:
        st.warning("Report files not found on disk. They may have been moved or deleted.")
        return

    for row_start in range(0, len(available), columns):
        row_items = available[row_start : row_start + columns]
        cols = st.columns(columns)

        for col, (fmt, path) in zip(cols, row_items):
            meta = _FORMAT_META.get(fmt, {"label": fmt.upper(), "mime": "application/octet-stream", "icon": "file"})
            file_path = Path(path)
            resolved = Path(os.path.abspath(path))
            if not str(resolved).startswith(str(_ALLOWED_OUTPUTS_DIR)):
                continue  # Skip files outside the allowed outputs directory
            size_str = _human_size(file_path.stat().st_size) if file_path.exists() else ""

            with col:
                file_bytes = resolved.read_bytes()
                label = f"{meta['label']} ({size_str})" if size_str else meta["label"]
                st.download_button(
                    label=label,
                    data=file_bytes,
                    file_name=file_path.name,
                    mime=meta["mime"],
                    key=f"dl_{fmt}",
                    use_container_width=True,
                )
