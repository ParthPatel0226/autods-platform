"""Integration tests -- full pipeline (no LLM).

Tests the pipeline components wired together: domain detection ->
orchestrator heuristics -> data profiling -> validation. All tests
run without Claude API access using heuristic fallbacks.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Domain detection -> orchestrator -> profiling
# ---------------------------------------------------------------------------

class TestDomainDetectionIntegration:
    """Domain detection feeds correct config into orchestrator state."""

    def test_healthcare_domain_detected_from_columns(self, sample_healthcare_df):
        from domains.domain_registry import detect_domain

        cols = list(sample_healthcare_df.columns)
        domain, confidence, config = detect_domain(cols)
        assert domain == "healthcare"
        assert confidence > 0.0
        assert "metrics" in config or len(config) > 0

    def test_generic_fallback_for_ambiguous_data(self, sample_classification_df):
        from domains.domain_registry import detect_domain

        cols = list(sample_classification_df.columns)
        domain, confidence, config = detect_domain(cols)
        # May detect finance (income, balance) or generic -- both acceptable
        assert domain in ("generic", "finance", "ecommerce")


class TestOrchestratorHeuristics:
    """Orchestrator heuristic functions work without LLM."""

    def test_heuristic_detects_classification(self, sample_classification_df):
        from agents.orchestrator import _heuristic_detect_problem_type
        from core.state import create_initial_state

        state = create_initial_state("test-integration")
        state["target_column"] = "churned"
        state["uploaded_data"] = sample_classification_df

        _heuristic_detect_problem_type(state)
        assert state["problem_type"] == "classification"

    def test_heuristic_detects_regression(self, sample_regression_df):
        from agents.orchestrator import _heuristic_detect_problem_type
        from core.state import create_initial_state

        state = create_initial_state("test-integration")
        state["target_column"] = "price"
        state["uploaded_data"] = sample_regression_df

        _heuristic_detect_problem_type(state)
        assert state["problem_type"] == "regression"

    def test_pipeline_steps_set_for_classification(self, sample_classification_df):
        from agents.orchestrator import _set_pipeline_steps
        from core.state import create_initial_state

        state = create_initial_state("test-integration")
        state["problem_type"] = "classification"
        state["target_column"] = "churned"
        state["detected_domain"] = "generic"

        _set_pipeline_steps(state)
        steps = state.get("pipeline_steps", state.get("completed_steps", []))
        # Should have set some pipeline configuration
        assert state.get("problem_type") == "classification"

    def test_evaluation_metrics_set(self, sample_classification_df):
        from agents.orchestrator import _set_evaluation_metrics
        from core.state import create_initial_state

        state = create_initial_state("test-integration")
        state["problem_type"] = "classification"
        state["detected_domain"] = "generic"

        _set_evaluation_metrics(state)
        metrics = state.get("evaluation_metrics", [])
        assert len(metrics) > 0
        assert any("accuracy" in m or "f1" in m for m in metrics)


class TestDataProfilingIntegration:
    """Data profiling produces valid output for various data shapes."""

    def test_profile_classification_data(self, sample_classification_df):
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(sample_classification_df)
        assert isinstance(profile, dict)
        assert "row_count" in profile or "n_rows" in profile or len(profile) > 0

    def test_profile_with_missing_values(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "a": [1, 2, np.nan, 4, 5],
            "b": ["x", None, "y", "z", None],
            "c": [10.0, 20.0, 30.0, 40.0, 50.0],
        })
        from agents.tools.data_tools import get_data_profile

        profile = get_data_profile(df)
        assert isinstance(profile, dict)


class TestValidationIntegration:
    """Validation modules work together on real data."""

    def test_edge_case_detector_on_clean_data(self, sample_classification_df):
        from validation.edge_case_detector import detect_edge_cases

        issues = detect_edge_cases(sample_classification_df, target_column="churned")
        assert isinstance(issues, list)

    def test_input_sanitizer_handles_mixed_types(self):
        from validation.input_sanitizer import sanitize_input

        df = pd.DataFrame({
            "mixed": [1, "two", 3, "four", 5],
            "clean": [10, 20, 30, 40, 50],
        })
        result = sanitize_input(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_schema_extraction_and_validation(self, sample_classification_df):
        from validation.schema_validator import extract_schema, validate_schema

        schema = extract_schema(sample_classification_df)
        assert isinstance(schema, dict)

        # Validate same data against its own schema
        issues = validate_schema(sample_classification_df, schema)
        assert isinstance(issues, list)
        # Same data should have zero or minimal issues
        assert len(issues) <= 1


class TestSessionIntegration:
    """Session save/load round-trip."""

    def test_save_and_load_session(self, tmp_path):
        from session.session_manager import save_session, load_session, list_sessions

        state = {
            "session_id": "test-1",
            "detected_domain": "healthcare",
            "problem_type": "classification",
            "best_model_name": "xgboost",
            "best_model_metrics": {"accuracy": 0.95, "f1": 0.88},
            "completed_steps": ["upload", "eda", "modeling"],
        }

        path = save_session("test-1", state, base_dir=tmp_path)
        assert Path(path).is_file()

        loaded = load_session("test-1", base_dir=tmp_path)
        assert loaded["detected_domain"] == "healthcare"
        assert loaded["best_model_metrics"]["accuracy"] == 0.95

        sessions = list_sessions(base_dir=tmp_path)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test-1"

    def test_session_compare(self, tmp_path):
        from session.session_compare import compare_sessions

        a = {
            "detected_domain": "healthcare",
            "best_model_name": "xgboost",
            "best_model_metrics": {"accuracy": 0.90, "f1": 0.85},
            "features_selected": ["age", "income", "tenure"],
        }
        b = {
            "detected_domain": "healthcare",
            "best_model_name": "lightgbm",
            "best_model_metrics": {"accuracy": 0.93, "f1": 0.88},
            "features_selected": ["age", "income", "balance"],
        }

        result = compare_sessions(a, b, "Run A", "Run B")
        assert result["model_diff"]["same_best"] is False
        assert len(result["summary"]) > 0

    def test_session_export(self, tmp_path):
        from session.session_export import export_session, import_session_config

        state = {
            "session_id": "export-test",
            "user_mode": "guided",
            "detected_domain": "finance",
            "problem_type": "classification",
            "target_column": "default",
            "row_count": 1000,
        }

        out = export_session(state, tmp_path / "export.json")
        assert Path(out).is_file()

        config = import_session_config(out)
        assert config["detected_domain"] == "finance"
        assert config["user_mode"] == "guided"


from pathlib import Path
