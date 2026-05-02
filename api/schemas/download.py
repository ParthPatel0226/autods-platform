"""Report download schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReportFormat = Literal["html", "pdf", "notebook", "executive_summary"]


class ReportRequest(BaseModel):
    project_id: str
    format: ReportFormat


class ReportJobResponse(BaseModel):
    job_id: str


class ReportResponse(BaseModel):
    report_id: str
    download_url: str
    format: ReportFormat
    generated_at: datetime
