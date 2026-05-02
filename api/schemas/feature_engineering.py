"""Feature engineering schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FESuggestion(BaseModel):
    column: str
    decisions: dict[str, Any]
    recommendation_reason: str


class FESuggestResponse(BaseModel):
    suggestions: list[FESuggestion]


class FEApplyRequest(BaseModel):
    project_id: str
    decisions: dict[str, dict[str, Any]]


class FEResults(BaseModel):
    project_id: str
    final_features: list[str]
    dropped: list[str]
    transformations: dict[str, Any]
