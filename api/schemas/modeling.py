"""Model training and evaluation schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelingConfig(BaseModel):
    algorithms: list[str]
    cv_folds: int = Field(default=5, ge=2, le=20)
    search_strategy: str = "auto"  # auto | grid | random | bayesian
    primary_metric: str
    time_budget_seconds: int = Field(default=300, ge=30)
    custom_instructions: Optional[str] = None


class TrainRequest(BaseModel):
    project_id: str
    config: ModelingConfig


class ModelEntry(BaseModel):
    model_name: str
    metrics: dict[str, float]
    train_time: float
    rank: int
    mlflow_run_id: Optional[str] = None


class Leaderboard(BaseModel):
    project_id: str
    entries: list[ModelEntry]
    best_model: str


class SelectBestRequest(BaseModel):
    project_id: str
    model_name: str
