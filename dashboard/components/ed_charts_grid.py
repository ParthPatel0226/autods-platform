"""2-column charts grid — renders pre-computed chart specs."""
from __future__ import annotations
import streamlit as st


TYPE_PILL_CLASSES = {
    "histogram": ("dist", "Distribution"),
    "distribution": ("dist", "Distribution"),
    "boxplot": ("box", "Box plot"),
    "box": ("box", "Box plot"),
    "scatter": ("scatter", "Scatter"),
    "bar": ("bar", "Bar"),
    "heatmap": ("dist", "Heatmap"),
    "line": ("dist", "Line"),
}


def render() -> None:
    charts = st.session_state.get("eda_charts", [])
    if not charts:
        return

    # Apply type filter from session state
    active_types = st.session_state.get("ed_filter_types", set(TYPE_PILL_CLASSES.keys()))
    visible = [c for c in charts if c.get("type", "histogram").lower() in active_types]

    st.markdown(
        f'<section>'
        f'  <div class="ed-sec">'
        f'    <h3>All <em>charts</em></h3>'
        f'    <span class="ed-sec-meta">{len(visible)} of {len(charts)} visible</span>'
        f'  </div>'
        f'</section>',
        unsafe_allow_html=True,
    )

    if not visible:
        st.info("No charts match the current filters.")
        return

    # Render in pairs
    for i in range(0, len(visible), 2):
        cols = st.columns(2, gap="medium")
        for col, chart in zip(cols, visible[i:i + 2]):
            with col:
                _render_tile(chart)


def _render_tile(chart: dict) -> None:
    chart_type = chart.get("type", "histogram").lower()
    pill_class, pill_label = TYPE_PILL_CLASSES.get(chart_type, ("dist", chart_type.title()))

    title = _html_escape(chart.get("title", "Untitled"))
    sub = _html_escape(chart.get("subtitle", ""))
    caption = _html_escape(chart.get("interpretation", chart.get("caption", "")))

    fig = chart.get("figure")
    chart_id = chart.get("id", title)

    st.markdown(
        f'<div class="ed-chart-tile">'
        f'  <div class="ed-chart-head">'
        f'    <div>'
        f'      <div class="ed-chart-title">{title}</div>'
        f'      <div class="ed-chart-sub">{sub}</div>'
        f'    </div>'
        f'    <span class="ed-chart-type-pill {pill_class}">{pill_label}</span>'
        f'  </div>',
        unsafe_allow_html=True,
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=f"ed_chart_{chart_id}")
    st.markdown(
        f'  <div class="ed-chart-caption">{caption}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
