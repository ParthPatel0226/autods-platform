"""Modeling service — wraps agents/modeling_agent.py for the FastAPI layer.

Exposes five callables consumed by the modeling router:
  - configure          Merge user model config into state; return ETA dict
  - train              Create job and schedule background training; return job_id
  - get_leaderboard    Return all model results + optional statistical comparison
  - select_best        Override best-model selection in state
  - _execute_training  Async background worker; updates progress per algorithm

The backend agent functions are synchronous LangGraph nodes run inside a
thread-pool executor so the event loop is never blocked.

Per-algorithm progress
----------------------
``execute_modeling`` trains all algorithms sequentially inside a single sync
function.  Rather than blocking until it finishes, ``_execute_training``
starts it in a thread-pool executor and then polls ``state["model_results"]``
(mutated in-place by the agent) every 0.5 s.  When a new algorithm key
appears, the job progress is incremented and a descriptive message is emitted.
This requires no modification to the frozen agent code.

MLflow
------
``execute_modeling`` calls ``_log_to_mlflow`` internally for each trained
algorithm.  Run IDs land in ``state["trained_models"][algo]["mlflow_run_id"]``
and are preserved transparently through this service layer.

Cancellation
------------
``_execute_training`` checks ``job_store.is_cancelled()`` before the state
load and after each polling iteration.  The background thread itself cannot
be interrupted mid-run, but the service returns immediately and the final
state save is skipped so partial results are never committed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.modeling_agent import (
    execute_modeling as _exec_modeling,
    generate_model_questions as _gen_questions,
)
from evaluation.model_comparator import compare_models as _compare_models
from api.services import state_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

# Path where execute_modeling saves model artifacts.
_MODEL_OUTPUT_DIR = Path("outputs") / "models"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure(project_id: str, user_id: str, config: dict) -> dict:
    """Merge user model configuration into state and return an ETA dict.

    Calls ``generate_model_questions`` so that question metadata is populated
    even in guided/expert mode, then overlays *config* onto ``model_choices``
    so user-provided values always win.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        config: Partial or full model-choices dict.  Recognised keys::

            {
                "algorithms":   list[str],   # e.g. ["xgboost", "random_forest"]
                "metric":       str,         # e.g. "f1", "rmse"
                "validation":   str,         # e.g. "cv", "holdout"
                "priority":     str,         # e.g. "accuracy", "interpretability"
            }

    Returns:
        ETA dict::

            {
                "model_choices":         dict,
                "questions":             list[dict],
                "estimated_algorithms":  int,
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    # Generate questions so guided-mode metadata is available; ignore errors
    # (the agent may require data that isn't ready yet in some edge cases).
    try:
        state = _gen_questions(state)
    except AutoDSError:
        raise
    except Exception as exc:
        logger.warning(
            "generate_model_questions failed during configure for project=%s: %s",
            project_id,
            exc,
        )

    # Overlay caller-supplied config on top of whatever auto-selection wrote.
    existing_choices: dict = state.get("model_choices") or {}
    merged_choices: dict = {**existing_choices, **config}
    state["model_choices"] = merged_choices

    state_service.save_state(project_id, state, user_id)
    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "model_configure",
        "action": "configure",
        "algorithms": merged_choices.get("algorithms") or [],
        "metric": merged_choices.get("metric"),
    })

    algorithms: list = merged_choices.get("algorithms") or []
    return {
        "model_choices": merged_choices,
        "questions": list(state.get("model_questions_asked") or []),
        "estimated_algorithms": len(algorithms),
    }


