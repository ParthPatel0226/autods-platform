"""Counterfactual explanations.

Answers "what minimal change to the input would flip the prediction?"
Uses a nearest-neighbor approach: find the closest training example whose
prediction differs from the query instance.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def generate_counterfactuals(
    model: Any,
    instance: pd.Series,
    X_train: pd.DataFrame,
    n_counterfactuals: int = 3,
    features_to_vary: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Find counterfactual examples from training data.

    Strategy: predict on all training rows, filter to those with a
    different prediction than ``instance``, then rank by Euclidean
    distance in feature space.

    Args:
        model: Fitted estimator.
        instance: Single observation (pd.Series) to explain.
        X_train: Training feature matrix.
        n_counterfactuals: Number of counterfactuals to return.
        features_to_vary: If provided, only consider distance on these
            features when ranking.  All features are still shown in
            output.

    Returns:
        List of dicts, each with ``original_values``,
        ``counterfactual_values``, ``changed_features``,
        ``original_pred``, ``new_pred``, and ``distance``.
    """
    if model is None or X_train.empty:
        logger.warning("Model or training data missing; cannot generate counterfactuals.")
        return []

    if len(instance) == 0:
        return []

    # Align instance to training columns
    common_cols = [c for c in X_train.columns if c in instance.index]
    if not common_cols:
        logger.warning("No common columns between instance and X_train.")
        return []

    X_aligned = X_train[common_cols].copy()
    inst_vals = instance[common_cols].copy()

    # Predict on instance and training set
    original_pred = _safe_predict(model, pd.DataFrame([inst_vals], columns=common_cols))
    try:
        train_preds = model.predict(X_aligned)
    except Exception as exc:
        logger.error("Counterfactual prediction on training data failed: %s", exc)
        return []

    # Filter to rows with a different prediction
    if _is_classification(original_pred, train_preds):
        diff_mask = train_preds != original_pred
    else:
        # Regression: require at least 10% relative change or 1 std
        std_pred = np.std(train_preds)
        threshold = max(0.1 * abs(float(original_pred)), 0.5 * float(std_pred))
        diff_mask = np.abs(train_preds - float(original_pred)) > threshold

    candidates = X_aligned[diff_mask]
    candidate_preds = train_preds[diff_mask]

    if len(candidates) == 0:
        logger.info("No counterfactual candidates found.")
        return []

    # Compute distances
    vary_cols = (
        [c for c in features_to_vary if c in common_cols]
        if features_to_vary
        else common_cols
    )
    inst_numeric = pd.to_numeric(inst_vals[vary_cols], errors="coerce").fillna(0).values
    cand_numeric = candidates[vary_cols].apply(pd.to_numeric, errors="coerce").fillna(0).values
    distances = np.sqrt(((cand_numeric - inst_numeric) ** 2).sum(axis=1))

    top_idx = np.argsort(distances)[:n_counterfactuals]

    results: list[dict[str, Any]] = []
    for idx in top_idx:
        cf_row = candidates.iloc[idx]
        changed = _identify_changes(inst_vals, cf_row, common_cols)
        results.append({
            "original_values": {k: _jsonable(v) for k, v in inst_vals.items()},
            "counterfactual_values": {k: _jsonable(v) for k, v in cf_row.items()},
            "changed_features": changed,
            "original_pred": _jsonable(original_pred),
            "new_pred": _jsonable(candidate_preds[idx]),
            "distance": round(float(distances[idx]), 6),
        })

    logger.info("Generated %d counterfactual(s).", len(results))
    return results


def format_counterfactual_explanation(cf: dict[str, Any]) -> str:
    """Format a single counterfactual dict as plain English.

    Args:
        cf: One element from ``generate_counterfactuals`` output.

    Returns:
        Human-readable string describing the changes.
    """
    if not cf or not cf.get("changed_features"):
        return "No meaningful changes identified."

    lines = [
        f"Original prediction: {cf.get('original_pred')}",
        f"Counterfactual prediction: {cf.get('new_pred')}",
        "",
        "Changes needed:",
    ]
    for change in cf["changed_features"]:
        feat = change["feature"]
        old = change["original"]
        new = change["counterfactual"]
        lines.append(f"  - {feat}: {old} -> {new}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_predict(model: Any, X: pd.DataFrame) -> Any:
    """Predict a single row, returning the raw prediction value."""
    try:
        return model.predict(X)[0]
    except Exception:
        return None


def _is_classification(original_pred: Any, train_preds: np.ndarray) -> bool:
    """Heuristic: if predictions are all integers or few unique values, it is classification."""
    unique = np.unique(train_preds)
    if len(unique) <= 20:
        return True
    if np.issubdtype(type(original_pred), np.integer):
        return True
    return False


def _identify_changes(
    original: pd.Series,
    counterfactual: pd.Series,
    columns: list[str],
) -> list[dict[str, Any]]:
    """Return list of features that differ between original and counterfactual."""
    changes: list[dict[str, Any]] = []
    for col in columns:
        o_val = original.get(col)
        c_val = counterfactual.get(col)
        if _values_differ(o_val, c_val):
            changes.append({
                "feature": col,
                "original": _jsonable(o_val),
                "counterfactual": _jsonable(c_val),
            })
    return changes


def _values_differ(a: Any, b: Any) -> bool:
    """Compare two values, handling NaN."""
    try:
        if pd.isna(a) and pd.isna(b):
            return False
        if pd.isna(a) or pd.isna(b):
            return True
    except (TypeError, ValueError):
        pass
    try:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(float(a) - float(b)) > 1e-9
    except (TypeError, ValueError):
        pass
    return a != b


def _jsonable(val: Any) -> Any:
    """Convert numpy types to JSON-serializable Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 6)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val
