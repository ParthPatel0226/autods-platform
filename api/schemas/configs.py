"""Domain config and agent prompt schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class DomainConfig(BaseModel):
    domain_name: str
    display_name: str
    icon: Optional[str] = None
    primary_metrics: dict[str, list[str]] = {}
    eda_questions: list[dict[str, Any]] = []
    feature_questions: list[dict[str, Any]] = []
    model_questions: list[dict[str, Any]] = []
    fairness: Optional[dict[str, Any]] = None
    compliance_notes: list[str] = []
    report_style: Optional[str] = None


class DomainConfigList(BaseModel):
    domains: list[DomainConfig]


class AgentPromptsResponse(BaseModel):
    """Contents of configs/agent_prompts.yaml keyed by agent name."""

    prompts: dict[str, dict[str, Any]]
