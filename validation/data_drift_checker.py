"""Validation: data_drift_checker.

Check feature distribution drift between a reference (training) dataset
and a current (new/production) dataset using KS tests and PSI.
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, chi2_contingency

logger = logging.getLogger(__name__)

_DRIFT_LEVELS = {
    "psi": [(0.1, "none"), (0.2, "low"), (0.25, "medium"), (math.inf, "high")],
}


def _drift_level_from_psi(psi: float) -> str:
    """Map a PSI value to a drift level label."""
    for threshold, label in _DRIFT_LEVELS["psi"]:
        if psi < threshold:
            return label
    return "high"


def _compute_psi(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    """Compute Population Stability Index between two numeric series.

    PSI < 0.1: no drift. 0.1-0.2: minor drift. > 0.2: significant drift.

    Args:
        expected: Reference (training) distribution.
        actual: Current (production) distribution.
        buckets: Number of quantile bins for discretisation.

    Returns:
        PSI value as a non-negative float.
    """
    expected_clean = expected.dropna()
    actual_clean = actual.dropna()

    if expected_clean.empty or actual_clean.empty:
        return 0.0

    breakpoints = np.unique(
        np.nanpercentile(expected_clean, np.linspace(0, 100, buckets + 1))
    )
    if len(breakpoints) < 2:
        return 0.0

    def _bin(series: pd.Series) -> np.ndarray:
        counts, _ = np.histogram(series, bins=breakpoints)
        pct = counts / max(counts.sum(), 1)
        return np.where(pct == 0, 1e-6, pct)

    exp_pct = _bin(expected_clean)
    act_pct = _bin(actual_clean)
    psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return max(psi, 0.0)


def _check_numeric_feature(
    ref_col: pd.Series,
    cur_col: pd.Series,
    threshold_ks: float,
    threshold_psi: float,
) -> dict:
    """Compute KS test + PSI for a single numeric feature."""
    ks_stat, ks_p = ks_2samp(ref_col.dropna(), cur_col.dropna())
    psi = _compute_psi(ref_col, cur_col)
    drift_detected = (ks_p < threshold_ks) or (psi > threshold_psi)
    drift_level = _drift_level_from_psi(psi)
    if ks_p < threshold_ks and drift_level == "none":
        drift_level = "low"
    return {
        "ks_statistic": round(float(ks_stat), 6),
        "ks_p_value": round(float(ks_p), 6),
        "psi": round(psi, 6),
        "drift_detected": drift_detected,
        "drift_level": drift_level,
    }


def _check_categorical_feature(
    ref_col: pd.Series,
    cur_col: pd.Series,
    threshold_ks: float,
    threshold_psi: float,
) -> dict:
    """Chi-square test for distribution shift in a categorical feature."""
    all_cats = pd.Index(
        set(ref_col.dropna().unique()) | set(cur_col.dropna().unique())
    )
    ref_counts = ref_col.value_counts().reindex(all_cats, fill_value=0)
    cur_counts = cur_col.value_counts().reindex(all_cats, fill_value=0)
    contingency = np.array([ref_counts.values, cur_counts.values])

    try:
        chi2, p_val, _, _ = chi2_contingency(contingency)
    except ValueError:
        chi2, p_val = 0.0, 1.0

    ref_pct = ref_counts / max(ref_counts.sum(), 1)
    cur_pct = cur_counts / max(cur_counts.sum(), 1)
    psi = float(
        np.sum(
            (cur_pct - ref_pct)
            * np.log((cur_pct + 1e-6) / (ref_pct + 1e-6))
        )
    )
    psi = max(psi, 0.0)
    drift_detected = (p_val < threshold_ks) or (psi > threshold_psi)
    drift_level = _drift_level_from_psi(psi)
    if p_val < threshold_ks and drift_level == "none":
        drift_level = "low"
    return {
        "ks_statistic": round(float(chi2), 6),
        "ks_p_value": round(float(p_val), 6),
        "psi": round(psi, 6),
        "drift_detected": drift_detected,
        "drift_level": drift_level,
    }


def check_data_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str] | None = None,
    threshold_ks: float = 0.05,
    threshold_psi: float = 0.2,
) -> dict:
    """Check feature distribution drift between reference and current data.

    Uses the Kolmogorov-Smirnov test and Population Stability Index for
    numeric features, and chi-square tests for categorical features.

    Args:
        reference_df: Training / baseline DataFrame.
        current_df: New / production DataFrame to compare against.
        features: Subset of column names to check. Defaults to all shared columns.
        threshold_ks: p-value threshold for KS / chi-square significance (default 0.05).
        threshold_psi: PSI threshold above which drift is flagged (default 0.2).

    Returns:
        Structured drift report dict.
    """
    if features is None:
        features = [c for c in reference_df.columns if c in current_df.columns]

    if not features:
        return {
            "overall_drift_detected": False,
            "drift_score": 0.0,
            "drifted_features": [],
            "stable_features": [],
            "feature_results": {},
            "summary": "No shared features found between reference and current datasets.",
            "recommendations": ["Verify that column names match between datasets."],
        }

    feature_results: dict[str, dict] = {}
    drifted: list[str] = []
    stable: list[str] = []

    for feat in features:
        if feat not in reference_df.columns or feat not in current_df.columns:
            logger.debug("Skipping missing feature: %s", feat)
            continue

        ref_col = reference_df[feat]
        cur_col = current_df[feat]

        try:
            if pd.api.types.is_numeric_dtype(ref_col):
                result = _check_numeric_feature(ref_col, cur_col, threshold_ks, threshold_psi)
            else:
                result = _check_categorical_feature(ref_col, cur_col, threshold_ks, threshold_psi)
        except Exception as exc:
            logger.warning("Drift check failed for feature '%s': %s", feat, exc)
            result = {
                "ks_statistic": 0.0, "ks_p_value": 1.0, "psi": 0.0,
                "drift_detected": False, "drift_level": "none",
            }

        feature_results[feat] = result
        (drifted if result["drift_detected"] else stable).append(feat)

    total = len(feature_results)
    drift_score = round(len(drifted) / total, 4) if total > 0 else 0.0
    overall_drift = len(drifted) > 0

    summary = _build_summary(drifted, stable, drift_score)
    recommendations = _build_recommendations(drifted, drift_score, feature_results)

    return {
        "overall_drift_detected": overall_drift,
        "drift_score": drift_score,
        "drifted_features": drifted,
        "stable_features": stable,
        "feature_results": feature_results,
        "summary": summary,
        "recommendations": recommendations,
    }


def _build_summary(drifted: list[str], stable: list[str], drift_score: float) -> str:
    """Compose a plain-English summary of drift results."""
    total = len(drifted) + len(stable)
    if not drifted:
        return f"No drift detected across all {total} features checked. Distributions are stable."
    pct = round(drift_score * 100, 1)
    top_drifted = ", ".join(drifted[:5]) + ("..." if len(drifted) > 5 else "")
    return (
        f"Drift detected in {len(drifted)} of {total} features ({pct}%). "
        f"Drifted features include: {top_drifted}. "
        f"Model performance may be degraded -- retraining is recommended."
    )


def _build_recommendations(
    drifted: list[str],
    drift_score: float,
    feature_results: dict,
) -> list[str]:
    """Generate actionable recommendations based on drift results."""
    recs: list[str] = []
    if not drifted:
        recs.append("No action required. Continue monitoring periodically.")
        return recs

    high_severity = [f for f, r in feature_results.items() if r.get("drift_level") == "high"]
    if high_severity:
        recs.append(
            f"HIGH severity drift in: {', '.join(high_severity)}. "
            f"Investigate data pipeline for these features immediately."
        )

    if drift_score >= 0.5:
        recs.append("More than 50% of features have drifted. Retrain the model on recent data before serving predictions.")
    elif drift_score >= 0.2:
        recs.append("Moderate drift detected. Consider retraining or updating the model.")
    else:
        recs.append("Minor drift detected. Monitor trends and retrain if performance drops.")

    recs.append("Check upstream data sources for schema changes, ETL pipeline issues, or population shifts.")
    return recs


def generate_drift_report(drift_result: dict) -> str:
    """Generate a markdown drift report from drift check results.

    Args:
        drift_result: Output dict from check_data_drift().

    Returns:
        Markdown-formatted drift report string.
    """
    lines: list[str] = ["# Data Drift Report\n"]
    lines.append(f"**Overall Drift Detected:** {drift_result['overall_drift_detected']}")
    lines.append(f"**Drift Score:** {drift_result['drift_score']:.2%} of features drifted\n")
    lines.append(f"## Summary\n\n{drift_result['summary']}\n")

    lines.append("## Recommendations\n")
    for rec in drift_result.get("recommendations", []):
        lines.append(f"- {rec}")
    lines.append("")

    feature_results = drift_result.get("feature_results", {})
    if feature_results:
        lines.append("## Feature-Level Results\n")
        lines.append("| Feature | KS Statistic | KS p-value | PSI | Drift Level | Drifted |")
        lines.append("|---|---|---|---|---|---|")
        for feat, res in sorted(feature_results.items(), key=lambda x: -x[1].get("psi", 0)):
            flag = "YES" if res["drift_detected"] else "no"
            lines.append(
                f"| {feat} | {res['ks_statistic']:.4f} | {res['ks_p_value']:.4g} "
                f"| {res['psi']:.4f} | {res['drift_level']} | {flag} |"
            )

    return "\n".join(lines)
