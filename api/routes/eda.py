"""EDA routes — question generation, answer submission, analysis execution.

Prefix : /eda
Tags   : eda
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.eda import EDAAnswerRequest, EDAQuestion, EDAResults, EDARunRequest
from api.services import eda_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/generate-questions",
    response_model=list[EDAQuestion],
    summary="Generate domain-aware EDA questions for the project",
)
async def generate_questions(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[EDAQuestion]:
    """Return interactive EDA questions based on domain and data profile."""
    try:
        questions = eda_service.generate_questions(project_id, current_user["user_id"])
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
            detail=f"Failed to generate EDA questions: {exc}",
        ) from exc

    return [
        EDAQuestion(
            id=q.get("id", ""),
            step=q.get("step", "eda"),
            question=q.get("question", ""),
            type=q.get("type", "single_select"),
            options=q.get("options"),
            recommendation_reason=q.get("recommendation_reason"),
        )
        for q in questions
    ]


@router.post(
    "/answer",
    response_model=dict,
    summary="Submit answers to EDA questions",
)
async def answer_questions(
    body: EDAAnswerRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Store user answers to EDA questions in project state."""
    try:
        eda_service.submit_answers(body.project_id, current_user["user_id"], body.answers)
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
            detail=f"Failed to submit EDA answers: {exc}",
        ) from exc

    return {"updated": True}


@router.post(
    "/run",
    response_model=dict,
    summary="Start EDA analysis in the background",
)
async def run_eda(
    body: EDARunRequest,
    tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Launch EDA execution as a background task and return the job_id."""
    try:
        job_id = job_store.create_job("eda", body.project_id, current_user["user_id"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create EDA job: {exc}",
        ) from exc

    tasks.add_task(eda_service._execute_eda, job_id, body.project_id, current_user["user_id"])

    return {"job_id": job_id}


@router.get(
    "/results/{project_id}",
    response_model=EDAResults,
    summary="Retrieve completed EDA results",
)
async def get_results(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> EDAResults:
    """Return EDA analysis results once the background job completes."""
    try:
        results = eda_service.get_results(project_id, current_user["user_id"])
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
            detail=f"Failed to retrieve EDA results: {exc}",
        ) from exc

    return EDAResults(
        eda_results=results.get("eda_results"),
        eda_charts=results.get("eda_charts"),
        eda_summary=results.get("eda_summary"),
        eda_insights=results.get("eda_insights"),
        eda_analyses_selected=results.get("eda_analyses_selected"),
    )
