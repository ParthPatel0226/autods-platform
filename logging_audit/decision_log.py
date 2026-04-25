"""Track every agent decision with reasoning for auditability.

Stores decisions in memory and provides export capabilities for
compliance review (healthcare, finance) and debugging.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DecisionLog:
    """Track agent decisions for auditability.

    Each decision records which agent made it, what was chosen, what the
    alternatives were, and the reasoning behind the choice.
    """

    def __init__(self) -> None:
        self.decisions: list[dict[str, Any]] = []

    def log_decision(
        self,
        agent: str,
        decision_type: str,
        chosen: str,
        alternatives: list[str] | None = None,
        reasoning: str = "",
        confidence: float | None = None,
    ) -> None:
        """Record a decision made by an agent.

        Args:
            agent: Name of the agent that made the decision (e.g. ``"eda_agent"``).
            decision_type: Category of decision (e.g. ``"imputation_strategy"``).
            chosen: The option that was selected.
            alternatives: Other options that were considered.
            reasoning: Free-text explanation of why *chosen* was preferred.
            confidence: Optional confidence score in ``[0.0, 1.0]``.
        """
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            logger.warning(
                "Confidence %.3f outside [0, 1] for decision '%s' by '%s'",
                confidence,
                decision_type,
                agent,
            )

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "decision_type": decision_type,
            "chosen": chosen,
            "alternatives": alternatives or [],
            "reasoning": reasoning,
            "confidence": confidence,
        }
        self.decisions.append(entry)

        logger.info(
            "[Decision] %s chose '%s' for %s (confidence=%s)",
            agent,
            chosen,
            decision_type,
            confidence,
        )

    def get_decisions_for_step(self, step: str) -> list[dict[str, Any]]:
        """Return all decisions associated with a given pipeline step / agent.

        The *step* argument is matched against the ``agent`` field using a
        case-insensitive substring check so that both ``"eda"`` and
        ``"eda_agent"`` match a decision logged by ``"eda_agent"``.
        """
        step_lower = step.lower()
        return [
            d for d in self.decisions
            if step_lower in d["agent"].lower()
        ]

    def get_all_decisions(self) -> list[dict[str, Any]]:
        """Return all recorded decisions."""
        return list(self.decisions)

    def to_state_format(self) -> list[dict[str, Any]]:
        """Format decisions for storage in ``AutoDSState.decision_log``.

        Returns a lightweight copy of every decision containing only the
        fields expected by the shared pipeline state.
        """
        return [
            {
                "timestamp": d["timestamp"],
                "agent": d["agent"],
                "decision_type": d["decision_type"],
                "chosen": d["chosen"],
                "alternatives": d["alternatives"],
                "reasoning": d["reasoning"],
                "confidence": d["confidence"],
            }
            for d in self.decisions
        ]

    def export_to_json(self, path: str) -> None:
        """Write all decisions to a JSON file.

        Args:
            path: Destination file path.  Parent directories are created if
                  they do not already exist.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(self.decisions, fh, indent=2, default=str)
        logger.info("Exported %d decisions to %s", len(self.decisions), out)
