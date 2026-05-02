"""Project routes — CRUD for analysis sessions.

Prefix : /projects
Tags   : projects

All routes require Bearer auth and enforce ownership via state_service.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from api.dependencies import get_current_user
from api.schemas.projects import (
    CreateProjectRequest,
    Project,
    ProjectListItem,
    UpdateProjectRequest,
)
from api.services import state_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_to_project(state: dict) -> Project:
    """Map state dict → Project Pydantic model."""
    meta: dict = state.get("_meta") or {}
    return Project(
        project_id=state.get("session_id", ""),
        name=state.get("project_name", ""),
        user_mode=state.get("user_mode"),
        detected_domain=state.get("detected_domain"),
        target_column=state.get("target_column"),
        problem_type=state.get("problem_type"),
        current_step=state.get("current_step"),
        completed_steps=list(state.get("completed_steps") or []),
        created_at=state.get("created_at"),
        updated_at=meta.get("saved_at"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    """Create a new project (analysis session)."""
    try:
        state = state_service.create_state(current_user["user_id"], body.name)
    except AutoDSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _state_to_project(state)


@router.get("/", response_model=list[ProjectListItem])
async def list_projects(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[ProjectListItem]:
    """List all projects owned by the current user."""
    items = state_service.list_projects(current_user["user_id"])
    return [
        ProjectListItem(
            project_id=item["project_id"],
            name=item.get("project_name", ""),
            detected_domain=item.get("domain"),
            problem_type=item.get("problem_type"),
            current_step=item.get("current_step"),
            workflow_status=item.get("workflow_status"),
            row_count=item.get("row_count"),
            best_model=item.get("best_model"),
            saved_at=item.get("saved_at"),
        )
        for item in items
    ]


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    """Return full state for a project."""
    try:
        state = state_service.load_state(project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _state_to_project(state)


@router.patch("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    """Patch project metadata (name, description)."""
    patches: dict[str, Any] = {}
    if body.name is not None:
        patches["project_name"] = body.name
    if body.description is not None:
        patches["project_description"] = body.description

    if not patches:
        # Nothing to update — just return current state.
        try:
            state = state_service.load_state(project_id, current_user["user_id"])
        except AutoDSError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return _state_to_project(state)

    try:
        state = state_service.update_state(project_id, current_user["user_id"], **patches)
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _state_to_project(state)


@router.delete("/{project_id}", response_class=Response)
async def delete_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    """Permanently delete a project and all its state."""
    try:
        state_service.delete_project(project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/activate", response_model=dict)
async def activate_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Mark a project as the active session (sets workflow_status=active)."""
    try:
        state_service.update_state(
            project_id, current_user["user_id"], workflow_status="active"
        )
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return {"activated": True, "project_id": project_id}
