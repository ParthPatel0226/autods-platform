# Spec 02 — Per-Column Transformations (Section 01)

## Layout

```
[Section header: "01 · Per-column transformations"]
[Tip strip]
[Quick actions row: ★ Auto-fill all · ↻ Reset · ◉ Show only missing · ⊘ Mark IDs]
[Filter row: search input + chips (All · Numeric · Categorical · Has missing)]
[Column accordion list — one card per column]
```

## File: `dashboard/components/fe_quick_actions.py`

```python
"""Quick-action mono pills above the column list."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    """4 quick actions that mutate `st.session_state['fe_choices']` in bulk.
    Each click triggers a rerun via `st.rerun()`.
    """
    df: pd.DataFrame | None = st.session_state.get("df")
    if df is None or df.empty:
        return

    project = project_service.get_active()
    fe_choices = st.session_state.setdefault("fe_choices", {})

    cols = st.columns(4, gap="small")
    with cols[0]:
        if st.button("★ Auto-fill all", key="fe_qa_auto", use_container_width=True):
            from agents.feature_engineer import recommend_choices
            try:
                recs = recommend_choices(df, project)  # adapt to actual signature
            except Exception:
                recs = _fallback_recommendations(df, project)
            fe_choices.update(recs)
            st.rerun()

    with cols[1]:
        if st.button("↻ Reset", key="fe_qa_reset", use_container_width=True):
            fe_choices.clear()
            st.rerun()

    with cols[2]:
        if st.button("◉ Show only missing", key="fe_qa_missing", use_container_width=True):
            st.session_state["fe_filter"] = "missing"
            st.rerun()

    with cols[3]:
        if st.button("⊘ Mark IDs", key="fe_qa_ids", use_container_width=True):
            for col in df.columns:
                if _looks_like_id(col, df[col]):
                    fe_choices[col] = {"action": "drop", "reason": "id_column"}
            st.rerun()


def _looks_like_id(name: str, series: pd.Series) -> bool:
    """Heuristic: column name contains 'id' AND is unique or near-unique."""
    name_l = name.lower()
    has_id = name_l == "id" or name_l.endswith("_id") or name_l.startswith("id_")
    if not has_id:
        return False
    nunique = series.nunique(dropna=True)
    return nunique >= len(series) * 0.95


def _fallback_recommendations(df: pd.DataFrame, project) -> dict:
    """Local heuristic when feature_engineer.recommend_choices is unavailable."""
    out = {}
    target = getattr(project, "target_column", None)
    for col in df.columns:
        if col == target:
            out[col] = {"action": "target"}
            continue
        if _looks_like_id(col, df[col]):
            out[col] = {"action": "drop", "reason": "id_column"}
            continue
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            out[col] = {
                "imputation": "median" if s.isna().any() else None,
                "encoding": None,
                "scaling": "robust",
                "outliers": "cap_iqr" if _has_outliers(s) else "keep",
            }
        elif pd.api.types.is_object_dtype(s):
            nunique = s.nunique(dropna=True)
            out[col] = {
                "imputation": "mode" if s.isna().any() else None,
                "encoding": "one_hot" if nunique <= 10 else "label",
                "scaling": None,
                "outliers": None,
            }
    return out


def _has_outliers(s: pd.Series) -> bool:
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        return False
    return ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).any()
```

## File: `dashboard/components/fe_filter_bar.py`

```python
"""Search + filter chips above the column list."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    cols = st.columns([4, 1, 1, 1, 1], gap="small")
    with cols[0]:
        st.text_input(
            "Search",
            key="fe_search",
            placeholder="Search columns by name...",
            label_visibility="collapsed",
        )

    chip_cols = [cols[1], cols[2], cols[3], cols[4]]
    chip_options = [
        ("all", "All"),
        ("numeric", "Numeric"),
        ("categorical", "Categorical"),
        ("missing", "Has missing"),
    ]
    current = st.session_state.get("fe_filter", "all")
    for col, (key, label) in zip(chip_cols, chip_options):
        with col:
            is_active = current == key
            if st.button(label, key=f"fe_chip_{key}", use_container_width=True,
                         disabled=is_active):
                st.session_state["fe_filter"] = key
                st.rerun()
```

## File: `dashboard/components/fe_column_card.py`

