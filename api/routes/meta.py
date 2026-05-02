"""Meta routes — tool registry, pipeline log, cost, domain configs, agent prompts.

Prefix : /meta
Tags   : meta
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user
from api.schemas.configs import AgentPromptsResponse, DomainConfigList
from api.schemas.meta import CostSummary, PipelineLogResponse
from api.services import meta_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/tools",
    response_model=None,
    summary="List registered tools",
)
async def list_tools(
    current_user: Annotated[dict, Depends(get_current_user)],
    category: Optional[str] = Query(None, description="Filter by registry category"),
    domain: Optional[str] = Query(None, description="Filter by domain name"),
) -> dict:
    """Return all registered tools with optional category/domain filter."""
    try:
        tools = meta_service.list_tools(category=category, domain=domain)
    except AutoDSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {exc}",
        ) from exc

    return {"tools": tools, "total": len(tools)}


@router.get(
    "/tools/{tool_name}",
    response_model=None,
    summary="Get a single tool entry by registry key",
)
async def get_tool(
    tool_name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Return full metadata for a tool by its registry key."""
    try:
        tool = meta_service.get_tool(tool_name)
    except AutoDSError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tool: {exc}",
        ) from exc

    return tool


@router.get(
    "/pipeline-log/{project_id}",
    response_model=PipelineLogResponse,
    summary="Get paginated pipeline log for a project",
)
async def get_pipeline_log(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(200, ge=1, le=1000, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
) -> PipelineLogResponse:
    """Return paginated pipeline log entries for a project (newest first)."""
    try:
        result = meta_service.get_pipeline_log(
            project_id, current_user["user_id"], limit=limit, offset=offset
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
            detail=f"Failed to retrieve pipeline log: {exc}",
        ) from exc

    return PipelineLogResponse(**result)


@router.get(
    "/costs/{project_id}",
    response_model=CostSummary,
    summary="Get API cost summary for a project",
)
async def get_cost_summary(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CostSummary:
    """Return API call count, token count, and per-step cost breakdown."""
    try:
        result = meta_service.get_cost_summary(project_id, current_user["user_id"])
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
            detail=f"Failed to retrieve cost summary: {exc}",
        ) from exc

    return CostSummary(**result)


@router.get(
    "/domains",
    response_model=DomainConfigList,
    summary="List all domain configurations",
)
async def get_domain_configs(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> DomainConfigList:
    """Return all domain configurations from domain_configs.yaml."""
    try:
        raw_configs = meta_service.get_domain_configs()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve domain configs: {exc}",
        ) from exc

    from api.schemas.configs import DomainConfig
    domains = []
    for cfg in raw_configs:
        try:
            domains.append(DomainConfig(**cfg))
        except Exception:
            # Partial configs — keep only the domain_name at minimum
            domains.append(DomainConfig(
                domain_name=cfg.get("domain_name", "unknown"),
                display_name=cfg.get("display_name", cfg.get("domain_name", "unknown")),
            ))

    return DomainConfigList(domains=domains)


@router.get(
    "/agent-prompts",
    response_model=AgentPromptsResponse,
    summary="Get all agent prompts (admin)",
)
async def get_agent_prompts(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AgentPromptsResponse:
    """Return all agent prompts from agent_prompts.yaml.

    Admin-only in production. Currently accepts any authenticated user.
    TODO: add role/email check once a roles system is in place.
    """
    try:
        prompts = meta_service.get_agent_prompts()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent prompts: {exc}",
        ) from exc

    return AgentPromptsResponse(prompts=prompts)
