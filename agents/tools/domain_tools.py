"""Tool module: domain_tools

Contains domain-specific calculation functions that agents call to perform
actual computation. These are deterministic, tested functions -- NOT LLM calls.

Domains covered:
- Healthcare: Charlson, Elixhauser, readmission features, clinical thresholds, survival
- Finance: KS statistic, Gini, PSI, RFM segmentation, vintage analysis
- E-commerce: CLV, cohort analysis, basket analysis, funnel metrics
- Manufacturing: OEE, MTBF/MTTR, SPC control limits
- HR: attrition features, diversity metrics, compensation equity
- Marketing: campaign lift, simple attribution
"""

from __future__ import annotations

import logging
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

# =============================================================================
# Healthcare
# =============================================================================

# Charlson weights keyed by ICD-10 prefix patterns
_CHARLSON_CATEGORIES: dict[str, tuple[str, int]] = {
    "I21": ("myocardial_infarction", 1),
    "I22": ("myocardial_infarction", 1),
    "I50": ("congestive_heart_failure", 1),
    "I43": ("congestive_heart_failure", 1),
    "G45": ("cerebrovascular_disease", 1),
    "I60": ("cerebrovascular_disease", 1),
    "I61": ("cerebrovascular_disease", 1),
    "I62": ("cerebrovascular_disease", 1),
    "I63": ("cerebrovascular_disease", 1),
    "I64": ("cerebrovascular_disease", 1),
    "F00": ("dementia", 1),
    "F01": ("dementia", 1),
    "F02": ("dementia", 1),
    "F03": ("dementia", 1),
    "G30": ("dementia", 1),
    "J40": ("chronic_pulmonary", 1),
    "J41": ("chronic_pulmonary", 1),
    "J42": ("chronic_pulmonary", 1),
    "J43": ("chronic_pulmonary", 1),
    "J44": ("chronic_pulmonary", 1),
    "J45": ("chronic_pulmonary", 1),
    "J46": ("chronic_pulmonary", 1),
    "J47": ("chronic_pulmonary", 1),
    "M05": ("rheumatic_disease", 1),
    "M06": ("rheumatic_disease", 1),
    "M32": ("rheumatic_disease", 1),
    "M33": ("rheumatic_disease", 1),
    "M34": ("rheumatic_disease", 1),
    "K25": ("peptic_ulcer", 1),
    "K26": ("peptic_ulcer", 1),
    "K27": ("peptic_ulcer", 1),
    "K28": ("peptic_ulcer", 1),
    "K70": ("liver_mild", 1),
    "K73": ("liver_mild", 1),
    "K74": ("liver_mild", 1),
    "E10": ("diabetes_uncomplicated", 1),
    "E11": ("diabetes_uncomplicated", 1),
    "E13": ("diabetes_uncomplicated", 1),
    "E14": ("diabetes_uncomplicated", 1),
    "G81": ("hemiplegia", 2),
    "G82": ("hemiplegia", 2),
    "N18": ("renal_disease", 2),
    "N19": ("renal_disease", 2),
    "C0": ("cancer", 2),
    "C1": ("cancer", 2),
    "C2": ("cancer", 2),
    "C3": ("cancer", 2),
    "C4": ("cancer", 2),
    "C5": ("cancer", 2),
    "C6": ("cancer", 2),
    "C7": ("cancer", 2),
    "C8": ("cancer", 2),
    "C9": ("cancer", 2),
    "I85": ("liver_severe", 3),
    "K72": ("liver_severe", 3),
    "C77": ("metastatic_cancer", 6),
    "C78": ("metastatic_cancer", 6),
    "C79": ("metastatic_cancer", 6),
    "C80": ("metastatic_cancer", 6),
    "B20": ("aids", 6),
    "B21": ("aids", 6),
    "B22": ("aids", 6),
    "B23": ("aids", 6),
    "B24": ("aids", 6),
}

