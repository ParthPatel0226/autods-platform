"""Chart Container -- Plotly chart wrapper with export buttons and data table.

Renders a Plotly figure inside a titled container with PNG / HTML / JSON
export options and a collapsible raw-data table.
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

try:
    import plotly.graph_objects as go  # type: ignore[import-untyped]
    import plotly.io as pio  # type: ignore[import-untyped]

    _HAS_PLOTLY = True
except ImportError:  # pragma: no cover
    _HAS_PLOTLY = False


def render_chart(
    fig: Any,
    title: str = "",
    key: str | None = None,
    show_export: bool = True,
    show_data: bool = True,
    height: int | None = None,
) -> None:
    """Render a Plotly figure with optional export buttons and data table.

    Args:
        fig: A ``plotly.graph_objects.Figure`` instance.
        title: Optional heading above the chart.
        key: Streamlit widget key prefix (auto-generated if ``None``).
        show_export: Whether to show PNG / HTML / JSON export buttons.
        show_data: Whether to show a collapsible data table.
        height: Override chart height in pixels.
    """
    if not _HAS_PLOTLY:
        st.error("Plotly is required for charts. Install with: pip install plotly")
        return

    widget_key = key or f"chart_{id(fig)}"

    if title:
        st.markdown(f"##### {title}")

    chart_config = {
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    }

    use_height = height or fig.layout.height or 450
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=chart_config,
        key=f"{widget_key}_plot",
        height=use_height,
    )

    if show_export:
        _render_export_buttons(fig, widget_key, title)

    if show_data:
        _render_data_table(fig, widget_key)


def _render_export_buttons(fig: Any, widget_key: str, title: str) -> None:
    """Render download buttons for PNG, HTML, and JSON."""
    col_png, col_html, col_json = st.columns(3)

    safe_title = (title or "chart").replace(" ", "_").lower()[:40]

    with col_png:
        try:
            png_bytes = pio.to_image(fig, format="png", width=1200, height=700)
            st.download_button(
                label="PNG",
                data=png_bytes,
                file_name=f"{safe_title}.png",
                mime="image/png",
                key=f"{widget_key}_dl_png",
                use_container_width=True,
            )
        except Exception:
            st.button("PNG (requires kaleido)", disabled=True, key=f"{widget_key}_dl_png_dis")

    with col_html:
        html_str = pio.to_html(fig, full_html=True, include_plotlyjs="cdn")
        st.download_button(
            label="HTML",
            data=html_str,
            file_name=f"{safe_title}.html",
            mime="text/html",
            key=f"{widget_key}_dl_html",
            use_container_width=True,
        )

    with col_json:
        json_str = json.dumps(fig.to_dict(), indent=2, default=str)
        st.download_button(
            label="JSON",
            data=json_str,
            file_name=f"{safe_title}.json",
            mime="application/json",
            key=f"{widget_key}_dl_json",
            use_container_width=True,
        )


def _render_data_table(fig: Any, widget_key: str) -> None:
    """Show the underlying data from the first trace in a collapsible table."""
    with st.expander("Show Data", expanded=False):
        try:
            import pandas as pd

            frames = []
            for trace in fig.data:
                trace_dict: dict[str, Any] = {}
                if hasattr(trace, "x") and trace.x is not None:
                    trace_dict["x"] = list(trace.x)
                if hasattr(trace, "y") and trace.y is not None:
                    trace_dict["y"] = list(trace.y)
                if hasattr(trace, "z") and trace.z is not None:
                    trace_dict["z"] = list(trace.z)
                if trace_dict:
                    min_len = min(len(v) for v in trace_dict.values())
                    trimmed = {k: v[:min_len] for k, v in trace_dict.items()}
                    frames.append(pd.DataFrame(trimmed))

            if frames:
                combined = pd.concat(frames, ignore_index=True)
                st.dataframe(combined, use_container_width=True, key=f"{widget_key}_data")
            else:
                st.caption("No tabular data available for this chart.")
        except Exception:
            st.caption("Unable to extract underlying data from this chart.")
