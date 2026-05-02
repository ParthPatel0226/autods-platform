"""Explainability and fairness schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SHAPRequest(BaseModel):
    project_id: str
    sample_size: int = Field(default=100, ge=1, le=10000)


class SHAPResponse(BaseModel):
    global_importance: dict[str, float]
    local_examples: list[dict[str, Any]]
    interactions: Optional[dict[str, Any]] = None


class WhatIfRequest(BaseModel):
    project_id: str
    base_row: dict[str, Any]
    modifications: dict[str, Any]


class WhatIfResponse(BaseModel):
    original_prediction: Any
    new_prediction: Any
    delta: Optional[float] = None
    feature_contributions: dict[str, float]


class FairnessRequest(BaseModel):
    project_id: str
    protected_attributes: list[str]


class FairnessReport(BaseModel):
    project_id: str
    metrics: dict[str, Any]
    disparities: dict[str, Any]
    recommendations: list[str]


class ModelCardResponse(BaseModel):
    project_id: str
    model_card: dict[str, Any]
