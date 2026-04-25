"""Track timing and resource usage per pipeline step.

Provides both an explicit start/end API and a context-manager for
convenient timing of code blocks.
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

logger = logging.getLogger(__name__)


class PerformanceLog:
    """Track timing and resource usage across pipeline steps.

    Timing data is stored in chronological order and can be queried for
    summaries, slowest steps, and total duration.
    """

    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []
        self._active_timers: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    @contextmanager
    def timer(self, step_name: str) -> Generator[None, None, None]:
        """Context manager for timing a step.

        Usage::

            with perf_log.timer("data_profiling"):
                run_profiling(df)

        Args:
            step_name: Descriptive name for the timed block.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._record(step_name, duration)

    # ------------------------------------------------------------------
    # Explicit start / end API
    # ------------------------------------------------------------------

    def start_step(self, step_name: str) -> None:
        """Mark the beginning of a named step.

        Args:
            step_name: Name of the step to start timing.
        """
        if step_name in self._active_timers:
            logger.warning(
                "Timer for '%s' already running; resetting start time",
                step_name,
            )
        self._active_timers[step_name] = time.perf_counter()

    def end_step(self, step_name: str) -> float:
        """Mark the end of a named step and return its duration.

        Args:
            step_name: Name of the step previously passed to
                       :meth:`start_step`.

        Returns:
            Duration of the step in seconds.

        Raises:
            KeyError: If *step_name* was never started.
        """
        start = self._active_timers.pop(step_name, None)
        if start is None:
            raise KeyError(
                f"No active timer for step '{step_name}'. "
                "Call start_step() first."
            )
        duration = time.perf_counter() - start
        self._record(step_name, duration)
        return round(duration, 3)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_total_duration(self) -> float:
        """Return the sum of all recorded step durations in seconds."""
        return round(sum(s["duration_seconds"] for s in self.steps), 3)

    def get_slowest_steps(self, n: int = 5) -> list[dict[str, Any]]:
        """Return the *n* slowest recorded steps, descending by duration.

        Args:
            n: Maximum number of steps to return.
        """
        sorted_steps = sorted(
            self.steps,
            key=lambda s: s["duration_seconds"],
            reverse=True,
        )
        return sorted_steps[:n]

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all performance data.

        Returns:
            Dictionary with ``total_duration``, ``step_count``,
            ``avg_duration``, and ``slowest_step``.
        """
        total = self.get_total_duration()
        count = len(self.steps)
        avg = round(total / count, 3) if count > 0 else 0.0
        slowest = self.get_slowest_steps(1)
        return {
            "total_duration": total,
            "step_count": count,
            "avg_duration": avg,
            "slowest_step": slowest[0]["step"] if slowest else None,
            "slowest_duration": slowest[0]["duration_seconds"] if slowest else None,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, step_name: str, duration: float) -> None:
        """Append a completed step entry."""
        rounded = round(duration, 3)
        self.steps.append({
            "step": step_name,
            "duration_seconds": rounded,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Step '%s' completed in %.3fs", step_name, rounded)
