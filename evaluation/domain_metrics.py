"""Evaluation: domain_metrics

Domain-specific evaluation metrics for the AutoDS platform. Each function
accepts arrays and returns structured dicts, enabling uniform downstream
consumption by agents and report generators.

Domains covered:
- Finance: KS statistic, Gini coefficient, Population Stability Index (PSI)
- Healthcare: Clinical metrics (sensitivity/specificity/PPV/NPV/LRs/NNT/NNS),
  Harrell's C-index for survival models
- E-commerce: RFM scoring, simple Customer Lifetime Value estimation
- Manufacturing: Overall Equipment Effectiveness (OEE), process capability
  indices (Cp, Cpk, Pp, Ppk)
- Marketing: Campaign lift with statistical significance
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_EPS = 1e-9  # prevent log(0) and div-by-zero throughout


def _safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Return numerator / denominator, or fallback when denominator is ~zero."""
    return numerator / denominator if abs(denominator) > _EPS else fallback


# =============================================================================
# FINANCE
# =============================================================================


def ks_statistic(y_true: np.ndarray, y_scores: np.ndarray) -> dict[str, Any]:
    """Kolmogorov-Smirnov statistic for binary classifier discrimination.

    Computes the maximum vertical distance between the empirical CDFs of
    the score distributions for class-0 and class-1 observations, and
    builds a decile-level summary table.

    Args:
        y_true: Binary labels (0/1), shape (n,).
        y_scores: Predicted probability of the positive class, shape (n,).

    Returns:
        Dict with keys:
            ks_statistic (float): KS value in [0, 1].
            ks_threshold (float): Score at which max separation occurs.
            decile_table (list[dict]): Per-decile summary with keys
                decile, min_score, max_score, count, event_rate,
                cumulative_pct_events, cumulative_pct_non_events, ks.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_scores = np.asarray(y_scores, dtype=float)

    if len(y_true) != len(y_scores):
        raise ValueError("y_true and y_scores must have the same length.")

    events = y_scores[y_true == 1]
    non_events = y_scores[y_true == 0]

    if len(events) == 0 or len(non_events) == 0:
        logger.warning("ks_statistic: one class has no samples — returning zeros.")
        return {"ks_statistic": 0.0, "ks_threshold": float("nan"), "decile_table": []}

    # Sort all scores descending (higher score = more likely positive)
    sort_idx = np.argsort(-y_scores)
    sorted_scores = y_scores[sort_idx]
    sorted_labels = y_true[sort_idx]

    n_total = len(sorted_labels)
    n_events = sorted_labels.sum()
    n_non_events = n_total - n_events

    cum_events = np.cumsum(sorted_labels) / max(n_events, 1)
    cum_non_events = np.cumsum(1 - sorted_labels) / max(n_non_events, 1)
    ks_curve = np.abs(cum_events - cum_non_events)

    max_idx = int(np.argmax(ks_curve))
    ks_val = float(ks_curve[max_idx])
    ks_thresh = float(sorted_scores[max_idx])

    # Build decile table
    n_deciles = 10
    decile_edges = np.percentile(sorted_scores, np.linspace(100, 0, n_deciles + 1))
    decile_table: list[dict[str, Any]] = []

    cum_evt = 0.0
    cum_non_evt = 0.0

    for i in range(n_deciles):
        low, high = decile_edges[i + 1], decile_edges[i]
        mask = (sorted_scores >= low) & (sorted_scores <= high)
        count = int(mask.sum())
        evt_count = int(sorted_labels[mask].sum())
        non_evt_count = count - evt_count
        cum_evt += evt_count
        cum_non_evt += non_evt_count
        cum_pct_evt = _safe_divide(cum_evt, n_events)
        cum_pct_non_evt = _safe_divide(cum_non_evt, n_non_events)
        decile_table.append(
            {
                "decile": i + 1,
                "min_score": round(float(low), 6),
                "max_score": round(float(high), 6),
                "count": count,
                "event_rate": round(_safe_divide(evt_count, count), 4),
                "cumulative_pct_events": round(cum_pct_evt, 4),
                "cumulative_pct_non_events": round(cum_pct_non_evt, 4),
                "ks": round(abs(cum_pct_evt - cum_pct_non_evt), 4),
            }
        )

    logger.debug("ks_statistic: KS=%.4f at threshold=%.4f", ks_val, ks_thresh)
    return {
        "ks_statistic": round(ks_val, 4),
        "ks_threshold": round(ks_thresh, 6),
        "decile_table": decile_table,
    }


def gini_coefficient(y_true: np.ndarray, y_scores: np.ndarray) -> dict[str, Any]:
    """Gini coefficient for binary classifier discrimination.

    Gini = 2 * AUC - 1.

    Args:
        y_true: Binary labels (0/1), shape (n,).
        y_scores: Predicted probability of the positive class, shape (n,).

    Returns:
        Dict with keys:
            gini (float): Gini coefficient in [-1, 1].
            auc (float): Area Under the ROC Curve.
            interpretation (str): Plain-English description.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_scores = np.asarray(y_scores, dtype=float)

    auc = float(roc_auc_score(y_true, y_scores))
    gini = 2.0 * auc - 1.0

    if gini >= 0.6:
        interp = "Excellent discriminating power (Gini >= 0.60)."
    elif gini >= 0.4:
        interp = "Good discriminating power (Gini 0.40–0.60)."
    elif gini >= 0.2:
        interp = "Moderate discriminating power (Gini 0.20–0.40)."
    else:
        interp = "Poor discriminating power (Gini < 0.20)."

    logger.debug("gini_coefficient: Gini=%.4f AUC=%.4f", gini, auc)
    return {
        "gini": round(gini, 4),
        "auc": round(auc, 4),
        "interpretation": interp,
    }


