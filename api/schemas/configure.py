"""Project configuration and domain detection schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DomainAlternative(BaseModel):
    domain: str
    confidence: float
    reason: str = ""


class DomainDetectionResponse(BaseModel):
    detected_domain: str
    confidence: float
    evidence: list[str]
    alternatives: list[DomainAlternative]
    project_id: str = ""


class ConfigureRequest(BaseModel):
    project_id: str
    domain: str
    target_column: Optional[str] = None
    problem_type: str
    user_mode: str = "auto"
    user_goal: str


class StartPipelineResponse(BaseModel):
    job_id: str
    current_step: str = "eda"
    message: str = ""
