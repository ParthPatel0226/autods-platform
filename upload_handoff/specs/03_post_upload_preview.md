# Spec 03 — Post-Upload Preview

## Goal

After a successful load, render a rich preview that gives the user a complete first-look at the data before they advance to Configure. This includes things that won't appear elsewhere in the pipeline:

- Filename + detected domain pill (with confidence)
- File metadata strip (format, encoding, separator, size, load time, memory)
- 4 metric cards (rows / columns / sources joined / memory)
- Data quality glance (missing %, duplicates, constant cols, high cardinality) with status pills + bars
- Schema preview table (column / type / missing bar / unique count / sample values)
- Bottom CTA → Configure

## File: `dashboard/components/up_post_preview.py`

```python
"""Post-upload preview — header, metadata, metrics, quality, schema, CTA."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service
from dashboard.components.up_quality_glance import render as render_quality
from dashboard.components.up_schema_table import render as render_schema
from domains.domain_registry import detect_domain


DOMAIN_DISPLAY = {
    "healthcare":    ("🏥 Healthcare",   "var(--green)"),
    "finance":       ("💳 Finance",      "var(--cyan)"),
    "ecommerce":     ("🛒 E-commerce",   "var(--amber)"),
    "marketing":     ("📣 Marketing",    "var(--pink)"),
    "hr":            ("👥 HR",           "var(--pink)"),
    "manufacturing": ("⚙️ Manufacturing", "var(--violet)"),
    "generic":       ("📊 Generic",       "var(--violet)"),
}


def render(df: pd.DataFrame, meta: dict, sources_joined: int = 1) -> None:
    """Render the entire post-upload section.

    Args:
        df: The loaded dataframe.
        meta: Loader metadata dict — expected keys:
              filename, format, encoding, separator (optional), size_bytes,
              load_seconds (optional), source_type, source_provider (optional).
        sources_joined: How many sources were joined to produce df. 1 = no join.
    """
    if df is None or df.empty:
        st.info("No data loaded yet. Pick a source above.")
        return

    # Run domain detection — already cached in project_service after first call
    project = project_service.get_active()
    if project and project.detected_domain:
        domain_key = project.detected_domain
        confidence = project.metric_summary or "—"  # we'll stash confidence here
    else:
        domain_key, confidence = _detect_and_persist(df, project)

    _render_header(meta, domain_key, confidence)
    _render_metadata_strip(df, meta)
    _render_metric_cards(df, meta, sources_joined)
    render_quality(df)
    render_schema(df)
    _render_continue_cta()


def _detect_and_persist(df: pd.DataFrame, project) -> tuple[str, str]:
    try:
        result = detect_domain(df)
        # result expected to be {"domain": "healthcare", "confidence": 0.94} or similar
        domain_key = result.get("domain", "generic") if isinstance(result, dict) else (result or "generic")
        conf = result.get("confidence", 0.0) if isinstance(result, dict) else 0.0
    except Exception:
        domain_key, conf = "generic", 0.0

    confidence_str = f"{int(conf * 100)}% confident"

    if project is not None:
        project.detected_domain = domain_key
        project.n_rows = len(df)
        project.n_cols = len(df.columns)
        # we re-use metric_summary to stash confidence text — repurposed later by modeling
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


def _render_metadata_strip(df, meta: dict) -> None:
    items = [
        ("Format", (meta.get("format") or _guess_format(meta.get("filename", "")) or "").upper()),
        ("Encoding", meta.get("encoding") or "UTF-8"),
        ("Separator", meta.get("separator") or "—"),
        ("Size on disk", _format_bytes(meta.get("size_bytes", 0))),
        ("Loaded in", f"{meta.get('load_seconds', 0):.2f} s" if meta.get("load_seconds") else "—"),
        ("Memory", _format_bytes(int(df.memory_usage(deep=True).sum()))),
    ]
    chunks = "".join(
        f'<div class="up-fm-item"><div class="up-fm-label">{l}</div><div class="up-fm-value">{_html_escape(str(v))}</div></div>'
        for l, v in items
    )
    st.markdown(f'<div class="up-file-meta">{chunks}</div>', unsafe_allow_html=True)


def _render_metric_cards(df, meta: dict, sources_joined: int) -> None:
    n_rows = len(df)
    n_cols = len(df.columns)

    # Type breakdown
    n_num = sum(1 for d in df.dtypes if pd.api.types.is_numeric_dtype(d))
    n_dt = sum(1 for d in df.dtypes if pd.api.types.is_datetime64_any_dtype(d))
    n_cat = n_cols - n_num - n_dt

    mem = _format_bytes(int(df.memory_usage(deep=True).sum()))
    sources_sub = "Single source" if sources_joined == 1 else f"{sources_joined} sources joined"

    cols = st.columns(4, gap="medium")
    cards = [
        ("Rows", f"{n_rows:,}", "After dedup"),
        ("Columns", f"{n_cols}", f"{n_num} num · {n_cat} cat · {n_dt} dt"),
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
        if st.button("Continue to Configure →", key="up_continue", type="primary",
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
```

