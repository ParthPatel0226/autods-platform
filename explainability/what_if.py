"""What-if analysis module.

Provides interactive exploration of how changing feature values affects
predictions. Supports single-change comparisons and sweep analysis
across a range of values for one feature.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def what_if_prediction(
    model: Any,
    baseline: pd.Series,
    changes: dict[str, Any],
    feature_names: list[str],
) -> dict[str, Any]:
    """Compare prediction before and after applying feature changes.

    Args:
        model: Fitted estimator.
        baseline: Original observation as a pd.Series.
        changes: Dict mapping feature name to new value.
        feature_names: Ordered list of feature names the model expects.

    Returns:
        Dict with ``baseline_pred``, ``modified_pred``, ``delta``,
        and ``changed_features`` details.
    """
    if model is None:
        return {"error": "Model is None."}
    if len(baseline) == 0:
        return {"error": "Baseline instance is empty."}

    baseline_aligned = _align_to_features(baseline, feature_names)
    baseline_pred = _safe_predict(model, baseline_aligned, feature_names)

    modified = baseline_aligned.copy()
    applied_changes: list[dict[str, Any]] = []
    for feat, new_val in changes.items():
        if feat in modified.index:
            old_val = modified[feat]
            modified[feat] = new_val
            applied_changes.append({
                "feature": feat,
                "old_value": _jsonable(old_val),
                "new_value": _jsonable(new_val),
            })
        else:
            logger.warning("Feature '%s' not found in baseline; skipping.", feat)

    modified_pred = _safe_predict(model, modified, feature_names)
    delta = modified_pred - baseline_pred if (
        baseline_pred is not None and modified_pred is not None
    ) else None

    return {
        "baseline_pred": _jsonable(baseline_pred),
        "modified_pred": _jsonable(modified_pred),
        "delta": _jsonable(delta),
        "changed_features": applied_changes,
    }


def what_if_sweep(
    model: Any,
    baseline: pd.Series,
    feature: str,
    values: list[Any],
    feature_names: list[str],
) -> list[dict[str, Any]]:
    """Sweep one feature across a range of values and predict each.

    Args:
        model: Fitted estimator.
        baseline: Original observation.
        feature: Feature name to sweep.
        values: List of values to substitute.
        feature_names: Feature names the model expects.

    Returns:
        List of dicts, each with ``value`` and ``prediction``.
    """
    if model is None:
        return [{"error": "Model is None."}]
    if feature not in baseline.index and feature not in feature_names:
        return [{"error": f"Feature '{feature}' not found."}]

    baseline_aligned = _align_to_features(baseline, feature_names)
    results: list[dict[str, Any]] = []

    for val in values:
        modified = baseline_aligned.copy()
        modified[feature] = val
        pred = _safe_predict(model, modified, feature_names)
        results.append({
            "value": _jsonable(val),
            "prediction": _jsonable(pred),
        })

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _align_to_features(series: pd.Series, feature_names: list[str]) -> pd.Series:
    """Reindex series to match expected feature names, filling missing with 0."""
    return series.reindex(feature_names, fill_value=0)


def _safe_predict(model: Any, instance: pd.Series, feature_names: list[str]) -> float | None:
    """Predict a single observation."""
    try:
        df = pd.DataFrame([instance], columns=feature_names)
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(df)
            return float(proba[0, -1])
        return float(model.predict(df)[0])
    except Exception as exc:
        logger.error("What-if prediction failed: %s", exc)
        return None


def _jsonable(val: Any) -> Any:
    """Convert numpy types to JSON-serializable Python types."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 6)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, float):
        return round(val, 6)
    return val
