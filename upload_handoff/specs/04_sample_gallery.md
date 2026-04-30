# Spec 04 — Sample Gallery & Recent Uploads

## Goal

Two small components shown above (recent) and below (samples) the source panels.

## Component A: `dashboard/components/up_sample_gallery.py`

Curated sample dataset cards. Each card has: name, domain pill (color-coded), description, rows / cols / size stats. One-click "Load" button.

### Backend reuse

The existing `data_connectors/direct_input/sample_datasets.py` module exposes built-in samples. **Inspect that file first** to find the actual loader function (likely `get_sample(key)` or `load_sample(key)` returning a dataframe). Adapt the code below to match.

```python
"""Curated sample dataset gallery — 8 cards."""
from __future__ import annotations
import streamlit as st

from data_connectors.direct_input import sample_datasets


SAMPLES = [
    # (key,           display_name,        description,                                          domain_key,    rows,     cols,  size_kb)
    ("iris",          "Iris",              "Classic flower species dataset for multi-class classification.",   "classification", 150,    5,    8),
    ("titanic",       "Titanic",           "Passenger survival prediction — binary classification.",            "classification", 891,    12,   61),
    ("heart_disease", "Heart Disease",     "Patient risk factors and presence of heart disease.",               "healthcare",     303,    14,   19),
    ("credit_risk",   "Credit Risk",       "German credit data — predict default risk from applicant attrs.",   "finance",        1000,   21,   79),
    ("ca_housing",    "CA Housing",        "California house price prediction from census-block features.",     "regression",     20640,  9,    1400),
    ("online_retail", "Online Retail",     "UK online store transactions — basket analysis and customer LTV.",  "ecommerce",      541909, 8,    44000),
    ("wine_quality",  "Wine Quality",      "Predict wine quality scores from physicochemical features.",        "regression",     4898,   12,   263),
    ("attrition",     "Attrition",         "IBM employee attrition — predict who is likely to leave.",          "hr",             1470,   35,   228),
]

DOMAIN_PILL_CLASS = {
    "classification": "up-dom-classification",
    "regression":     "up-dom-regression",
    "healthcare":     "up-dom-healthcare",
    "finance":        "up-dom-finance",
    "ecommerce":      "up-dom-ecommerce",
    "hr":             "up-dom-hr",
}
DOMAIN_PILL_LABEL = {
    "classification": "Classification",
    "regression":     "Regression",
    "healthcare":     "Healthcare",
    "finance":        "Finance",
    "ecommerce":      "E-commerce",
    "hr":             "HR",
}


def render(on_loaded) -> None:
    """Render the sample gallery. on_loaded(df, meta) called when a sample is chosen."""
    st.markdown(
        '<div class="up-sec-divider">'
        '<span class="up-sec-label">Or start with a sample</span>'
        '<span class="up-sec-line"></span>'
        '</div>'
        '<h2 class="up-sec-title">Curated <em>sample datasets</em></h2>'
        '<p class="up-sec-sub">One-click load. Each dataset is paired with a domain so AutoDS configures itself appropriately.</p>',
        unsafe_allow_html=True,
    )

    # 4 columns × 2 rows
    rows = [SAMPLES[i:i + 4] for i in range(0, len(SAMPLES), 4)]
    for row in rows:
        cols = st.columns(4, gap="medium")
        for col, sample in zip(cols, row):
            with col:
                _render_sample_card(sample, on_loaded)


def _render_sample_card(sample, on_loaded) -> None:
    key, name, desc, domain, rows, cols, size_kb = sample
    pill_cls = DOMAIN_PILL_CLASS.get(domain, "up-dom-classification")
    pill_lbl = DOMAIN_PILL_LABEL.get(domain, "Generic")
    size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

    st.markdown(
        f'<div class="up-sample-card">'
        f'  <div class="up-sample-head">'
        f'    <div class="up-sample-name">{name}</div>'
        f'    <div class="up-sample-domain {pill_cls}">{pill_lbl}</div>'
        f'  </div>'
        f'  <div class="up-sample-desc">{desc}</div>'
        f'  <div class="up-sample-stats">'
        f'    <div class="up-sample-stat"><span class="v">{rows:,}</span>rows</div>'
        f'    <div class="up-sample-stat"><span class="v">{cols}</span>cols</div>'
        f'    <div class="up-sample-stat"><span class="v">{size_str}</span></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Load {name}", key=f"up_sample_{key}", use_container_width=True):
        with st.spinner(f"Loading {name}..."):
            try:
                df = sample_datasets.get_sample(key)  # ADAPT to actual function name
                meta = {
                    "filename": f"{key}.csv",
                    "format": "csv",
                    "encoding": "UTF-8",
                    "size_bytes": size_kb * 1024,
                    "source_type": "sample",
                    "source_provider": "built-in",
                }
                on_loaded(df, meta)
                st.success(f"Loaded {name}")
            except Exception as e:
                st.error(f"Failed to load sample: {e}")
```

