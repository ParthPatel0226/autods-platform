"""Adverse action reason code generator.

Used in finance (ECOA/Reg B compliance): when a credit or lending decision
is negative, the lender must provide the top N reasons (typically 4) that
most contributed to the adverse outcome.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def generate_adverse_action_codes(
    model: Any,
    instance: pd.Series,
    shap_values: np.ndarray | list,
    feature_names: list[str],
    top_n: int = 4,
) -> list[dict[str, Any]]:
    """Generate adverse action reason codes from SHAP contributions.

    Sorts features by absolute SHAP value descending and returns the
    top N as structured reason codes.

    Args:
        model: Fitted estimator (used for context; not called).
        instance: The applicant observation.
        shap_values: SHAP values for this instance (1-D or 2-D array;
            if 2-D, the first row is used).
        feature_names: Feature names matching the SHAP values.
        top_n: Number of reason codes to return (typically 4 for ECOA).

    Returns:
        List of dicts with ``reason_code``, ``feature``,
        ``feature_value``, ``impact``, and ``direction``.
    """
    arr = np.array(shap_values)
    if arr.ndim == 2:
        arr = arr[0]

    if len(arr) != len(feature_names):
        logger.error(
            "SHAP values length (%d) does not match feature names (%d).",
            len(arr), len(feature_names),
        )
        return []

    if len(arr) == 0:
        return []

    abs_vals = np.abs(arr)
    top_idx = np.argsort(abs_vals)[::-1][:top_n]

    codes: list[dict[str, Any]] = []
    for rank, idx in enumerate(top_idx, start=1):
        feat = feature_names[idx]
        impact = float(arr[idx])
        feat_val = instance.get(feat, None)

        codes.append({
            "reason_code": f"AA{rank:02d}",
            "feature": feat,
            "feature_value": _jsonable(feat_val),
            "impact": round(impact, 6),
            "direction": "adverse" if impact > 0 else "favorable",
            "rank": rank,
        })

    logger.info("Generated %d adverse action code(s).", len(codes))
    return codes


def format_adverse_action_notice(codes: list[dict[str, Any]]) -> str:
    """Format adverse action codes into a consumer-facing notice.

    Args:
        codes: Output from ``generate_adverse_action_codes``.

    Returns:
        Multi-line plain text notice.
    """
    if not codes:
        return "No adverse action reasons available."

    lines = [
        "ADVERSE ACTION NOTICE",
        "=" * 40,
        "",
        "The following factors contributed most to this decision:",
        "",
    ]

    for code in codes:
        reason = _human_readable_reason(code["feature"], code["feature_value"], code["direction"])
        lines.append(f"  {code['reason_code']}: {reason}")

    lines.extend([
        "",
        "This notice is provided in accordance with the Equal Credit Opportunity Act (ECOA).",
        "You have the right to request additional information about the factors that affected this decision.",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEATURE_DESCRIPTIONS: dict[str, str] = {
    "credit_score": "Credit score",
    "debt_to_income": "Debt-to-income ratio",
    "loan_amount": "Requested loan amount",
    "annual_income": "Annual income",
    "employment_length": "Length of employment",
    "num_delinquencies": "Number of delinquencies",
    "credit_utilization": "Credit utilization ratio",
    "num_open_accounts": "Number of open credit accounts",
    "months_since_last_delinq": "Time since last delinquency",
    "total_credit_lines": "Total number of credit lines",
}


def _human_readable_reason(feature: str, value: Any, direction: str) -> str:
    """Convert a feature name and value into a human-readable reason."""
    display_name = _FEATURE_DESCRIPTIONS.get(feature, feature.replace("_", " ").title())
    val_str = _format_value(value)

    if direction == "adverse":
        return f"{display_name} ({val_str}) negatively affected this decision."
    return f"{display_name} ({val_str}) was a favorable factor but insufficient to change the outcome."


def _format_value(val: Any) -> str:
    """Format a value for display in the notice."""
    if val is None:
        return "not provided"
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:,.2f}"
        return f"{val:.4f}"
    return str(val)


def _jsonable(val: Any) -> Any:
    """Convert numpy types for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 6)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val
