"""Internal utilities and multi-model tests for model_comparator.py.

Not part of the public API — import from evaluation.model_comparator instead.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from scipy import stats

from core.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

MIN_SAMPLES: int = 3

# Nemenyi q_alpha table: (alpha, k) → q_alpha. Source: Demsar (2006).
_Q_ALPHA_TABLE: dict[tuple[float, int], float] = {
    (0.05, 3): 2.343, (0.05, 4): 2.569, (0.05, 5): 2.728,
    (0.05, 6): 2.850, (0.05, 7): 2.949, (0.05, 8): 3.031,
    (0.05, 9): 3.102, (0.05, 10): 3.164,
    (0.10, 3): 2.052, (0.10, 4): 2.291, (0.10, 5): 2.459,
    (0.10, 6): 2.589, (0.10, 7): 2.693, (0.10, 8): 2.780,
    (0.10, 9): 2.855, (0.10, 10): 2.920,
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_paired_scores(
    scores_a: list[float],
    scores_b: list[float],
    label_a: str = "scores_a",
    label_b: str = "scores_b",
) -> tuple[np.ndarray, np.ndarray]:
    """Validate and convert two paired score lists to float64 numpy arrays.

    Args:
        scores_a: Scores for model A.
        scores_b: Scores for model B.
        label_a: Name used in error messages for the first list.
        label_b: Name used in error messages for the second list.

    Returns:
        Tuple (arr_a, arr_b) as float64 numpy arrays.

    Raises:
        ValueError: Length mismatch or NaN values.
        InsufficientDataError: Fewer than MIN_SAMPLES observations.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError(
            f"Length mismatch: {label_a}={len(scores_a)}, {label_b}={len(scores_b)}."
        )
    if len(scores_a) < MIN_SAMPLES:
        raise InsufficientDataError(
            f"At least {MIN_SAMPLES} paired observations required; got {len(scores_a)}."
        )
    arr_a = np.asarray(scores_a, dtype=np.float64)
    arr_b = np.asarray(scores_b, dtype=np.float64)
    if np.any(np.isnan(arr_a)) or np.any(np.isnan(arr_b)):
        raise ValueError("NaN values detected in score arrays.")
    return arr_a, arr_b


def validate_score_matrix(
    score_matrix: list[list[float]],
    model_names: list[str],
) -> np.ndarray:
    """Validate a fold-by-model score matrix and return it as a 2-D array.

    Args:
        score_matrix: Nested list (n_folds × n_models).
        model_names: Model names; length must equal n_models.

    Returns:
        (n_folds, n_models) float64 numpy array.

    Raises:
        InsufficientDataError: Fewer than MIN_SAMPLES folds.
        ValueError: Malformed matrix, name count mismatch, or fewer than 3 models.
    """
    if not score_matrix:
        raise InsufficientDataError("score_matrix is empty.")
    n_folds = len(score_matrix)
    if n_folds < MIN_SAMPLES:
        raise InsufficientDataError(
            f"At least {MIN_SAMPLES} folds required; got {n_folds}."
        )
    n_models = len(score_matrix[0])
    if n_models != len(model_names):
        raise ValueError(
            f"score_matrix has {n_models} columns but {len(model_names)} names provided."
        )
    if n_models < 3:
        raise ValueError("Friedman / Nemenyi tests require at least 3 models.")
    matrix = np.array(score_matrix, dtype=np.float64)
    if matrix.shape != (n_folds, n_models):
        raise ValueError("score_matrix rows have inconsistent lengths.")
    if np.any(np.isnan(matrix)):
        raise ValueError("NaN values detected in score_matrix.")
    return matrix


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def significance_label(p_value: float, alpha: float) -> str:
    """Return a human-readable significance description.

    Args:
        p_value: The p-value of the test.
        alpha: The significance level threshold.

    Returns:
        Short descriptive string.
    """
    if p_value < 0.001:
        return "highly significant (p < 0.001)"
    if p_value < 0.01:
        return "very significant (p < 0.01)"
    if p_value < alpha:
        return f"significant (p < {alpha})"
    return f"not significant (p = {p_value:.4f}, threshold = {alpha})"


def rank_matrix_best_first(matrix: np.ndarray) -> np.ndarray:
    """Rank models within each fold so that rank 1 = highest score.

    Args:
        matrix: (n_folds, n_models) float64 array.

    Returns:
        Integer rank array of the same shape.
    """
    return np.apply_along_axis(
        lambda row: stats.rankdata(-row), axis=1, arr=matrix
    )


def nemenyi_q_alpha(alpha: float, n_models: int) -> float:
    """Look up or approximate the Nemenyi critical-difference q_alpha value.

    Args:
        alpha: Significance level (typically 0.05 or 0.10).
        n_models: Number of models being compared.

    Returns:
        q_alpha scalar.
    """
    key = (round(alpha, 2), n_models)
    if key in _Q_ALPHA_TABLE:
        return _Q_ALPHA_TABLE[key]
    n_comp = n_models * (n_models - 1) / 2
    q = float(stats.norm.ppf(1 - alpha / (2 * n_comp)))
    logger.warning(
        "nemenyi_q_alpha: k=%d alpha=%.2f not in table; Bonferroni approx=%.4f.",
        n_models, alpha, q,
    )
    return q