## Component B: `dashboard/components/up_recent_uploads.py`

Pill strip listing the user's recently uploaded files (per-project). Click → re-load that file from its saved path.

```python
"""Recent uploads pill strip — shows last few files for fast re-pick."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render(on_loaded) -> None:
    """Render the recent uploads strip. Hidden if user has no recent files."""
    recent = project_service.get_recent_files(limit=5)
    if not recent:
        return

    st.markdown(
        '<div class="up-recent-strip">'
        '<div class="up-strip-label">Recent uploads</div>'
        '<div class="up-recent-grid">',
        unsafe_allow_html=True,
    )
    for entry in recent:
        # entry: {"filename", "path", "uploaded_at_relative", "project_id", "n_rows"}
        if st.button(
            f"📄 {entry['filename']}  ·  {entry['uploaded_at_relative']}",
            key=f"up_recent_{entry['filename']}_{entry['project_id'][:6]}",
        ):
            _load_recent(entry, on_loaded)
    st.markdown('</div></div>', unsafe_allow_html=True)


def _load_recent(entry, on_loaded) -> None:
    from data_connectors.universal_loader import load
    try:
        with st.spinner(f"Reloading {entry['filename']}..."):
            df, meta = load(entry["path"])
            meta = {**(meta or {}), "filename": entry["filename"],
                    "size_bytes": entry.get("size_bytes", 0),
                    "source_type": "recent"}
            on_loaded(df, meta)
            st.success(f"Reloaded {entry['filename']}")
    except FileNotFoundError:
        st.error(f"File no longer exists at {entry['path']}")
    except Exception as e:
        st.error(f"Failed to reload: {e}")
```

## `project_service.py` — add `get_recent_files`

Append to `dashboard/components/project_service.py`:

```python
def get_recent_files(limit: int = 5, user_id: str = "local") -> list[dict]:
    """Return recently uploaded files across all of the user's projects.

    Each entry: {filename, path, uploaded_at_relative, project_id, n_rows, size_bytes}
    Sorted by upload time, newest first. Empty if no files.
    """
    from datetime import datetime
    projects = list_all(user_id=user_id)
    files = []
    for p in projects:
        if p.dataset_path and p.dataset_name:
            files.append({
                "filename": p.dataset_name,
                "path": p.dataset_path,
                "project_id": p.id,
                "n_rows": p.n_rows or 0,
                "uploaded_at": p.updated_at,
            })
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)
    files = files[:limit]
    # Add relative time
    for f in files:
        try:
            t = datetime.fromisoformat(f["uploaded_at"].replace("Z", ""))
            delta = datetime.utcnow() - t
            s = int(delta.total_seconds())
            if s < 60: f["uploaded_at_relative"] = "just now"
            elif s < 3600: f["uploaded_at_relative"] = f"{s // 60} min ago"
            elif s < 86400: f["uploaded_at_relative"] = f"{s // 3600} hr ago"
            else: f["uploaded_at_relative"] = f"{s // 86400} day{'s' if s // 86400 != 1 else ''} ago"
        except (ValueError, AttributeError):
            f["uploaded_at_relative"] = "recently"
    return files
```

## CSS additions