## File: `dashboard/components/up_quality_glance.py`

```python
"""Quality-at-a-glance — 4 indicator cards with bars and status pills."""
from __future__ import annotations
import streamlit as st
import pandas as pd


def render(df: pd.DataFrame) -> None:
    """4 indicators with status pills."""
    indicators = _compute(df)

    st.markdown(
        '<div class="up-quality">'
        '<h3 class="up-quality-title">🛡 Data quality at a glance</h3>'
        '<div class="up-quality-grid">',
        unsafe_allow_html=True,
    )
    for ind in indicators:
        st.markdown(
            f'<div class="up-qg-item">'
            f'  <div class="up-qg-label">{ind["label"]}</div>'
            f'  <div class="up-qg-value">'
            f'    <span class="up-qg-num">{ind["display"]}</span>'
            f'    <span class="up-qg-tag up-qg-{ind["status"]}">{ind["status_label"]}</span>'
            f'  </div>'
            f'  <div class="up-qg-bar"><div class="up-qg-fill up-qg-fill-{ind["status"]}" style="width:{ind["bar_pct"]}%"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div></div>', unsafe_allow_html=True)


def _compute(df: pd.DataFrame) -> list[dict]:
    n = len(df)
    if n == 0:
        return []

    miss_pct = float(df.isna().sum().sum()) / (n * len(df.columns)) * 100
    dups = int(df.duplicated().sum())
    constant_cols = sum(1 for c in df.columns if df[c].nunique(dropna=False) <= 1)
    high_card_cols = sum(1 for c in df.columns
                          if df[c].dtype == "object" and df[c].nunique(dropna=False) > min(1000, n * 0.5))

    return [
        {
            "label": "Missing values",
            "display": f"{miss_pct:.1f}%",
            "status": _missing_status(miss_pct),
            "status_label": _missing_label(miss_pct),
            "bar_pct": min(miss_pct * 2, 100),  # scale 50% missing → full bar
        },
        {
            "label": "Duplicates",
            "display": f"{dups:,}",
            "status": "good" if dups == 0 else "warn",
            "status_label": "None" if dups == 0 else f"{dups / n * 100:.1f}%",
            "bar_pct": min(dups / n * 100, 100) if n else 0,
        },
        {
            "label": "Constant columns",
            "display": str(constant_cols),
            "status": "good" if constant_cols == 0 else "warn",
            "status_label": "None" if constant_cols == 0 else "Review",
            "bar_pct": constant_cols / max(len(df.columns), 1) * 100,
        },
        {
            "label": "High cardinality",
            "display": str(high_card_cols),
            "status": "good" if high_card_cols == 0 else "warn",
            "status_label": "None" if high_card_cols == 0 else "Review",
            "bar_pct": high_card_cols / max(len(df.columns), 1) * 100,
        },
    ]


def _missing_status(pct: float) -> str:
    if pct < 5: return "good"
    if pct < 20: return "warn"
    return "bad"


def _missing_label(pct: float) -> str:
    if pct < 5: return "Good"
    if pct < 20: return "Review"
    return "High"
```

## File: `dashboard/components/up_schema_table.py`