def train(project_id: str, user_id: str, config: dict) -> str:
    """Create a training job and schedule it as an async background task.

    If *config* is non-empty it is merged into ``model_choices`` in state
    before the job starts (same semantics as ``configure``).  This allows
    callers to skip a separate ``configure`` call for simple AUTO-mode use.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        config: Optional override for model choices.  Merged on top of any
            previously saved ``model_choices``.

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    # Ownership check before creating a job record.
    state_service.load_state(project_id, user_id)

    if config:
        state = state_service.load_state(project_id, user_id)
        merged = {**(state.get("model_choices") or {}), **config}
        state_service.update_state(project_id, user_id, model_choices=merged)

    job_id = job_store.create_job("model_training", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_training(job_id, project_id, user_id, config))
    except RuntimeError:
        # No running event loop (e.g., sync test context).
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.",
            job_id,
        )
        asyncio.run(_execute_training(job_id, project_id, user_id, config))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "model_execute",
        "action": "train",
        "job_id": job_id,
        "status": "scheduled",
    })

    return job_id


def get_leaderboard(project_id: str, user_id: str) -> dict:
    """Return all trained model results and an optional statistical comparison.

    If two or more models have been trained the leaderboard includes output
    from ``compare_models`` (statistical ranking via paired t-test or Friedman
    test).  If comparison raises (e.g. insufficient CV folds) the field is
    ``None`` rather than propagating the error to the caller.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        Dict with keys: ``model_results``, ``trained_models``, ``best_model``,
        ``best_model_metrics``, ``feature_importance``, ``model_choices``,
        ``comparison``.

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(project_id, user_id)

    model_results: dict = state.get("model_results") or {}
    model_choices: dict = state.get("model_choices") or {}
    metric: str = model_choices.get("metric", "f1")

    comparison: dict | None = None
    if len(model_results) >= 2:
        try:
            comparison = _compare_models(model_results, metric=metric)
        except Exception as exc:
            logger.warning(
                "compare_models failed for project=%s: %s — skipping comparison.",
                project_id,
                exc,
            )

    return {
        "model_results": model_results,
        "trained_models": state.get("trained_models") or {},
        "best_model": state.get("best_model"),
        "best_model_metrics": state.get("best_model_metrics") or {},
        "feature_importance": state.get("feature_importance") or {},
        "model_choices": model_choices,
        "comparison": comparison,
    }


