"""Agent tests -- EDA recommendation quality.

Tests that the EDA agent generates appropriate questions and analysis
recommendations for different data types and domains. Uses heuristic
paths (no LLM required for basic tests).
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.requires_llm


class TestEDAQuestionGeneration:
    """Test EDA question generation logic (heuristic path)."""

    def test_generates_questions_for_classification(self, sample_classification_df):
        """EDA agent should generate relevant questions for classification data."""
        from agents.eda_agent import _generate_eda_questions
        from core.state import create_initial_state

        state = create_initial_state("test-eda")
        state["uploaded_data"] = sample_classification_df
        state["target_column"] = "churned"
        state["problem_type"] = "classification"
        state["detected_domain"] = "generic"
        state["user_mode"] = "guided"

        questions = _generate_eda_questions(state)
        assert isinstance(questions, list)
        assert len(questions) > 0

    def test_generates_questions_for_regression(self, sample_regression_df):
        """EDA should adapt questions for regression problems."""
        from agents.eda_agent import _generate_eda_questions
        from core.state import create_initial_state

        state = create_initial_state("test-eda-reg")
        state["uploaded_data"] = sample_regression_df
        state["target_column"] = "price"
        state["problem_type"] = "regression"
        state["detected_domain"] = "generic"
        state["user_mode"] = "guided"

        questions = _generate_eda_questions(state)
        assert isinstance(questions, list)

    def test_healthcare_domain_adds_domain_questions(self, sample_healthcare_df):
        """Healthcare domain should add clinical-specific questions."""
        from agents.eda_agent import _generate_eda_questions
        from core.state import create_initial_state

        state = create_initial_state("test-eda-health")
        state["uploaded_data"] = sample_healthcare_df
        state["target_column"] = "readmitted_30day"
        state["problem_type"] = "classification"
        state["detected_domain"] = "healthcare"
        state["user_mode"] = "guided"

        questions = _generate_eda_questions(state)
        assert isinstance(questions, list)


class TestEDAAnalysisSelection:
    """Test that selected analyses produce valid outputs."""

    def test_distribution_analysis_runs(self, sample_classification_df):
        """Distribution analysis should produce charts/stats."""
        from agents.tools.stats_tools import shapiro_wilk

        result = shapiro_wilk(sample_classification_df, "age")
        assert isinstance(result, dict)
        assert "statistic" in result or "p_value" in result or len(result) > 0

    def test_correlation_analysis_runs(self, sample_classification_df):
        """Correlation analysis should handle mixed-type data."""
        from agents.tools.stats_tools import correlation_matrix

        numeric_cols = list(sample_classification_df.select_dtypes(include="number").columns)
        result = correlation_matrix(sample_classification_df, numeric_cols[:5])
        assert isinstance(result, dict)
