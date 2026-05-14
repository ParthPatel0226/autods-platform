"""In-memory job store with SSE event queues.

Stores job state in a plain dict protected by a threading.Lock.
Each active job also has an asyncio.Queue that SSE routes consume via
``subscribe()``.  When a job reaches a terminal state the final event is
published and the queue is closed so the iterator exits cleanly.

Production replacement
----------------------
Swap this module for one backed by Redis Streams:
  - State dict → Redis HSET per job_id
  - Event queues → Redis XADD / XREAD consumer groups
  - cancel_flag → Redis key with TTL
  - subscribe() → async XREAD loop

The function signatures and JobProgressEvent shape stay identical, so
routes require no changes.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from api.schemas.jobs import JobProgressEvent, JobStatus

logger = logging.getLogger(__name__)

_TERMINAL = {"completed", "failed", "cancelled"}

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# job_id -> dict (raw fields, not Pydantic — cheaper to update)
_jobs: dict[str, dict] = {}

# job_id -> dict (arbitrary result payload)
_results: dict[str, dict] = {}

# job_id -> asyncio.Queue[JobProgressEvent | None]
# None is the sentinel that closes the iterator.
_queues: dict[str, asyncio.Queue] = {}

# job_id -> bool  (cancellation flag polled by long-running services)
_cancel_flags: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_job(job_type: str, project_id: str, user_id: str) -> str:
    """Create a new pending job and return its job_id."""
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0.0,
            "current_step": None,
            "started_at": now,
            "finished_at": None,
            "error": None,
            # extra metadata not in JobStatus schema
            "job_type": job_type,
            "project_id": project_id,
            "user_id": user_id,
        }
        _cancel_flags[job_id] = False
        _queues[job_id] = asyncio.Queue()
    return job_id


def get_job(job_id: str) -> Optional[JobStatus]:
    """Return current JobStatus, or None if job_id unknown."""
    with _lock:
        raw = _jobs.get(job_id)
    if raw is None:
        return None
    return JobStatus(
        job_id=raw["job_id"],
        status=raw["status"],
        progress=raw["progress"],
        current_step=raw["current_step"],
        started_at=raw["started_at"],
        finished_at=raw["finished_at"],
        error=raw["error"],
    )


def get_job_owner(job_id: str) -> Optional[str]:
    """Return the user_id that owns *job_id*, or None if unknown."""
    with _lock:
        raw = _jobs.get(job_id)
    if raw is None:
        return None
    return raw.get("user_id")


def update_job(job_id: str, **fields) -> None:
    """Update job fields and publish a JobProgressEvent to the SSE queue.

    Accepted keyword args: status, progress, current_step, error, message.
    ``message`` is used only for the event payload; it is not stored on the job.
    Terminal status transitions also set finished_at.
    """
    message = fields.pop("message", "")
    terminal = False

    with _lock:
        raw = _jobs.get(job_id)
        if raw is None:
            logger.warning("update_job called for unknown job_id=%s", job_id)
            return

        for key, val in fields.items():
            if key in raw:
                raw[key] = val

        status = raw["status"]
        if status in _TERMINAL and raw["finished_at"] is None:
            raw["finished_at"] = datetime.now(timezone.utc)
            terminal = True

        event = JobProgressEvent(
            job_id=job_id,
            status=status,
            progress=raw["progress"],
            message=message or f"Step: {raw['current_step'] or status}",
            timestamp=datetime.now(timezone.utc),
        )
        q = _queues.get(job_id)

    if q is not None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for job_id=%s — event dropped.", job_id)

        if terminal:
            try:
                q.put_nowait(None)  # sentinel — closes the async iterator
            except asyncio.QueueFull:
                pass


def set_result(job_id: str, result: dict) -> None:
    """Store an arbitrary result payload for a completed job."""
    with _lock:
        _results[job_id] = result


def get_result(job_id: str) -> Optional[dict]:
    """Return stored result payload, or None."""
    with _lock:
        return _results.get(job_id)


def cancel_job(job_id: str) -> bool:
    """Request cancellation; return False if job is already terminal or unknown."""
    with _lock:
        raw = _jobs.get(job_id)
        if raw is None or raw["status"] in _TERMINAL:
            return False
        _cancel_flags[job_id] = True
        raw["status"] = "cancelled"
        raw["finished_at"] = datetime.now(timezone.utc)

        event = JobProgressEvent(
            job_id=job_id,
            status="cancelled",
            progress=raw["progress"],
            message="Job cancelled.",
            timestamp=datetime.now(timezone.utc),
        )
        q = _queues.get(job_id)

    if q is not None:
        try:
            q.put_nowait(event)
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass

    return True


def is_cancelled(job_id: str) -> bool:
    """Polling check for long-running services inside a job loop."""
    with _lock:
        return _cancel_flags.get(job_id, False)


async def subscribe(job_id: str) -> AsyncIterator[JobProgressEvent]:
    """Async iterator yielding JobProgressEvents until the job terminates.

    Usage in an SSE route::

        async for event in subscribe(job_id):
            yield f"data: {event.model_dump_json()}\\n\\n"
    """
    with _lock:
        q = _queues.get(job_id)

    if q is None:
        logger.warning("subscribe called for unknown job_id=%s", job_id)
        return

    while True:
        item = await q.get()
        if item is None:
            # Sentinel received — job has reached terminal state.
            break
        yield item
