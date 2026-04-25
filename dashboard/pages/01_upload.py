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

_SAMPLE_DATASETS: list[dict[str, Any]] = [
    {
        "key": "iris",
        "label": "Iris",
        "task": "Classification",
        "rows": "~150",
        "icon": "🌸",
        "desc": "Classic flower species dataset",
    },
    {
        "key": "titanic",
        "label": "Titanic",
        "task": "Classification",
        "rows": "~891",
        "icon": "🚢",
        "desc": "Passenger survival prediction",
    },
    {
        "key": "boston",
        "label": "CA Housing",
        "task": "Regression",
        "rows": "~20 k",
        "icon": "🏠",
        "desc": "California house price prediction",
    },
    {
        "key": "wine",
        "label": "Wine Quality",
        "task": "Classification",
        "rows": "~178",
        "icon": "🍷",
        "desc": "Wine variety from chemical features",
    },
    {
        "key": "tips",
        "label": "Tips",
        "task": "Regression",
        "rows": "~244",
        "icon": "💵",
        "desc": "Restaurant tip amount prediction",
    },
]

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ── tokens ── */
:root {
    --c-bg:      #0f172a;
    --c-card:    #1e293b;
    --c-border:  #334155;
    --c-primary: #6366f1;
    --c-success: #22c55e;
    --c-accent:  #0ea5e9;
    --c-muted:   #94a3b8;
    --c-text:    #e2e8f0;
    --c-text-hi: #f8fafc;
    --r-card:    12px;
    --r-pill:    999px;
    --shadow:    0 4px 24px rgba(0,0,0,.35);
}

/* ── global page tint ── */
[data-testid="stAppViewContainer"] {
    background: var(--c-bg) !important;
}
[data-testid="stSidebar"] {
    background: #0d1626 !important;
}

/* ── page heading ── */
.upload-heading {
    margin: 0 0 4px 0;
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8 0%, #6366f1 50%, #0ea5e9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.upload-sub {
    color: var(--c-muted);
    font-size: .95rem;
    margin: 0 0 28px 0;
}

/* ── upload zone ── */
[data-testid="stFileUploader"] {
    background: var(--c-card) !important;
    border: 2px dashed var(--c-border) !important;
    border-radius: var(--r-card) !important;
    padding: 40px 24px !important;
    transition: border-color .2s, box-shadow .2s;
}
[data-testid="stFileUploader"]:hover,
[data-testid="stFileUploader"]:focus-within {
    border-color: var(--c-primary) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,.18) !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: var(--c-muted) !important;
}

/* ── upload icon block ── */
.upload-icon-row {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    pointer-events: none;
}
.upload-icon {
    width: 52px;
    height: 52px;
    background: rgba(99,102,241,.12);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
}
.upload-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--c-text-hi);
}
.upload-hint {
    font-size: .82rem;
    color: var(--c-muted);
}

/* ── format badges ── */
.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 12px 0 0 0;
}
.badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: var(--r-pill);
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .04em;
    text-transform: uppercase;
    background: rgba(99,102,241,.12);
    color: #a5b4fc;
    border: 1px solid rgba(99,102,241,.25);
}

/* ── section divider ── */
.section-label {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 28px 0 16px 0;
    color: var(--c-muted);
    font-size: .8rem;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
}
.section-label::before,
.section-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--c-border);
}

