"""Data upload and connector schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DataSource(BaseModel):
    model_config = {"protected_namespaces": ()}

    source_id: str
    name: str
    format: str
    n_rows: int
    n_cols: int
    columns: list[str]
    schema: dict[str, Any]
    uploaded_at: datetime


class UploadFileResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    source_id: str
    preview: list[dict[str, Any]]
    schema: dict[str, Any]
    n_rows: int
    n_cols: int
    detected_format: str


class SampleDatasetInfo(BaseModel):
    name: str
    display_name: str
    domain: str
    n_rows: int
    n_cols: int
    description: str


class SampleDatasetRequest(BaseModel):
    dataset_name: str


class ConnectorUploadRequest(BaseModel):
    connector_type: str
    config: dict[str, Any]


class JoinKey(BaseModel):
    left_column: str
    right_column: str


class JoinPlan(BaseModel):
    left_source_id: str
    right_source_id: str
    join_keys: list[JoinKey]
    join_type: Literal["inner", "left", "right", "outer"] = "inner"


class SuggestJoinResponse(BaseModel):
    plan: JoinPlan
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ApplyJoinResponse(BaseModel):
    joined_source_id: str
    n_rows: int
    n_cols: int
    columns: list[str]
