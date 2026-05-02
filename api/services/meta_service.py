"""Meta service — exposes platform metadata for Expert mode and ops dashboards.

Exposes six callables consumed by the meta router:
  - list_tools        Enumerate registered tools with optional category/domain filter
  - get_tool          Return full metadata for a single tool by its registry key
  - get_pipeline_log  Return paginated pipeline log entries from state
  - get_cost_summary  Return API call / token / cost summary for a project
  - get_domain_configs  Return all domain configurations from YAML
  - get_agent_prompts   Return all agent prompts from YAML

Data sources
------------
``list_tools`` / ``get_tool``
    Read directly from ``agents.tools.tool_registry.TOOL_REGISTRY`` — the
    authoritative Python dict (not the YAML copy).

``get_pipeline_log``
    Reads ``state["pipeline_log"]`` via ``state_service.load_state``.
    Supports cursor-style pagination via ``limit`` and ``offset``.

``get_cost_summary``
    Composes from ``state["api_call_count"]``, ``state["api_token_count"]``,
    and a scan of ``state["pipeline_log"]`` for entries with ``tokens`` or
    ``cost`` fields.  No per-project ``CostTracker`` instance exists; this
    service derives what it can from available state.

``get_domain_configs`` / ``get_agent_prompts``
    Call ``configs.loader.load_domain_configs`` and
    ``configs.loader.load_agent_prompts`` respectively (both are cached
    ``@lru_cache`` functions — safe to call freely).
"""
from __future__ import annotations

import logging
from typing import Optional

from agents.tools.tool_registry import TOOL_REGISTRY
from configs.loader import load_agent_prompts, load_domain_configs
from api.services import state_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_tools(
    category: Optional[str] = None,
    domain: Optional[str] = None,
) -> list[dict]:
    """Return all registered tools, optionally filtered by category or domain.

    Each entry in the returned list contains at minimum:
    ``category``, ``tool_id``, ``name``, ``description``, ``domains``.
    Additional keys (``when_to_use``, ``parameters``, ``output``, ``type``,
    ``function``) are included when present in the registry entry.

    Args:
        category: Optional registry category key, e.g.
            ``"statistical_tests"``, ``"visualizations"``,
            ``"feature_engineering"``, ``"models"``.  If omitted all
            categories are returned.
        domain:   Optional domain name, e.g. ``"healthcare"``.  Tools
            whose ``domains`` list contains ``"all"`` are always included.

    Returns:
        Flat list of tool dicts sorted by ``category`` then ``tool_id``.

    Raises:
        AutoDSError: If *category* is not a valid registry category.
    """
    if category is not None and category not in TOOL_REGISTRY:
        available = sorted(TOOL_REGISTRY.keys())
        raise AutoDSError(
            f"Unknown category '{category}'. "
            f"Valid categories: {available}"
        )

    categories = [category] if category else sorted(TOOL_REGISTRY.keys())

    tools: list[dict] = []
    for cat in categories:
        for tool_id, info in TOOL_REGISTRY[cat].items():
            # Domain filter — a tool is included if its domains list
            # contains "all" or the requested domain.
            if domain is not None:
                tool_domains: list = info.get("domains") or []
                if "all" not in tool_domains and domain not in tool_domains:
                    continue

            tools.append({
                "category": cat,
                "tool_id": tool_id,
                **info,
            })

    return tools


def get_tool(tool_name: str) -> dict:
    """Return full metadata for a single tool by its registry key.

    Searches every category in ``TOOL_REGISTRY`` for ``tool_name`` as a
    ``tool_id``.

    Args:
        tool_name: Registry key, e.g. ``"t_test_independent"``.

    Returns:
        Dict containing ``category``, ``tool_id``, and all registry fields.

    Raises:
        AutoDSError: If *tool_name* is not found in any category.
    """
    for cat, tools in TOOL_REGISTRY.items():
        if tool_name in tools:
            return {
                "category": cat,
                "tool_id": tool_name,
                **tools[tool_name],
            }

    raise AutoDSError(
        f"Tool '{tool_name}' not found in registry. "
        f"Use list_tools() to see all registered tools."
    )


def get_pipeline_log(
    project_id: str,
    user_id: str,
    limit: int = 200,
    offset: int = 0,
) -> dict:
    """Return paginated pipeline log entries for a project.

    Args:
        project_id: Session / project identifier.
        user_id:    Requesting user's ID (ownership check).
        limit:      Maximum number of entries to return (default 200).
        offset:     Number of entries to skip from the start (default 0).

    Returns:
        Dict with keys::

            {
                "total":   int,        # Total entries in the log
                "offset":  int,        # Echo of the requested offset
                "limit":   int,        # Echo of the requested limit
                "entries": list[dict], # Paginated log entries (newest first)
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    log: list[dict] = list(state.get("pipeline_log") or [])
    # Return in reverse-chronological order (newest first).
    log_reversed = list(reversed(log))

    total = len(log_reversed)
    page = log_reversed[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": page,
    }


def get_cost_summary(project_id: str, user_id: str) -> dict:
    """Return API call / token / cost summary for a project.

    Reads ``state["api_call_count"]`` and ``state["api_token_count"]`` for
    headline numbers.  Also scans ``state["pipeline_log"]`` for entries
    that carry per-step ``tokens`` or ``cost`` breakdown fields (written by
    agents that call ``_log_cost`` internally).

    Because ``CostTracker`` is instantiated per-run (not per-project), this
    service composes the summary from available state keys rather than
    instantiating a tracker.

    Args:
        project_id: Session / project identifier.
        user_id:    Requesting user's ID (ownership check).

    Returns:
        Dict with keys::

            {
                "api_call_count":   int,
                "api_token_count":  int,
                "step_breakdown":   list[dict],  # per-step token/cost entries
                "current_step":     str | None,
                "completed_steps":  list[str],
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    log: list[dict] = list(state.get("pipeline_log") or [])

    # Collect log entries that have token or cost information.
    step_breakdown: list[dict] = [
        entry for entry in log
        if "tokens" in entry or "cost" in entry or "token_count" in entry
    ]

    return {
        "api_call_count": int(state.get("api_call_count") or 0),
        "api_token_count": int(state.get("api_token_count") or 0),
        "step_breakdown": step_breakdown,
        "current_step": state.get("current_step"),
        "completed_steps": list(state.get("completed_steps") or []),
    }


def get_domain_configs() -> list[dict]:
    """Return all domain configurations from ``configs/domain_configs.yaml``.

    Does not require ``project_id`` — this is global platform configuration,
    not per-project data.

    Returns:
        List of domain config dicts, each containing at minimum a
        ``domain_name`` key (inferred from the YAML mapping key when absent).
        Empty list if the YAML file is missing or unparseable.
    """
    raw: dict = load_domain_configs()

    configs: list[dict] = []
    for domain_key, config in raw.items():
        if not isinstance(config, dict):
            continue
        entry = dict(config)
        # Ensure domain_name is present even if the YAML omits it.
        if "domain_name" not in entry:
            entry["domain_name"] = domain_key
        configs.append(entry)

    return configs


def get_agent_prompts() -> dict:
    """Return all agent prompts from ``configs/agent_prompts.yaml``.

    Does not require ``project_id`` — this is global platform configuration.

    Returns:
        Dict mapping agent name → prompt config dict (``role``,
        ``instructions``, ``output_format``).  Empty dict if the YAML
        file is missing or unparseable.
    """
    return dict(load_agent_prompts())
