# Spec 01 — Project Model & `project_service.py`

## Concept

A **project** = one analysis run. It bundles:
- Identity: `id`, `name`, `created_at`, `updated_at`
- Domain: `detected_domain`, `confirmed_domain`
- Mode: `analysis_mode` (auto/guided/expert)
- Dataset: `dataset_path`, `dataset_name`, `n_rows`, `n_cols`
- Target: `target_column`, `problem_type`
- Pipeline state: `step_status` dict — which steps are `done`/`active`/`pending`
- Outputs: paths to EDA results, models, reports
- Owner: `user_id` (mock for now)

## Mapping to existing backend

The existing `session/session_manager.py` already has SQLite-backed save/load/list/delete. **Reuse it.** A "project" is a thin layer on top of a session record:

- `project.id` → session's UUID
- Project metadata (name, status, domain, etc.) → either new columns or a JSON blob stored in an existing `meta` column. Check `session/session_manager.py` for the actual column structure; if there's an unused JSON/text column, use it. If not, add one column called `project_meta` (TEXT, JSON-encoded).

**Do not break existing session functionality.** Test that `session_manager.list_sessions()` still works after any schema change.

## File: `dashboard/components/project_service.py`

```python
"""
project_service.py — Claude-style project model on top of session_manager.

A project is one analysis run with a name, status, and pipeline progress.
Projects map 1:1 to session records; this module is the user-facing API.
"""
from __future__ import annotations
from typing import Optional, Literal
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import uuid

import streamlit as st

# Reuse existing session backend
from session import session_manager

# ---------------------------------------------------------------- types

PipelineStep = Literal[
    "upload", "configure", "eda", "features",
    "modeling", "explainability", "predict",
]
StepStatus = Literal["pending", "active", "done"]
ProjectStatus = Literal["new", "in_progress", "complete"]

PIPELINE_STEPS: list[PipelineStep] = [
    "upload", "configure", "eda", "features",
    "modeling", "explainability", "predict",
]


@dataclass
class Project:
    id: str
    name: str
    created_at: str
    updated_at: str
    user_id: str = "local"
    detected_domain: Optional[str] = None
    confirmed_domain: Optional[str] = None
    analysis_mode: Optional[str] = None  # auto / guided / expert
    dataset_name: Optional[str] = None
    dataset_path: Optional[str] = None
    n_rows: Optional[int] = None
    n_cols: Optional[int] = None
    target_column: Optional[str] = None
    problem_type: Optional[str] = None
    step_status: dict[str, str] = field(default_factory=lambda: {s: "pending" for s in PIPELINE_STEPS})
    metric_summary: Optional[str] = None  # e.g., "AUC 0.847"
    status: ProjectStatus = "new"

    @property
    def progress_pct(self) -> int:
        done = sum(1 for s in PIPELINE_STEPS if self.step_status.get(s) == "done")
        return int(round(done / len(PIPELINE_STEPS) * 100))

    @property
    def steps_done(self) -> int:
        return sum(1 for s in PIPELINE_STEPS if self.step_status.get(s) == "done")

    @property
    def current_step(self) -> Optional[str]:
        for s in PIPELINE_STEPS:
            if self.step_status.get(s) == "active":
                return s
        for s in PIPELINE_STEPS:
            if self.step_status.get(s) == "pending":
                return s
        return None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(**d)


# ---------------------------------------------------------------- API

def create(name: str, user_id: str = "local") -> Project:
    """Create a new empty project. Returns the project. Sets it as active."""
    now = datetime.utcnow().isoformat()
    p = Project(
        id=str(uuid.uuid4()),
        name=name,
        created_at=now,
        updated_at=now,
        user_id=user_id,
    )
    _persist(p)
    set_active(p.id)
    return p


def get(project_id: str) -> Optional[Project]:
    """Load project by id."""
    raw = session_manager.load_session(project_id)
    if not raw:
        return None
    meta = _extract_meta(raw)
    if not meta:
        return None
    return Project.from_dict(meta)


def list_all(user_id: str = "local") -> list[Project]:
    """All projects for a user, newest first."""
    sessions = session_manager.list_sessions()
    projects: list[Project] = []
    for s in sessions:
        meta = _extract_meta(s)
        if meta and meta.get("user_id", "local") == user_id:
            projects.append(Project.from_dict(meta))
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    return projects


def update(project: Project) -> None:
    """Persist updates."""
    project.updated_at = datetime.utcnow().isoformat()
    project.status = _derive_status(project)
    _persist(project)


def update_step(project_id: str, step: PipelineStep, status: StepStatus) -> Optional[Project]:
    """Mark a pipeline step as pending/active/done."""
    p = get(project_id)
    if not p:
        return None
    p.step_status[step] = status
    update(p)
    return p


def delete(project_id: str) -> bool:
    """Delete a project."""
    if get_active_id() == project_id:
        clear_active()
    return session_manager.delete_session(project_id)


def rename(project_id: str, new_name: str) -> Optional[Project]:
    p = get(project_id)
    if not p:
        return None
    p.name = new_name
    update(p)
    return p


def duplicate(project_id: str) -> Optional[Project]:
    """Clone a project under a new id with '(copy)' appended to the name."""
    p = get(project_id)
    if not p:
        return None
    now = datetime.utcnow().isoformat()
    clone = Project(**{**p.to_dict(), "id": str(uuid.uuid4()), "name": f"{p.name} (copy)",
                       "created_at": now, "updated_at": now})
    _persist(clone)
    return clone


# ---------------------------------------------------------------- active project (session_state)

ACTIVE_KEY = "active_project_id"


def get_active_id() -> Optional[str]:
    return st.session_state.get(ACTIVE_KEY)


def get_active() -> Optional[Project]:
    pid = get_active_id()
    return get(pid) if pid else None


def set_active(project_id: str) -> None:
    st.session_state[ACTIVE_KEY] = project_id


def clear_active() -> None:
    if ACTIVE_KEY in st.session_state:
        del st.session_state[ACTIVE_KEY]


def is_active(project_id: str) -> bool:
    return get_active_id() == project_id


# ---------------------------------------------------------------- internals

def _persist(p: Project) -> None:
    """Save through session_manager. Encode project metadata as JSON in the meta column."""
    payload = {
        "session_id": p.id,
        "project_meta": json.dumps(p.to_dict()),
        # Mirror common fields onto the session for backward-compat with anything
        # that reads them directly:
        "domain": p.confirmed_domain or p.detected_domain,
        "analysis_mode": p.analysis_mode,
        "target_column": p.target_column,
        "problem_type": p.problem_type,
    }
    session_manager.save_session(payload)


def _extract_meta(raw: dict) -> Optional[dict]:
    blob = raw.get("project_meta")
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return None


def _derive_status(p: Project) -> ProjectStatus:
    done = p.steps_done
    total = len(PIPELINE_STEPS)
    if done == 0:
        return "new"
    if done == total:
        return "complete"
    return "in_progress"
```

## Compatibility check before implementing

1. Open `session/session_manager.py` and inspect the actual schema. The `_persist` payload above assumes columns `session_id`, `project_meta`, `domain`, `analysis_mode`, `target_column`, `problem_type`. If `session_manager.save_session` accepts a different signature, **adapt the payload to match its signature** rather than changing session_manager.
2. If session_manager has no JSON column at all, add one ALTER TABLE migration. Handle the case where existing sessions don't have `project_meta` — `_extract_meta` should return `None` cleanly so old sessions don't show up as broken projects.
3. Run `pytest tests/integration/test_full_pipeline.py` after this step — session round-trip must still pass.

## Tests to add

`tests/unit/test_project_service.py`:
- create → get → returns same project
- create → list_all → contains the project
- update_step("upload", "done") → progress_pct == ~14
- mark all steps done → status == "complete"
- duplicate → new id, same metadata, name has "(copy)"
- delete active project → active cleared
- list_all sorted by updated_at desc

Target: 8–12 tests, all passing.