```python
"""Single column accordion card.

Collapsed: column name · type badge · missing % · decision pills · arrow
Expanded: 4 dropdowns (imputation/encoding/scaling/outliers) + reasoning box
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Any

from dashboard.components import project_service


# Choice option lists — must align with feature_tools options
IMPUTATION_OPTIONS = [
    ("none", "None (drop rows)"),
    ("mean", "Mean"),
    ("median", "Median"),
    ("mode", "Mode"),
    ("knn", "KNN (k=5)"),
    ("mice", "Iterative (MICE)"),
    ("forward_fill", "Forward fill"),
    ("flag_missing", "Flag missing"),
]
ENCODING_OPTIONS_NUM = [
    ("none", "None (numeric)"),
    ("binning_5", "Binning · 5 bins"),
    ("binning_10", "Binning · 10 bins"),
    ("log", "Log transform"),
]
ENCODING_OPTIONS_CAT = [
    ("none", "None"),
    ("label", "Label"),
    ("one_hot", "One-Hot"),
    ("ordinal", "Ordinal"),
    ("target", "Target encoding"),
    ("hash", "Hash"),
    ("extract_title", "Extract Title"),
    ("extract_deck", "Extract Deck"),
]
SCALING_OPTIONS = [
    ("none", "None"),
    ("standard", "Standard (z-score)"),
    ("minmax", "MinMax"),
    ("robust", "Robust"),
]
OUTLIER_OPTIONS = [
    ("keep", "Keep"),
    ("cap_iqr", "Cap (Winsorize IQR)"),
    ("cap_pct", "Cap (Percentile 1-99)"),
    ("remove", "Remove rows"),
    ("log", "Log transform"),
]


def render(col_name: str, df: pd.DataFrame, expanded_key: str) -> None:
    """Render one column card. Toggles expansion via session_state.

    The card uses a single Streamlit button keyed `fe_card_{col_name}` to toggle
    expansion. When expanded, four st.selectbox widgets render below.
    """
    project = project_service.get_active()
    fe_choices = st.session_state.setdefault("fe_choices", {})
    target = getattr(project, "target_column", None)
    is_target = (col_name == target)
    is_expanded = (st.session_state.get(expanded_key) == col_name)

    series = df[col_name]
    dtype = _classify_dtype(series)
    missing_pct = float(series.isna().mean() * 100)
    miss_class = "high" if missing_pct >= 20 else ("medium" if missing_pct > 0 else "low")

    choice = fe_choices.get(col_name, {})
    pills_html = _render_pills_html(choice, is_target)

    target_classes = " target" if is_target else ""
    expanded_classes = " expanded" if is_expanded else ""

    target_badge = ('<span class="fe-col-target-badge">★ Target</span>' if is_target else "")

    # Card header (always visible)
    st.markdown(
        f'<div class="fe-col{target_classes}{expanded_classes}">'
        f'  <div class="fe-col-head" id="fe_head_{col_name}">'
        f'    <div>'
        f'      <div class="fe-col-name">{_html_escape(col_name)}</div>'
        f'      {target_badge}'
        f'    </div>'
        f'    <div><span class="fe-type {dtype}">{_html_escape(_dtype_label(series))}</span></div>'
        f'    <div class="fe-miss {miss_class}">{missing_pct:.1f}%</div>'
        f'    <div class="fe-pills">{pills_html}</div>'
        f'    <span class="fe-arrow">▸</span>'
        f'  </div>',
        unsafe_allow_html=True,
    )

    # Toggle button (invisible label — overlays the head visually via CSS)
    if st.button("toggle", key=f"fe_card_{col_name}", label_visibility="collapsed"):
        st.session_state[expanded_key] = (None if is_expanded else col_name)
        st.rerun()

    if is_expanded:
        _render_detail(col_name, series, dtype, choice, fe_choices, is_target)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_detail(col_name: str, series: pd.Series, dtype: str,
                   choice: dict, fe_choices: dict, is_target: bool) -> None:
    if is_target:
        st.markdown(
            '<div class="fe-col-body">'
            '  <div class="fe-reasoning">Target column — no transformations applied. AutoDS will preserve this column as-is for modeling.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    enc_options = ENCODING_OPTIONS_NUM if dtype == "numeric" else ENCODING_OPTIONS_CAT

    # 4 dropdowns side-by-side
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        st.markdown('<label class="fe-field-label">Imputation</label>', unsafe_allow_html=True)
        imp_keys = [k for k, _ in IMPUTATION_OPTIONS]
        imp_labels = [l for _, l in IMPUTATION_OPTIONS]
        cur_imp = choice.get("imputation") or "none"
        idx = imp_keys.index(cur_imp) if cur_imp in imp_keys else 0
        new_imp = st.selectbox("Imputation", imp_labels, index=idx,
                               key=f"fe_imp_{col_name}", label_visibility="collapsed")
        choice["imputation"] = imp_keys[imp_labels.index(new_imp)]

    with col2:
        st.markdown('<label class="fe-field-label">Encoding</label>', unsafe_allow_html=True)
        enc_keys = [k for k, _ in enc_options]
        enc_labels = [l for _, l in enc_options]
        cur_enc = choice.get("encoding") or "none"
        idx = enc_keys.index(cur_enc) if cur_enc in enc_keys else 0
        new_enc = st.selectbox("Encoding", enc_labels, index=idx,
                               key=f"fe_enc_{col_name}", label_visibility="collapsed")
        choice["encoding"] = enc_keys[enc_labels.index(new_enc)]

    with col3:
        st.markdown('<label class="fe-field-label">Scaling</label>', unsafe_allow_html=True)
        scl_keys = [k for k, _ in SCALING_OPTIONS]
        scl_labels = [l for _, l in SCALING_OPTIONS]
        cur_scl = choice.get("scaling") or "none"
        idx = scl_keys.index(cur_scl) if cur_scl in scl_keys else 0
        new_scl = st.selectbox("Scaling", scl_labels, index=idx,
                               key=f"fe_scl_{col_name}", label_visibility="collapsed")
        choice["scaling"] = scl_keys[scl_labels.index(new_scl)]

    with col4:
        st.markdown('<label class="fe-field-label">Outliers</label>', unsafe_allow_html=True)
        out_keys = [k for k, _ in OUTLIER_OPTIONS]
        out_labels = [l for _, l in OUTLIER_OPTIONS]
        cur_out = choice.get("outliers") or "keep"
        idx = out_keys.index(cur_out) if cur_out in out_keys else 0
        new_out = st.selectbox("Outliers", out_labels, index=idx,
                               key=f"fe_out_{col_name}", label_visibility="collapsed")
        choice["outliers"] = out_keys[out_labels.index(new_out)]

    fe_choices[col_name] = choice

    # AI reasoning box
    reasoning = _generate_reasoning(col_name, series, dtype, choice)
    st.markdown(
        f'<div class="fe-reasoning">{_html_escape(reasoning)}</div>',
        unsafe_allow_html=True,
    )


# ---------------- helpers ----------------

def _classify_dtype(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    nunique = s.nunique(dropna=True)
    if pd.api.types.is_object_dtype(s) and nunique <= max(20, int(len(s) * 0.1)):
        return "categorical"
    return "text"


def _dtype_label(s: pd.Series) -> str:
    return str(s.dtype)


def _render_pills_html(choice: dict, is_target: bool) -> str:
    if is_target:
        return '<span class="fe-pill tgt">Target — no transform</span>'
    if choice.get("action") == "drop":
        reason = choice.get("reason", "drop")
        reason_label = "ID column" if reason == "id_column" else reason.replace("_", " ")
        return f'<span class="fe-pill drop">Drop · {reason_label}</span>'
    pills = []
    if choice.get("imputation") and choice["imputation"] != "none":
        pills.append(f'<span class="fe-pill imp">{_imp_label(choice["imputation"])}</span>')
    if choice.get("encoding") and choice["encoding"] != "none":
        pills.append(f'<span class="fe-pill enc">{_enc_label(choice["encoding"])}</span>')
    if choice.get("scaling") and choice["scaling"] != "none":
        pills.append(f'<span class="fe-pill scl">{_scl_label(choice["scaling"])}</span>')
    if choice.get("outliers") and choice["outliers"] not in ("none", "keep"):
        pills.append(f'<span class="fe-pill out">{_out_label(choice["outliers"])}</span>')
    return "".join(pills) if pills else '<span class="fe-pill" style="color:var(--text-muted);background:rgba(255,255,255,0.04);">—</span>'


def _imp_label(k: str) -> str:
    return dict(IMPUTATION_OPTIONS).get(k, k.title())


def _enc_label(k: str) -> str:
    for label_dict in (dict(ENCODING_OPTIONS_NUM), dict(ENCODING_OPTIONS_CAT)):
        if k in label_dict:
            return label_dict[k]
    return k.title()


def _scl_label(k: str) -> str:
    return dict(SCALING_OPTIONS).get(k, k.title())


def _out_label(k: str) -> str:
    return dict(OUTLIER_OPTIONS).get(k, k.title())


def _generate_reasoning(col_name: str, series: pd.Series, dtype: str, choice: dict) -> str:
    """Produce a one-paragraph plain-English rationale."""
    bits = []
    miss_pct = series.isna().mean() * 100
    if miss_pct > 0:
        bits.append(f"{col_name} has {miss_pct:.1f}% missing values.")
    if dtype == "numeric":
        skew = float(series.skew()) if series.notna().any() else 0.0
        if abs(skew) > 0.5:
            bits.append(f"Distribution is {'right' if skew > 0 else 'left'}-skewed (skew = {skew:.2f}).")
        if choice.get("imputation") == "median":
            bits.append("Median imputation is robust to skew.")
        if choice.get("scaling") == "robust":
            bits.append("Robust scaling handles outliers without removing them.")
        if choice.get("outliers") == "cap_iqr":
            bits.append("IQR capping preserves extreme but plausible values.")
    elif dtype == "categorical":
        nunique = series.nunique(dropna=True)
        bits.append(f"{nunique} unique values.")
        if choice.get("encoding") == "one_hot":
            bits.append("One-hot encoding is appropriate for low-cardinality unordered categories.")
        elif choice.get("encoding") == "label":
            bits.append("Label encoding is fine for binary or ordered categories.")
    return " ".join(bits) or "AutoDS recommends keeping this column as-is."


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/fe_columns_panel.py`

