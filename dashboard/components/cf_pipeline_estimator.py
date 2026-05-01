"""Heuristic pipeline cost/time estimator for the Configure tab."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class PipelineEstimate:
    n_charts: int
    n_stat_tests: int
    n_models: int
    n_shap: int
    runtime_seconds: float
    llm_cost_usd: float

    @property
    def runtime_str(self) -> str:
        s = self.runtime_seconds
        if s < 60:
            return f"~{int(s)}s"
        m = s / 60
        if m < 60:
            return f"~{int(m)}m"
        return f"~{m/60:.1f}h"

    @property
    def cost_str(self) -> str:
        c = self.llm_cost_usd
        if c < 0.01:
            return "<$0.01"
        return f"${c:.2f}"


_COMPLIANCE_DOMAINS = {"healthcare", "finance", "hr"}


def estimate(
    *,
    n_rows: int,
    n_cols_kept: int,
    mode: str,
    problem_type: str,
    domain_key: str,
) -> PipelineEstimate:
    """Return a heuristic PipelineEstimate."""
    # --- charts ---
    base_charts = max(4, min(n_cols_kept, 20))
    n_charts = base_charts if mode == "auto" else base_charts + 6

    # --- stat tests ---
    n_stat_tests = min(n_cols_kept * 2, 30)

    # --- models ---
    if problem_type in ("classification", "regression"):
        n_models = 4 if mode == "expert" else 3
    elif problem_type == "time_series":
        n_models = 3
    else:
        n_models = 2

    # --- SHAP ---
    n_shap = n_cols_kept if problem_type not in ("clustering",) else 0

    # --- runtime (seconds) ---
    row_factor = math.log10(max(n_rows, 100)) / 4  # log scale
    col_factor = n_cols_kept / 10
    runtime = 30 + row_factor * 40 + col_factor * 10 + n_models * 15 + n_shap * 0.1
    if mode == "expert":
        runtime *= 1.3

    # --- LLM cost (rough) ---
    llm_cost = 0.003 + n_charts * 0.001 + n_stat_tests * 0.0005 + n_models * 0.002
    if domain_key in _COMPLIANCE_DOMAINS:
        llm_cost *= 1.15  # compliance summaries cost more

    return PipelineEstimate(
        n_charts=n_charts,
        n_stat_tests=n_stat_tests,
        n_models=n_models,
        n_shap=n_shap,
        runtime_seconds=runtime,
        llm_cost_usd=llm_cost,
    )
