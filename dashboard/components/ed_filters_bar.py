"""Bottom filters bar — 3 columns horizontal."""
from __future__ import annotations
import streamlit as st


CHART_TYPES = [
    ("histogram", "Distributions"),
    ("box",       "Box plots"),
    ("scatter",   "Scatter"),
    ("bar",       "Bar charts"),
    ("heatmap",   "Heatmaps"),
]


def render() -> None:
    """Render the 3-column filters bar. State stored in ed_filter_* session keys."""
    charts = st.session_state.get("eda_charts", [])

    if "ed_filter_types" not in st.session_state:
        st.session_state["ed_filter_types"] = {t for t, _ in CHART_TYPES}
    if "ed_filter_significance" not in st.session_state:
        st.session_state["ed_filter_significance"] = 0.05
    if "ed_filter_column_kind" not in st.session_state:
        st.session_state["ed_filter_column_kind"] = "all"

    type_counts: dict[str, int] = {}
    for c in charts:
        t = c.get("type", "histogram").lower()
        type_counts[t] = type_counts.get(t, 0) + 1

    st.markdown('<section class="ed-filters">', unsafe_allow_html=True)

    cols = st.columns(3, gap="large")

    with cols[0]:
        st.markdown('<div class="ed-filters-group"><h4>Chart type</h4></div>', unsafe_allow_html=True)
        active = set(st.session_state["ed_filter_types"])
        changed = False
        for type_key, type_label in CHART_TYPES:
            count = type_counts.get(type_key, 0)
            checked = type_key in active
            new = st.checkbox(
                f"{type_label}  ({count})",
                value=checked,
                key=f"ed_filter_type_{type_key}",
            )
            if new != checked:
                if new:
                    active.add(type_key)
                else:
                    active.discard(type_key)
                changed = True
        if changed:
            st.session_state["ed_filter_types"] = active
            st.rerun()

    with cols[1]:
        st.markdown('<div class="ed-filters-group"><h4>Significance</h4></div>', unsafe_allow_html=True)
        new_sig = st.slider(
            "Significance threshold",
            min_value=0.01, max_value=0.10, step=0.01,
            value=float(st.session_state["ed_filter_significance"]),
            key="ed_filter_sig_slider",
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="ed-filter-slider-meta"><span>p &lt; 0.01</span><span>p &lt; 0.05</span><span>p &lt; 0.10</span></div>',
            unsafe_allow_html=True,
        )
        if new_sig != st.session_state["ed_filter_significance"]:
            st.session_state["ed_filter_significance"] = new_sig
            st.rerun()

    with cols[2]:
        st.markdown('<div class="ed-filters-group"><h4>Column</h4></div>', unsafe_allow_html=True)
        kind = st.radio(
            "Column type",
            options=["all", "numeric", "categorical"],
            index=["all", "numeric", "categorical"].index(st.session_state["ed_filter_column_kind"]),
            format_func=lambda k: {"all": "All columns", "numeric": "Numeric only", "categorical": "Categorical only"}[k],
            key="ed_filter_col_radio",
            label_visibility="collapsed",
        )
        if kind != st.session_state["ed_filter_column_kind"]:
            st.session_state["ed_filter_column_kind"] = kind
            st.rerun()

    st.markdown('</section>', unsafe_allow_html=True)
