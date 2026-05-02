"""Pipeline audit and cost tracking schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class PipelineLogEntry(BaseModel):
    timestamp: str
    step: str
    tool: str
    params: dict[str, Any]
    duration_seconds: float
    status: str  # success | error
    error: Optional[str] = None


class PipelineLogResponse(BaseModel):
    project_id: str
    entries: list[PipelineLogEntry]
    total: int


class CostSummary(BaseModel):
    project_id: str
    total_tokens: int
    total_cost_usd: float
    by_step: dict[str, float]
    by_provider: dict[str, float]
