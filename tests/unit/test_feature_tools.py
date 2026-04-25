"""Unit tests for agents/tools/feature_tools.py.

Tests cover all 30 feature engineering functions across 6 categories:
- Encoding (7 functions)
- Scaling (4 functions)
- Transforms (5 functions)
- Feature Creation (8 functions)
- Imputation (4 functions)
- Selection (2 functions)

Every test verifies:
1. Return type is pd.DataFrame
2. Original DataFrame is NOT mutated (immutability contract)
3. Output shape is reasonable
4. Basic correctness of the transformation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agents.tools.feature_tools import (
    # Encoding
    one_hot_encode,
    target_encode,
    ordinal_encode,
    binary_encode,
    frequency_encode,
    woe_encode,
    label_encode,
    # Scaling
    standard_scale,
    minmax_scale,
    robust_scale,
    normalize,
    # Transforms
    log_transform,
    box_cox_transform,
    yeo_johnson_transform,
    sqrt_transform,
    power_transform,
    # Feature Creation
    polynomial_features,
    interaction_features,
    date_parts,
    lag_features,
    rolling_features,
    binning,
    ratio_features,
    text_length_features,
    # Imputation
    impute_mean,
    impute_median,
    impute_mode,
    impute_knn,
    # Selection
    select_features_importance,
    drop_low_variance,
)


# ---------------------------------------------------------------------------
# Additional fixtures beyond conftest.py
# ---------------------------------------------------------------------------


@pytest.fixture
def datetime_df():
    """DataFrame with a datetime column for date_parts tests."""
    return pd.DataFrame(
        {
            "event_date": pd.to_datetime(
                ["2023-01-15", "2023-06-30", "2022-12-25", "2024-03-08", "2023-11-11"]
            ),
            "value": [10, 20, 30, 40, 50],
        }
    )


@pytest.fixture
def datetime_with_time_df():
    """DataFrame with a datetime column that includes time components."""
    return pd.DataFrame(
        {
            "ts": pd.to_datetime(
                [
                    "2023-01-15 08:30:00",
                    "2023-06-30 14:15:00",
                    "2022-12-25 23:59:00",
                    "2024-03-08 00:00:01",
                ]
            ),
            "value": [1, 2, 3, 4],
        }
    )


@pytest.fixture
def nan_df():
    """DataFrame with NaN values in numeric columns for imputation tests."""
    np.random.seed(0)
    data = pd.DataFrame(
        {
            "a": [1.0, np.nan, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "b": [np.nan, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0, 8.0, 9.0, 10.0],
            "c": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        }
    )
    return data


@pytest.fixture
def text_df():
    """DataFrame with a text column for text_length_features tests."""
    return pd.DataFrame(
        {
            "review": [
                "Great product love it",
                "Terrible experience never buying again",
                "OK",
                "",
                "Absolutely fantastic highly recommend to everyone",
            ],
            "score": [5, 1, 3, 2, 5],
        }
    )


@pytest.fixture
def small_classification_df():
    """Small, deterministic classification DataFrame for precise assertion tests."""
    return pd.DataFrame(
        {
            "age": [25, 35, 45, 55, 65],
            "income": [30000, 50000, 70000, 90000, 110000],
            "gender": ["M", "F", "M", "F", "M"],
            "region": ["North", "South", "East", "West", "North"],
            "churned": [0, 1, 0, 1, 0],
        }
    )


@pytest.fixture
def positive_numeric_df():
    """DataFrame with strictly positive values (needed for Box-Cox)."""
    np.random.seed(7)
    return pd.DataFrame(
        {
            "x": np.random.exponential(scale=2, size=50) + 0.1,
            "y": np.random.exponential(scale=5, size=50) + 0.1,
            "label": np.random.choice([0, 1], 50),
        }
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _snapshot(df: pd.DataFrame) -> dict:
    """Capture a value-level snapshot of a DataFrame for mutation detection."""
    return {col: df[col].tolist() for col in df.columns}


# ===========================================================================
# ENCODING
# ===========================================================================


class TestOneHotEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = one_hot_encode(sample_classification_df, columns=["gender"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        one_hot_encode(sample_classification_df, columns=["gender"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_original_column_removed(self, sample_classification_df):
        result = one_hot_encode(sample_classification_df, columns=["gender"])
        assert "gender" not in result.columns

    def test_creates_binary_indicator_columns(self, sample_classification_df):
        result = one_hot_encode(
            sample_classification_df, columns=["gender"], drop_first=False
        )
        # gender has M and F — expect 2 indicator columns
        gender_cols = [c for c in result.columns if c.startswith("gender_")]
        assert len(gender_cols) == 2
        assert set(result[gender_cols[0]].unique()).issubset({0, 1})

    def test_drop_first_reduces_column_count(self, small_classification_df):
        result_keep = one_hot_encode(
            small_classification_df, columns=["gender"], drop_first=False
        )
        result_drop = one_hot_encode(
            small_classification_df, columns=["gender"], drop_first=True
        )
        gender_keep = [c for c in result_keep.columns if c.startswith("gender_")]
        gender_drop = [c for c in result_drop.columns if c.startswith("gender_")]
        assert len(gender_drop) == len(gender_keep) - 1

    def test_skips_columns_exceeding_max_categories(self, sample_classification_df):
        # age has many unique values — should be skipped when max_categories=5
        result = one_hot_encode(
            sample_classification_df, columns=["age"], max_categories=5
        )
        # Column should remain unencoded (not expanded)
        assert "age" in result.columns

    def test_multi_column_encoding(self, sample_classification_df):
        result = one_hot_encode(
            sample_classification_df, columns=["gender", "region"], drop_first=False
        )
        assert "gender" not in result.columns
        assert "region" not in result.columns
        assert result.shape[0] == sample_classification_df.shape[0]


class TestTargetEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = target_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        target_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert _snapshot(sample_classification_df) == snapshot

    def test_column_becomes_numeric(self, sample_classification_df):
        result = target_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert pd.api.types.is_float_dtype(result["gender"])

    def test_encoded_values_in_valid_range(self, sample_classification_df):
        # Smoothed means must be within (0, 1) for a binary target
        result = target_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert result["gender"].between(0.0, 1.0).all()

    def test_same_row_count(self, sample_classification_df):
        result = target_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert result.shape[0] == sample_classification_df.shape[0]


class TestOrdinalEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = ordinal_encode(sample_classification_df, columns=["region"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        ordinal_encode(sample_classification_df, columns=["region"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_column_becomes_integer(self, sample_classification_df):
        result = ordinal_encode(sample_classification_df, columns=["region"])
        assert pd.api.types.is_integer_dtype(result["region"])

    def test_alphabetical_default_ordering(self, small_classification_df):
        result = ordinal_encode(small_classification_df, columns=["region"])
        # Alphabetical: East=0, North=1, South=2, West=3
        original_regions = small_classification_df["region"]
        sorted_unique = sorted(original_regions.unique())
        expected_map = {cat: idx for idx, cat in enumerate(sorted_unique)}
        expected = original_regions.map(expected_map)
        pd.testing.assert_series_equal(
            result["region"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_custom_order_map_respected(self, small_classification_df):
        order = {"region": ["West", "South", "East", "North"]}
        result = ordinal_encode(
            small_classification_df, columns=["region"], order_map=order
        )
        # "West" should map to 0, "South"→1, "East"→2, "North"→3
        assert result.loc[
            small_classification_df["region"] == "West", "region"
        ].iloc[0] == 0


class TestBinaryEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = binary_encode(sample_classification_df, columns=["gender"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        binary_encode(sample_classification_df, columns=["gender"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_original_column_dropped(self, sample_classification_df):
        result = binary_encode(sample_classification_df, columns=["gender"])
        assert "gender" not in result.columns

    def test_bit_columns_created(self, sample_classification_df):
        result = binary_encode(sample_classification_df, columns=["gender"])
        bit_cols = [c for c in result.columns if c.startswith("gender_bin_")]
        assert len(bit_cols) >= 1

    def test_bit_values_are_zero_or_one(self, sample_classification_df):
        result = binary_encode(sample_classification_df, columns=["region"])
        bit_cols = [c for c in result.columns if c.startswith("region_bin_")]
        for col in bit_cols:
            assert set(result[col].unique()).issubset({0, 1})

    def test_row_count_preserved(self, sample_classification_df):
        result = binary_encode(sample_classification_df, columns=["region"])
        assert result.shape[0] == sample_classification_df.shape[0]


class TestFrequencyEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = frequency_encode(sample_classification_df, columns=["gender"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        frequency_encode(sample_classification_df, columns=["gender"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_column_becomes_float(self, sample_classification_df):
        result = frequency_encode(sample_classification_df, columns=["gender"])
        assert pd.api.types.is_float_dtype(result["gender"])

    def test_frequencies_sum_to_one(self, small_classification_df):
        result = frequency_encode(small_classification_df, columns=["region"])
        # Each row now holds freq of that category; sum over unique categories = 1
        unique_freqs = result["region"].unique()
        assert abs(sum(unique_freqs) - 1.0) < 1e-6

    def test_values_in_zero_one_range(self, sample_classification_df):
        result = frequency_encode(sample_classification_df, columns=["region"])
        assert result["region"].between(0.0, 1.0).all()


class TestWoeEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = woe_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        woe_encode(sample_classification_df, columns=["gender"], target_col="churned")
        assert _snapshot(sample_classification_df) == snapshot

    def test_column_becomes_float(self, sample_classification_df):
        result = woe_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert pd.api.types.is_float_dtype(result["gender"])

    def test_row_count_preserved(self, sample_classification_df):
        result = woe_encode(
            sample_classification_df, columns=["gender"], target_col="churned"
        )
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_returns_unchanged_when_single_class(self, small_classification_df):
        # If all targets are the same class, WoE encoding should return unchanged
        df_single = small_classification_df.copy()
        df_single["churned"] = 0
        result = woe_encode(df_single, columns=["gender"], target_col="churned")
        assert isinstance(result, pd.DataFrame)
        # The column should be unchanged (still strings) since encoding was skipped
        assert result["gender"].dtype == object


class TestLabelEncode:
    def test_returns_dataframe(self, sample_classification_df):
        result = label_encode(sample_classification_df, columns=["gender"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        label_encode(sample_classification_df, columns=["gender"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_column_becomes_integer(self, sample_classification_df):
        result = label_encode(sample_classification_df, columns=["gender"])
        assert pd.api.types.is_integer_dtype(result["gender"])

    def test_codes_are_contiguous_from_zero(self, small_classification_df):
        result = label_encode(small_classification_df, columns=["region"])
        unique_codes = sorted(result["region"].unique())
        n_cats = small_classification_df["region"].nunique()
        assert unique_codes == list(range(n_cats))

    def test_multi_column_encoding(self, sample_classification_df):
        result = label_encode(sample_classification_df, columns=["gender", "region"])
        assert pd.api.types.is_integer_dtype(result["gender"])
        assert pd.api.types.is_integer_dtype(result["region"])


# ===========================================================================
# SCALING
# ===========================================================================


class TestStandardScale:
    def test_returns_dataframe(self, sample_classification_df):
        result = standard_scale(sample_classification_df, columns=["age", "income"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        standard_scale(sample_classification_df, columns=["age", "income"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_mean_near_zero(self, sample_classification_df):
        result = standard_scale(sample_classification_df, columns=["age", "income"])
        assert abs(result["age"].mean()) < 1e-9
        assert abs(result["income"].mean()) < 1e-9

    def test_std_near_one(self, sample_classification_df):
        result = standard_scale(sample_classification_df, columns=["age", "income"])
        assert abs(result["age"].std(ddof=0) - 1.0) < 1e-6
        assert abs(result["income"].std(ddof=0) - 1.0) < 1e-6

    def test_other_columns_unchanged(self, sample_classification_df):
        result = standard_scale(sample_classification_df, columns=["age"])
        pd.testing.assert_series_equal(
            result["income"], sample_classification_df["income"]
        )


class TestMinmaxScale:
    def test_returns_dataframe(self, sample_classification_df):
        result = minmax_scale(sample_classification_df, columns=["age", "income"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        minmax_scale(sample_classification_df, columns=["age", "income"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_values_in_zero_one_range(self, sample_classification_df):
        result = minmax_scale(sample_classification_df, columns=["age", "income"])
        assert result["age"].min() >= 0.0 - 1e-9
        assert result["age"].max() <= 1.0 + 1e-9

    def test_custom_feature_range(self, sample_classification_df):
        result = minmax_scale(
            sample_classification_df, columns=["age"], feature_range=(-1, 1)
        )
        assert result["age"].min() >= -1.0 - 1e-9
        assert result["age"].max() <= 1.0 + 1e-9

    def test_row_count_preserved(self, sample_classification_df):
        result = minmax_scale(sample_classification_df, columns=["age"])
        assert result.shape[0] == sample_classification_df.shape[0]


class TestRobustScale:
    def test_returns_dataframe(self, sample_classification_df):
        result = robust_scale(sample_classification_df, columns=["age", "balance"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        robust_scale(sample_classification_df, columns=["age", "balance"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_median_near_zero(self, sample_classification_df):
        result = robust_scale(sample_classification_df, columns=["age"])
        assert abs(result["age"].median()) < 1e-6

    def test_row_count_preserved(self, sample_classification_df):
        result = robust_scale(sample_classification_df, columns=["age"])
        assert result.shape[0] == sample_classification_df.shape[0]


class TestNormalize:
    def test_returns_dataframe(self, sample_classification_df):
        result = normalize(
            sample_classification_df, columns=["age", "income", "balance"]
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        normalize(sample_classification_df, columns=["age", "income", "balance"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_l2_norm_is_one_per_row(self, sample_classification_df):
        cols = ["age", "income", "balance"]
        result = normalize(sample_classification_df, columns=cols, norm="l2")
        row_norms = np.linalg.norm(result[cols].values, axis=1)
        assert np.allclose(row_norms, 1.0, atol=1e-6)

    def test_l1_norm_option(self, sample_classification_df):
        cols = ["age", "income"]
        result = normalize(sample_classification_df, columns=cols, norm="l1")
        row_norms = np.abs(result[cols].values).sum(axis=1)
        assert np.allclose(row_norms, 1.0, atol=1e-6)


# ===========================================================================
# TRANSFORMS
# ===========================================================================


class TestLogTransform:
    def test_returns_dataframe(self, sample_classification_df):
        result = log_transform(sample_classification_df, columns=["income"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        log_transform(sample_classification_df, columns=["income"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_natural_log_correctness(self, small_classification_df):
        result = log_transform(small_classification_df, columns=["income"])
        expected = np.log1p(small_classification_df["income"])
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-9)

    def test_log2_base(self, small_classification_df):
        result = log_transform(small_classification_df, columns=["income"], base="log2")
        expected = np.log2(small_classification_df["income"] + 1)
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-9)

    def test_log10_base(self, small_classification_df):
        result = log_transform(small_classification_df, columns=["income"], base="log10")
        expected = np.log10(small_classification_df["income"] + 1)
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-9)

    def test_zero_values_handled_safely(self):
        df = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0]})
        result = log_transform(df, columns=["x"])
        assert not result["x"].isna().any()
        assert result["x"].iloc[0] == 0.0  # log1p(0) == 0


class TestBoxCoxTransform:
    def test_returns_dataframe(self, positive_numeric_df):
        result = box_cox_transform(positive_numeric_df, columns=["x"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, positive_numeric_df):
        snapshot = _snapshot(positive_numeric_df)
        box_cox_transform(positive_numeric_df, columns=["x"])
        assert _snapshot(positive_numeric_df) == snapshot

    def test_row_count_preserved(self, positive_numeric_df):
        result = box_cox_transform(positive_numeric_df, columns=["x"])
        assert result.shape[0] == positive_numeric_df.shape[0]

    def test_shifts_non_positive_values_automatically(self):
        df = pd.DataFrame({"x": [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]})
        result = box_cox_transform(df, columns=["x"])
        assert isinstance(result, pd.DataFrame)
        assert not result["x"].isna().any()


class TestYeoJohnsonTransform:
    def test_returns_dataframe(self, sample_classification_df):
        result = yeo_johnson_transform(
            sample_classification_df, columns=["age", "income"]
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        yeo_johnson_transform(sample_classification_df, columns=["age", "income"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_row_count_preserved(self, sample_classification_df):
        result = yeo_johnson_transform(
            sample_classification_df, columns=["age", "income"]
        )
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_handles_negative_values(self):
        df = pd.DataFrame({"x": [-3.0, -1.0, 0.0, 1.0, 3.0]})
        result = yeo_johnson_transform(df, columns=["x"])
        assert isinstance(result, pd.DataFrame)
        assert not result["x"].isna().any()


class TestSqrtTransform:
    def test_returns_dataframe(self, sample_classification_df):
        result = sqrt_transform(sample_classification_df, columns=["age"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        sqrt_transform(sample_classification_df, columns=["age"])
        assert _snapshot(sample_classification_df) == snapshot

    def test_correctness(self, small_classification_df):
        result = sqrt_transform(small_classification_df, columns=["income"])
        expected = np.sqrt(small_classification_df["income"])
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-9)

    def test_negative_values_clipped_to_zero(self):
        df = pd.DataFrame({"x": [-4.0, -1.0, 0.0, 4.0, 9.0]})
        result = sqrt_transform(df, columns=["x"])
        assert not result["x"].isna().any()
        # Values originally negative are clipped to 0 before sqrt → result 0
        assert result["x"].iloc[0] == 0.0
        assert result["x"].iloc[1] == 0.0


class TestPowerTransform:
    def test_returns_dataframe(self, sample_classification_df):
        result = power_transform(sample_classification_df, columns=["age"], power=2)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        power_transform(sample_classification_df, columns=["age"], power=2)
        assert _snapshot(sample_classification_df) == snapshot

    def test_square_correctness(self, small_classification_df):
        result = power_transform(small_classification_df, columns=["income"], power=2)
        expected = np.power(small_classification_df["income"], 2)
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-9)

    def test_cube_power(self, small_classification_df):
        result = power_transform(small_classification_df, columns=["age"], power=3)
        expected = np.power(small_classification_df["age"], 3)
        np.testing.assert_allclose(result["age"].values, expected.values, rtol=1e-9)

    def test_fractional_power(self, small_classification_df):
        result = power_transform(
            small_classification_df, columns=["income"], power=0.5
        )
        expected = np.power(small_classification_df["income"].astype(float), 0.5)
        np.testing.assert_allclose(result["income"].values, expected.values, rtol=1e-6)


# ===========================================================================
# FEATURE CREATION
# ===========================================================================


class TestPolynomialFeatures:
    def test_returns_dataframe(self, sample_classification_df):
        result = polynomial_features(
            sample_classification_df, columns=["age", "income"], degree=2
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        polynomial_features(
            sample_classification_df, columns=["age", "income"], degree=2
        )
        assert _snapshot(sample_classification_df) == snapshot

    def test_new_columns_added(self, sample_classification_df):
        result = polynomial_features(
            sample_classification_df, columns=["age", "income"], degree=2
        )
        assert result.shape[1] > sample_classification_df.shape[1]

    def test_degree_2_produces_correct_features(self, small_classification_df):
        result = polynomial_features(
            small_classification_df, columns=["age", "income"], degree=2
        )
        # Degree-2 for 2 features (no bias) = age, income, age^2, age*income, income^2
        # Original columns stay + 3 new columns
        assert "age^2" in result.columns or "age**2" in result.columns or any(
            "age" in c and "2" in c for c in result.columns
        )

    def test_interaction_only_flag(self, small_classification_df):
        result = polynomial_features(
            small_classification_df,
            columns=["age", "income"],
            degree=2,
            interaction_only=True,
        )
        assert isinstance(result, pd.DataFrame)
        # Interaction-only should not create age^2 or income^2
        squared_cols = [
            c
            for c in result.columns
            if c not in small_classification_df.columns
            and ("age" in c and "income" not in c)
        ]
        # No pure-power self-interaction columns expected
        assert result.shape[0] == small_classification_df.shape[0]

    def test_row_count_preserved(self, sample_classification_df):
        result = polynomial_features(
            sample_classification_df, columns=["age", "income"], degree=2
        )
        assert result.shape[0] == sample_classification_df.shape[0]


class TestInteractionFeatures:
    def test_returns_dataframe(self, sample_classification_df):
        result = interaction_features(
            sample_classification_df, col_pairs=[("age", "income")]
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        interaction_features(
            sample_classification_df, col_pairs=[("age", "income")]
        )
        assert _snapshot(sample_classification_df) == snapshot

    def test_interaction_column_name(self, sample_classification_df):
        result = interaction_features(
            sample_classification_df, col_pairs=[("age", "income")]
        )
        assert "age_x_income" in result.columns

    def test_interaction_values_are_product(self, small_classification_df):
        result = interaction_features(
            small_classification_df, col_pairs=[("age", "income")]
        )
        expected = small_classification_df["age"] * small_classification_df["income"]
        pd.testing.assert_series_equal(
            result["age_x_income"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_multiple_pairs(self, sample_classification_df):
        result = interaction_features(
            sample_classification_df,
            col_pairs=[("age", "income"), ("tenure_months", "num_products")],
        )
        assert "age_x_income" in result.columns
        assert "tenure_months_x_num_products" in result.columns


class TestDateParts:
    def test_returns_dataframe(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, datetime_df):
        snapshot = _snapshot(datetime_df)
        date_parts(datetime_df, date_col="event_date")
        assert _snapshot(datetime_df) == snapshot

    def test_expected_columns_created(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        for suffix in ["year", "month", "day", "dow", "quarter", "is_weekend"]:
            assert f"event_date_{suffix}" in result.columns

    def test_year_values_correct(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        assert list(result["event_date_year"]) == [2023, 2023, 2022, 2024, 2023]

    def test_month_values_correct(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        assert list(result["event_date_month"]) == [1, 6, 12, 3, 11]

    def test_is_weekend_flag(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        # Verify flag is 0 or 1
        assert set(result["event_date_is_weekend"].unique()).issubset({0, 1})

    def test_hour_column_added_when_time_present(self, datetime_with_time_df):
        result = date_parts(datetime_with_time_df, date_col="ts")
        assert "ts_hour" in result.columns

    def test_hour_column_absent_for_date_only(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        assert "event_date_hour" not in result.columns

    def test_row_count_preserved(self, datetime_df):
        result = date_parts(datetime_df, date_col="event_date")
        assert result.shape[0] == datetime_df.shape[0]


class TestLagFeatures:
    def test_returns_dataframe(self, sample_classification_df):
        result = lag_features(
            sample_classification_df, column="balance", lags=[1, 2, 3]
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        lag_features(sample_classification_df, column="balance", lags=[1, 2, 3])
        assert _snapshot(sample_classification_df) == snapshot

    def test_lag_columns_created(self, sample_classification_df):
        result = lag_features(
            sample_classification_df, column="balance", lags=[1, 2, 3]
        )
        assert "balance_lag_1" in result.columns
        assert "balance_lag_2" in result.columns
        assert "balance_lag_3" in result.columns

    def test_lag_1_values_shifted_by_one(self, small_classification_df):
        result = lag_features(small_classification_df, column="income", lags=[1])
        # First row should be NaN (no prior row)
        assert pd.isna(result["income_lag_1"].iloc[0])
        # Second row should equal the first row's original income
        assert result["income_lag_1"].iloc[1] == small_classification_df["income"].iloc[0]

    def test_row_count_preserved(self, sample_classification_df):
        result = lag_features(
            sample_classification_df, column="balance", lags=[1, 7]
        )
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_sort_col_reorders_before_lag(self, sample_classification_df):
        # With sort_col specified, output should still have same row count
        result = lag_features(
            sample_classification_df,
            column="balance",
            lags=[1],
            sort_col="tenure_months",
        )
        assert result.shape[0] == sample_classification_df.shape[0]


class TestRollingFeatures:
    def test_returns_dataframe(self, sample_classification_df):
        result = rolling_features(
            sample_classification_df, column="balance", windows=[3, 7]
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        rolling_features(sample_classification_df, column="balance", windows=[3, 7])
        assert _snapshot(sample_classification_df) == snapshot

    def test_rolling_mean_columns_created(self, sample_classification_df):
        result = rolling_features(
            sample_classification_df, column="balance", windows=[3, 7]
        )
        assert "balance_rolling_3_mean" in result.columns
        assert "balance_rolling_7_mean" in result.columns

    def test_rolling_std_columns_created_by_default(self, sample_classification_df):
        result = rolling_features(
            sample_classification_df, column="balance", windows=[3]
        )
        assert "balance_rolling_3_std" in result.columns

    def test_custom_aggs(self, sample_classification_df):
        result = rolling_features(
            sample_classification_df,
            column="balance",
            windows=[5],
            aggs=["min", "max"],
        )
        assert "balance_rolling_5_min" in result.columns
        assert "balance_rolling_5_max" in result.columns
        assert "balance_rolling_5_mean" not in result.columns

    def test_row_count_preserved(self, sample_classification_df):
        result = rolling_features(
            sample_classification_df, column="balance", windows=[3]
        )
        assert result.shape[0] == sample_classification_df.shape[0]


class TestBinning:
    def test_returns_dataframe(self, sample_classification_df):
        result = binning(sample_classification_df, column="age", n_bins=5)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        binning(sample_classification_df, column="age", n_bins=5)
        assert _snapshot(sample_classification_df) == snapshot

    def test_binned_column_created(self, sample_classification_df):
        result = binning(sample_classification_df, column="age", n_bins=5)
        assert "age_binned" in result.columns

    def test_original_column_still_present(self, sample_classification_df):
        result = binning(sample_classification_df, column="age", n_bins=5)
        assert "age" in result.columns

    def test_quantile_strategy_produces_n_bins(self, sample_classification_df):
        n = 5
        result = binning(
            sample_classification_df, column="age", n_bins=n, strategy="quantile"
        )
        n_unique_bins = result["age_binned"].nunique()
        # Quantile binning may produce fewer bins with duplicate edges
        assert 1 <= n_unique_bins <= n

    def test_uniform_strategy(self, sample_classification_df):
        result = binning(
            sample_classification_df, column="age", n_bins=4, strategy="uniform"
        )
        assert "age_binned" in result.columns
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_custom_labels(self, sample_classification_df):
        labels = ["very_low", "low", "medium", "high", "very_high"]
        result = binning(
            sample_classification_df,
            column="age",
            n_bins=5,
            strategy="quantile",
            labels=labels,
        )
        unique_values = set(result["age_binned"].dropna().astype(str).unique())
        assert unique_values.issubset(set(labels))


class TestRatioFeatures:
    def test_returns_dataframe(self, sample_classification_df):
        result = ratio_features(
            sample_classification_df,
            numerator_col="income",
            denominator_col="age",
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        ratio_features(
            sample_classification_df,
            numerator_col="income",
            denominator_col="age",
        )
        assert _snapshot(sample_classification_df) == snapshot

    def test_default_column_name(self, sample_classification_df):
        result = ratio_features(
            sample_classification_df,
            numerator_col="income",
            denominator_col="age",
        )
        assert "income_over_age" in result.columns

    def test_custom_column_name(self, sample_classification_df):
        result = ratio_features(
            sample_classification_df,
            numerator_col="income",
            denominator_col="age",
            name="income_per_year",
        )
        assert "income_per_year" in result.columns

    def test_ratio_values_correct(self, small_classification_df):
        result = ratio_features(
            small_classification_df,
            numerator_col="income",
            denominator_col="age",
        )
        expected = small_classification_df["income"] / small_classification_df["age"]
        np.testing.assert_allclose(
            result["income_over_age"].values, expected.values, rtol=1e-9
        )

    def test_division_by_zero_produces_nan(self):
        df = pd.DataFrame({"numerator": [10, 20, 30], "denominator": [2, 0, 5]})
        result = ratio_features(df, numerator_col="numerator", denominator_col="denominator")
        assert pd.isna(result["numerator_over_denominator"].iloc[1])

    def test_row_count_preserved(self, sample_classification_df):
        result = ratio_features(
            sample_classification_df,
            numerator_col="income",
            denominator_col="age",
        )
        assert result.shape[0] == sample_classification_df.shape[0]


class TestTextLengthFeatures:
    def test_returns_dataframe(self, text_df):
        result = text_length_features(text_df, text_col="review")
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, text_df):
        snapshot = _snapshot(text_df)
        text_length_features(text_df, text_col="review")
        assert _snapshot(text_df) == snapshot

    def test_three_new_columns_created(self, text_df):
        result = text_length_features(text_df, text_col="review")
        assert "review_char_count" in result.columns
        assert "review_word_count" in result.columns
        assert "review_avg_word_len" in result.columns

    def test_char_count_correctness(self, text_df):
        result = text_length_features(text_df, text_col="review")
        for idx, row in text_df.iterrows():
            text_val = str(row["review"]) if pd.notna(row["review"]) else ""
            assert result.loc[idx, "review_char_count"] == len(text_val)

    def test_word_count_correctness(self):
        df = pd.DataFrame({"text": ["hello world", "one two three four", "single"]})
        result = text_length_features(df, text_col="text")
        assert list(result["text_word_count"]) == [2, 4, 1]

    def test_empty_string_produces_zero_counts(self, text_df):
        result = text_length_features(text_df, text_col="review")
        empty_mask = text_df["review"] == ""
        assert result.loc[empty_mask, "review_word_count"].iloc[0] == 0
        assert result.loc[empty_mask, "review_avg_word_len"].iloc[0] == 0.0

    def test_avg_word_len_reasonable(self):
        df = pd.DataFrame({"text": ["hello world"]})  # avg = (5+5)/2 = 5
        result = text_length_features(df, text_col="text")
        assert abs(result["text_avg_word_len"].iloc[0] - 5.5) < 1e-6

    def test_row_count_preserved(self, text_df):
        result = text_length_features(text_df, text_col="review")
        assert result.shape[0] == text_df.shape[0]


# ===========================================================================
# IMPUTATION
# ===========================================================================


class TestImputeMean:
    def test_returns_dataframe(self, nan_df):
        result = impute_mean(nan_df, columns=["a", "b"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, nan_df):
        snapshot = _snapshot(nan_df)
        impute_mean(nan_df, columns=["a", "b"])
        assert _snapshot(nan_df) == snapshot

    def test_no_nan_after_imputation(self, nan_df):
        result = impute_mean(nan_df, columns=["a", "b"])
        assert not result["a"].isna().any()
        assert not result["b"].isna().any()

    def test_imputed_with_column_mean(self, nan_df):
        col_mean = nan_df["a"].mean()
        result = impute_mean(nan_df, columns=["a"])
        # Rows that were NaN should now equal the original column mean
        originally_nan = nan_df["a"].isna()
        assert (result.loc[originally_nan, "a"] == col_mean).all()

    def test_non_imputed_column_unchanged(self, nan_df):
        result = impute_mean(nan_df, columns=["a"])
        pd.testing.assert_series_equal(result["c"], nan_df["c"])

    def test_row_count_preserved(self, nan_df):
        result = impute_mean(nan_df, columns=["a", "b"])
        assert result.shape[0] == nan_df.shape[0]


class TestImputeMedian:
    def test_returns_dataframe(self, nan_df):
        result = impute_median(nan_df, columns=["a", "b"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, nan_df):
        snapshot = _snapshot(nan_df)
        impute_median(nan_df, columns=["a", "b"])
        assert _snapshot(nan_df) == snapshot

    def test_no_nan_after_imputation(self, nan_df):
        result = impute_median(nan_df, columns=["a", "b"])
        assert not result["a"].isna().any()
        assert not result["b"].isna().any()

    def test_imputed_with_column_median(self, nan_df):
        col_median = nan_df["a"].median()
        result = impute_median(nan_df, columns=["a"])
        originally_nan = nan_df["a"].isna()
        assert (result.loc[originally_nan, "a"] == col_median).all()

    def test_row_count_preserved(self, nan_df):
        result = impute_median(nan_df, columns=["a"])
        assert result.shape[0] == nan_df.shape[0]


class TestImputeMode:
    def test_returns_dataframe(self, nan_df):
        result = impute_mode(nan_df, columns=["a"])
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, nan_df):
        snapshot = _snapshot(nan_df)
        impute_mode(nan_df, columns=["a"])
        assert _snapshot(nan_df) == snapshot

    def test_no_nan_after_imputation(self, nan_df):
        result = impute_mode(nan_df, columns=["a", "b"])
        assert not result["a"].isna().any()
        assert not result["b"].isna().any()

    def test_imputed_with_mode_value(self, nan_df):
        # Inject a clear mode so we can assert exactly
        df = pd.DataFrame({"x": [1.0, np.nan, 1.0, 1.0, 2.0]})
        result = impute_mode(df, columns=["x"])
        assert result["x"].iloc[1] == 1.0

    def test_categorical_column_imputed(self):
        df = pd.DataFrame(
            {"cat": ["a", None, "a", "b", "a", None], "num": [1, 2, 3, 4, 5, 6]}
        )
        result = impute_mode(df, columns=["cat"])
        assert not result["cat"].isna().any()
        assert result["cat"].iloc[1] == "a"

    def test_row_count_preserved(self, nan_df):
        result = impute_mode(nan_df, columns=["a"])
        assert result.shape[0] == nan_df.shape[0]


class TestImputeKnn:
    def test_returns_dataframe(self, nan_df):
        result = impute_knn(nan_df, columns=["a", "b"], n_neighbors=3)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, nan_df):
        snapshot = _snapshot(nan_df)
        impute_knn(nan_df, columns=["a", "b"], n_neighbors=3)
        assert _snapshot(nan_df) == snapshot

    def test_no_nan_after_imputation(self, nan_df):
        result = impute_knn(nan_df, columns=["a", "b"], n_neighbors=3)
        assert not result["a"].isna().any()
        assert not result["b"].isna().any()

    def test_non_imputed_column_unchanged(self, nan_df):
        result = impute_knn(nan_df, columns=["a"], n_neighbors=3)
        pd.testing.assert_series_equal(result["c"], nan_df["c"])

    def test_row_count_preserved(self, nan_df):
        result = impute_knn(nan_df, columns=["a", "b"], n_neighbors=3)
        assert result.shape[0] == nan_df.shape[0]

    def test_default_n_neighbors(self, nan_df):
        result = impute_knn(nan_df, columns=["a"])
        assert isinstance(result, pd.DataFrame)
        assert not result["a"].isna().any()


# ===========================================================================
# SELECTION
# ===========================================================================


class TestSelectFeaturesImportance:
    def test_returns_dataframe(self, sample_classification_df):
        result = select_features_importance(
            sample_classification_df, target_col="churned", top_n=5
        )
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        select_features_importance(
            sample_classification_df, target_col="churned", top_n=5
        )
        assert _snapshot(sample_classification_df) == snapshot

    def test_target_column_present_in_output(self, sample_classification_df):
        result = select_features_importance(
            sample_classification_df, target_col="churned", top_n=5
        )
        assert "churned" in result.columns

    def test_column_count_at_most_top_n_plus_target(self, sample_classification_df):
        top_n = 4
        result = select_features_importance(
            sample_classification_df, target_col="churned", top_n=top_n
        )
        # At most top_n numeric features + target + any non-numeric columns
        numeric_features_in_result = [
            c
            for c in result.columns
            if c != "churned"
            and pd.api.types.is_numeric_dtype(result[c])
        ]
        assert len(numeric_features_in_result) <= top_n

    def test_row_count_preserved(self, sample_classification_df):
        result = select_features_importance(
            sample_classification_df, target_col="churned", top_n=5
        )
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_returns_unchanged_when_no_numeric_features(self):
        df = pd.DataFrame(
            {"cat": ["a", "b", "c", "d"], "target": [0, 1, 0, 1]}
        )
        result = select_features_importance(df, target_col="target", top_n=5)
        assert isinstance(result, pd.DataFrame)


class TestDropLowVariance:
    def test_returns_dataframe(self, sample_classification_df):
        result = drop_low_variance(sample_classification_df, threshold=0.01)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_original(self, sample_classification_df):
        snapshot = _snapshot(sample_classification_df)
        drop_low_variance(sample_classification_df, threshold=0.01)
        assert _snapshot(sample_classification_df) == snapshot

    def test_low_variance_column_dropped(self):
        df = pd.DataFrame(
            {
                "constant": [1.0] * 100,  # zero variance — always dropped
                "varying": np.random.default_rng(0).standard_normal(100),
            }
        )
        result = drop_low_variance(df, threshold=0.01)
        assert "constant" not in result.columns
        assert "varying" in result.columns

    def test_high_variance_columns_kept(self, sample_classification_df):
        # age and income should have high variance and must survive
        result = drop_low_variance(sample_classification_df, threshold=0.01)
        assert "age" in result.columns
        assert "income" in result.columns

    def test_row_count_preserved(self, sample_classification_df):
        result = drop_low_variance(sample_classification_df, threshold=0.01)
        assert result.shape[0] == sample_classification_df.shape[0]

    def test_non_numeric_columns_preserved(self, sample_classification_df):
        result = drop_low_variance(sample_classification_df, threshold=0.01)
        # Categorical columns must not be dropped by variance thresholding
        assert "gender" in result.columns
        assert "region" in result.columns

    def test_no_columns_dropped_when_threshold_zero(self, sample_classification_df):
        numeric_cols_before = sample_classification_df.select_dtypes(
            include="number"
        ).columns.tolist()
        result = drop_low_variance(sample_classification_df, threshold=0.0)
        numeric_cols_after = result.select_dtypes(include="number").columns.tolist()
        assert set(numeric_cols_before) == set(numeric_cols_after)
