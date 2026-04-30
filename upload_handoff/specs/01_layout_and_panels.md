# Spec 01 — Layout & Source Panels

## Page structure

```
[Top breadcrumb + theme toggle]
[Hero — eyebrow chip + Instrument Serif title + subtitle]
[Source tabs — Manual | Cloud | Database | API & Web]
[Recent uploads strip (if any)]
[Active panel — drop zone OR connector form, with side info panel]
[Multi-source join section (collapsible)]
[Sample dataset gallery — 8 cards]
[Post-upload preview — only after a successful load]
[Bottom CTA — Continue to Configure]
```

## File: `dashboard/components/up_source_tabs.py`

```python
"""4-tab source switcher for the upload page."""
from __future__ import annotations
import streamlit as st


TABS = [
    ("manual",   "Manual upload",  "📁"),
    ("cloud",    "Cloud storage",  "☁️"),
    ("database", "Database",       "🗄️"),
    ("api",      "API & Web",      "🌐"),
]


def render() -> str:
    """Render the source tabs. Returns the active panel key.
    State is persisted in st.session_state["upload_panel"].
    """
    active = st.session_state.get("upload_panel", "manual")

    # Render tabs as a single horizontal pill group
    st.markdown('<div class="up-tabs">', unsafe_allow_html=True)
    cols = st.columns(len(TABS), gap="small")
    for col, (key, label, icon) in zip(cols, TABS):
        with col:
            css_class = "up-tab-active" if key == active else "up-tab"
            if st.button(f"{icon}  {label}", key=f"up_tab_{key}",
                         use_container_width=True):
                st.session_state["upload_panel"] = key
                st.rerun()
            # Apply class via marker — sibling selector in CSS
            st.markdown(
                f'<div data-up-tab="{key}" data-active="{1 if key == active else 0}"></div>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)
    return active
```

## File: `dashboard/components/up_panel_manual.py`

```python
"""Manual upload panel — drag-drop file uploader + format chips."""
from __future__ import annotations
import io
import streamlit as st

from data_connectors.universal_loader import load as universal_load


SUPPORTED_FORMATS = ["csv", "tsv", "xlsx", "xls", "parquet", "json", "jsonl", "feather", "orc"]


def render(on_loaded) -> None:
    """Render the manual upload panel.
    on_loaded(df, meta) is called when a file successfully loads.
    """
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown(
            '<div class="up-drop-zone">'
            '  <div class="up-drop-icon">'
            '    <svg width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
            '      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '      <polyline points="17 8 12 3 7 8"/>'
            '      <line x1="12" y1="3" x2="12" y2="15"/>'
            '    </svg>'
            '  </div>'
            '  <div class="up-drop-title">Drag and drop, or click to browse</div>'
            '  <div class="up-drop-sub">Up to 200 MB per file</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload file",
            type=SUPPORTED_FORMATS,
            label_visibility="collapsed",
            key="up_manual_uploader",
        )

        # Format chips
        chips_html = "".join(
            f'<span class="up-fmt-chip">{f.upper()}</span>' for f in SUPPORTED_FORMATS
        )
        st.markdown(f'<div class="up-fmt-chips">{chips_html}</div>', unsafe_allow_html=True)

        if uploaded is not None:
            with st.spinner(f"Loading {uploaded.name}..."):
                try:
                    df, meta = _load_uploaded(uploaded)
                    on_loaded(df, meta)
                    st.success(f"Loaded {uploaded.name} — {len(df):,} rows × {len(df.columns)} columns")
                except Exception as e:
                    st.error(f"Failed to load: {e}")

    with cols[1]:
        _render_info_panels()


def _load_uploaded(uploaded_file) -> tuple:
    """Save the uploaded file to a temp path and call universal_loader."""
    import tempfile
    from pathlib import Path
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    df, meta = universal_load(str(tmp_path))
    # Enrich meta with original filename and stats
    meta = {
        **(meta or {}),
        "filename": uploaded_file.name,
        "size_bytes": len(uploaded_file.getvalue()),
        "source_type": "manual",
        "source_path": str(tmp_path),
    }
    return df, meta


def _render_info_panels() -> None:
    st.markdown(
        '<div class="up-info-panel">'
        '  <h4>💡 Tips for best results</h4>'
        '  <ul>'
        '    <li>First row should be column headers</li>'
        '    <li>One row per observation</li>'
        '    <li>Mixed types in a column will be auto-detected and cleaned</li>'
        '    <li>UTF-8 encoding is preferred</li>'
        '  </ul>'
        '</div>'
        '<div class="up-info-panel">'
        '  <h4>🛡 Privacy</h4>'
        '  <p>Files stay in your session. Nothing is uploaded to third-party services.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
```