/* ── sample dataset cards ── */
.sample-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 12px;
    margin-bottom: 4px;
}
.sample-card {
    background: var(--c-card);
    border: 1.5px solid var(--c-border);
    border-radius: var(--r-card);
    padding: 14px 14px 12px;
    cursor: pointer;
    transition: border-color .18s, box-shadow .18s, transform .12s;
    text-align: left;
}
.sample-card:hover {
    border-color: var(--c-primary);
    box-shadow: 0 0 0 3px rgba(99,102,241,.18);
    transform: translateY(-1px);
}
.sample-card.active {
    border-color: var(--c-primary);
    background: rgba(99,102,241,.08);
}
.sc-icon  { font-size: 1.5rem; margin-bottom: 6px; }
.sc-name  { font-weight: 700; font-size: .9rem; color: var(--c-text-hi); }
.sc-desc  { font-size: .75rem; color: var(--c-muted); margin-top: 2px; line-height: 1.35; }
.sc-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: var(--r-pill);
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .04em;
    margin-top: 6px;
}
.sc-badge.cls { background: rgba(99,102,241,.15); color: #818cf8; }
.sc-badge.reg { background: rgba(14,165,233,.15); color: #38bdf8; }
.sc-rows { font-size: .72rem; color: var(--c-muted); margin-top: 3px; }

/* ── metric cards ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 20px 0 24px;
}
.metric-card {
    background: var(--c-card);
    border: 1px solid var(--c-border);
    border-radius: var(--r-card);
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: var(--shadow);
}
.mc-icon {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    flex-shrink: 0;
}
.mc-icon.rows  { background: rgba(99,102,241,.15); }
.mc-icon.cols  { background: rgba(14,165,233,.15); }
.mc-icon.mem   { background: rgba(34,197,94,.15); }
.mc-value { font-size: 1.45rem; font-weight: 700; color: var(--c-text-hi); line-height: 1.15; }
.mc-label { font-size: .75rem; color: var(--c-muted); margin-top: 1px; }

/* ── section headings ── */
.sec-heading {
    font-size: 1rem;
    font-weight: 700;
    color: var(--c-text-hi);
    margin: 0 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sec-heading::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--c-border);
}

/* ── data table (st.dataframe) ── */
[data-testid="stDataFrame"] {
    background: var(--c-card) !important;
    border: 1px solid var(--c-border) !important;
    border-radius: var(--r-card) !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    background: rgba(99,102,241,.10) !important;
    color: #a5b4fc !important;
    font-size: .78rem !important;
    font-weight: 700 !important;
    letter-spacing: .04em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--c-border) !important;
}
[data-testid="stDataFrame"] tr:nth-child(even) td {
    background: rgba(255,255,255,.025) !important;
}
[data-testid="stDataFrame"] td {
    font-size: .82rem !important;
    color: var(--c-text) !important;
    border-bottom: 1px solid rgba(51,65,85,.6) !important;
}

