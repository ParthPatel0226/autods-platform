"""Schema preview table with type pills, missing bars, and sample values."""
from __future__ import annotations
import streamlit as st
import pandas as pd


def render(df: pd.DataFrame, max_rows: int = 12) -> None:
    """Render a schema preview limited to max_rows columns."""
    schema = _build_schema(df, max_rows)

    st.markdown('<h3 class="up-schema-title">Schema preview</h3>', unsafe_allow_html=True)

    rows_html = ""
    for s in schema:
        type_class = _type_class(s["dtype"])
        if s["missing_pct"] == 0:
            miss_class = "up-miss-zero"
        elif s["missing_pct"] > 30:
            miss_class = "up-miss-high"
        else:
            miss_class = "up-miss-mid"
        rows_html += (
            f'<tr>'
            f'  <td class="up-col-name">{_html_escape(s["name"])}</td>'
            f'  <td><span class="up-dtype-pill up-dtype-{type_class}">{_html_escape(s["dtype_short"])}</span></td>'
            f'  <td>'
            f'    <div class="up-miss-bar">'
            f'      <div class="up-miss-track"><div class="up-miss-fill {miss_class}" style="width:{min(s["missing_pct"], 100):.1f}%"></div></div>'
            f'      <span class="up-miss-pct">{s["missing_pct"]:.1f}%</span>'
            f'    </div>'
            f'  </td>'
            f'  <td>{s["unique"]:,}</td>'
            f'  <td class="up-sample-vals">{_html_escape(s["samples"])}</td>'
            f'</tr>'
        )

    table_html = (
        '<div class="up-schema-wrap"><table class="up-schema">'
        '<thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Sample values</th></tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    if len(df.columns) > max_rows:
        if st.button(f"View all {len(df.columns)} columns", key="up_schema_expand"):
            render(df, max_rows=len(df.columns))


def _build_schema(df: pd.DataFrame, max_rows: int) -> list[dict]:
    n = max(len(df), 1)
    schema = []
    for col in df.columns[:max_rows]:
        dtype = str(df[col].dtype)
        miss = float(df[col].isna().sum()) / n * 100
        unique = int(df[col].nunique(dropna=False))
        samples = _sample_values(df[col])
        schema.append({
            "name": col,
            "dtype": dtype,
            "dtype_short": _short_dtype(dtype),
            "missing_pct": miss,
            "unique": unique,
            "samples": samples,
        })
    return schema


def _sample_values(s: pd.Series, n: int = 3) -> str:
    vals = s.dropna().unique()[:n]
    formatted = []
    for v in vals:
        if isinstance(v, str):
            formatted.append(f'"{v}"')
        elif pd.api.types.is_float(v):
            formatted.append(f"{v:.4g}")
        else:
            formatted.append(str(v))
    return ", ".join(formatted) if formatted else "\u2014"


def _short_dtype(dtype: str) -> str:
    if "int" in dtype:
        return dtype
    if "float" in dtype:
        return dtype
    if "datetime" in dtype:
        return "datetime"
    if "bool" in dtype:
        return "bool"
    if dtype == "object":
        return "object"
    return dtype


def _type_class(dtype: str) -> str:
    if "int" in dtype:
        return "int"
    if "float" in dtype:
        return "float"
    if "datetime" in dtype:
        return "object"
    if "bool" in dtype:
        return "bool"
    return "object"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
