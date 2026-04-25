"""Metric Cards -- renders KPI metric cards in a responsive grid.

Each card shows a large number, a label, and an optional delta indicator.
"""

from typing import Any

import streamlit as st

# Metric names that should be rendered as percentages (0-1 range)
_PCT_KEYWORDS = frozenset({
    "accuracy", "precision", "recall", "f1", "auc", "auc_roc", "auc_pr",
    "sensitivity", "specificity", "npv", "ppv", "r2", "adjusted_r2",
    "silhouette_score", "confidence", "missing_pct", "completeness",
    "gini_coefficient",
})

# Metric names where higher is worse
_INVERSE_METRICS = frozenset({
    "rmse", "mae", "mape", "log_loss", "brier_score", "max_error",
    "median_absolute_error", "davies_bouldin", "missing_pct",
})


def _format_value(name: str, value: float) -> str:
    """Format a metric value based on its name."""
    lower_name = name.lower().replace(" ", "_")

    if any(kw in lower_name for kw in _PCT_KEYWORDS):
        if 0 <= value <= 1:
            return f"{value:.1%}"
        return f"{value:.2f}%"

    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        if abs(value) >= 10:
            return f"{value:.1f}"
        return f"{value:.4f}"

    return str(value)


def _delta_color(name: str) -> str:
    """Return 'normal' or 'inverse' for st.metric delta_color."""
    lower_name = name.lower().replace(" ", "_")
    if any(kw in lower_name for kw in _INVERSE_METRICS):
        return "inverse"
    return "normal"


def render_metric_cards(
    metrics: dict[str, float | dict[str, Any]],
    columns: int = 4,
    title: str = "",
) -> None:
    """Display KPI metric cards in a grid.

    Args:
        metrics: Mapping of metric_name -> value, or metric_name -> dict with
                 keys ``value`` and optionally ``delta``.
        columns: Number of columns in the grid (default 4).
        title: Optional section title above the cards.
    """
    if not metrics:
        return

    if title:
        st.markdown(f"##### {title}")

    items = list(metrics.items())
    for row_start in range(0, len(items), columns):
        row_items = items[row_start : row_start + columns]
        cols = st.columns(columns)

        for col, (name, raw) in zip(cols, row_items):
            if isinstance(raw, dict):
                value = raw.get("value", 0)
                delta = raw.get("delta")
            else:
                value = raw
                delta = None

            display_name = name.replace("_", " ").title()
            display_value = _format_value(name, value)
            d_color = _delta_color(name)

            with col:
                if delta is not None:
                    delta_str = _format_value(name, delta)
                    st.metric(
                        label=display_name,
                        value=display_value,
                        delta=delta_str,
                        delta_color=d_color,
                    )
                else:
                    st.metric(label=display_name, value=display_value)