def psi(
    expected: np.ndarray, actual: np.ndarray, n_bins: int = 10
) -> dict[str, Any]:
    """Population Stability Index between a reference and a current distribution.

    PSI < 0.10  → stable, no action needed.
    0.10–0.25   → moderate shift, warrants investigation.
    > 0.25      → significant shift, model likely needs retraining.

    Args:
        expected: Reference (training-time) score distribution.
        actual: Current (production) score distribution.
        n_bins: Number of equal-frequency bins derived from ``expected``.

    Returns:
        Dict with keys:
            psi_value (float): Total PSI.
            bin_details (list[dict]): Per-bin breakdown.
            is_stable (bool): PSI < 0.10.
            needs_investigation (bool): 0.10 <= PSI <= 0.25.
            significant_shift (bool): PSI > 0.25.
            interpretation (str): Plain-English description.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    breakpoints = np.unique(
        np.nanpercentile(expected, np.linspace(0, 100, n_bins + 1))
    )
    if len(breakpoints) < 2:
        logger.warning("psi: cannot define bins — returning 0.")
        return {
            "psi_value": 0.0,
            "bin_details": [],
            "is_stable": True,
            "needs_investigation": False,
            "significant_shift": False,
            "interpretation": "Cannot compute PSI: insufficient unique values.",
        }

    exp_counts, _ = np.histogram(expected, bins=breakpoints)
    act_counts, _ = np.histogram(actual, bins=breakpoints)

    exp_pct = exp_counts / max(exp_counts.sum(), 1)
    act_pct = act_counts / max(act_counts.sum(), 1)

    exp_pct = np.where(exp_pct == 0, _EPS, exp_pct)
    act_pct = np.where(act_pct == 0, _EPS, act_pct)

    bin_psi = (act_pct - exp_pct) * np.log(act_pct / exp_pct)
    total_psi = float(bin_psi.sum())

    bin_details = [
        {
            "bin": i + 1,
            "lower": round(float(breakpoints[i]), 6),
            "upper": round(float(breakpoints[i + 1]), 6),
            "expected_pct": round(float(exp_pct[i]), 4),
            "actual_pct": round(float(act_pct[i]), 4),
            "bin_psi": round(float(bin_psi[i]), 6),
        }
        for i in range(len(bin_psi))
    ]

    is_stable = total_psi < 0.10
    needs_investigation = 0.10 <= total_psi <= 0.25
    significant_shift = total_psi > 0.25

    if is_stable:
        interp = f"PSI={total_psi:.4f}: Distribution is stable — no action needed."
    elif needs_investigation:
        interp = (
            f"PSI={total_psi:.4f}: Moderate shift detected — investigate score distributions."
        )
    else:
        interp = (
            f"PSI={total_psi:.4f}: Significant population shift — model retraining recommended."
        )

    logger.debug("psi: PSI=%.4f (stable=%s)", total_psi, is_stable)
    return {
        "psi_value": round(total_psi, 4),
        "bin_details": bin_details,
        "is_stable": is_stable,
        "needs_investigation": needs_investigation,
        "significant_shift": significant_shift,
        "interpretation": interp,
    }


# =============================================================================
# HEALTHCARE
# =============================================================================


def clinical_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    prevalence: float | None = None,
) -> dict[str, Any]:
    """Clinical performance metrics for binary classifiers.

    Computes sensitivity, specificity, PPV, NPV, likelihood ratios, NNT,
    and NNS. When ``prevalence`` is provided, PPV and NPV are adjusted
    using Bayes' theorem to reflect that population prevalence rather than
    the sample prevalence.

    Args:
        y_true: True binary labels (0 = negative, 1 = positive), shape (n,).
        y_pred: Hard binary predictions (0/1), shape (n,).
        prevalence: Optional external prevalence for PPV/NPV adjustment.
            Must be in (0, 1).

    Returns:
        Dict with keys:
            sensitivity, specificity, ppv, npv (float): Core metrics.
            lr_positive, lr_negative (float): Likelihood ratios.
            nnt (float): Number Needed to Treat (1 / absolute_risk_reduction).
            nns (float): Number Needed to Screen (1 / sensitivity * prevalence).
            prevalence (float): Prevalence used for Bayes adjustment.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    tp = float(((y_pred == 1) & (y_true == 1)).sum())
    tn = float(((y_pred == 0) & (y_true == 0)).sum())
    fp = float(((y_pred == 1) & (y_true == 0)).sum())
    fn = float(((y_pred == 0) & (y_true == 1)).sum())

    sensitivity = _safe_divide(tp, tp + fn)
    specificity = _safe_divide(tn, tn + fp)
    sample_prev = _safe_divide(tp + fn, tp + tn + fp + fn)
    used_prevalence = prevalence if prevalence is not None else sample_prev

    if prevalence is not None:
        # Bayes-adjusted PPV/NPV
        ppv = _safe_divide(
            sensitivity * used_prevalence,
            sensitivity * used_prevalence + (1 - specificity) * (1 - used_prevalence),
        )
        npv = _safe_divide(
            specificity * (1 - used_prevalence),
            specificity * (1 - used_prevalence) + (1 - sensitivity) * used_prevalence,
        )
    else:
        ppv = _safe_divide(tp, tp + fp)
        npv = _safe_divide(tn, tn + fn)

    lr_positive = _safe_divide(sensitivity, 1 - specificity, fallback=float("inf"))
    lr_negative = _safe_divide(1 - sensitivity, specificity, fallback=0.0)

    # NNT: difference in event rates between test-positive and test-negative groups
    event_rate_positive = _safe_divide(tp, tp + fp)
    event_rate_negative = _safe_divide(fn, fn + tn)
    absolute_risk_reduction = event_rate_positive - event_rate_negative
    nnt = _safe_divide(1.0, absolute_risk_reduction, fallback=float("inf"))

    # NNS: how many to screen to detect one true positive
    nns = _safe_divide(1.0, sensitivity * used_prevalence, fallback=float("inf"))

    logger.debug(
        "clinical_metrics: sens=%.3f spec=%.3f ppv=%.3f npv=%.3f",
        sensitivity, specificity, ppv, npv,
    )
    return {
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "ppv": round(ppv, 4),
        "npv": round(npv, 4),
        "lr_positive": round(lr_positive, 4) if math.isfinite(lr_positive) else float("inf"),
        "lr_negative": round(lr_negative, 4),
        "nnt": round(nnt, 2) if math.isfinite(nnt) else float("inf"),
        "nns": round(nns, 2) if math.isfinite(nns) else float("inf"),
        "prevalence": round(used_prevalence, 4),
    }


