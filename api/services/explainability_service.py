"""Explainability service — wraps explainability/* for the FastAPI layer.

Exposes six callables consumed by the explainability router:
  - compute_shap         Sync SHAP computation (recommended for sample_size ≤ 50)
  - compute_shap_async   Background job for larger sample sizes; returns job_id
  - whatif               Apply feature modifications, compare predictions
  - fairness_audit       Disparate-impact / group-fairness metrics
  - get_model_card       Build or return cached model card from state
  - _execute_shap        Async background worker for compute_shap_async

Data loading strategy
---------------------
The backend agents store a DuckDB table reference (``joined_data_ref``) in
state.  This service attempts to query that table first.  If the table is
unavailable (e.g. the connection was closed between requests), it falls back
to loading from the first entry in ``data_sources``.

Model loading
-------------
The best model artifact is loaded from ``state["best_model_path"]`` using
``joblib.load``.  If the path does not exist the function raises
``AutoDSError`` with an actionable message rather than propagating a raw
``FileNotFoundError``.

Cancellation
------------
``_execute_shap`` checks ``job_store.is_cancelled()`` before and after the
CPU-bound SHAP computation.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from explainability.shap_explainer import compute_shap_values as _compute_shap
from explainability.fairness_audit import run_fairness_audit as _run_fairness_audit
from explainability.counterfactual import generate_counterfactuals as _gen_counterfactuals
from explainability.model_card_generator import generate_model_card as _gen_model_card
from api.services import state_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_model(state: dict) -> Any:
    """Load the best-model artifact from ``best_model_path`` in state."""
    model_path: str | None = state.get("best_model_path")
    if not model_path:
        raise AutoDSError(
            "No best_model_path in state — run modeling (train) before computing "
            "explainability."
        )
    path = Path(model_path)
    if not path.exists():
        raise AutoDSError(
            f"Model artifact not found at '{model_path}'.  "
            "Re-run model training to regenerate the artifact."
        )
    return joblib.load(path)


def _load_df(state: dict) -> pd.DataFrame:
    """Return a DataFrame for the working dataset.

    Tries ``state["joined_data_ref"]`` as a DuckDB table name first; falls
    back to the first accessible path in ``state["data_sources"]``.

    Raises:
        AutoDSError: If no data can be loaded via either strategy.
    """
    import duckdb  # deferred — not always installed in minimal envs

    # ---- DuckDB strategy ------------------------------------------------
    joined_ref: str | None = state.get("joined_data_ref")
    if joined_ref:
        try:
            con = duckdb.connect()
            df = con.execute(f'SELECT * FROM "{joined_ref}"').df()
            con.close()
            if not df.empty:
                return df
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "DuckDB load failed for joined_data_ref=%s: %s", joined_ref, exc
            )

    # ---- data_sources fallback ------------------------------------------
    data_sources: list = state.get("data_sources") or []
    for src in data_sources:
        path: str | None = None
        if isinstance(src, dict):
            path = src.get("local_path") or src.get("file_path")
        elif hasattr(src, "local_path"):
            path = str(src.local_path)
        elif hasattr(src, "file_path"):
            path = str(src.file_path)

        if path and Path(path).exists():
            try:
                p = Path(path)
                if p.suffix.lower() in {".parquet", ".feather"}:
                    return pd.read_parquet(p)
                return pd.read_csv(p)
            except Exception as exc:  # noqa: BLE001
                logger.debug("File load failed for path=%s: %s", path, exc)

    raise AutoDSError(
        "No data available: DuckDB table not found and no accessible data source paths."
    )


def _feature_columns(state: dict) -> list[str]:
    """Return the final feature column list from state (best available key)."""
    return (
        state.get("feature_list")
        or state.get("features_selected")
        or state.get("features_created")
        or []
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_shap(
    project_id: str,
    user_id: str,
    sample_size: int = 100,
) -> dict:
    """Compute SHAP global and local explanations synchronously.

    Loads the best model and feature data from state, computes SHAP values,
    persists results to state, and returns the result dict.

    For ``sample_size > 50`` consider using ``compute_shap_async`` so the
    caller is not blocked.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        sample_size: Maximum rows to pass to the SHAP explainer.

    Returns:
        Dict with keys: ``global_importance``, ``top_features``,
        ``shap_values``, ``feature_names``, ``n_rows_explained``.

    Raises:
        AutoDSError: If state not found, model artifact missing, or data
            unavailable.
    """
    state = state_service.load_state(project_id, user_id)
    model = _load_model(state)

    feature_cols = _feature_columns(state)
    df = _load_df(state)

    # Filter to known feature columns; fall back to all numeric if list empty.
    if feature_cols:
        X = df[[c for c in feature_cols if c in df.columns]]
    else:
        X = df.select_dtypes(include="number")

    problem_type: str = state.get("problem_type", "classification")

    shap_result: dict = _compute_shap(
        model, X, problem_type=problem_type, max_rows=sample_size
    )

    if not shap_result:
        logger.warning(
            "compute_shap_values returned empty result for project=%s", project_id
        )

    state_service.update_state(project_id, user_id, shap_values=shap_result)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "explainability",
        "action": "compute_shap",
        "sample_size": sample_size,
        "n_features": len(shap_result.get("feature_names") or []),
    })

    return shap_result


def compute_shap_async(
    project_id: str,
    user_id: str,
    sample_size: int,
) -> str:
    """Create a background SHAP job and return its job_id.

    Recommended when ``sample_size > 50``.  The caller should poll
    ``GET /jobs/{job_id}`` or use SSE to track progress.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        sample_size: Maximum rows passed to the SHAP explainer.

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state_service.load_state(project_id, user_id)  # ownership check

    job_id = job_store.create_job("shap_computation", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_shap(job_id, project_id, user_id, sample_size))
    except RuntimeError:
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.", job_id
        )
        asyncio.run(_execute_shap(job_id, project_id, user_id, sample_size))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "explainability",
        "action": "compute_shap_async",
        "job_id": job_id,
        "sample_size": sample_size,
        "status": "scheduled",
    })

    return job_id