```python
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
        miss_class = "up-miss-zero" if s["missing_pct"] == 0 else ("up-miss-high" if s["missing_pct"] > 30 else "up-miss-mid")
        rows_html += (
            f'<tr>'
            f'  <td class="up-col-name">{_html_escape(s["name"])}</td>'
            f'  <td><span class="up-dtype-pill up-dtype-{type_class}">{_html_escape(s["dtype_short"])}</span></td>'
            f'  <td>'
            f'    <div class="up-miss-bar">'
            f'      <div class="up-miss-track"><div class="up-miss-fill {miss_class}" style="width:{min(s["missing_pct"], 100)}%"></div></div>'
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
        if st.button(f"View all {len(df.columns)} columns",
                     key="up_schema_expand"):
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
    """First n unique non-null sample values, formatted compactly."""
    vals = s.dropna().unique()[:n]
    formatted = []
    for v in vals:
        if isinstance(v, str):
            formatted.append(f'"{v}"')
        elif pd.api.types.is_float(v):
            formatted.append(f"{v:.4g}")
        else:
            formatted.append(str(v))
    return ", ".join(formatted) if formatted else "—"


def _short_dtype(dtype: str) -> str:
    if "int" in dtype: return dtype  # int64 stays int64
    if "float" in dtype: return dtype
    if "datetime" in dtype: return "datetime"
    if "bool" in dtype: return "bool"
    if dtype == "object": return "object"
    return dtype


def _type_class(dtype: str) -> str:
    if "int" in dtype: return "int"
    if "float" in dtype: return "float"
    if "datetime" in dtype: return "object"
    if "bool" in dtype: return "bool"
    return "object"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Post-upload preview ============ */
.up-result-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-bottom: 24px; gap: 24px; flex-wrap: wrap;
}
.up-result-title h2 { font-family: var(--font-display); font-size: 30px; line-height: 1.1; }
.up-result-title h2 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.up-result-title p {
  font-size: 13px; color: var(--text-muted); margin-top: 4px;
  font-family: var(--font-mono); letter-spacing: 0.4px;
}
.up-domain-detected {
  display: flex; align-items: center; gap: 14px; padding: 12px 20px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; backdrop-filter: blur(14px);
}
.up-dd-label {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.2px;
  text-transform: uppercase; color: var(--text-faint);
}
.up-dd-value { display: flex; align-items: center; gap: 8px;
                font-size: 16px; font-weight: 500; }
.up-dd-conf {
  font-family: var(--font-mono); font-size: 11px; color: var(--green);
  padding: 3px 8px; background: rgba(52,211,153,0.1);
  border-radius: 999px; border: 1px solid rgba(52,211,153,0.3);
}

/* file metadata */
.up-file-meta {
  display: flex; flex-wrap: wrap; gap: 22px; padding: 16px 22px;
  background: rgba(139,92,246,0.03); border: 1px solid var(--border-subtle);
  border-radius: 12px; margin-bottom: 28px; backdrop-filter: blur(8px);
}
.up-fm-item { display: flex; flex-direction: column; gap: 2px; }
.up-fm-label {
  font-family: var(--font-mono); font-size: 9.5px;
  color: var(--text-faint); letter-spacing: 1px; text-transform: uppercase;
}
.up-fm-value { font-size: 12.5px; color: var(--text-secondary); font-family: var(--font-mono); }

/* metric cards */
.up-metric-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 20px; backdrop-filter: blur(14px);
  position: relative; overflow: hidden;
}
.up-metric-card::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  opacity: 0.7;
}
.up-metric-label {
  font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 1px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px;
}
.up-metric-value { font-family: var(--font-display); font-size: 36px; line-height: 1; }
.up-metric-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px;
                  font-family: var(--font-mono); }

/* quality glance */
.up-quality {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px; margin: 28px 0; backdrop-filter: blur(14px);
}
.up-quality-title {
  font-size: 14px; font-weight: 600; margin-bottom: 18px;
  color: var(--text-primary);
}
.up-quality-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.up-qg-item { display: flex; flex-direction: column; gap: 6px; }
.up-qg-label {
  font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1px;
}
.up-qg-value { display: flex; justify-content: space-between; align-items: baseline; }
.up-qg-num { font-family: var(--font-display); font-size: 22px; }
.up-qg-tag {
  font-family: var(--font-mono); font-size: 9.5px; padding: 2px 7px;
  border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase;
}
.up-qg-good { color: var(--green); background: rgba(52,211,153,0.1);
               border: 1px solid rgba(52,211,153,0.3); }
.up-qg-warn { color: var(--amber); background: rgba(251,191,36,0.1);
               border: 1px solid rgba(251,191,36,0.3); }
.up-qg-bad  { color: var(--red); background: rgba(248,113,113,0.1);
               border: 1px solid rgba(248,113,113,0.3); }
.up-qg-bar {
  height: 6px; background: rgba(139,92,246,0.1);
  border-radius: 3px; overflow: hidden;
}
.up-qg-fill { height: 100%; border-radius: 3px;
              box-shadow: 0 0 6px rgba(139,92,246,0.5); }
.up-qg-fill-good { background: linear-gradient(135deg, var(--green), var(--cyan)); }
.up-qg-fill-warn { background: linear-gradient(135deg, var(--amber), var(--red)); }
.up-qg-fill-bad  { background: linear-gradient(135deg, var(--red), var(--pink)); }

/* schema table */
.up-schema-title { font-size: 14px; font-weight: 600; margin-bottom: 14px;
                    color: var(--text-primary); margin-top: 28px; }
.up-schema-wrap {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; overflow: hidden; backdrop-filter: blur(14px);
  margin-bottom: 14px;
}
.up-schema { width: 100%; border-collapse: collapse; font-size: 13px; }
.up-schema thead {
  background: rgba(139,92,246,0.06);
  border-bottom: 1px solid var(--border-subtle);
}
.up-schema th {
  text-align: left; padding: 12px 18px; font-family: var(--font-mono);
  font-size: 10px; font-weight: 600; letter-spacing: 1.2px;
  text-transform: uppercase; color: var(--text-muted);
}
.up-schema td { padding: 12px 18px; border-bottom: 1px solid var(--border-subtle);
                 color: var(--text-secondary); }
.up-schema tr:last-child td { border-bottom: none; }
.up-schema tr:hover { background: rgba(139,92,246,0.04); }
.up-col-name { color: var(--text-primary); font-weight: 500; }
.up-dtype-pill {
  font-family: var(--font-mono); font-size: 10px; padding: 2px 8px;
  border-radius: 6px; letter-spacing: 0.4px;
}
.up-dtype-int    { color: var(--cyan);   background: rgba(34,211,238,0.1);  border: 1px solid rgba(34,211,238,0.3); }
.up-dtype-float  { color: var(--violet); background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); }
.up-dtype-object { color: var(--amber);  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.up-dtype-bool   { color: var(--green);  background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.up-miss-bar { display: inline-flex; align-items: center; gap: 8px; }
.up-miss-track { width: 60px; height: 4px;
                  background: rgba(139,92,246,0.08);
                  border-radius: 2px; overflow: hidden; }
.up-miss-fill { height: 100%; border-radius: 2px; background: var(--violet); }
.up-miss-zero { background: rgba(139,92,246,0.2); }
.up-miss-mid { background: var(--violet); }
.up-miss-high { background: var(--pink); }
.up-miss-pct { font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); }
.up-sample-vals { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); }

/* CTA */
.up-cta-text { display: flex; flex-direction: column; }
.up-cta-text strong { font-size: 15px; color: var(--text-primary); }
.up-cta-text span { font-size: 12px; color: var(--text-muted); }
```

## Notes on `detect_domain`

The exact return shape of `domains.domain_registry.detect_domain` may differ from the assumption above (`{"domain", "confidence"}`). The component falls back to `"generic"` and 0.0 if the call fails. **Verify the actual API and adapt `_detect_and_persist` accordingly** — but do NOT modify `domain_registry.py`.

If domain detection is expensive (re-ranking many features), wrap it in `@st.cache_data` so it doesn't re-run on every rerender.
