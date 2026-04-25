"""Statistical model comparison functions for the AutoDS platform.

Public API
----------
paired_ttest        Paired t-test on CV fold scores.
mcnemar_test        McNemar's test for two classifiers.
wilcoxon_test       Wilcoxon signed-rank test (non-parametric paired).
friedman_test       Friedman test for 3+ models over CV folds.
nemenyi_posthoc     Nemenyi post-hoc test after a significant Friedman result.
compare_models      High-level dispatcher; picks the right test automatically.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from scipy import stats

from core.exceptions import InsufficientDataError
from evaluation._comparator_utils import (
    MIN_SAMPLES,
    friedman_test,
    nemenyi_posthoc,
    significance_label,
    validate_paired_scores,
)

# Re-export multi-model tests so callers only need this module.
__all__ = [
    "paired_ttest",
    "mcnemar_test",
    "wilcoxon_test",
    "friedman_test",
    "nemenyi_posthoc",
    "compare_models",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paired two-model tests
# ---------------------------------------------------------------------------


def paired_ttest(
    scores_a: list[float],
    scores_b: list[float],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Paired t-test on CV fold scores (assumes normal differences).

    Returns dict: statistic, p_value, mean_diff, ci_lower, ci_upper,
    significant (bool), interpretation (str).

    Raises InsufficientDataError if fewer than MIN_SAMPLES folds;
    ValueError on length mismatch or NaN.
    """
    arr_a, arr_b = validate_paired_scores(scores_a, scores_b)
    differences = arr_a - arr_b
    n = len(differences)

    result = stats.ttest_rel(arr_a, arr_b)
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    mean_diff = float(np.mean(differences))

    se = float(np.std(differences, ddof=1)) / np.sqrt(n)
    t_crit = float(stats.t.ppf(1 - alpha / 2, df=n - 1))
    ci_lower = mean_diff - t_crit * se
    ci_upper = mean_diff + t_crit * se

    significant = p_value < alpha
    direction = "A > B" if mean_diff > 0 else ("A < B" if mean_diff < 0 else "A = B")
    interpretation = (
        f"Paired t-test is {significance_label(p_value, alpha)}. "
        f"Mean diff (A−B) = {mean_diff:.4f} ({direction}). "
        f"{int((1-alpha)*100)}% CI: [{ci_lower:.4f}, {ci_upper:.4f}]."
    )
    logger.debug("paired_ttest: stat=%.4f p=%.4f sig=%s", statistic, p_value, significant)
    return {
        "statistic": statistic,
        "p_value": p_value,
        "mean_diff": mean_diff,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "significant": significant,
        "interpretation": interpretation,
    }


