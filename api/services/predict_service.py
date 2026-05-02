"""Prediction service — wraps serving/model_loader.py for the FastAPI layer.

Exposes three callables consumed by the prediction router:
  - predict_single    Load model, predict one row, compute local SHAP
  - predict_batch     Create job and schedule background batch inference; return job_id
  - _execute_batch    Async background worker; chunks input file, predicts, uploads CSV

Composition
-----------
``serving.model_loader.load_model_cached`` handles model loading with an
in-process cache keyed to the model path — no joblib re-load per request.

``explainability.shap_explainer.compute_shap_values`` computes local SHAP for a
single row; returns ``{}`` on failure (non-fatal).

``api.storage.file_storage`` reads the uploaded input file and writes the
results CSV back to the same storage layer (Supabase or local /tmp fallback).

Batch chunking
--------------
``_execute_batch`` reads the input file in full (download_dataset returns bytes),
parses it, then predicts in chunks of 1 000 rows.  Progress is emitted after
each chunk; the band is 0.20 → 0.85 for the prediction loop.

Cancellation
------------
``_execute_batch`` checks ``job_store.is_cancelled()`` after the setup phase and
after each chunk.  The results are not uploaded if the job is cancelled.
"""
from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from api.services import state_service
from api.storage import job_store
from api.storage.file_storage import download_dataset, upload_report
from core.exceptions import AutoDSError
from explainability.shap_explainer import compute_shap_values as _compute_shap
from serving.model_loader import get_feature_names, load_model_cached

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1_000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _feature_columns(state: dict) -> list[str]:
    """Priority chain for feature column names in state."""
    return (
        state.get("feature_list")
        or state.get("features_selected")
        or state.get("features_created")
        or []
    )


def _parse_bytes(data: bytes) -> pd.DataFrame:
    """Parse raw bytes into a DataFrame.  Tries CSV then Parquet."""
    try:
        return pd.read_csv(io.BytesIO(data))
    except Exception:
        pass
    try:
        return pd.read_parquet(io.BytesIO(data))
    except Exception as exc:
        raise AutoDSError(f"Cannot parse input file (tried CSV and Parquet): {exc}") from exc


