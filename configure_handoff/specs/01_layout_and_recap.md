# Spec 01 — Layout & Dataset Recap

## Page structure

```
[Sidebar (Pipeline → Configure active)]
[Main content
  ├─ topbar (breadcrumb + theme toggle)
  ├─ hero (eyebrow + Instrument Serif title + subtitle)
  ├─ dataset recap strip (read-only)
  ├─ two-column grid:
  │   ├─ LEFT: scrolling sections 01–05
  │   │   01 Domain (cards + Why? explainer + compliance notice)
  │   │   02 Mode (flashcards + Auto unsure helper)
  │   │   03 Problem type (pills)
  │   │   04 Target & goal
  │   │   05 Excluded columns
  │   └─ RIGHT (sticky): Analysis Plan summary + pipeline estimate + Start Analysis button
  └─ end of page
]
```

Two-column grid uses `1fr 340px` on desktop, single column below 1100px.

## File: `dashboard/components/cf_dataset_recap.py`

```python
"""Dataset recap strip — read-only summary at the top of Configure."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    """Render the recap strip from active project + current df.

    Pulls:
        - filename → project.dataset_name
        - rows / cols → df shape
        - type breakdown → df.dtypes
        - missing % → df.isna()
        - sources joined → st.session_state.multisource.files (if any)
    """
    project = project_service.get_active()
    df = st.session_state.get("df")
    if project is None or df is None:
        return  # nothing to recap yet

    n_rows, n_cols = df.shape
    n_num = sum(1 for d in df.dtypes if pd.api.types.is_numeric_dtype(d))
    n_dt  = sum(1 for d in df.dtypes if pd.api.types.is_datetime64_any_dtype(d))
    n_cat = n_cols - n_num - n_dt

    miss_pct = float(df.isna().sum().sum()) / max(n_rows * n_cols, 1) * 100
    miss_label = "Acceptable" if miss_pct < 5 else ("Review" if miss_pct < 20 else "High")

    msm = st.session_state.get("multisource", {})
    sources = max(1, len([f for f in msm.get("files", []) if f.get("role") in ("primary", "secondary")]))
    sources_label = "Single" if sources == 1 else "Joined"

    items = [
        ("Dataset",  project.dataset_name or "—",
            None,  "filename"),
        ("Rows",     f"{n_rows:,}",
            None,  "number"),
        ("Columns",  f"{n_cols}",
            f"{n_num} num · {n_cat} cat · {n_dt} dt", "number"),
        ("Missing",  f"{miss_pct:.1f}%",
            miss_label, "number"),
        ("Sources",  f"{sources}",
            sources_label, "number"),
    ]

    cells_html = "".join(
        f'<div class="cf-recap-item">'
        f'  <div class="cf-recap-label">{label}</div>'
        f'  <div class="cf-recap-value{" cf-recap-fname" if kind == "filename" else ""}">{_html_escape(str(value))}</div>'
        f'  {f"<div class=\"cf-recap-sub\">{_html_escape(sub)}</div>" if sub else ""}'
        f'</div>'
        for label, value, sub, kind in items
    )
    st.markdown(f'<div class="cf-recap-strip">{cells_html}</div>',
                unsafe_allow_html=True)


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions to `shared_css.py`

```css
/* ============ Configure — hero + crumbs ============ */
.cf-crumbs {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-muted); letter-spacing: 0.4px; margin-bottom: 24px;
}
.cf-crumbs .sep { color: var(--text-faint); }
.cf-crumbs .cur { color: var(--text-primary); }

.cf-hero { margin-bottom: 28px; }
.cf-hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 8px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 999px;
  font-size: 11.5px; color: var(--text-secondary); margin-bottom: 16px;
  backdrop-filter: blur(12px); font-family: var(--font-mono);
  letter-spacing: 0.6px; text-transform: uppercase;
}
.cf-hero-eyebrow svg { width: 14px; height: 14px; color: var(--violet); }
.cf-hero h1 {
  font-family: var(--font-display); font-size: 56px;
  line-height: 1; letter-spacing: -0.5px; margin-bottom: 12px;
  color: var(--text-primary);
}
.cf-hero h1 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.cf-hero p { font-size: 16px; color: var(--text-muted); max-width: 720px; }

/* ============ Two-column layout ============ */
.cf-main-inner {
  display: grid; grid-template-columns: 1fr 340px; gap: 32px;
}
@media (max-width: 1100px) {
  .cf-main-inner { grid-template-columns: 1fr; }
}

/* ============ Section structure ============ */
.cf-section { margin-bottom: 56px; }
.cf-sec-header {
  display: flex; align-items: baseline; gap: 12px;
  margin-bottom: 6px; flex-wrap: wrap;
}
.cf-sec-num {
  font-family: var(--font-mono); font-size: 11px;
  padding: 3px 10px; background: rgba(139,92,246,0.08);
  border: 1px solid var(--border-subtle); border-radius: 999px;
  color: var(--violet); letter-spacing: 1px;
}
.cf-sec-title {
  font-family: var(--font-display); font-size: 30px; line-height: 1.1;
  color: var(--text-primary);
}
.cf-sec-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.cf-sec-sub {
  font-size: 14px; color: var(--text-muted);
  margin: 4px 0 22px;
}

/* ============ Dataset recap strip ============ */
.cf-recap-strip {
  display: flex; flex-wrap: wrap; gap: 22px;
  padding: 18px 22px; margin-bottom: 36px;
  background: rgba(139,92,246,0.03);
  border: 1px solid var(--border-subtle); border-radius: 14px;
  backdrop-filter: blur(8px);
}
.cf-recap-item {
  display: flex; flex-direction: column; gap: 2px; min-width: 90px;
}
.cf-recap-label {
  font-family: var(--font-mono); font-size: 9.5px;
  color: var(--text-faint); letter-spacing: 1px; text-transform: uppercase;
}
.cf-recap-value {
  font-family: var(--font-display); font-size: 22px;
  color: var(--text-primary); line-height: 1;
}
.cf-recap-value.cf-recap-fname {
  font-family: var(--font-mono); font-size: 14px;
}
.cf-recap-sub {
  font-size: 11px; color: var(--text-muted); margin-top: 2px;
  font-family: var(--font-mono);
}
```

## Implementation note

The recap strip relies on `project.dataset_name` being set by the upload page (handoff #2 already does this). If you find any `dataset_name` is None on a fresh project mid-flow, it means upload didn't write it — check 01_upload.py's `_handle_data_loaded` callback.