def whatif(
    project_id: str,
    user_id: str,
    base_row: dict,
    modifications: dict,
) -> dict:
    """Apply feature modifications to a base row and compare predictions.

    Constructs an original row from *base_row*, creates a modified copy by
    overlaying *modifications*, generates predictions for both, and attempts
    to find counterfactual examples from the training data.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        base_row: Mapping of feature name → original value.
        modifications: Mapping of feature name → new value.  Keys must be
            a subset of *base_row*'s feature names.

    Returns:
        Dict with keys: ``base_row``, ``modified_row``,
        ``original_prediction``, ``modified_prediction``,
        ``changed_features``, ``counterfactuals``.

    Raises:
        AutoDSError: If the project is not found, access is denied, or the
            model artifact is missing.
    """
    state = state_service.load_state(project_id, user_id)
    model = _load_model(state)

    feature_cols = _feature_columns(state)
    modified_data: dict = {**base_row, **modifications}

    orig_df = pd.DataFrame([base_row])
    mod_df = pd.DataFrame([modified_data])

    # Restrict to the columns the model was trained on.
    if feature_cols:
        model_cols = [c for c in feature_cols if c in orig_df.columns]
    else:
        model_cols = list(orig_df.select_dtypes(include="number").columns)

    original_pred: Any = None
    modified_pred: Any = None

    if model_cols:
        try:
            if hasattr(model, "predict_proba"):
                original_pred = model.predict_proba(orig_df[model_cols])[0].tolist()
                modified_pred = model.predict_proba(mod_df[model_cols])[0].tolist()
            else:
                val = model.predict(orig_df[model_cols])[0]
                original_pred = val.item() if hasattr(val, "item") else val
                val = model.predict(mod_df[model_cols])[0]
                modified_pred = val.item() if hasattr(val, "item") else val
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "whatif prediction failed for project=%s: %s", project_id, exc
            )

    # Best-effort counterfactuals.
    counterfactuals: list[dict] = []
    try:
        df = _load_df(state)
        X_train = df[[c for c in model_cols if c in df.columns]] if model_cols else df
        instance = pd.Series(modified_data)
        if model_cols:
            instance = instance.reindex(model_cols)
        counterfactuals = _gen_counterfactuals(
            model, instance, X_train, n_counterfactuals=3
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "whatif counterfactuals failed for project=%s: %s", project_id, exc
        )

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "explainability",
        "action": "whatif",
        "changed_features": list(modifications.keys()),
    })

    return {
        "base_row": base_row,
        "modified_row": modified_data,
        "original_prediction": original_pred,
        "modified_prediction": modified_pred,
        "changed_features": list(modifications.keys()),
        "counterfactuals": counterfactuals,
    }


def fairness_audit(
    project_id: str,
    user_id: str,
    protected_attributes: list[str],
) -> dict:
    """Run a disparate-impact / group-fairness audit on the best model.

    Loads the full dataset, extracts features, true labels, and the
    requested sensitive attributes, then delegates to
    ``run_fairness_audit``.  Results are persisted to state.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        protected_attributes: Column names in the dataset to audit
            (e.g. ``["gender", "race"]``).

    Returns:
        Dict with keys: ``per_attribute``, ``n_samples``,
        ``n_attributes_audited``, ``recommendations``.

    Raises:
        AutoDSError: If the project is not found, access is denied,
            the model artifact is missing, no protected attribute columns
            are found in the data, or the target column is absent.
    """
    state = state_service.load_state(project_id, user_id)
    model = _load_model(state)

    target_column: str | None = state.get("target_column")
    feature_cols = _feature_columns(state)

    df = _load_df(state)

    # Build feature matrix.
    if feature_cols:
        available_features = [c for c in feature_cols if c in df.columns]
        X = df[available_features] if available_features else df.select_dtypes(include="number")
    else:
        X = df.select_dtypes(include="number")

    # True labels.
    if not target_column or target_column not in df.columns:
        raise AutoDSError(
            f"target_column '{target_column}' not found in dataset columns.  "
            "Set target_column in project configuration."
        )
    y_true = df[target_column]

    # Sensitive feature series.
    sensitive_features: dict[str, pd.Series] = {
        attr: df[attr]
        for attr in protected_attributes
        if attr in df.columns
    }
    missing = [a for a in protected_attributes if a not in df.columns]
    if missing:
        logger.warning(
            "fairness_audit: protected attributes %s not found in data — skipped.",
            missing,
        )
    if not sensitive_features:
        raise AutoDSError(
            f"None of the requested protected attributes {protected_attributes} "
            "were found in the dataset columns."
        )

    result: dict = _run_fairness_audit(model, X, y_true, sensitive_features)

    state_service.update_state(project_id, user_id, fairness_report=result)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "explainability",
        "action": "fairness_audit",
        "protected_attributes": protected_attributes,
        "attributes_audited": list(sensitive_features.keys()),
    })

    return result


