"""Chat routes — conversational follow-up.

Prefix : /chat
Tags   : chat
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.chat import ChatHistory, ChatMessage, ChatResponse, ChatSendRequest
from api.services import chat_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Send a follow-up message in the project conversation",
)
async def send_message(
    body: ChatSendRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ChatResponse:
    """Dispatch message to the follow-up agent and return the assistant reply."""
    try:
        result = chat_service.send_message(
            body.project_id, current_user["user_id"], body.message
        )
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {exc}",
        ) from exc

    return ChatResponse(
        reply=result.get("reply", ""),
        suggested_actions=result.get("suggested_actions") or [],
        references=result.get("references") or [],
    )


@router.get(
    "/history/{project_id}",
    response_model=ChatHistory,
    summary="Retrieve full chat history for a project",
)
async def get_history(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ChatHistory:
    """Return all chat messages exchanged in the project session."""
    try:
        result = chat_service.get_history(project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {exc}",
        ) from exc

    raw_messages: list[dict] = result if isinstance(result, list) else result.get("messages") or []
    messages = [
        ChatMessage(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m["timestamp"],
        )
        for m in raw_messages
        if "timestamp" in m
    ]
    return ChatHistory(project_id=project_id, messages=messages)


@router.delete(
    "/history/{project_id}",
    response_model=dict,
    summary="Clear chat history for a project",
)
async def clear_history(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Wipe all chat messages from the project session."""
    try:
        chat_service.clear_history(project_id, current_user["user_id"])
    except AutoDSError as exc:
        code = (
            status.HTTP_403_FORBIDDEN
            if "denied" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat history: {exc}",
        ) from exc

    return {"cleared": True}