def concordance_index(
    event_times: np.ndarray,
    predicted_risk: np.ndarray,
    event_observed: np.ndarray,
) -> dict[str, Any]:
    """Harrell's C-index for survival model discrimination.

    Iterates over all admissible pairs (i, j) where i had an event before j,
    and counts concordant, discordant, and tied pairs.  A bootstrap-free
    standard error is estimated via the Greenwood-style formula.

    Args:
        event_times: Observed event or censoring times, shape (n,).
        predicted_risk: Predicted risk scores (higher = higher risk), shape (n,).
        event_observed: Binary indicator: 1 if event occurred, 0 if censored,
            shape (n,).

    Returns:
        Dict with keys:
            c_index (float): Harrell's C in [0, 1].
            se (float): Estimated standard error.
            ci_lower, ci_upper (float): 95% confidence interval.
            n_concordant, n_discordant, n_tied (int): Pair counts.
            interpretation (str): Plain-English description.
    """
    event_times = np.asarray(event_times, dtype=float)
    predicted_risk = np.asarray(predicted_risk, dtype=float)
    event_observed = np.asarray(event_observed, dtype=float)

    # Cap input size to avoid O(n^2) blowup on large datasets
    _MAX_CI_SAMPLES = 5000
    n = len(event_times)
    if n > _MAX_CI_SAMPLES:
        logger.info(
            "concordance_index: subsampling from %d to %d samples", n, _MAX_CI_SAMPLES
        )
        rng = np.random.default_rng(42)
        idx = rng.choice(n, size=_MAX_CI_SAMPLES, replace=False)
        event_times = event_times[idx]
        predicted_risk = predicted_risk[idx]
        event_observed = event_observed[idx]
        n = _MAX_CI_SAMPLES

    concordant = discordant = tied = 0

    for i in range(n):
        if event_observed[i] == 0:
            continue
        for j in range(n):
            if i == j:
                continue
            if event_times[j] <= event_times[i]:
                continue
            # i had an earlier event than j
            concordant += int(predicted_risk[i] > predicted_risk[j])
            discordant += int(predicted_risk[i] < predicted_risk[j])
            tied += int(predicted_risk[i] == predicted_risk[j])

    total = concordant + discordant + tied
    c_idx = _safe_divide(concordant + 0.5 * tied, total, fallback=0.5)

    # Approximate SE: sqrt(c*(1-c) / total_pairs)
    se = math.sqrt(_safe_divide(c_idx * (1 - c_idx), max(total, 1)))
    z = 1.96
    ci_lower = max(0.0, c_idx - z * se)
    ci_upper = min(1.0, c_idx + z * se)

    if c_idx >= 0.75:
        interp = f"C-index={c_idx:.3f}: Excellent survival discrimination."
    elif c_idx >= 0.65:
        interp = f"C-index={c_idx:.3f}: Good survival discrimination."
    elif c_idx >= 0.55:
        interp = f"C-index={c_idx:.3f}: Moderate survival discrimination."
    else:
        interp = f"C-index={c_idx:.3f}: Poor discrimination (near random at 0.50)."

    logger.debug("concordance_index: C=%.4f SE=%.4f", c_idx, se)
    return {
        "c_index": round(c_idx, 4),
        "se": round(se, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "n_concordant": concordant,
        "n_discordant": discordant,
        "n_tied": tied,
        "interpretation": interp,
    }


# =============================================================================
# E-COMMERCE
# =============================================================================


def rfm_scores(
    df: pd.DataFrame,
    customer_col: str,
    date_col: str,
    amount_col: str,
    reference_date: str | None = None,
) -> dict[str, Any]:
    """Compute Recency-Frequency-Monetary quintile scores per customer.

    Each dimension is scored 1–5 where 5 is always best:
    - Recency: 5 = most recent (lowest days since last purchase).
    - Frequency: 5 = highest purchase count.
    - Monetary: 5 = highest total spend.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Column name for customer identifier.
        date_col: Column name for transaction date (parseable string or datetime).
        amount_col: Column name for transaction amount.
        reference_date: ISO date string used as "today" for recency calculation.
            Defaults to the maximum date in ``date_col``.

    Returns:
        Dict with keys:
            rfm_table (list[dict]): Per-customer RFM values and scores.
            segment_distribution (dict): Count per RFM segment label.
            top_segments (list[dict]): Top-5 segments by customer count.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    ref = (
        pd.Timestamp(reference_date)
        if reference_date
        else df[date_col].max()
    )

    rfm = (
        df.groupby(customer_col)
        .agg(
            recency=(date_col, lambda x: (ref - x.max()).days),
            frequency=(date_col, "count"),
            monetary=(amount_col, "sum"),
        )
        .reset_index()
    )

    def _quintile(series: pd.Series, ascending: bool = True) -> pd.Series:
        labels = [1, 2, 3, 4, 5] if ascending else [5, 4, 3, 2, 1]
        try:
            return pd.qcut(series, q=5, labels=labels, duplicates="drop").astype(int)
        except ValueError:
            return pd.Series([3] * len(series), index=series.index)

    rfm["r_score"] = _quintile(rfm["recency"], ascending=False)  # lower recency = better
    rfm["f_score"] = _quintile(rfm["frequency"], ascending=True)
    rfm["m_score"] = _quintile(rfm["monetary"], ascending=True)
    rfm["rfm_score"] = rfm["r_score"] * 100 + rfm["f_score"] * 10 + rfm["m_score"]

    def _segment(row: pd.Series) -> str:
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        avg = (r + f + m) / 3
        if avg >= 4.5:
            return "Champions"
        if r >= 4 and f >= 3:
            return "Loyal Customers"
        if r >= 4 and f <= 2:
            return "Recent Customers"
        if r >= 3 and m >= 4:
            return "Potential Loyalists"
        if r <= 2 and f >= 4:
            return "At Risk"
        if r <= 2 and f >= 2:
            return "Cant Lose Them"
        if r <= 2 and f <= 1:
            return "Lost"
        return "Needs Attention"

    rfm["segment"] = rfm.apply(_segment, axis=1)

    seg_dist = rfm["segment"].value_counts().to_dict()
    # pandas 2.0+: value_counts().reset_index() yields columns [segment, count]
    top_df = rfm["segment"].value_counts().head(5).reset_index()
    top_df.columns = ["segment", "count"]
    top_segs = top_df.to_dict("records")

    logger.debug("rfm_scores: processed %d customers", len(rfm))
    return {
        "rfm_table": rfm.round(4).to_dict("records"),
        "segment_distribution": seg_dist,
        "top_segments": top_segs,
    }


def clv_simple(
    df: pd.DataFrame,
    customer_col: str,
    amount_col: str,
    date_col: str,
    margin: float = 0.3,
    discount_rate: float = 0.1,
) -> dict[str, Any]:
    """Simple CLV estimation using aggregate purchase behaviour.

    CLV = avg_purchase_value * purchase_frequency * margin
          * (retention_rate / (1 + discount_rate - retention_rate))

    Retention rate is estimated as 1 - churn_rate, where churn_rate is the
    fraction of customers who made only a single purchase.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Column name for customer identifier.
        amount_col: Column name for transaction amount.
        date_col: Column name for transaction date (for frequency computation).
        margin: Gross margin as a fraction (default 0.30 = 30%).
        discount_rate: Annual discount / cost-of-capital rate (default 0.10).

    Returns:
        Dict with keys:
            clv_table (list[dict]): Per-customer CLV.
            avg_clv (float): Mean CLV across all customers.
            total_clv (float): Sum of all customer CLVs.
            clv_distribution_stats (dict): mean, median, std, p25, p75, max.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    customer_stats = (
        df.groupby(customer_col)
        .agg(
            total_spend=(amount_col, "sum"),
            purchase_count=(date_col, "count"),
        )
        .reset_index()
    )

    avg_purchase = customer_stats["total_spend"] / customer_stats["purchase_count"]
    frequency = customer_stats["purchase_count"]

    # Retention: customers with >1 purchase are considered retained
    n_customers = len(customer_stats)
    n_retained = int((customer_stats["purchase_count"] > 1).sum())
    retention_rate = _safe_divide(n_retained, n_customers, fallback=0.5)
    retention_rate = max(0.01, min(0.99, retention_rate))

    denom = 1 + discount_rate - retention_rate
    multiplier = _safe_divide(retention_rate, denom, fallback=0.0)

    customer_stats["avg_purchase_value"] = avg_purchase
    customer_stats["clv"] = avg_purchase * frequency * margin * multiplier

    clv_vals = customer_stats["clv"]
    dist_stats = {
        "mean": round(float(clv_vals.mean()), 2),
        "median": round(float(clv_vals.median()), 2),
        "std": round(float(clv_vals.std()), 2),
        "p25": round(float(clv_vals.quantile(0.25)), 2),
        "p75": round(float(clv_vals.quantile(0.75)), 2),
        "max": round(float(clv_vals.max()), 2),
    }

    logger.debug(
        "clv_simple: avg_clv=%.2f total_clv=%.2f retention=%.3f",
        clv_vals.mean(), clv_vals.sum(), retention_rate,
    )
    return {
        "clv_table": customer_stats.round(4).to_dict("records"),
        "avg_clv": round(float(clv_vals.mean()), 2),
        "total_clv": round(float(clv_vals.sum()), 2),
        "clv_distribution_stats": dist_stats,
    }


# =============================================================================
# MANUFACTURING
# =============================================================================


def oee_score(
    availability: float, performance: float, quality: float
) -> dict[str, Any]:
    """Overall Equipment Effectiveness (OEE = Availability * Performance * Quality).

    Args:
        availability: Fraction of scheduled time the equipment is available (0–1).
        performance: Fraction of maximum possible throughput achieved (0–1).
        quality: Fraction of output that meets quality standards (0–1).

    Returns:
        Dict with keys:
            oee (float): Combined OEE score.
            availability, performance, quality (float): Input components.
            world_class (bool): True when OEE >= 0.85.
            interpretation (str): Tiered plain-English description.
    """
    for name, val in [
        ("availability", availability),
        ("performance", performance),
        ("quality", quality),
    ]:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"oee_score: '{name}' must be in [0, 1], got {val}.")

    oee = availability * performance * quality
    world_class = oee >= 0.85

    if oee >= 0.85:
        interp = f"OEE={oee:.1%}: World-class performance."
    elif oee >= 0.65:
        interp = f"OEE={oee:.1%}: Typical performance — improvement opportunities exist."
    else:
        interp = f"OEE={oee:.1%}: Below average — significant losses present."

    logger.debug("oee_score: OEE=%.4f world_class=%s", oee, world_class)
    return {
        "oee": round(oee, 4),
        "availability": round(availability, 4),
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "world_class": world_class,
        "interpretation": interp,
    }


