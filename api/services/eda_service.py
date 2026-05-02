"""EDA service — wraps agents/eda_agent.py for the FastAPI layer.

Exposes five callables consumed by the EDA router:
  - generate_questions   Ask the EDA agent to build domain-aware questions
  - submit_answers       Merge user responses and derive analysis list
  - run_analysis         Start a background EDA job; return job_id
  - get_results          Read completed EDA results from state
  - _execute_eda         Async background worker called by run_analysis

The backend agent functions are synchronous LangGraph nodes; they are run
inside a thread-pool executor so the event loop is never blocked.

Cancellation
------------
_execute_eda polls job_store.is_cancelled() between the two major steps
(state load and analysis execution).  If the flag is set the coroutine
returns without writing results, and the job remains in "cancelled" state
(already set by job_store.cancel_job).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from agents.eda_agent import (
    _extract_analyses_from_answers,
    execute_eda as _exec_eda,
    generate_eda_questions as _gen_questions,
)
from api.services import state_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_questions(project_id: str, user_id: str) -> list[dict]:
    """Generate domain-aware EDA questions for the project.

    Loads state, invokes ``generate_eda_questions`` (LangGraph node), persists
    the updated state, and returns ``state["eda_questions_asked"]``.

    In AUTO mode the agent auto-answers and returns an empty list; callers
    should proceed directly to ``run_analysis`` in that case.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        List of question dicts (may be empty for AUTO mode).

    Raises:
        AutoDSError: If the project is not found, access is denied, or the
            agent raises an unexpected error.
    """
    state = state_service.load_state(project_id, user_id)

    try:
        updated = _gen_questions(state)
    except AutoDSError:
        raise
    except Exception as exc:
        logger.exception("generate_eda_questions failed for project=%s", project_id)
        raise AutoDSError(f"EDA question generation failed: {exc}") from exc

    state_service.save_state(project_id, updated, user_id)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "eda_questions",
        "action": "generate_questions",
        "status": "success",
        "question_count": len(updated.get("eda_questions_asked") or []),
    })

    return list(updated.get("eda_questions_asked") or [])


def submit_answers(project_id: str, user_id: str, answers: dict) -> dict:
    """Store user answers to EDA questions and derive the analysis list.

    Merges ``{question_id: user_response}`` from *answers* into the stored
    ``eda_questions_asked`` list, then calls ``_extract_analyses_from_answers``
    to derive ``eda_analyses_selected``.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        answers: Mapping of question ``id`` → user response value.

    Returns:
        Summary dict::

            {
                "questions_answered": int,
                "total_questions": int,
                "analyses_selected": list[str],
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)
    questions: list[dict] = list(state.get("eda_questions_asked") or [])

    # Merge caller-supplied answers into the stored question objects.
    for q in questions:
        qid = q.get("id")
        if qid and qid in answers:
            q["user_response"] = answers[qid]

    # Derive the analysis list from answered questions.
    analyses: list[str] = _extract_analyses_from_answers(questions)

    state_service.update_state(
        project_id,
        user_id,
        eda_questions_asked=questions,
        eda_analyses_selected=analyses,
    )

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "eda_questions",
        "action": "submit_answers",
        "answered": len(answers),
        "analyses_selected": len(analyses),
    })

    return {
        "questions_answered": len(answers),
        "total_questions": len(questions),
        "analyses_selected": analyses,
    }


def run_analysis(project_id: str, user_id: str) -> str:
    """Create an EDA analysis job and schedule it as an async background task.

    Verifies ownership, creates a job entry in ``job_store``, schedules
    ``_execute_eda`` on the running event loop, and returns immediately with
    the ``job_id``.

    Callers should poll ``GET /jobs/{job_id}`` or connect via SSE to track
    progress.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    # Ownership check before creating a job record.
    state_service.load_state(project_id, user_id)

    job_id = job_store.create_job("eda_analysis", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_eda(job_id, project_id, user_id))
    except RuntimeError:
        # No running event loop (e.g., sync test context). Fall back to
        # blocking execution so callers always get a terminal job state.
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.",
            job_id,
        )
        asyncio.run(_execute_eda(job_id, project_id, user_id))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "eda_execute",
        "action": "run_analysis",
        "job_id": job_id,
        "status": "scheduled",
    })

    return job_id


def get_results(project_id: str, user_id: str) -> dict:
    """Return the EDA results stored in state.

    Returns a snapshot of the EDA output fields regardless of job status.
    If analysis has not yet run, all fields will be empty / None.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        Dict with keys: ``eda_results``, ``eda_charts``, ``eda_summary``,
        ``eda_insights``, ``eda_analyses_selected``.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    return {
        "eda_results": state.get("eda_results") or {},
        "eda_charts": state.get("eda_charts") or [],
        "eda_summary": state.get("eda_summary") or "",
        "eda_insights": state.get("eda_insights") or [],
        "eda_analyses_selected": state.get("eda_analyses_selected") or [],
    }


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_eda(job_id: str, project_id: str, user_id: str) -> None:
    """Background coroutine that runs the EDA analysis pipeline.

    Steps:
        1. Mark job running.
        2. Load state (check cancel between steps).
        3. Run ``execute_eda`` agent in thread executor (sync function).
        4. Persist updated state.
        5. Set job result and mark completed.

    On any exception the job is marked ``failed`` with the error message.
    Cancellation is checked after the state load and after the executor call;
    if the flag is set the coroutine returns silently (the job is already
    in "cancelled" state).

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="eda_execute",
        message="Starting EDA analysis...",
    )

    try:
        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 1 — load state
        # ------------------------------------------------------------------ #
        state = await loop.run_in_executor(
            None,
            lambda: state_service.load_state(project_id, user_id),
        )

        job_store.update_job(
            job_id,
            progress=0.10,
            message="Running statistical analyses and generating visualizations...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 2 — execute EDA (CPU-bound, runs in thread pool)
        # ------------------------------------------------------------------ #
        updated = await loop.run_in_executor(None, _exec_eda, state)

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 3 — persist results
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.90,
            message="Saving EDA results...",
        )

        await loop.run_in_executor(
            None,
            lambda: state_service.save_state(project_id, updated, user_id),
        )

        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "eda_execute",
            "action": "complete",
            "job_id": job_id,
        })

        result = {
            "eda_results": updated.get("eda_results") or {},
            "eda_charts": updated.get("eda_charts") or [],
            "eda_summary": updated.get("eda_summary") or "",
            "eda_insights": updated.get("eda_insights") or [],
        }
        job_store.set_result(job_id, result)

        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="EDA analysis complete.",
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception("EDA analysis failed for job_id=%s project=%s", job_id, project_id)
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"EDA analysis failed: {exc}",
        )
