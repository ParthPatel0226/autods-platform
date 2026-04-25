"""Page 01 -- Data Upload.

File uploader supporting CSV, Excel, Parquet, and JSON.  Shows a data preview,
column info table, and shape summary.  Stores the loaded DataFrame and column
metadata in ``st.session_state``.
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = ["csv", "tsv", "xlsx", "xls", "parquet", "json", "jsonl"]

_SAMPLE_DATASETS: dict[str, str] = {
    "-- select --": "",
    "Iris (classification)": "iris",
    "Titanic (classification)": "titanic",
    "Boston Housing (regression)": "boston",
    "Wine Quality (classification)": "wine",
    "Tips (regression)": "tips",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_uploaded_file(uploaded_file: Any) -> pd.DataFrame | None:
    """Read an uploaded file into a DataFrame based on extension."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith((".csv", ".tsv")):
            sep = "\t" if name.endswith(".tsv") else ","
            return pd.read_csv(uploaded_file, sep=sep, low_memory=False)
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        if name.endswith(".parquet"):
            return pd.read_parquet(BytesIO(uploaded_file.read()))
        if name.endswith((".json", ".jsonl")):
            return pd.read_json(uploaded_file, lines=name.endswith(".jsonl"))
    except Exception as exc:
        st.error(f"Failed to load file: {exc}")
        logger.exception("File load error for %s", name)
    return None


def _load_sample_dataset(key: str) -> pd.DataFrame | None:
    """Load a built-in sample dataset."""
    try:
        if key == "iris":
            from sklearn.datasets import load_iris
            data = load_iris(as_frame=True)
            df = data.frame
            df["target"] = data.target
            return df
        if key == "titanic":
            url = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
            return pd.read_csv(url)
        if key == "boston":
            from sklearn.datasets import fetch_california_housing
            data = fetch_california_housing(as_frame=True)
            return data.frame
        if key == "wine":
            from sklearn.datasets import load_wine
            data = load_wine(as_frame=True)
            df = data.frame
            df["target"] = data.target
            return df
        if key == "tips":
            import plotly.express as px  # type: ignore[import-untyped]
            return px.data.tips()
    except Exception as exc:
        st.error(f"Failed to load sample dataset: {exc}")
        logger.exception("Sample dataset error for key=%s", key)
    return None


def _build_column_info(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build per-column metadata summary."""
    info_rows: list[dict[str, Any]] = []
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        total = len(series)
        info_rows.append({
            "Column": col,
            "Type": str(series.dtype),
            "Missing": missing,
            "Missing %": f"{missing / total * 100:.1f}%" if total > 0 else "0%",
            "Unique": int(series.nunique()),
            "Sample": str(series.dropna().iloc[0]) if not series.dropna().empty else "N/A",
        })
    return info_rows


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    st.header("Upload Your Data")
    st.markdown(
        "Upload a dataset to begin analysis. Supported formats: "
        "CSV, TSV, Excel, Parquet, JSON."
    )

    # ---- File uploader ----
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=_SUPPORTED_EXTENSIONS,
        help="Drag and drop or click to browse. Max 200 MB.",
        key="file_uploader_main",
    )

    # ---- Sample datasets ----
    with st.expander("Or use a sample dataset"):
        sample_choice = st.selectbox(
            "Sample dataset",
            options=list(_SAMPLE_DATASETS.keys()),
            key="sample_dataset_select",
        )

    # ---- Load logic ----
    df: pd.DataFrame | None = st.session_state.get("uploaded_data")

    if uploaded_file is not None:
        cache_key = f"file_{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("_upload_cache_key") != cache_key:
            with st.spinner("Loading file..."):
                df = _load_uploaded_file(uploaded_file)
            if df is not None:
                st.session_state["uploaded_data"] = df
                st.session_state["uploaded_file_name"] = uploaded_file.name
                st.session_state["_upload_cache_key"] = cache_key
                st.success(f"Loaded **{uploaded_file.name}**")

    elif sample_choice and _SAMPLE_DATASETS.get(sample_choice):
        sample_key = _SAMPLE_DATASETS[sample_choice]
        if st.session_state.get("_upload_cache_key") != f"sample_{sample_key}":
            with st.spinner(f"Loading {sample_choice}..."):
                df = _load_sample_dataset(sample_key)
            if df is not None:
                st.session_state["uploaded_data"] = df
                st.session_state["uploaded_file_name"] = sample_choice
                st.session_state["_upload_cache_key"] = f"sample_{sample_key}"
                st.success(f"Loaded sample: **{sample_choice}**")

    # ---- Preview ----
    df = st.session_state.get("uploaded_data")
    if df is None:
        st.info("Upload a file or select a sample dataset to get started.")
        st.stop()

    st.divider()

    # Shape summary
    col_rows, col_cols, col_mem = st.columns(3)
    col_rows.metric("Rows", f"{len(df):,}")
    col_cols.metric("Columns", f"{len(df.columns):,}")
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    col_mem.metric("Memory", f"{mem_mb:.1f} MB")

    # Data preview
    st.subheader("Data Preview")
    preview_rows = st.slider(
        "Rows to show",
        min_value=5,
        max_value=min(500, len(df)),
        value=min(100, len(df)),
        step=5,
        key="preview_row_count",
    )
    st.dataframe(df.head(preview_rows), use_container_width=True, key="data_preview_table")

    # Column info
    st.subheader("Column Information")
    col_info = _build_column_info(df)
    st.session_state["columns"] = col_info
    st.dataframe(
        pd.DataFrame(col_info),
        use_container_width=True,
        hide_index=True,
        key="col_info_table",
    )

    # Multi-source option
    with st.expander("Upload additional files (advanced)"):
        extra_file = st.file_uploader(
            "Add another file",
            type=_SUPPORTED_EXTENSIONS,
            key="extra_file_uploader",
        )
        if extra_file is not None:
            extra_df = _load_uploaded_file(extra_file)
            if extra_df is not None:
                additional: list[dict[str, Any]] = st.session_state.get("additional_datasets", [])
                additional.append({"name": extra_file.name, "data": extra_df})
                st.session_state["additional_datasets"] = additional
                st.success(
                    f"Added **{extra_file.name}** ({len(extra_df):,} rows x {len(extra_df.columns)} cols)"
                )

    # Proceed
    st.divider()
    if st.button("Proceed to Configuration", type="primary", use_container_width=True):
        st.switch_page("pages/02_configure.py")


_page()
