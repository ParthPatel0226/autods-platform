# Spec 06 — Bottom Filters Bar + Action Bar

## Goal

Below the chat composer, render two more sections:

1. **Filters bar** — full-width 3-column horizontal layout for filtering the results above (Chart type checkboxes · Significance slider · Column type filter)
2. **Action bar** — full-width 2-column grid (Next steps card + Run summary card)

Both are stacked at the bottom (per user's explicit feedback — no sidebar / sticky). When the user changes a filter, the page reruns and the relevant sections (charts grid, stats table) update.

## File: `dashboard/components/ed_filters_bar.py`

```python
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
    """Render the 3-column filters bar. State is in session_state under ed_filter_*."""
    charts = st.session_state.get("eda_charts", [])
    stats = st.session_state.get("eda_stats", [])

    # Initialize filter state
    if "ed_filter_types" not in st.session_state:
        st.session_state["ed_filter_types"] = {t for t, _ in CHART_TYPES}
    if "ed_filter_significance" not in st.session_state:
        st.session_state["ed_filter_significance"] = 0.05
    if "ed_filter_column_kind" not in st.session_state:
        st.session_state["ed_filter_column_kind"] = "all"

    # Count by type
    type_counts = {}
    for c in charts:
        t = c.get("type", "histogram").lower()
        type_counts[t] = type_counts.get(t, 0) + 1

    st.markdown('<section class="ed-filters">', unsafe_allow_html=True)

    cols = st.columns(3, gap="large")

    with cols[0]:
        st.markdown('<div class="ed-filters-group"><h4>Chart type</h4></div>', unsafe_allow_html=True)
        active = st.session_state["ed_filter_types"]
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
                st.session_state["ed_filter_types"] = active
                st.rerun()

    with cols[1]:
        st.markdown('<div class="ed-filters-group"><h4>Significance</h4></div>', unsafe_allow_html=True)
        new_sig = st.slider(
            "Significance threshold",
            min_value=0.01, max_value=0.10, step=0.01,
            value=st.session_state["ed_filter_significance"],
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
```

## File: `dashboard/components/ed_action_bar.py`

```python
"""Bottom action bar — 2-column (Next steps + Run summary)."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


def render(on_continue, on_reconfigure, on_export) -> None:
    """Render the bottom action bar.

    Args:
        on_continue() — Continue to Features
        on_reconfigure() — go back to Questions phase
        on_export() — export EDA report
    """
    project = project_service.get_active()

    st.markdown('<section class="ed-actions">', unsafe_allow_html=True)
    cols = st.columns([1.4, 1], gap="medium")

    # ----- Next steps card -----
    with cols[0]:
        st.markdown(
            '<div class="ed-actions-card">'
            '  <h4>Next steps</h4>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Continue to Features →", key="ed_action_continue",
                     type="primary", use_container_width=True):
            on_continue()
        if st.button("⟲ Reconfigure questions", key="ed_action_reconfig",
                     use_container_width=True):
            on_reconfigure()
        if st.button("⬇ Export EDA report", key="ed_action_export",
                     use_container_width=True):
            on_export()

    # ----- Run summary card -----
    with cols[1]:
        n_charts = len(st.session_state.get("eda_charts", []))
        n_stats = len(st.session_state.get("eda_stats", []))
        n_insights = len(st.session_state.get("eda_insights", []))
        runtime = st.session_state.get("ed_run_runtime_str", "—")
        cost = st.session_state.get("ed_run_cost_str", "—")

        st.markdown(
            f'<div class="ed-actions-card ed-actions-summary">'
            f'  <h4>Run summary</h4>'
            f'  <div class="ed-run-summary">'
            f'    <div>{n_charts} charts generated</div>'
            f'    <div>{n_stats} stat tests run</div>'
            f'    <div>{n_insights} insights extracted</div>'
            f'    <div>Runtime: {runtime}</div>'
            f'    <div>LLM cost: {cost}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</section>', unsafe_allow_html=True)
```

## CSS additions

```css
/* ============ Filters bar ============ */
.ed-filters {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 28px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px 22px;
  margin: 18px 0;
  backdrop-filter: blur(14px);
}
@media (max-width: 800px) { .ed-filters { grid-template-columns: 1fr; } }
.ed-filters-group h4 {
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 1.2px; text-transform: uppercase;
  color: var(--text-faint); margin-bottom: 12px; margin-top: 0;
}
.ed-filter-slider-meta {
  display: flex; justify-content: space-between;
  font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); margin-top: 4px;
}

/* Streamlit checkbox / slider / radio in filters */
.ed-filters [data-testid="stCheckbox"] label { font-size: 13px !important; color: var(--text-secondary); }
.ed-filters [data-testid="stSlider"] [role="slider"] { background: var(--violet) !important; }

/* ============ Action bar ============ */
.ed-actions {
  display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px;
  margin-bottom: 36px;
}
@media (max-width: 1024px) { .ed-actions { grid-template-columns: 1fr; } }
.ed-actions-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px;
  backdrop-filter: blur(14px);
}
.ed-actions-card h4 {
  font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 1.2px; text-transform: uppercase;
  color: var(--text-faint); margin-bottom: 10px;
}
.ed-actions-summary {
  background: rgba(139,92,246,0.04) !important;
  border-style: dashed !important;
}
.ed-actions-summary h4 { color: var(--violet) !important; }
.ed-run-summary {
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); line-height: 1.6;
}

/* Action buttons inside the Next steps card */
[data-testid="stMain"] .stButton > button[key="ed_action_continue"] {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 10px !important;
  padding: 12px 16px !important;
  font-size: 14px !important; font-weight: 500 !important;
  box-shadow: 0 0 20px rgba(139,92,246,0.4) !important;
  margin-bottom: 8px;
}
[data-testid="stMain"] .stButton > button[key="ed_action_continue"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 28px rgba(139,92,246,0.6) !important;
}
[data-testid="stMain"] .stButton > button[key="ed_action_reconfig"],
[data-testid="stMain"] .stButton > button[key="ed_action_export"] {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
  font-size: 13px !important;
  margin-top: 8px;
}
[data-testid="stMain"] .stButton > button[key="ed_action_reconfig"]:hover,
[data-testid="stMain"] .stButton > button[key="ed_action_export"]:hover {
  border-color: var(--border-strong) !important;
  color: var(--text-primary) !important;
}
```
