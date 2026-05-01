"""Column exclusion grid for the Configure tab."""
from __future__ import annotations

import streamlit as st

PII_KEYWORDS = ["name", "email", "phone", "address", "zip", "postal", "ssn", "dob", "birth"]
ID_KEYWORDS = ["_id", "id_", "uuid", "guid", "index", "row_num", "record_id"]
LEAK_KEYWORDS = ["target", "label", "outcome", "result", "y_", "_y"]
HIGH_CARD_THRESHOLD = 0.95  # nunique/nrows ratio


def _suggest_reason(col: str, df, target: str) -> str | None:
    """Return a short reason string if column should be suggested for exclusion."""
    col_l = col.lower()
    if any(p in col_l for p in PII_KEYWORDS):
        return "PII"
    if any(p in col_l for p in ID_KEYWORDS):
        return "ID"
    if col_l == (target or "").lower():
        return None  # don't suggest excluding the target
    if any(p in col_l for p in LEAK_KEYWORDS) and col != target:
        return "potential leak"
    if df is not None and len(df) > 0:
        try:
            ratio = df[col].nunique() / len(df)
            if ratio >= HIGH_CARD_THRESHOLD:
                return "high cardinality"
        except Exception:
            pass
        try:
            if df[col].nunique() <= 1:
                return "constant"
        except Exception:
            pass
    return None


def render(df, target: str = "") -> set[str]:
    """Render column exclusion grid.

    State key: cf_excluded (set[str])
    Returns set of excluded column names.
    """
    if df is None:
        return set()

    columns = list(df.columns)
    init_key = f"cf_excl_initkey_{id(df)}_{target}"

    # Auto-initialise exclusions once per df/target combo
    if st.session_state.get("_cf_excl_init") != init_key:
        auto: set[str] = set()
        for col in columns:
            if _suggest_reason(col, df, target):
                auto.add(col)
        st.session_state["cf_excluded"] = auto
        st.session_state["_cf_excl_init"] = init_key

    excluded: set[str] = set(st.session_state.get("cf_excluded", set()))

    # Header row
    n_excl = len(excluded)
    st.markdown(
        f'<div class="cf-excl-header">'
        f'  <span>{len(columns)} columns &nbsp;·&nbsp; {n_excl} excluded</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("Clear exclusions", key="cf_excl_clear_all"):
        st.session_state["cf_excluded"] = set()
        st.rerun()

    # 4-column grid
    grid_cols = st.columns(4)
    for i, col in enumerate(columns):
        reason = _suggest_reason(col, df, target)
        is_excl = col in excluded

        badge = f'<span class="cf-excl-reason">{reason}</span>' if reason else ""
        btn_label = "✓ Excluded" if is_excl else ("⚠ Exclude?" if reason else "Include")
        btn_class = "cf-excl-active" if is_excl else ("cf-excl-suggested" if reason else "")

        with grid_cols[i % 4]:
            st.markdown(
                f'<div class="cf-excl-cell {btn_class}">'
                f'  <span class="cf-excl-colname">{col}</span>{badge}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(btn_label, key=f"cf_excl_btn_{col}", use_container_width=True):
                if col in excluded:
                    excluded.discard(col)
                else:
                    excluded.add(col)
                st.session_state["cf_excluded"] = excluded
                st.rerun()

    return set(st.session_state.get("cf_excluded", set()))
