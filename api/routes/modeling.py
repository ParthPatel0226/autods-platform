"""Modeling routes — configure, train, leaderboard, select-best.

Prefix : /modeling
Tags   : modeling
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.modeling import Leaderboard, ModelEntry, SelectBestRequest, TrainRequest
from api.services import modeling_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/configure",
    response_model=dict,
    summary="Configure modeling: algorithms, metric, validation strategy",
)
async def configure_modeling(
    project_id: str,
    body: dict,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Merge user model configuration into project state and return an ETA estimate."""
    try:
        result = modeling_service.configure(project_id, current_user["user_id"], body)
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
            detail=f"Failed to configure modeling: {exc}",
        ) from exc

    estimated_algorithms: int = result.get("estimated_algorithms") or 3
    return {"eta_seconds": estimated_algorithms * 60}


@router.post(
    "/train",
    response_model=dict,
    summary="Start model training in the background",
)
async def train_models(
    body: TrainRequest,
    tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Schedule model training as a background job and return the job_id."""
    try:
        job_id = modeling_service.train(
            body.project_id,
            current_user["user_id"],
            body.config.model_dump(),
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
            detail=f"Failed to start model training: {exc}",
        ) from exc

    return {"job_id": job_id}


@router.get(
    "/leaderboard/{project_id}",
    response_model=Leaderboard,
    summary="Retrieve model leaderboard for a project",
)
async def get_leaderboard(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Leaderboard:
    """Return all trained model results ranked by primary metric."""
    try:
        result = modeling_service.get_leaderboard(project_id, current_user["user_id"])
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
            detail=f"Failed to retrieve leaderboard: {exc}",
        ) from exc

    raw_entries: list[dict] = result.get("entries") or []
    entries = [
        ModelEntry(
            model_name=e.get("model_name", ""),
            metrics=e.get("metrics") or {},
            train_time=float(e.get("train_time", 0.0)),
            rank=int(e.get("rank", 0)),
            mlflow_run_id=e.get("mlflow_run_id"),
        )
        for e in raw_entries
    ]

    return Leaderboard(
        project_id=project_id,
        entries=entries,
        best_model=result.get("best_model", ""),
    )


@router.post(
    "/select-best",
    response_model=dict,
    summary="Override best-model selection for a project",
)
async def select_best(
    body: SelectBestRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Persist a user-chosen model as the project best model."""
    try:
        modeling_service.select_best(
            body.project_id, current_user["user_id"], body.model_name
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
            detail=f"Failed to select best model: {exc}",
        ) from exc

    return {"selected": body.model_name}
