"""Background job status schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | completed | failed
    progress: float = 0.0  # 0.0–1.0
    current_step: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class JobResult(BaseModel):
    job_id: str
    result: dict[str, Any]


class JobProgressEvent(BaseModel):
    """Server-Sent Events payload for live job progress streaming."""

    job_id: str
    status: str
    progress: float
    message: str
    timestamp: datetime
