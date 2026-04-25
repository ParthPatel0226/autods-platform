"""FastAPI prediction endpoint.

Serves predictions from trained AutoDS models.  Run with:
    uvicorn serving.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from serving.model_loader import (
    clear_cache,
    get_feature_names,
    get_model_info,
    load_model_cached,
    load_model_metadata,
)
from serving.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ErrorResponse,
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
    PredictionResult,
)

logger = logging.getLogger(__name__)

_VERSION = "0.1.0"
_MODEL_PATH_ENV = "AUTODS_MODEL_PATH"
_API_KEY_ENV = "AUTODS_API_KEY"
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Validate X-API-Key header if AUTODS_API_KEY env var is set. No-op if not set."""
    required_key = os.environ.get(_API_KEY_ENV)
    if not required_key:
        return  # Auth not configured — allow all requests
    if api_key != required_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(
    title="AutoDS Prediction API",
    description="Serve predictions from AutoDS-trained models",
    version=_VERSION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_model_path() -> str:
    """Resolve model path from env var or default."""
    return os.environ.get(_MODEL_PATH_ENV, "artifacts/best_model.joblib")


def _predict_single(
    model: Any,
    features: dict[str, Any],
    feature_names: list[str],
    include_shap: bool = False,
) -> PredictionResult:
    """Run prediction for a single sample."""
    # Build DataFrame with correct column order
    if feature_names:
        missing = [f for f in feature_names if f not in features]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        row = {f: features[f] for f in feature_names}
    else:
        row = features

    df = pd.DataFrame([row])

    # Prediction
    prediction = model.predict(df)[0]
    if isinstance(prediction, (np.integer, np.floating)):
        prediction = prediction.item()

    # Probabilities (classification)
    confidence = None
    probabilities = None
    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(df)[0]
            classes = model.classes_
            probabilities = {str(c): round(float(p), 6) for c, p in zip(classes, proba)}
            confidence = float(max(proba))
        except Exception:
            pass

    # SHAP (optional)
    shap_values = None
    if include_shap:
        shap_values = _compute_shap(model, df, feature_names or list(features.keys()))

    return PredictionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=probabilities,
        shap_values=shap_values,
    )


def _compute_shap(
    model: Any,
    df: pd.DataFrame,
    feature_names: list[str],
) -> dict[str, float] | None:
    """Compute SHAP values for a single sample. Returns None on failure."""
    try:
        import shap

        try:
            explainer = shap.TreeExplainer(model)
        except Exception:
            explainer = shap.KernelExplainer(model.predict, df)

        sv = explainer.shap_values(df)
        if isinstance(sv, list):
            sv = sv[1] if len(sv) > 1 else sv[0]
        values = sv[0] if sv.ndim > 1 else sv
        return {name: round(float(v), 6) for name, v in zip(feature_names, values)}
    except Exception as exc:
        logger.warning("SHAP computation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, dependencies=[Security(_verify_api_key)])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    model_loaded = False
    try:
        model_path = _get_model_path()
        from pathlib import Path

        model_loaded = Path(model_path).is_file()
    except Exception:
        pass

    return HealthResponse(status="healthy", version=_VERSION, model_loaded=model_loaded)


@app.get("/info", response_model=ModelInfoResponse, dependencies=[Security(_verify_api_key)])
def model_info() -> ModelInfoResponse:
    """Return model metadata."""
    model_path = _get_model_path()
    metadata = load_model_metadata(model_path)
    info = get_model_info(metadata)
    feature_names = get_feature_names(metadata)

    return ModelInfoResponse(
        algorithm=info["algorithm"],
        problem_type=info["problem_type"],
        trained_at=info["trained_at"],
        features=info["features"],
        domain=info["domain"],
        feature_names=feature_names,
    )


@app.post("/predict", response_model=PredictionResponse, dependencies=[Security(_verify_api_key)])
def predict(request: PredictionRequest) -> PredictionResponse:
    """Single sample prediction."""
    model_path = _get_model_path()

    try:
        model, metadata = load_model_cached(model_path)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Model not loaded. Train a model first.")
    except RuntimeError as exc:
        logger.error("Model load error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error loading model.")

    feature_names = get_feature_names(metadata)

    try:
        result = _predict_single(model, request.features, feature_names, request.include_shap)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise HTTPException(status_code=500, detail="Prediction error. Check server logs.")

    return PredictionResponse(result=result)


@app.post("/predict/batch", response_model=BatchPredictionResponse, dependencies=[Security(_verify_api_key)])
def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """Batch prediction for multiple samples."""
    model_path = _get_model_path()

    try:
        model, metadata = load_model_cached(model_path)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Model not loaded. Train a model first.")
    except RuntimeError as exc:
        logger.error("Model load error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error loading model.")

    feature_names = get_feature_names(metadata)
    results: list[PredictionResult] = []

    for i, sample in enumerate(request.samples):
        try:
            result = _predict_single(model, sample, feature_names, request.include_shap)
            results.append(result)
        except Exception as exc:
            logger.error("Prediction failed for sample %d: %s", i, exc)
            results.append(PredictionResult(prediction=None, confidence=None))

    return BatchPredictionResponse(results=results, count=len(results))


@app.post("/reload", dependencies=[Security(_verify_api_key)])
def reload_model() -> dict[str, str]:
    """Force reload the model from disk (after retraining)."""
    clear_cache()
    return {"status": "cache_cleared", "message": "Model will be reloaded on next prediction."}