```python
"""Stack of column cards + quick actions + filter bar."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import (
    fe_quick_actions, fe_filter_bar, fe_column_card,
)

EXPANDED_KEY = "fe_expanded_col"


def render() -> None:
    df: pd.DataFrame | None = st.session_state.get("df")
    if df is None or df.empty:
        st.info("Upload data and complete EDA to start feature engineering.")
        return

    st.markdown(
        '<div class="fe-sec">'
        '  <div class="fe-sec-head">'
        '    <div class="fe-sec-num">01</div>'
        '    <div style="flex:1;">'
        f'      <div class="fe-sec-title">Per-column <em>transformations</em></div>'
        f'      <div class="fe-sec-meta">{len(df.columns)} columns · click any column to refine its decisions</div>'
        '    </div>'
        '  </div>'
        '  <div class="fe-sec-tip">'
        '    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="2" x2="12" y2="6"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="18" x2="12" y2="22"/></svg>'
        '    AutoDS pre-fills recommendations based on column type, missingness, distribution, and the active domain.'
        '  </div>',
        unsafe_allow_html=True,
    )

    fe_quick_actions.render()
    fe_filter_bar.render()

    # Filtered column iteration
    filtered = _filter_columns(df)
    st.markdown('<div class="fe-col-list">', unsafe_allow_html=True)
    for col_name in filtered:
        fe_column_card.render(col_name, df, EXPANDED_KEY)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def _filter_columns(df: pd.DataFrame) -> list[str]:
    search = (st.session_state.get("fe_search") or "").strip().lower()
    flt = st.session_state.get("fe_filter", "all")

    cols = list(df.columns)
    if search:
        cols = [c for c in cols if search in c.lower()]
    if flt == "numeric":
        cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    elif flt == "categorical":
        cols = [c for c in cols if pd.api.types.is_object_dtype(df[c])]
    elif flt == "missing":
        cols = [c for c in cols if df[c].isna().any()]
    return cols
```

