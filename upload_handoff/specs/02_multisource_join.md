# Spec 02 — Multi-Source Join

## Goal

Promote multi-source joining out of the tiny collapsed expander into a proper section. User can:

1. Add multiple files (any source)
2. Mark exactly one as **Primary**, others as **Secondary**
3. See auto-detected join keys (with confidence: "auto · 100% match" green / "fuzzy · 94% match" amber)
4. Pick join type per secondary file (LEFT / INNER / RIGHT / FULL)
5. Execute the join and use the result as the project's working dataframe

Backend reuse: `data_connectors.multi_source_manager.MultiSourceManager` and `data_connectors.schema_matcher`.

## Data model

Tracked in session state under key `multisource`:

```python
st.session_state["multisource"] = {
    "files": [
        {
            "id": "uuid",
            "filename": "patients.csv",
            "df_ref": "duckdb_table_name",  # registered in DuckDB by multi_source_manager
            "n_rows": 24380,
            "n_cols": 38,
            "size_bytes": 1234567,
            "source_type": "manual",  # manual / cloud / database / api
            "role": "primary",        # primary / secondary
        },
        ...
    ],
    "joins": [
        {
            "secondary_id": "uuid",
            "left_key": "patient_id",   # primary's column
            "right_key": "patient_id",  # secondary's column
            "match_type": "exact",       # exact / fuzzy
            "match_confidence": 1.0,
            "join_type": "left",         # left / inner / right / full
        },
        ...
    ],
    "joined_df_id": None,    # set after successful join
}
```

## File: `dashboard/components/up_multisource_join.py`

