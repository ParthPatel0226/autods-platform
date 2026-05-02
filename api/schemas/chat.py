"""Conversational follow-up schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    timestamp: datetime


class ChatSendRequest(BaseModel):
    project_id: str
    message: str


class SuggestedAction(BaseModel):
    label: str
    action: str
    params: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    suggested_actions: list[SuggestedAction] = []
    references: list[str] = []


class ChatHistory(BaseModel):
    project_id: str
    messages: list[ChatMessage]