# Elixhauser category prefixes (simplified)
_ELIXHAUSER_CATEGORIES: dict[str, list[str]] = {
    "congestive_heart_failure": ["I50", "I43"],
    "cardiac_arrhythmias": ["I44", "I45", "I47", "I48", "I49"],
    "valvular_disease": ["I05", "I06", "I07", "I08", "I09"],
    "pulmonary_circulation": ["I26", "I27", "I28"],
    "peripheral_vascular": ["I70", "I71", "I73"],
    "hypertension_uncomplicated": ["I10"],
    "hypertension_complicated": ["I11", "I12", "I13"],
    "paralysis": ["G81", "G82", "G83"],
    "neurodegenerative": ["G10", "G11", "G12", "G20", "G21"],
    "chronic_pulmonary": ["J40", "J41", "J42", "J43", "J44", "J45", "J46", "J47"],
    "diabetes_uncomplicated": ["E10", "E11", "E13"],
    "diabetes_complicated": ["E102", "E112", "E132"],
    "hypothyroidism": ["E00", "E01", "E02", "E03"],
    "renal_failure": ["N17", "N18", "N19"],
    "liver_disease": ["K70", "K72", "K73", "K74"],
    "peptic_ulcer": ["K25", "K26", "K27", "K28"],
    "aids": ["B20", "B21", "B22", "B23", "B24"],
    "lymphoma": ["C81", "C82", "C83", "C84", "C85"],
    "metastatic_cancer": ["C77", "C78", "C79", "C80"],
    "solid_tumor": ["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
    "rheumatoid_arthritis": ["M05", "M06", "M32", "M33", "M34"],
    "coagulopathy": ["D65", "D66", "D67", "D68"],
    "obesity": ["E66"],
    "weight_loss": ["E40", "E41", "E42", "E43", "E44", "E45", "E46"],
    "fluid_electrolyte": ["E86", "E87"],
    "blood_loss_anemia": ["D50"],
    "deficiency_anemia": ["D51", "D52", "D53"],
    "alcohol_abuse": ["F10"],
    "drug_abuse": ["F11", "F12", "F13", "F14", "F15", "F16", "F18", "F19"],
    "psychoses": ["F20", "F22", "F23", "F24", "F25", "F28", "F29"],
    "depression": ["F32", "F33"],
}


def _match_icd_prefix(code: str, prefix: str) -> bool:
    """Check whether an ICD code string starts with a given prefix."""
    cleaned = str(code).strip().upper().replace(".", "")
    return cleaned.startswith(prefix)


def charlson_comorbidity_index(df: pd.DataFrame, icd_column: str) -> dict[str, Any]:
    """Calculate Charlson Comorbidity Index from ICD-10 codes.

    Args:
        df: DataFrame containing ICD code data.
        icd_column: Column name with ICD-10 codes (may contain comma-separated lists).

    Returns:
        Dictionary with per-row scores and summary statistics.

    Raises:
        ToolExecutionError: If the specified column is missing.
    """
    if icd_column not in df.columns:
        raise ToolExecutionError(f"Column '{icd_column}' not found in DataFrame.")

    scores = []
    for _, row in df.iterrows():
        raw = row[icd_column]
        if pd.isna(raw):
            scores.append(0)
            continue

        codes = [c.strip() for c in str(raw).split(",")]
        matched_categories: dict[str, int] = {}

        for code in codes:
            for prefix, (category, weight) in _CHARLSON_CATEGORIES.items():
                if _match_icd_prefix(code, prefix):
                    if category not in matched_categories or weight > matched_categories[category]:
                        matched_categories[category] = weight

        scores.append(sum(matched_categories.values()))

    score_series = pd.Series(scores, index=df.index, name="charlson_score")

    distribution = score_series.value_counts().sort_index().to_dict()
    summary = {
        "mean": round(float(score_series.mean()), 3),
        "median": float(score_series.median()),
        "std": round(float(score_series.std()), 3),
        "min": int(score_series.min()),
        "max": int(score_series.max()),
        "distribution": {int(k): int(v) for k, v in distribution.items()},
    }
    return {"scores": score_series.tolist(), "summary": summary}


def elixhauser_comorbidity(df: pd.DataFrame, icd_column: str) -> dict[str, Any]:
    """Count Elixhauser comorbidity categories present per row.

    Args:
        df: DataFrame with ICD code data.
        icd_column: Column with ICD-10 codes (comma-separated accepted).

    Returns:
        Dictionary with category counts and per-row totals.

    Raises:
        ToolExecutionError: If the column is missing.
    """
    if icd_column not in df.columns:
        raise ToolExecutionError(f"Column '{icd_column}' not found in DataFrame.")

    category_counts: dict[str, int] = {cat: 0 for cat in _ELIXHAUSER_CATEGORIES}
    row_totals = []

    for _, row in df.iterrows():
        raw = row[icd_column]
        if pd.isna(raw):
            row_totals.append(0)
            continue

        codes = [c.strip() for c in str(raw).split(",")]
        row_cats: set[str] = set()

        for code in codes:
            for category, prefixes in _ELIXHAUSER_CATEGORIES.items():
                for prefix in prefixes:
                    if _match_icd_prefix(code, prefix):
                        row_cats.add(category)
                        break

        for cat in row_cats:
            category_counts[cat] += 1
        row_totals.append(len(row_cats))

    return {
        "category_counts": {k: v for k, v in category_counts.items() if v > 0},
        "total_comorbidities": row_totals,
    }


def readmission_risk_features(
    df: pd.DataFrame,
    admission_date_col: str | None = None,
    discharge_date_col: str | None = None,
) -> pd.DataFrame:
    """Create readmission-risk feature columns.

    Features created (when date columns are available):
        - prior_admissions_count: cumulative count of prior rows per patient
        - days_since_last_admission: gap between consecutive admissions
        - avg_length_of_stay: rolling average LOS

    If no date columns are provided, returns a copy with
    ``prior_admissions_count`` only (based on row order).

    Args:
        df: DataFrame with patient records.
        admission_date_col: Column with admission dates.
        discharge_date_col: Column with discharge dates.

    Returns:
        New DataFrame with additional feature columns.

    Raises:
        ToolExecutionError: If specified columns are missing.
    """
    result = df.copy()

    for col_name, col_val in [("admission_date_col", admission_date_col),
                               ("discharge_date_col", discharge_date_col)]:
        if col_val is not None and col_val not in df.columns:
            raise ToolExecutionError(f"Column '{col_val}' ({col_name}) not found in DataFrame.")

    # Try to find a patient identifier column
    patient_col = None
    for candidate in ["patient_id", "patient", "id", "subject_id", "encounter_id"]:
        if candidate in df.columns:
            patient_col = candidate
            break

    if patient_col:
        result["prior_admissions_count"] = result.groupby(patient_col).cumcount()
    else:
        result["prior_admissions_count"] = range(len(result))

    if admission_date_col and discharge_date_col:
        adm = pd.to_datetime(result[admission_date_col], errors="coerce")
        dis = pd.to_datetime(result[discharge_date_col], errors="coerce")
        result["length_of_stay"] = (dis - adm).dt.days

        if patient_col:
            sorted_df = result.sort_values([patient_col, admission_date_col])
            sorted_df["days_since_last_admission"] = (
                sorted_df.groupby(patient_col)[admission_date_col]
                .apply(lambda s: pd.to_datetime(s).diff().dt.days)
                .reset_index(level=0, drop=True)
            )
            sorted_df["avg_length_of_stay"] = (
                sorted_df.groupby(patient_col)["length_of_stay"]
                .expanding()
                .mean()
                .reset_index(level=0, drop=True)
            )
            result = sorted_df
        else:
            result["days_since_last_admission"] = pd.to_datetime(
                result[admission_date_col]
            ).diff().dt.days
            result["avg_length_of_stay"] = result["length_of_stay"].expanding().mean()

    return result


def clinical_threshold_flags(
    df: pd.DataFrame,
    column_thresholds: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Flag values outside clinical normal ranges.

    Args:
        df: DataFrame with clinical measurements.
        column_thresholds: Mapping of column name to ``{"low": float, "high": float}``.
            Either key may be omitted if only one bound is relevant.

    Returns:
        Copy of DataFrame with boolean flag columns ``{col}_abnormal``.

    Raises:
        ToolExecutionError: If a specified column is not found.
    """
    result = df.copy()
    for col, bounds in column_thresholds.items():
        if col not in df.columns:
            raise ToolExecutionError(f"Threshold column '{col}' not found in DataFrame.")

        low = bounds.get("low")
        high = bounds.get("high")
        flag = pd.Series(False, index=df.index)
        if low is not None:
            flag = flag | (pd.to_numeric(df[col], errors="coerce") < low)
        if high is not None:
            flag = flag | (pd.to_numeric(df[col], errors="coerce") > high)
        result[f"{col}_abnormal"] = flag

    return result


def survival_features(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
) -> dict[str, Any]:
    """Compute basic survival statistics from duration and event data.

    Args:
        df: DataFrame with time-to-event data.
        duration_col: Column with duration (numeric, e.g. days).
        event_col: Column with event indicator (1=event, 0=censored).

    Returns:
        Dictionary with median survival, survival rates at key time points,
        and event counts.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [duration_col, event_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    duration = pd.to_numeric(df[duration_col], errors="coerce").dropna()
    event = pd.to_numeric(df[event_col], errors="coerce").reindex(duration.index).fillna(0)

    total = len(duration)
    events_total = int(event.sum())
    censored_total = total - events_total

    # Kaplan-Meier-style survival rate estimation at key time points
    time_points = [30, 60, 90, 365]
    survival_rates: dict[str, float | None] = {}
    for t in time_points:
        at_risk = (duration >= t).sum()
        if total > 0:
            survival_rates[f"survival_rate_{t}d"] = round(at_risk / total, 4)
        else:
            survival_rates[f"survival_rate_{t}d"] = None

    # Estimate median survival (time at which ~50% have had the event)
    event_times = duration[event == 1].sort_values()
    median_survival: float | None = None
    if len(event_times) > 0:
        median_survival = float(event_times.median())

    return {
        "total_subjects": total,
        "total_events": events_total,
        "total_censored": censored_total,
        "median_survival_time": median_survival,
        "survival_rates": survival_rates,
        "duration_summary": {
            "mean": round(float(duration.mean()), 2),
            "median": float(duration.median()),
            "std": round(float(duration.std()), 2),
            "min": float(duration.min()),
            "max": float(duration.max()),
        },
    }


# =============================================================================
# Finance
# =============================================================================


def ks_statistic(
    y_true: np.ndarray | pd.Series,
    y_scores: np.ndarray | pd.Series,
) -> dict[str, Any]:
    """Kolmogorov-Smirnov statistic for binary classifier discrimination.

    Args:
        y_true: True binary labels (0/1).
        y_scores: Predicted probabilities or scores.

    Returns:
        Dictionary with KS statistic, optimal threshold, and decile table.

    Raises:
        ToolExecutionError: If inputs have mismatched lengths or invalid values.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_scores = np.asarray(y_scores, dtype=float)

    if len(y_true) != len(y_scores):
        raise ToolExecutionError("y_true and y_scores must have the same length.")

    mask = ~(np.isnan(y_true) | np.isnan(y_scores))
    y_true, y_scores = y_true[mask], y_scores[mask]

    if len(y_true) == 0:
        raise ToolExecutionError("No valid observations after removing NaN values.")

    unique_labels = set(y_true)
    if unique_labels - {0.0, 1.0}:
        raise ToolExecutionError("y_true must contain only 0 and 1 values.")

    # Sort by descending score
    order = np.argsort(-y_scores)
    y_true_sorted = y_true[order]
    y_scores_sorted = y_scores[order]

    n_pos = y_true_sorted.sum()
    n_neg = len(y_true_sorted) - n_pos

    if n_pos == 0 or n_neg == 0:
        raise ToolExecutionError("y_true must contain both positive and negative classes.")

    cum_pos = np.cumsum(y_true_sorted) / n_pos
    cum_neg = np.cumsum(1 - y_true_sorted) / n_neg
    ks_values = np.abs(cum_pos - cum_neg)

    ks_idx = int(np.argmax(ks_values))
    ks_stat_value = float(ks_values[ks_idx])
    ks_threshold = float(y_scores_sorted[ks_idx])

    # Build a decile table
    n = len(y_scores_sorted)
    decile_size = n // 10 or 1
    ks_table = []
    for i in range(10):
        start = i * decile_size
        end = (i + 1) * decile_size if i < 9 else n
        bucket_true = y_true_sorted[start:end]
        ks_table.append({
            "decile": i + 1,
            "count": int(end - start),
            "events": int(bucket_true.sum()),
            "event_rate": round(float(bucket_true.mean()), 4),
            "cum_event_pct": round(float(cum_pos[min(end - 1, n - 1)]), 4),
            "cum_nonevent_pct": round(float(cum_neg[min(end - 1, n - 1)]), 4),
            "ks": round(float(ks_values[min(end - 1, n - 1)]), 4),
        })

    return {
        "ks_stat": round(ks_stat_value, 4),
        "ks_threshold": round(ks_threshold, 4),
        "ks_table": ks_table,
    }


def gini_coefficient(
    y_true: np.ndarray | pd.Series,
    y_scores: np.ndarray | pd.Series,
) -> dict[str, Any]:
    """Gini coefficient (2 * AUC - 1) for model discrimination.

    Args:
        y_true: True binary labels (0/1).
        y_scores: Predicted probabilities or scores.

    Returns:
        Dictionary with Gini, AUC, and Lorenz curve data points.

    Raises:
        ToolExecutionError: On invalid inputs.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_scores = np.asarray(y_scores, dtype=float)

    if len(y_true) != len(y_scores):
        raise ToolExecutionError("y_true and y_scores must have the same length.")

    mask = ~(np.isnan(y_true) | np.isnan(y_scores))
    y_true, y_scores = y_true[mask], y_scores[mask]

    if len(y_true) == 0:
        raise ToolExecutionError("No valid observations after removing NaN values.")

    # Manual AUC calculation (trapezoidal)
    order = np.argsort(y_scores)
    y_sorted = y_true[order]
    n_pos = y_sorted.sum()
    n_neg = len(y_sorted) - n_pos

    if n_pos == 0 or n_neg == 0:
        raise ToolExecutionError("Both classes must be present in y_true.")

    # Wilcoxon-Mann-Whitney formulation
    ranks = np.argsort(np.argsort(y_scores)) + 1  # 1-based ranks
    auc_value = float((ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
    gini_value = 2 * auc_value - 1

    # Lorenz curve data (sampled at 20 points)
    order_desc = np.argsort(-y_scores)
    y_sorted_desc = y_true[order_desc]
    cum_pop = np.linspace(0, 1, 21)
    cum_event = np.concatenate([[0], np.cumsum(y_sorted_desc) / n_pos])
    indices = np.round(np.linspace(0, len(cum_event) - 1, 21)).astype(int)
    lorenz_data = [
        {"population_pct": round(float(cum_pop[i]), 2),
         "event_pct": round(float(cum_event[indices[i]]), 4)}
        for i in range(len(cum_pop))
    ]

    return {
        "gini": round(gini_value, 4),
        "auc": round(auc_value, 4),
        "lorenz_curve_data": lorenz_data,
    }


def psi_calculation(
    expected: np.ndarray | pd.Series,
    actual: np.ndarray | pd.Series,
    bins: int = 10,
) -> dict[str, Any]:
    """Population Stability Index to measure distribution shift.

    Args:
        expected: Baseline (training) score distribution.
        actual: Current (production) score distribution.
        bins: Number of equal-width buckets.

    Returns:
        Dictionary with PSI value, bucket details, and stability flag.

    Raises:
        ToolExecutionError: If inputs are empty or contain only NaN.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        raise ToolExecutionError("Expected and actual arrays must be non-empty.")

    # Create bins from expected distribution
    breakpoints = np.linspace(np.min(expected), np.max(expected), bins + 1)
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf

    expected_counts = np.histogram(expected, bins=breakpoints)[0]
    actual_counts = np.histogram(actual, bins=breakpoints)[0]

    # Replace zeros to avoid division by zero / log(0)
    expected_pct = np.clip(expected_counts / len(expected), 1e-6, None)
    actual_pct = np.clip(actual_counts / len(actual), 1e-6, None)

    bucket_psi = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
    psi_value = float(np.sum(bucket_psi))

    bucket_details = []
    for i in range(bins):
        lo = float(breakpoints[i]) if not np.isinf(breakpoints[i]) else None
        hi = float(breakpoints[i + 1]) if not np.isinf(breakpoints[i + 1]) else None
        bucket_details.append({
            "bucket": i + 1,
            "range_low": lo,
            "range_high": hi,
            "expected_pct": round(float(expected_pct[i]), 4),
            "actual_pct": round(float(actual_pct[i]), 4),
            "psi_bucket": round(float(bucket_psi[i]), 6),
        })

    # PSI thresholds: <0.1 stable, 0.1-0.2 moderate shift, >0.2 significant shift
    if psi_value < 0.1:
        stability = "stable"
    elif psi_value < 0.2:
        stability = "moderate_shift"
    else:
        stability = "significant_shift"

    return {
        "psi_value": round(psi_value, 4),
        "bucket_details": bucket_details,
        "is_stable": psi_value < 0.1,
        "stability_label": stability,
    }


def rfm_segmentation(
    df: pd.DataFrame,
    customer_col: str,
    date_col: str,
    amount_col: str,
) -> pd.DataFrame:
    """RFM (Recency, Frequency, Monetary) segmentation with quintile scoring.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Column identifying customers.
        date_col: Transaction date column.
        amount_col: Transaction amount column.

    Returns:
        DataFrame with one row per customer and columns R_score, F_score,
        M_score, RFM_segment, recency_days, frequency, monetary.

    Raises:
        ToolExecutionError: If required columns are missing.
    """
    for col in [customer_col, date_col, amount_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    df_work = df.copy()
    df_work[date_col] = pd.to_datetime(df_work[date_col], errors="coerce")
    df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce")
    df_work = df_work.dropna(subset=[date_col, amount_col])

    if df_work.empty:
        raise ToolExecutionError("No valid rows after parsing dates and amounts.")

    reference_date = df_work[date_col].max() + pd.Timedelta(days=1)

    rfm = df_work.groupby(customer_col).agg(
        recency_days=(date_col, lambda x: (reference_date - x.max()).days),
        frequency=(date_col, "count"),
        monetary=(amount_col, "sum"),
    ).reset_index()

    # Quintile scoring (1-5, with 5 being best)
    def _safe_qcut(series: pd.Series, labels: list, ascending: bool = True) -> pd.Series:
        """Attempt qcut; fall back to rank-based scoring on failure."""
        try:
            if ascending:
                return pd.qcut(series.rank(method="first"), q=5, labels=labels, duplicates="drop").astype(int)
            else:
                return pd.qcut(series, q=5, labels=labels, duplicates="drop").astype(int)
        except (ValueError, TypeError):
            # Fall back to rank-based scoring when qcut fails
            # When ascending=False (e.g. recency: lower value = better), rank ascending
            # so rank 1 = lowest value = best customer, which maps to highest label (5).
            fallback_ascending = True if not ascending else ascending
            ranks = series.rank(method="first", ascending=fallback_ascending)
            n_bins = min(5, int(series.nunique()))
            if n_bins < 1:
                return pd.Series(3, index=series.index)
            bin_labels = labels[:n_bins] if n_bins < 5 else labels
            return pd.cut(ranks, bins=n_bins, labels=bin_labels, include_lowest=True).astype(int)

    rfm["R_score"] = _safe_qcut(rfm["recency_days"], labels=[5, 4, 3, 2, 1], ascending=False)
    rfm["F_score"] = _safe_qcut(rfm["frequency"], labels=[1, 2, 3, 4, 5], ascending=True)
    rfm["M_score"] = _safe_qcut(rfm["monetary"], labels=[1, 2, 3, 4, 5], ascending=True)

    rfm["RFM_segment"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)

    return rfm


def vintage_analysis(
    df: pd.DataFrame,
    origination_col: str,
    performance_col: str,
    time_col: str,
) -> dict[str, Any]:
    """Vintage analysis: track performance by origination cohort over time.

    Args:
        df: DataFrame with loan/account-level data.
        origination_col: Column with origination date (will be truncated to month).
        performance_col: Column with performance indicator (numeric, e.g. default flag).
        time_col: Column with observation date.

    Returns:
        Dictionary with cohort performance matrix and summary.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [origination_col, performance_col, time_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    df_work = df.copy()
    df_work[origination_col] = pd.to_datetime(df_work[origination_col], errors="coerce")
    df_work[time_col] = pd.to_datetime(df_work[time_col], errors="coerce")
    df_work[performance_col] = pd.to_numeric(df_work[performance_col], errors="coerce")
    df_work = df_work.dropna(subset=[origination_col, time_col, performance_col])

    if df_work.empty:
        raise ToolExecutionError("No valid rows after parsing dates and performance values.")

    df_work["cohort"] = df_work[origination_col].dt.to_period("M").astype(str)
    df_work["months_on_book"] = (
        (df_work[time_col].dt.year - df_work[origination_col].dt.year) * 12
        + (df_work[time_col].dt.month - df_work[origination_col].dt.month)
    )

    pivot = df_work.groupby(["cohort", "months_on_book"])[performance_col].mean().reset_index()
    matrix = pivot.pivot(index="cohort", columns="months_on_book", values=performance_col)

    cohort_sizes = df_work.groupby("cohort")[performance_col].count().to_dict()

    return {
        "vintage_matrix": matrix.round(4).to_dict(),
        "cohort_sizes": cohort_sizes,
        "cohorts": sorted(matrix.index.tolist()),
        "max_months_on_book": int(matrix.columns.max()) if len(matrix.columns) else 0,
    }


# =============================================================================
# E-commerce
# =============================================================================


def clv_calculation(
    df: pd.DataFrame,
    customer_col: str,
    amount_col: str,
    date_col: str,
) -> pd.DataFrame:
    """Calculate simple Customer Lifetime Value estimates.

    Features produced per customer: total_spend, avg_order_value,
    purchase_frequency, customer_lifespan_days, clv_estimate.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Customer identifier column.
        amount_col: Transaction amount column.
        date_col: Transaction date column.

    Returns:
        DataFrame with one row per customer and CLV features.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [customer_col, amount_col, date_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    df_work = df.copy()
    df_work[date_col] = pd.to_datetime(df_work[date_col], errors="coerce")
    df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce")
    df_work = df_work.dropna(subset=[date_col, amount_col])

    if df_work.empty:
        raise ToolExecutionError("No valid rows after parsing.")

    clv = df_work.groupby(customer_col).agg(
        total_spend=(amount_col, "sum"),
        purchase_count=(amount_col, "count"),
        first_purchase=(date_col, "min"),
        last_purchase=(date_col, "max"),
    ).reset_index()

    clv["avg_order_value"] = (clv["total_spend"] / clv["purchase_count"]).round(2)
    clv["customer_lifespan_days"] = (clv["last_purchase"] - clv["first_purchase"]).dt.days
    clv["customer_lifespan_days"] = clv["customer_lifespan_days"].clip(lower=1)

    # Purchase frequency: purchases per 30-day period
    clv["purchase_frequency"] = (
        clv["purchase_count"] / (clv["customer_lifespan_days"] / 30)
    ).round(3)

    # Simple CLV = avg_order_value * purchase_frequency * avg_lifespan_months(12)
    clv["clv_estimate"] = (clv["avg_order_value"] * clv["purchase_frequency"] * 12).round(2)

    return clv.drop(columns=["first_purchase", "last_purchase"])


def cohort_analysis(
    df: pd.DataFrame,
    customer_col: str,
    date_col: str,
    metric_col: str | None = None,
) -> pd.DataFrame:
    """Cohort retention analysis based on first-purchase date.

    Args:
        df: Transaction-level DataFrame.
        customer_col: Customer identifier column.
        date_col: Transaction date column.
        metric_col: Optional metric column to aggregate (defaults to count).

    Returns:
        Pivot DataFrame: rows = cohort (month), columns = period offset,
        values = retention rate (fraction of cohort active).

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [customer_col, date_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    df_work = df.copy()
    df_work[date_col] = pd.to_datetime(df_work[date_col], errors="coerce")
    df_work = df_work.dropna(subset=[date_col])

    if df_work.empty:
        raise ToolExecutionError("No valid rows after parsing dates.")

    df_work["order_period"] = df_work[date_col].dt.to_period("M")

    # First purchase per customer
    first_purchase = df_work.groupby(customer_col)["order_period"].min().rename("cohort")
    df_work = df_work.merge(first_purchase, on=customer_col)

    df_work["period_offset"] = (df_work["order_period"] - df_work["cohort"]).apply(
        lambda x: x.n if hasattr(x, "n") else 0
    )

    cohort_sizes = df_work.groupby("cohort")[customer_col].nunique()
    retention = (
        df_work.groupby(["cohort", "period_offset"])[customer_col]
        .nunique()
        .reset_index()
    )

    retention["cohort_str"] = retention["cohort"].astype(str)
    retention = retention.merge(
        cohort_sizes.rename("cohort_size").reset_index(),
        on="cohort",
    )
    retention["retention_rate"] = (retention[customer_col] / retention["cohort_size"]).round(4)

    pivot = retention.pivot(index="cohort_str", columns="period_offset", values="retention_rate")
    pivot.index.name = "cohort"
    return pivot


def basket_analysis(
    df: pd.DataFrame,
    transaction_col: str,
    item_col: str,
) -> dict[str, Any]:
    """Market basket analysis: item frequency and co-occurrence.

    Args:
        df: Transaction-item level DataFrame (one row per item per transaction).
        transaction_col: Transaction identifier column.
        item_col: Item identifier column.

    Returns:
        Dictionary with item frequencies, top co-occurring pairs, and support info.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [transaction_col, item_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    total_transactions = df[transaction_col].nunique()
    if total_transactions == 0:
        raise ToolExecutionError("No transactions found.")

    # Item frequencies
    item_freq = df[item_col].value_counts()
    item_frequencies = {
        str(item): {"count": int(count), "support": round(count / total_transactions, 4)}
        for item, count in item_freq.head(50).items()
    }

    # Co-occurrence pairs
    baskets = df.groupby(transaction_col)[item_col].apply(set)
    pair_counts: dict[tuple[str, str], int] = {}

    for basket in baskets:
        items = sorted(str(i) for i in basket)
        if len(items) > 50:
            items = items[:50]  # cap to avoid combinatorial explosion
        for a, b in combinations(items, 2):
            key = (a, b)
            pair_counts[key] = pair_counts.get(key, 0) + 1

    top_pairs = sorted(pair_counts.items(), key=lambda x: -x[1])[:30]
    top_pairs_list = [
        {
            "item_a": pair[0],
            "item_b": pair[1],
            "count": count,
            "support": round(count / total_transactions, 4),
        }
        for pair, count in top_pairs
    ]

    return {
        "total_transactions": total_transactions,
        "unique_items": int(df[item_col].nunique()),
        "item_frequencies": item_frequencies,
        "top_pairs": top_pairs_list,
    }


def funnel_metrics(
    df: pd.DataFrame,
    stage_col: str,
    count_col: str | None = None,
) -> dict[str, Any]:
    """Calculate conversion funnel metrics between sequential stages.

    Args:
        df: DataFrame with one row per stage (or per user-stage).
            If ``count_col`` is None, counts are derived from row counts per stage.
        stage_col: Column containing stage names.
        count_col: Optional column with pre-aggregated counts.

    Returns:
        Dictionary with stage-by-stage metrics including conversion rate and drop-off.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    if stage_col not in df.columns:
        raise ToolExecutionError(f"Column '{stage_col}' not found in DataFrame.")
    if count_col is not None and count_col not in df.columns:
        raise ToolExecutionError(f"Column '{count_col}' not found in DataFrame.")

    if count_col:
        stage_counts = (
            df.groupby(stage_col)[count_col]
            .sum()
            .sort_values(ascending=False)
        )
    else:
        stage_counts = df[stage_col].value_counts()

    stages_list = []
    prev_count = None
    for stage_name, count in stage_counts.items():
        entry: dict[str, Any] = {
            "stage": str(stage_name),
            "count": int(count),
        }
        if prev_count is not None and prev_count > 0:
            entry["conversion_rate"] = round(count / prev_count, 4)
            entry["dropoff"] = int(prev_count - count)
            entry["dropoff_rate"] = round(1 - count / prev_count, 4)
        else:
            entry["conversion_rate"] = 1.0
            entry["dropoff"] = 0
            entry["dropoff_rate"] = 0.0
        prev_count = count
        stages_list.append(entry)

    overall_conversion = None
    if len(stages_list) >= 2 and stages_list[0]["count"] > 0:
        overall_conversion = round(stages_list[-1]["count"] / stages_list[0]["count"], 4)

    return {
        "stages": stages_list,
        "overall_conversion": overall_conversion,
        "total_stages": len(stages_list),
    }


# =============================================================================
# Manufacturing
# =============================================================================


def oee_calculation(
    df: pd.DataFrame,
    availability_col: str,
    performance_col: str,
    quality_col: str,
) -> dict[str, Any]:
    """Calculate Overall Equipment Effectiveness (OEE).

    OEE = Availability * Performance * Quality

    Args:
        df: DataFrame with OEE component values (0-1 scale or 0-100 scale).
        availability_col: Availability ratio column.
        performance_col: Performance ratio column.
        quality_col: Quality ratio column.

    Returns:
        Dictionary with aggregate OEE, component averages, and loss analysis.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [availability_col, performance_col, quality_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    avail = pd.to_numeric(df[availability_col], errors="coerce")
    perf = pd.to_numeric(df[performance_col], errors="coerce")
    qual = pd.to_numeric(df[quality_col], errors="coerce")

    # Auto-detect scale: if values are commonly > 1, treat as percentage
    if avail.median() > 1:
        avail = avail / 100.0
    if perf.median() > 1:
        perf = perf / 100.0
    if qual.median() > 1:
        qual = qual / 100.0

    oee = avail * perf * qual

    avail_mean = float(avail.mean())
    perf_mean = float(perf.mean())
    qual_mean = float(qual.mean())

    return {
        "oee": round(float(oee.mean()), 4),
        "availability": round(avail_mean, 4),
        "performance": round(perf_mean, 4),
        "quality": round(qual_mean, 4),
        "losses": {
            "availability_loss": round(1.0 - avail_mean, 4),
            "performance_loss": round(avail_mean * (1.0 - perf_mean), 4),
            "quality_loss": round(avail_mean * perf_mean * (1.0 - qual_mean), 4),
        },
        "oee_per_record": oee.round(4).tolist(),
        "world_class_benchmark": 0.85,
        "is_world_class": float(oee.mean()) >= 0.85,
    }


def mtbf_mttr(
    df: pd.DataFrame,
    failure_time_col: str,
    repair_time_col: str,
) -> dict[str, Any]:
    """Mean Time Between Failures and Mean Time To Repair.

    Args:
        df: DataFrame with failure event data.
        failure_time_col: Column with timestamps or durations since last failure.
        repair_time_col: Column with repair duration values (numeric, e.g. hours).

    Returns:
        Dictionary with MTBF, MTTR, availability, and descriptive statistics.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    for col in [failure_time_col, repair_time_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    failure_time = pd.to_numeric(df[failure_time_col], errors="coerce").dropna()
    repair_time = pd.to_numeric(df[repair_time_col], errors="coerce").dropna()

    if failure_time.empty or repair_time.empty:
        raise ToolExecutionError("Failure time and repair time columns must have numeric values.")

    mtbf_val = float(failure_time.mean())
    mttr_val = float(repair_time.mean())

    # Inherent availability = MTBF / (MTBF + MTTR)
    availability = mtbf_val / (mtbf_val + mttr_val) if (mtbf_val + mttr_val) > 0 else 0.0

    return {
        "mtbf": round(mtbf_val, 2),
        "mttr": round(mttr_val, 2),
        "availability": round(availability, 4),
        "failure_rate": round(1.0 / mtbf_val, 6) if mtbf_val > 0 else None,
        "total_failures": len(failure_time),
        "mtbf_stats": {
            "mean": round(mtbf_val, 2),
            "median": round(float(failure_time.median()), 2),
            "std": round(float(failure_time.std()), 2),
            "min": round(float(failure_time.min()), 2),
            "max": round(float(failure_time.max()), 2),
        },
        "mttr_stats": {
            "mean": round(mttr_val, 2),
            "median": round(float(repair_time.median()), 2),
            "std": round(float(repair_time.std()), 2),
            "min": round(float(repair_time.min()), 2),
            "max": round(float(repair_time.max()), 2),
        },
    }


def spc_control_limits(
    df: pd.DataFrame,
    measurement_col: str,
    subgroup_col: str | None = None,
) -> dict[str, Any]:
    """Statistical Process Control: calculate control limits.

    Uses X-bar and R chart logic for subgrouped data, or
    individuals (I-MR) chart for non-subgrouped data.

    Args:
        df: DataFrame with measurement data.
        measurement_col: Column with continuous measurement values.
        subgroup_col: Optional column defining rational subgroups.

    Returns:
        Dictionary with UCL, LCL, center line, and out-of-control points.

    Raises:
        ToolExecutionError: If columns are missing.
    """
    if measurement_col not in df.columns:
        raise ToolExecutionError(f"Column '{measurement_col}' not found in DataFrame.")
    if subgroup_col is not None and subgroup_col not in df.columns:
        raise ToolExecutionError(f"Column '{subgroup_col}' not found in DataFrame.")

    values = pd.to_numeric(df[measurement_col], errors="coerce").dropna()

    if len(values) < 2:
        raise ToolExecutionError("Need at least 2 measurements for control limits.")

    if subgroup_col is None:
        # Individuals chart (I-MR)
        center = float(values.mean())
        moving_range = values.diff().abs().dropna()
        mr_bar = float(moving_range.mean())
        # d2 constant for n=2 is 1.128
        sigma_est = mr_bar / 1.128
        ucl = center + 3 * sigma_est
        lcl = center - 3 * sigma_est

        out_of_control_idx = values[(values > ucl) | (values < lcl)].index.tolist()
    else:
        # X-bar chart
        subgroup_stats = df.groupby(subgroup_col)[measurement_col].agg(["mean", "std", "count"])
        subgroup_stats = subgroup_stats.dropna()
        center = float(subgroup_stats["mean"].mean())
        avg_range = float(subgroup_stats["std"].mean())
        avg_n = float(subgroup_stats["count"].mean())

        # A3 approximation: 3 / sqrt(n)
        a3 = 3.0 / np.sqrt(avg_n) if avg_n > 0 else 3.0
        ucl = center + a3 * avg_range
        lcl = center - a3 * avg_range

        out_of_control_idx = subgroup_stats[
            (subgroup_stats["mean"] > ucl) | (subgroup_stats["mean"] < lcl)
        ].index.tolist()

    return {
        "center_line": round(center, 4),
        "ucl": round(ucl, 4),
        "lcl": round(lcl, 4),
        "sigma": round((ucl - center) / 3, 4),
        "out_of_control_count": len(out_of_control_idx),
        "out_of_control_indices": out_of_control_idx[:50],  # cap output size
        "total_points": len(values),
        "process_capability": {
            "cp_proxy": round((ucl - lcl) / (6 * values.std()), 4) if values.std() > 0 else None,
        },
    }


# =============================================================================
# HR / People Analytics
# =============================================================================


def attrition_risk_features(
    df: pd.DataFrame,
    hire_date_col: str | None = None,
    department_col: str | None = None,
) -> pd.DataFrame:
    """Create attrition risk feature columns.

    Features: tenure_days, tenure_years, salary_ratio_to_dept_avg,
    is_long_tenure (>3yr), department_size.

    Args:
        df: Employee-level DataFrame.
        hire_date_col: Column with hire date.
        department_col: Column with department name.

    Returns:
        Copy of DataFrame with new feature columns.

    Raises:
        ToolExecutionError: If specified columns are missing.
    """
    for col_name, col_val in [("hire_date_col", hire_date_col),
                               ("department_col", department_col)]:
        if col_val is not None and col_val not in df.columns:
            raise ToolExecutionError(f"Column '{col_val}' ({col_name}) not found in DataFrame.")

    result = df.copy()

    if hire_date_col:
        hire = pd.to_datetime(result[hire_date_col], errors="coerce")
        today = pd.Timestamp.now()
        result["tenure_days"] = (today - hire).dt.days
        result["tenure_years"] = (result["tenure_days"] / 365.25).round(2)
        result["is_long_tenure"] = result["tenure_years"] > 3

    # Salary ratio to department average
    salary_col = None
    for candidate in ["salary", "compensation", "base_salary", "annual_salary", "pay"]:
        if candidate in df.columns:
            salary_col = candidate
            break

    if salary_col and department_col:
        salary = pd.to_numeric(result[salary_col], errors="coerce")
        dept_avg = salary.groupby(result[department_col]).transform("mean")
        result["salary_ratio_to_dept_avg"] = (salary / dept_avg).round(3)

    if department_col:
        result["department_size"] = result.groupby(department_col)[department_col].transform("count")

    return result


def diversity_metrics(
    df: pd.DataFrame,
    demographic_cols: list[str],
) -> dict[str, Any]:
    """Compute diversity representation and Simpson's Diversity Index.

    Args:
        df: Employee-level DataFrame.
        demographic_cols: List of columns with categorical demographic data.

    Returns:
        Dictionary with representation percentages and diversity index per column.

    Raises:
        ToolExecutionError: If any specified column is missing.
    """
    for col in demographic_cols:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    total = len(df)
    if total == 0:
        raise ToolExecutionError("DataFrame is empty.")

    results: dict[str, Any] = {}

    for col in demographic_cols:
        counts = df[col].value_counts(dropna=False)
        representation = {
            str(k): {
                "count": int(v),
                "percentage": round(v / total * 100, 2),
            }
            for k, v in counts.items()
        }

        # Simpson's Diversity Index: 1 - sum(p_i^2)
        proportions = counts.values / total
        simpson = float(1.0 - np.sum(proportions ** 2))

        results[col] = {
            "representation": representation,
            "simpson_diversity_index": round(simpson, 4),
            "unique_groups": int(counts.shape[0]),
        }

    return results


def compensation_equity(
    df: pd.DataFrame,
    salary_col: str,
    group_col: str,
    role_col: str | None = None,
) -> dict[str, Any]:
    """Pay gap analysis between demographic groups.

    Args:
        df: Employee-level DataFrame.
        salary_col: Column with salary/compensation values.
        group_col: Column with group labels (e.g. gender, ethnicity).
        role_col: Optional column with job role/level for adjusted analysis.

    Returns:
        Dictionary with raw gap metrics and adjusted gap if role_col is provided.

    Raises:
        ToolExecutionError: If required columns are missing.
    """
    for col in [salary_col, group_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")
    if role_col is not None and role_col not in df.columns:
        raise ToolExecutionError(f"Column '{role_col}' not found in DataFrame.")

    salary = pd.to_numeric(df[salary_col], errors="coerce")
    groups = df[group_col]

    # Raw gap: mean and median by group
    group_stats = salary.groupby(groups).agg(["mean", "median", "count", "std"])
    group_stats = group_stats.round(2)

    raw_gap = {}
    for group_name, row in group_stats.iterrows():
        raw_gap[str(group_name)] = {
            "mean": float(row["mean"]),
            "median": float(row["median"]),
            "count": int(row["count"]),
            "std": float(row["std"]) if not pd.isna(row["std"]) else 0.0,
        }

    # Overall gap relative to highest-paid group
    means = group_stats["mean"]
    ref_group = str(means.idxmax())
    ref_mean = float(means.max())

    gap_vs_reference = {}
    for group_name in means.index:
        if str(group_name) == ref_group:
            continue
        diff = float(ref_mean - means[group_name])
        pct = round(diff / ref_mean * 100, 2) if ref_mean > 0 else 0.0
        gap_vs_reference[str(group_name)] = {
            "absolute_gap": round(diff, 2),
            "percentage_gap": pct,
        }

    result: dict[str, Any] = {
        "raw_gap": raw_gap,
        "reference_group": ref_group,
        "gap_vs_reference": gap_vs_reference,
    }

    # Adjusted gap: within-role comparison
    if role_col:
        adjusted = {}
        for role, role_df in df.groupby(role_col):
            role_salary = pd.to_numeric(role_df[salary_col], errors="coerce")
            role_groups = role_df[group_col]
            role_means = role_salary.groupby(role_groups).mean()
            if len(role_means) > 1:
                role_ref = float(role_means.max())
                for g in role_means.index:
                    if float(role_means[g]) < role_ref:
                        key = f"{role}_{g}"
                        adjusted[key] = {
                            "role": str(role),
                            "group": str(g),
                            "gap_pct": round((role_ref - float(role_means[g])) / role_ref * 100, 2),
                        }
        result["adjusted_gap"] = adjusted

    return result


# =============================================================================
# Marketing
# =============================================================================


def campaign_lift(
    df: pd.DataFrame,
    treatment_col: str,
    outcome_col: str,
) -> dict[str, Any]:
    """A/B test campaign lift analysis.

    Args:
        df: DataFrame with experiment data.
        treatment_col: Binary column (1=treatment, 0=control).
        outcome_col: Binary outcome column (1=converted, 0=not).

    Returns:
        Dictionary with treatment/control rates, lift, and statistical significance.

    Raises:
        ToolExecutionError: If columns are missing or data is invalid.
    """
    for col in [treatment_col, outcome_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")

    treatment = pd.to_numeric(df[treatment_col], errors="coerce")
    outcome = pd.to_numeric(df[outcome_col], errors="coerce")

    mask = ~(treatment.isna() | outcome.isna())
    treatment, outcome = treatment[mask], outcome[mask]

    treat_mask = treatment == 1
    ctrl_mask = treatment == 0

    n_treat = int(treat_mask.sum())
    n_ctrl = int(ctrl_mask.sum())

    if n_treat == 0 or n_ctrl == 0:
        raise ToolExecutionError("Both treatment and control groups must have observations.")

    treat_rate = float(outcome[treat_mask].mean())
    ctrl_rate = float(outcome[ctrl_mask].mean())

    absolute_lift = treat_rate - ctrl_rate
    relative_lift = absolute_lift / ctrl_rate if ctrl_rate > 0 else float("inf")

    # Two-proportion z-test
    p_pooled = float(outcome.mean())
    if p_pooled > 0 and p_pooled < 1:
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1 / n_treat + 1 / n_ctrl))
        z_stat = absolute_lift / se if se > 0 else 0.0
        p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
    else:
        z_stat = 0.0
        p_value = 1.0

    return {
        "treatment_rate": round(treat_rate, 4),
        "control_rate": round(ctrl_rate, 4),
        "absolute_lift": round(absolute_lift, 4),
        "relative_lift": round(relative_lift, 4),
        "n_treatment": n_treat,
        "n_control": n_ctrl,
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "is_significant": p_value < 0.05,
        "confidence_level": 0.95,
    }


def attribution_simple(
    df: pd.DataFrame,
    channel_col: str,
    conversion_col: str,
    revenue_col: str | None = None,
) -> dict[str, Any]:
    """Last-touch attribution: conversions and revenue per channel.

    Args:
        df: DataFrame with marketing touchpoint data.
        channel_col: Column with channel/source name.
        conversion_col: Binary column indicating conversion.
        revenue_col: Optional revenue column.

    Returns:
        Dictionary with per-channel attribution metrics.

    Raises:
        ToolExecutionError: If required columns are missing.
    """
    for col in [channel_col, conversion_col]:
        if col not in df.columns:
            raise ToolExecutionError(f"Column '{col}' not found in DataFrame.")
    if revenue_col is not None and revenue_col not in df.columns:
        raise ToolExecutionError(f"Column '{revenue_col}' not found in DataFrame.")

    conversion = pd.to_numeric(df[conversion_col], errors="coerce").fillna(0)
    total_conversions = float(conversion.sum())

    channels: dict[str, Any] = {}
    for channel, group in df.groupby(channel_col):
        ch_conversion = pd.to_numeric(group[conversion_col], errors="coerce").fillna(0)
        ch_conversions = float(ch_conversion.sum())
        ch_total = len(group)

        entry: dict[str, Any] = {
            "impressions_or_touches": ch_total,
            "conversions": int(ch_conversions),
            "conversion_rate": round(ch_conversions / ch_total, 4) if ch_total > 0 else 0.0,
            "attribution_share": round(ch_conversions / total_conversions, 4) if total_conversions > 0 else 0.0,
        }

        if revenue_col:
            ch_revenue = pd.to_numeric(group[revenue_col], errors="coerce").fillna(0).sum()
            entry["revenue"] = round(float(ch_revenue), 2)
            entry["revenue_per_conversion"] = (
                round(float(ch_revenue) / ch_conversions, 2) if ch_conversions > 0 else 0.0
            )

        channels[str(channel)] = entry

    result: dict[str, Any] = {
        "attribution_model": "last_touch",
        "total_conversions": int(total_conversions),
        "channels": channels,
    }

    if revenue_col:
        total_revenue = float(pd.to_numeric(df[revenue_col], errors="coerce").fillna(0).sum())
        result["total_revenue"] = round(total_revenue, 2)

    return result
