"""State service — single source of truth for AutoDSState I/O.

Wraps ``session/session_manager.py``.  All state mutations in the API layer
must go through this module; no service or router touches session_manager
directly.

User ownership
--------------
``session_manager`` has no concept of ``user_id``.  Ownership is stored
inside the state envelope at ``state["_meta"]["user_id"]``.  Every write
stamps this field; every read verifies it.

Concurrency
-----------
``session_manager.save_session`` calls ``path.write_text`` directly with no
locking, so concurrent writes to the same project would produce torn files.
A module-level ``threading.Lock`` serialises all saves in a single process.
(For multi-process deployments, upgrade to a file-lock or DB-backed store.)

Exception stand-ins
-------------------
``core/exceptions.py`` is a frozen backend module — the api/ layer never
modifies it.  ``ResourceNotFoundError`` and ``AuthorizationError`` do not
exist there, so this module raises plain ``AutoDSError`` with descriptive
messages instead.  ``api/main.py`` inspects the message text to assign the
correct HTTP status code (404 for "not found", 403 for "Access denied").

TODO: when core/exceptions.py gains ResourceNotFoundError and
      AuthorizationError, replace the AutoDSError raises below with the
      specific subclasses and remove the message-based routing in main.py.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from core.exceptions import AutoDSError
from session.session_manager import (
    delete_session,
    list_sessions,
    load_session,
    save_session,
    session_exists,
)

_SAVE_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stamp_meta(state: dict, user_id: str) -> dict:
    """Return *state* with ``_meta.user_id`` set (does not mutate in-place)."""
    meta = dict(state.get("_meta") or {})
    meta["user_id"] = user_id
    return {**state, "_meta": meta}


def _check_ownership(state: dict, project_id: str, user_id: str) -> None:
    """Raise if the stored owner doesn't match *user_id*."""
    owner = (state.get("_meta") or {}).get("user_id")
    if owner != user_id:
        raise AutoDSError(
            f"Access denied to project '{project_id}'."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_state(user_id: str, project_name: str) -> dict:
    """Create a new AutoDSState, persist it, and return it.

    Args:
        user_id: ID of the user creating the project.
        project_name: Human-readable project name stored in ``session_id``.

    Returns:
        Dict with at minimum ``project_id`` (the session_id used for storage)
        and the full initial state.
    """
    project_id = str(uuid.uuid4())
    initial_state: dict[str, Any] = {
        "session_id": project_id,
        "project_name": project_name,
        "workflow_status": "created",
        "completed_steps": [],
        "pipeline_log": [],
        "errors": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state = _stamp_meta(initial_state, user_id)
    with _SAVE_LOCK:
        save_session(project_id, state)
    return state


def load_state(project_id: str, user_id: str) -> dict:
    """Load and return a project's AutoDSState.

    Args:
        project_id: The session_id / project identifier.
        user_id: ID of the requesting user.

    Returns:
        The stored AutoDSState dict.

    Raises:
        AutoDSError: If no session file exists for *project_id*
            (message contains "not found").
        AutoDSError: If the stored owner differs from *user_id*
            (message contains "Access denied").
    """
    if not session_exists(project_id):
        raise AutoDSError(f"Project '{project_id}' not found.")
    try:
        state = load_session(project_id)
    except FileNotFoundError:
        raise AutoDSError(f"Project '{project_id}' not found.")
    _check_ownership(state, project_id, user_id)
    return state


def save_state(project_id: str, state: dict, user_id: str) -> None:
    """Persist *state* for an existing project.

    Stamps ``_meta.user_id`` before writing so ownership is preserved even
    if the caller stripped the ``_meta`` key.

    Args:
        project_id: The session_id / project identifier.
        state: Full AutoDSState dict to persist.
        user_id: Owner's user ID — will be written into ``state["_meta"]``.
    """
    stamped = _stamp_meta(state, user_id)
    with _SAVE_LOCK:
        save_session(project_id, stamped)


def update_state(project_id: str, user_id: str, **patches: Any) -> dict:
    """Load, deep-merge *patches*, save, and return the updated state.

    Nested dict values (e.g. ``eda_results``, ``fe_choices``) are merged at
    the top level: ``existing[key].update(patches[key])`` for dict values,
    replace otherwise.

    Args:
        project_id: The session_id / project identifier.
        user_id: Owner's user ID.
        **patches: Key/value pairs to merge into the stored state.

    Returns:
        The updated AutoDSState dict.

    Raises:
        AutoDSError: If the project doesn't exist or caller doesn't own it.
    """
    state = load_state(project_id, user_id)
    for key, value in patches.items():
        if isinstance(value, dict) and isinstance(state.get(key), dict):
            merged = dict(state[key])
            merged.update(value)
            state[key] = merged
        else:
            state[key] = value
    save_state(project_id, state, user_id)
    return state


def list_projects(user_id: str) -> list[dict]:
    """Return summary metadata for all projects owned by *user_id*.

    Suitable for sidebar / project-picker display.  Each item contains:
    ``project_id``, ``project_name``, ``saved_at``, ``domain``,
    ``problem_type``, ``workflow_status``, ``row_count``, ``best_model``.

    Args:
        user_id: Owner's user ID.

    Returns:
        List of project metadata dicts, most-recently-saved first.
    """
    all_sessions = list_sessions()
    result: list[dict] = []
    for meta in all_sessions:
        sid = meta.get("session_id", "")
        if not sid:
            continue
        try:
            state = load_session(sid)
        except (FileNotFoundError, Exception):
            continue
        owner = (state.get("_meta") or {}).get("user_id")
        if owner != user_id:
            continue
        result.append({
            "project_id": sid,
            "project_name": state.get("project_name", sid),
            "saved_at": meta.get("saved_at", ""),
            "domain": meta.get("domain", "unknown"),
            "problem_type": meta.get("problem_type", ""),
            "workflow_status": meta.get("workflow_status", ""),
            "row_count": meta.get("row_count", 0),
            "best_model": meta.get("best_model", ""),
        })
    return result


def delete_project(project_id: str, user_id: str) -> None:
    """Delete a project after verifying ownership.

    Args:
        project_id: The session_id / project identifier.
        user_id: Owner's user ID.

    Raises:
        AutoDSError: If the project doesn't exist or caller doesn't own it.
    """
    # load_state already performs both checks
    load_state(project_id, user_id)
    delete_session(project_id)


def append_to_pipeline_log(project_id: str, entry: dict) -> None:
    """Append *entry* to ``state["pipeline_log"]`` and save.

    Convenience wrapper; does not require *user_id* because the pipeline
    itself is the caller and ownership is already established.  The lock
    inside ``save_state`` prevents concurrent-write races.

    Note: loads the raw state directly (bypassing the ownership check) so
    that internal pipeline steps don't need to pass a user_id.  Only use
    this from trusted internal callers.

    Args:
        project_id: The session_id / project identifier.
        entry: Log entry dict to append.
    """
    if not session_exists(project_id):
        raise AutoDSError(f"Project '{project_id}' not found.")
    try:
        state = load_session(project_id)
    except FileNotFoundError:
        raise AutoDSError(f"Project '{project_id}' not found.")

    log = list(state.get("pipeline_log") or [])
    log.append(entry)
    state["pipeline_log"] = log

    with _SAVE_LOCK:
        save_session(project_id, state)
