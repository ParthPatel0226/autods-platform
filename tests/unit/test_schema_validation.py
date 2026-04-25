"""Unit tests for validation/schema_validator.py.

Covers all three public functions and the internal helper:
  - extract_training_schema
  - validate_prediction_schema
  - adapt_prediction_data
  - _dtypes_compatible (internal, tested indirectly and directly)

Each function has at minimum:
  - A happy-path test verifying return shape, key types, and value correctness.
  - Edge-case tests verifying correct behavior on degenerate or unusual input.

Fixture dependencies (from tests/conftest.py):
  - sample_classification_df  (500 rows, mixed numeric + categorical columns)

Local fixtures defined here:
  - numeric_df           -- small numeric-only DataFrame
  - categorical_df       -- small categorical-only DataFrame
  - mixed_df             -- DataFrame with numeric, categorical, and datetime columns
  - training_schema      -- pre-extracted schema from mixed_df
  - all_nan_df           -- DataFrame where every value is NaN
"""

import numpy as np
import pandas as pd
import pytest

from validation.schema_validator import (
    _dtypes_compatible,
    adapt_prediction_data,
    extract_training_schema,
    validate_prediction_schema,
)


# ======================================================================
# Local fixtures
# ======================================================================


@pytest.fixture
def numeric_df() -> pd.DataFrame:
    """Small DataFrame with only numeric columns."""
    return pd.DataFrame({
        "age": [25, 30, 35, 40, 45],
        "income": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
        "score": [0.8, 0.6, 0.9, 0.7, 0.5],
    })


@pytest.fixture
def categorical_df() -> pd.DataFrame:
    """Small DataFrame with only object/categorical columns."""
    return pd.DataFrame({
        "color": ["red", "blue", "green", "red", "blue"],
        "size": pd.Categorical(["S", "M", "L", "M", "S"]),
    })


@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """DataFrame with numeric, categorical, and boolean columns."""
    return pd.DataFrame({
        "age": [25, 30, 35, 40, 45],
        "income": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
        "city": ["NYC", "LA", "CHI", "NYC", "LA"],
        "active": [True, False, True, True, False],
    })


@pytest.fixture
def training_schema(mixed_df: pd.DataFrame) -> dict:
    """Pre-extracted schema from mixed_df for validation tests."""
    return extract_training_schema(mixed_df)


@pytest.fixture
def all_nan_df() -> pd.DataFrame:
    """DataFrame where every value is NaN."""
    return pd.DataFrame({
        "x": [np.nan, np.nan, np.nan],
        "y": [np.nan, np.nan, np.nan],
    })


@pytest.fixture
def single_row_df() -> pd.DataFrame:
    """DataFrame with a single row."""
    return pd.DataFrame({"a": [1], "b": ["hello"], "c": [3.14]})


# ======================================================================
# Tests: extract_training_schema
# ======================================================================


