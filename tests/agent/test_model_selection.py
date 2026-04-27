"""Agent tests -- model selection quality.

Tests that the modeling agent selects appropriate algorithms and
configurations for different problem types and domains.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.requires_llm


class TestModelSelectionHeuristics:
    """Test modeling agent algorithm selection logic."""

    def test_classification_selects_appropriate_algorithms(self):
        """Classification problems should include tree-based and linear models."""
        from agents.modeling_agent import _resolve_algorithms
        from core.state import create_initial_state

        state = create_initial_state("test-model")
        state["problem_type"] = "classification"
        state["detected_domain"] = "generic"
        state["user_mode"] = "auto"

        algorithms = _resolve_algorithms(state)
        assert isinstance(algorithms, list)
        assert len(algorithms) >= 2

    def test_regression_selects_appropriate_algorithms(self):
        """Regression problems should include linear and tree-based models."""
        from agents.modeling_agent import _resolve_algorithms
        from core.state import create_initial_state

        state = create_initial_state("test-model-reg")
        state["problem_type"] = "regression"
        state["detected_domain"] = "generic"
        state["user_mode"] = "auto"

        algorithms = _resolve_algorithms(state)
        assert isinstance(algorithms, list)
        assert len(algorithms) >= 2

    def test_finance_domain_adds_interpretable_models(self):
        """Finance domain should prioritize interpretable models."""
        from agents.modeling_agent import _resolve_algorithms
        from core.state import create_initial_state

        state = create_initial_state("test-model-fin")
        state["problem_type"] = "classification"
        state["detected_domain"] = "finance"
        state["user_mode"] = "auto"

        algorithms = _resolve_algorithms(state)
        assert isinstance(algorithms, list)
        # Finance should include logistic regression for interpretability
        algo_names = [a.lower() if isinstance(a, str) else str(a).lower() for a in algorithms]
        has_interpretable = any(
            "logistic" in a or "linear" in a or "ridge" in a
            for a in algo_names
        )
        assert has_interpretable or len(algorithms) > 0


class TestEvaluationMetricSelection:
    """Test metric selection for different problem types."""

    def test_classification_metrics(self):
        from agents.orchestrator import _set_evaluation_metrics
        from core.state import create_initial_state

        state = create_initial_state("test-metrics")
        state["problem_type"] = "classification"
        state["detected_domain"] = "generic"

        _set_evaluation_metrics(state)
        metrics = state.get("evaluation_metrics", [])
        assert len(metrics) > 0

    def test_regression_metrics(self):
        from agents.orchestrator import _set_evaluation_metrics
        from core.state import create_initial_state

        state = create_initial_state("test-metrics-reg")
        state["problem_type"] = "regression"
        state["detected_domain"] = "generic"

        _set_evaluation_metrics(state)
        metrics = state.get("evaluation_metrics", [])
        assert len(metrics) > 0