def get_model_card(project_id: str, user_id: str) -> dict:
    """Build a model card for the best model and return it.

    Returns the cached model card from state if one was already generated.
    Otherwise builds it from state data (SHAP results and fairness report
    are included if available) and persists it.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        Model card dict with keys: ``model_details``, ``intended_use``,
        ``training_data``, ``metrics``, ``feature_importance``,
        ``limitations``, ``ethical_considerations``, ``fairness``,
        ``generated_at``.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    # Return cached card if present.
    cached: dict | None = state.get("model_card")
    if cached:
        return cached

    model_name: str = (
        state.get("best_model")
        or state.get("best_model_name")
        or "unknown"
    )
    problem_type: str = state.get("problem_type", "classification")
    domain: str = state.get("detected_domain", "generic")
    metrics: dict = state.get("best_model_metrics") or {}
    features: list[str] = _feature_columns(state)

    # Best-effort row count.
    training_rows = 0
    try:
        df = _load_df(state)
        training_rows = len(df)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "get_model_card: could not load data for row count: %s", exc
        )
        training_rows = state.get("row_count") or 0

    card: dict = _gen_model_card(
        model_name=model_name,
        problem_type=problem_type,
        domain=domain,
        metrics=metrics,
        features=features,
        training_rows=training_rows,
        shap_results=state.get("shap_values"),
        fairness_results=state.get("fairness_report"),
        domain_config=state.get("domain_config"),
    )

    state_service.update_state(project_id, user_id, model_card=card)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "explainability",
        "action": "get_model_card",
        "model_name": model_name,
    })

    return card


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_shap(
    job_id: str,
    project_id: str,
    user_id: str,
    sample_size: int,
) -> None:
    """Background coroutine that computes SHAP values for a large sample.

    Steps:
        1. Mark job running.
        2. Load state (check cancel).
        3. Load model + feature data in thread executor.
        4. Run ``compute_shap_values`` in thread executor (CPU-bound).
        5. Persist results to state.
        6. Set job result and mark completed.

    Cancellation is checked after state load and after computation.

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
        sample_size: Max rows passed to the SHAP explainer.
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="explainability",
        message=f"Starting SHAP computation (sample_size={sample_size})...",
    )

    try:
        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 1 — load state
        # ------------------------------------------------------------------ #
        state: dict = await loop.run_in_executor(
            None,
            lambda: state_service.load_state(project_id, user_id),
        )

        if job_store.is_cancelled(job_id):
            return

        job_store.update_job(
            job_id,
            progress=0.10,
            message="Loading model and feature data...",
        )

        # ------------------------------------------------------------------ #
        # Step 2 — load model + data (I/O-bound, still in executor)
        # ------------------------------------------------------------------ #
        def _load() -> tuple[Any, pd.DataFrame, str]:
            mdl = _load_model(state)
            feature_cols = _feature_columns(state)
            df = _load_df(state)
            if feature_cols:
                X = df[[c for c in feature_cols if c in df.columns]]
            else:
                X = df.select_dtypes(include="number")
            pt = state.get("problem_type", "classification")
            return mdl, X, pt

        model, X, problem_type = await loop.run_in_executor(None, _load)

        job_store.update_job(
            job_id,
            progress=0.20,
            message=f"Computing SHAP values for {min(len(X), sample_size)} rows...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 3 — compute SHAP (CPU-bound)
        # ------------------------------------------------------------------ #
        shap_result: dict = await loop.run_in_executor(
            None,
            lambda: _compute_shap(model, X, problem_type=problem_type, max_rows=sample_size),
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 4 — persist results
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.90,
            message="Saving SHAP results...",
        )

        await loop.run_in_executor(
            None,
            lambda: state_service.update_state(
                project_id, user_id, shap_values=shap_result
            ),
        )

        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "explainability",
            "action": "compute_shap_async_complete",
            "job_id": job_id,
            "n_features": len(shap_result.get("feature_names") or []),
            "n_rows_explained": shap_result.get("n_rows_explained", 0),
        })

        job_store.set_result(job_id, shap_result)

        top = (shap_result.get("top_features") or [])[:3]
        top_names = [f["feature"] for f in top if isinstance(f, dict)]
        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message=(
                f"SHAP complete. Top features: {', '.join(top_names) or 'N/A'}."
            ),
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception(
            "SHAP computation failed for job_id=%s project=%s", job_id, project_id
        )
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"SHAP computation failed: {exc}",
        )
