"""Feature Engineering routes — suggest decisions, apply, results.

Prefix : /fe
Tags   : feature-engineering
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.feature_engineering import FEApplyRequest, FEResults, FESuggestResponse, FESuggestion
from api.services import fe_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/suggest",
    response_model=FESuggestResponse,
    summary="Get per-column feature engineering suggestions",
)
async def suggest_decisions(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> FESuggestResponse:
    """Return domain-aware FE suggestions for each column in the project."""
    try:
        suggestions_raw = fe_service.suggest_decisions(project_id, current_user["user_id"])
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
            detail=f"Failed to generate FE suggestions: {exc}",
        ) from exc

    suggestions = [
        FESuggestion(
            column=s.get("column", ""),
            decisions=s.get("decisions", {}),
            recommendation_reason=s.get("recommendation_reason"),
        )
        for s in suggestions_raw
    ]

    return FESuggestResponse(suggestions=suggestions, project_id=project_id)


@router.post(
    "/apply",
    response_model=dict,
    summary="Apply feature engineering decisions in the background",
)
async def apply_decisions(
    body: FEApplyRequest,
    tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Store FE decisions and launch feature engineering as a background job."""
    try:
        job_id = fe_service.apply_decisions(
            body.project_id, current_user["user_id"], body.decisions
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
            detail=f"Failed to apply FE decisions: {exc}",
        ) from exc

    return {"job_id": job_id}


@router.get(
    "/results/{project_id}",
    response_model=FEResults,
    summary="Retrieve completed feature engineering results",
)
async def get_results(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> FEResults:
    """Return FE results once the background job completes."""
    try:
        results = fe_service.get_results(project_id, current_user["user_id"])
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
            detail=f"Failed to retrieve FE results: {exc}",
        ) from exc

    return FEResults(
        features_created=results.get("features_created"),
        features_selected=results.get("features_selected"),
        feature_importance_preliminary=results.get("feature_importance_preliminary"),
        fe_choices=results.get("fe_choices"),
        imputation_strategy=results.get("imputation_strategy"),
        encoding_strategy=results.get("encoding_strategy"),
        scaling_strategy=results.get("scaling_strategy"),
        outlier_strategy=results.get("outlier_strategy"),
    )
