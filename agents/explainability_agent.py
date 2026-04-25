"""Explainability Agent.

Generates SHAP global + local explanations, fairness audits, and
a structured model card for the best trained model.

State fields read:
    best_model / best_model_name  - model identifier
    best_model_path               - path to saved model .pkl
    model_results / trained_models / best_model_metrics - metrics
    feature_list / features_selected - feature names
    target_column                 - target variable name
    problem_type                  - classification | regression | clustering
    detected_domain               - domain string
    domain_config                 - full domain config dict
    joined_data_ref               - DuckDB table name for data
    data_sources                  - fallback list of DataSourceInfo
    user_mode                     - auto | guided | expert

State fields written:
    shap_values       - SHAP results dict
    fairness_report   - fairness audit results (or None)
    model_card        - model card dict
    explainability_results - combined results dict
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from agents.tools.data_tools import query_duckdb, split_train_test
from agents.tools.ml_tools import get_feature_importance, load_model
from core.state import AutoDSState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain-specific model card text
# ---------------------------------------------------------------------------

_DOMAIN_INTENDED_USE: dict[str, str] = {
    "healthcare": (
        "Intended for clinical decision support only. "
        "This model does not replace clinical judgment and requires physician review "
        "before any action is taken on its outputs."
    ),
    "finance": (
        "Credit scoring or financial risk model. "
        "Subject to fair lending regulations and adverse action notice requirements. "
        "Outputs must be reviewed by a qualified compliance officer before use."
    ),
    "hr": (
        "Employee attrition or HR outcome prediction. "
        "Sensitive use case — requires HR leadership review and approval "
        "before any personnel decisions are influenced by this model."
    ),
    "generic": (
        "General purpose predictive model. "
        "Validate performance on representative new data before deployment."
    ),
}

_DOMAIN_LIMITATIONS: dict[str, str] = {
    "healthcare": (
        "Model performance may degrade for patient subgroups underrepresented in training data. "
        "Not validated for use outside the data distribution it was trained on. "
        "Does not account for temporal drift in clinical practice guidelines."
    ),
    "finance": (
        "Model reflects historical lending patterns, which may contain systemic biases. "
        "Requires ongoing monitoring for population shift and regulatory compliance. "
        "Not suitable for real-time decisioning without additional validation."
    ),
    "hr": (
        "Predictions are correlational, not causal. "
        "Sensitive to demographic representation in training data. "
        "Must not be used as sole basis for employment decisions."
    ),
    "generic": (
        "Performance may degrade if the prediction context changes significantly "
        "from conditions at training time. Monitor for data drift after deployment."
    ),
}


def _get_domain_text(domain: str, mapping: dict[str, str]) -> str:
    """Return domain-specific text with generic fallback."""
    return mapping.get(domain, mapping["generic"])


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

_MAX_SHAP_ROWS = 500


def _load_dataframe(state: AutoDSState) -> pd.DataFrame | None:
    """Attempt to load a DataFrame from DuckDB or data_sources fallback."""
    table_ref: str = state.get("joined_data_ref", "")
    if table_ref:
        try:
            return query_duckdb(f"SELECT * FROM {table_ref}")
        except Exception as exc:
            logger.warning("DuckDB load failed for table '%s': %s", table_ref, exc)

    sources = state.get("data_sources", [])
    for src in sources:
        path = src.get("source_path", "")
        fmt = src.get("format", "")
        if not path:
            continue
        try:
            if "csv" in fmt or path.endswith(".csv"):
                return pd.read_csv(path)
            if "parquet" in fmt or path.endswith(".parquet"):
                return pd.read_parquet(path)
            if "excel" in fmt or path.endswith((".xlsx", ".xls")):
                return pd.read_excel(path)
        except Exception as exc:
            logger.warning("Fallback load failed for '%s': %s", path, exc)

    return None


def _resolve_model(state: AutoDSState) -> Any | None:
    """Load the best model from disk; return None on failure."""
    path: str = state.get("best_model_path", "")
    if not path:
        logger.warning("No best_model_path in state; skipping model load.")
        return None
    try:
        loaded = load_model(path)
        if isinstance(loaded, dict):
            return loaded["model"]
        return loaded
    except Exception as exc:
        logger.error("Failed to load model from '%s': %s", path, exc)
        return None


def _resolve_feature_list(state: AutoDSState) -> list[str]:
    """Return the feature list from state, trying multiple keys."""
    return (
        state.get("feature_list")
        or state.get("features_selected")
        or state.get("features_created")
        or []
    )


def _resolve_model_name(state: AutoDSState) -> str:
    return state.get("best_model") or state.get("best_model_name") or "unknown_model"


def _resolve_metrics(state: AutoDSState) -> dict[str, Any]:
    model_name = _resolve_model_name(state)
    explicit = state.get("best_model_metrics")
    if explicit:
        return explicit
    results = state.get("model_results") or {}
    if model_name in results:
        return results[model_name]
    trained = state.get("trained_models") or {}
    entry = trained.get(model_name, {})
    return entry.get("metrics", {})


# ---------------------------------------------------------------------------
# SHAP computation
# ---------------------------------------------------------------------------


def _compute_shap(
    model: Any,
    X_test: pd.DataFrame,
    problem_type: str,
    state: AutoDSState,
) -> dict[str, Any]:
    """Compute SHAP values (global mean |SHAP| + raw values array).

    Returns an empty dict and appends an error to state on failure.
    """
    try:
        import shap  # type: ignore[import]
    except ImportError:
        logger.warning("shap package not installed; skipping SHAP computation.")
        return {}

    X_test = X_test.select_dtypes(include="number")
    if X_test.empty:
        logger.warning("No numeric columns available for SHAP computation.")
        return {}
    sample = X_test.iloc[:_MAX_SHAP_ROWS].copy()

    try:
        if hasattr(model, "feature_importances_") and not hasattr(model, "coef_"):
            explainer = shap.TreeExplainer(model)
            shap_vals = explainer.shap_values(sample)
        elif problem_type == "classification" and hasattr(model, "predict_proba"):
            background = shap.sample(sample, min(50, len(sample)))
            explainer = shap.KernelExplainer(model.predict_proba, background)
            shap_vals = explainer.shap_values(sample, nsamples=100)
        else:
            background = shap.sample(sample, min(50, len(sample)))
            explainer = shap.KernelExplainer(model.predict, background)
            shap_vals = explainer.shap_values(sample, nsamples=100)

        # Normalise multi-class output: take class-1 or average across classes
        if isinstance(shap_vals, list):
            if len(shap_vals) == 2:
                arr = np.array(shap_vals[1])
            else:
                arr = np.mean([np.abs(v) for v in shap_vals], axis=0)
        else:
            arr = np.array(shap_vals)

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        feature_names = list(sample.columns)
        mean_abs_shap = np.abs(arr).mean(axis=0).tolist()
        global_importance = {
            feat: round(float(val), 6)
            for feat, val in zip(feature_names, mean_abs_shap)
        }
        sorted_importance = sorted(
            global_importance.items(), key=lambda x: x[1], reverse=True
        )

        logger.info("SHAP computation succeeded for %d rows.", len(sample))
        return {
            "global_importance": global_importance,
            "top_features": [
                {"feature": k, "mean_abs_shap": v} for k, v in sorted_importance[:20]
            ],
            "shap_values_sample": arr.tolist(),
            "n_rows_explained": len(sample),
            "feature_names": feature_names,
        }

    except Exception as exc:
        logger.error("SHAP computation failed: %s", exc)
        _append_error(state, "shap_error", str(exc))
        return {}


# ---------------------------------------------------------------------------
# Fairness audit
# ---------------------------------------------------------------------------


def _run_fairness_audit(
    model: Any,
    df: pd.DataFrame,
    target_col: str,
    protected_attributes: list[str],
    state: AutoDSState,
) -> dict[str, Any]:
    """Compute demographic parity difference for each protected attribute."""
    feature_list = _resolve_feature_list(state)
    available_attrs = [a for a in protected_attributes if a in df.columns]

    if not available_attrs:
        logger.info("No protected attributes found in data; skipping fairness audit.")
        return {"skipped": True, "reason": "No protected attributes present in dataset."}

    x_cols = (
        [c for c in feature_list if c in df.columns]
        if feature_list
        else [c for c in df.columns if c != target_col]
    )
    X = df[x_cols].fillna(0)
    y_true = df[target_col]

    try:
        y_pred = pd.Series(model.predict(X), index=df.index)
    except Exception as exc:
        logger.error("Fairness: prediction failed: %s", exc)
        _append_error(state, "fairness_predict_error", str(exc))
        return {}

    results: dict[str, Any] = {}
    for attr in available_attrs:
        try:
            results[attr] = _fairness_for_attribute(y_true, y_pred, df[attr])
        except Exception as exc:
            logger.warning("Fairness metric failed for '%s': %s", attr, exc)
            results[attr] = {"error": str(exc)}

    return {
        "protected_attributes_audited": available_attrs,
        "metrics_per_attribute": results,
    }


def _fairness_for_attribute(
    y_true: pd.Series,
    y_pred: pd.Series,
    group_col: pd.Series,
) -> dict[str, Any]:
    """Compute demographic parity difference (and equalized odds if available)."""
    try:
        from fairlearn.metrics import (  # type: ignore[import]
            demographic_parity_difference,
            equalized_odds_difference,
        )
        dpd = float(demographic_parity_difference(y_true, y_pred, sensitive_features=group_col))
        eod = float(equalized_odds_difference(y_true, y_pred, sensitive_features=group_col))
        return {
            "demographic_parity_difference": round(dpd, 6),
            "equalized_odds_difference": round(eod, 6),
            "method": "fairlearn",
        }
    except ImportError:
        pass

    # Manual fallback: demographic parity = max group rate - min group rate
    group_rates: dict[str, float] = {}
    for grp in group_col.unique():
        mask = group_col == grp
        if mask.sum() == 0:
            continue
        group_rates[str(grp)] = float(y_pred[mask].mean())

    if not group_rates:
        return {"demographic_parity_difference": None, "method": "manual"}

    rates = list(group_rates.values())
    dpd_manual = round(max(rates) - min(rates), 6)
    return {
        "demographic_parity_difference": dpd_manual,
        "group_prediction_rates": {k: round(v, 6) for k, v in group_rates.items()},
        "method": "manual",
    }


# ---------------------------------------------------------------------------
# Model card generation
# ---------------------------------------------------------------------------


def _build_model_card(
    state: AutoDSState,
    shap_results: dict[str, Any],
    fairness_result: dict[str, Any] | None,
    training_rows: int,
) -> dict[str, Any]:
    """Assemble a structured model card."""
    domain: str = state.get("detected_domain") or "generic"
    model_name = _resolve_model_name(state)
    feature_list = _resolve_feature_list(state)
    metrics = _resolve_metrics(state)

    top_features: list[dict[str, Any]] = []
    if shap_results.get("top_features"):
        top_features = shap_results["top_features"][:10]
    elif state.get("feature_importance_preliminary"):
        raw = state["feature_importance_preliminary"]
        sorted_fi = sorted(raw.items(), key=lambda x: x[1], reverse=True)
        top_features = [{"feature": k, "score": v} for k, v in sorted_fi[:10]]

    return {
        "model_name": model_name,
        "problem_type": state.get("problem_type", "unknown"),
        "domain": domain,
        "training_data_rows": training_rows,
        "features": feature_list,
        "feature_count": len(feature_list),
        "target": state.get("target_column"),
        "performance": metrics,
        "feature_importance": top_features,
        "fairness_report": fairness_result,
        "intended_use": _get_domain_text(domain, _DOMAIN_INTENDED_USE),
        "limitations": _get_domain_text(domain, _DOMAIN_LIMITATIONS),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _append_error(state: AutoDSState, error_type: str, detail: str) -> None:
    errors: list[dict[str, Any]] = list(state.get("errors") or [])
    errors.append(
        {
            "step": "explainability",
            "type": error_type,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    state["errors"] = errors


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_explainability(state: AutoDSState) -> AutoDSState:
    """Execute the explainability pipeline.

    Steps:
    1. Load model from disk.
    2. Load evaluation data and prepare a held-out test split.
    3. Compute SHAP global + local explanations (TreeExplainer or KernelExplainer).
    4. Run fairness audit when domain_config requires it.
    5. Build a structured model card.
    6. Write all results back to state.

    Args:
        state: Shared LangGraph workflow state.

    Returns:
        Updated state with shap_values, fairness_report, model_card,
        and explainability_results populated.
    """
    state["current_step"] = "explainability"
    logger.info("Starting explainability agent for model '%s'.", _resolve_model_name(state))

    model = _resolve_model(state)
    feature_list = _resolve_feature_list(state)
    target_col: str = state.get("target_column") or ""
    problem_type: str = state.get("problem_type") or "classification"
    domain: str = state.get("detected_domain") or "generic"
    domain_config: dict[str, Any] = state.get("domain_config") or {}

    # --- Load data -----------------------------------------------------------
    df: pd.DataFrame | None = _load_dataframe(state)
    training_rows = len(df) if df is not None else 0

    X_test: pd.DataFrame | None = None
    if df is not None and model is not None and target_col and target_col in df.columns:
        try:
            _, test_df = split_train_test(df, target_col, test_size=0.2, stratify=True)
            x_cols = (
                [c for c in feature_list if c in test_df.columns]
                if feature_list
                else [c for c in test_df.columns if c != target_col]
            )
            X_test = test_df[x_cols]
        except Exception as exc:
            logger.warning("Train/test split failed: %s. Using full df sample.", exc)
            x_cols = (
                [c for c in feature_list if c in df.columns]
                if feature_list
                else [c for c in df.columns if c != target_col]
            )
            X_test = df[x_cols].iloc[:_MAX_SHAP_ROWS]

    # --- SHAP ----------------------------------------------------------------
    shap_results: dict[str, Any] = {}
    if model is not None and X_test is not None:
        shap_results = _compute_shap(model, X_test, problem_type, state)
    else:
        logger.warning(
            "SHAP skipped: model_loaded=%s, X_test_available=%s",
            model is not None,
            X_test is not None,
        )

    state["shap_values"] = shap_results

    # --- Fairness audit ------------------------------------------------------
    fairness_result: dict[str, Any] | None = None
    fairness_cfg: dict[str, Any] = domain_config.get("fairness", {})
    fairness_required: bool = bool(fairness_cfg.get("required", False))

    if fairness_required and model is not None and df is not None and target_col:
        protected_attrs: list[str] = fairness_cfg.get("protected_attributes", [])
        try:
            fairness_result = _run_fairness_audit(model, df, target_col, protected_attrs, state)
            logger.info("Fairness audit complete for attributes: %s", protected_attrs)
        except Exception as exc:
            logger.error("Fairness audit failed: %s", exc)
            _append_error(state, "fairness_error", str(exc))
            fairness_result = {"error": str(exc)}
    else:
        logger.info(
            "Fairness audit skipped (required=%s, model=%s, data=%s).",
            fairness_required,
            model is not None,
            df is not None,
        )

    state["fairness_report"] = fairness_result

    # --- Model card ----------------------------------------------------------
    try:
        model_card = _build_model_card(state, shap_results, fairness_result, training_rows)
        state["model_card"] = model_card
        logger.info("Model card generated at %s.", model_card["generated_at"])
    except Exception as exc:
        logger.error("Model card generation failed: %s", exc)
        _append_error(state, "model_card_error", str(exc))
        state["model_card"] = {}

    # --- Combine all results -------------------------------------------------
    state["explainability_results"] = {
        "shap": shap_results,
        "fairness": fairness_result,
        "model_card": state.get("model_card"),
        "domain": domain,
        "model_name": _resolve_model_name(state),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    completed: list[str] = list(state.get("completed_steps") or [])
    if "explainability" not in completed:
        completed.append("explainability")
    state["completed_steps"] = completed

    logger.info("Explainability agent finished successfully.")
    return state
