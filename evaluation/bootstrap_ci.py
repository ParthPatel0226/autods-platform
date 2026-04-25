"""Bootstrap confidence interval estimation for the AutoDS platform."""

import logging
from collections.abc import Callable

import numpy as np
from scipy import stats

from core.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

_MIN_SAMPLES: int = 20
_MIN_BOOTSTRAP: int = 100


def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
    method: str = "percentile",
) -> dict:
    """Compute a bootstrap confidence interval for any scalar metric function.

    Args:
        y_true: Ground-truth labels or values, shape (n_samples,).
        y_pred: Model predictions, shape (n_samples,).
        metric_fn: Callable with signature metric_fn(y_true, y_pred) -> float.
        n_bootstrap: Number of bootstrap resamples. Must be >= 100.
        ci_level: Confidence level in (0, 1).
        seed: Random seed for reproducibility.
        method: ``"percentile"`` or ``"bca"`` (bias-corrected accelerated).

    Returns:
        Dict with keys: point_estimate, ci_lower, ci_upper, ci_level,
        std_error, bootstrap_distribution (list[float]), method.

    Raises:
        InsufficientDataError: Fewer than 20 samples or n_bootstrap < 100.
        ValueError: Invalid method or ci_level not in (0, 1).
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)

    if n < _MIN_SAMPLES:
        raise InsufficientDataError(
            f"bootstrap_ci requires at least {_MIN_SAMPLES} samples; got {n}."
        )
    if n_bootstrap < _MIN_BOOTSTRAP:
        raise InsufficientDataError(
            f"n_bootstrap must be >= {_MIN_BOOTSTRAP}; got {n_bootstrap}."
        )
    if not (0.0 < ci_level < 1.0):
        raise ValueError(f"ci_level must be in (0, 1); got {ci_level}.")
    if method not in ("percentile", "bca"):
        raise ValueError(f"method must be 'percentile' or 'bca'; got '{method}'.")

    logger.debug("Computing %s bootstrap CI: n=%d, n_bootstrap=%d", method, n, n_bootstrap)

    point_estimate: float = metric_fn(y_true, y_pred)
    rng = np.random.default_rng(seed)
    bootstrap_dist = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        bootstrap_dist[i] = metric_fn(y_true[idx], y_pred[idx])

    std_error = float(np.std(bootstrap_dist, ddof=1))

    if method == "percentile":
        alpha = 1.0 - ci_level
        ci_lower = float(np.percentile(bootstrap_dist, 100 * alpha / 2))
        ci_upper = float(np.percentile(bootstrap_dist, 100 * (1 - alpha / 2)))
    else:
        jackknife_values = _compute_jackknife(y_true, y_pred, metric_fn)
        ci_lower, ci_upper = _bca_correction(
            bootstrap_dist, jackknife_values, point_estimate, ci_level
        )

    logger.info(
        "Bootstrap CI (%s): point=%.4f, [%.4f, %.4f]",
        method, point_estimate, ci_lower, ci_upper,
    )
    return {
        "point_estimate": point_estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "ci_level": ci_level,
        "std_error": std_error,
        "bootstrap_distribution": bootstrap_dist.tolist(),
        "method": method,
    }


def bootstrap_compare(
    y_true: np.ndarray,
    preds_a: np.ndarray,
    preds_b: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    alpha: float | None = None,
    seed: int = 42,
) -> dict:
    """Paired bootstrap test comparing two models on the same ground truth.

    Computes the distribution of (metric_a - metric_b) over paired resamples
    and derives a two-tailed p-value for H0: mean_diff == 0.

    Args:
        y_true: Ground-truth labels or values, shape (n_samples,).
        preds_a: Predictions from model A, shape (n_samples,).
        preds_b: Predictions from model B, shape (n_samples,).
        metric_fn: Callable with signature metric_fn(y_true, y_pred) -> float.
            Higher values are assumed to be better.
        n_bootstrap: Number of paired bootstrap resamples.
        ci_level: Confidence level for the difference CI.
        alpha: Significance threshold for the hypothesis test. Defaults to
            ``1 - ci_level`` when not provided, but can be set independently.
        seed: Random seed for reproducibility.

    Returns:
        Dict with keys: mean_diff, ci_lower, ci_upper, p_value, significant,
        model_a_better_pct (float, percentage), interpretation (str).

    Raises:
        InsufficientDataError: Fewer than 20 samples provided.
        ValueError: Array length mismatch or ci_level not in (0, 1).
    """
    y_true = np.asarray(y_true)
    preds_a = np.asarray(preds_a)
    preds_b = np.asarray(preds_b)
    n = len(y_true)

    if n < _MIN_SAMPLES:
        raise InsufficientDataError(
            f"bootstrap_compare requires at least {_MIN_SAMPLES} samples; got {n}."
        )
    if len(preds_a) != n or len(preds_b) != n:
        raise ValueError("y_true, preds_a, and preds_b must all have the same length.")
    if not (0.0 < ci_level < 1.0):
        raise ValueError(f"ci_level must be in (0, 1); got {ci_level}.")

    # Separate alpha for hypothesis testing from ci_level for the CI
    sig_alpha = alpha if alpha is not None else (1.0 - ci_level)

    rng = np.random.default_rng(seed)
    diff_dist = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        diff_dist[i] = metric_fn(y_true[idx], preds_a[idx]) - metric_fn(y_true[idx], preds_b[idx])

    mean_diff = float(np.mean(diff_dist))
    ci_alpha = 1.0 - ci_level
    ci_lower = float(np.percentile(diff_dist, 100 * ci_alpha / 2))
    ci_upper = float(np.percentile(diff_dist, 100 * (1 - ci_alpha / 2)))

    # Two-tailed p-value: proportion of resamples with sign opposite to mean_diff, doubled.
    if mean_diff >= 0:
        p_value = min(float(np.mean(diff_dist <= 0)) * 2, 1.0)
    else:
        p_value = min(float(np.mean(diff_dist >= 0)) * 2, 1.0)

    significant = p_value < sig_alpha
    model_a_better_pct = float(np.mean(diff_dist > 0)) * 100.0

    if significant and mean_diff > 0:
        interpretation = (
            f"Model A is significantly better (mean diff={mean_diff:+.4f}, p={p_value:.4f})."
        )
    elif significant and mean_diff < 0:
        interpretation = (
            f"Model B is significantly better (mean diff={mean_diff:+.4f}, p={p_value:.4f})."
        )
    else:
        interpretation = (
            f"No statistically significant difference detected "
            f"(mean diff={mean_diff:+.4f}, p={p_value:.4f})."
        )

    logger.info(
        "Bootstrap compare: mean_diff=%.4f, [%.4f, %.4f], p=%.4f, significant=%s",
        mean_diff, ci_lower, ci_upper, p_value, significant,
    )
    return {
        "mean_diff": mean_diff,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "significant": significant,
        "model_a_better_pct": model_a_better_pct,
        "interpretation": interpretation,
    }


def bootstrap_multi_metric(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fns: dict[str, Callable[[np.ndarray, np.ndarray], float]],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> dict:
    """Compute bootstrap CIs for multiple metrics in a single resampling pass.

    Resampling is performed once and all metrics are evaluated on each resample,
    which is more efficient than calling ``bootstrap_ci`` per metric.

    Args:
        y_true: Ground-truth labels or values, shape (n_samples,).
        y_pred: Model predictions, shape (n_samples,).
        metric_fns: Mapping of metric_name -> callable (y_true, y_pred) -> float.
        n_bootstrap: Number of bootstrap resamples shared across all metrics.
        ci_level: Confidence level for all CIs.
        seed: Random seed for reproducibility.

    Returns:
        Dict keyed by metric name, each value a dict with:
        point_estimate, ci_lower, ci_upper, std_error.

    Raises:
        InsufficientDataError: Fewer than 20 samples provided.
        ValueError: Empty metric_fns or ci_level not in (0, 1).
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)

    if n < _MIN_SAMPLES:
        raise InsufficientDataError(
            f"bootstrap_multi_metric requires at least {_MIN_SAMPLES} samples; got {n}."
        )
    if not metric_fns:
        raise ValueError("metric_fns must contain at least one metric.")
    if not (0.0 < ci_level < 1.0):
        raise ValueError(f"ci_level must be in (0, 1); got {ci_level}.")

    metric_names = list(metric_fns.keys())
    point_estimates = {name: metric_fns[name](y_true, y_pred) for name in metric_names}

    # Single resampling pass shared across all metrics.
    bootstrap_matrix = np.empty((n_bootstrap, len(metric_names)))
    rng = np.random.default_rng(seed)

    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        yt_b, yp_b = y_true[idx], y_pred[idx]
        for j, name in enumerate(metric_names):
            bootstrap_matrix[i, j] = metric_fns[name](yt_b, yp_b)

    alpha = 1.0 - ci_level
    results: dict[str, dict] = {}

    for j, name in enumerate(metric_names):
        col = bootstrap_matrix[:, j]
        results[name] = {
            "point_estimate": point_estimates[name],
            "ci_lower": float(np.percentile(col, 100 * alpha / 2)),
            "ci_upper": float(np.percentile(col, 100 * (1 - alpha / 2))),
            "std_error": float(np.std(col, ddof=1)),
        }
        logger.info(
            "Multi-metric CI — %s: point=%.4f, [%.4f, %.4f]",
            name, results[name]["point_estimate"],
            results[name]["ci_lower"], results[name]["ci_upper"],
        )

    return results


