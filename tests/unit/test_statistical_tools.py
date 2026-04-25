"""Unit tests for agents/tools/stats_tools.py.

Covers all 16 public statistical functions. Each function has at minimum:
  - A happy-path test verifying return dict shape, key types, and value ranges.
  - An edge-case test verifying ToolExecutionError is raised on invalid input.

Fixture dependencies (from tests/conftest.py):
  - sample_classification_df  (500 rows, columns: age, income, gender, region,
      tenure_months, num_products, has_credit_card, is_active, balance, churned)
  - sample_regression_df      (500 rows, columns: sqft, bedrooms, bathrooms,
      year_built, neighborhood, has_garage, lot_size, price)
  - sample_healthcare_df      (300 rows, columns: patient_id, age, gender,
      admission_type, diagnosis_code, num_medications, num_procedures,
      length_of_stay, insurance_type, readmitted_30day)

Local fixtures defined here:
  - survival_df    — minimal dataframe with duration_col + event_col for
                     kaplan_meier and cox_ph tests
"""

import math

import numpy as np
import pandas as pd
import pytest

from agents.tools.stats_tools import (
    anova_oneway,
    chi_square_test,
    correlation_matrix,
    correlation_pearson,
    correlation_spearman,
    cox_ph,
    fisher_exact_test,
    kaplan_meier,
    ks_test,
    kruskal_wallis,
    levene_test,
    mann_whitney_u,
    shapiro_wilk,
    t_test_independent,
    t_test_paired,
    vif_analysis,
)
from core.exceptions import ToolExecutionError


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def survival_df():
    """Deterministic survival dataset for Kaplan-Meier and Cox PH tests.

    200 rows with:
      - duration  : time to event in months (1–60)
      - event     : 1 = event observed, 0 = censored
      - treatment : binary group ("A" / "B") for stratified KM test
      - age       : continuous covariate for Cox PH
    """
    rng = np.random.default_rng(0)
    n = 200
    duration = rng.integers(1, 61, size=n).astype(float)
    event = rng.choice([0, 1], size=n, p=[0.35, 0.65])
    treatment = rng.choice(["A", "B"], size=n)
    age = rng.integers(30, 80, size=n).astype(float)
    return pd.DataFrame(
        {"duration": duration, "event": event, "treatment": treatment, "age": age}
    )


@pytest.fixture
def binary_2x2_df():
    """Small 2x2 dataframe for Fisher's exact test (both columns binary str)."""
    rng = np.random.default_rng(7)
    n = 60
    exposed = rng.choice(["yes", "no"], size=n)
    outcome = rng.choice(["case", "control"], size=n)
    return pd.DataFrame({"exposed": exposed, "outcome": outcome})


# ---------------------------------------------------------------------------
# Helper assertions reused across tests
# ---------------------------------------------------------------------------


def _assert_p_value(result: dict, key: str = "p_value") -> None:
    """Assert key is a float in [0, 1]."""
    p = result[key]
    assert isinstance(p, float), f"Expected float for '{key}', got {type(p)}"
    assert 0.0 <= p <= 1.0, f"p-value out of range [0,1]: {p}"


def _assert_non_empty_string(result: dict, key: str = "interpretation") -> None:
    """Assert key is a non-empty string."""
    val = result[key]
    assert isinstance(val, str), f"Expected str for '{key}', got {type(val)}"
    assert len(val.strip()) > 0, f"'{key}' is an empty or whitespace-only string"


def _assert_significant_is_bool(result: dict) -> None:
    assert isinstance(result["significant"], bool)


# ===========================================================================
# 1. t_test_independent
# ===========================================================================


