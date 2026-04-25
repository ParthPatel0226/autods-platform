"""Pydantic schemas for the prediction API.

Provides request/response models for single and batch predictions.
Feature schemas are dynamically validated against model metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    """Single prediction request."""

    features: dict[str, Any] = Field(
        ...,
        description="Feature name -> value mapping for one sample.",
    )
    include_shap: bool = Field(
        default=False,
        description="Whether to return SHAP explanations for this prediction.",
    )


class BatchPredictionRequest(BaseModel):
    """Batch prediction request (multiple samples)."""

    samples: list[dict[str, Any]] = Field(
        ...,
        description="List of feature dicts, one per sample.",
        min_length=1,
        max_length=10_000,
    )
    include_shap: bool = Field(
        default=False,
        description="Whether to return SHAP explanations per sample.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PredictionResult(BaseModel):
    """Single prediction result."""

    prediction: Any = Field(..., description="Predicted value or class.")
    confidence: float | None = Field(
        default=None,
        description="Prediction confidence (probability of predicted class).",
    )
    probabilities: dict[str, float] | None = Field(
        default=None,
        description="Per-class probabilities (classification only).",
    )
    shap_values: dict[str, float] | None = Field(
        default=None,
        description="SHAP values per feature (if requested).",
    )


class PredictionResponse(BaseModel):
    """Single prediction response."""

    success: bool = True
    result: PredictionResult


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""

    success: bool = True
    results: list[PredictionResult]
    count: int = Field(..., description="Number of predictions returned.")


class ModelInfoResponse(BaseModel):
    """Model metadata response."""

    algorithm: str
    problem_type: str
    trained_at: str
    features: int
    domain: str
    feature_names: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    model_loaded: bool


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str
    detail: str | None = None