class TestExtractTrainingSchema:
    """Tests for extract_training_schema."""

    def test_returns_dict_with_all_columns(
        self, sample_classification_df: pd.DataFrame
    ) -> None:
        """Schema dict should contain an entry for every column."""
        schema = extract_training_schema(sample_classification_df)
        assert isinstance(schema, dict)
        assert set(schema.keys()) == set(sample_classification_df.columns)

    def test_numeric_column_has_stats(self, numeric_df: pd.DataFrame) -> None:
        """Numeric columns should include min, max, mean, std."""
        schema = extract_training_schema(numeric_df)
        entry = schema["age"]

        assert entry["dtype"] == "int64"
        assert entry["min"] == 25.0
        assert entry["max"] == 45.0
        assert isinstance(entry["mean"], float)
        assert isinstance(entry["std"], float)
        assert entry["categories"] is None
        assert entry["n_unique"] == 5

    def test_float_column_stats(self, numeric_df: pd.DataFrame) -> None:
        """Float columns should have correct stats."""
        schema = extract_training_schema(numeric_df)
        entry = schema["income"]

        assert entry["dtype"] == "float64"
        assert entry["min"] == 50000.0
        assert entry["max"] == 90000.0
        assert abs(entry["mean"] - 70000.0) < 1e-6

    def test_object_column_has_categories(
        self, categorical_df: pd.DataFrame
    ) -> None:
        """Object columns should capture category values."""
        schema = extract_training_schema(categorical_df)
        entry = schema["color"]

        assert entry["dtype"] == "object"
        assert set(entry["categories"]) == {"red", "blue", "green"}
        assert entry["min"] is None
        assert entry["max"] is None
        assert entry["mean"] is None
        assert entry["std"] is None

    def test_categorical_dtype_column(
        self, categorical_df: pd.DataFrame
    ) -> None:
        """pd.Categorical columns should be handled like object columns."""
        schema = extract_training_schema(categorical_df)
        entry = schema["size"]

        assert entry["categories"] is not None
        assert set(entry["categories"]) == {"S", "M", "L"}

    def test_boolean_column(self, mixed_df: pd.DataFrame) -> None:
        """Boolean columns are treated as numeric by pandas."""
        schema = extract_training_schema(mixed_df)
        entry = schema["active"]

        assert "bool" in entry["dtype"]
        # pandas treats bool as numeric, so min/max/mean/std are populated
        assert entry["min"] is not None
        assert entry["categories"] is None

    def test_all_nan_numeric_column(self) -> None:
        """When a numeric column is all-NaN, stats should be None."""
        df = pd.DataFrame({"x": pd.array([np.nan, np.nan], dtype="float64")})
        schema = extract_training_schema(df)
        entry = schema["x"]

        assert entry["dtype"] == "float64"
        assert entry["min"] is None
        assert entry["max"] is None
        assert entry["mean"] is None
        assert entry["std"] is None

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame (no rows) should still produce a schema."""
        df = pd.DataFrame({"a": pd.Series(dtype="int64"), "b": pd.Series(dtype="object")})
        schema = extract_training_schema(df)

        assert "a" in schema
        assert "b" in schema
        assert schema["a"]["n_unique"] == 0
        assert schema["b"]["categories"] == []

    def test_single_row(self, single_row_df: pd.DataFrame) -> None:
        """Schema extraction should work with a single row."""
        schema = extract_training_schema(single_row_df)

        assert schema["a"]["min"] == 1.0
        assert schema["a"]["max"] == 1.0
        assert schema["b"]["categories"] == ["hello"]
        assert schema["c"]["n_unique"] == 1

    def test_n_unique_correct(self) -> None:
        """n_unique should reflect actual unique count including potential duplicates."""
        df = pd.DataFrame({"x": [1, 1, 2, 2, 3]})
        schema = extract_training_schema(df)
        assert schema["x"]["n_unique"] == 3

    def test_categories_exclude_nan(self) -> None:
        """Categories should not include NaN values."""
        df = pd.DataFrame({"color": ["red", "blue", np.nan, "red", np.nan]})
        schema = extract_training_schema(df)
        assert set(schema["color"]["categories"]) == {"red", "blue"}


# ======================================================================
# Tests: validate_prediction_schema
# ======================================================================


class TestValidatePredictionSchema:
    """Tests for validate_prediction_schema."""

    def test_perfect_match_returns_valid(
        self, mixed_df: pd.DataFrame, training_schema: dict
    ) -> None:
        """Identical data should pass validation with no issues."""
        is_valid, issues = validate_prediction_schema(mixed_df, training_schema)
        assert is_valid is True
        # No critical or warning issues for identical data
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        assert len(critical_issues) == 0

    def test_missing_column_is_critical(self, training_schema: dict) -> None:
        """Missing a required column should produce a critical issue."""
        pred_df = pd.DataFrame({
            "age": [25],
            "income": [50000.0],
            # "city" is missing
            # "active" is missing
        })
        is_valid, issues = validate_prediction_schema(pred_df, training_schema)

        assert is_valid is False
        missing_issues = [i for i in issues if i["type"] == "missing_columns"]
        assert len(missing_issues) == 1
        assert "city" in missing_issues[0]["columns"]
        assert "active" in missing_issues[0]["columns"]
        assert missing_issues[0]["severity"] == "critical"

    def test_extra_column_is_info(self, training_schema: dict) -> None:
        """Extra columns not in training schema should produce info-level issue."""
        pred_df = pd.DataFrame({
            "age": [25],
            "income": [50000.0],
            "city": ["NYC"],
            "active": [True],
            "extra_col": [99],
        })
        is_valid, issues = validate_prediction_schema(pred_df, training_schema)

        assert is_valid is True
        extra_issues = [i for i in issues if i["type"] == "extra_columns"]
        assert len(extra_issues) == 1
        assert "extra_col" in extra_issues[0]["columns"]
        assert extra_issues[0]["severity"] == "info"

    def test_dtype_mismatch_warning(self, training_schema: dict) -> None:
        """Mismatched dtype should produce a warning, not a critical failure."""
        pred_df = pd.DataFrame({
            "age": ["twenty-five"],  # object instead of int64
            "income": [50000.0],
            "city": ["NYC"],
            "active": [True],
        })
        is_valid, issues = validate_prediction_schema(pred_df, training_schema)

        # dtype mismatch is warning, not critical
        assert is_valid is True
        dtype_issues = [i for i in issues if i["type"] == "dtype_mismatch"]
        assert len(dtype_issues) >= 1
        age_issue = [i for i in dtype_issues if "age" in i["columns"]]
        assert len(age_issue) == 1
        assert age_issue[0]["severity"] == "warning"

    def test_numeric_out_of_range_warning(self) -> None:
        """Values outside training range should produce a warning."""
        train_df = pd.DataFrame({"x": [10.0, 20.0, 30.0]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"x": [5.0, 50.0]})  # below min, above max
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        assert is_valid is True
        range_issues = [i for i in issues if i["type"] == "out_of_range"]
        assert len(range_issues) == 1
        assert range_issues[0]["severity"] == "warning"

    def test_numeric_within_range_no_warning(self) -> None:
        """Values within training range should not produce range warnings."""
        train_df = pd.DataFrame({"x": [10.0, 20.0, 30.0]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"x": [15.0, 25.0]})
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        assert is_valid is True
        range_issues = [i for i in issues if i["type"] == "out_of_range"]
        assert len(range_issues) == 0

    def test_unknown_categories_warning(self) -> None:
        """Unseen category values should produce a warning."""
        train_df = pd.DataFrame({"color": ["red", "blue", "green"]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"color": ["red", "purple", "orange"]})
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        assert is_valid is True
        cat_issues = [i for i in issues if i["type"] == "unknown_categories"]
        assert len(cat_issues) == 1
        assert cat_issues[0]["severity"] == "warning"
        assert "2" in cat_issues[0]["message"]  # 2 unseen categories

    def test_known_categories_no_warning(self) -> None:
        """All-known category values should not produce a warning."""
        train_df = pd.DataFrame({"color": ["red", "blue", "green"]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"color": ["red", "blue"]})
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        cat_issues = [i for i in issues if i["type"] == "unknown_categories"]
        assert len(cat_issues) == 0

    def test_empty_prediction_df_missing_all_columns(
        self, training_schema: dict
    ) -> None:
        """Empty DataFrame with no columns should flag all as missing."""
        pred_df = pd.DataFrame()
        is_valid, issues = validate_prediction_schema(pred_df, training_schema)

        assert is_valid is False
        missing_issues = [i for i in issues if i["type"] == "missing_columns"]
        assert len(missing_issues) == 1
        assert set(missing_issues[0]["columns"]) == set(training_schema.keys())

    def test_multiple_issues_combined(self) -> None:
        """Validate that multiple issue types can coexist."""
        train_df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "b": ["x", "y", "z"],
            "c": [10, 20, 30],
        })
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({
            # "c" is missing -> critical
            "a": [0.0, 100.0],  # out of range -> warning
            "b": ["x", "w"],    # unknown category -> warning
            "extra": [1, 2],    # extra column -> info
        })
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        assert is_valid is False
        types_found = {i["type"] for i in issues}
        assert "missing_columns" in types_found
        assert "out_of_range" in types_found
        assert "unknown_categories" in types_found
        assert "extra_columns" in types_found

    def test_compatible_int_float_no_mismatch(self) -> None:
        """int64 vs float64 should be compatible and not raise a dtype warning."""
        train_df = pd.DataFrame({"x": [1, 2, 3]})  # int64
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})  # float64
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        dtype_issues = [i for i in issues if i["type"] == "dtype_mismatch"]
        assert len(dtype_issues) == 0

    def test_nan_categories_in_prediction_ignored(self) -> None:
        """NaN values in categorical prediction column should not count as unknown."""
        train_df = pd.DataFrame({"color": ["red", "blue"]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"color": ["red", np.nan, "blue"]})
        is_valid, issues = validate_prediction_schema(pred_df, schema)

        cat_issues = [i for i in issues if i["type"] == "unknown_categories"]
        assert len(cat_issues) == 0


# ======================================================================
# Tests: adapt_prediction_data
# ======================================================================


class TestAdaptPredictionData:
    """Tests for adapt_prediction_data."""

    def test_columns_reordered_to_schema_order(self) -> None:
        """Output columns should follow the schema key order."""
        train_df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"c": [30], "a": [10], "b": [20]})
        result = adapt_prediction_data(pred_df, schema)

        assert list(result.columns) == ["a", "b", "c"]

    def test_extra_columns_dropped(self) -> None:
        """Columns not in the training schema should be removed."""
        train_df = pd.DataFrame({"a": [1], "b": [2]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"a": [10], "b": [20], "extra": [99]})
        result = adapt_prediction_data(pred_df, schema)

        assert "extra" not in result.columns
        assert list(result.columns) == ["a", "b"]

    def test_missing_numeric_column_filled_with_mean(self) -> None:
        """Missing numeric columns should be filled with training mean."""
        train_df = pd.DataFrame({"a": [10.0, 20.0, 30.0], "b": [1.0, 2.0, 3.0]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"a": [15.0]})  # "b" is missing
        result = adapt_prediction_data(pred_df, schema)

        assert "b" in result.columns
        expected_mean = 2.0  # mean of [1, 2, 3]
        assert abs(result["b"].iloc[0] - expected_mean) < 1e-6

    def test_missing_categorical_column_filled_with_first_category(self) -> None:
        """Missing categorical columns should be filled with first known category."""
        train_df = pd.DataFrame({"x": [1, 2, 3], "color": ["red", "blue", "green"]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"x": [5]})  # "color" is missing
        result = adapt_prediction_data(pred_df, schema)

        assert "color" in result.columns
        # First category from training data
        assert result["color"].iloc[0] == schema["color"]["categories"][0]

    def test_missing_column_no_mean_no_categories_fills_nan(self) -> None:
        """Missing columns with no mean and no categories should be NaN.

        Boolean columns are numeric in pandas, so they get a mean fill.
        Use a datetime column instead to test the NaN fallback path.
        """
        train_df = pd.DataFrame({
            "ts": pd.to_datetime(["2021-01-01", "2021-01-02", "2021-01-03"]),
        })
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"unrelated": [1]})
        result = adapt_prediction_data(pred_df, schema)

        assert "ts" in result.columns
        assert result["ts"].isna().all()

    def test_dtype_coercion_string_to_numeric(self) -> None:
        """String values that look numeric should be coerced to numeric."""
        train_df = pd.DataFrame({"price": [10.0, 20.0, 30.0]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"price": ["15.5", "25.0", "invalid"]})
        result = adapt_prediction_data(pred_df, schema)

        assert result["price"].iloc[0] == 15.5
        assert result["price"].iloc[1] == 25.0
        assert pd.isna(result["price"].iloc[2])  # "invalid" coerced to NaN

    def test_dtype_coercion_numeric_to_object(self) -> None:
        """Numeric values should be castable to object dtype."""
        train_df = pd.DataFrame({"label": ["a", "b", "c"]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"label": [1, 2, 3]})
        result = adapt_prediction_data(pred_df, schema)

        assert str(result["label"].dtype) == "object"

    def test_original_dataframe_not_mutated(self) -> None:
        """adapt_prediction_data should not modify the input DataFrame."""
        train_df = pd.DataFrame({"a": [1, 2, 3]})
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"a": [10], "extra": [99]})
        original_cols = list(pred_df.columns)
        _ = adapt_prediction_data(pred_df, schema)

        assert list(pred_df.columns) == original_cols
        assert "extra" in pred_df.columns

    def test_adapt_then_validate_passes(self) -> None:
        """Adapted data should pass validation without critical issues."""
        train_df = pd.DataFrame({
            "age": [25, 30, 35],
            "city": ["NYC", "LA", "CHI"],
            "score": [0.8, 0.6, 0.9],
        })
        schema = extract_training_schema(train_df)

        # Prediction data with missing columns, extra columns, wrong order
        pred_df = pd.DataFrame({
            "extra": [1],
            "age": [28],
            # "city" and "score" are missing
        })
        adapted = adapt_prediction_data(pred_df, schema)
        is_valid, issues = validate_prediction_schema(adapted, schema)

        assert is_valid is True
        critical = [i for i in issues if i["severity"] == "critical"]
        assert len(critical) == 0

    def test_empty_prediction_gets_all_defaults(self) -> None:
        """An empty prediction DataFrame should get all columns filled."""
        train_df = pd.DataFrame({
            "num": [10.0, 20.0],
            "cat": ["a", "b"],
        })
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"unrelated": [1, 2, 3]})
        result = adapt_prediction_data(pred_df, schema)

        assert set(result.columns) == {"num", "cat"}
        assert len(result) == 3  # preserves row count from pred_df
        assert abs(result["num"].iloc[0] - 15.0) < 1e-6  # mean of [10, 20]


# ======================================================================
# Tests: _dtypes_compatible (internal helper)
# ======================================================================


class TestDtypesCompatible:
    """Tests for the internal _dtypes_compatible helper."""

    def test_identical_types_compatible(self) -> None:
        assert _dtypes_compatible("float64", "float64") is True
        assert _dtypes_compatible("int64", "int64") is True
        assert _dtypes_compatible("object", "object") is True

    def test_int_variants_compatible(self) -> None:
        assert _dtypes_compatible("int32", "int64") is True
        assert _dtypes_compatible("int8", "int64") is True
        assert _dtypes_compatible("uint8", "int32") is True

    def test_float_variants_compatible(self) -> None:
        assert _dtypes_compatible("float32", "float64") is True
        assert _dtypes_compatible("float16", "Float64") is True

    def test_int_float_cross_compatible(self) -> None:
        assert _dtypes_compatible("int64", "float64") is True
        assert _dtypes_compatible("float64", "int64") is True
        assert _dtypes_compatible("Int64", "float32") is True

    def test_object_vs_numeric_incompatible(self) -> None:
        assert _dtypes_compatible("object", "int64") is False
        assert _dtypes_compatible("object", "float64") is False

    def test_bool_vs_numeric_incompatible(self) -> None:
        assert _dtypes_compatible("bool", "int64") is False
        assert _dtypes_compatible("bool", "float64") is False

    def test_object_vs_bool_incompatible(self) -> None:
        assert _dtypes_compatible("object", "bool") is False

    def test_nullable_int_compatible(self) -> None:
        """Pandas nullable Int64 should be compatible with int64."""
        assert _dtypes_compatible("Int64", "int64") is True
        assert _dtypes_compatible("Int32", "int64") is True

    def test_datetime_vs_numeric_incompatible(self) -> None:
        assert _dtypes_compatible("datetime64[ns]", "float64") is False
        assert _dtypes_compatible("int64", "datetime64[ns]") is False


# ======================================================================
# Tests: integration scenarios
# ======================================================================


class TestSchemaRoundTrip:
    """End-to-end scenarios combining extract + validate + adapt."""

    def test_full_roundtrip_classification_data(
        self, sample_classification_df: pd.DataFrame
    ) -> None:
        """Extract schema from training data, validate same data, expect pass."""
        schema = extract_training_schema(sample_classification_df)
        is_valid, issues = validate_prediction_schema(
            sample_classification_df, schema
        )
        assert is_valid is True
        critical = [i for i in issues if i["severity"] == "critical"]
        assert len(critical) == 0

    def test_subset_columns_fails_validation_then_adapt_fixes(self) -> None:
        """Prediction with missing columns fails validation; adapt fills them."""
        train_df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0],
            "b": ["x", "y", "z"],
            "c": [10, 20, 30],
        })
        schema = extract_training_schema(train_df)

        pred_df = pd.DataFrame({"a": [1.5]})

        # Before adaptation: fails
        is_valid_before, _ = validate_prediction_schema(pred_df, schema)
        assert is_valid_before is False

        # After adaptation: passes
        adapted = adapt_prediction_data(pred_df, schema)
        is_valid_after, issues_after = validate_prediction_schema(
            adapted, schema
        )
        assert is_valid_after is True

    def test_large_dataframe_performance(self) -> None:
        """Schema operations should handle moderately large DataFrames."""
        np.random.seed(42)
        n = 10_000
        df = pd.DataFrame({
            f"num_{i}": np.random.randn(n) for i in range(20)
        })
        df["cat_0"] = np.random.choice(["a", "b", "c", "d"], n)

        schema = extract_training_schema(df)
        assert len(schema) == 21

        is_valid, issues = validate_prediction_schema(df, schema)
        assert is_valid is True

    def test_schema_with_nan_in_numeric_training(self) -> None:
        """Training data with NaN in numeric columns should still produce valid schema."""
        train_df = pd.DataFrame({
            "x": [1.0, np.nan, 3.0, np.nan, 5.0],
            "y": ["a", "b", "a", "b", "a"],
        })
        schema = extract_training_schema(train_df)

        assert schema["x"]["min"] == 1.0
        assert schema["x"]["max"] == 5.0

        pred_df = pd.DataFrame({"x": [2.0], "y": ["a"]})
        is_valid, issues = validate_prediction_schema(pred_df, schema)
        assert is_valid is True