# =============================================================================
# Private helpers
# =============================================================================


def _compute_jackknife(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
) -> np.ndarray:
    """Return leave-one-out jackknife metric values for BCa acceleration."""
    n = len(y_true)
    jackknife_values = np.empty(n)
    all_indices = np.arange(n)
    for i in range(n):
        mask = all_indices != i
        jackknife_values[i] = metric_fn(y_true[mask], y_pred[mask])
    return jackknife_values


def _bca_correction(
    bootstrap_dist: np.ndarray,
    jackknife_values: np.ndarray,
    point_estimate: float,
    ci_level: float,
) -> tuple[float, float]:
    """Compute BCa confidence interval bounds.

    Args:
        bootstrap_dist: Array of bootstrap metric values, shape (n_bootstrap,).
        jackknife_values: Leave-one-out jackknife metric values, shape (n,).
        point_estimate: Metric value on the original dataset.
        ci_level: Confidence level in (0, 1).

    Returns:
        Tuple of (ci_lower, ci_upper).
    """
    n_bootstrap = len(bootstrap_dist)
    alpha = 1.0 - ci_level

    # Bias-correction z0: z-score of the proportion of bootstrap values below
    # the point estimate.
    prop_below = np.clip(np.mean(bootstrap_dist < point_estimate), 1e-10, 1 - 1e-10)
    z0 = float(stats.norm.ppf(prop_below))

    # Acceleration a: skewness of the jackknife distribution.
    jk_mean = np.mean(jackknife_values)
    jk_diff = jk_mean - jackknife_values
    numerator = float(np.sum(jk_diff**3))
    denominator = 6.0 * float(np.sum(jk_diff**2) ** 1.5)

    if abs(denominator) < 1e-12:
        logger.debug("BCa: degenerate acceleration denominator — using z0 only.")
        acceleration = 0.0
    else:
        acceleration = numerator / denominator

    sorted_dist = np.sort(bootstrap_dist)

    def _adjusted_pct(z_alpha: float) -> float:
        inner = z0 + z_alpha
        adj_z = z0 + inner / (1.0 - acceleration * inner)
        adj_p = np.clip(float(stats.norm.cdf(adj_z)), 0.0, 1.0)
        idx = int(np.clip(np.floor(adj_p * n_bootstrap), 0, n_bootstrap - 1))
        return float(sorted_dist[idx])

    return _adjusted_pct(stats.norm.ppf(alpha / 2)), _adjusted_pct(stats.norm.ppf(1.0 - alpha / 2))
