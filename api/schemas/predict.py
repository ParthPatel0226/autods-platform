"""Prediction request/response schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class PredictRequest(BaseModel):
    project_id: str
    features: dict[str, Any]


class ConfidenceInterval(BaseModel):
    lower: float
    upper: float


class PredictResponse(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    shap: Optional[dict[str, float]] = None


class BatchPredictRequest(BaseModel):
    project_id: str
    file_id: str


class BatchPredictResponse(BaseModel):
    job_id: str
    n_rows: int
