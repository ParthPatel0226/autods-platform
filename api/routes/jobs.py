"""Jobs routes — job status, results, and SSE streaming.

Prefix : /jobs
Tags   : jobs
"""
from __future__ import annotations

import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dependencies import get_current_user
from api.schemas.jobs import JobProgressEvent, JobResult, JobStatus
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(job_id: str, user_id: str) -> dict:
    """Fetch job dict; raise 404 if missing, 403 if owned by another user."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id!r} not found")
    if job.get("user_id") and job["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return job


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}",
    response_model=JobStatus,
    summary="Get job status",
)
async def get_job_status(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> JobStatus:
    """Return current status and progress for a background job."""
    try:
        job = _get_or_404(job_id, current_user["user_id"])
    except HTTPException:
        raise
    except AutoDSError as exc:
        code = status.HTTP_403_FORBIDDEN if "denied" in str(exc).lower() else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job: {exc}",
        ) from exc

    return JobStatus(
        job_id=job["job_id"],
        status=job.get("status", "pending"),
        progress=job.get("progress", 0.0),
        current_step=job.get("current_step"),
        started_at=job["started_at"],
        finished_at=job.get("finished_at"),
        error=job.get("error"),
    )


@router.get(
    "/{job_id}/result",
    response_model=JobResult,
    summary="Get job result",
)
async def get_job_result(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> JobResult:
    """Return the result payload for a completed job."""
    try:
        _get_or_404(job_id, current_user["user_id"])
        result = job_store.get_result(job_id)
    except HTTPException:
        raise
    except AutoDSError as exc:
        code = status.HTTP_403_FORBIDDEN if "denied" in str(exc).lower() else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job result: {exc}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not yet available; job may still be running",
        )

    return JobResult(job_id=job_id, result=result)


@router.delete(
    "/{job_id}",
    response_model=dict,
    summary="Cancel a job",
)
async def cancel_job(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Request cancellation of a pending or running job."""
    try:
        _get_or_404(job_id, current_user["user_id"])
        cancelled = job_store.cancel_job(job_id)
    except HTTPException:
        raise
    except AutoDSError as exc:
        code = status.HTTP_403_FORBIDDEN if "denied" in str(exc).lower() else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {exc}",
        ) from exc

    return {"cancelled": cancelled}


@router.get(
    "/{job_id}/stream",
    response_class=StreamingResponse,
    summary="Stream job progress via SSE",
)
async def stream_job(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> StreamingResponse:
    """Open a Server-Sent Events stream that emits JobProgressEvent updates until the job reaches a terminal state."""
    # Verify access before opening the stream.
    try:
        _get_or_404(job_id, current_user["user_id"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open job stream: {exc}",
        ) from exc

    try:
        from sse_starlette.sse import EventSourceResponse  # type: ignore[import]
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SSE streaming requires sse-starlette package",
        ) from exc

    async def _event_generator() -> AsyncGenerator[dict, None]:
        async for event in job_store.subscribe(job_id):
            if event is None:
                # Sentinel — stream finished
                break
            if isinstance(event, dict):
                payload = event
            else:
                # Pydantic model or dataclass
                payload = event if isinstance(event, dict) else vars(event) if hasattr(event, "__dict__") else dict(event)
            yield {"data": JobProgressEvent(**payload).model_dump_json()}

    return EventSourceResponse(_event_generator())
