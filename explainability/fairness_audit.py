"""Fairness audit module.

Computes group-level fairness metrics (demographic parity, equalized odds,
disparate impact ratio) and generates a plain-text summary report.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def run_fairness_audit(
    model: Any,
    X: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    sensitive_features: dict[str, pd.Series],
) -> dict[str, Any]:
    """Run a comprehensive fairness audit.

    Args:
        model: Fitted estimator with ``predict``.
        X: Feature matrix for prediction.
        y_true: True labels.
        sensitive_features: Mapping of attribute name to a Series of
            group labels aligned with ``X``.

    Returns:
        Dict with ``overall_metrics``, ``per_attribute`` breakdown, and
        ``recommendations``.
    """
    if model is None or X.empty:
        return {"error": "Model or feature data missing."}

    y_true_arr = np.asarray(y_true)
    try:
        y_pred = model.predict(X)
    except Exception as exc:
        logger.error("Fairness audit prediction failed: %s", exc)
        return {"error": str(exc)}

    results: dict[str, Any] = {"per_attribute": {}}

    for attr_name, attr_series in sensitive_features.items():
        attr_arr = np.asarray(attr_series)
        if len(attr_arr) != len(y_true_arr):
            logger.warning(
                "Attribute '%s' length mismatch (%d vs %d); skipping.",
                attr_name, len(attr_arr), len(y_true_arr),
            )
            continue

        attr_result = _audit_single_attribute(y_true_arr, y_pred, attr_arr, attr_name)
        results["per_attribute"][attr_name] = attr_result

    # Overall summary
    results["n_samples"] = int(len(y_true_arr))
    results["n_attributes_audited"] = len(results["per_attribute"])
    results["recommendations"] = _generate_recommendations(results["per_attribute"])

    logger.info("Fairness audit complete for %d attribute(s).", len(results["per_attribute"]))
    return results


def _audit_single_attribute(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
    attr_name: str,
) -> dict[str, Any]:
    """Compute fairness metrics for one sensitive attribute."""
    result: dict[str, Any] = {"group_metrics": {}}

    # Try fairlearn first
    try:
        from fairlearn.metrics import (  # type: ignore[import]
            demographic_parity_difference,
            equalized_odds_difference,
        )
        dpd = float(demographic_parity_difference(y_true, y_pred, sensitive_features=groups))
        eod = float(equalized_odds_difference(y_true, y_pred, sensitive_features=groups))
        result["demographic_parity_difference"] = round(dpd, 6)
        result["equalized_odds_difference"] = round(eod, 6)
        result["method"] = "fairlearn"
    except ImportError:
        dpd, eod = _manual_fairness_metrics(y_true, y_pred, groups)
        result["demographic_parity_difference"] = dpd
        result["equalized_odds_difference"] = eod
        result["method"] = "manual"

    # Per-group metrics
    unique_groups = np.unique(groups)
    for grp in unique_groups:
        mask = groups == grp
        if mask.sum() == 0:
            continue
        grp_key = str(grp)
        grp_pred = y_pred[mask]
        grp_true = y_true[mask]

        selection_rate = float(np.mean(grp_pred))
        tp_mask = (grp_true == 1)
        fp_mask = (grp_true == 0)
        tpr = float(np.mean(grp_pred[tp_mask])) if tp_mask.sum() > 0 else None
        fpr = float(np.mean(grp_pred[fp_mask])) if fp_mask.sum() > 0 else None

        result["group_metrics"][grp_key] = {
            "count": int(mask.sum()),
            "selection_rate": round(selection_rate, 6),
            "true_positive_rate": round(tpr, 6) if tpr is not None else None,
            "false_positive_rate": round(fpr, 6) if fpr is not None else None,
        }

    # Disparate impact ratio
    result["disparate_impact_ratio"] = _compute_disparate_impact(y_pred, groups)

    return result


def _manual_fairness_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
) -> tuple[float | None, float | None]:
    """Manual fallback for demographic parity and equalized odds differences."""
    unique_groups = np.unique(groups)
    selection_rates: list[float] = []
    tprs: list[float] = []

    for grp in unique_groups:
        mask = groups == grp
        if mask.sum() == 0:
            continue
        selection_rates.append(float(np.mean(y_pred[mask])))
        pos = (y_true[mask] == 1)
        if pos.sum() > 0:
            tprs.append(float(np.mean(y_pred[mask][pos])))

    dpd = round(max(selection_rates) - min(selection_rates), 6) if selection_rates else None
    eod = round(max(tprs) - min(tprs), 6) if len(tprs) >= 2 else None
    return dpd, eod


def disparate_impact_ratio(
    y_pred: np.ndarray | pd.Series,
    sensitive_col: np.ndarray | pd.Series,
) -> float:
    """Compute the disparate impact ratio (min group rate / max group rate).

    Args:
        y_pred: Predicted labels (binary).
        sensitive_col: Group labels.

    Returns:
        Ratio in [0, 1]. Values below 0.8 typically indicate
        disparate impact.
    """
    return _compute_disparate_impact(np.asarray(y_pred), np.asarray(sensitive_col))


def _compute_disparate_impact(y_pred: np.ndarray, groups: np.ndarray) -> float:
    """Internal disparate impact calculation."""
    unique_groups = np.unique(groups)
    rates: list[float] = []
    for grp in unique_groups:
        mask = groups == grp
        if mask.sum() == 0:
            continue
        rates.append(float(np.mean(y_pred[mask])))

    if not rates or max(rates) == 0:
        return 0.0
    return round(min(rates) / max(rates), 6)


def generate_fairness_report(audit_results: dict[str, Any]) -> str:
    """Generate a plain-text summary of fairness audit results.

    Args:
        audit_results: Output from ``run_fairness_audit``.

    Returns:
        Multi-line string with summary.
    """
    if "error" in audit_results:
        return f"Fairness audit failed: {audit_results['error']}"

    lines = [
        "=" * 60,
        "FAIRNESS AUDIT REPORT",
        "=" * 60,
        f"Samples evaluated: {audit_results.get('n_samples', 'N/A')}",
        f"Attributes audited: {audit_results.get('n_attributes_audited', 0)}",
        "",
    ]

    per_attr = audit_results.get("per_attribute", {})
    for attr_name, metrics in per_attr.items():
        lines.append(f"--- Attribute: {attr_name} ---")
        dpd = metrics.get("demographic_parity_difference")
        eod = metrics.get("equalized_odds_difference")
        di = metrics.get("disparate_impact_ratio")
        lines.append(f"  Demographic Parity Difference: {dpd}")
        lines.append(f"  Equalized Odds Difference:     {eod}")
        lines.append(f"  Disparate Impact Ratio:        {di}")

        if dpd is not None and abs(dpd) > 0.1:
            lines.append("  [WARNING] Demographic parity difference exceeds 0.1 threshold.")
        if di is not None and di < 0.8:
            lines.append("  [WARNING] Disparate impact ratio below 0.8 (four-fifths rule).")

        group_metrics = metrics.get("group_metrics", {})
        if group_metrics:
            lines.append("  Per-group breakdown:")
            for grp, gm in group_metrics.items():
                sr = gm.get("selection_rate", "N/A")
                tpr = gm.get("true_positive_rate", "N/A")
                fpr = gm.get("false_positive_rate", "N/A")
                lines.append(f"    {grp}: rate={sr}, TPR={tpr}, FPR={fpr} (n={gm.get('count')})")
        lines.append("")

    recs = audit_results.get("recommendations", [])
    if recs:
        lines.append("RECOMMENDATIONS:")
        for rec in recs:
            lines.append(f"  - {rec}")

    lines.append("=" * 60)
    return "\n".join(lines)


def _generate_recommendations(per_attribute: dict[str, Any]) -> list[str]:
    """Generate actionable recommendations from audit results."""
    recs: list[str] = []
    for attr, metrics in per_attribute.items():
        dpd = metrics.get("demographic_parity_difference")
        di = metrics.get("disparate_impact_ratio")
        if dpd is not None and abs(dpd) > 0.1:
            recs.append(
                f"Investigate selection rate disparities across '{attr}' groups. "
                f"Consider re-weighting, threshold adjustment, or post-processing calibration."
            )
        if di is not None and di < 0.8:
            recs.append(
                f"Disparate impact detected for '{attr}' (ratio={di}). "
                f"Review feature set for proxies and consider fairness-constrained training."
            )
    if not recs:
        recs.append("No significant fairness concerns detected. Continue monitoring in production.")
    return recs