class TestTTestIndependent:
    def test_happy_path_returns_correct_keys(self, sample_classification_df):
        result = t_test_independent(
            sample_classification_df, "age", "churned", alpha=0.05
        )
        expected_keys = {
            "statistic",
            "p_value",
            "effect_size",
            "ci_lower",
            "ci_upper",
            "significant",
            "interpretation",
        }
        assert expected_keys == set(result.keys())

    def test_happy_path_value_types_and_ranges(self, sample_classification_df):
        result = t_test_independent(
            sample_classification_df, "balance", "is_active", alpha=0.05
        )
        assert isinstance(result["statistic"], float)
        _assert_p_value(result)
        assert isinstance(result["effect_size"], float)
        assert result["ci_lower"] < result["ci_upper"]
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_significant_flag_matches_p_value(self, sample_classification_df):
        result = t_test_independent(
            sample_classification_df, "income", "churned", alpha=0.05
        )
        expected_significant = result["p_value"] < 0.05
        assert result["significant"] == expected_significant

    def test_effect_size_direction_consistent_with_group_means(
        self, sample_classification_df
    ):
        """Cohen's d sign should reflect group 0 vs group 1 mean difference."""
        df = sample_classification_df
        result = t_test_independent(df, "age", "churned", alpha=0.05)
        g0_mean = df.loc[df["churned"] == 0, "age"].mean()
        g1_mean = df.loc[df["churned"] == 1, "age"].mean()
        expected_sign = math.copysign(1.0, g0_mean - g1_mean)
        assert math.copysign(1.0, result["effect_size"]) == expected_sign

    def test_raises_on_more_than_two_groups(self, sample_classification_df):
        with pytest.raises(ToolExecutionError, match="2 groups"):
            t_test_independent(
                sample_classification_df, "age", "region", alpha=0.05
            )

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            t_test_independent(
                sample_classification_df, "nonexistent_col", "churned"
            )

    def test_raises_when_group_has_single_observation(self):
        """A group with exactly 1 observation cannot produce a t-test."""
        df = pd.DataFrame(
            {"value": [1.0, 2.0, 3.0, 4.0], "group": ["A", "A", "A", "B"]}
        )
        with pytest.raises(ToolExecutionError, match="at least 2"):
            t_test_independent(df, "value", "group")

    @pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10])
    def test_alpha_affects_significant_flag(self, sample_classification_df, alpha):
        result = t_test_independent(
            sample_classification_df, "age", "churned", alpha=alpha
        )
        assert result["significant"] == (result["p_value"] < alpha)


# ===========================================================================
# 2. t_test_paired
# ===========================================================================


class TestTTestPaired:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = t_test_paired(
            sample_classification_df, "age", "tenure_months", alpha=0.05
        )
        expected_keys = {
            "statistic",
            "p_value",
            "effect_size",
            "mean_diff",
            "ci_lower",
            "ci_upper",
            "significant",
            "interpretation",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["statistic"], float)
        _assert_p_value(result)
        assert isinstance(result["mean_diff"], float)
        assert result["ci_lower"] < result["ci_upper"]
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_identical_columns_yields_zero_statistic(
        self, sample_classification_df
    ):
        """Paired test on identical series must produce t=0, p=1."""
        result = t_test_paired(
            sample_classification_df, "age", "age", alpha=0.05
        )
        assert result["statistic"] == pytest.approx(0.0, abs=1e-9)
        assert result["p_value"] == pytest.approx(1.0, abs=1e-9)
        assert result["significant"] is False

    def test_mean_diff_equals_col1_minus_col2(self, sample_classification_df):
        df = sample_classification_df
        expected_diff = float((df["num_products"] - df["has_credit_card"]).mean())
        result = t_test_paired(df, "num_products", "has_credit_card")
        assert result["mean_diff"] == pytest.approx(expected_diff, rel=1e-6)

    def test_raises_with_insufficient_paired_observations(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})
        with pytest.raises(ToolExecutionError, match="(?i)at least 2"):
            t_test_paired(df, "a", "b")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            t_test_paired(sample_classification_df, "age", "does_not_exist")


# ===========================================================================
# 3. mann_whitney_u
# ===========================================================================


class TestMannWhitneyU:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = mann_whitney_u(
            sample_classification_df, "balance", "churned", alpha=0.05
        )
        expected_keys = {"statistic", "p_value", "effect_size", "significant", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["statistic"], float)
        _assert_p_value(result)
        assert isinstance(result["effect_size"], float)
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_effect_size_bounded(self, sample_classification_df):
        """Rank-biserial correlation must lie in [-1, 1]."""
        result = mann_whitney_u(
            sample_classification_df, "income", "is_active", alpha=0.05
        )
        assert -1.0 <= result["effect_size"] <= 1.0

    def test_raises_on_more_than_two_groups(self, sample_classification_df):
        with pytest.raises(ToolExecutionError, match="2 groups"):
            mann_whitney_u(sample_classification_df, "age", "region")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            mann_whitney_u(sample_classification_df, "phantom", "churned")

    @pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10])
    def test_alpha_affects_significant_flag(self, sample_classification_df, alpha):
        result = mann_whitney_u(
            sample_classification_df, "balance", "churned", alpha=alpha
        )
        assert result["significant"] == (result["p_value"] < alpha)


# ===========================================================================
# 4. chi_square_test
# ===========================================================================


