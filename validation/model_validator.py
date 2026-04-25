"""Validation: model_validator.

Validate a trained model before deployment. Checks model integrity,
prediction capability, performance thresholds, and domain-specific
requirements. Provides a structured deployment recommendation.
"""

from __future__ import annotations

import logging
from typing import Any

import joblib

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default performance thresholds by problem type and domain
# ---------------------------------------------------------------------------

_DEFAULT_THRESHOLDS: dict[str, dict] = {
    "classification": {"min_accuracy": 0.5, "min_auc": 0.6},
    "regression": {"min_r2": 0.0, "max_rmse_ratio": 2.0},
}

_DOMAIN_OVERRIDES: dict[str, dict] = {
    "healthcare": {"min_sensitivity": 0.7, "min_auc": 0.65},
    "finance": {"min_auc": 0.65},
    "generic": {"min_accuracy": 0.5},
}


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _compute_classification_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> dict[str, float]:
    """Compute classification metrics safely, returning NaN on failure.

    Args:
        y_true: Ground-truth labels.
        y_pred: Hard predicted labels.
        y_proba: Predicted probabilities (optional, enables AUC).

    Returns:
        Dict of metric name -> float value.
    """
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        roc_auc_score,
    )

    metrics: dict[str, float] = {}
    try:
        metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
        metrics["precision"] = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
        metrics["recall"] = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
        metrics["f1"] = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
        if y_proba is not None:
            classes = np.unique(y_true)
            if len(classes) == 2:
                proba_pos = y_proba[:, 1] if y_proba.ndim == 2 else y_proba
                metrics["auc"] = float(roc_auc_score(y_true, proba_pos))
            else:
                metrics["auc"] = float(roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted"))
    except Exception as exc:
        logger.warning("Metric computation error: %s", exc)
    return metrics


def _compute_regression_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, float]:
    """Compute regression metrics safely."""
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    metrics: dict[str, float] = {}
    try:
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
        metrics["r2"] = float(r2_score(y_true, y_pred))
        std = float(np.std(y_true))
        metrics["rmse_ratio"] = metrics["rmse"] / std if std > 0 else float("inf")
    except Exception as exc:
        logger.warning("Regression metric error: %s", exc)
    return metrics


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_loads(model_path: str) -> tuple[Any, str | None]:
    """Attempt to load the model from disk.

    Returns:
        Tuple of (model_object, error_message). error_message is None on success.
    """
    try:
        # SECURITY: Use joblib instead of pickle to reduce deserialization risks.
        # Never load model files from untrusted sources.
        loaded = joblib.load(model_path)
        model = loaded["model"] if isinstance(loaded, dict) else loaded
        return model, None
    except FileNotFoundError:
        return None, f"Model file not found: {model_path}"
    except Exception as exc:
        return None, f"Failed to load model: {exc}"


def _check_predicts(model: Any, X_test: pd.DataFrame) -> tuple[np.ndarray | None, np.ndarray | None, str | None]:
    """Run predictions and optionally predict_proba.

    Returns:
        (y_pred, y_proba, error_message)
    """
    try:
        y_pred = model.predict(X_test)
    except Exception as exc:
        return None, None, f"model.predict() failed: {exc}"

    y_proba: np.ndarray | None = None
    if hasattr(model, "predict_proba"):
        try:
            y_proba = model.predict_proba(X_test)
        except Exception:
            pass  # Non-fatal; AUC will be skipped

    return y_pred, y_proba, None


def _check_constant_predictions(y_pred: np.ndarray) -> str | None:
    """Return error string if predictions are all the same value."""
    if len(np.unique(y_pred)) == 1:
        return f"Model predicts a constant value ({y_pred[0]}) for all inputs."
    return None


def _check_feature_count(model: Any, X_test: pd.DataFrame) -> str | None:
    """Verify the model's expected feature count matches X_test."""
    expected: int | None = None
    for attr in ("n_features_in_", "num_features", "n_features"):
        if hasattr(model, attr):
            expected = int(getattr(model, attr))
            break
    if expected is not None and X_test.shape[1] != expected:
        return (
            f"Feature count mismatch: model expects {expected} features, "
            f"but X_test has {X_test.shape[1]}."
        )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_model_for_deployment(
    model_path: str,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    problem_type: str,
    domain: str = "generic",
    min_performance: dict | None = None,
) -> dict:
    """Validate a trained model before deployment.

    Runs integrity, prediction, performance, and domain-specific checks.

    Args:
        model_path: Absolute path to the pickled model file.
        X_test: Hold-out feature matrix.
        y_test: Hold-out ground-truth labels.
        problem_type: "classification" or "regression".
        domain: Industry domain key (e.g. "healthcare", "finance", "generic").
        min_performance: Override default performance thresholds.

    Returns:
        Structured validation report dict.
    """
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    metrics: dict = {}

    # --- 1. Load model ---
    model, load_err = _check_loads(model_path)
    if load_err:
        failed.append(f"Model load: {load_err}")
        return _build_result(passed, failed, warnings, metrics, problem_type)
    passed.append("Model loads correctly from disk")

    # --- 2. Run predictions ---
    y_pred, y_proba, pred_err = _check_predicts(model, X_test)
    if pred_err:
        failed.append(f"Prediction: {pred_err}")
        return _build_result(passed, failed, warnings, metrics, problem_type)
    passed.append("Predictions run without error")

    # --- 3. Constant prediction check ---
    const_err = _check_constant_predictions(y_pred)
    if const_err:
        failed.append(f"Constant predictions: {const_err}")
    else:
        passed.append("Predictions are non-constant")

    # --- 4. Feature count check ---
    feat_err = _check_feature_count(model, X_test)
    if feat_err:
        warnings.append(f"Feature count: {feat_err}")
    else:
        passed.append("Feature count matches model expectation")

    # --- 5. Compute metrics ---
    if problem_type == "classification":
        metrics = _compute_classification_metrics(y_test.values, y_pred, y_proba)
    else:
        metrics = _compute_regression_metrics(y_test.values, y_pred)

    # --- 6. Performance threshold checks ---
    thresholds = dict(_DEFAULT_THRESHOLDS.get(problem_type, {}))
    if domain in _DOMAIN_OVERRIDES:
        thresholds.update(_DOMAIN_OVERRIDES[domain])
    if min_performance:
        thresholds.update(min_performance)

    _evaluate_thresholds(metrics, thresholds, problem_type, passed, failed, warnings)

    return _build_result(passed, failed, warnings, metrics, problem_type)


