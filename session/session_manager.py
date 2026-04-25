"""Session management -- save, resume, list, and delete analysis sessions.

Sessions are stored as JSON files in a configurable directory (default:
``~/.autods/sessions/``).  Each session captures the full AutoDSState so
that a pipeline run can be resumed or replayed later.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".autods" / "sessions"


def _sessions_dir(base_dir: str | Path | None = None) -> Path:
    d = Path(base_dir) if base_dir else _DEFAULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_path(session_id: str, base_dir: str | Path | None = None) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]{1,128}", session_id):
        raise ValueError(f"Invalid session_id: {session_id!r}")
    sessions_dir = _sessions_dir(base_dir)
    resolved = (sessions_dir / f"{session_id}.json").resolve()
    if not str(resolved).startswith(str(sessions_dir.resolve())):
        raise ValueError(f"session_id resolves outside sessions directory: {session_id!r}")
    return resolved


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_session(
    session_id: str,
    state: dict[str, Any],
    base_dir: str | Path | None = None,
) -> str:
    """Save a session state to disk.

    Args:
        session_id: Unique session identifier.
        state: Full AutoDSState dict (or subset).
        base_dir: Override session storage directory.

    Returns:
        Path to the saved session file.
    """
    path = _session_path(session_id, base_dir)

    envelope = {
        "session_id": session_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "state": _make_serializable(state),
    }

    path.write_text(json.dumps(envelope, indent=2, default=str), encoding="utf-8")
    logger.info("Session '%s' saved to %s", session_id, path)
    return str(path)


def load_session(
    session_id: str,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load a session from disk.

    Args:
        session_id: Session identifier.
        base_dir: Override session storage directory.

    Returns:
        The saved state dict.

    Raises:
        FileNotFoundError: If session file does not exist.
    """
    path = _session_path(session_id, base_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Session not found: {session_id}")

    envelope = json.loads(path.read_text(encoding="utf-8"))
    logger.info("Session '%s' loaded from %s", session_id, path)
    return envelope.get("state", {})


def list_sessions(base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """List all saved sessions with summary metadata.

    Returns:
        List of dicts with session_id, saved_at, domain, problem_type, status.
    """
    d = _sessions_dir(base_dir)
    sessions: list[dict[str, Any]] = []

    for f in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            envelope = json.loads(f.read_text(encoding="utf-8"))
            state = envelope.get("state", {})
            sessions.append({
                "session_id": envelope.get("session_id", f.stem),
                "saved_at": envelope.get("saved_at", ""),
                "domain": state.get("detected_domain", "unknown"),
                "problem_type": state.get("problem_type", ""),
                "workflow_status": state.get("workflow_status", ""),
                "completed_steps": state.get("completed_steps", []),
                "row_count": state.get("row_count", 0),
                "best_model": state.get("best_model_name", ""),
            })
        except Exception as exc:
            logger.warning("Failed to read session %s: %s", f.name, exc)

    return sessions


def delete_session(
    session_id: str,
    base_dir: str | Path | None = None,
) -> bool:
    """Delete a session file.

    Returns:
        True if deleted, False if not found.
    """
    path = _session_path(session_id, base_dir)
    if path.is_file():
        path.unlink()
        logger.info("Session '%s' deleted", session_id)
        return True
    return False


def session_exists(
    session_id: str,
    base_dir: str | Path | None = None,
) -> bool:
    """Check if a session file exists."""
    return _session_path(session_id, base_dir).is_file()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_serializable(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable objects to strings."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    # pandas / numpy fallbacks
    try:
        import numpy as np

        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    try:
        import pandas as pd

        if isinstance(obj, pd.DataFrame):
            return {"__type__": "DataFrame", "data": obj.to_dict(orient="list")}
        if isinstance(obj, pd.Series):
            return {"__type__": "Series", "data": obj.to_list()}
    except ImportError:
        pass

    return str(obj)
