"""Explainability routes — SHAP, what-if, fairness, model card.

Prefix : /explain
Tags   : explainability
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from api.dependencies import get_current_user
from api.schemas.explainability import (
    FairnessReport,
    FairnessRequest,
    ModelCardResponse,
    SHAPRequest,
    SHAPResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from api.services import explainability_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()

_SYNC_SHAP_THRESHOLD = 50


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/shap",
    response_model=None,
    summary="Compute SHAP values (sync ≤50 rows, async >50 rows)",
)
async def compute_shap(
    body: SHAPRequest,
    tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SHAPResponse | Response:
    """Return SHAP values synchronously for small samples; launch background job for large ones."""
    if body.sample_size <= _SYNC_SHAP_THRESHOLD:
        try:
            result = explainability_service.compute_shap(
                body.project_id, current_user["user_id"], body.sample_size
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
                detail=f"SHAP computation failed: {exc}",
            ) from exc

        return SHAPResponse(
            global_importance=result.get("global_importance") or {},
            local_examples=result.get("local_examples") or [],
            interactions=result.get("interactions"),
        )

    # Async path — large sample
    try:
        job_id = explainability_service.compute_shap_async(
            body.project_id, current_user["user_id"], body.sample_size
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
            detail=f"Failed to start async SHAP job: {exc}",
        ) from exc

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"job_id": job_id},
    )


@router.post(
    "/whatif",
    response_model=WhatIfResponse,
    summary="Run a what-if analysis by modifying feature values",
)
async def whatif(
    body: WhatIfRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> WhatIfResponse:
    """Apply feature modifications to a base row and compare predictions."""
    try:
        result = explainability_service.whatif(
            body.project_id,
            current_user["user_id"],
            body.base_row,
            body.modifications,
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
            detail=f"What-if analysis failed: {exc}",
        ) from exc

    return WhatIfResponse(
        original_prediction=result.get("original_prediction"),
        new_prediction=result.get("new_prediction"),
        delta=result.get("delta"),
        feature_contributions=result.get("feature_contributions") or {},
    )


@router.post(
    "/fairness",
    response_model=FairnessReport,
    summary="Run fairness audit on the best model",
)
async def fairness_audit(
    body: FairnessRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> FairnessReport:
    """Compute disparate-impact and group-fairness metrics for protected attributes."""
    try:
        result = explainability_service.fairness_audit(
            body.project_id, current_user["user_id"], body.protected_attributes
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
            detail=f"Fairness audit failed: {exc}",
        ) from exc

    return FairnessReport(
        project_id=body.project_id,
        metrics=result.get("metrics") or {},
        disparities=result.get("disparities") or {},
        recommendations=result.get("recommendations") or [],
    )


@router.get(
    "/model-card/{project_id}",
    response_model=ModelCardResponse,
    summary="Retrieve or generate model card for a project",
)
async def get_model_card(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ModelCardResponse:
    """Return the standardised model card (Google model card format) for the project."""
    try:
        result = explainability_service.get_model_card(
            project_id, current_user["user_id"]
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
            detail=f"Failed to retrieve model card: {exc}",
        ) from exc

    return ModelCardResponse(
        project_id=project_id,
        model_card=result if isinstance(result, dict) else {"content": result},
    )
