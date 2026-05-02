"""Feature Engineering service — wraps agents/feature_engineer.py for the FastAPI layer.

Exposes four callables consumed by the FE router:
  - suggest_decisions   Ask the FE agent to build strategy questions
  - apply_decisions     Store user decisions and schedule execution; return job_id
  - get_results         Read completed FE results from state
  - _execute_fe         Async background worker called by apply_decisions

The backend agent functions are synchronous LangGraph nodes; they are run
inside a thread-pool executor so the event loop is never blocked.

Decision translation
--------------------
The FE agent reads from four flat state keys rather than a single questions
list.  ``apply_decisions`` receives a ``decisions`` mapping of question ID
to user answer and translates it before handing off to ``_execute_fe``:

    fe_q1_imputation  → imputation_strategy  (dict col→method)
    fe_q2_encoding    → encoding_strategy    (dict col→method)
    fe_q3_scaling     → scaling_strategy     (str)
    fe_q4_outliers    → outlier_strategy     (dict col→method)

Cancellation
------------
_execute_fe polls job_store.is_cancelled() between the two major steps
(state load and execution).  If the flag is set the coroutine returns
without writing results, and the job remains in "cancelled" state
(already set by job_store.cancel_job).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from agents.feature_engineer import (
    execute_feature_engineering as _exec_fe,
    generate_fe_questions as _gen_questions,
)
from api.services import state_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Question-ID → state-key mapping
# ---------------------------------------------------------------------------

_DECISION_KEY_MAP: dict[str, str] = {
    "fe_q1_imputation": "imputation_strategy",
    "fe_q2_encoding": "encoding_strategy",
    "fe_q3_scaling": "scaling_strategy",
    "fe_q4_outliers": "outlier_strategy",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def suggest_decisions(project_id: str, user_id: str) -> list[dict]:
    """Generate feature-engineering strategy questions for the project.

    Loads state, invokes ``generate_fe_questions`` (LangGraph node), persists
    the updated state, and returns ``state["fe_questions_asked"]``.

    In AUTO mode the agent auto-selects strategies and returns an empty list;
    callers should proceed directly to ``apply_decisions`` in that case.

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
        logger.exception("generate_fe_questions failed for project=%s", project_id)
        raise AutoDSError(f"FE question generation failed: {exc}") from exc

    state_service.save_state(project_id, updated, user_id)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "fe_questions",
        "action": "suggest_decisions",
        "status": "success",
        "question_count": len(updated.get("fe_questions_asked") or []),
    })

    return list(updated.get("fe_questions_asked") or [])


def apply_decisions(project_id: str, user_id: str, decisions: dict) -> str:
    """Store user strategy decisions and schedule FE execution.

    Translates ``{question_id: answer}`` from *decisions* into the flat state
    keys expected by ``execute_feature_engineering``, persists them, creates a
    job entry in ``job_store``, schedules ``_execute_fe`` on the running event
    loop, and returns immediately with the ``job_id``.

    Callers should poll ``GET /jobs/{job_id}`` or connect via SSE to track
    progress.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        decisions: Mapping of question ``id`` → user answer value.
            Per-column decisions should be ``{col: method}`` dicts.
            Scalar decisions (e.g. scaling) should be plain strings.

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    # Ownership check before creating a job record.
    state_service.load_state(project_id, user_id)

    # Translate and persist decisions into flat strategy keys.
    patches: dict = {}
    for qid, answer in decisions.items():
        state_key = _DECISION_KEY_MAP.get(qid)
        if state_key is not None:
            patches[state_key] = answer
        else:
            logger.warning(
                "apply_decisions: unknown question_id=%s for project=%s — skipped.",
                qid,
                project_id,
            )

    if patches:
        state_service.update_state(project_id, user_id, **patches)

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "fe_questions",
        "action": "apply_decisions",
        "decisions_applied": len(patches),
    })

    job_id = job_store.create_job("fe_execution", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_fe(job_id, project_id, user_id, decisions))
    except RuntimeError:
        # No running event loop (e.g., sync test context). Fall back to
        # blocking execution so callers always get a terminal job state.
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.",
            job_id,
        )
        asyncio.run(_execute_fe(job_id, project_id, user_id, decisions))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "fe_execute",
        "action": "apply_decisions",
        "job_id": job_id,
        "status": "scheduled",
    })

    return job_id


def get_results(project_id: str, user_id: str) -> dict:
    """Return the feature engineering results stored in state.

    Returns a snapshot of the FE output fields regardless of job status.
    If FE has not yet run, all fields will be empty / None.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        Dict with keys: ``features_created``, ``features_selected``,
        ``feature_importance_preliminary``, ``fe_choices``,
        ``imputation_strategy``, ``encoding_strategy``,
        ``scaling_strategy``, ``outlier_strategy``.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    return {
        "features_created": state.get("features_created") or [],
        "features_selected": state.get("features_selected") or [],
        "feature_importance_preliminary": state.get("feature_importance_preliminary") or {},
        "fe_choices": state.get("fe_choices") or {},
        "imputation_strategy": state.get("imputation_strategy") or {},
        "encoding_strategy": state.get("encoding_strategy") or {},
        "scaling_strategy": state.get("scaling_strategy") or "",
        "outlier_strategy": state.get("outlier_strategy") or {},
    }


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_fe(
    job_id: str,
    project_id: str,
    user_id: str,
    decisions: dict,
) -> None:
    """Background coroutine that runs the feature engineering pipeline.

    Steps:
        1. Mark job running.
        2. Load state (check cancel between steps).
        3. Patch state with translated strategy keys from *decisions*.
        4. Run ``execute_feature_engineering`` agent in thread executor.
        5. Persist updated state.
        6. Set job result and mark completed.

    On any exception the job is marked ``failed`` with the error message.
    Cancellation is checked after the state load and after the executor call;
    if the flag is set the coroutine returns silently (the job is already
    in "cancelled" state).

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
        decisions:  Mapping of question ID → user answer (used to patch
                    strategy keys before execution).
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="fe_execute",
        message="Starting feature engineering...",
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
            message="Applying feature engineering strategies...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 2 — patch strategy keys from decisions
        # ------------------------------------------------------------------ #
        for qid, answer in decisions.items():
            state_key = _DECISION_KEY_MAP.get(qid)
            if state_key is not None:
                state[state_key] = answer

        job_store.update_job(
            job_id,
            progress=0.20,
            message="Running imputation, encoding, scaling, and outlier handling...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 3 — execute FE (CPU-bound, runs in thread pool)
        # ------------------------------------------------------------------ #
        updated = await loop.run_in_executor(None, _exec_fe, state)

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 4 — persist results
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.90,
            message="Saving feature engineering results...",
        )

        await loop.run_in_executor(
            None,
            lambda: state_service.save_state(project_id, updated, user_id),
        )

        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "fe_execute",
            "action": "complete",
            "job_id": job_id,
        })

        result = {
            "features_created": updated.get("features_created") or [],
            "features_selected": updated.get("features_selected") or [],
            "feature_importance_preliminary": updated.get("feature_importance_preliminary") or {},
            "fe_choices": updated.get("fe_choices") or {},
        }
        job_store.set_result(job_id, result)

        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="Feature engineering complete.",
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception("FE execution failed for job_id=%s project=%s", job_id, project_id)
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"Feature engineering failed: {exc}",
        )
