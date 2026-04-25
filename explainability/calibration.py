"""Calibration analysis for probabilistic classifiers.

Provides calibration curve data, reliability diagrams (Plotly), expected
calibration error (ECE), and Brier score.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def calibration_curve_data(
    y_true: np.ndarray | list,
    y_prob: np.ndarray | list,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Compute calibration curve data binned by predicted probability.

    Args:
        y_true: True binary labels (0/1).
        y_prob: Predicted probabilities for the positive class.
        n_bins: Number of equal-width bins.

    Returns:
        Dict with ``bin_edges``, ``mean_predicted``,
        ``fraction_positive``, and ``bin_counts``.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_prob, dtype=float)

    if len(y_t) == 0 or len(y_p) == 0:
        return {"bin_edges": [], "mean_predicted": [], "fraction_positive": [], "bin_counts": []}

    if len(y_t) != len(y_p):
        logger.error("y_true and y_prob length mismatch: %d vs %d", len(y_t), len(y_p))
        return {"error": "Length mismatch between y_true and y_prob."}

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    mean_predicted: list[float] = []
    fraction_positive: list[float] = []
    bin_counts: list[int] = []

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i < n_bins - 1:
            mask = (y_p >= lo) & (y_p < hi)
        else:
            mask = (y_p >= lo) & (y_p <= hi)

        count = int(mask.sum())
        bin_counts.append(count)

        if count > 0:
            mean_predicted.append(round(float(y_p[mask].mean()), 6))
            fraction_positive.append(round(float(y_t[mask].mean()), 6))
        else:
            mean_predicted.append(None)  # type: ignore[arg-type]
            fraction_positive.append(None)  # type: ignore[arg-type]

    return {
        "bin_edges": bin_edges.tolist(),
        "mean_predicted": mean_predicted,
        "fraction_positive": fraction_positive,
        "bin_counts": bin_counts,
    }


def calibration_plot(
    y_true: np.ndarray | list,
    y_prob: np.ndarray | list,
    model_name: str = "Model",
    n_bins: int = 10,
) -> Any:
    """Generate a reliability diagram as a Plotly figure.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities.
        model_name: Label for the model trace.
        n_bins: Number of calibration bins.

    Returns:
        ``plotly.graph_objects.Figure``.
    """
    import plotly.graph_objects as go

    data = calibration_curve_data(y_true, y_prob, n_bins)

    if "error" in data:
        fig = go.Figure()
        fig.update_layout(title=f"Calibration error: {data['error']}")
        return fig

    mp = data["mean_predicted"]
    fp = data["fraction_positive"]

    # Filter out None bins
    valid = [(m, f) for m, f in zip(mp, fp) if m is not None and f is not None]
    if not valid:
        fig = go.Figure()
        fig.update_layout(title="No valid calibration bins")
        return fig

    x_vals, y_vals = zip(*valid)

    fig = go.Figure()

    # Perfect calibration line
    fig.add_trace(go.Scatter(
        x=[0, 1],
        y=[0, 1],
        mode="lines",
        line=dict(dash="dash", color="gray", width=1),
        name="Perfect calibration",
    ))

    # Model calibration curve
    fig.add_trace(go.Scatter(
        x=list(x_vals),
        y=list(y_vals),
        mode="lines+markers",
        line=dict(color="rgba(99,110,250,0.9)", width=2),
        marker=dict(size=8),
        name=model_name,
    ))

    # Histogram of predictions
    counts = data["bin_counts"]
    max_count = max(counts) if counts else 1
    bin_edges = data["bin_edges"]
    bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(counts))]
    normalized_counts = [c / max_count * 0.3 for c in counts]

    fig.add_trace(go.Bar(
        x=bin_centers,
        y=normalized_counts,
        marker_color="rgba(99,110,250,0.2)",
        name="Prediction distribution",
        yaxis="y2",
    ))

    ece = expected_calibration_error(y_true, y_prob, n_bins)
    bs = brier_score(y_true, y_prob)

    fig.update_layout(
        title=f"Calibration Plot: {model_name} (ECE={ece:.4f}, Brier={bs:.4f})",
        xaxis_title="Mean predicted probability",
        yaxis_title="Fraction of positives",
        yaxis=dict(range=[0, 1]),
        yaxis2=dict(overlaying="y", side="right", showticklabels=False, range=[0, 1]),
        height=500,
        legend=dict(x=0.02, y=0.98),
    )

    return fig


def expected_calibration_error(
    y_true: np.ndarray | list,
    y_prob: np.ndarray | list,
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE).

    ECE is the weighted average of per-bin calibration gaps, where
    weights are proportional to the number of samples in each bin.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities.
        n_bins: Number of calibration bins.

    Returns:
        ECE value in [0, 1]. Lower is better calibrated.
    """
    data = calibration_curve_data(y_true, y_prob, n_bins)
    if "error" in data:
        return 1.0

    mp = data["mean_predicted"]
    fp = data["fraction_positive"]
    counts = data["bin_counts"]
    total = sum(counts)

    if total == 0:
        return 1.0

    ece = 0.0
    for m, f, c in zip(mp, fp, counts):
        if m is not None and f is not None and c > 0:
            ece += (c / total) * abs(f - m)

    return round(ece, 6)


def brier_score(
    y_true: np.ndarray | list,
    y_prob: np.ndarray | list,
) -> float:
    """Compute the Brier score (mean squared error of probabilities).

    Args:
        y_true: True binary labels (0/1).
        y_prob: Predicted probabilities.

    Returns:
        Brier score in [0, 1]. Lower is better.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_prob, dtype=float)

    if len(y_t) == 0:
        return 1.0

    return round(float(np.mean((y_t - y_p) ** 2)), 6)
