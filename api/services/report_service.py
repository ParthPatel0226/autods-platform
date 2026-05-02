"""Report service — wraps agents/report_agent.py for the FastAPI layer.

Exposes three callables consumed by the report router:
  - generate_report   Create job and schedule background generation; return job_id
  - get_report        Return report paths / URLs from state
  - _execute_report   Async background worker; dispatches to per-format generators

Format dispatch
---------------
The ``format`` parameter selects which generator to invoke:

    ``html``              → reports.generators.html_report.generate_html_report
    ``executive_summary`` → reports.generators.executive_summary.generate_executive_summary
    ``notebook``          → reports.generators.notebook_export.generate_notebook
    ``zip``               → reports.generators.zip_packager.create_zip_package
                            (bundles existing report files; generates all formats first
                            if none exist yet)
    ``all``               → agents.report_agent.generate_reports (all formats in one call)

Output paths are stored in ``state["report_paths"]`` and returned as relative path
strings (treated as the "URL" by callers — no external storage service).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.report_agent import generate_reports as _generate_all
from reports.generators.html_report import generate_html_report as _gen_html
from reports.generators.executive_summary import (
    generate_executive_summary as _gen_exec,
)
from reports.generators.notebook_export import generate_notebook as _gen_notebook
from reports.generators.zip_packager import create_zip_package as _create_zip
from api.services import state_service
from api.storage import job_store
from core.exceptions import AutoDSError

logger = logging.getLogger(__name__)

_VALID_FORMATS = frozenset({"html", "executive_summary", "notebook", "zip", "all"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_report(project_id: str, user_id: str, format: str) -> str:
    """Create a report generation job and schedule it as an async background task.

    Validates *format*, checks project ownership, creates a job entry in
    ``job_store``, schedules ``_execute_report`` on the running event loop,
    and returns immediately with the ``job_id``.

    Callers should poll ``GET /jobs/{job_id}`` or connect via SSE to track
    progress.

    Args:
        project_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).
        format: One of ``"html"``, ``"executive_summary"``, ``"notebook"``,
            ``"zip"``, or ``"all"``.

    Returns:
        job_id string for progress polling.

    Raises:
        AutoDSError: If *format* is invalid, the project is not found, or
            access is denied.
    """
    if format not in _VALID_FORMATS:
        raise AutoDSError(
            f"Invalid report format '{format}'. "
            f"Valid formats: {sorted(_VALID_FORMATS)}"
        )

    # Ownership check before creating a job record.
    state_service.load_state(project_id, user_id)

    job_id = job_store.create_job("report_generation", project_id, user_id)

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_execute_report(job_id, project_id, user_id, format))
    except RuntimeError:
        # No running event loop (e.g., sync test context).
        logger.warning(
            "No running event loop for job_id=%s — executing synchronously.",
            job_id,
        )
        asyncio.run(_execute_report(job_id, project_id, user_id, format))

    state_service.append_to_pipeline_log(project_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": "report_generate",
        "action": "generate_report",
        "job_id": job_id,
        "format": format,
        "status": "scheduled",
    })

    return job_id


def get_report(report_id: str, user_id: str) -> dict:
    """Return report paths and generation status for a project.

    Uses *report_id* as the project identifier (same value, different
    parameter name for router symmetry).

    Args:
        report_id: Session / project identifier.
        user_id: Requesting user's ID (ownership check).

    Returns:
        Dict with keys::

            {
                "report_paths":    dict,   # format → local file path (str)
                "report_generated": bool,  # True if at least one path exists
            }

    Raises:
        AutoDSError: If the project is not found or access is denied.
    """
    state = state_service.load_state(report_id, user_id)
    return {
        "report_paths": state.get("report_paths") or {},
        "report_generated": bool(state.get("report_generated")),
    }


# ---------------------------------------------------------------------------
# Private background worker
# ---------------------------------------------------------------------------


async def _execute_report(
    job_id: str,
    project_id: str,
    user_id: str,
    format: str,
) -> None:
    """Background coroutine that runs the report generation pipeline.

    Steps:
        1. Mark job running.
        2. Load state; prepare output directory.
        3. Dispatch to the appropriate generator(s) in thread executor.
        4. Persist updated report_paths to state.
        5. Set job result and mark completed.

    For ``format == "zip"``, if no existing report files are found, all
    formats are generated first via ``_generate_all`` before packaging.

    Cancellation is checked after the state load and after generation.

    Args:
        job_id:     Job identifier in ``job_store``.
        project_id: Session / project identifier.
        user_id:    Owner's user ID used for state I/O.
        format:     Validated format string.
    """
    loop = asyncio.get_event_loop()

    job_store.update_job(
        job_id,
        status="running",
        progress=0.05,
        current_step="report_generate",
        message=f"Starting report generation (format={format})...",
    )

    try:
        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 1 — load state
        # ------------------------------------------------------------------ #
        state: dict = await loop.run_in_executor(
            None,
            lambda: state_service.load_state(project_id, user_id),
        )

        job_store.update_job(
            job_id,
            progress=0.10,
            message="Preparing output directory...",
        )

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 2 — prepare output directory
        # ------------------------------------------------------------------ #
        session_id: str = state.get("session_id") or project_id
        output_dir = Path("outputs") / session_id / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        job_store.update_job(
            job_id,
            progress=0.15,
            message=f"Generating {format} report...",
        )

        existing_paths: dict = dict(state.get("report_paths") or {})
        new_paths: dict = {}

        # ------------------------------------------------------------------ #
        # Step 3 — dispatch to generator(s)
        # ------------------------------------------------------------------ #
        if format == "all":
            updated: dict = await loop.run_in_executor(
                None, lambda: _generate_all(state)
            )
            new_paths = dict(updated.get("report_paths") or {})
            state = updated

        elif format == "html":
            path = await loop.run_in_executor(
                None, lambda: _gen_html(state, output_dir)
            )
            if path:
                new_paths["html"] = str(path)

        elif format == "executive_summary":
            path = await loop.run_in_executor(
                None, lambda: _gen_exec(state, output_dir)
            )
            if path:
                new_paths["executive_summary"] = str(path)

        elif format == "notebook":
            path = await loop.run_in_executor(
                None, lambda: _gen_notebook(state, output_dir)
            )
            if path:
                new_paths["notebook"] = str(path)

        elif format == "zip":
            source_paths: list[str] = [
                p for p in existing_paths.values() if p and Path(p).exists()
            ]
            if not source_paths:
                job_store.update_job(
                    job_id,
                    progress=0.20,
                    message="No existing report files; generating all formats first...",
                )
                updated = await loop.run_in_executor(
                    None, lambda: _generate_all(state)
                )
                state = updated
                generated: dict = dict(updated.get("report_paths") or {})
                new_paths.update(generated)
                source_paths = [
                    p
                    for k, p in generated.items()
                    if k != "zip" and p and Path(p).exists()
                ]

            if source_paths:
                zip_path = await loop.run_in_executor(
                    None,
                    lambda: _create_zip(source_paths, output_dir, session_id),
                )
                if zip_path:
                    new_paths["zip"] = str(zip_path)

        if job_store.is_cancelled(job_id):
            return

        # ------------------------------------------------------------------ #
        # Step 4 — persist results
        # ------------------------------------------------------------------ #
        job_store.update_job(
            job_id,
            progress=0.90,
            message="Saving report results...",
        )

        merged_paths: dict = {**existing_paths, **new_paths}

        await loop.run_in_executor(
            None,
            lambda: state_service.update_state(
                project_id,
                user_id,
                report_paths=merged_paths,
                report_generated=bool(merged_paths),
            ),
        )

        state_service.append_to_pipeline_log(project_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": "report_generate",
            "action": "complete",
            "job_id": job_id,
            "format": format,
            "paths_generated": list(new_paths.keys()),
        })

        result = {
            "report_paths": merged_paths,
            "report_generated": bool(merged_paths),
            "format": format,
            "urls": {k: str(v) for k, v in new_paths.items()},
        }
        job_store.set_result(job_id, result)

        job_store.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message=(
                f"Report generation complete "
                f"({', '.join(new_paths.keys()) if new_paths else 'none'})."
            ),
        )

    except Exception as exc:  # noqa: BLE001 — top-level worker catch
        logger.exception(
            "Report generation failed for job_id=%s project=%s", job_id, project_id
        )
        job_store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            message=f"Report generation failed: {exc}",
        )
