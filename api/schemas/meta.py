"""Meta endpoint schemas — pipeline log, cost summary."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class PipelineLogResponse(BaseModel):
    total: int
    offset: int
    limit: int
    entries: list[dict[str, Any]]


class CostSummary(BaseModel):
    api_call_count: int
    api_token_count: int
    step_breakdown: list[dict[str, Any]]
    current_step: Optional[str] = None
    completed_steps: list[str] = []
