"""AutoDS Platform -- Main Streamlit Application.

Entry point for the web dashboard.  Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED, PLATFORM_VERSION

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AutoDS -- Autonomous Data Science Platform",
    page_icon="DS",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    """Render sidebar with mode selector, workflow nav, and session management."""
    with st.sidebar:
        st.header("Configuration")

        # Mode selector
        mode_options = {MODE_AUTO: "Auto", MODE_GUIDED: "Guided", MODE_EXPERT: "Expert"}
        current_mode = st.session_state.get("user_mode", MODE_GUIDED)
        mode_labels = list(mode_options.values())
        mode_keys = list(mode_options.keys())
        mode_idx = mode_keys.index(current_mode) if current_mode in mode_keys else 1

        selected_label = st.radio(
            "Analysis Mode",
            mode_labels,
            index=mode_idx,
            help="Auto: system decides. Guided: system recommends, you choose. Expert: full control.",
        )
        st.session_state["user_mode"] = mode_keys[mode_labels.index(selected_label)]

        st.divider()

        # Workflow navigation
        st.markdown("##### Workflow")
        completed: list[str] = st.session_state.get("completed_steps", [])
        current: str = st.session_state.get("current_step", "upload")
        has_data = "uploaded_data" in st.session_state

        for step in _WORKFLOW_STEPS:
            key = step["key"]
            label = step["label"]

            if key in completed:
                prefix = "[done] "
            elif key == current:
                prefix = ">> "
            else:
                prefix = "   "

            # Only allow clicking if data uploaded (except upload page itself)
            enabled = has_data or key == "upload"
            if st.button(f"{prefix}{label}", key=f"nav_{key}", use_container_width=True, disabled=not enabled):
                st.switch_page(step["page"])

        st.divider()

        # Session management
        st.markdown("##### Session")
        if st.button("New Session", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.divider()
        st.caption(f"AutoDS v{PLATFORM_VERSION}")


def _landing_page() -> None:
    """Landing page shown when no data is uploaded yet."""
    st.title("AutoDS -- Autonomous Data Science Platform")
    st.markdown(
        "Upload any dataset. Get analyst + scientist level outputs. "
        "Full control over every analytical decision."
    )

    st.divider()

    # Quick upload
    st.subheader("Get Started")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "parquet", "json", "tsv"],
        help="Supported: CSV, Excel, Parquet, JSON, TSV.",
    )

    if uploaded_file is not None:
        _process_upload(uploaded_file)

    # Feature highlights
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Multi-Source Ingestion**")
        st.caption("CSV, Excel, Parquet, JSON, databases, APIs, cloud storage")
    with col2:
        st.markdown("**Domain Intelligence**")
        st.caption("Healthcare, Finance, E-commerce, Manufacturing, HR, Marketing")
    with col3:
        st.markdown("**Full Pipeline**")
        st.caption("EDA -> Features -> Modeling -> Explainability -> Deployment")


def _process_upload(uploaded_file: Any) -> None:
    """Process uploaded file into a DataFrame and store in session state."""
    try:
        name = uploaded_file.name
        if name.endswith(".csv") or name.endswith(".tsv"):
            sep = "\t" if name.endswith(".tsv") else ","
            df = pd.read_csv(uploaded_file, sep=sep)
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
        return

    st.session_state["uploaded_data"] = df
    st.session_state["row_count"] = len(df)
    st.session_state["column_count"] = len(df.columns)
    st.session_state["current_step"] = "configure"
    st.session_state["completed_steps"] = st.session_state.get("completed_steps", []) + ["upload"]

    st.success(f"Loaded **{name}**: {len(df):,} rows, {len(df.columns)} columns")
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("Continue to Configuration", type="primary"):
        st.switch_page("pages/02_configure.py")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _sidebar()

    if "uploaded_data" not in st.session_state:
        _landing_page()
    else:
        # If user lands on app.py with data, redirect to current step
        current = st.session_state.get("current_step", "upload")
        step_map = {s["key"]: s["page"] for s in _WORKFLOW_STEPS}
        page = step_map.get(current)
        if page:
            st.switch_page(page)
        else:
            _landing_page()


if __name__ == "__main__":
    main()

main()