def select_best(project_id: str, user_id: str, model_name: str) -> dict:
    """Override best-model selection in state.

    Verifies that *model_name* exists in ``model_results`` before updating
    state.  Reconstructs the model artifact path from the agent's naming
    convention (``outputs/models/{model_name}.pkl``).

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        model_name: Name of the algorithm to promote as best model.

    Returns:
        Dict with keys: ``best_model``, ``best_model_path``,
        ``best_model_metrics``, ``message``.

    Raises:
        AutoDSError: If the project is not found, access is denied, or
            *model_name* is not in ``model_results``.
    """
    state = state_service.load_state(project_id, user_id)

    model_results: dict = state.get("model_results") or {}
    if model_name not in model_results:
        available = list(model_results.keys())
        raise AutoDSError(
            f"Model '{model_name}' not found in results.  "
            f"Available models: {available}"
        )

    best_metrics: dict = model_results[model_name].get("metrics") or {}
    model_path: str = str(_MODEL_OUTPUT_DIR / f"{model_name}.pkl")

    state_service.update_state(
        project_id,
        user_id,
        best_model=model_name,
        best_model_name=model_name,
        best_model_path=model_path,
        best_model_metrics=best_metrics,
    )

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "model_execute",
        "action": "select_best",
        "model_name": model_name,
        "metrics": best_metrics,
    })

    return {
        "best_model": model_name,
        "best_model_path": model_path,
        "best_model_metrics": best_metrics,
        "message": f"Best model updated to '{model_name}'.",
    }


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_training(
    job_id: str,
    project_id: str,
    user_id: str,
    config: dict,
) -> None:
    """Background coroutine that runs the full model training pipeline.

    Steps:
        1. Mark job running.
        2. Load state; merge *config* into ``model_choices``.
        3. Start ``execute_modeling`` in thread executor (non-blocking).
        4. Poll ``state["model_results"]`` every 0.5 s; emit a progress event
           each time a new algorithm key appears (per-algorithm updates).
        5. Await executor completion.
        6. Persist updated state.
        7. Optionally run statistical comparison; set job result and complete.

    Cancellation is checked before the state load and inside the polling loop.
    Because ``execute_modeling`` runs in a thread it cannot be interrupted
    mid-algorithm, but the state save and job completion are skipped.

    MLflow run IDs written by ``execute_modeling`` are preserved transparently
    in ``state["trained_models"][algo]["mlflow_run_id"]``.

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
        config:     Optional model-choices override dict.
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="model_execute",
        message="Starting model training...",
    )

    try:
        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 1 — load state and apply config
        # ------------------------------------------------------------------ #
        state: dict = await loop.run_in_executor(
            None,
            lambda: state_service.load_state(project_id, user_id),
        )

        if config:
            merged: dict = {**(state.get("model_choices") or {}), **config}
            state["model_choices"] = merged

        # Determine the expected algorithm list for progress accounting.
        algorithms: list[str] = (state.get("model_choices") or {}).get("algorithms") or []
        n_expected: int = max(len(algorithms), 1)

        job_store.update_job(
            job_id,
            progress=0.10,
            message=(
                f"Training {n_expected} algorithm(s): "
                f"{', '.join(algorithms) if algorithms else 'auto-selected'}..."
            ),
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 2 — launch execute_modeling in thread pool (non-blocking)
        # ------------------------------------------------------------------ #
        # state["model_results"] is mutated in-place by the agent as each
        # algorithm finishes; we poll it below to emit per-algorithm events.
        state["model_results"] = state.get("model_results") or {}

        training_future = loop.run_in_executor(None, _exec_modeling, state)

        # ------------------------------------------------------------------ #
        # Step 3 — poll per-algorithm progress while agent runs
        # ------------------------------------------------------------------ #
        seen_algos: set[str] = set()

        while not training_future.done():
            if job_store.is_cancelled(job_id):
                # Thread cannot be stopped; return and skip state save.
                return

            try:
                current_results: dict = dict(state.get("model_results") or {})
                new_algos = set(current_results.keys()) - seen_algos
                for algo in sorted(new_algos):
                    seen_algos.add(algo)
                    completed_count = len(seen_algos)
                    # Progress band: 0.15 → 0.80 during training.
                    progress = 0.15 + 0.65 * min(completed_count / n_expected, 1.0)
                    algo_metrics = current_results[algo].get("metrics") or {}
                    metric_line = ", ".join(
                        f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in list(algo_metrics.items())[:3]
                    )
                    job_store.update_job(
                        job_id,
                        progress=progress,
                        message=(
                            f"Completed {algo} "
                            f"({completed_count}/{n_expected}) — {metric_line}"
                        ),
                    )
            except Exception:
                # Dict iteration during concurrent writes can raise; skip.
                pass

            await asyncio.sleep(0.5)

        # Retrieve result (re-raises any exception from the thread).
        updated: dict = await training_future

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 4 — persist results
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.90,
            message="Saving model results...",
        )

        await loop.run_in_executor(
            None,
            lambda: state_service.save_state(project_id, updated, user_id),
        )

        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "model_execute",
            "action": "complete",
            "job_id": job_id,
            "models_trained": list((updated.get("model_results") or {}).keys()),
            "best_model": updated.get("best_model"),
        })

        # ------------------------------------------------------------------ #
        # Step 5 — statistical comparison (best-effort)
        # ------------------------------------------------------------------ #
        model_results: dict = updated.get("model_results") or {}
        metric_key: str = (updated.get("model_choices") or {}).get("metric", "f1")

        comparison: dict | None = None
        if len(model_results) >= 2:
            try:
                comparison = _compare_models(model_results, metric=metric_key)
            except Exception as exc:
                logger.warning(
                    "compare_models failed for job_id=%s: %s — skipping.",
                    job_id,
                    exc,
                )

        result = {
            "model_results": model_results,
            "trained_models": updated.get("trained_models") or {},
            "best_model": updated.get("best_model"),
            "best_model_metrics": updated.get("best_model_metrics") or {},
            "feature_importance": updated.get("feature_importance") or {},
            "comparison": comparison,
        }
        job_store.set_result(job_id, result)

        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message=(
                f"Training complete. Best model: {updated.get('best_model', 'N/A')}."
            ),
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception(
            "Model training failed for job_id=%s project=%s", job_id, project_id
        )
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"Model training failed: {exc}",
        )
