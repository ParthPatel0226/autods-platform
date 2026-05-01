"""Multi-source join section — primary + secondary files with auto-detected joins."""
from __future__ import annotations
import uuid
import streamlit as st

from dashboard.components.up_ms_adapter import MSAdapter, detect_join_keys


def render() -> None:
    """Render the collapsible multi-source join section."""
    state = _ensure_state()
    has_files = len(state["files"]) > 0

    expanded = st.session_state.get("up_ms_expanded", False)

    header_cols = st.columns([1, 12, 1])
    with header_cols[0]:
        st.markdown('<div class="up-ms-icon">\u2295</div>', unsafe_allow_html=True)
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
        toggle_label = "\u2303" if expanded else "\u2304"
        if st.button(toggle_label, key="up_ms_toggle", help="Toggle section"):
            st.session_state["up_ms_expanded"] = not expanded
            st.rerun()

    if not expanded:
        return

    st.markdown('<div class="up-ms-body">', unsafe_allow_html=True)

    if not state["files"]:
        st.markdown(
            '<p class="up-ms-help">Pick one file as the '
            '<strong style="color:var(--violet);">primary</strong>; '
            'others become secondary tables joined on detected keys.</p>',
            unsafe_allow_html=True,
        )

    for f in state["files"]:
        _render_file_row(f, state)

    if st.button("\uff0b Add another file", key="up_ms_add", use_container_width=True):
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

    secondaries = [f for f in state["files"] if f["role"] == "secondary"]
    primary = next((f for f in state["files"] if f["role"] == "primary"), None)

    if primary and secondaries:
        _render_join_config(primary, secondaries, state)

    if primary and secondaries:
        if st.button("Build joined dataset", type="primary", key="up_ms_execute"):
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
        st.markdown('<div class="up-ms-fileicon">\U0001f4c4</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            f'<div class="up-ms-fname">{_html_escape(f["filename"])}</div>'
            f'<div class="up-ms-fmeta">{f.get("source_type", "file").upper()} \xb7 {_format_size(f["size_bytes"])}</div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(f'<div class="up-ms-rows">{f["n_rows"]:,} rows</div>',
                    unsafe_allow_html=True)
    with cols[3]:
        sub = st.columns(2, gap="small")
        with sub[0]:
            if st.button("Primary", key=f"up_ms_prim_{f['id']}",
                         use_container_width=True, disabled=is_primary):
                _set_primary(f["id"], state)
                st.rerun()
        with sub[1]:
            if st.button("Secondary", key=f"up_ms_sec_{f['id']}",
                         use_container_width=True, disabled=not is_primary):
                _set_secondary(f["id"], state)
                st.rerun()
    with cols[4]:
        if st.button("\u2715", key=f"up_ms_del_{f['id']}", help="Remove"):
            _remove_file(f["id"], state)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_join_config(primary: dict, secondaries: list[dict], state: dict) -> None:
    st.markdown(
        '<div class="up-ms-join-config">'
        '<div class="up-ms-join-title">\U0001f517 Detected joins</div>',
        unsafe_allow_html=True,
    )

    adapter = _get_adapter()
    detected = state.setdefault("_detected", {})
    for sec in secondaries:
        key = (primary["id"], sec["id"])
        if key not in detected:
            detected[key] = detect_join_keys(adapter, primary["df_ref"], sec["df_ref"])

    for sec in secondaries:
        det = detected.get((primary["id"], sec["id"]), {})

        cols = st.columns([3, 0.5, 3, 2])
        with cols[0]:
            primary_cols = adapter.get_columns(primary["df_ref"])
            default_lk = det.get("left_key", primary_cols[0] if primary_cols else "")
            left_idx = primary_cols.index(default_lk) if default_lk in primary_cols else 0
            left_key = st.selectbox(
                f"{primary['filename']} key",
                primary_cols,
                index=left_idx,
                key=f"up_ms_lk_{sec['id']}",
                label_visibility="collapsed",
            )
        with cols[1]:
            st.markdown('<div class="up-ms-arrow">\u2192</div>', unsafe_allow_html=True)
        with cols[2]:
            sec_cols = adapter.get_columns(sec["df_ref"])
            default_rk = det.get("right_key", sec_cols[0] if sec_cols else "")
            right_idx = sec_cols.index(default_rk) if default_rk in sec_cols else 0
            right_key = st.selectbox(
                f"{sec['filename']} key",
                sec_cols,
                index=right_idx,
                key=f"up_ms_rk_{sec['id']}",
                label_visibility="collapsed",
            )
            conf_pct = int(det.get("confidence", 0.0) * 100)
            match_class = "up-detected-exact" if det.get("match_type") == "exact" else "up-detected-fuzzy"
            label = f"auto \xb7 {conf_pct}%" if det.get("match_type") == "exact" else f"fuzzy \xb7 {conf_pct}%"
            st.markdown(f'<span class="up-detected {match_class}">{label}</span>',
                        unsafe_allow_html=True)
        with cols[3]:
            join_type = st.selectbox(
                "Join",
                ["LEFT", "INNER", "RIGHT", "FULL"],
                key=f"up_ms_jt_{sec['id']}",
                label_visibility="collapsed",
            )

        _upsert_join(state, sec["id"], primary["df_ref"], sec["df_ref"],
                     left_key, right_key,
                     det.get("match_type", "fuzzy"), det.get("confidence", 0.0),
                     join_type.lower())

    st.markdown('</div>', unsafe_allow_html=True)


