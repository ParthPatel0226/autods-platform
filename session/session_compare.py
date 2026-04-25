"""Session comparison -- diff metrics between two sessions on the same dataset.

Useful for comparing different modeling approaches, feature sets, or
hyperparameter configurations across separate runs.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compare_sessions(
    session_a: dict[str, Any],
    session_b: dict[str, Any],
    label_a: str = "Session A",
    label_b: str = "Session B",
) -> dict[str, Any]:
    """Compare two session states and return structured diff.

    Args:
        session_a: First session state dict.
        session_b: Second session state dict.
        label_a: Display label for first session.
        label_b: Display label for second session.

    Returns:
        Dict with sections: config_diff, metric_diff, feature_diff, summary.
    """
    return {
        "labels": [label_a, label_b],
        "config_diff": _compare_config(session_a, session_b, label_a, label_b),
        "metric_diff": _compare_metrics(session_a, session_b, label_a, label_b),
        "feature_diff": _compare_features(session_a, session_b, label_a, label_b),
        "model_diff": _compare_models(session_a, session_b, label_a, label_b),
        "summary": _generate_summary(session_a, session_b, label_a, label_b),
    }


def _compare_config(
    a: dict[str, Any],
    b: dict[str, Any],
    label_a: str,
    label_b: str,
) -> list[dict[str, Any]]:
    """Compare configuration keys."""
    config_keys = [
        "detected_domain", "problem_type", "target_column", "user_mode",
        "validation_strategy", "tuning_strategy", "scaling_strategy",
    ]
    diffs: list[dict[str, Any]] = []
    for key in config_keys:
        val_a = a.get(key)
        val_b = b.get(key)
        if val_a != val_b:
            diffs.append({
                "key": key,
                label_a: val_a,
                label_b: val_b,
                "changed": True,
            })
        else:
            diffs.append({
                "key": key,
                label_a: val_a,
                label_b: val_b,
                "changed": False,
            })
    return diffs


def _compare_metrics(
    a: dict[str, Any],
    b: dict[str, Any],
    label_a: str,
    label_b: str,
) -> list[dict[str, Any]]:
    """Compare best model metrics."""
    metrics_a: dict[str, float] = a.get("best_model_metrics", {})
    metrics_b: dict[str, float] = b.get("best_model_metrics", {})
    all_keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))

    diffs: list[dict[str, Any]] = []
    for key in all_keys:
        val_a = metrics_a.get(key)
        val_b = metrics_b.get(key)

        delta = None
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            delta = val_b - val_a

        diffs.append({
            "metric": key,
            label_a: val_a,
            label_b: val_b,
            "delta": delta,
            "improved": delta > 0 if delta is not None else None,
        })
    return diffs


def _compare_features(
    a: dict[str, Any],
    b: dict[str, Any],
    label_a: str,
    label_b: str,
) -> dict[str, Any]:
    """Compare feature sets used."""
    feats_a = set(a.get("features_selected", []) or a.get("feature_list", []))
    feats_b = set(b.get("features_selected", []) or b.get("feature_list", []))

    return {
        "common": sorted(feats_a & feats_b),
        f"only_{label_a}": sorted(feats_a - feats_b),
        f"only_{label_b}": sorted(feats_b - feats_a),
        "count_a": len(feats_a),
        "count_b": len(feats_b),
    }


def _compare_models(
    a: dict[str, Any],
    b: dict[str, Any],
    label_a: str,
    label_b: str,
) -> dict[str, Any]:
    """Compare trained model sets."""
    models_a = set(a.get("trained_models", {}).keys())
    models_b = set(b.get("trained_models", {}).keys())

    return {
        f"best_{label_a}": a.get("best_model_name", ""),
        f"best_{label_b}": b.get("best_model_name", ""),
        f"algorithms_{label_a}": sorted(models_a),
        f"algorithms_{label_b}": sorted(models_b),
        "same_best": a.get("best_model_name") == b.get("best_model_name"),
    }


def _generate_summary(
    a: dict[str, Any],
    b: dict[str, Any],
    label_a: str,
    label_b: str,
) -> list[str]:
    """Generate human-readable comparison summary."""
    lines: list[str] = []

    # Domain match
    domain_a = a.get("detected_domain", "")
    domain_b = b.get("detected_domain", "")
    if domain_a == domain_b:
        lines.append(f"Both sessions use domain: {domain_a}")
    else:
        lines.append(f"Domain differs: {label_a}={domain_a}, {label_b}={domain_b}")

    # Best model
    best_a = a.get("best_model_name", "")
    best_b = b.get("best_model_name", "")
    if best_a == best_b:
        lines.append(f"Both sessions selected: {best_a}")
    else:
        lines.append(f"Best model differs: {label_a}={best_a}, {label_b}={best_b}")

    # Key metric comparison
    metrics_a = a.get("best_model_metrics", {})
    metrics_b = b.get("best_model_metrics", {})
    for key in ["accuracy", "f1", "auc_roc", "r2", "rmse"]:
        va = metrics_a.get(key)
        vb = metrics_b.get(key)
        if va is not None and vb is not None:
            delta = vb - va
            direction = "improved" if delta > 0 else "declined" if delta < 0 else "unchanged"
            lines.append(f"{key}: {label_a}={va:.4f}, {label_b}={vb:.4f} ({direction}, delta={delta:+.4f})")

    return lines