## CSS additions

```css
/* Quick actions */
.fe-quick {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin-bottom: 14px;
}
/* Streamlit's button is wrapped — target via parent block selector */
.fe-quick + div [data-testid="stButton"] > button {
  background: rgba(139,92,246,0.08);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-secondary); letter-spacing: 0.4px;
}
.fe-quick + div [data-testid="stButton"] > button:hover {
  background: rgba(139,92,246,0.15);
  color: var(--text-primary); border-color: var(--border-default);
}

/* Filter bar */
[data-testid="stTextInput"][aria-label="Search"] input {
  background: rgba(7,9,26,0.4);
  border: 1px solid var(--border-subtle); border-radius: 10px;
  color: var(--text-primary); font-size: 13px;
}

/* Column accordion */
.fe-col-list { display: flex; flex-direction: column; gap: 8px; }
.fe-col {
  background: rgba(7,9,26,0.4);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.22s ease;
}
.fe-col:hover { border-color: var(--border-default); }
.fe-col.expanded {
  border-color: var(--border-strong);
  box-shadow: 0 0 30px -10px rgba(139,92,246,0.3);
}
.fe-col.target { border-left: 3px solid var(--violet); }

.fe-col-head {
  display: grid;
  grid-template-columns: 200px 84px 86px 1fr 24px;
  gap: 14px; align-items: center;
  padding: 14px 18px; cursor: pointer;
}
.fe-col-name {
  font-family: var(--font-mono); font-size: 13px; font-weight: 500;
  color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fe-col-target-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 10px;
  background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.30);
  color: var(--purple); font-family: var(--font-mono);
  font-size: 9.5px; font-weight: 600;
  letter-spacing: 0.6px; text-transform: uppercase;
  margin-top: 4px; width: fit-content;
}
.fe-type {
  display: inline-block; padding: 3px 9px; border-radius: 5px;
  font-family: var(--font-mono); font-size: 10px;
  font-weight: 500; letter-spacing: 0.4px; text-align: center;
  text-transform: uppercase;
}
.fe-type.numeric { background: rgba(34,211,238,0.12); color: var(--cyan); }
.fe-type.categorical { background: rgba(168,85,247,0.12); color: var(--purple); }
.fe-type.text { background: rgba(251,191,36,0.12); color: var(--amber); }
.fe-type.datetime { background: rgba(52,211,153,0.12); color: var(--green); }
.fe-type.boolean { background: rgba(236,72,153,0.12); color: var(--pink); }

.fe-miss {
  font-family: var(--font-mono); font-size: 12.5px; font-weight: 500;
  text-align: center;
}
.fe-miss.high { color: var(--red); }
.fe-miss.medium { color: var(--amber); }
.fe-miss.low { color: var(--text-muted); }

.fe-pills {
  display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;
}
.fe-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 999px;
  font-family: var(--font-mono); font-size: 10.5px;
  font-weight: 500; letter-spacing: 0.4px; white-space: nowrap;
  border: 1px solid transparent;
}
.fe-pill.imp { background: rgba(99,102,241,0.12); color: #8B92F8; border-color: rgba(99,102,241,0.22); }
.fe-pill.enc { background: rgba(168,85,247,0.12); color: #C28BF8; border-color: rgba(168,85,247,0.22); }
.fe-pill.scl { background: rgba(34,211,238,0.12); color: var(--cyan); border-color: rgba(34,211,238,0.22); }
.fe-pill.out { background: rgba(251,191,36,0.12); color: var(--amber); border-color: rgba(251,191,36,0.22); }
.fe-pill.drop { background: rgba(248,113,113,0.10); color: var(--red); border-color: rgba(248,113,113,0.22); }
.fe-pill.tgt { background: rgba(168,85,247,0.12); color: var(--purple); border-color: rgba(168,85,247,0.22); }
.fe-pill.new { background: rgba(52,211,153,0.10); color: var(--green); border-color: rgba(52,211,153,0.22); }

.fe-arrow {
  color: var(--text-muted); transition: transform 0.22s;
  font-family: var(--font-mono);
}
.fe-col.expanded .fe-arrow { transform: rotate(90deg); color: var(--violet); }

/* Expanded body — selectbox styling */
.fe-col.expanded [data-testid="stSelectbox"] > div > div {
  background: rgba(7,9,26,0.5);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}
.fe-field-label {
  display: block; font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 0.8px; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 6px;
}
.fe-reasoning {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 10px 14px;
  background: rgba(139,92,246,0.06);
  border: 1px solid var(--border-subtle); border-radius: 10px;
  font-size: 12px; color: var(--text-secondary); line-height: 1.55;
  margin-top: 14px;
}
.fe-reasoning::before {
  content: "✦"; color: var(--violet); flex-shrink: 0; margin-top: 1px;
}
```

## Mode-aware behavior

- **Auto mode:** On first render, `fe_quick_actions` automatically calls `Auto-fill all` if `fe_choices` is empty. The Configure phase still renders, but all decisions are pre-filled.
- **Guided mode:** Quick action `Auto-fill all` is suggested via a blinking border on the button (CSS class `fe-qa-suggest`). User clicks it manually.
- **Expert mode:** Decisions start blank. No auto-fill suggestion.

The mode is read from `project.analysis_mode` and applied in `pages/04_feature_engineering.py` (see Spec 08).
