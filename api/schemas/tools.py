"""Tool registry schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class ToolEntry(BaseModel):
    name: str
    category: str
    description: str
    parameters: list[ToolParameter]
    domain_specific: bool = False
    domains: list[str] = []


class ToolListResponse(BaseModel):
    tools: list[ToolEntry]
    total: int