```python
"""Multi-source join section — primary + secondary files with auto-detected joins."""
from __future__ import annotations
import uuid
import streamlit as st

from data_connectors.multi_source_manager import MultiSourceManager
from data_connectors import schema_matcher


def render() -> None:
    """Render the collapsible multi-source join section."""
    state = _ensure_state()
    has_files = len(state["files"]) > 0

    expanded = st.session_state.get("up_ms_expanded", has_files)

    # Header
    header_cols = st.columns([1, 12, 1])
    with header_cols[0]:
        st.markdown('<div class="up-ms-icon">⊕</div>', unsafe_allow_html=True)
    with header_cols[1]:
        tag = f'<span class="up-ms-tag">+{len(state["files"])} files</span>' if has_files else ""
        st.markdown(
            f'<div class="up-ms-header-text">'
            f'<h3>Multi-source join {tag}</h3>'
            f'<p>Combine multiple tables with auto-detected join keys.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with header_cols[2]:
        if st.button("⌃" if expanded else "⌄", key="up_ms_toggle", help="Toggle"):
            st.session_state["up_ms_expanded"] = not expanded
            st.rerun()

    if not expanded:
        return

    st.markdown('<div class="up-ms-body">', unsafe_allow_html=True)

    # File rows
    if not state["files"]:
        st.markdown(
            '<p class="up-ms-help">Pick one file as the <strong style="color:var(--violet);">primary</strong>; others become secondary tables joined on detected keys.</p>',
            unsafe_allow_html=True,
        )

    for f in state["files"]:
        _render_file_row(f, state)

    # Add another
    add_col = st.empty()
    add_clicked = add_col.button("＋ Add another file", key="up_ms_add",
                                  use_container_width=True)
    if add_clicked:
        st.session_state["up_ms_show_uploader"] = True

    if st.session_state.get("up_ms_show_uploader"):
        new_file = st.file_uploader(
            "Add a file to join",
            type=["csv", "tsv", "xlsx", "xls", "parquet", "json", "jsonl"],
            key="up_ms_uploader",
        )
        if new_file is not None:
            _ingest_additional_file(new_file, state)
            st.session_state["up_ms_show_uploader"] = False
            st.rerun()

    # Detected joins
    secondaries = [f for f in state["files"] if f["role"] == "secondary"]
    primary = next((f for f in state["files"] if f["role"] == "primary"), None)

    if primary and secondaries:
        _render_join_config(primary, secondaries, state)

    # Execute join
    if primary and secondaries and st.button("Build joined dataset", type="primary",
                                              key="up_ms_execute"):
        _execute_join(state)

    st.markdown('</div>', unsafe_allow_html=True)


def _ensure_state() -> dict:
    if "multisource" not in st.session_state:
        st.session_state["multisource"] = {"files": [], "joins": [], "joined_df_id": None}
    return st.session_state["multisource"]


def _render_file_row(f: dict, state: dict) -> None:
    is_primary = f["role"] == "primary"
    klass = "up-ms-file up-ms-primary" if is_primary else "up-ms-file"

    st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
    cols = st.columns([0.5, 4, 2, 2, 0.5])
    with cols[0]:
        st.markdown('<div class="up-ms-fileicon">📄</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            f'<div class="up-ms-fname">{_html_escape(f["filename"])}</div>'
            f'<div class="up-ms-fmeta">{f.get("source_type", "file").upper()} · {_format_size(f["size_bytes"])}</div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(f'<div class="up-ms-rows">{f["n_rows"]:,} rows</div>',
                    unsafe_allow_html=True)
    with cols[3]:
        # Role toggle — Primary / Secondary
        sub = st.columns(2, gap="small")
        with sub[0]:
            if st.button("Primary",
                         key=f"up_ms_prim_{f['id']}",
                         use_container_width=True,
                         disabled=is_primary):
                _set_primary(f["id"], state)
                st.rerun()
        with sub[1]:
            if st.button("Secondary",
                         key=f"up_ms_sec_{f['id']}",
                         use_container_width=True,
                         disabled=not is_primary):
                _set_secondary(f["id"], state)
                st.rerun()
    with cols[4]:
        if st.button("✕", key=f"up_ms_del_{f['id']}", help="Remove"):
            _remove_file(f["id"], state)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_join_config(primary: dict, secondaries: list[dict], state: dict) -> None:
    st.markdown(
        '<div class="up-ms-join-config">'
        '<div class="up-ms-join-title">🔗 Detected joins</div>',
        unsafe_allow_html=True,
    )

    # Compute / refresh join detections
    detected = state.setdefault("_detected", {})
    for sec in secondaries:
        key = (primary["id"], sec["id"])
        if key not in detected:
            detected[key] = schema_matcher.detect_join_keys(
                primary["df_ref"], sec["df_ref"]
            )

    # Render one row per secondary
    for sec in secondaries:
        det = detected[(primary["id"], sec["id"])]  # {"left_key": ..., "right_key": ..., "confidence": ..., "match_type": ...}

        cols = st.columns([3, 0.5, 3, 2])
        with cols[0]:
            primary_cols = _columns_for(primary["df_ref"])
            left_key = st.selectbox(
                f"{primary['filename']} key",
                primary_cols,
                index=primary_cols.index(det["left_key"]) if det["left_key"] in primary_cols else 0,
                key=f"up_ms_lk_{sec['id']}",
                label_visibility="collapsed",
            )
        with cols[1]:
            st.markdown('<div class="up-ms-arrow">→</div>', unsafe_allow_html=True)
        with cols[2]:
            sec_cols = _columns_for(sec["df_ref"])
            right_key = st.selectbox(
                f"{sec['filename']} key",
                sec_cols,
                index=sec_cols.index(det["right_key"]) if det["right_key"] in sec_cols else 0,
                key=f"up_ms_rk_{sec['id']}",
                label_visibility="collapsed",
            )
            # Confidence pill
            conf_pct = int(det.get("confidence", 1.0) * 100)
            match_class = "up-detected-exact" if det.get("match_type") == "exact" else "up-detected-fuzzy"
            label = f"auto · {conf_pct}%" if det.get("match_type") == "exact" else f"fuzzy · {conf_pct}%"
            st.markdown(f'<span class="up-detected {match_class}">{label}</span>',
                        unsafe_allow_html=True)
        with cols[3]:
            join_type = st.selectbox(
                "Join",
                ["LEFT", "INNER", "RIGHT", "FULL"],
                key=f"up_ms_jt_{sec['id']}",
                label_visibility="collapsed",
            )

        # Stash current selection back into state
        _upsert_join(state, sec["id"], left_key, right_key,
                      det.get("match_type", "exact"), det.get("confidence", 1.0),
                      join_type.lower())

    st.markdown('</div>', unsafe_allow_html=True)


def _columns_for(df_ref: str) -> list[str]:
    """Get column list for a registered DuckDB table reference."""
    mgr = _get_manager()
    return mgr.get_columns(df_ref)


def _ingest_additional_file(uploaded_file, state: dict) -> None:
    """Upload + register a file for multi-source joining."""
    import tempfile, pathlib
    suffix = pathlib.Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    mgr = _get_manager()
    df_ref = mgr.add_source(tmp_path, name=uploaded_file.name)
    info = mgr.get_source_info(df_ref)

    record = {
        "id": str(uuid.uuid4()),
        "filename": uploaded_file.name,
        "df_ref": df_ref,
        "n_rows": info["n_rows"],
        "n_cols": info["n_cols"],
        "size_bytes": len(uploaded_file.getvalue()),
        "source_type": "manual",
        "role": "primary" if not state["files"] else "secondary",
    }
    state["files"].append(record)
    state["_detected"] = {}  # invalidate detection cache


def _set_primary(file_id: str, state: dict) -> None:
    for f in state["files"]:
        f["role"] = "primary" if f["id"] == file_id else "secondary"
    state["_detected"] = {}


def _set_secondary(file_id: str, state: dict) -> None:
    target = next((f for f in state["files"] if f["id"] == file_id), None)
    if not target:
        return
    target["role"] = "secondary"
    if not any(f["role"] == "primary" for f in state["files"]):
        # Promote first remaining file to primary
        if state["files"]:
            state["files"][0]["role"] = "primary"
    state["_detected"] = {}


def _remove_file(file_id: str, state: dict) -> None:
    target = next((f for f in state["files"] if f["id"] == file_id), None)
    if not target:
        return
    state["files"] = [f for f in state["files"] if f["id"] != file_id]
    state["joins"] = [j for j in state["joins"] if j.get("secondary_id") != file_id]
    state["_detected"] = {}
    if target["role"] == "primary" and state["files"]:
        state["files"][0]["role"] = "primary"


def _upsert_join(state: dict, secondary_id: str, left_key: str, right_key: str,
                  match_type: str, confidence: float, join_type: str) -> None:
    state.setdefault("joins", [])
    for j in state["joins"]:
        if j["secondary_id"] == secondary_id:
            j.update(left_key=left_key, right_key=right_key,
                     match_type=match_type, match_confidence=confidence,
                     join_type=join_type)
            return
    state["joins"].append({
        "secondary_id": secondary_id,
        "left_key": left_key, "right_key": right_key,
        "match_type": match_type, "match_confidence": confidence,
        "join_type": join_type,
    })


def _execute_join(state: dict) -> None:
    mgr = _get_manager()
    primary = next((f for f in state["files"] if f["role"] == "primary"), None)
    if not primary:
        st.error("No primary file selected.")
        return
    join_specs = []
    for j in state["joins"]:
        sec = next((f for f in state["files"] if f["id"] == j["secondary_id"]), None)
        if not sec:
            continue
        join_specs.append({
            "left_ref": primary["df_ref"],
            "right_ref": sec["df_ref"],
            "left_key": j["left_key"],
            "right_key": j["right_key"],
            "join_type": j["join_type"],
        })
    try:
        with st.spinner("Building joined dataset..."):
            joined_df = mgr.execute_joins(primary["df_ref"], join_specs)
            state["joined_df_id"] = mgr.last_result_id
            st.session_state["df"] = joined_df  # the canonical working frame
            st.success(
                f"Joined {len(state['files'])} sources → {len(joined_df):,} rows × {len(joined_df.columns)} columns"
            )
    except Exception as e:
        st.error(f"Join failed: {e}")


def _get_manager() -> MultiSourceManager:
    if "_msm" not in st.session_state:
        st.session_state["_msm"] = MultiSourceManager()
    return st.session_state["_msm"]


def _format_size(bytes_: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}" if unit != "B" else f"{bytes_} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## Backend API expected

The component assumes these methods exist on `MultiSourceManager` and `schema_matcher`. **Verify the actual method names in the existing codebase before implementing** and adapt the component if names differ:

```python
# data_connectors/multi_source_manager.py — expected interface
class MultiSourceManager:
    def add_source(self, file_path: str, name: str = None) -> str: ...
    def get_source_info(self, df_ref: str) -> dict: ...   # returns {"n_rows", "n_cols", "columns"}
    def get_columns(self, df_ref: str) -> list[str]: ...
    def execute_joins(self, primary_ref: str, joins: list[dict]) -> pd.DataFrame: ...
    last_result_id: str  # set after execute_joins