```css
/* ============ Recent uploads ============ */
.up-recent-strip { margin: 0 0 32px; }
.up-strip-label {
  font-family: var(--font-mono); font-size: 11px;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text-faint); margin-bottom: 12px;
}
.up-recent-grid { display: flex; gap: 10px; flex-wrap: wrap; }
[data-testid="stMain"] .stButton > button[key^="up_recent_"] {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 14px !important; background: var(--bg-card) !important;
  border: 1px solid var(--border-default) !important; border-radius: 999px !important;
  font-size: 12.5px !important; cursor: pointer;
  backdrop-filter: blur(8px); transition: all 0.2s ease !important;
}
[data-testid="stMain"] .stButton > button[key^="up_recent_"]:hover {
  border-color: var(--border-strong) !important; transform: translateY(-1px);
}

/* ============ Sample gallery ============ */
.up-sec-divider {
  display: flex; align-items: center; gap: 14px; margin: 56px 0 24px;
}
.up-sec-label {
  font-family: var(--font-mono); font-size: 11px;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--violet); padding: 4px 12px;
  background: rgba(139,92,246,0.08); border-radius: 999px;
  border: 1px solid var(--border-subtle); white-space: nowrap;
}
.up-sec-line { height: 1px; flex: 1; background: var(--border-subtle); }
.up-sec-title { font-family: var(--font-display); font-size: 32px; margin-bottom: 6px; }
.up-sec-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.up-sec-sub { font-size: 14px; color: var(--text-muted); margin-bottom: 22px; }

.up-sample-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 20px; cursor: pointer;
  transition: all 0.25s ease; backdrop-filter: blur(14px);
  position: relative; overflow: hidden; height: 100%;
}
.up-sample-card::before {
  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  opacity: 0; transition: opacity 0.25s;
}
.up-sample-card:hover { transform: translateY(-3px); border-color: var(--border-strong);
                        box-shadow: var(--shadow-glow); }
.up-sample-card:hover::before { opacity: 1; }
.up-sample-head { display: flex; justify-content: space-between; align-items: flex-start;
                   margin-bottom: 8px; gap: 8px; }
.up-sample-name { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.up-sample-domain {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 3px 8px; border-radius: 999px; letter-spacing: 0.5px;
  text-transform: uppercase; flex-shrink: 0;
}
.up-dom-classification { color: var(--violet); border: 1px solid rgba(168,85,247,0.4); background: rgba(168,85,247,0.1); }
.up-dom-regression     { color: var(--cyan);   border: 1px solid rgba(34,211,238,0.4); background: rgba(34,211,238,0.1); }
.up-dom-healthcare     { color: var(--green);  border: 1px solid rgba(52,211,153,0.4); background: rgba(52,211,153,0.1); }
.up-dom-finance        { color: var(--cyan);   border: 1px solid rgba(34,211,238,0.4); background: rgba(34,211,238,0.1); }
.up-dom-ecommerce      { color: var(--amber);  border: 1px solid rgba(251,191,36,0.4); background: rgba(251,191,36,0.1); }
.up-dom-hr             { color: var(--pink);   border: 1px solid rgba(236,72,153,0.4); background: rgba(236,72,153,0.1); }
.up-sample-desc { font-size: 12.5px; color: var(--text-muted);
                   line-height: 1.5; margin-bottom: 14px; min-height: 36px; }
.up-sample-stats { display: flex; gap: 14px; padding-top: 12px;
                    border-top: 1px solid var(--border-subtle); }
.up-sample-stat { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-secondary); }
.up-sample-stat .v { color: var(--text-primary); font-weight: 500; padding-right: 4px; }
```

## Implementation notes

- The exact function name in `direct_input/sample_datasets.py` may not be `get_sample(key)`. **Open that file first** and use whatever it exposes. Common alternatives: `load_sample()`, `SAMPLE_DATASETS[key]`, etc.
- The 8 sample list above must match what the existing `sample_datasets` module actually has. If the existing module only ships 6 samples, slim the list to those 6. Do NOT add new samples to that module unless the user asks.
- Recent uploads only show projects with non-null `dataset_path` and `dataset_name` — this matches what the home grid filters for.
