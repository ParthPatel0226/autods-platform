"""Prediction routes — single row and batch inference.

Prefix : /predict
Tags   : predict
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.predict import (
    BatchPredictRequest,
    BatchPredictResponse,
    ConfidenceInterval,
    PredictRequest,
    PredictResponse,
)
from api.services import predict_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/single",
    response_model=PredictResponse,
    summary="Predict a single row using the project's best model",
)
async def predict_single(
    body: PredictRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> PredictResponse:
    """Load best model and return prediction + optional SHAP values for one row."""
    try:
        result = predict_service.predict_single(
            body.project_id, current_user["user_id"], body.features
        )
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc

    ci_raw = result.get("confidence_interval")
    ci = (
        ConfidenceInterval(lower=ci_raw["lower"], upper=ci_raw["upper"])
        if isinstance(ci_raw, dict) and "lower" in ci_raw and "upper" in ci_raw
        else None
    )

    return PredictResponse(
        prediction=result.get("prediction"),
        probability=result.get("probability"),
        confidence_interval=ci,
        shap=result.get("shap"),
    )


@router.post(
    "/batch",
    response_model=BatchPredictResponse,
    summary="Start batch prediction in the background",
)
async def predict_batch(
    body: BatchPredictRequest,
    tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> BatchPredictResponse:
    """Schedule batch inference as a background job; returns job_id and row count."""
    try:
        result = predict_service.predict_batch(
            body.project_id, current_user["user_id"], body.file_id
        )
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch prediction: {exc}",
        ) from exc

    if isinstance(result, str):
        return BatchPredictResponse(job_id=result, n_rows=0)

    return BatchPredictResponse(
        job_id=result.get("job_id", ""),
        n_rows=int(result.get("n_rows", 0)),
    )
