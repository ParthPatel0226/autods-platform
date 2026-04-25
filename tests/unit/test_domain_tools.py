"""Unit tests for agents/tools/domain_tools.py

Covers domain-specific calculation functions across Healthcare, Finance,
E-commerce, Manufacturing, and Marketing domains. Each function has
happy-path and edge-case tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.exceptions import ToolExecutionError

from agents.tools.domain_tools import (
    charlson_comorbidity_index,
    elixhauser_comorbidity,
    ks_statistic,
    gini_coefficient,
    psi_calculation,
    rfm_segmentation,
    clv_calculation,
    oee_calculation,
    campaign_lift,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def icd_df() -> pd.DataFrame:
    """DataFrame with ICD-10 codes for comorbidity tests."""
    return pd.DataFrame({
        "patient_id": [1, 2, 3, 4, 5],
        "icd_codes": [
            "I50,E11,N18",        # CHF(1) + diabetes(1) + renal(2) = 4
            "J44,M05",            # chronic pulmonary(1) + rheumatic(1) = 2
            "C78,B20",            # metastatic cancer(6) + cancer via C7(2) + AIDS(6) = 14
            np.nan,               # missing -> 0
            "I10,Z00",            # no Charlson match -> 0
        ],
    })


@pytest.fixture
def binary_scores() -> tuple[np.ndarray, np.ndarray]:
    """Deterministic binary labels and predicted scores for KS/Gini tests."""
    rng = np.random.RandomState(99)
    n = 200
    y_true = np.array([1] * 80 + [0] * 120)
    # Positives get higher scores on average
    y_scores = np.where(y_true == 1, rng.beta(5, 2, n), rng.beta(2, 5, n))
    return y_true, y_scores


@pytest.fixture
def transaction_df() -> pd.DataFrame:
    """Transaction-level DataFrame for RFM and CLV tests."""
    rng = np.random.RandomState(42)
    n = 100
    customers = rng.choice(["C001", "C002", "C003", "C004", "C005"], n)
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    return pd.DataFrame({
        "customer_id": customers,
        "date": rng.choice(dates, n),
        "amount": rng.uniform(10, 500, n).round(2),
    })


@pytest.fixture
def oee_df() -> pd.DataFrame:
    """DataFrame with OEE component columns (0-1 scale)."""
    rng = np.random.RandomState(7)
    n = 30
    return pd.DataFrame({
        "availability": rng.uniform(0.80, 0.99, n).round(4),
        "performance": rng.uniform(0.75, 0.98, n).round(4),
        "quality": rng.uniform(0.90, 1.0, n).round(4),
    })


@pytest.fixture
def campaign_df() -> pd.DataFrame:
    """DataFrame for A/B test campaign lift analysis."""
    rng = np.random.RandomState(123)
    n = 1000
    treatment = np.array([1] * 500 + [0] * 500)
    # Treatment group has higher conversion rate
    outcome = np.where(
        treatment == 1,
        rng.binomial(1, 0.12, n),
        rng.binomial(1, 0.08, n),
    )
    return pd.DataFrame({
        "treatment": treatment,
        "converted": outcome,
    })


# =========================================================================
# Healthcare: charlson_comorbidity_index
# =========================================================================


class TestCharlsonComorbidityIndex:
    """Tests for the Charlson Comorbidity Index calculator."""

    def test_happy_path_scores(self, icd_df: pd.DataFrame) -> None:
        result = charlson_comorbidity_index(icd_df, "icd_codes")

        scores = result["scores"]
        assert len(scores) == 5

        # Patient 1: CHF(1) + diabetes(1) + renal(2) = 4
        assert scores[0] == 4
        # Patient 2: pulmonary(1) + rheumatic(1) = 2
        assert scores[1] == 2
        # Patient 3: metastatic cancer(6) + cancer via C7 prefix(2) + AIDS(6) = 14
        assert scores[2] == 14
        # Patient 4: NaN -> 0
        assert scores[3] == 0
        # Patient 5: no Charlson match -> 0
        assert scores[4] == 0

        summary = result["summary"]
        assert "mean" in summary
        assert "median" in summary
        assert "distribution" in summary
        assert summary["min"] == 0
        assert summary["max"] == 14

    def test_missing_column_raises(self) -> None:
        df = pd.DataFrame({"other": ["A", "B"]})
        with pytest.raises(ToolExecutionError, match="not found"):
            charlson_comorbidity_index(df, "icd_codes")

    def test_empty_dataframe_raises(self) -> None:
        """Empty DataFrame triggers a ValueError because summary stats
        on an empty Series produce NaN which cannot convert to int.
        This documents current behavior -- a future fix could return
        an empty result instead."""
        df = pd.DataFrame({"icd_codes": pd.Series([], dtype=str)})
        with pytest.raises(ValueError):
            charlson_comorbidity_index(df, "icd_codes")

    def test_all_nan_codes(self) -> None:
        df = pd.DataFrame({"icd_codes": [np.nan, np.nan, np.nan]})
        result = charlson_comorbidity_index(df, "icd_codes")
        assert result["scores"] == [0, 0, 0]


# =========================================================================
# Healthcare: elixhauser_comorbidity
# =========================================================================


class TestElixhauserComorbidity:
    """Tests for the Elixhauser comorbidity counter."""

    def test_happy_path(self, icd_df: pd.DataFrame) -> None:
        result = elixhauser_comorbidity(icd_df, "icd_codes")

        assert "category_counts" in result
        assert "total_comorbidities" in result
        assert len(result["total_comorbidities"]) == 5

        # Patient 1 has I50 (CHF), E11 (diabetes_uncomplicated), N18 (renal_failure)
        assert result["total_comorbidities"][0] >= 3
        # Patient 4 is NaN -> 0
        assert result["total_comorbidities"][3] == 0

        # Only non-zero categories should appear
        for count in result["category_counts"].values():
            assert count > 0

    def test_missing_column_raises(self) -> None:
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ToolExecutionError, match="not found"):
            elixhauser_comorbidity(df, "icd_codes")

    def test_no_matches(self) -> None:
        df = pd.DataFrame({"icd_codes": ["Z99", "Z00"]})
        result = elixhauser_comorbidity(df, "icd_codes")
        assert result["category_counts"] == {}
        assert result["total_comorbidities"] == [0, 0]


# =========================================================================
# Finance: ks_statistic
# =========================================================================


class TestKsStatistic:
    """Tests for the KS statistic calculator."""

    def test_happy_path(self, binary_scores: tuple[np.ndarray, np.ndarray]) -> None:
        y_true, y_scores = binary_scores
        result = ks_statistic(y_true, y_scores)

        assert 0.0 < result["ks_stat"] <= 1.0
        assert "ks_threshold" in result
        assert len(result["ks_table"]) == 10
        # First decile should have a higher event rate than last
        assert result["ks_table"][0]["event_rate"] >= result["ks_table"][-1]["event_rate"]

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="same length"):
            ks_statistic(np.array([0, 1]), np.array([0.5]))

    def test_all_nan_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="No valid"):
            ks_statistic(np.array([np.nan, np.nan]), np.array([np.nan, np.nan]))

    def test_single_class_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="both positive and negative"):
            ks_statistic(np.array([1, 1, 1, 1]), np.array([0.5, 0.6, 0.7, 0.8]))

    def test_invalid_labels_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="only 0 and 1"):
            ks_statistic(np.array([0, 1, 2]), np.array([0.1, 0.5, 0.9]))

    def test_perfect_discrimination(self) -> None:
        y_true = np.array([1, 1, 1, 0, 0, 0])
        y_scores = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
        result = ks_statistic(y_true, y_scores)
        assert result["ks_stat"] == 1.0


# =========================================================================
# Finance: gini_coefficient
# =========================================================================


class TestGiniCoefficient:
    """Tests for the Gini coefficient (2*AUC - 1) calculator."""

    def test_happy_path(self, binary_scores: tuple[np.ndarray, np.ndarray]) -> None:
        y_true, y_scores = binary_scores
        result = gini_coefficient(y_true, y_scores)

        assert -1.0 <= result["gini"] <= 1.0
        assert 0.0 <= result["auc"] <= 1.0
        # For a reasonable model, Gini should be positive
        assert result["gini"] > 0
        # Lorenz curve has 21 points (0% to 100% in 5% steps)
        assert len(result["lorenz_curve_data"]) == 21
        assert result["lorenz_curve_data"][0]["population_pct"] == 0.0
        assert result["lorenz_curve_data"][-1]["population_pct"] == 1.0

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="same length"):
            gini_coefficient(np.array([0, 1, 0]), np.array([0.5, 0.6]))

    def test_single_class_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="Both classes"):
            gini_coefficient(np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3]))

    def test_perfect_model_gini(self) -> None:
        y_true = np.array([1, 1, 1, 0, 0, 0])
        y_scores = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
        result = gini_coefficient(y_true, y_scores)
        assert result["auc"] == 1.0
        assert result["gini"] == 1.0

    def test_random_model_gini_near_zero(self) -> None:
        rng = np.random.RandomState(0)
        n = 5000
        y_true = rng.choice([0, 1], n)
        y_scores = rng.uniform(0, 1, n)
        result = gini_coefficient(y_true, y_scores)
        assert abs(result["gini"]) < 0.1


# =========================================================================
# Finance: psi_calculation
# =========================================================================


class TestPsiCalculation:
    """Tests for Population Stability Index."""

    def test_stable_distributions(self) -> None:
        rng = np.random.RandomState(1)
        expected = rng.normal(0.5, 0.1, 1000)
        actual = rng.normal(0.5, 0.1, 1000)
        result = psi_calculation(expected, actual)

        assert result["psi_value"] < 0.1
        assert result["is_stable"] is True
        assert result["stability_label"] == "stable"
        assert len(result["bucket_details"]) == 10

    def test_significant_shift(self) -> None:
        rng = np.random.RandomState(2)
        expected = rng.normal(0.5, 0.1, 1000)
        actual = rng.normal(0.8, 0.15, 1000)  # clearly shifted
        result = psi_calculation(expected, actual)

        assert result["psi_value"] > 0.2
        assert result["is_stable"] is False
        assert result["stability_label"] == "significant_shift"

    def test_empty_expected_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="non-empty"):
            psi_calculation(np.array([]), np.array([1, 2, 3]))

    def test_all_nan_raises(self) -> None:
        with pytest.raises(ToolExecutionError, match="non-empty"):
            psi_calculation(np.array([np.nan]), np.array([1.0]))

    def test_identical_distributions_zero_psi(self) -> None:
        data = np.linspace(0, 1, 500)
        result = psi_calculation(data, data)
        assert result["psi_value"] < 0.001

    def test_custom_bins(self) -> None:
        rng = np.random.RandomState(3)
        expected = rng.normal(0, 1, 500)
        actual = rng.normal(0, 1, 500)
        result = psi_calculation(expected, actual, bins=5)
        assert len(result["bucket_details"]) == 5


# =========================================================================
# E-commerce: rfm_segmentation
# =========================================================================


class TestRfmSegmentation:
    """Tests for RFM (Recency, Frequency, Monetary) segmentation."""

    def test_happy_path(self, transaction_df: pd.DataFrame) -> None:
        result = rfm_segmentation(
            transaction_df,
            customer_col="customer_id",
            date_col="date",
            amount_col="amount",
        )

        assert isinstance(result, pd.DataFrame)
        # Should have one row per unique customer
        assert len(result) == transaction_df["customer_id"].nunique()

        required_columns = [
            "customer_id", "recency_days", "frequency", "monetary",
            "R_score", "F_score", "M_score", "RFM_segment",
        ]
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"

        # Scores should be between 1 and 5
        for score_col in ["R_score", "F_score", "M_score"]:
            assert result[score_col].min() >= 1
            assert result[score_col].max() <= 5

        # RFM_segment should be a 3-digit string
        assert all(len(s) == 3 for s in result["RFM_segment"])

    def test_missing_column_raises(self, transaction_df: pd.DataFrame) -> None:
        with pytest.raises(ToolExecutionError, match="not found"):
            rfm_segmentation(transaction_df, "customer_id", "date", "nonexistent")

    def test_all_unparseable_dates_raises(self) -> None:
        df = pd.DataFrame({
            "cust": ["A", "B"],
            "dt": ["not_a_date", "also_not"],
            "amt": [10, 20],
        })
        with pytest.raises(ToolExecutionError, match="No valid rows"):
            rfm_segmentation(df, "cust", "dt", "amt")

    def test_single_customer(self) -> None:
        df = pd.DataFrame({
            "cust": ["A", "A", "A"],
            "dt": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "amt": [100, 200, 150],
        })
        result = rfm_segmentation(df, "cust", "dt", "amt")
        assert len(result) == 1
        assert result.iloc[0]["frequency"] == 3
        assert result.iloc[0]["monetary"] == 450.0


# =========================================================================
# E-commerce: clv_calculation
# =========================================================================


class TestClvCalculation:
    """Tests for Customer Lifetime Value estimation."""

    def test_happy_path(self, transaction_df: pd.DataFrame) -> None:
        result = clv_calculation(
            transaction_df,
            customer_col="customer_id",
            date_col="date",
            amount_col="amount",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == transaction_df["customer_id"].nunique()

        required_columns = [
            "customer_id", "total_spend", "purchase_count",
            "avg_order_value", "customer_lifespan_days",
            "purchase_frequency", "clv_estimate",
        ]
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"

        # All values should be positive
        assert (result["total_spend"] > 0).all()
        assert (result["purchase_count"] > 0).all()
        assert (result["clv_estimate"] > 0).all()
        # Lifespan clipped to at least 1 day
        assert (result["customer_lifespan_days"] >= 1).all()

    def test_missing_column_raises(self) -> None:
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        with pytest.raises(ToolExecutionError, match="not found"):
            clv_calculation(df, "customer", "date", "amount")

    def test_all_invalid_amounts_raises(self) -> None:
        df = pd.DataFrame({
            "cust": ["A"],
            "dt": ["2024-01-01"],
            "amt": ["not_a_number"],
        })
        with pytest.raises(ToolExecutionError, match="No valid rows"):
            clv_calculation(df, "cust", "dt", "amt")


# =========================================================================
# Manufacturing: oee_calculation
# =========================================================================


class TestOeeCalculation:
    """Tests for Overall Equipment Effectiveness."""

    def test_happy_path(self, oee_df: pd.DataFrame) -> None:
        result = oee_calculation(
            oee_df,
            availability_col="availability",
            performance_col="performance",
            quality_col="quality",
        )

        assert 0.0 <= result["oee"] <= 1.0
        assert 0.0 <= result["availability"] <= 1.0
        assert 0.0 <= result["performance"] <= 1.0
        assert 0.0 <= result["quality"] <= 1.0

        # Losses should sum approximately to 1 - OEE
        losses = result["losses"]
        total_loss = (
            losses["availability_loss"]
            + losses["performance_loss"]
            + losses["quality_loss"]
        )
        assert abs(total_loss - (1.0 - result["oee"])) < 0.05

        assert len(result["oee_per_record"]) == len(oee_df)
        assert result["world_class_benchmark"] == 0.85

    def test_percentage_scale_auto_detection(self) -> None:
        df = pd.DataFrame({
            "avail": [90, 95, 85],
            "perf": [88, 92, 80],
            "qual": [99, 97, 95],
        })
        result = oee_calculation(df, "avail", "perf", "qual")
        # Should auto-convert from 0-100 to 0-1 range
        assert result["availability"] < 1.0
        assert result["oee"] < 1.0

    def test_missing_column_raises(self, oee_df: pd.DataFrame) -> None:
        with pytest.raises(ToolExecutionError, match="not found"):
            oee_calculation(oee_df, "availability", "performance", "missing_col")

    def test_perfect_oee(self) -> None:
        df = pd.DataFrame({
            "a": [1.0, 1.0],
            "p": [1.0, 1.0],
            "q": [1.0, 1.0],
        })
        result = oee_calculation(df, "a", "p", "q")
        assert result["oee"] == 1.0
        assert result["is_world_class"] is True
        assert result["losses"]["availability_loss"] == 0.0


# =========================================================================
# Marketing: campaign_lift
# =========================================================================


class TestCampaignLift:
    """Tests for A/B test campaign lift analysis."""

    def test_happy_path(self, campaign_df: pd.DataFrame) -> None:
        result = campaign_lift(campaign_df, "treatment", "converted")

        assert 0.0 <= result["treatment_rate"] <= 1.0
        assert 0.0 <= result["control_rate"] <= 1.0
        assert result["n_treatment"] == 500
        assert result["n_control"] == 500
        # Treatment group has higher conversion rate by construction
        assert result["absolute_lift"] > 0
        assert result["relative_lift"] > 0
        assert "z_statistic" in result
        assert 0.0 <= result["p_value"] <= 1.0
        assert result["confidence_level"] == 0.95

    def test_missing_column_raises(self) -> None:
        df = pd.DataFrame({"a": [1, 0], "b": [0, 1]})
        with pytest.raises(ToolExecutionError, match="not found"):
            campaign_lift(df, "treatment", "outcome")

    def test_no_control_group_raises(self) -> None:
        df = pd.DataFrame({"treatment": [1, 1, 1], "outcome": [1, 0, 1]})
        with pytest.raises(ToolExecutionError, match="Both treatment and control"):
            campaign_lift(df, "treatment", "outcome")

    def test_no_treatment_group_raises(self) -> None:
        df = pd.DataFrame({"treatment": [0, 0, 0], "outcome": [1, 0, 1]})
        with pytest.raises(ToolExecutionError, match="Both treatment and control"):
            campaign_lift(df, "treatment", "outcome")

    def test_identical_rates_zero_lift(self) -> None:
        df = pd.DataFrame({
            "treatment": [1, 1, 0, 0],
            "outcome": [1, 0, 1, 0],
        })
        result = campaign_lift(df, "treatment", "outcome")
        assert result["absolute_lift"] == 0.0

    def test_significance_detection(self) -> None:
        """Large sample with clear effect should be significant."""
        rng = np.random.RandomState(777)
        n = 5000
        treatment = np.array([1] * (n // 2) + [0] * (n // 2))
        outcome = np.where(
            treatment == 1,
            rng.binomial(1, 0.20, n),
            rng.binomial(1, 0.10, n),
        )
        df = pd.DataFrame({"t": treatment, "o": outcome})
        result = campaign_lift(df, "t", "o")
        assert result["is_significant"] is True
        assert result["p_value"] < 0.05
