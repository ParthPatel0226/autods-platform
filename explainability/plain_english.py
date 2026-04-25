"""Plain English explanation generator.

Converts SHAP values and feature importances into natural language
explanations suitable for non-technical stakeholders.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def explain_prediction(
    model: Any,
    instance: pd.Series,
    feature_names: list[str],
    shap_values: np.ndarray | list | None = None,
    top_n: int = 5,
) -> str:
    """Generate a plain English explanation for a single prediction.

    Uses SHAP values (preferred) or model feature importance to explain
    which features drive the prediction and in which direction.

    Args:
        model: Fitted estimator (used for prediction and fallback importance).
        instance: The observation to explain.
        feature_names: Feature names matching the model input.
        shap_values: SHAP values for this instance (1-D array).
            If a 2-D array is passed, the first row is used.
        top_n: Number of top contributing features to mention.

    Returns:
        Human-readable explanation string.
    """
    if model is None:
        return "Cannot generate explanation: model is not available."

    # Get prediction
    pred_str = _format_prediction(model, instance, feature_names)

    # Determine feature contributions
    if shap_values is not None:
        contributions = _contributions_from_shap(shap_values, feature_names, instance)
    elif hasattr(model, "feature_importances_"):
        contributions = _contributions_from_importance(model, feature_names, instance)
    else:
        return (
            f"{pred_str}\n\n"
            "Feature contribution details are not available for this model type."
        )

    if not contributions:
        return f"{pred_str}\n\nNo feature contributions could be determined."

    # Sort by absolute impact descending
    sorted_contribs = sorted(contributions, key=lambda c: abs(c["impact"]), reverse=True)
    top = sorted_contribs[:top_n]

    parts = [pred_str, ""]
    parts.append(f"This prediction is primarily driven by the following {len(top)} factors:")
    parts.append("")

    for i, c in enumerate(top, 1):
        direction = "increasing" if c["impact"] > 0 else "decreasing"
        magnitude = abs(c["impact"])
        parts.append(
            f"  {i}. {c['feature']} = {c['value']} "
            f"({direction} the prediction by {magnitude:.4f})"
        )

    # Summary sentence
    top_feat = top[0]
    parts.append("")
    parts.append(
        f"The strongest driver is '{top_feat['feature']}' with a value of "
        f"{top_feat['value']}, which {'pushes the prediction higher' if top_feat['impact'] > 0 else 'pushes the prediction lower'}."
    )

    return "\n".join(parts)


def explain_model_overall(
    global_importance: dict[str, float],
    metrics: dict[str, Any],
    problem_type: str,
) -> str:
    """Generate a plain English overview of the model.

    Args:
        global_importance: Feature name to importance score mapping.
        metrics: Model performance metrics dict.
        problem_type: ``"classification"`` or ``"regression"``.

    Returns:
        Human-readable model overview string.
    """
    lines: list[str] = []

    # Problem type
    if problem_type == "classification":
        lines.append("This is a classification model that predicts categorical outcomes.")
    elif problem_type == "regression":
        lines.append("This is a regression model that predicts continuous numerical outcomes.")
    else:
        lines.append(f"This is a {problem_type} model.")

    # Performance summary
    if metrics:
        lines.append("")
        lines.append("Performance summary:")
        for metric_name, value in metrics.items():
            if isinstance(value, float):
                lines.append(f"  - {metric_name}: {value:.4f}")
            else:
                lines.append(f"  - {metric_name}: {value}")

    # Top features
    if global_importance:
        sorted_features = sorted(global_importance.items(), key=lambda p: p[1], reverse=True)
        top = sorted_features[:5]
        lines.append("")
        lines.append(f"The model relies most heavily on {len(top)} features:")
        for i, (feat, score) in enumerate(top, 1):
            lines.append(f"  {i}. {feat} (importance: {score:.4f})")

        if len(sorted_features) > 5:
            remaining = len(sorted_features) - 5
            lines.append(f"  ... and {remaining} additional features with lower importance.")
    else:
        lines.append("\nFeature importance information is not available.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_prediction(model: Any, instance: pd.Series, feature_names: list[str]) -> str:
    """Format the model prediction as a readable string."""
    try:
        df = pd.DataFrame([instance.reindex(feature_names, fill_value=0)], columns=feature_names)
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(df)[0]
            pred = model.predict(df)[0]
            return f"Prediction: {pred} (probability: {proba.max():.2%})"
        pred = model.predict(df)[0]
        if isinstance(pred, (float, np.floating)):
            return f"Predicted value: {pred:.4f}"
        return f"Prediction: {pred}"
    except Exception:
        return "Prediction: unavailable"


def _contributions_from_shap(
    shap_values: np.ndarray | list,
    feature_names: list[str],
    instance: pd.Series,
) -> list[dict[str, Any]]:
    """Extract per-feature contributions from SHAP values."""
    arr = np.array(shap_values)
    if arr.ndim == 2:
        arr = arr[0]
    if len(arr) != len(feature_names):
        logger.warning("SHAP values length (%d) != feature count (%d)", len(arr), len(feature_names))
        return []

    contributions: list[dict[str, Any]] = []
    for i, feat in enumerate(feature_names):
        val = instance.get(feat, None)
        contributions.append({
            "feature": feat,
            "value": _format_value(val),
            "impact": float(arr[i]),
        })
    return contributions


def _contributions_from_importance(
    model: Any,
    feature_names: list[str],
    instance: pd.Series,
) -> list[dict[str, Any]]:
    """Fallback: use feature_importances_ as a proxy for contribution magnitude."""
    importances = model.feature_importances_
    if len(importances) != len(feature_names):
        return []
    contributions: list[dict[str, Any]] = []
    for i, feat in enumerate(feature_names):
        val = instance.get(feat, None)
        contributions.append({
            "feature": feat,
            "value": _format_value(val),
            "impact": float(importances[i]),
        })
    return contributions


def _format_value(val: Any) -> str:
    """Format a feature value for display."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "missing"
    if isinstance(val, float):
        return f"{val:.4f}" if abs(val) < 1000 else f"{val:.2f}"
    return str(val)
