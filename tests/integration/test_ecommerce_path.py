"""Integration tests -- e-commerce domain path.

Verifies e-commerce-specific pipeline behavior: domain detection,
RFM scoring, CLV estimation, and e-commerce report template.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def ecommerce_df():
    """E-commerce dataset with transaction columns."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "customer_id": np.random.randint(1, 100, n),
        "order_id": range(1, n + 1),
        "order_date": pd.date_range("2023-01-01", periods=n, freq="2h"),
        "order_amount": np.random.lognormal(3.5, 1, n).round(2),
        "product_category": np.random.choice(
            ["Electronics", "Clothing", "Books", "Home", "Sports"], n
        ),
        "quantity": np.random.randint(1, 10, n),
        "discount_pct": np.random.choice([0, 5, 10, 15, 20], n),
        "returned": np.random.choice([0, 1], n, p=[0.92, 0.08]),
    })


class TestEcommerceDomainDetection:
    def test_detects_ecommerce_from_columns(self, ecommerce_df):
        from domains.domain_registry import detect_domain

        domain, confidence, config = detect_domain(list(ecommerce_df.columns))
        assert domain == "ecommerce"
        assert confidence > 0.0


class TestEcommerceTools:
    def test_rfm_scoring(self, ecommerce_df):
        from agents.tools.domain_tools import rfm_scoring

        result = rfm_scoring(
            ecommerce_df,
            customer_id_col="customer_id",
            date_col="order_date",
            amount_col="order_amount",
        )
        assert isinstance(result, dict)

    def test_clv_estimation(self, ecommerce_df):
        from agents.tools.domain_tools import clv_estimation

        result = clv_estimation(
            ecommerce_df,
            customer_id_col="customer_id",
            date_col="order_date",
            amount_col="order_amount",
        )
        assert isinstance(result, dict)


class TestEcommerceEdgeCases:
    def test_single_customer_rfm(self):
        from agents.tools.domain_tools import rfm_scoring

        df = pd.DataFrame({
            "customer_id": [1] * 5,
            "order_date": pd.date_range("2024-01-01", periods=5),
            "order_amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        })
        result = rfm_scoring(df, "customer_id", "order_date", "order_amount")
        assert isinstance(result, dict)
