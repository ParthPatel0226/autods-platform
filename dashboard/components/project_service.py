"""Project model + CRUD backed by session/session_manager.py (JSON file store).

Session manager API (verified):
    save_session(session_id: str, state: dict) -> str
    load_session(session_id: str) -> dict            # returns state dict
    list_sessions() -> list[dict]                   # summary dicts only
    delete_session(session_id: str) -> bool
    session_exists(session_id: str) -> bool
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

_STEP_KEYS: list[str] = [
    "upload",
    "configure",
    "eda",
    "feature_engineering",
    "modeling",
    "explainability",
    "predict",
]


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    user_id: str = "local"
    detected_domain: str = ""
    confirmed_domain: str = ""
    problem_type: str = ""
    target_column: str = ""
    analysis_mode: str = "guided"
    status: str = "draft"
    step_status: dict[str, str] = field(
        default_factory=lambda: {k: "pending" for k in _STEP_KEYS}
    )
    dataset_name: str = ""
    dataset_path: str = ""
    n_rows: int = 0
    n_cols: int = 0
    metric_summary: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    excluded_columns: list[str] = field(default_factory=list)
    goal: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Project":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_meta(state: dict[str, Any]) -> dict[str, Any] | None:
    """Pull project_meta out of a loaded session state dict."""
    raw = state.get("project_meta")
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
    if isinstance(raw, dict):
        return raw
    return None


def _persist(p: Project) -> None:
    """Persist project to JSON file store via session_manager."""
    from session import session_manager  # lazy — avoids import-time path dependency

    p.updated_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "project_meta": json.dumps(p.to_dict()),
        "detected_domain": p.confirmed_domain or p.detected_domain,
        "problem_type": p.problem_type,
        "workflow_status": p.status,
        "completed_steps": [s for s, st in p.step_status.items() if st == "done"],
        "target_column": p.target_column,
        "analysis_mode": p.analysis_mode,
    }
    session_manager.save_session(p.id, payload)


# ---------------------------------------------------------------------------
# Public CRUD API
# ---------------------------------------------------------------------------


def create(name: str = "Untitled Project", user_id: str = "local") -> Project:
    """Create and persist a new project, return it."""
    p = Project(name=name, user_id=user_id)
    _persist(p)
    return p


def get(project_id: str) -> Project | None:
    """Load project by ID. Returns None if not found."""
    from session import session_manager

    if not session_manager.session_exists(project_id):
        return None
    try:
        state = session_manager.load_session(project_id)
    except FileNotFoundError:
        return None
    meta = _extract_meta(state)
    if meta is None:
        return None
    try:
        return Project.from_dict(meta)
    except (TypeError, KeyError):
        return None


def save(p: Project) -> None:
    """Persist changes to an existing project."""
    _persist(p)


def delete(project_id: str) -> bool:
    """Delete a project. Returns True if deleted."""
    from session import session_manager

    return session_manager.delete_session(project_id)


def list_all(user_id: str = "local") -> list[Project]:
    """Return all projects for a user, sorted newest first.

    list_sessions() summaries don't contain project_meta, so each session
    is fully loaded via load_session() to extract it.
    """
    from session import session_manager

    summaries = session_manager.list_sessions()
    projects: list[Project] = []
    for s in summaries:
        sid = s["session_id"]
        try:
            state = session_manager.load_session(sid)
        except Exception:
            continue
        meta = _extract_meta(state)
        if meta and meta.get("user_id", "local") == user_id:
            try:
                projects.append(Project.from_dict(meta))
            except (TypeError, KeyError):
                continue
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    return projects


def update(p: Project) -> None:
    """Alias for save(). Persist changes to an existing project."""
    _persist(p)


def get_active() -> "Project | None":
    """Return the active project from session state, or None."""
    import streamlit as st  # lazy

    pid = st.session_state.get("active_project_id")
    if not pid:
        return None
    return get(pid)


def set_active(project_id: str) -> None:
    """Set the active project ID in Streamlit session state."""
    import streamlit as st  # lazy

    st.session_state["active_project_id"] = project_id


def get_recent_files(user_id: str = "local", limit: int = 5) -> list[dict[str, Any]]:
    """Return recent file uploads for a user as list of dicts.

    Each dict has: dataset_name, dataset_path, project_name, project_id.
    Only projects with a dataset_path are included.
    """
    projects = list_all(user_id=user_id)
    result: list[dict[str, Any]] = []
    for p in projects:
        if p.dataset_path:
            result.append(
                {
                    "dataset_name": p.dataset_name or p.dataset_path,
                    "dataset_path": p.dataset_path,
                    "project_name": p.name,
                    "project_id": p.id,
                }
            )
        if len(result) >= limit:
            break
    return result


def clear_active() -> None:
    """Remove active project key from Streamlit session state (on logout)."""
    import streamlit as st  # lazy to stay import-clean

    st.session_state.pop("active_project_id", None)