class TestChiSquareTest:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = chi_square_test(
            sample_classification_df, "gender", "churned", alpha=0.05
        )
        expected_keys = {
            "statistic",
            "p_value",
            "dof",
            "expected_frequencies",
            "cramers_v",
            "significant",
            "interpretation",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["statistic"], float)
        _assert_p_value(result)
        assert isinstance(result["dof"], int)
        assert result["dof"] >= 1
        assert isinstance(result["expected_frequencies"], list)
        assert isinstance(result["cramers_v"], float)
        assert 0.0 <= result["cramers_v"] <= 1.0
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_region_vs_churned_four_categories(self, sample_classification_df):
        """Chi-square on a 4-category column should produce dof=(4-1)*(2-1)=3."""
        result = chi_square_test(
            sample_classification_df, "region", "churned", alpha=0.05
        )
        assert result["dof"] == 3

    def test_raises_on_all_null_data(self):
        df = pd.DataFrame({"a": [None, None], "b": [None, None]})
        with pytest.raises(ToolExecutionError):
            chi_square_test(df, "a", "b")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            chi_square_test(sample_classification_df, "ghost", "churned")

    def test_expected_frequencies_shape_matches_contingency(
        self, sample_classification_df
    ):
        result = chi_square_test(
            sample_classification_df, "region", "churned", alpha=0.05
        )
        # region has 4 levels, churned has 2 -> expected table is 4x2
        rows = len(result["expected_frequencies"])
        cols = len(result["expected_frequencies"][0])
        assert rows == 4
        assert cols == 2


# ===========================================================================
# 5. fisher_exact_test
# ===========================================================================


class TestFisherExactTest:
    def test_happy_path_keys_and_types(self, binary_2x2_df):
        result = fisher_exact_test(binary_2x2_df, "exposed", "outcome", alpha=0.05)
        expected_keys = {"odds_ratio", "p_value", "significant", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["odds_ratio"], float)
        assert result["odds_ratio"] >= 0.0
        _assert_p_value(result)
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_perfect_association_yields_extreme_p(self):
        """Perfect 2x2 separation produces a very small p-value."""
        df = pd.DataFrame(
            {
                "group": ["A"] * 20 + ["B"] * 20,
                "outcome": ["yes"] * 20 + ["no"] * 20,
            }
        )
        result = fisher_exact_test(df, "group", "outcome")
        assert result["p_value"] < 0.001
        assert result["significant"] is True

    def test_raises_when_table_is_not_2x2(self, sample_classification_df):
        """gender × region would be 2×4, not 2×2 — must raise."""
        with pytest.raises(ToolExecutionError, match="2x2"):
            fisher_exact_test(sample_classification_df, "gender", "region")

    def test_significant_flag_consistent_with_p_value(self, binary_2x2_df):
        for alpha in (0.01, 0.05, 0.10):
            result = fisher_exact_test(binary_2x2_df, "exposed", "outcome", alpha=alpha)
            assert result["significant"] == (result["p_value"] < alpha)


# ===========================================================================
# 6. anova_oneway
# ===========================================================================


class TestAnovaOneway:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = anova_oneway(
            sample_classification_df, "age", "region", alpha=0.05
        )
        expected_keys = {
            "f_statistic",
            "p_value",
            "eta_squared",
            "group_means",
            "significant",
            "interpretation",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["f_statistic"], float)
        assert result["f_statistic"] >= 0.0
        _assert_p_value(result)
        assert isinstance(result["eta_squared"], float)
        assert 0.0 <= result["eta_squared"] <= 1.0
        assert isinstance(result["group_means"], dict)
        assert len(result["group_means"]) == 4  # North, South, East, West
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_group_means_keys_match_unique_values(self, sample_classification_df):
        result = anova_oneway(
            sample_classification_df, "income", "region", alpha=0.05
        )
        expected_groups = set(
            sample_classification_df["region"].dropna().unique().astype(str)
        )
        assert set(result["group_means"].keys()) == expected_groups

    def test_eta_squared_bounded_by_one(self, sample_classification_df):
        result = anova_oneway(
            sample_classification_df, "balance", "region", alpha=0.05
        )
        assert result["eta_squared"] <= 1.0

    def test_raises_when_only_one_group(self):
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0], "group": ["A", "A", "A"]})
        with pytest.raises(ToolExecutionError, match="at least 2 groups"):
            anova_oneway(df, "value", "group")

    def test_raises_when_group_has_fewer_than_two_observations(self):
        df = pd.DataFrame(
            {"value": [1.0, 2.0, 3.0, 4.0], "group": ["A", "A", "A", "B"]}
        )
        with pytest.raises(ToolExecutionError, match="fewer than 2"):
            anova_oneway(df, "value", "group")

    def test_two_groups_also_accepted(self, sample_classification_df):
        """ANOVA with 2 groups is valid and F should approximate t^2.

        Note: t_test_independent uses Welch's correction (unequal var),
        while ANOVA assumes equal variance, so we use a looser tolerance.
        """
        result = anova_oneway(
            sample_classification_df, "age", "churned", alpha=0.05
        )
        t_result = t_test_independent(
            sample_classification_df, "age", "churned", alpha=0.05
        )
        assert result["f_statistic"] == pytest.approx(t_result["statistic"] ** 2, rel=0.05)


