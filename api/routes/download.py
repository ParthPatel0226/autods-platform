"""Download routes — report generation and file streaming.

Prefix : /download
Tags   : download
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import get_current_user
from api.schemas.download import ReportJobResponse, ReportRequest
from api.services import report_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/report",
    response_model=ReportJobResponse,
    summary="Enqueue a report generation job",
)
async def generate_report(
    body: ReportRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ReportJobResponse:
    """Schedule report generation as a background job and return the job_id."""
    try:
        job_id = report_service.generate_report(
            body.project_id, current_user["user_id"], body.format
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
            detail=f"Failed to start report generation: {exc}",
        ) from exc

    return ReportJobResponse(job_id=job_id)


@router.get(
    "/file/{report_id}",
    response_class=FileResponse,
    summary="Stream a generated report file",
)
async def download_file(
    report_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> FileResponse:
    """Return the generated report file as a binary download."""
    try:
        result = report_service.get_report(report_id, current_user["user_id"])
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
            detail=f"Failed to retrieve report: {exc}",
        ) from exc

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # result may be a dict with a "path" key or a mapping of format -> path
    file_path: str | None = None
    if isinstance(result, dict):
        file_path = result.get("path") or result.get("file_path")
        if file_path is None:
            # pick the first non-None path value from a format-keyed dict
            for v in result.values():
                if isinstance(v, str) and v:
                    file_path = v
                    break

    if not file_path or not Path(file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not yet available; check job status first",
        )

    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="application/octet-stream",
    )
