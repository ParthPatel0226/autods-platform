"""Configure routes — domain detection, target setup, pipeline start.

Prefix : /configure
Tags   : configure

All routes require Bearer auth.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.configure import (
    ConfigureRequest,
    DomainDetectionResponse,
    DomainAlternative,
    StartPipelineResponse,
)
from api.schemas.projects import Project
from api.services import state_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_to_project(state: dict) -> Project:
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

@router.post(
    "/detect-domain",
    response_model=DomainDetectionResponse,
    summary="Auto-detect domain from uploaded data",
)
async def detect_domain(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> DomainDetectionResponse:
    """Run domain detection on the project's loaded data sources."""
    try:
        state = state_service.load_state(project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    # Build a minimal AutoDSState and run domain detection
    from core.state import AutoDSState
    from agents.domain_detector import run_domain_detection

    # Reconstruct columns from data_sources stored in state
    data_sources: list[dict] = state.get("data_sources") or []
    columns: list[dict] = []
    for src in data_sources:
        for col_name in (src.get("columns") or []):
            columns.append({"name": col_name})

    agent_state: AutoDSState = {  # type: ignore[assignment]
        **state,
        "session_id": project_id,
        "columns": columns,
    }

    try:
        updated = run_domain_detection(agent_state)
    except Exception as exc:
        logger.warning("Domain detection failed for %s: %s", project_id, exc)
        updated = agent_state
        updated["detected_domain"] = updated.get("detected_domain", "generic")
        updated["domain_detection_confidence"] = updated.get("domain_detection_confidence", 0.0)

    detected_domain: str = updated.get("detected_domain", "generic")
    confidence: float = float(updated.get("domain_detection_confidence", 0.0))
    domain_config: dict = updated.get("domain_config") or {}

    # Persist detected domain back to project state
    try:
        state_service.update_state(
            project_id,
            current_user["user_id"],
            detected_domain=detected_domain,
            domain_detection_confidence=confidence,
            domain_config=domain_config,
        )
    except AutoDSError:
        logger.warning("Failed to persist domain detection for %s", project_id)

    # Build alternatives list from domain_config if available
    alternatives: list[DomainAlternative] = []
    for alt in (domain_config.get("alternatives") or []):
        alternatives.append(
            DomainAlternative(
                domain=alt.get("domain", ""),
                confidence=float(alt.get("confidence", 0.0)),
                reason=alt.get("reason", ""),
            )
        )

    evidence: list[str] = domain_config.get("evidence") or []

    return DomainDetectionResponse(
        detected_domain=detected_domain,
        confidence=confidence,
        alternatives=alternatives,
        evidence=evidence,
        project_id=project_id,
    )


@router.post(
    "/set-target",
    response_model=Project,
    summary="Set target column, problem type, user mode, and goal",
)
async def set_target(
    body: ConfigureRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    """Apply domain, target, problem type, user mode, and goal to the project."""
    patches: dict = {}
    if body.domain is not None:
        patches["detected_domain"] = body.domain
    if body.target_column is not None:
        patches["target_column"] = body.target_column
    if body.problem_type is not None:
        patches["problem_type"] = body.problem_type
    if body.user_mode is not None:
        patches["user_mode"] = body.user_mode
    if body.user_goal is not None:
        patches["user_goal"] = body.user_goal

    try:
        if patches:
            state = state_service.update_state(body.project_id, current_user["user_id"], **patches)
        else:
            state = state_service.load_state(body.project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    return _state_to_project(state)


@router.post(
    "/start-pipeline",
    response_model=StartPipelineResponse,
    summary="Mark configuration complete and advance to first pipeline step",
)
async def start_pipeline(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> StartPipelineResponse:
    """Advance the project to the EDA step and set workflow_status=active."""
    import uuid

    job_id = str(uuid.uuid4())

    try:
        state_service.update_state(
            project_id,
            current_user["user_id"],
            workflow_status="active",
            current_step="eda",
        )
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    return StartPipelineResponse(
        job_id=job_id,
        current_step="eda",
        message="Pipeline started. Proceed to /eda/generate-questions.",
    )
