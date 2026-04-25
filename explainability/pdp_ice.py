"""Partial Dependence Plots (PDP) and Individual Conditional Expectation (ICE).

Generates Plotly figures showing how one or two features affect predictions,
holding all other features constant.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def partial_dependence_plot(
    model: Any,
    X: pd.DataFrame,
    feature: str,
    grid_resolution: int = 50,
    title: str | None = None,
) -> Any:
    """Generate a Partial Dependence Plot for a single feature.

    Args:
        model: Fitted estimator with ``predict`` (or ``predict_proba``).
        X: Feature matrix used for computing PDP.
        feature: Column name to vary.
        grid_resolution: Number of grid points along the feature axis.
        title: Optional plot title override.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    if feature not in X.columns:
        fig = go.Figure()
        fig.update_layout(title=f"Feature '{feature}' not found")
        return fig

    col = X[feature].dropna()
    if len(col) == 0:
        fig = go.Figure()
        fig.update_layout(title=f"Feature '{feature}' has no non-null values")
        return fig

    grid = np.linspace(float(col.min()), float(col.max()), grid_resolution)
    mean_preds = _compute_pdp(model, X, feature, grid)

    fig = go.Figure(go.Scatter(
        x=grid.tolist(),
        y=mean_preds,
        mode="lines",
        line=dict(color="rgba(99,110,250,0.9)", width=3),
        name="PDP",
    ))
    fig.update_layout(
        title=title or f"Partial Dependence: {feature}",
        xaxis_title=feature,
        yaxis_title="Predicted value (avg)",
        height=450,
    )
    return fig


def ice_plot(
    model: Any,
    X: pd.DataFrame,
    feature: str,
    num_ice_lines: int = 50,
    grid_resolution: int = 50,
    title: str | None = None,
) -> Any:
    """Generate an Individual Conditional Expectation plot.

    Args:
        model: Fitted estimator.
        X: Feature matrix.
        feature: Column to vary.
        num_ice_lines: Number of individual lines to draw.
        grid_resolution: Grid points along the feature axis.
        title: Optional title.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    if feature not in X.columns:
        fig = go.Figure()
        fig.update_layout(title=f"Feature '{feature}' not found")
        return fig

    col = X[feature].dropna()
    if len(col) == 0:
        fig = go.Figure()
        fig.update_layout(title=f"No non-null values for '{feature}'")
        return fig

    grid = np.linspace(float(col.min()), float(col.max()), grid_resolution)
    sample = X.sample(n=min(num_ice_lines, len(X)), random_state=42).copy()

    fig = go.Figure()
    for _, row in sample.iterrows():
        preds = _predict_over_grid(model, row, feature, grid, X.columns.tolist())
        fig.add_trace(go.Scatter(
            x=grid.tolist(),
            y=preds,
            mode="lines",
            line=dict(color="rgba(99,110,250,0.15)", width=1),
            showlegend=False,
            hoverinfo="skip",
        ))

    mean_preds = _compute_pdp(model, X, feature, grid)
    fig.add_trace(go.Scatter(
        x=grid.tolist(),
        y=mean_preds,
        mode="lines",
        line=dict(color="rgba(239,85,59,1)", width=3),
        name="PDP (mean)",
    ))

    fig.update_layout(
        title=title or f"ICE Plot: {feature}",
        xaxis_title=feature,
        yaxis_title="Predicted value",
        height=500,
    )
    return fig


def pdp_interact_plot(
    model: Any,
    X: pd.DataFrame,
    feature1: str,
    feature2: str,
    grid_resolution: int = 25,
    title: str | None = None,
) -> Any:
    """Generate a 2-D Partial Dependence contour plot.

    Args:
        model: Fitted estimator.
        X: Feature matrix.
        feature1: First feature (x-axis).
        feature2: Second feature (y-axis).
        grid_resolution: Grid points per axis.
        title: Optional title.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    for f in (feature1, feature2):
        if f not in X.columns:
            fig = go.Figure()
            fig.update_layout(title=f"Feature '{f}' not found")
            return fig

    g1 = np.linspace(float(X[feature1].min()), float(X[feature1].max()), grid_resolution)
    g2 = np.linspace(float(X[feature2].min()), float(X[feature2].max()), grid_resolution)

    z = np.zeros((grid_resolution, grid_resolution))
    base = X.mean(axis=0)

    for i, v1 in enumerate(g1):
        for j, v2 in enumerate(g2):
            row = base.copy()
            row[feature1] = v1
            row[feature2] = v2
            pred = _safe_predict_single(model, pd.DataFrame([row]))
            z[j, i] = pred

    fig = go.Figure(go.Contour(
        x=g1.tolist(),
        y=g2.tolist(),
        z=z.tolist(),
        colorscale="Viridis",
        colorbar_title="Prediction",
    ))
    fig.update_layout(
        title=title or f"PDP Interaction: {feature1} x {feature2}",
        xaxis_title=feature1,
        yaxis_title=feature2,
        height=500,
    )
    return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_predict_single(model: Any, X_single: pd.DataFrame) -> float:
    """Predict for a single-row DataFrame, returning a scalar."""
    try:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_single)
            return float(proba[0, -1])
        return float(model.predict(X_single)[0])
    except Exception:
        return 0.0


def _predict_over_grid(
    model: Any,
    base_row: pd.Series,
    feature: str,
    grid: np.ndarray,
    columns: list[str],
) -> list[float]:
    """Predict for one instance across a grid of feature values."""
    results: list[float] = []
    for val in grid:
        modified = base_row.copy()
        modified[feature] = val
        df_row = pd.DataFrame([modified], columns=columns)
        results.append(_safe_predict_single(model, df_row))
    return results


def _compute_pdp(
    model: Any,
    X: pd.DataFrame,
    feature: str,
    grid: np.ndarray,
) -> list[float]:
    """Compute average prediction at each grid point (PDP)."""
    sample = X.sample(n=min(100, len(X)), random_state=42).copy()
    mean_preds: list[float] = []
    for val in grid:
        temp = sample.copy()
        temp[feature] = val
        preds = _batch_predict(model, temp)
        mean_preds.append(float(np.mean(preds)))
    return mean_preds


def _batch_predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Batch predict, returning 1-D array."""
    try:
        if hasattr(model, "predict_proba"):
            return model.predict_proba(X)[:, -1]
        return model.predict(X)
    except Exception:
        return np.zeros(len(X))