def process_capability(
    measurements: np.ndarray, usl: float, lsl: float
) -> dict[str, Any]:
    """Process capability indices: Cp, Cpk, Pp, Ppk.

    Cp and Cpk use within-subgroup (short-term) variation estimated from the
    sample standard deviation.  When only overall variation is available, Cp
    == Pp and Cpk == Ppk.

    Args:
        measurements: Observed process measurements, shape (n,).
        usl: Upper specification limit.
        lsl: Lower specification limit.

    Returns:
        Dict with keys:
            cp, cpk, pp, ppk (float): Capability indices.
            mean, std (float): Sample statistics.
            is_capable (bool): True when Cpk >= 1.33.
            interpretation (str): Plain-English description.
    """
    measurements = np.asarray(measurements, dtype=float)
    measurements = measurements[~np.isnan(measurements)]

    if len(measurements) < 2:
        raise ValueError("process_capability requires at least 2 non-NaN measurements.")
    if usl <= lsl:
        raise ValueError(f"USL ({usl}) must be greater than LSL ({lsl}).")

    mean = float(np.mean(measurements))
    std = float(np.std(measurements, ddof=1))

    if std < _EPS:
        logger.warning("process_capability: std ~ 0, capability indices undefined.")
        return {
            "cp": float("inf"), "cpk": float("inf"),
            "pp": float("inf"), "ppk": float("inf"),
            "mean": round(mean, 6), "std": 0.0,
            "is_capable": True,
            "interpretation": "Zero process variation detected — all measurements identical.",
        }

    spec_range = usl - lsl
    cp = _safe_divide(spec_range, 6 * std)
    cpu = _safe_divide(usl - mean, 3 * std)
    cpl = _safe_divide(mean - lsl, 3 * std)
    cpk = min(cpu, cpl)

    # Pp/Ppk use overall std (identical here without subgrouping data)
    pp = cp
    ppk = cpk

    is_capable = cpk >= 1.33

    if cpk >= 1.67:
        interp = f"Cpk={cpk:.3f}: Excellent capability — process well within specification."
    elif cpk >= 1.33:
        interp = f"Cpk={cpk:.3f}: Capable process — meets Six Sigma minimum threshold."
    elif cpk >= 1.0:
        interp = f"Cpk={cpk:.3f}: Marginally capable — some defects likely."
    else:
        interp = f"Cpk={cpk:.3f}: Incapable process — significant defects expected."

    logger.debug("process_capability: Cp=%.3f Cpk=%.3f", cp, cpk)
    return {
        "cp": round(cp, 4),
        "cpk": round(cpk, 4),
        "pp": round(pp, 4),
        "ppk": round(ppk, 4),
        "mean": round(mean, 6),
        "std": round(std, 6),
        "is_capable": is_capable,
        "interpretation": interp,
    }