def _predict_df(model: Any, df: pd.DataFrame, problem_type: str) -> tuple[list, list | None]:
    """Run model inference on a DataFrame.

    Returns:
        Tuple of (predictions, probabilities).
        ``probabilities`` is a list of dicts {class: prob} for classification,
        or None for regression.
    """
    predictions = model.predict(df).tolist()

    probabilities: list | None = None
    if problem_type == "classification" and hasattr(model, "predict_proba"):
        try:
            proba_arr = model.predict_proba(df)
            classes = [str(c) for c in model.classes_]
            probabilities = [
                {cls: float(p) for cls, p in zip(classes, row)}
                for row in proba_arr
            ]
        except Exception as exc:
            logger.warning("predict_proba failed: %s — skipping probabilities.", exc)

    return predictions, probabilities


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def predict_single(project_id: str, user_id: str, features: dict) -> dict:
    """Load model, predict one row, and compute a local SHAP explanation.

    ``features`` is a flat dict of ``{column_name: value}``.  Only keys matching
    the model's feature list are forwarded; extra keys are silently ignored and
    missing keys are filled with NaN so the model receives a complete row.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        features: Dict of feature name → scalar value for the row to predict.

    Returns:
        Dict with keys::

            {
                "prediction":       int | float | str,
                "prediction_label": str,
                "probabilities":    dict[str, float] | None,
                "confidence":       float | None,
                "shap_explanation": list[dict] | None,
                "model":            str,
                "features_used":    list[str],
                "features_received": int,
            }

    Raises:
        AutoDSError: If the project is not found, access denied, or no trained
            model is available.
    """
    state = state_service.load_state(project_id, user_id)

    model_path: str | None = state.get("best_model_path")
    if not model_path:
        raise AutoDSError(
            "No trained model found.  Run the modeling step before predicting."
        )

    # ------------------------------------------------------------------ #
    # Load model (cached)
    # ------------------------------------------------------------------ #
    try:
        model, metadata = load_model_cached(model_path)
    except FileNotFoundError as exc:
        raise AutoDSError(str(exc)) from exc

    # Feature column priority: metadata sidecar > state
    model_cols: list[str] = get_feature_names(metadata) or _feature_columns(state)
    problem_type: str = (
        metadata.get("problem_type")
        or state.get("problem_type")
        or "classification"
    )

    # ------------------------------------------------------------------ #
    # Build single-row DataFrame aligned to model columns
    # ------------------------------------------------------------------ #
    row: dict = {col: features.get(col, np.nan) for col in model_cols} if model_cols else features
    X = pd.DataFrame([row])
    if model_cols:
        # Ensure column order and no extras
        X = X.reindex(columns=model_cols)

    # ------------------------------------------------------------------ #
    # Predict
    # ------------------------------------------------------------------ #
    predictions, probabilities = _predict_df(model, X, problem_type)
    raw_pred = predictions[0]
    pred_label = str(raw_pred)

    confidence: float | None = None
    proba_row: dict | None = None
    if probabilities:
        proba_row = probabilities[0]
        confidence = max(proba_row.values())

    # ------------------------------------------------------------------ #
    # Local SHAP (best-effort — returns {} on failure)
    # ------------------------------------------------------------------ #
    shap_explanation: list[dict] | None = None
    shap_result = _compute_shap(model, X, problem_type=problem_type, max_rows=1)
    if shap_result:
        global_imp: dict = shap_result.get("global_importance") or {}
        feat_names: list = shap_result.get("feature_names") or list(X.columns)
        shap_vals = shap_result.get("shap_values")

        # Build per-feature local explanation
        if shap_vals is not None and len(shap_vals) > 0:
            local_vals = np.asarray(shap_vals[0]) if hasattr(shap_vals, "__getitem__") else np.array([])
            if local_vals.ndim > 1:
                local_vals = local_vals.mean(axis=-1)

            shap_explanation = []
            for idx, fname in enumerate(feat_names):
                local_v = float(local_vals[idx]) if idx < len(local_vals) else 0.0
                shap_explanation.append({
                    "feature": fname,
                    "value": float(X.iloc[0][fname]) if fname in X.columns else None,
                    "shap_value": local_v,
                    "global_importance": float(global_imp.get(fname, 0.0)),
                })
            shap_explanation.sort(key=lambda d: abs(d["shap_value"]), reverse=True)
        elif global_imp:
            shap_explanation = [
                {"feature": k, "value": float(X.iloc[0][k]) if k in X.columns else None,
                 "shap_value": None, "global_importance": float(v)}
                for k, v in sorted(global_imp.items(), key=lambda x: abs(x[1]), reverse=True)
            ]

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "predict_single",
        "action": "predict",
        "model": state.get("best_model", "unknown"),
        "prediction": pred_label,
    })

    return {
        "prediction": raw_pred,
        "prediction_label": pred_label,
        "probabilities": proba_row,
        "confidence": confidence,
        "shap_explanation": shap_explanation,
        "model": state.get("best_model", metadata.get("algorithm", "unknown")),
        "features_used": model_cols or list(X.columns),
        "features_received": len(features),
    }


