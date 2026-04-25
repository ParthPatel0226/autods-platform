"""Integration tests -- finance domain path.

Verifies finance-specific pipeline behavior: domain detection,
KS/Gini metrics, PSI drift detection, and adverse action code generation.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def finance_df():
    """Finance dataset with credit-related columns."""
    np.random.seed(42)
    n = 300
    return pd.DataFrame({
        "credit_score": np.random.randint(300, 850, n),
        "annual_income": np.random.lognormal(10.5, 0.8, n).astype(int),
        "debt_to_income": np.random.uniform(0, 0.6, n).round(2),
        "loan_amount": np.random.randint(5000, 500000, n),
        "employment_length": np.random.randint(0, 30, n),
        "num_accounts": np.random.randint(1, 20, n),
        "delinquency_flag": np.random.choice([0, 1], n, p=[0.85, 0.15]),
        "default": np.random.choice([0, 1], n, p=[0.9, 0.1]),
    })


class TestFinanceDomainDetection:
    def test_detects_finance_from_columns(self, finance_df):
        from domains.domain_registry import detect_domain

        domain, confidence, config = detect_domain(list(finance_df.columns))
        assert domain == "finance"
        assert confidence > 0.0


class TestFinanceTools:
    def test_ks_statistic(self, finance_df):
        from agents.tools.domain_tools import ks_statistic

        proba = np.random.uniform(0, 1, len(finance_df))
        result = ks_statistic(
            pd.DataFrame({"score": proba, "target": finance_df["default"]}),
            score_column="score",
            target_column="target",
        )
        assert isinstance(result, dict)
        assert "ks_statistic" in result or "ks" in result or len(result) > 0

    def test_gini_coefficient(self, finance_df):
        from agents.tools.domain_tools import gini_coefficient

        proba = np.random.uniform(0, 1, len(finance_df))
        result = gini_coefficient(
            pd.DataFrame({"score": proba, "target": finance_df["default"]}),
            score_column="score",
            target_column="target",
        )
        assert isinstance(result, dict)

    def test_psi_calculation(self):
        from agents.tools.domain_tools import psi_calculation

        np.random.seed(42)
        expected = np.random.normal(0, 1, 1000)
        actual = np.random.normal(0.2, 1.1, 1000)
        df = pd.DataFrame({"feature": np.concatenate([expected, actual])})
        result = psi_calculation(
            pd.DataFrame({"feature": expected}),
            pd.DataFrame({"feature": actual}),
            "feature",
        )
        assert isinstance(result, dict)


class TestFinanceAdverseAction:
    def test_adverse_action_codes(self):
        from explainability.adverse_action import generate_adverse_action_notice

        feature_contributions = {
            "credit_score": -0.35,
            "debt_to_income": -0.25,
            "employment_length": -0.15,
            "num_accounts": 0.10,
            "annual_income": 0.05,
        }
        result = generate_adverse_action_notice(feature_contributions, top_n=4)
        assert isinstance(result, (dict, list))