# data_connectors/schema_matcher.py — expected interface
def detect_join_keys(left_ref: str, right_ref: str) -> dict:
    """Returns {'left_key': str, 'right_key': str, 'match_type': 'exact'|'fuzzy', 'confidence': 0..1}"""
```

If the existing implementations use different signatures, **wrap them in this interface** in a new helper file `dashboard/components/up_ms_adapter.py` rather than modifying `data_connectors/`.

## CSS additions

```css
/* ============ Multi-source join ============ */
.up-multisource {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 0; margin: 40px 0;
  backdrop-filter: blur(14px); overflow: hidden;
}
.up-ms-icon { font-size: 22px; color: var(--violet); padding-top: 6px; }
.up-ms-header-text h3 {
  font-family: var(--font-display); font-size: 22px; margin-bottom: 2px;
}
.up-ms-header-text p { font-size: 13px; color: var(--text-muted); }
.up-ms-tag {
  font-family: var(--font-mono); font-size: 9.5px; padding: 3px 8px;
  background: rgba(139,92,246,0.1); border: 1px solid var(--border-subtle);
  border-radius: 999px; color: var(--violet); letter-spacing: 0.6px;
  text-transform: uppercase; vertical-align: middle; margin-left: 8px;
}
.up-ms-body { padding: 0 24px 24px; }
.up-ms-help { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.up-ms-file {
  display: grid; grid-template-columns: auto 1fr auto auto auto;
  gap: 14px; align-items: center;
  padding: 12px 16px; background: rgba(139,92,246,0.04);
  border: 1px solid var(--border-subtle); border-radius: 12px;
  margin-bottom: 10px; transition: all 0.2s ease;
}
.up-ms-primary {
  background: rgba(139,92,246,0.1) !important;
  border-color: var(--border-strong) !important;
  box-shadow: 0 0 14px -4px var(--violet);
}
.up-ms-fileicon {
  width: 36px; height: 36px; border-radius: 9px;
  background: rgba(139,92,246,0.12); display: grid; place-items: center;
  color: var(--violet); font-size: 16px;
}
.up-ms-fname { font-size: 13.5px; font-weight: 500; color: var(--text-primary); }
.up-ms-fmeta { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); }
.up-ms-rows { font-family: var(--font-mono); font-size: 10.5px;
               color: var(--text-secondary); padding: 4px 8px;
               background: rgba(139,92,246,0.04); border-radius: 6px; }
.up-ms-arrow { color: var(--text-faint); text-align: center; }

.up-ms-join-config {
  background: rgba(139,92,246,0.04); border: 1px solid var(--border-subtle);
  border-radius: 12px; padding: 18px; margin-top: 22px;
}
.up-ms-join-title {
  font-size: 13px; font-weight: 600; margin-bottom: 12px;
  color: var(--text-primary);
}
.up-detected {
  display: inline-flex; align-items: center;
  font-family: var(--font-mono); font-size: 9.5px; padding: 2px 8px;
  border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase;
  margin-top: 4px;
}
.up-detected-exact {
  color: var(--green); background: rgba(52,211,153,0.08);
  border: 1px solid rgba(52,211,153,0.3);
}
.up-detected-fuzzy {
  color: var(--amber); background: rgba(251,191,36,0.08);
  border: 1px solid rgba(251,191,36,0.3);
}
```