def mcnemar_test(
    y_true: np.ndarray,
    preds_a: np.ndarray,
    preds_b: np.ndarray,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """McNemar's test comparing two classifiers on the same test set.

    Uses exact binomial for discordant pairs < 25, chi-squared otherwise.
    Returns dict: statistic, p_value, contingency_table (n00/n01/n10/n11),
    significant (bool), interpretation (str).

    Raises InsufficientDataError if fewer than MIN_SAMPLES samples;
    ValueError on shape mismatch.
    """
    y_true = np.asarray(y_true)
    preds_a = np.asarray(preds_a)
    preds_b = np.asarray(preds_b)

    if not (y_true.shape == preds_a.shape == preds_b.shape):
        raise ValueError("y_true, preds_a, and preds_b must have the same shape.")
    if len(y_true) < MIN_SAMPLES:
        raise InsufficientDataError(
            f"At least {MIN_SAMPLES} samples required; got {len(y_true)}."
        )

    correct_a = (preds_a == y_true).astype(int)
    correct_b = (preds_b == y_true).astype(int)
    n11 = int(np.sum((correct_a == 1) & (correct_b == 1)))
    n10 = int(np.sum((correct_a == 1) & (correct_b == 0)))
    n01 = int(np.sum((correct_a == 0) & (correct_b == 1)))
    n00 = int(np.sum((correct_a == 0) & (correct_b == 0)))
    discordant = n10 + n01

    if discordant == 0:
        statistic, p_value = 0.0, 1.0
    elif discordant < 25:
        binom = stats.binomtest(n10, discordant, p=0.5, alternative="two-sided")
        statistic, p_value = float(n10), float(binom.pvalue)
    else:
        chi2 = (abs(n10 - n01) - 1) ** 2 / discordant
        statistic, p_value = float(chi2), float(stats.chi2.sf(chi2, df=1))

    significant = p_value < alpha
    n = len(y_true)
    acc_a, acc_b = (n11 + n10) / n, (n11 + n01) / n
    better = "A" if acc_a > acc_b else ("B" if acc_b > acc_a else "neither")
    interpretation = (
        f"McNemar's test is {significance_label(p_value, alpha)}. "
        f"Accuracy — A: {acc_a:.4f}, B: {acc_b:.4f}. "
        f"Discordant: {discordant} (A-only: {n10}, B-only: {n01}). "
        f"Classifier {better} performs better."
    )
    logger.debug("mcnemar_test: stat=%.4f p=%.4f sig=%s", statistic, p_value, significant)
    return {
        "statistic": statistic,
        "p_value": p_value,
        "contingency_table": {"n00": n00, "n01": n01, "n10": n10, "n11": n11},
        "significant": significant,
        "interpretation": interpretation,
    }


def wilcoxon_test(
    scores_a: list[float],
    scores_b: list[float],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Wilcoxon signed-rank test — non-parametric paired comparison.

    Does not assume normality of score differences. Returns dict:
    statistic, p_value, significant (bool), interpretation (str).

    Raises InsufficientDataError if fewer than MIN_SAMPLES folds;
    ValueError on length mismatch or NaN.
    """
    arr_a, arr_b = validate_paired_scores(scores_a, scores_b)
    differences = arr_a - arr_b
    nonzero = int(np.sum(differences != 0))
    if nonzero < MIN_SAMPLES:
        logger.warning("wilcoxon_test: only %d non-zero differences; result may be unreliable.",
                       nonzero)

    result = stats.wilcoxon(arr_a, arr_b, alternative="two-sided")
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    significant = p_value < alpha
    median_diff = float(np.median(differences))
    direction = "A > B" if median_diff > 0 else ("A < B" if median_diff < 0 else "A ≈ B")
    interpretation = (
        f"Wilcoxon test is {significance_label(p_value, alpha)}. "
        f"Median diff (A−B) = {median_diff:.4f} ({direction})."
    )
    logger.debug("wilcoxon_test: stat=%.4f p=%.4f sig=%s", statistic, p_value, significant)
    return {"statistic": statistic, "p_value": p_value,
            "significant": significant, "interpretation": interpretation}


# ---------------------------------------------------------------------------
# High-level dispatcher
# ---------------------------------------------------------------------------


def compare_models(
    model_results: dict[str, dict],
    metric: str = "f1",
    method: str = "auto",
    alpha: float = 0.05,
) -> dict[str, Any]:
    """High-level model comparison dispatcher.

    method="auto" picks paired_ttest for 2 models, friedman_test for 3+.
    model_results format: {name: {"cv_scores": [...], "metrics": {...}}}.
    "cv_scores" is required; "metrics" is optional.

    Returns dict: ranking (list[dict] with model/mean_score/rank),
    best_model, statistical_test_results, method_used, summary.

    Raises ValueError on bad input; InsufficientDataError on too few folds.
    """
    if not model_results:
        raise ValueError("model_results must not be empty.")

    valid_methods = {"auto", "ttest", "wilcoxon", "friedman"}
    if method not in valid_methods:
        raise ValueError(f"Unknown method '{method}'. Valid: {sorted(valid_methods)}.")

    model_names = list(model_results.keys())
    n_models = len(model_names)

    cv_scores: dict[str, list[float]] = {}
    for name, result in model_results.items():
        scores = result.get("cv_scores")
        if not scores:
            raise ValueError(f"Model '{name}' is missing non-empty 'cv_scores'.")
        cv_scores[name] = list(scores)

    fold_counts = {name: len(s) for name, s in cv_scores.items()}
    if len(set(fold_counts.values())) > 1:
        raise ValueError(f"Inconsistent fold counts across models: {fold_counts}.")

    def _mean_score(name: str) -> float:
        m = model_results[name].get("metrics", {})
        return float(m[metric]) if metric in m else float(np.mean(cv_scores[name]))

    mean_scores = {name: _mean_score(name) for name in model_names}
    sorted_models = sorted(model_names, key=lambda n: mean_scores[n], reverse=True)
    ranking = [
        {"model": name, "mean_score": mean_scores[name], "rank": rank + 1}
        for rank, name in enumerate(sorted_models)
    ]
    best_model = sorted_models[0]
    chosen = ("ttest" if n_models == 2 else "friedman") if method == "auto" else method

    if chosen in ("ttest", "wilcoxon") and n_models != 2:
        raise ValueError(f"Method '{chosen}' requires exactly 2 models; got {n_models}.")
    if chosen == "friedman" and n_models < 3:
        raise ValueError(f"Friedman requires at least 3 models; got {n_models}.")

    if chosen == "ttest":
        test_results = paired_ttest(cv_scores[model_names[0]], cv_scores[model_names[1]], alpha)
    elif chosen == "wilcoxon":
        test_results = wilcoxon_test(cv_scores[model_names[0]], cv_scores[model_names[1]], alpha)
    else:
        n_folds = len(cv_scores[model_names[0]])
        score_matrix = [
            [cv_scores[name][fold] for name in model_names] for fold in range(n_folds)
        ]
        test_results = friedman_test(score_matrix, model_names, alpha)

    rank_lines = ", ".join(
        f"{r['rank']}. {r['model']} ({r['mean_score']:.4f})" for r in ranking
    )
    sig_note = (
        "Difference is statistically significant."
        if test_results.get("significant")
        else "Difference is NOT statistically significant."
    )
    summary = (
        f"Compared {n_models} models on '{metric}' using {chosen} (alpha={alpha}). "
        f"Ranking: {rank_lines}. Best: {best_model} "
        f"({metric}={mean_scores[best_model]:.4f}). {sig_note}"
    )
    logger.info("compare_models: method=%s n=%d best=%s metric=%s",
                chosen, n_models, best_model, metric)
    return {
        "ranking": ranking,
        "best_model": best_model,
        "statistical_test_results": test_results,
        "method_used": chosen,
        "summary": summary,
    }
