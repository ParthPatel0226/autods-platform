"""Track LLM API costs per pipeline run.

Reads provider cost tables from ``core.llm_config.PROVIDER_COSTS`` so
the single source of truth for pricing lives in one place.  If the
import is unavailable (e.g. during isolated testing), a local fallback
table is used.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Fallback costs per 1K tokens, kept in sync with core/llm_config.py.
_FALLBACK_COSTS: dict[str, dict[str, float]] = {
    "gemini": {"input": 0.00013, "output": 0.00038},
    "ollama": {"input": 0.0, "output": 0.0},
    "anthropic": {"input": 0.003, "output": 0.015},
    "openai": {"input": 0.005, "output": 0.015},
}


def _load_provider_costs() -> dict[str, dict[str, float]]:
    """Import provider costs from core, fall back to local copy."""
    try:
        from core.llm_config import PROVIDER_COSTS
        return dict(PROVIDER_COSTS)
    except ImportError:
        logger.debug("core.llm_config unavailable; using fallback cost table")
        return dict(_FALLBACK_COSTS)


class CostTracker:
    """Track LLM API costs across a pipeline run.

    Args:
        provider: LLM provider key (``"gemini"``, ``"ollama"``,
                  ``"anthropic"``, ``"openai"``).  Determines the
                  cost-per-token rates applied to every logged call.
    """

    PROVIDER_COSTS: dict[str, dict[str, float]] = _load_provider_costs()

    def __init__(self, provider: str = "gemini") -> None:
        self.provider = provider.lower()
        self.calls: list[dict[str, Any]] = []

        if self.provider not in self.PROVIDER_COSTS:
            logger.warning(
                "Unknown provider '%s'. Cost will be estimated as zero.",
                self.provider,
            )

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def log_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        agent: str = "unknown",
    ) -> None:
        """Record an LLM API call with token counts.

        Args:
            prompt_tokens: Number of input/prompt tokens.
            completion_tokens: Number of output/completion tokens.
            agent: Name of the agent that triggered the call.
        """
        cost = self._calculate_cost(prompt_tokens, completion_tokens)
        self.calls.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(cost, 6),
            "provider": self.provider,
        })
        logger.debug(
            "LLM call by %s: %d in / %d out tokens ($%.6f)",
            agent,
            prompt_tokens,
            completion_tokens,
            cost,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_total_cost(self) -> float:
        """Return the cumulative estimated cost in USD."""
        return round(sum(c["cost_usd"] for c in self.calls), 6)

    def get_total_tokens(self) -> dict[str, int]:
        """Return aggregate token counts.

        Returns:
            Dictionary with ``input``, ``output``, and ``total`` keys.
        """
        total_in = sum(c["prompt_tokens"] for c in self.calls)
        total_out = sum(c["completion_tokens"] for c in self.calls)
        return {
            "input": total_in,
            "output": total_out,
            "total": total_in + total_out,
        }

    def get_cost_by_agent(self) -> dict[str, float]:
        """Return cost breakdown grouped by agent name."""
        breakdown: dict[str, float] = {}
        for call in self.calls:
            agent = call["agent"]
            breakdown[agent] = round(
                breakdown.get(agent, 0.0) + call["cost_usd"], 6
            )
        return breakdown

    def get_summary(self) -> dict[str, Any]:
        """Return an overall cost summary.

        Returns:
            Dictionary with ``provider``, ``total_calls``,
            ``total_cost_usd``, ``total_tokens``, and
            ``cost_by_agent``.
        """
        return {
            "provider": self.provider,
            "total_calls": len(self.calls),
            "total_cost_usd": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "cost_by_agent": self.get_cost_by_agent(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost in USD for the given token counts."""
        rates = self.PROVIDER_COSTS.get(
            self.provider, {"input": 0.0, "output": 0.0}
        )
        input_cost = (prompt_tokens / 1000.0) * rates["input"]
        output_cost = (completion_tokens / 1000.0) * rates["output"]
        return input_cost + output_cost