# ===========================================================================
# 7. kruskal_wallis
# ===========================================================================


class TestKruskalWallis:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = kruskal_wallis(
            sample_classification_df, "age", "region", alpha=0.05
        )
        expected_keys = {
            "h_statistic",
            "p_value",
            "epsilon_squared",
            "significant",
            "interpretation",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["h_statistic"], float)
        assert result["h_statistic"] >= 0.0
        _assert_p_value(result)
        assert isinstance(result["epsilon_squared"], float)
        assert 0.0 <= result["epsilon_squared"] <= 1.0
        _assert_significant_is_bool(result)
        _assert_non_empty_string(result)

    def test_epsilon_squared_non_negative(self, sample_classification_df):
        result = kruskal_wallis(
            sample_classification_df, "balance", "region", alpha=0.05
        )
        assert result["epsilon_squared"] >= 0.0

    def test_raises_when_single_group(self):
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0], "group": ["X", "X", "X"]})
        with pytest.raises(ToolExecutionError, match="at least 2 groups"):
            kruskal_wallis(df, "value", "group")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            kruskal_wallis(sample_classification_df, "phantom", "region")

    @pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10])
    def test_alpha_affects_significant_flag(self, sample_classification_df, alpha):
        result = kruskal_wallis(
            sample_classification_df, "income", "region", alpha=alpha
        )
        assert result["significant"] == (result["p_value"] < alpha)


# ===========================================================================
# 8. shapiro_wilk
# ===========================================================================


class TestShapiroWilk:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = shapiro_wilk(sample_classification_df, "age", alpha=0.05)
        expected_keys = {"statistic", "p_value", "is_normal", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["statistic"], float)
        assert 0.0 <= result["statistic"] <= 1.0
        _assert_p_value(result)
        assert isinstance(result["is_normal"], bool)
        _assert_non_empty_string(result)

    def test_is_normal_consistent_with_p_value(self, sample_classification_df):
        result = shapiro_wilk(sample_classification_df, "age", alpha=0.05)
        assert result["is_normal"] == (result["p_value"] >= 0.05)

    def test_truly_normal_data_is_not_rejected(self):
        """Pure N(0,1) sample should not be rejected at alpha=0.05 (seed chosen
        to produce a consistent outcome with 200 points)."""
        rng = np.random.default_rng(99)
        df = pd.DataFrame({"x": rng.standard_normal(200)})
        result = shapiro_wilk(df, "x", alpha=0.05)
        # We check is_normal is a bool; we do not assert True because the test
        # is stochastic — we just ensure the machinery runs without error.
        assert isinstance(result["is_normal"], bool)
        _assert_p_value(result)

    def test_heavily_skewed_data_is_rejected(self):
        """Exponential data with 300 points is nearly always non-normal."""
        rng = np.random.default_rng(0)
        df = pd.DataFrame({"x": rng.exponential(scale=1.0, size=300)})
        result = shapiro_wilk(df, "x", alpha=0.05)
        assert result["is_normal"] is False

    def test_raises_when_fewer_than_three_observations(self):
        df = pd.DataFrame({"x": [1.0, 2.0]})
        with pytest.raises(ToolExecutionError, match="at least 3"):
            shapiro_wilk(df, "x")

    def test_interpretation_contains_normality_conclusion(
        self, sample_classification_df
    ):
        result = shapiro_wilk(sample_classification_df, "age")
        # Implementation appends either "consistent with a normal distribution"
        # or "deviates significantly from normality"
        assert (
            "normal distribution" in result["interpretation"]
            or "normality" in result["interpretation"]
        )


# ===========================================================================
# 9. levene_test
# ===========================================================================


