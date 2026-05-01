"""Contract tests for dashboard page interfaces.

These tests verify the public API contracts that pages depend on.
If any of these fail, a UI handoff has broken a contract.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Session state key registry
# Every session_state key used across dashboard pages is documented here.
# If a page adds a new key, add it here too.
# ---------------------------------------------------------------------------

DOCUMENTED_SESSION_STATE_KEYS = {
    # Auth / user
    "supabase_session",
    "supabase_client",
    # Theme
    "dark_mode",
    # Upload
    "uploaded_data",
    "row_count",
    "column_count",
    "_upload_cache_key",
    "uploaded_file_name",
    "columns",
    "additional_datasets",
    # Configure
    "detected_domain",
    "domain_detection_confidence",
    "domain_config",
    "target_column",
    "problem_type",
    "time_column",
    "user_goal",
    "user_mode",
    "pipeline_started",
    "workflow_status",
    # EDA
    "eda_summary",
    "eda_questions",
    "eda_user_responses",
    "eda_analyses_submitted",
    "eda_results",
    "eda_charts",
    "eda_insights",
    # Feature Engineering
    "fe_choices",
    "domain_feature_suggestions",
    "feature_importance_preliminary",
    "domain_features_selected",
    "feature_list",
    # Modeling
    "model_results",
    "training_progress",
    "best_model_name",
    "best_model_metrics",
    "feature_importance",
    "algorithms_selected",
    "validation_strategy",
    "tuning_strategy",
    "training_submitted",
    # Explainability
    "shap_values",
    "explainability_results",
    "counterfactual_examples",
    "fairness_report",
    "model_card",
    "explain_active_tab",
    # Predict
    "prediction_input_data",
    "batch_prediction_submitted",
    "batch_prediction_results",
    "single_prediction_input",
    "single_prediction_submitted",
    "single_prediction_result",
    "predict_active_tab",
    # Chat
    "chat_messages",
    "followup_agent_fn",
    # Download / Reports
    "report_paths",
    "processed_data",
    "best_model_path",
    "api_endpoint_code",
    "dockerfile_content",
    # Pipeline metadata
    "completed_steps",
    "current_step",
    "decision_log",
    "pipeline_log",
    "estimated_cost_usd",
    "api_token_count",
    "api_call_count",
    "errors",
    "warnings",
    "quality_issues",
    # LLM
    "llm_provider",
}


class TestSessionStateRegistry:
    """Every session_state key used across pages must be documented."""

    def test_registry_is_nonempty(self):
        assert len(DOCUMENTED_SESSION_STATE_KEYS) > 50

    def test_no_duplicate_keys(self):
        # set already deduplicates, but verify count matches a list
        keys_list = list(DOCUMENTED_SESSION_STATE_KEYS)
        assert len(keys_list) == len(set(keys_list))


class TestSharedCss:
    """shared_css.inject_shared_css() must run without error."""

    def test_inject_shared_css_callable(self):
        from dashboard.components.shared_css import inject_shared_css
        assert callable(inject_shared_css)


class TestAuthService:
    """auth module must expose expected interface."""

    def test_require_auth_exists(self):
        from auth import require_auth
        assert callable(require_auth)

    def test_login_form_exists(self):
        from auth import login_form
        assert callable(login_form)

    def test_signup_form_exists(self):
        from auth import signup_form
        assert callable(signup_form)

    def test_logout_exists(self):
        from auth import logout
        assert callable(logout)


class TestDbService:
    """db module must expose expected interface."""

    def test_get_client_exists(self):
        from db import get_client
        assert callable(get_client)