# ---------------------------------------------------------------------------
# Multi-model statistical tests (also exported via model_comparator)
# ---------------------------------------------------------------------------


def friedman_test(
    score_matrix: list[list[float]],
    model_names: list[str],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Friedman test for comparing 3+ models over CV folds.

    Non-parametric repeated-measures ANOVA. Ranks models within each fold
    and tests whether rank distributions differ significantly across models.

    Args:
        score_matrix: (n_folds × n_models) nested list. Each row is one fold.
        model_names: Model names in column order.
        alpha: Significance level (default 0.05).

    Returns:
        Dict with keys: statistic, p_value, significant,
        rankings (model → mean rank, lower = better), interpretation.

    Raises:
        InsufficientDataError: Fewer than MIN_SAMPLES folds.
        ValueError: Malformed matrix or fewer than 3 models.
    """
    matrix = validate_score_matrix(score_matrix, model_names)
    n_folds, n_models = matrix.shape
    result = stats.friedmanchisquare(*[matrix[:, j] for j in range(n_models)])
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    rank_mat = rank_matrix_best_first(matrix)
    mean_ranks: dict[str, float] = {
        name: float(np.mean(rank_mat[:, j])) for j, name in enumerate(model_names)
    }
    best_model = min(mean_ranks, key=mean_ranks.__getitem__)
    significant = p_value < alpha
    rank_str = ", ".join(
        f"{n}: {r:.2f}" for n, r in sorted(mean_ranks.items(), key=lambda kv: kv[1])
    )
    interpretation = (
        f"Friedman test is {significance_label(p_value, alpha)} "
        f"({n_folds} folds, {n_models} models). "
        f"Mean ranks (lower=better): {rank_str}. Best: {best_model}."
    )
    if significant:
        interpretation += " Run nemenyi_posthoc() for pairwise comparisons."
    logger.debug("friedman_test: stat=%.4f p=%.4f sig=%s best=%s",
                 statistic, p_value, significant, best_model)
    return {
        "statistic": statistic,
        "p_value": p_value,
        "significant": significant,
        "rankings": mean_ranks,
        "interpretation": interpretation,
    }


def nemenyi_posthoc(
    score_matrix: list[list[float]],
    model_names: list[str],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Nemenyi post-hoc test following a significant Friedman result.

    Two models differ significantly when |mean_rank_A − mean_rank_B| > CD.

    Args:
        score_matrix: Same (n_folds × n_models) matrix used for friedman_test.
        model_names: Model names in column order.
        alpha: Significance level (default 0.05).

    Returns:
        Dict with keys: cd (float), pairwise_comparisons (list of dicts with
        model_a, model_b, mean_rank_a, mean_rank_b, rank_diff, significant,
        interpretation), interpretation (str).

    Raises:
        InsufficientDataError: Fewer than MIN_SAMPLES folds.
        ValueError: Malformed matrix or fewer than 3 models.
    """
    matrix = validate_score_matrix(score_matrix, model_names)
    n_folds, n_models = matrix.shape
    rank_mat = rank_matrix_best_first(matrix)
    mean_ranks: dict[str, float] = {
        name: float(np.mean(rank_mat[:, j])) for j, name in enumerate(model_names)
    }
    q_alpha = nemenyi_q_alpha(alpha, n_models)
    cd = float(q_alpha * np.sqrt(n_models * (n_models + 1) / (6 * n_folds)))
    pairwise: list[dict[str, Any]] = []
    model_list = list(model_names)
    for i in range(len(model_list)):
        for j in range(i + 1, len(model_list)):
            name_a, name_b = model_list[i], model_list[j]
            rank_a, rank_b = mean_ranks[name_a], mean_ranks[name_b]
            diff = abs(rank_a - rank_b)
            sig = diff > cd
            better = name_a if rank_a < rank_b else name_b
            pair_interp = (
                f"|rank({name_a})−rank({name_b})| = {diff:.4f} "
                f"({'>' if sig else '<='} CD {cd:.4f}): "
                + (f"significant — {better} is better." if sig else "no significant difference.")
            )
            pairwise.append({
                "model_a": name_a, "model_b": name_b,
                "mean_rank_a": rank_a, "mean_rank_b": rank_b,
                "rank_diff": float(diff), "significant": sig,
                "interpretation": pair_interp,
            })
    sig_count = sum(1 for p in pairwise if p["significant"])
    interpretation = (
        f"Nemenyi post-hoc (CD={cd:.4f}, alpha={alpha}): "
        f"{sig_count}/{len(pairwise)} pairs significantly different."
    )
    if sig_count == 0:
        interpretation += " No models differ significantly."
    logger.debug("nemenyi_posthoc: cd=%.4f sig=%d/%d", cd, sig_count, len(pairwise))
    return {"cd": cd, "pairwise_comparisons": pairwise, "interpretation": interpretation}
