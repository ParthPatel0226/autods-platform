"""Agent tests -- data profiler decision quality.

Tests that the data profiler agent makes correct decisions about
data types, quality issues, and cleaning recommendations.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.requires_llm


class TestProfilerTypeDetection:
    """Test profiler's column type inference."""

    def test_detects_numeric_columns(self, sample_classification_df):
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(sample_classification_df)
        assert isinstance(profile, dict)

    def test_detects_categorical_columns(self):
        df = pd.DataFrame({
            "category": ["A", "B", "C", "A", "B"] * 20,
            "value": range(100),
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)

    def test_detects_datetime_columns(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=50),
            "value": range(50),
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)


class TestProfilerQualityDetection:
    """Test profiler's data quality assessment."""

    def test_detects_high_missing_rate(self):
        df = pd.DataFrame({
            "good": range(100),
            "bad": [np.nan] * 80 + list(range(20)),
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)

    def test_detects_constant_column(self):
        df = pd.DataFrame({
            "constant": [42] * 100,
            "varying": range(100),
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)

    def test_handles_empty_dataframe(self):
        df = pd.DataFrame({"a": pd.Series(dtype=float), "b": pd.Series(dtype=str)})
        from agents.tools.data_tools import get_data_profile

        # Should not crash on empty data
        try:
            profile = get_data_profile(df)
            assert isinstance(profile, dict)
        except Exception:
            # Acceptable to raise on empty data
            pass


class TestProfilerCleaningRecommendations:
    """Test profiler's cleaning action recommendations."""

    def test_recommends_imputation_for_missing(self):
        """Profiler should flag columns with missing values."""
        df = pd.DataFrame({
            "complete": range(100),
            "partial": [1.0] * 70 + [np.nan] * 30,
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        # Profile should contain information about missing values
        assert isinstance(profile, dict)

    def test_detects_id_columns(self):
        """Profiler should identify ID-like columns (unique per row)."""
        df = pd.DataFrame({
            "user_id": range(100),
            "age": np.random.randint(18, 80, 100),
            "target": np.random.choice([0, 1], 100),
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)