def _ingest_additional_file(uploaded_file, state: dict) -> None:
    import tempfile, pathlib
    suffix = pathlib.Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    adapter = _get_adapter()
    df_ref = adapter.add_source(tmp_path, name=uploaded_file.name)
    info = adapter.get_source_info(df_ref)

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
    state["_detected"] = {}


def _set_primary(file_id: str, state: dict) -> None:
    for f in state["files"]:
        f["role"] = "primary" if f["id"] == file_id else "secondary"
    state["_detected"] = {}


def _set_secondary(file_id: str, state: dict) -> None:
    target = next((f for f in state["files"] if f["id"] == file_id), None)
    if not target:
        return
    target["role"] = "secondary"
    if not any(f["role"] == "primary" for f in state["files"]) and state["files"]:
        state["files"][0]["role"] = "primary"
    state["_detected"] = {}


def _remove_file(file_id: str, state: dict) -> None:
    target = next((f for f in state["files"] if f["id"] == file_id), None)
    if not target:
        return
    state["files"] = [f for f in state["files"] if f["id"] != file_id]
    state["joins"] = [j for j in state["joins"] if j.get("secondary_id") != file_id]
    state.pop("_detected", None)
    if target["role"] == "primary" and state["files"]:
        state["files"][0]["role"] = "primary"


def _upsert_join(state: dict, secondary_id: str, left_ref: str, right_ref: str,
                 left_key: str, right_key: str,
                 match_type: str, confidence: float, join_type: str) -> None:
    state.setdefault("joins", [])
    for j in state["joins"]:
        if j["secondary_id"] == secondary_id:
            j.update(left_ref=left_ref, right_ref=right_ref,
                     left_key=left_key, right_key=right_key,
                     match_type=match_type, match_confidence=confidence,
                     join_type=join_type)
            return
    state["joins"].append({
        "secondary_id": secondary_id,
        "left_ref": left_ref,
        "right_ref": right_ref,
        "left_key": left_key,
        "right_key": right_key,
        "match_type": match_type,
        "match_confidence": confidence,
        "join_type": join_type,
    })


def _execute_join(state: dict) -> None:
    adapter = _get_adapter()
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
        with st.spinner("Building joined dataset\u2026"):
            joined_df = adapter.execute_joins(primary["df_ref"], join_specs)
            state["joined_df_id"] = adapter.last_result_id
            st.session_state["df"] = joined_df
            st.success(
                f"Joined {len(state['files'])} sources \u2192 "
                f"{len(joined_df):,} rows \xd7 {len(joined_df.columns)} columns"
            )
    except Exception as e:
        st.error(f"Join failed: {e}")


def _get_adapter() -> MSAdapter:
    if "_msm" not in st.session_state:
        st.session_state["_msm"] = MSAdapter()
    return st.session_state["_msm"]


def _format_size(bytes_: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}" if unit != "B" else f"{bytes_} B"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