def _evaluate_thresholds(
    metrics: dict,
    thresholds: dict,
    problem_type: str,
    passed: list[str],
    failed: list[str],
    warnings: list[str],
) -> None:
    """Populate passed/failed/warnings based on metric thresholds."""
    check_map = {
        "min_accuracy": ("accuracy", ">="),
        "min_auc": ("auc", ">="),
        "min_sensitivity": ("recall", ">="),
        "min_r2": ("r2", ">="),
        "max_rmse_ratio": ("rmse_ratio", "<="),
    }
    for key, (metric_name, op) in check_map.items():
        if key not in thresholds:
            continue
        threshold = thresholds[key]
        value = metrics.get(metric_name)
        if value is None:
            warnings.append(f"Could not compute '{metric_name}' -- threshold check skipped.")
            continue
        if op == ">=" and value >= threshold:
            passed.append(f"{metric_name.upper()} = {value:.4f} >= {threshold} (threshold met)")
        elif op == "<=" and value <= threshold:
            passed.append(f"{metric_name.upper()} = {value:.4f} <= {threshold} (threshold met)")
        else:
            failed.append(
                f"{metric_name.upper()} = {value:.4f} does not meet threshold ({op} {threshold})"
            )


def _build_result(
    passed: list[str],
    failed: list[str],
    warnings: list[str],
    metrics: dict,
    problem_type: str,
) -> dict:
    """Assemble the final validation result dict."""
    is_valid = len(failed) == 0
    if is_valid:
        recommendation = "deploy"
        summary = (
            f"Model passed all {len(passed)} checks. "
            f"Safe to deploy. Metrics: {_metrics_str(metrics)}."
        )
    elif len(failed) <= 2 and all("threshold" in f.lower() for f in failed):
        recommendation = "review"
        summary = (
            f"Model failed {len(failed)} performance threshold(s) but is otherwise functional. "
            f"Review metrics before deploying: {_metrics_str(metrics)}."
        )
    else:
        recommendation = "reject"
        summary = (
            f"Model failed {len(failed)} critical check(s). "
            f"Do not deploy until issues are resolved."
        )

    return {
        "is_valid": is_valid,
        "passed_checks": passed,
        "failed_checks": failed,
        "warnings": warnings,
        "metrics": metrics,
        "recommendation": recommendation,
        "summary": summary,
    }


def _metrics_str(metrics: dict) -> str:
    """Format metrics dict as a compact string."""
    return ", ".join(f"{k}={v:.4f}" for k, v in metrics.items() if isinstance(v, float))


def check_model_stability(
    model_path: str,
    X_test: pd.DataFrame,
    n_runs: int = 5,
) -> dict:
    """Check that model predictions are stable across repeated runs.

    A well-trained deterministic model should return identical predictions
    on the same input every time. Non-determinism indicates a problem.

    Args:
        model_path: Absolute path to the pickled model file.
        X_test: Feature matrix to run predictions on.
        n_runs: Number of prediction passes to compare.

    Returns:
        Dict with is_stable (bool), max_variance (float), and summary (str).
    """
    model, load_err = _check_loads(model_path)
    if load_err:
        return {"is_stable": False, "max_variance": float("nan"), "summary": load_err}

    predictions: list[np.ndarray] = []
    for i in range(n_runs):
        try:
            preds = model.predict(X_test)
            predictions.append(np.array(preds, dtype=float))
        except Exception as exc:
            return {"is_stable": False, "max_variance": float("nan"), "summary": f"Prediction run {i + 1} failed: {exc}"}

    stacked = np.stack(predictions, axis=0)
    variance_per_sample = np.var(stacked, axis=0)
    max_var = float(np.max(variance_per_sample))
    is_stable = max_var == 0.0

    summary = (
        "Predictions are perfectly stable across all runs."
        if is_stable
        else f"Non-deterministic predictions detected. Max variance across runs: {max_var:.6f}."
    )
    return {"is_stable": is_stable, "max_variance": max_var, "summary": summary}