def predict_batch(project_id: str, user_id: str, file_id: str) -> str:
    """Create a batch prediction job and schedule it as an async background task.

    The input file (CSV or Parquet) must have been uploaded via the upload
    endpoint first.  ``file_id`` is the ``source_id`` returned by that upload.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        file_id: Storage identifier of the uploaded input file.

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    # Ownership check before creating a job record.
    state_service.load_state(project_id, user_id)

    job_id = job_store.create_job("batch_prediction", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_batch(job_id, project_id, user_id, file_id))
    except RuntimeError:
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.", job_id
        )
        asyncio.run(_execute_batch(job_id, project_id, user_id, file_id))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "predict_batch",
        "action": "predict_batch",
        "job_id": job_id,
        "file_id": file_id,
        "status": "scheduled",
    })

    return job_id


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_batch(
    job_id: str,
    project_id: str,
    user_id: str,
    file_id: str,
) -> None:
    """Background coroutine that runs batch inference on an uploaded file.

    Steps:
        1. Mark job running.
        2. Load state; resolve model path and feature columns.
        3. Load model via ``load_model_cached`` in thread executor.
        4. Download input file bytes from file storage.
        5. Parse bytes into DataFrame (CSV first, then Parquet fallback).
        6. Predict in chunks of 1 000 rows, emitting progress events.
        7. Assemble results; upload as CSV to report storage.
        8. Set job result with download URL and mark completed.

    Cancellation is checked after setup and after each chunk.  If cancelled,
    the results file is not uploaded and the job remains in its cancelled state.

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
        file_id:    ``source_id`` of the uploaded input file in file storage.
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="predict_batch",
        message="Starting batch prediction...",
    )

    try:
        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 1 — load state, model, metadata
        # ------------------------------------------------------------------ #
        state: dict = await loop.run_in_executor(
            None,
            lambda: state_service.load_state(project_id, user_id),
        )

        model_path: str | None = state.get("best_model_path")
        if not model_path:
            raise AutoDSError(
                "No trained model found.  Run the modeling step before batch prediction."
            )

        job_store.update_job(
            job_id,
            progress=0.08,
            message="Loading model...",
        )

        model, metadata = await loop.run_in_executor(
            None, lambda: load_model_cached(model_path)
        )

        model_cols: list[str] = get_feature_names(metadata) or _feature_columns(state)
        problem_type: str = (
            metadata.get("problem_type")
            or state.get("problem_type")
            or "classification"
        )

        job_store.update_job(
            job_id,
            progress=0.10,
            message=f"Model loaded ({state.get('best_model', 'unknown')}). Downloading input file...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 2 — download and parse input file
        # ------------------------------------------------------------------ #
        raw_bytes: bytes = await loop.run_in_executor(
            None, lambda: download_dataset(file_id, project_id)
        )

        df_input: pd.DataFrame = await loop.run_in_executor(
            None, lambda: _parse_bytes(raw_bytes)
        )

        total_rows = len(df_input)
        n_chunks = max(1, (total_rows + _CHUNK_SIZE - 1) // _CHUNK_SIZE)

        job_store.update_job(
            job_id,
            progress=0.15,
            message=f"Input file loaded: {total_rows:,} rows. Predicting in {n_chunks} chunk(s)...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 3 — chunk predictions (0.20 → 0.85 band)
        # ------------------------------------------------------------------ #
        all_predictions: list = []
        all_probabilities: list[dict | None] = []

        for chunk_idx in range(n_chunks):
            if job_store.is_cancelled(job_id):
                return

            start = chunk_idx * _CHUNK_SIZE
            end = min(start + _CHUNK_SIZE, total_rows)
            chunk = df_input.iloc[start:end].copy()

            # Align to model feature columns
            if model_cols:
                for col in model_cols:
                    if col not in chunk.columns:
                        chunk[col] = np.nan
                chunk = chunk.reindex(columns=model_cols)

            try:
                preds, probas = await loop.run_in_executor(
                    None, lambda c=chunk: _predict_df(model, c, problem_type)
                )
                all_predictions.extend(preds)
                if probas is not None:
                    all_probabilities.extend(probas)
                else:
                    all_probabilities.extend([None] * len(preds))
            except Exception as exc:
                logger.warning(
                    "Chunk %d/%d failed for job_id=%s: %s — filling NaN.",
                    chunk_idx + 1, n_chunks, job_id, exc,
                )
                all_predictions.extend([None] * (end - start))
                all_probabilities.extend([None] * (end - start))

            progress = 0.20 + 0.65 * ((chunk_idx + 1) / n_chunks)
            job_store.update_job(
                job_id,
                progress=round(progress, 3),
                message=(
                    f"Predicted rows {start + 1:,}–{end:,} of {total_rows:,} "
                    f"({chunk_idx + 1}/{n_chunks} chunks)..."
                ),
            )

            # Yield control so the event loop can flush SSE
            await asyncio.sleep(0)

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 4 — assemble results DataFrame and upload
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.88,
            message="Assembling results and uploading...",
        )

        result_df = df_input.copy()
        result_df["prediction"] = all_predictions

        # Attach per-class probability columns for classification
        has_probas = any(p is not None for p in all_probabilities)
        if has_probas:
            # Collect union of class keys
            all_classes: list[str] = []
            for p in all_probabilities:
                if p is not None:
                    for k in p:
                        if k not in all_classes:
                            all_classes.append(k)
            for cls in all_classes:
                result_df[f"prob_{cls}"] = [
                    (p.get(cls) if p else None) for p in all_probabilities
                ]

        # Serialise to CSV bytes
        csv_bytes: bytes = result_df.to_csv(index=False).encode("utf-8")

        report_id, download_url = await loop.run_in_executor(
            None,
            lambda: upload_report(csv_bytes, project_id, "csv"),
        )

        # ------------------------------------------------------------------ #
        # Step 5 — finalise
        # ------------------------------------------------------------------ #
        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "predict_batch",
            "action": "complete",
            "job_id": job_id,
            "total_rows": total_rows,
            "report_id": report_id,
        })

        result = {
            "total_rows": total_rows,
            "model": state.get("best_model", metadata.get("algorithm", "unknown")),
            "problem_type": problem_type,
            "report_id": report_id,
            "download_url": download_url,
            "columns": list(result_df.columns),
        }
        job_store.set_result(job_id, result)

        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message=(
                f"Batch prediction complete. "
                f"{total_rows:,} rows predicted. Download: {download_url}"
            ),
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception(
            "Batch prediction failed for job_id=%s project=%s", job_id, project_id
        )
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"Batch prediction failed: {exc}",
        )
