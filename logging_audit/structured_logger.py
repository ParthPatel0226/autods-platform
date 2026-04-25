"""Timestamped JSON structured logging system for pipeline events.

Writes one JSON object per line (JSONL format) to a session-specific log
file under the configured log directory.  Each entry includes a UTC
timestamp, log level, event name, and an arbitrary data payload.

Thread safety is achieved by opening the file in append mode for every
write, which is atomic on all major OSes for reasonably sized lines.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Timestamped JSON structured logger for pipeline events.

    Args:
        session_id: Unique session identifier used as the log filename.
        log_dir: Directory where log files are stored.  Created if missing.
    """

    def __init__(self, session_id: str, log_dir: str = "logs") -> None:
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")

        self._session_id = session_id
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / f"{session_id}.jsonl"

        logger.info(
            "StructuredLogger initialised for session '%s' at %s",
            session_id,
            self._log_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_event(
        self,
        event: str,
        data: dict[str, Any] | None = None,
        level: str = "info",
    ) -> None:
        """Log a structured event.

        Args:
            event: Short, human-readable event name (e.g. ``"step_start"``).
            data: Optional dictionary of contextual data.
            level: Log level string (``"debug"``, ``"info"``, ``"warning"``,
                   ``"error"``, ``"critical"``).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "level": level.upper(),
            "event": event,
            "data": data or {},
        }
        self._write_entry(entry)
        getattr(logger, level.lower(), logger.info)(
            "[%s] %s  %s", self._session_id, event, data or ""
        )

    def log_step_start(self, step_name: str) -> None:
        """Log the start of a pipeline step.

        Args:
            step_name: Name of the pipeline step beginning execution.
        """
        self.log_event(
            "step_start",
            {"step": step_name},
            level="info",
        )

    def log_step_end(
        self,
        step_name: str,
        duration_seconds: float,
        status: str = "success",
    ) -> None:
        """Log the completion of a pipeline step.

        Args:
            step_name: Name of the completed step.
            duration_seconds: Wall-clock time spent in the step.
            status: Outcome indicator (``"success"`` or ``"failure"``).
        """
        self.log_event(
            "step_end",
            {
                "step": step_name,
                "duration_seconds": round(duration_seconds, 3),
                "status": status,
            },
            level="info" if status == "success" else "warning",
        )

    def log_tool_call(
        self,
        tool_name: str,
        params: dict[str, Any],
        result_summary: str,
        duration: float,
    ) -> None:
        """Log a tool-function invocation.

        Args:
            tool_name: Registered name of the tool.
            params: Parameters passed to the tool.
            result_summary: Short textual summary of the result.
            duration: Execution time in seconds.
        """
        self.log_event(
            "tool_call",
            {
                "tool": tool_name,
                "params": params,
                "result_summary": result_summary,
                "duration_seconds": round(duration, 3),
            },
            level="info",
        )

    def log_error(
        self,
        step: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log an error with full context and traceback.

        Args:
            step: Pipeline step where the error occurred.
            error: The caught exception instance.
            context: Additional context about the failure.
        """
        data: dict[str, Any] = {
            "step": step,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exception(type(error), error, error.__traceback__),
        }
        if context:
            data["context"] = context
        self.log_event("error", data, level="error")

    def get_log_path(self) -> str:
        """Return the absolute path to the current log file."""
        return str(self._log_path.resolve())

    def get_all_events(self) -> list[dict[str, Any]]:
        """Read and return all events from the log file.

        Returns:
            List of event dictionaries in chronological order.
        """
        if not self._log_path.exists():
            return []

        events: list[dict[str, Any]] = []
        with self._log_path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed JSON on line %d of %s",
                        line_no,
                        self._log_path,
                    )
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Append a single JSON line to the log file.

        Uses append mode so concurrent writers do not clobber each other
        on POSIX systems (writes up to PIPE_BUF are atomic).
        """
        try:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, default=str) + "\n")
        except OSError:
            logger.exception("Failed to write log entry to %s", self._log_path)
