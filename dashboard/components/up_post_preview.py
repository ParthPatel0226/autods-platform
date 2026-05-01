"""Post-upload preview — header, metadata, metrics, quality, schema, CTA."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service
from dashboard.components.up_quality_glance import render as render_quality
from dashboard.components.up_schema_table import render as render_schema
from domains.domain_registry import detect_domain


DOMAIN_DISPLAY = {
    "healthcare":    ("\U0001f3e5 Healthcare",   "var(--green)"),
    "finance":       ("\U0001f4b3 Finance",      "var(--cyan)"),
    "ecommerce":     ("\U0001f6d2 E-commerce",   "var(--amber)"),
    "marketing":     ("\U0001f4e3 Marketing",    "var(--pink)"),
    "hr":            ("\U0001f465 HR",           "var(--pink)"),
    "manufacturing": ("\u2699\ufe0f Manufacturing", "var(--violet)"),
    "generic":       ("\U0001f4ca Generic",       "var(--violet)"),
}


def render(df: pd.DataFrame, meta: dict, sources_joined: int = 1) -> None:
    """Render the entire post-upload section.

    Args:
        df: The loaded dataframe.
        meta: Loader metadata dict.
        sources_joined: How many sources were joined to produce df. 1 = no join.
    """
    if df is None or df.empty:
        st.info("No data loaded yet. Pick a source above.")
        return

    project = project_service.get_active()
    if project and project.detected_domain:
        domain_key = project.detected_domain
        confidence = project.metric_summary or "\u2014"
    else:
        domain_key, confidence = _detect_and_persist(df, project)

    _render_header(meta, domain_key, confidence)
    _render_metadata_strip(df, meta)
    _render_metric_cards(df, meta, sources_joined)
    render_quality(df)
    render_schema(df)
    _render_continue_cta()


@st.cache_data(show_spinner=False)
def _cached_detect_domain(col_names_tuple: tuple) -> tuple:
    """Cache domain detection by column names."""
    result = detect_domain(list(col_names_tuple))
    if isinstance(result, tuple) and len(result) >= 2:
        return result[0], result[1]
    return "generic", 0.0


def _detect_and_persist(df: pd.DataFrame, project) -> tuple[str, str]:
    try:
        domain_key, conf = _cached_detect_domain(tuple(df.columns.tolist()))
        domain_key = domain_key or "generic"
        conf = conf or 0.0
    except Exception:
        domain_key, conf = "generic", 0.0

    confidence_str = f"{int(conf * 100)}% confident"

    if project is not None:
        project.detected_domain = domain_key
        project.n_rows = len(df)
        project.n_cols = len(df.columns)
        project.metric_summary = confidence_str
        project_service.update(project)

    return domain_key, confidence_str


def _render_header(meta: dict, domain_key: str, confidence: str) -> None:
    label, _ = DOMAIN_DISPLAY.get(domain_key, DOMAIN_DISPLAY["generic"])
    filename = meta.get("filename", "dataset")
    sub = ""
    if meta.get("source_type") == "cloud":
        sub = f"From {meta.get('source_provider', 'cloud').upper()}"
    elif meta.get("source_type") == "database":
        sub = f"From {meta.get('source_provider', 'database').upper()}"
    elif meta.get("source_type") == "api":
        sub = f"From {meta.get('source_provider', 'API').upper()}"
    elif meta.get("source_type") == "sample":
        sub = "Built-in sample dataset"

    st.markdown(
        f'<div class="up-result-header">'
        f'  <div class="up-result-title">'
        f'    <h2>Loaded <em>{_html_escape(filename)}</em></h2>'
        f'    <p>{sub or "Local file"}</p>'
        f'  </div>'
        f'  <div class="up-domain-detected">'
        f'    <div class="up-dd-label">Detected domain</div>'
        f'    <div class="up-dd-value">{label} <span class="up-dd-conf">{confidence}</span></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_metadata_strip(df: pd.DataFrame, meta: dict) -> None:
    items = [
        ("Format", (meta.get("format") or _guess_format(meta.get("filename", "")) or "").upper()),
        ("Encoding", meta.get("encoding") or "UTF-8"),
        ("Separator", meta.get("separator") or "\u2014"),
        ("Size on disk", _format_bytes(meta.get("size_bytes", 0))),
        ("Loaded in", f"{meta.get('load_seconds', 0):.2f} s" if meta.get("load_seconds") else "\u2014"),
        ("Memory", _format_bytes(int(df.memory_usage(deep=True).sum()))),
    ]
    chunks = "".join(
        f'<div class="up-fm-item"><div class="up-fm-label">{l}</div><div class="up-fm-value">{_html_escape(str(v))}</div></div>'
        for l, v in items
    )
    st.markdown(f'<div class="up-file-meta">{chunks}</div>', unsafe_allow_html=True)


def _render_metric_cards(df: pd.DataFrame, meta: dict, sources_joined: int) -> None:
    n_rows = len(df)
    n_cols = len(df.columns)

    n_num = sum(1 for d in df.dtypes if pd.api.types.is_numeric_dtype(d))
    n_dt = sum(1 for d in df.dtypes if pd.api.types.is_datetime64_any_dtype(d))
    n_cat = n_cols - n_num - n_dt

    mem = _format_bytes(int(df.memory_usage(deep=True).sum()))
    sources_sub = "Single source" if sources_joined == 1 else f"{sources_joined} sources joined"

    cols = st.columns(4, gap="medium")
    cards = [
        ("Rows", f"{n_rows:,}", "After dedup"),
        ("Columns", f"{n_cols}", f"{n_num} num \xb7 {n_cat} cat \xb7 {n_dt} dt"),
        ("Sources", f"{sources_joined}", sources_sub),
        ("Memory", mem, "In-memory pandas"),
    ]
    for col, (label, value, sub) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="up-metric-card">'
                f'  <div class="up-metric-label">{label}</div>'
                f'  <div class="up-metric-value">{value}</div>'
                f'  <div class="up-metric-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_continue_cta() -> None:
    cols = st.columns([4, 1])
    with cols[0]:
        st.markdown(
            '<div class="up-cta-text">'
            '  <strong>Ready to configure your analysis?</strong>'
            '  <span>Confirm domain, pick a target, and choose your mode.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        if st.button("Continue to Configure \u2192", key="up_continue", type="primary",
                     use_container_width=True):
            project = project_service.get_active()
            if project:
                project.step_status["upload"] = "done"
                project.step_status["configure"] = "active"
                project_service.update(project)
            st.switch_page("pages/02_configure.py")


def _format_bytes(n: int) -> str:
    n = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def _guess_format(filename: str) -> str:
    if not filename:
        return ""
    return filename.rsplit(".", 1)[-1] if "." in filename else ""


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