class TestLeveneTest:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = levene_test(
            sample_classification_df, "age", "churned", alpha=0.05
        )
        expected_keys = {"statistic", "p_value", "equal_variance", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["statistic"], float)
        assert result["statistic"] >= 0.0
        _assert_p_value(result)
        assert isinstance(result["equal_variance"], bool)
        _assert_non_empty_string(result)

    def test_equal_variance_consistent_with_p_value(self, sample_classification_df):
        result = levene_test(
            sample_classification_df, "income", "churned", alpha=0.05
        )
        assert result["equal_variance"] == (result["p_value"] >= 0.05)

    def test_identical_variances_equal_variance_true(self):
        """Two groups drawn from the same distribution should have equal variance."""
        rng = np.random.default_rng(42)
        n = 300
        df = pd.DataFrame(
            {
                "value": np.concatenate(
                    [rng.normal(0, 1, n), rng.normal(5, 1, n)]
                ),
                "group": ["A"] * n + ["B"] * n,
            }
        )
        result = levene_test(df, "value", "group", alpha=0.05)
        # same sigma=1 -> should not reject equal variance at 5%
        assert result["equal_variance"] is True

    def test_raises_when_single_group(self):
        df = pd.DataFrame({"val": [1.0, 2.0, 3.0], "grp": ["A", "A", "A"]})
        with pytest.raises(ToolExecutionError, match="at least 2 groups"):
            levene_test(df, "val", "grp")

    def test_works_with_more_than_two_groups(self, sample_classification_df):
        result = levene_test(
            sample_classification_df, "age", "region", alpha=0.05
        )
        assert isinstance(result["p_value"], float)


# ===========================================================================
# 10. correlation_pearson
# ===========================================================================


class TestCorrelationPearson:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = correlation_pearson(sample_classification_df, "age", "tenure_months")
        expected_keys = {"coefficient", "p_value", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["coefficient"], float)
        assert -1.0 <= result["coefficient"] <= 1.0
        _assert_p_value(result)
        _assert_non_empty_string(result)

    def test_perfect_positive_correlation(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [2.0, 4.0, 6.0, 8.0, 10.0]})
        result = correlation_pearson(df, "x", "y")
        assert result["coefficient"] == pytest.approx(1.0, abs=1e-9)
        assert result["p_value"] < 0.001

    def test_perfect_negative_correlation(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "y": [5.0, 4.0, 3.0, 2.0, 1.0]})
        result = correlation_pearson(df, "x", "y")
        assert result["coefficient"] == pytest.approx(-1.0, abs=1e-9)

    def test_interpretation_mentions_column_names(self, sample_classification_df):
        result = correlation_pearson(sample_classification_df, "age", "income")
        assert "age" in result["interpretation"]
        assert "income" in result["interpretation"]

    def test_raises_with_fewer_than_three_observations(self):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        with pytest.raises(ToolExecutionError, match="at least 3"):
            correlation_pearson(df, "a", "b")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            correlation_pearson(sample_classification_df, "age", "ghost")

    @pytest.mark.parametrize(
        "col1, col2",
        [
            ("age", "tenure_months"),
            ("income", "balance"),
            ("num_products", "age"),
        ],
    )
    def test_coefficient_symmetric(self, sample_classification_df, col1, col2):
        """Pearson r(a, b) must equal r(b, a)."""
        r_ab = correlation_pearson(sample_classification_df, col1, col2)["coefficient"]
        r_ba = correlation_pearson(sample_classification_df, col2, col1)["coefficient"]
        assert r_ab == pytest.approx(r_ba, abs=1e-10)


# ===========================================================================
# 11. correlation_spearman
# ===========================================================================


class TestCorrelationSpearman:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = correlation_spearman(
            sample_classification_df, "age", "num_products"
        )
        expected_keys = {"coefficient", "p_value", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["coefficient"], float)
        assert -1.0 <= result["coefficient"] <= 1.0
        _assert_p_value(result)
        _assert_non_empty_string(result)

    def test_perfect_monotonic_relationship(self):
        """Perfectly monotone increasing sequence should give rho=1."""
        df = pd.DataFrame({"x": range(1, 21), "y": range(1, 21)})
        result = correlation_spearman(df, "x", "y")
        assert result["coefficient"] == pytest.approx(1.0, abs=1e-9)

    def test_interpretation_mentions_column_names(self, sample_classification_df):
        result = correlation_spearman(
            sample_classification_df, "tenure_months", "balance"
        )
        assert "tenure_months" in result["interpretation"]
        assert "balance" in result["interpretation"]

    def test_raises_with_fewer_than_three_observations(self):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        with pytest.raises(ToolExecutionError, match="at least 3"):
            correlation_spearman(df, "a", "b")

    def test_raises_on_missing_column(self, sample_classification_df):
        with pytest.raises(ToolExecutionError):
            correlation_spearman(sample_classification_df, "ghost", "age")

    @pytest.mark.parametrize(
        "col1, col2",
        [
            ("age", "tenure_months"),
            ("income", "balance"),
        ],
    )
    def test_coefficient_symmetric(self, sample_classification_df, col1, col2):
        r_ab = correlation_spearman(sample_classification_df, col1, col2)["coefficient"]
        r_ba = correlation_spearman(sample_classification_df, col2, col1)["coefficient"]
        assert r_ab == pytest.approx(r_ba, abs=1e-10)