# =============================================================================
# MARKETING
# =============================================================================


def campaign_lift(
    control_conversion: float,
    treatment_conversion: float,
    control_n: int,
    treatment_n: int,
) -> dict[str, Any]:
    """Compute campaign lift and its statistical significance via a two-proportion z-test.

    Args:
        control_conversion: Observed conversion rate in the control group (0–1).
        treatment_conversion: Observed conversion rate in the treatment group (0–1).
        control_n: Number of subjects in the control group.
        treatment_n: Number of subjects in the treatment group.

    Returns:
        Dict with keys:
            absolute_lift (float): treatment_conversion - control_conversion.
            relative_lift (float): absolute_lift / control_conversion.
            z_statistic (float): Two-proportion z-test statistic.
            p_value (float): Two-tailed p-value.
            significant (bool): True when p_value < 0.05.
            ci_lower, ci_upper (float): 95% CI for absolute lift.
            interpretation (str): Plain-English description.
    """
    for name, val in [
        ("control_conversion", control_conversion),
        ("treatment_conversion", treatment_conversion),
    ]:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"campaign_lift: '{name}' must be in [0, 1], got {val}.")
    if control_n <= 0 or treatment_n <= 0:
        raise ValueError("campaign_lift: group sizes must be positive integers.")

    abs_lift = treatment_conversion - control_conversion
    rel_lift = _safe_divide(abs_lift, control_conversion, fallback=float("nan"))

    # Pooled proportion for null hypothesis
    pooled_p = _safe_divide(
        control_conversion * control_n + treatment_conversion * treatment_n,
        control_n + treatment_n,
    )
    pooled_se = math.sqrt(
        pooled_p * (1 - pooled_p) * (1 / control_n + 1 / treatment_n)
    )
    z_stat = _safe_divide(abs_lift, pooled_se)
    p_val = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
    significant = p_val < 0.05

    # 95% CI using unpooled SE
    unpooled_se = math.sqrt(
        _safe_divide(control_conversion * (1 - control_conversion), control_n)
        + _safe_divide(treatment_conversion * (1 - treatment_conversion), treatment_n)
    )
    ci_lower = abs_lift - 1.96 * unpooled_se
    ci_upper = abs_lift + 1.96 * unpooled_se

    if significant and abs_lift > 0:
        interp = (
            f"Significant positive lift of {abs_lift:.1%} "
            f"(p={p_val:.4f}). The campaign improved conversions."
        )
    elif significant and abs_lift < 0:
        interp = (
            f"Significant negative lift of {abs_lift:.1%} "
            f"(p={p_val:.4f}). The campaign hurt conversions."
        )
    else:
        interp = (
            f"No statistically significant lift detected "
            f"(absolute_lift={abs_lift:.1%}, p={p_val:.4f})."
        )

    logger.debug(
        "campaign_lift: abs=%.4f rel=%.4f z=%.3f p=%.4f sig=%s",
        abs_lift, rel_lift, z_stat, p_val, significant,
    )
    return {
        "absolute_lift": round(abs_lift, 4),
        "relative_lift": round(rel_lift, 4) if math.isfinite(rel_lift) else float("nan"),
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_val, 4),
        "significant": significant,
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "interpretation": interp,
    }