## File: `dashboard/components/up_panel_cloud.py`

```python
"""Cloud storage connector panel — S3 / GCS / Azure Blob."""
from __future__ import annotations
import streamlit as st

from data_connectors.connector_factory import get_connector


PROVIDERS = [
    ("s3",    "AWS S3",       "🪣"),
    ("gcs",   "Google GCS",   "☁️"),
    ("azure", "Azure Blob",   "🟦"),
]


def render(on_loaded) -> None:
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown('<div class="up-conn-card">', unsafe_allow_html=True)
        st.markdown(
            '<h3 class="up-conn-title">Connect to <em>cloud storage</em></h3>'
            '<p class="up-conn-sub">Pull objects directly from your cloud bucket. Read-only credentials only.</p>',
            unsafe_allow_html=True,
        )

        provider = _render_provider_tiles("up_cloud_prov", PROVIDERS, default="s3")

        c1, c2 = st.columns(2)
        with c1:
            bucket = st.text_input("Bucket name", placeholder="my-data-bucket", key="up_cloud_bucket")
        with c2:
            region = st.text_input("Region", value="us-east-1", key="up_cloud_region")

        path = st.text_input("Object key or prefix", placeholder="path/to/file.csv or folder/",
                              key="up_cloud_path")

        c3, c4 = st.columns(2)
        with c3:
            access_key = st.text_input("Access key", placeholder="AKIA…", key="up_cloud_access")
        with c4:
            secret_key = st.text_input("Secret key", type="password", placeholder="••••••••",
                                       key="up_cloud_secret")

        b1, b2 = st.columns([1, 1])
        with b1:
            test_clicked = st.button("Test connection", key="up_cloud_test")
        with b2:
            load_clicked = st.button("Load data", type="primary", key="up_cloud_load")

        if test_clicked or load_clicked:
            try:
                conn = get_connector("cloud", provider)
                conn.configure(
                    bucket=bucket, region=region, key=path,
                    access_key=access_key, secret_key=secret_key,
                )
                if test_clicked:
                    if conn.test_connection():
                        st.success("✓ Connected")
                    else:
                        st.error("Connection failed — check credentials and permissions")
                if load_clicked:
                    with st.spinner(f"Loading from {provider}..."):
                        df, meta = conn.load()
                        meta = {**(meta or {}),
                                "filename": path.split("/")[-1] or "cloud_data",
                                "source_type": "cloud",
                                "source_provider": provider}
                        on_loaded(df, meta)
                        st.success(f"Loaded {len(df):,} rows × {len(df.columns)} columns")
            except Exception as e:
                st.error(f"Failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        st.markdown(
            '<div class="up-info-panel">'
            '  <h4>🔒 Use IAM with least privilege</h4>'
            '  <p>Create a dedicated IAM user with read-only access to this bucket only.</p>'
            '</div>'
            '<div class="up-info-panel">'
            '  <h4>🛡 Credentials handling</h4>'
            '  <p>Keys are stored encrypted in your session and never logged.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_provider_tiles(state_key: str, providers, default: str) -> str:
    selected = st.session_state.get(state_key, default)
    st.markdown('<div class="up-providers">', unsafe_allow_html=True)
    cols = st.columns(len(providers))
    for col, (key, label, icon) in zip(cols, providers):
        with col:
            klass = "up-prov-selected" if key == selected else "up-prov"
            if st.button(f"{icon}\n{label}", key=f"{state_key}_{key}",
                         use_container_width=True):
                st.session_state[state_key] = key
                st.rerun()
            st.markdown(
                f'<div data-up-prov="{key}" data-selected="{1 if key == selected else 0}"></div>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)
    return selected
```

## File: `dashboard/components/up_panel_database.py`

Same pattern as `up_panel_cloud.py` but with these providers and extra fields:

```python
PROVIDERS = [
    ("postgres",  "PostgreSQL",   "🐘"),
    ("mysql",     "MySQL",        "🐬"),
    ("sqlserver", "SQL Server",   "🔷"),
    ("duckdb",    "DuckDB",       "🦆"),
    ("bigquery",  "BigQuery",     "📊"),
    ("snowflake", "Snowflake",    "❄️"),
    ("redshift",  "Redshift",     "🔴"),
]
```

Fields: host, port, database, schema (optional), username, password, query/table textarea.
Buttons: Test connection, Preview rows, Load data.
Backend call: `get_connector("database", provider).configure(...).load(query=...)`.

Side info: query best practices + SSL note.

## File: `dashboard/components/up_panel_api.py`

Same pattern with these providers:

```python
PROVIDERS = [
    ("rest",        "REST API",      "🌐"),
    ("scrape",      "Web scrape",    "🕸️"),
    ("kaggle",      "Kaggle",        "📈"),
    ("huggingface", "HuggingFace",   "🤗"),
    ("sheets",      "Google Sheets", "📑"),
    ("worldbank",   "World Bank",    "🌎"),
    ("fred",        "FRED",          "💵"),
    ("yahoo",       "Yahoo Finance", "📊"),
    ("census",      "US Census",     "🇺🇸"),
]
```

Fields shown depend on provider — branch with `if provider == "rest": ...`. Common fields: endpoint URL, method, auth type, token, response root path. Provider-specific fields handled in helper functions.

Side info: pagination behavior + rate limit reminders.

## CSS additions to `shared_css.py`

Append to the CSS string in `inject_shared_css()`:

```css
/* ============ Upload — source tabs ============ */
.up-tabs {
  display: flex; gap: 6px; margin-bottom: 24px; padding: 6px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; backdrop-filter: blur(14px); width: fit-content;
}
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="1"]) {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important;
  box-shadow: 0 0 18px rgba(139,92,246,0.4) !important;
  border: none !important;
}
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="0"]) {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: none !important;
}
[data-testid="stMain"] .stButton > button:has(+ div[data-up-tab][data-active="0"]):hover {
  color: var(--text-primary) !important;
  background: rgba(139,92,246,0.06) !important;
}

/* ============ Drop zone ============ */
.up-drop-zone {
  background: var(--bg-card); border: 2px dashed var(--border-default);
  border-radius: 20px; padding: 48px 32px 28px; text-align: center;
  backdrop-filter: blur(14px); transition: all 0.25s ease;
  margin-bottom: 14px;
}
.up-drop-zone:hover { border-color: var(--violet); background: rgba(139,92,246,0.06);
                       box-shadow: var(--shadow-glow); }
.up-drop-icon {
  width: 64px; height: 64px; margin: 0 auto 18px; border-radius: 50%;
  background: rgba(139,92,246,0.12); border: 1px solid var(--border-default);
  display: grid; place-items: center; color: var(--violet);
}
.up-drop-title { font-size: 18px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
.up-drop-sub { font-size: 13px; color: var(--text-muted); }
.up-fmt-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;
                 margin-top: 18px; padding: 0 12px; }
.up-fmt-chip {
  padding: 4px 10px; background: rgba(139,92,246,0.06);
  border: 1px solid var(--border-subtle); border-radius: 999px;
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-secondary); letter-spacing: 0.5px;
}

/* ============ Connector cards ============ */
.up-conn-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 28px; backdrop-filter: blur(14px);
}
.up-conn-title { font-family: var(--font-display); font-size: 22px; margin-bottom: 6px; }
.up-conn-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.up-conn-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 24px; }

/* Provider tile selected style */
.up-providers { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
                 gap: 8px; margin-bottom: 22px; }
[data-testid="stMain"] .stButton > button:has(+ div[data-up-prov][data-selected="1"]) {
  background: rgba(139,92,246,0.15) !important;
  border: 1px solid var(--violet) !important;
  box-shadow: 0 0 14px -4px var(--violet) !important;
  color: var(--text-primary) !important;
}
[data-testid="stMain"] .stButton > button:has(+ div[data-up-prov][data-selected="0"]) {
  background: rgba(139,92,246,0.06) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-secondary) !important;
}

/* ============ Side info panels ============ */
.up-info-panel {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 16px; padding: 18px 20px; backdrop-filter: blur(14px);
  margin-bottom: 16px;
}
.up-info-panel h4 { font-size: 13px; font-weight: 600; margin-bottom: 10px;
                     color: var(--text-primary); }
.up-info-panel p { font-size: 12.5px; color: var(--text-muted);
                    line-height: 1.55; }
.up-info-panel ul { list-style: none; padding: 0; margin: 0; }
.up-info-panel li { font-size: 12.5px; color: var(--text-secondary);
                     padding: 4px 0; padding-left: 14px; position: relative; }
.up-info-panel li::before { content: "•"; position: absolute; left: 4px; color: var(--violet); }
```

## Implementation notes

- The `:has(+ div[...])` sibling-selector trick ties Streamlit's button rendering to a tiny marker div with `data-*` attributes. If this CSS doesn't take effect in your Streamlit version, fall back to using emoji/text inside the button label to indicate state (e.g., `▸ Manual upload` for inactive vs `● Manual upload` for active).
- Each panel manages its **own** `session_state` keys (prefixed `up_<panel>_*`) so switching tabs preserves form values.
- All 4 panels expose the same `on_loaded(df, meta)` callback. The page (spec 05) wires this to `_handle_data_loaded()` which updates the project record and renders the post-upload preview.