/* ── column type pills in table ── */
.type-num  { color: #60a5fa; font-weight: 600; }
.type-cat  { color: #c084fc; font-weight: 600; }
.type-dt   { color: #34d399; font-weight: 600; }
.type-bool { color: #fbbf24; font-weight: 600; }
.type-oth  { color: var(--c-muted); }

/* ── progress bar (missing %) ── */
.pbar-wrap {
    display: flex;
    align-items: center;
    gap: 7px;
}
.pbar-track {
    flex: 1;
    height: 5px;
    background: rgba(255,255,255,.08);
    border-radius: var(--r-pill);
    overflow: hidden;
}
.pbar-fill {
    height: 100%;
    border-radius: var(--r-pill);
    background: linear-gradient(90deg, var(--c-primary), var(--c-accent));
}
.pbar-fill.warn { background: linear-gradient(90deg, #f59e0b, #ef4444); }
.pbar-pct { font-size: .75rem; color: var(--c-muted); min-width: 34px; text-align: right; }

/* ── advanced expander ── */
[data-testid="stExpander"] {
    background: var(--c-card) !important;
    border: 1px solid var(--c-border) !important;
    border-radius: var(--r-card) !important;
}
[data-testid="stExpander"] summary {
    color: var(--c-muted) !important;
    font-size: .88rem !important;
}

/* ── proceed button ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, var(--c-primary) 0%, #4f46e5 60%, var(--c-accent) 130%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: .95rem !important;
    letter-spacing: .03em !important;
    padding: 14px 32px !important;
    box-shadow: 0 4px 18px rgba(99,102,241,.4) !important;
    transition: opacity .15s, box-shadow .15s, transform .1s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    opacity: .92 !important;
    box-shadow: 0 6px 24px rgba(99,102,241,.55) !important;
    transform: translateY(-1px) !important;
}

/* ── slider ── */
[data-testid="stSlider"] {
    padding: 0 4px !important;
}

/* ── info / success alerts ── */
[data-testid="stAlert"] {
    border-radius: var(--r-card) !important;
    border-left-width: 3px !important;
}

/* ── divider ── */
hr { border-color: var(--c-border) !important; margin: 28px 0 !important; }
</style>
"""

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
            "Missing %": f"{missing / total * 100:.1f}%" if total > 0 else "0.0%",
            "Unique": int(series.nunique()),
            "Sample": str(series.dropna().iloc[0]) if not series.dropna().empty else "N/A",
        })
    return info_rows


def _dtype_category(dtype_str: str) -> str:
    """Return a semantic category for a dtype string."""
    d = dtype_str.lower()
    if any(t in d for t in ("int", "float", "complex", "decimal")):
        return "numeric"
    if "datetime" in d or "period" in d or "timedelta" in d:
        return "datetime"
    if "bool" in d:
        return "boolean"
    return "categorical"


def _missing_pct(pct_str: str) -> float:
    """Parse '12.3%' -> 12.3."""
    try:
        return float(pct_str.replace("%", ""))
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Sub-render helpers
# ---------------------------------------------------------------------------

def _render_metric_cards(df: pd.DataFrame) -> None:
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    mem_label = f"{mem_mb:.1f} MB" if mem_mb >= 1.0 else f"{mem_mb * 1024:.0f} KB"

    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-card">
            <div class="mc-icon rows">&#8801;</div>
            <div>
              <div class="mc-value">{len(df):,}</div>
              <div class="mc-label">Rows</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="mc-icon cols">&#9783;</div>
            <div>
              <div class="mc-value">{len(df.columns):,}</div>
              <div class="mc-label">Columns</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="mc-icon mem">&#9671;</div>
            <div>
              <div class="mc-value">{mem_label}</div>
              <div class="mc-label">Memory</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_column_info_table(col_info: list[dict[str, Any]]) -> None:
    """Render a styled column-info table with progress bars for missing %."""
    type_color = {
        "numeric": "#60a5fa",
        "datetime": "#34d399",
        "boolean": "#fbbf24",
        "categorical": "#c084fc",
    }

    header_cells = "".join(
        f'<th style="background:rgba(99,102,241,.10);color:#a5b4fc;'
        f'font-size:.75rem;font-weight:700;letter-spacing:.05em;'
        f'text-transform:uppercase;padding:9px 12px;border-bottom:1px solid #334155;">{h}</th>'
        for h in ["Column", "Type", "Missing", "Unique", "Sample"]
    )

    rows_html = ""
    for i, row in enumerate(col_info):
        bg = "rgba(255,255,255,.018)" if i % 2 == 1 else "transparent"
        cat = _dtype_category(row["Type"])
        tc = type_color.get(cat, "#94a3b8")
        pct = _missing_pct(row["Missing %"])
        warn = "warn" if pct > 20 else ""

        pbar = (
            f'<div class="pbar-wrap">'
            f'  <div class="pbar-track"><div class="pbar-fill {warn}" style="width:{min(pct,100):.1f}%"></div></div>'
            f'  <span class="pbar-pct">{pct:.1f}%</span>'
            f'</div>'
        )

        td = 'style="padding:9px 12px;font-size:.82rem;color:#e2e8f0;border-bottom:1px solid rgba(51,65,85,.55);"'
        rows_html += (
            f'<tr style="background:{bg};">'
            f'  <td {td}><span style="font-weight:600;color:#f8fafc;">{row["Column"]}</span></td>'
            f'  <td {td}><span style="color:{tc};font-weight:600;font-size:.76rem;">{row["Type"]}</span></td>'
            f'  <td {td}>{pbar}</td>'
            f'  <td {td}>{row["Unique"]:,}</td>'
            f'  <td {td} style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'
            f'color:#94a3b8;">{row["Sample"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f"""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;
                    overflow:auto;box-shadow:0 4px 24px rgba(0,0,0,.35);margin-bottom:8px;">
          <table style="width:100%;border-collapse:collapse;">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Page heading ──────────────────────────────────────────────────────
    st.markdown(
        '<h1 class="upload-heading">Upload Your Data</h1>'
        '<p class="upload-sub">Import any tabular dataset to begin your autonomous analysis pipeline.</p>',
        unsafe_allow_html=True,
    )

    # ── Upload zone decorative header ─────────────────────────────────────
    st.markdown(
        """
        <div class="upload-icon-row">
          <div class="upload-icon">&#8679;</div>
          <span class="upload-title">Drag & Drop or Click to Browse</span>
          <span class="upload-hint">Max 200 MB &mdash; all common tabular formats accepted</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=_SUPPORTED_EXTENSIONS,
        help="Drag and drop or click to browse. Max 200 MB.",
        key="file_uploader_main",
        label_visibility="collapsed",
    )

    # Format badges
    st.markdown(
        '<div class="badge-row">'
        + "".join(
            f'<span class="badge">{ext}</span>'
            for ext in ["CSV", "TSV", "Excel", "Parquet", "JSON", "JSONL"]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Sample dataset cards ───────────────────────────────────────────────
    st.markdown(
        '<div class="section-label">or start with a sample dataset</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(_SAMPLE_DATASETS))
    active_sample_key: str | None = None

    for col, ds in zip(cols, _SAMPLE_DATASETS):
        with col:
            badge_cls = "reg" if ds["task"] == "Regression" else "cls"
            current_cache = st.session_state.get("_upload_cache_key", "")
            is_active = current_cache == f"sample_{ds['key']}"
            card_cls = "sample-card active" if is_active else "sample-card"

            st.markdown(
                f"""
                <div class="{card_cls}">
                  <div class="sc-icon">{ds['icon']}</div>
                  <div class="sc-name">{ds['label']}</div>
                  <div class="sc-desc">{ds['desc']}</div>
                  <span class="sc-badge {badge_cls}">{ds['task']}</span>
                  <div class="sc-rows">{ds['rows']} rows</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"Load {ds['label']}",
                key=f"sample_btn_{ds['key']}",
                use_container_width=True,
            ):
                active_sample_key = ds["key"]

    # ── Load logic ─────────────────────────────────────────────────────────
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
                st.success(f"Loaded **{uploaded_file.name}** successfully.")

    elif active_sample_key is not None:
        sample_label = next(
            (d["label"] for d in _SAMPLE_DATASETS if d["key"] == active_sample_key),
            active_sample_key,
        )
        if st.session_state.get("_upload_cache_key") != f"sample_{active_sample_key}":
            with st.spinner(f"Loading {sample_label}..."):
                df = _load_sample_dataset(active_sample_key)
            if df is not None:
                st.session_state["uploaded_data"] = df
                st.session_state["uploaded_file_name"] = sample_label
                st.session_state["_upload_cache_key"] = f"sample_{active_sample_key}"
                st.success(f"Loaded sample dataset: **{sample_label}**")

    # ── Preview section ────────────────────────────────────────────────────
    df = st.session_state.get("uploaded_data")
    if df is None:
        st.info("Upload a file above or select one of the sample datasets to get started.")
        st.stop()

    st.divider()

    # Metric cards
    _render_metric_cards(df)

    # Data preview heading + row slider
    st.markdown('<p class="sec-heading">Data Preview</p>', unsafe_allow_html=True)

    max_rows = min(500, len(df))
    default_rows = min(50, len(df))
    preview_rows = st.slider(
        "Rows to display",
        min_value=5,
        max_value=max_rows,
        value=default_rows,
        step=5,
        key="preview_row_count_slider",
    )
    st.dataframe(
        df.head(preview_rows),
        use_container_width=True,
        key="data_preview_table",
    )

    # Column information heading + styled table
    st.markdown('<p class="sec-heading" style="margin-top:24px;">Column Information</p>', unsafe_allow_html=True)
    col_info = _build_column_info(df)
    st.session_state["columns"] = col_info
    _render_column_info_table(col_info)

    # ── Additional files expander ──────────────────────────────────────────
    with st.expander("Upload additional files (advanced / multi-source join)"):
        extra_file = st.file_uploader(
            "Add another file",
            type=_SUPPORTED_EXTENSIONS,
            key="extra_file_uploader",
        )
        if extra_file is not None:
            extra_df = _load_uploaded_file(extra_file)
            if extra_df is not None:
                additional: list[dict[str, Any]] = st.session_state.get(
                    "additional_datasets", []
                )
                additional.append({"name": extra_file.name, "data": extra_df})
                st.session_state["additional_datasets"] = additional
                st.success(
                    f"Added **{extra_file.name}** "
                    f"({len(extra_df):,} rows x {len(extra_df.columns)} cols)"
                )

    # ── Proceed button ─────────────────────────────────────────────────────
    st.divider()
    if st.button(
        "Proceed to Configuration  →",
        type="primary",
        use_container_width=True,
        key="proceed_to_configure_btn",
    ):
        st.switch_page("pages/02_configure.py")


_page()
