"""Page 01 -- Data Upload.

File uploader supporting CSV, Excel, Parquet, and JSON.  Shows a data preview,
column info table, and shape summary.  Stores the loaded DataFrame and column
metadata in ``st.session_state``.
"""

from __future__ import annotations

import logging
from io import BytesIO
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
        "desc": "Classic flower species dataset",
    },
    {
        "key": "titanic",
        "label": "Titanic",
        "task": "Classification",
        "rows": "~891",
        "desc": "Passenger survival prediction",
    },
    {
        "key": "boston",
        "label": "CA Housing",
        "task": "Regression",
        "rows": "~20 k",
        "desc": "California house price prediction",
    },
    {
        "key": "wine",
        "label": "Wine Quality",
        "task": "Classification",
        "rows": "~178",
        "desc": "Wine variety from chemical features",
    },
    {
        "key": "diabetes",
        "label": "Diabetes",
        "task": "Regression",
        "rows": "~442",
        "desc": "Disease progression prediction",
    },
    {
        "key": "tips",
        "label": "Tips",
        "task": "Regression",
        "rows": "~244",
        "desc": "Restaurant tip amount prediction",
    },
]

# ---------------------------------------------------------------------------
# CSS -- design tokens matching app.py
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* -- design tokens ---------------------------------------------------- */
:root {
    --bg-primary: #0a0a0f;
    --bg-card: #12121a;
    --bg-card-hover: #1a1a25;
    --bg-elevated: #16161f;
    --border-subtle: rgba(99,102,241,0.12);
    --border-active: rgba(99,102,241,0.4);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-primary: #6366f1;
    --accent-secondary: #0ea5e9;
    --accent-success: #22c55e;
    --accent-warning: #f59e0b;
    --gradient-primary: linear-gradient(135deg, #6366f1, #0ea5e9);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --shadow-card: 0 4px 24px rgba(0,0,0,0.25);
    --shadow-glow: 0 0 20px rgba(99,102,241,0.15);
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* -- keyframes -------------------------------------------------------- */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes borderDash {
    to { stroke-dashoffset: 0; }
}
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* -- page background -------------------------------------------------- */
[data-testid="stAppViewContainer"] { background: var(--bg-primary) !important; }
[data-testid="stSidebar"] { background: #08080d !important; }

/* -- page heading ----------------------------------------------------- */
.upload-heading {
    margin: 0 0 4px;
    font-size: 2rem;
    font-weight: 700;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    animation: fadeInUp var(--transition-normal) both;
}
.upload-sub {
    color: var(--text-secondary);
    font-size: 0.92rem;
    margin: 0 0 28px;
    animation: fadeInUp var(--transition-normal) 60ms both;
}

/* -- upload zone ------------------------------------------------------ */
.upload-zone-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 28px 24px 12px;
    pointer-events: none;
    animation: fadeInUp var(--transition-normal) 120ms both;
}
.upload-zone-icon {
    width: 56px; height: 56px;
    background: rgba(99,102,241,0.10);
    border: 1.5px solid var(--border-active);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    position: relative;
}
/* CSS arrow shape instead of emoji */
.upload-zone-icon::after {
    content: "";
    width: 14px; height: 14px;
    border-left: 2.5px solid var(--accent-primary);
    border-top: 2.5px solid var(--accent-primary);
    transform: rotate(45deg) translateY(3px);
}
.upload-zone-title {
    font-size: 1.05rem; font-weight: 600;
    color: var(--text-primary);
}
.upload-zone-hint {
    font-size: 0.82rem;
    color: var(--text-muted);
}

[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 2px dashed var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    padding: 0 24px 24px !important;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    backdrop-filter: blur(12px);
}
[data-testid="stFileUploader"]:hover,
[data-testid="stFileUploader"]:focus-within {
    border-color: var(--accent-primary) !important;
    box-shadow: var(--shadow-glow) !important;
}
[data-testid="stFileUploaderDropzone"] { background: transparent !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { color: var(--text-muted) !important; }

/* -- format badges ---------------------------------------------------- */
.badge-row {
    display: flex; flex-wrap: wrap; gap: 6px;
    margin: 12px 0 0;
}
.badge {
    display: inline-flex; align-items: center;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase;
    background: rgba(99,102,241,0.08);
    color: #a5b4fc;
    border: 1px solid var(--border-subtle);
    transition: background var(--transition-fast);
}
.badge:hover { background: rgba(99,102,241,0.15); }

/* -- section header --------------------------------------------------- */
.section-header {
    display: flex; align-items: center; gap: 12px;
    margin: 32px 0 18px;
    animation: fadeInUp var(--transition-normal) both;
}
.section-header-text {
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-muted);
    white-space: nowrap;
}
.section-header::after {
    content: "";
    flex: 1; height: 1px;
    background: var(--gradient-primary);
    opacity: 0.3;
}

/* -- sample dataset grid ---------------------------------------------- */
.sample-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 8px;
}
@media (max-width: 768px) {
    .sample-grid { grid-template-columns: repeat(2, 1fr); }
}
.sample-card {
    background: var(--bg-card);
    border: 1.5px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px;
    backdrop-filter: blur(12px);
    transition: border-color var(--transition-fast),
                box-shadow var(--transition-fast),
                transform var(--transition-fast),
                background var(--transition-fast);
    animation: fadeInUp var(--transition-normal) both;
}
.sample-card:hover {
    border-color: var(--border-active);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
    background: var(--bg-card-hover);
}
.sample-card.active {
    border-color: var(--accent-primary);
    background: rgba(99,102,241,0.06);
    box-shadow: var(--shadow-glow);
}
.sc-name {
    font-weight: 700; font-size: 0.92rem;
    color: var(--text-primary);
    margin-bottom: 4px;
}
.sc-desc {
    font-size: 0.76rem; color: var(--text-muted);
    line-height: 1.4; margin-bottom: 8px;
}
.sc-meta { display: flex; align-items: center; gap: 8px; }
.sc-pill {
    display: inline-flex; align-items: center;
    padding: 2px 9px; border-radius: 999px;
    font-size: 0.67rem; font-weight: 700;
    letter-spacing: 0.03em;
}
.sc-pill.cls { background: rgba(99,102,241,0.12); color: #818cf8; }
.sc-pill.reg { background: rgba(14,165,233,0.12); color: #38bdf8; }
.sc-rows {
    font-size: 0.7rem; color: var(--text-muted);
}

/* -- metric cards ----------------------------------------------------- */
.metric-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 20px 0 28px;
    animation: fadeInUp var(--transition-normal) both;
}
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 18px 20px;
    display: flex; align-items: center; gap: 16px;
    box-shadow: var(--shadow-card);
    backdrop-filter: blur(12px);
    position: relative;
    overflow: hidden;
    transition: box-shadow var(--transition-fast);
}
.metric-card:hover { box-shadow: var(--shadow-glow); }
.mc-accent {
    position: absolute; left: 0; top: 0;
    width: 3px; height: 100%;
}
.mc-accent.rows  { background: var(--accent-primary); }
.mc-accent.cols  { background: var(--accent-secondary); }
.mc-accent.mem   { background: var(--accent-success); }
.mc-icon {
    width: 44px; height: 44px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.mc-icon.rows { background: rgba(99,102,241,0.10); }
.mc-icon.cols { background: rgba(14,165,233,0.10); }
.mc-icon.mem  { background: rgba(34,197,94,0.10); }
/* geometric icon shapes */
.mc-icon-shape { display: flex; flex-direction: column; gap: 3px; }
.mc-icon-shape span {
    display: block; height: 2px; border-radius: 1px;
}
.mc-icon.rows .mc-icon-shape span { background: var(--accent-primary); }
.mc-icon.cols .mc-icon-shape span { background: var(--accent-secondary); }
.mc-icon.mem  .mc-icon-shape span { background: var(--accent-success); }
.mc-icon-shape span:nth-child(1) { width: 18px; }
.mc-icon-shape span:nth-child(2) { width: 14px; }
.mc-icon-shape span:nth-child(3) { width: 10px; }
.mc-value {
    font-size: 1.5rem; font-weight: 700;
    color: var(--text-primary); line-height: 1.15;
}
.mc-label {
    font-size: 0.73rem; color: var(--text-muted);
    margin-top: 2px;
}

/* -- data table ------------------------------------------------------- */
.data-table-wrap {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: auto;
    box-shadow: var(--shadow-card);
    margin-bottom: 10px;
    animation: fadeInUp var(--transition-normal) both;
}
.data-table-wrap table {
    width: 100%; border-collapse: collapse;
}
.data-table-wrap th {
    background: var(--bg-elevated);
    color: #a5b4fc;
    font-size: 0.73rem; font-weight: 700;
    letter-spacing: 0.05em; text-transform: uppercase;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-subtle);
    position: sticky; top: 0; z-index: 2;
}
.data-table-wrap tr:nth-child(even) td {
    background: rgba(255,255,255,0.015);
}
.data-table-wrap td {
    font-size: 0.82rem; color: var(--text-primary);
    padding: 10px 14px;
    border-bottom: 1px solid rgba(99,102,241,0.06);
}

/* type pills */
.type-pill {
    display: inline-block; padding: 1px 8px;
    border-radius: 999px; font-size: 0.72rem; font-weight: 600;
}
.type-num  { background: rgba(96,165,250,0.10); color: #60a5fa; }
.type-cat  { background: rgba(192,132,252,0.10); color: #c084fc; }
.type-dt   { background: rgba(52,211,153,0.10); color: #34d399; }
.type-bool { background: rgba(251,191,36,0.10); color: #fbbf24; }
.type-oth  { background: rgba(100,116,139,0.10); color: var(--text-muted); }

/* progress bar (missing %) */
.pbar-wrap { display: flex; align-items: center; gap: 8px; }
.pbar-track {
    flex: 1; height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 999px; overflow: hidden;
}
.pbar-fill {
    height: 100%; border-radius: 999px;
    transition: width var(--transition-normal);
}
.pbar-fill.green  { background: var(--accent-success); }
.pbar-fill.amber  { background: var(--accent-warning); }
.pbar-fill.red    { background: #ef4444; }
.pbar-pct {
    font-size: 0.73rem; color: var(--text-muted);
    min-width: 38px; text-align: right;
}

/* -- st.dataframe override -------------------------------------------- */
[data-testid="stDataFrame"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}

/* -- expander --------------------------------------------------------- */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
}
[data-testid="stExpander"] summary { color: var(--text-muted) !important; }

/* -- proceed button --------------------------------------------------- */
[data-testid="stButton"] > button[kind="primary"] {
    background: var(--gradient-primary) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.03em !important;
    padding: 14px 32px !important;
    min-height: 44px !important;
    box-shadow: 0 4px 18px rgba(99,102,241,0.35) !important;
    transition: opacity var(--transition-fast),
                box-shadow var(--transition-fast),
                transform var(--transition-fast) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    opacity: 0.92 !important;
    box-shadow: 0 6px 24px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="primary"]:focus-visible {
    outline: 2px solid var(--accent-primary) !important;
    outline-offset: 2px !important;
}

/* -- focus-visible rings ---------------------------------------------- */
button:focus-visible, input:focus-visible, [tabindex]:focus-visible {
    outline: 2px solid var(--accent-primary) !important;
    outline-offset: 2px !important;
}

/* -- alerts ----------------------------------------------------------- */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border-left-width: 3px !important;
}

/* -- divider ---------------------------------------------------------- */
hr { border-color: var(--border-subtle) !important; margin: 28px 0 !important; }
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
        if key == "diabetes":
            from sklearn.datasets import load_diabetes
            data = load_diabetes(as_frame=True)
            return data.frame
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


def _pbar_class(pct: float) -> str:
    """Return color class by missing % threshold."""
    if pct < 5.0:
        return "green"
    if pct <= 20.0:
        return "amber"
    return "red"


# ---------------------------------------------------------------------------
# Sub-render helpers
# ---------------------------------------------------------------------------

def _render_section_header(label: str) -> None:
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-header-text">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_metric_cards(df: pd.DataFrame) -> None:
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    mem_label = f"{mem_mb:.1f} MB" if mem_mb >= 1.0 else f"{mem_mb * 1024:.0f} KB"

    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-card">
            <div class="mc-accent rows"></div>
            <div class="mc-icon rows">
              <div class="mc-icon-shape"><span></span><span></span><span></span></div>
            </div>
            <div>
              <div class="mc-value">{len(df):,}</div>
              <div class="mc-label">Rows</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="mc-accent cols"></div>
            <div class="mc-icon cols">
              <div class="mc-icon-shape"><span></span><span></span><span></span></div>
            </div>
            <div>
              <div class="mc-value">{len(df.columns):,}</div>
              <div class="mc-label">Columns</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="mc-accent mem"></div>
            <div class="mc-icon mem">
              <div class="mc-icon-shape"><span></span><span></span><span></span></div>
            </div>
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
    type_cls = {
        "numeric": "type-num",
        "datetime": "type-dt",
        "boolean": "type-bool",
        "categorical": "type-cat",
    }

    headers = ["Column", "Type", "Missing", "Unique", "Sample"]
    header_cells = "".join(f"<th>{h}</th>" for h in headers)

    rows_html = ""
    for row in col_info:
        cat = _dtype_category(row["Type"])
        tcls = type_cls.get(cat, "type-oth")
        pct = _missing_pct(row["Missing %"])
        color_cls = _pbar_class(pct)

        pbar = (
            f'<div class="pbar-wrap">'
            f'  <div class="pbar-track">'
            f'    <div class="pbar-fill {color_cls}" style="width:{min(pct, 100):.1f}%"></div>'
            f'  </div>'
            f'  <span class="pbar-pct">{pct:.1f}%</span>'
            f'</div>'
        )

        sample_val = str(row["Sample"])
        if len(sample_val) > 32:
            sample_val = sample_val[:29] + "..."

        rows_html += (
            f"<tr>"
            f'  <td><span style="font-weight:600;color:var(--text-primary)">{row["Column"]}</span></td>'
            f'  <td><span class="type-pill {tcls}">{row["Type"]}</span></td>'
            f"  <td>{pbar}</td>"
            f"  <td>{row['Unique']:,}</td>"
            f'  <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;color:var(--text-secondary)">{sample_val}</td>'
            f"</tr>"
        )

    st.markdown(
        f'<div class="data-table-wrap">'
        f"  <table><thead><tr>{header_cells}</tr></thead>"
        f"  <tbody>{rows_html}</tbody></table>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_sample_cards() -> str | None:
    """Render sample dataset cards as a 2x3 grid. Return chosen key or None."""
    current_cache = st.session_state.get("_upload_cache_key", "")

    cards_html = ""
    for i, ds in enumerate(_SAMPLE_DATASETS):
        is_active = current_cache == f"sample_{ds['key']}"
        active_cls = " active" if is_active else ""
        pill_cls = "reg" if ds["task"] == "Regression" else "cls"
        delay = i * 40

        cards_html += (
            f'<div class="sample-card{active_cls}" style="animation-delay:{delay}ms">'
            f'  <div class="sc-name">{ds["label"]}</div>'
            f'  <div class="sc-desc">{ds["desc"]}</div>'
            f'  <div class="sc-meta">'
            f'    <span class="sc-pill {pill_cls}">{ds["task"]}</span>'
            f'    <span class="sc-rows">{ds["rows"]} rows</span>'
            f'  </div>'
            f"</div>"
        )

    st.markdown(
        f'<div class="sample-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

    # Streamlit buttons for interaction (below the visual cards)
    cols = st.columns(len(_SAMPLE_DATASETS))
    active_key: str | None = None
    for col, ds in zip(cols, _SAMPLE_DATASETS):
        with col:
            if st.button(
                f"Load {ds['label']}",
                key=f"sample_btn_{ds['key']}",
                use_container_width=True,
            ):
                active_key = ds["key"]
    return active_key


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # -- Page heading
    st.markdown(
        '<h1 class="upload-heading">Upload Your Data</h1>'
        '<p class="upload-sub">'
        "Import any tabular dataset to begin your autonomous analysis pipeline."
        "</p>",
        unsafe_allow_html=True,
    )

    # -- Upload zone decorative header
    st.markdown(
        '<div class="upload-zone-header">'
        '  <div class="upload-zone-icon"></div>'
        '  <span class="upload-zone-title">Drag and Drop or Click to Browse</span>'
        '  <span class="upload-zone-hint">'
        "Max 200 MB -- all common tabular formats accepted</span>"
        "</div>",
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

    # -- Sample dataset section
    _render_section_header("Or start with a sample dataset")
    active_sample_key = _render_sample_cards()

    # -- Load logic
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

    # -- Preview section
    df = st.session_state.get("uploaded_data")
    if df is None:
        st.info(
            "Upload a file above or select one of the sample datasets to get started."
        )
        st.stop()

    st.divider()

    # Metric cards
    _render_metric_cards(df)

    # Data preview
    _render_section_header("Data Preview")

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

    # Column information
    _render_section_header("Column Information")
    col_info = _build_column_info(df)
    st.session_state["columns"] = col_info
    _render_column_info_table(col_info)

    # -- Additional files expander
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

    # -- Proceed button
    st.divider()
    if st.button(
        "Proceed to Configuration  -->",
        type="primary",
        use_container_width=True,
        key="proceed_to_configure_btn",
    ):
        st.switch_page("pages/02_configure.py")


_page()
