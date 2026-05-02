"""Exploratory Data Analysis schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class EDAQuestionOption(BaseModel):
    value: str
    label: str
    recommended: bool = False


class EDAQuestion(BaseModel):
    id: str
    step: str = "eda"
    question: str
    type: str  # single_select | multi_select | slider | per_column_table | text_input | number_input
    options: list[EDAQuestionOption] = []
    recommendation_reason: Optional[str] = None
    domain_specific: bool = False


class EDAAnswerRequest(BaseModel):
    project_id: str
    answers: dict[str, Any]


class EDARunRequest(BaseModel):
    project_id: str


class EDAResults(BaseModel):
    project_id: str
    charts: dict[str, Any]
    insights: list[str]
    statistical_tests: dict[str, Any]
    summary: str
