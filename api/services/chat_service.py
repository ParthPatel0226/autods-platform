"""Chat service — wraps agents/followup_agent.py for the FastAPI layer.

Exposes three callables consumed by the chat router:
  - send_message   Dispatch a user message to the follow-up agent; store
                   both sides of the exchange in state["chat_history"]
  - get_history    Return the full chat history for a project
  - clear_history  Wipe chat_history from state

Chat history format
-------------------
Each entry in state["chat_history"] is::

    {
        "role":      "user" | "assistant",
        "content":   str,
        "timestamp": ISO-8601 str,
        "action_taken": str | None,   # filled for assistant turns only
        "charts":    list[dict],       # filled for assistant turns only
        "data":      Any,              # filled for assistant turns only
    }

Defensive fallback
------------------
If ``handle_followup`` returns ``action_taken == "default_help"`` or raises,
the service stores the original user message in history and returns a generic
help response.  This mirrors how the Streamlit 08_chat.py page handles
unrecognised input: always persist the exchange, never surface a raw
exception to the caller.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.followup_agent import handle_followup, _CAPABILITIES_SUMMARY
from api.services import state_service
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

# Sentinel returned by the agent for unrecognised intent.
_FALLBACK_ACTION = "default_help"

_GENERIC_FALLBACK = (
    "I couldn't determine what you were asking.\n\n" + _CAPABILITIES_SUMMARY
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_turn(
    history: list[dict],
    role: str,
    content: str,
    *,
    action_taken: str | None = None,
    charts: list[dict] | None = None,
    data: object = None,
) -> None:
    """Append a turn to the in-memory history list (mutates in place)."""
    entry: dict = {
        "role": role,
        "content": content,
        "timestamp": _now_iso(),
    }
    if role == "assistant":
        entry["action_taken"] = action_taken
        entry["charts"] = charts or []
        entry["data"] = data
    history.append(entry)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_message(project_id: str, user_id: str, message: str) -> dict:
    """Dispatch *message* to the follow-up agent and persist both turns.

    The user message is always recorded in chat history before calling the
    agent, so even if the agent fails the exchange is captured.  If the
    agent raises or returns ``action_taken == "default_help"`` the service
    returns a generic capabilities summary instead of propagating the error.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        message: Raw user message string.

    Returns:
        Dict with keys::

            {
                "response":     str,        # Markdown-formatted reply
                "action_taken": str,        # Intent / action identifier
                "charts":       list[dict], # Chart specs (may be empty)
                "data":         Any,        # Raw result data (may be None)
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    history: list[dict] = list(state.get("chat_history") or [])

    # Always record user turn first so it survives a partial failure.
    _append_turn(history, "user", message)

    # ------------------------------------------------------------------ #
    # Dispatch to follow-up agent (defensive)
    # ------------------------------------------------------------------ #
    agent_result: dict = {}
    try:
        agent_result = handle_followup(state, message)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "handle_followup raised for project=%s message=%r: %s",
            project_id,
            message[:80],
            exc,
        )
        agent_result = {
            "response": _GENERIC_FALLBACK,
            "charts": [],
            "data": None,
            "action_taken": "error_fallback",
        }

    response: str = agent_result.get("response") or _GENERIC_FALLBACK
    action_taken: str = agent_result.get("action_taken") or _FALLBACK_ACTION
    charts: list[dict] = agent_result.get("charts") or []
    data = agent_result.get("data")

    # Downgrade unrecognised-intent to generic message (already in response).
    if action_taken == _FALLBACK_ACTION and not response.strip():
        response = _GENERIC_FALLBACK

    _append_turn(
        history,
        "assistant",
        response,
        action_taken=action_taken,
        charts=charts,
        data=data,
    )

    # Persist updated history.
    state_service.update_state(project_id, user_id, chat_history=history)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": _now_iso(),
        "step": "chat",
        "action": "send_message",
        "action_taken": action_taken,
        "message_preview": message[:80],
    })

    return {
        "response": response,
        "action_taken": action_taken,
        "charts": charts,
        "data": data,
    }


def get_history(project_id: str, user_id: str) -> list[dict]:
    """Return the full chat history for a project.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        List of turn dicts (may be empty if no messages yet).

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)
    return list(state.get("chat_history") or [])


def clear_history(project_id: str, user_id: str) -> None:
    """Wipe chat history from state.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state_service.update_state(project_id, user_id, chat_history=[])
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": _now_iso(),
        "step": "chat",
        "action": "clear_history",
    })