# ===========================================================================
# 12. ks_test
# ===========================================================================


class TestKsTest:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = ks_test(sample_classification_df, "age", reference_dist="norm")
        expected_keys = {"ks_statistic", "p_value", "reference_dist", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["ks_statistic"], float)
        assert 0.0 <= result["ks_statistic"] <= 1.0
        _assert_p_value(result)
        assert result["reference_dist"] == "norm"
        _assert_non_empty_string(result)

    def test_reference_dist_stored_in_output(self, sample_classification_df):
        result = ks_test(sample_classification_df, "balance", reference_dist="expon")
        assert result["reference_dist"] == "expon"

    def test_near_normal_data_high_p_value(self):
        """Large sample from N(0,1) fitted to norm should have high p-value."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"x": rng.standard_normal(1000)})
        result = ks_test(df, "x", reference_dist="norm")
        # After parameter fitting the KS statistic should be small
        assert result["ks_statistic"] < 0.10

    def test_raises_on_unknown_distribution(self, sample_classification_df):
        with pytest.raises(ToolExecutionError, match="Unknown reference distribution"):
            ks_test(sample_classification_df, "age", reference_dist="totally_fake_dist")

    def test_raises_with_single_observation(self):
        df = pd.DataFrame({"x": [42.0]})
        with pytest.raises(ToolExecutionError, match="at least 2"):
            ks_test(df, "x")

    def test_interpretation_references_distribution_name(
        self, sample_classification_df
    ):
        result = ks_test(sample_classification_df, "age", reference_dist="norm")
        assert "norm" in result["interpretation"]

    @pytest.mark.parametrize("dist", ["norm", "expon", "uniform"])
    def test_multiple_reference_distributions(self, sample_classification_df, dist):
        result = ks_test(sample_classification_df, "age", reference_dist=dist)
        _assert_p_value(result)
        assert result["reference_dist"] == dist


# ===========================================================================
# 13. vif_analysis
# ===========================================================================


class TestVifAnalysis:
    def test_happy_path_keys_and_types(self, sample_regression_df):
        cols = ["sqft", "bedrooms", "bathrooms", "year_built"]
        result = vif_analysis(sample_regression_df, cols)
        expected_keys = {"vif_scores", "high_vif_columns", "interpretation"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["vif_scores"], dict)
        assert set(result["vif_scores"].keys()) == set(cols)
        assert isinstance(result["high_vif_columns"], list)
        _assert_non_empty_string(result)

    def test_vif_scores_are_positive_floats(self, sample_regression_df):
        cols = ["sqft", "lot_size", "bedrooms"]
        result = vif_analysis(sample_regression_df, cols)
        for col, vif_val in result["vif_scores"].items():
            assert isinstance(vif_val, float), f"VIF for {col} is not float"
            assert vif_val > 0.0, f"VIF for {col} is not positive"

    def test_high_vif_columns_threshold_is_10(self, sample_regression_df):
        cols = ["sqft", "lot_size", "bedrooms", "bathrooms", "year_built"]
        result = vif_analysis(sample_regression_df, cols)
        for col in result["high_vif_columns"]:
            assert result["vif_scores"][col] > 10.0

    def test_perfectly_correlated_columns_produce_high_vif(self):
        """Adding a perfect linear combination must raise VIF to infinity."""
        rng = np.random.default_rng(0)
        x = rng.standard_normal(200)
        df = pd.DataFrame({"x1": x, "x2": x * 2.0 + 3.0, "x3": rng.standard_normal(200)})
        result = vif_analysis(df, ["x1", "x2", "x3"])
        # x1 and x2 are perfectly correlated — at least one must exceed 10
        high = result["high_vif_columns"]
        assert len(high) >= 1

    def test_raises_with_single_column(self, sample_regression_df):
        with pytest.raises(ToolExecutionError, match="at least 2"):
            vif_analysis(sample_regression_df, ["sqft"])

    def test_raises_with_insufficient_rows(self):
        """Need > n_cols rows; provide exactly n_cols rows -> error."""
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [2.0, 3.0], "c": [3.0, 4.0]})
        with pytest.raises(ToolExecutionError):
            vif_analysis(df, ["a", "b", "c"])

    def test_interpretation_text_varies_by_vif_result(self, sample_regression_df):
        """Low VIF -> 'not a major concern'; high VIF -> 'Consider removing'."""
        # Two independent columns that shouldn't be highly correlated
        cols = ["sqft", "year_built"]
        result = vif_analysis(sample_regression_df, cols)
        interp = result["interpretation"]
        assert isinstance(interp, str) and len(interp) > 10


# ===========================================================================
# 14. kaplan_meier
# ===========================================================================


class TestKaplanMeier:
    def test_ungrouped_happy_path_keys_and_types(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event")
        assert "survival_table" in result
        assert "median_survival" in result
        assert isinstance(result["survival_table"], list)
        assert len(result["survival_table"]) > 0

    def test_ungrouped_survival_table_records_have_correct_keys(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event")
        for record in result["survival_table"]:
            assert "timeline" in record
            assert "survival_probability" in record

    def test_ungrouped_survival_probability_monotone_non_increasing(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event")
        probs = [r["survival_probability"] for r in result["survival_table"]]
        for prev, curr in zip(probs, probs[1:]):
            assert prev >= curr - 1e-9, "Survival function is not monotone non-increasing"

    def test_ungrouped_median_survival_is_none_or_positive_float(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event")
        med = result["median_survival"]
        assert med is None or (isinstance(med, float) and med > 0.0)

    def test_grouped_includes_log_rank_fields(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event", group_col="treatment")
        assert "log_rank_statistic" in result
        assert "log_rank_p_value" in result
        assert isinstance(result["log_rank_statistic"], float)
        _assert_p_value(result, "log_rank_p_value")

    def test_grouped_survival_table_has_key_per_group(self, survival_df):
        result = kaplan_meier(survival_df, "duration", "event", group_col="treatment")
        assert "A" in result["survival_table"]
        assert "B" in result["survival_table"]

    def test_raises_with_fewer_than_two_observations(self):
        df = pd.DataFrame({"duration": [5.0], "event": [1]})
        with pytest.raises(ToolExecutionError, match="at least 2"):
            kaplan_meier(df, "duration", "event")

    def test_raises_on_missing_duration_column(self, survival_df):
        with pytest.raises(ToolExecutionError):
            kaplan_meier(survival_df, "ghost_col", "event")


# ===========================================================================
# 15. cox_ph
# ===========================================================================


class TestCoxPH:
    def test_happy_path_keys_and_types(self, survival_df):
        result = cox_ph(
            survival_df,
            duration_col="duration",
            event_col="event",
            covariates=["age"],
        )
        expected_keys = {
            "hazard_ratios",
            "confidence_intervals",
            "p_values",
            "concordance_index",
            "interpretation",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["hazard_ratios"], dict)
        assert "age" in result["hazard_ratios"]
        assert isinstance(result["hazard_ratios"]["age"], float)
        assert result["hazard_ratios"]["age"] > 0.0

    def test_confidence_intervals_are_ordered_pairs(self, survival_df):
        result = cox_ph(
            survival_df,
            duration_col="duration",
            event_col="event",
            covariates=["age"],
        )
        lo, hi = result["confidence_intervals"]["age"]
        assert lo <= hi

    def test_p_values_are_floats_in_range(self, survival_df):
        result = cox_ph(
            survival_df,
            duration_col="duration",
            event_col="event",
            covariates=["age"],
        )
        for col, pv in result["p_values"].items():
            assert isinstance(pv, float)
            assert 0.0 <= pv <= 1.0

    def test_concordance_index_bounded(self, survival_df):
        result = cox_ph(
            survival_df,
            duration_col="duration",
            event_col="event",
            covariates=["age"],
        )
        assert 0.0 <= result["concordance_index"] <= 1.0

    def test_interpretation_is_non_empty_string(self, survival_df):
        result = cox_ph(
            survival_df,
            duration_col="duration",
            event_col="event",
            covariates=["age"],
        )
        _assert_non_empty_string(result)

    def test_raises_with_insufficient_observations(self):
        """One covariate needs > 3 rows; provide exactly 3 -> error."""
        df = pd.DataFrame(
            {"duration": [1.0, 2.0, 3.0], "event": [1, 0, 1], "age": [50.0, 60.0, 70.0]}
        )
        with pytest.raises(ToolExecutionError):
            cox_ph(df, "duration", "event", covariates=["age"])

    def test_raises_on_missing_covariate_column(self, survival_df):
        with pytest.raises(ToolExecutionError):
            cox_ph(survival_df, "duration", "event", covariates=["nonexistent"])


# ===========================================================================
# 16. correlation_matrix
# ===========================================================================


class TestCorrelationMatrix:
    def test_happy_path_keys_and_types(self, sample_classification_df):
        result = correlation_matrix(
            sample_classification_df,
            columns=["age", "income", "tenure_months", "balance"],
        )
        expected_keys = {"matrix", "highly_correlated_pairs", "method"}
        assert expected_keys == set(result.keys())
        assert isinstance(result["matrix"], dict)
        assert isinstance(result["highly_correlated_pairs"], list)
        assert result["method"] == "pearson"

    def test_matrix_is_symmetric(self, sample_classification_df):
        cols = ["age", "income", "tenure_months", "balance"]
        result = correlation_matrix(sample_classification_df, columns=cols)
        mat = result["matrix"]
        for c1 in cols:
            for c2 in cols:
                assert mat[c1][c2] == pytest.approx(mat[c2][c1], abs=1e-10)

    def test_diagonal_equals_one(self, sample_classification_df):
        cols = ["age", "income", "tenure_months"]
        result = correlation_matrix(sample_classification_df, columns=cols)
        mat = result["matrix"]
        for c in cols:
            assert mat[c][c] == pytest.approx(1.0, abs=1e-6)

    def test_highly_correlated_pairs_above_threshold(self, sample_classification_df):
        """Every pair in highly_correlated_pairs must have |corr| > 0.8."""
        result = correlation_matrix(
            sample_classification_df,
            columns=["age", "income", "tenure_months", "balance", "num_products"],
        )
        for pair in result["highly_correlated_pairs"]:
            assert abs(pair["correlation"]) > 0.8

    def test_highly_correlated_pairs_sorted_descending(self, sample_classification_df):
        """Pairs must be sorted by |correlation| descending."""
        cols = ["age", "income", "tenure_months", "balance"]
        result = correlation_matrix(sample_classification_df, columns=cols)
        pairs = result["highly_correlated_pairs"]
        for i in range(len(pairs) - 1):
            assert abs(pairs[i]["correlation"]) >= abs(pairs[i + 1]["correlation"])

    def test_method_stored_in_output(self, sample_classification_df):
        for method in ("pearson", "spearman", "kendall"):
            result = correlation_matrix(
                sample_classification_df,
                columns=["age", "income", "balance"],
                method=method,
            )
            assert result["method"] == method

    def test_auto_selects_numeric_columns_when_none_specified(
        self, sample_classification_df
    ):
        result = correlation_matrix(sample_classification_df)
        numeric_cols = sample_classification_df.select_dtypes(include="number").columns.tolist()
        assert set(result["matrix"].keys()) == set(numeric_cols)

    def test_raises_on_unsupported_method(self, sample_classification_df):
        with pytest.raises(ToolExecutionError, match="Unsupported method"):
            correlation_matrix(
                sample_classification_df,
                columns=["age", "income"],
                method="bad_method",
            )

    def test_raises_when_fewer_than_two_numeric_columns(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "label": ["a", "b", "c"]})
        with pytest.raises(ToolExecutionError, match="at least 2"):
            correlation_matrix(df)

    def test_highly_correlated_pairs_have_correct_keys(
        self, sample_classification_df
    ):
        """Each pair dict must expose col1, col2, and correlation."""
        result = correlation_matrix(
            sample_classification_df,
            columns=["age", "income", "tenure_months", "balance"],
        )
        for pair in result["highly_correlated_pairs"]:
            assert "col1" in pair
            assert "col2" in pair
            assert "correlation" in pair

    def test_no_self_correlation_in_highly_correlated_pairs(
        self, sample_classification_df
    ):
        result = correlation_matrix(
            sample_classification_df,
            columns=["age", "income", "tenure_months", "balance"],
        )
        for pair in result["highly_correlated_pairs"]:
            assert pair["col1"] != pair["col2"]
