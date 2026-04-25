"""SHAP-based model explainability.

Provides global explanations (summary bar plot, bee-swarm) and local
explanations (waterfall, force-style) using the ``shap`` library with
automatic explainer selection (TreeExplainer vs KernelExplainer).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core SHAP computation
# ---------------------------------------------------------------------------

def compute_shap_values(
    model: Any,
    X: pd.DataFrame,
    problem_type: str = "classification",
    max_rows: int = 500,
) -> dict[str, Any]:
    """Compute SHAP values for a fitted model.

    Args:
        model: A fitted scikit-learn compatible estimator.
        X: Feature matrix (numeric columns only are used).
        problem_type: ``"classification"`` or ``"regression"``.
        max_rows: Maximum rows to explain (subsampled if exceeded).

    Returns:
        Dict with keys ``global_importance``, ``top_features``,
        ``shap_values``, ``feature_names``, ``n_rows_explained``.
        Empty dict on failure.
    """
    try:
        import shap  # type: ignore[import]
    except ImportError:
        logger.warning("shap package not installed; returning empty results.")
        return {}

    if model is None:
        logger.warning("Model is None; cannot compute SHAP values.")
        return {}

    X_numeric = X.select_dtypes(include="number")
    if X_numeric.empty:
        logger.warning("No numeric columns in X; cannot compute SHAP.")
        return {}

    sample = X_numeric.iloc[:max_rows].copy()
    if len(sample) == 0:
        return {}

    try:
        explainer, shap_vals = _select_and_compute(model, sample, problem_type, shap)
    except Exception as exc:
        logger.error("SHAP computation failed: %s", exc)
        return {}

    arr = _normalize_shap_array(shap_vals)
    if arr is None:
        return {}

    feature_names = list(sample.columns)
    mean_abs = np.abs(arr).mean(axis=0)

    global_importance = {
        feat: round(float(val), 6)
        for feat, val in zip(feature_names, mean_abs)
    }
    sorted_pairs = sorted(global_importance.items(), key=lambda p: p[1], reverse=True)

    return {
        "global_importance": global_importance,
        "top_features": [
            {"feature": k, "mean_abs_shap": v} for k, v in sorted_pairs[:20]
        ],
        "shap_values": arr.tolist(),
        "feature_names": feature_names,
        "n_rows_explained": len(sample),
    }


def _select_and_compute(
    model: Any,
    sample: pd.DataFrame,
    problem_type: str,
    shap_mod: Any,
) -> tuple[Any, Any]:
    """Choose TreeExplainer or KernelExplainer and compute SHAP values."""
    if hasattr(model, "feature_importances_") and not hasattr(model, "coef_"):
        explainer = shap_mod.TreeExplainer(model)
        vals = explainer.shap_values(sample)
        return explainer, vals

    bg_size = min(50, len(sample))
    background = shap_mod.sample(sample, bg_size)
    if problem_type == "classification" and hasattr(model, "predict_proba"):
        explainer = shap_mod.KernelExplainer(model.predict_proba, background)
    else:
        explainer = shap_mod.KernelExplainer(model.predict, background)
    vals = explainer.shap_values(sample, nsamples=100)
    return explainer, vals


def _normalize_shap_array(shap_vals: Any) -> np.ndarray | None:
    """Normalize SHAP output to a 2-D numpy array."""
    if isinstance(shap_vals, list):
        if len(shap_vals) == 0:
            return None
        if len(shap_vals) == 2:
            arr = np.array(shap_vals[1])
        else:
            arr = np.mean([np.abs(np.array(v)) for v in shap_vals], axis=0)
    else:
        arr = np.array(shap_vals)

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


# ---------------------------------------------------------------------------
# Plotly visualizations
# ---------------------------------------------------------------------------

def shap_summary_plot(
    shap_values: list | np.ndarray,
    feature_names: list[str],
    max_features: int = 20,
    title: str = "SHAP Feature Importance",
) -> Any:
    """Create a beeswarm-style summary plot as a Plotly figure.

    Args:
        shap_values: 2-D array of SHAP values (n_samples x n_features).
        feature_names: Feature names matching columns.
        max_features: Max features to display.
        title: Plot title.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    arr = np.array(shap_values)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    mean_abs = np.abs(arr).mean(axis=0)
    indices = np.argsort(mean_abs)[-max_features:]

    sorted_names = [feature_names[i] for i in indices]
    sorted_vals = mean_abs[indices]

    fig = go.Figure(go.Bar(
        x=sorted_vals.tolist(),
        y=sorted_names,
        orientation="h",
        marker_color="rgba(99, 110, 250, 0.8)",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Mean |SHAP value|",
        yaxis_title="Feature",
        height=max(400, 25 * len(sorted_names)),
        margin=dict(l=200),
    )
    return fig


def shap_waterfall_plot(
    shap_values: list | np.ndarray,
    feature_names: list[str],
    instance_idx: int = 0,
    max_features: int = 15,
    title: str = "SHAP Waterfall — Single Prediction",
) -> Any:
    """Create a waterfall plot for a single prediction.

    Args:
        shap_values: 2-D SHAP values array.
        feature_names: Feature names.
        instance_idx: Row index to explain.
        max_features: Max features shown.
        title: Plot title.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    arr = np.array(shap_values)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if instance_idx >= len(arr):
        instance_idx = 0

    row = arr[instance_idx]
    abs_vals = np.abs(row)
    top_idx = np.argsort(abs_vals)[-max_features:][::-1]

    names = [feature_names[i] for i in top_idx]
    vals = [float(row[i]) for i in top_idx]
    colors = ["rgba(239,85,59,0.8)" if v > 0 else "rgba(99,110,250,0.8)" for v in vals]

    fig = go.Figure(go.Bar(
        x=vals,
        y=names,
        orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="SHAP value (impact on prediction)",
        height=max(400, 28 * len(names)),
        margin=dict(l=200),
    )
    return fig


def shap_bar_plot(
    global_importance: dict[str, float],
    max_features: int = 20,
    title: str = "Global Feature Importance (SHAP)",
) -> Any:
    """Horizontal bar chart of global SHAP importance.

    Args:
        global_importance: Feature name to mean |SHAP| mapping.
        max_features: Max features to show.
        title: Plot title.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    if not global_importance:
        fig = go.Figure()
        fig.update_layout(title="No SHAP importance data available")
        return fig

    sorted_items = sorted(global_importance.items(), key=lambda p: p[1], reverse=True)
    top = sorted_items[:max_features]
    names = [p[0] for p in reversed(top)]
    vals = [p[1] for p in reversed(top)]

    fig = go.Figure(go.Bar(
        x=vals,
        y=names,
        orientation="h",
        marker_color="rgba(0,204,150,0.8)",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Mean |SHAP value|",
        yaxis_title="Feature",
        height=max(400, 25 * len(names)),
        margin=dict(l=200),
    )
    return fig