# =============================================================================
# DISPATCHER
# =============================================================================

_DOMAIN_DISPATCH: dict[str, list[str]] = {
    "finance": ["ks_statistic", "gini_coefficient", "psi"],
    "healthcare": ["clinical_metrics", "concordance_index"],
    "ecommerce": ["rfm_scores", "clv_simple"],
    "manufacturing": ["oee_score", "process_capability"],
    "marketing": ["campaign_lift"],
}


def get_domain_metrics(
    domain: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_scores: np.ndarray | None = None,
    problem_type: str = "classification",
) -> dict[str, dict[str, Any]]:
    """High-level dispatcher: compute all relevant domain metrics in one call.

    Dispatches to every metric function registered for ``domain``.  Metric
    functions that require arguments beyond ``y_true``, ``y_pred``, and
    ``y_scores`` (e.g. ``rfm_scores``, ``oee_score``) are skipped with a
    logged warning — callers should invoke those functions directly with the
    full required arguments.

    Args:
        domain: Industry domain key.  One of: ``finance``, ``healthcare``,
            ``ecommerce``, ``manufacturing``, ``marketing``.
        y_true: True labels or target values, shape (n,).
        y_pred: Hard predictions (binary for classification), shape (n,).
        y_scores: Predicted probabilities for the positive class, shape (n,).
            Required for AUC-based metrics (finance, healthcare).
        problem_type: ``"classification"`` or ``"regression"``.

    Returns:
        Dict mapping metric-function-name to the result dict produced by
        that function, or to ``{"error": str}`` when computation fails.
    """
    domain_lower = domain.lower()
    registered = _DOMAIN_DISPATCH.get(domain_lower, [])

    if not registered:
        logger.warning(
            "get_domain_metrics: unknown domain '%s'. Known domains: %s",
            domain,
            list(_DOMAIN_DISPATCH.keys()),
        )
        return {}

    results: dict[str, dict[str, Any]] = {}

    for metric_name in registered:
        try:
            if metric_name == "ks_statistic":
                if y_scores is None:
                    results[metric_name] = {"error": "y_scores required for ks_statistic"}
                    continue
                results[metric_name] = ks_statistic(y_true, y_scores)

            elif metric_name == "gini_coefficient":
                if y_scores is None:
                    results[metric_name] = {"error": "y_scores required for gini_coefficient"}
                    continue
                results[metric_name] = gini_coefficient(y_true, y_scores)

            elif metric_name == "psi":
                if y_scores is None:
                    results[metric_name] = {"error": "y_scores required for psi"}
                    continue
                # Use y_true as expected, y_scores as actual (score distribution check)
                results[metric_name] = psi(y_true.astype(float), y_scores)

            elif metric_name == "clinical_metrics":
                if problem_type == "classification":
                    results[metric_name] = clinical_metrics(y_true, y_pred)
                else:
                    results[metric_name] = {"skipped": "classification problem_type required"}

            elif metric_name == "concordance_index":
                # Requires event_observed; fall back gracefully
                results[metric_name] = {
                    "skipped": (
                        "concordance_index requires event_times and event_observed — "
                        "call directly with survival data."
                    )
                }

            elif metric_name in ("rfm_scores", "clv_simple"):
                results[metric_name] = {
                    "skipped": (
                        f"{metric_name} requires a transaction DataFrame — "
                        "call directly with the full DataFrame."
                    )
                }

            elif metric_name == "oee_score":
                results[metric_name] = {
                    "skipped": (
                        "oee_score requires availability, performance, quality scalars — "
                        "call directly with OEE components."
                    )
                }

            elif metric_name == "process_capability":
                results[metric_name] = {
                    "skipped": (
                        "process_capability requires measurements array plus USL/LSL — "
                        "call directly with measurement data."
                    )
                }

            elif metric_name == "campaign_lift":
                results[metric_name] = {
                    "skipped": (
                        "campaign_lift requires group-level scalars — "
                        "call directly with conversion rates and sample sizes."
                    )
                }

            else:
                logger.warning("get_domain_metrics: unhandled metric '%s'", metric_name)

        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "get_domain_metrics: error computing '%s' for domain '%s'",
                metric_name,
                domain_lower,
            )
            results[metric_name] = {"error": str(exc)}

    logger.debug(
        "get_domain_metrics: domain='%s' computed %d metrics",
        domain_lower,
        len(results),
    )
    return results
