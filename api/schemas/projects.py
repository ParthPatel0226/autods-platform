"""Project (session) schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Project(BaseModel):
    project_id: str
    name: str
    user_mode: str = "auto"
    detected_domain: Optional[str] = None
    target_column: Optional[str] = None
    problem_type: Optional[str] = None
    current_step: Optional[str] = None
    completed_steps: list[str] = []
    created_at: datetime
    updated_at: datetime


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectListItem(BaseModel):
    """Lightweight summary for the sidebar / project-picker."""

    project_id: str
    name: str
    detected_domain: Optional[str] = None
    problem_type: Optional[str] = None
    current_step: Optional[str] = None
    workflow_status: Optional[str] = None
    row_count: int = 0
    best_model: Optional[str] = None
    saved_at: Optional[str] = None
