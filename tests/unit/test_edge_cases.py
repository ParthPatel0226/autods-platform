"""Unit tests for validation/edge_case_detector.py.

Covers all 9 public edge-case detection functions plus the aggregate
``detect_all_edge_cases`` runner.  Each check has at minimum:
  - A positive case (edge case IS present).
  - A negative case (edge case is NOT present -- clean data).

Fixture dependencies (from tests/conftest.py):
  - sample_classification_df  (500 rows, columns: age, income, gender, region,
      tenure_months, num_products, has_credit_card, is_active, balance, churned)
  - sample_regression_df      (500 rows, columns: sqft, bedrooms, bathrooms,
      year_built, neighborhood, has_garage, lot_size, price)
  - sample_healthcare_df      (300 rows, columns: patient_id, age, gender,
      admission_type, diagnosis_code, num_medications, num_procedures,
      length_of_stay, insurance_type, readmitted_30day)
"""

import numpy as np
import pandas as pd
import pytest

from validation.edge_case_detector import (
    check_constant_columns,
    check_extreme_imbalance,
    check_high_cardinality,
    check_id_like_columns,
    check_perfect_correlation,
    check_single_class_target,
    check_target_leakage,
    check_too_few_rows,
    check_too_many_missing,
    detect_all_edge_cases,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_issue(issues: list[dict], issue_type: str) -> dict | None:
    """Return the first issue matching *issue_type*, or None."""
    for issue in issues:
        if issue["type"] == issue_type:
            return issue
    return None


def _assert_issue_schema(issue: dict) -> None:
    """Validate that an issue dict has the required keys and value types."""
    required_keys = {"type", "severity", "message", "suggestion", "affected_columns"}
    assert required_keys == set(issue.keys()), (
        f"Issue keys mismatch: expected {required_keys}, got {set(issue.keys())}"
    )
    assert isinstance(issue["type"], str)
    assert issue["severity"] in {"critical", "warning", "info"}
    assert isinstance(issue["message"], str) and len(issue["message"]) > 0
    assert isinstance(issue["suggestion"], str) and len(issue["suggestion"]) > 0
    assert isinstance(issue["affected_columns"], list)


# ===========================================================================
# 1. check_single_class_target
# ===========================================================================


class TestCheckSingleClassTarget:
    """Target column has only one unique value -- classification impossible."""

    def test_detects_single_class(self):
        df = pd.DataFrame({"feature": [1, 2, 3, 4, 5], "target": [1, 1, 1, 1, 1]})
        issues = check_single_class_target(df, "target")
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "single_class"
        assert issues[0]["severity"] == "critical"
        assert "target" in issues[0]["affected_columns"]

    def test_no_issue_with_two_classes(self, sample_classification_df):
        issues = check_single_class_target(sample_classification_df, "churned")
        assert len(issues) == 0

    def test_detects_zero_unique_values_all_null(self):
        df = pd.DataFrame({"feature": [1, 2, 3], "target": [None, None, None]})
        issues = check_single_class_target(df, "target")
        assert len(issues) == 1
        assert issues[0]["type"] == "single_class"

    def test_returns_empty_when_target_is_none(self, sample_classification_df):
        issues = check_single_class_target(sample_classification_df, None)
        assert issues == []

    def test_returns_empty_when_target_not_in_columns(self, sample_classification_df):
        issues = check_single_class_target(sample_classification_df, "nonexistent")
        assert issues == []

    def test_no_issue_with_multi_class(self):
        df = pd.DataFrame({"target": ["A", "B", "C", "A", "B"]})
        issues = check_single_class_target(df, "target")
        assert len(issues) == 0


# ===========================================================================
# 2. check_extreme_imbalance
# ===========================================================================


class TestCheckExtremeImbalance:
    """Minority class represents less than 1% of total rows."""

    def test_detects_extreme_imbalance(self):
        target = [0] * 999 + [1] * 1
        df = pd.DataFrame({"feature": range(1000), "target": target})
        issues = check_extreme_imbalance(df, "target")
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "extreme_imbalance"
        assert issues[0]["severity"] == "warning"
        assert "target" in issues[0]["affected_columns"]

    def test_no_issue_with_balanced_target(self, sample_classification_df):
        issues = check_extreme_imbalance(sample_classification_df, "churned")
        assert len(issues) == 0

    def test_custom_threshold(self):
        # 5% minority -- should trigger with threshold=0.10 but not 0.01
        target = [0] * 950 + [1] * 50
        df = pd.DataFrame({"feature": range(1000), "target": target})
        issues_strict = check_extreme_imbalance(df, "target", threshold=0.10)
        assert len(issues_strict) == 1
        issues_lenient = check_extreme_imbalance(df, "target", threshold=0.01)
        assert len(issues_lenient) == 0

    def test_returns_empty_when_target_is_none(self, sample_classification_df):
        issues = check_extreme_imbalance(sample_classification_df, None)
        assert issues == []

    def test_returns_empty_when_target_not_in_columns(self, sample_classification_df):
        issues = check_extreme_imbalance(sample_classification_df, "nonexistent")
        assert issues == []

    def test_message_contains_minority_class_ratio(self):
        target = [0] * 998 + [1] * 2
        df = pd.DataFrame({"feature": range(1000), "target": target})
        issues = check_extreme_imbalance(df, "target")
        assert len(issues) == 1
        assert "0.20%" in issues[0]["message"]


# ===========================================================================
# 3. check_target_leakage
# ===========================================================================


class TestCheckTargetLeakage:
    """Columns with suspiciously high correlation (> 0.95) to target."""

    def test_detects_leakage_with_perfect_correlation(self):
        np.random.seed(42)
        target = np.random.randint(0, 2, 200).astype(float)
        leaky = target * 2.0 + 0.5  # perfect linear relationship
        df = pd.DataFrame({
            "feature_a": np.random.randn(200),
            "leaky_col": leaky,
            "target": target,
        })
        issues = check_target_leakage(df, "target")
        assert len(issues) >= 1
        leakage_issue = _find_issue(issues, "leakage")
        assert leakage_issue is not None
        _assert_issue_schema(leakage_issue)
        assert leakage_issue["severity"] == "critical"
        assert "leaky_col" in leakage_issue["affected_columns"]
        assert "target" in leakage_issue["affected_columns"]

    def test_no_leakage_with_independent_features(self, sample_classification_df):
        issues = check_target_leakage(sample_classification_df, "churned")
        leakage_issues = [i for i in issues if i["type"] == "leakage"]
        assert len(leakage_issues) == 0

    def test_returns_empty_when_target_is_none(self, sample_classification_df):
        issues = check_target_leakage(sample_classification_df, None)
        assert issues == []

    def test_returns_empty_when_target_not_in_columns(self, sample_classification_df):
        issues = check_target_leakage(sample_classification_df, "nonexistent")
        assert issues == []

    def test_returns_empty_when_target_not_numeric(self):
        df = pd.DataFrame({
            "feature": [1, 2, 3, 4, 5],
            "target": ["A", "B", "A", "B", "A"],
        })
        issues = check_target_leakage(df, "target")
        assert issues == []

    def test_does_not_flag_moderate_correlation(self):
        np.random.seed(42)
        n = 500
        target = np.random.randn(n)
        # Moderate correlation (~0.7) should not trigger leakage
        moderate = target * 0.7 + np.random.randn(n) * 0.71
        df = pd.DataFrame({"moderate_col": moderate, "target": target})
        issues = check_target_leakage(df, "target")
        assert len(issues) == 0


# ===========================================================================
# 4. check_constant_columns
# ===========================================================================


class TestCheckConstantColumns:
    """Columns with only one unique non-null value."""

    def test_detects_constant_column(self):
        df = pd.DataFrame({
            "feature": [1, 2, 3, 4, 5],
            "constant": [42, 42, 42, 42, 42],
        })
        issues = check_constant_columns(df)
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "constant_column"
        assert issues[0]["severity"] == "warning"
        assert "constant" in issues[0]["affected_columns"]

    def test_no_issue_with_varied_columns(self, sample_classification_df):
        issues = check_constant_columns(sample_classification_df)
        assert len(issues) == 0

    def test_detects_all_null_column(self):
        df = pd.DataFrame({
            "feature": [1, 2, 3],
            "empty": [None, None, None],
        })
        issues = check_constant_columns(df)
        assert len(issues) >= 1
        null_issue = _find_issue(issues, "constant_column")
        assert null_issue is not None
        assert "empty" in null_issue["affected_columns"]

    def test_detects_multiple_constant_columns(self):
        df = pd.DataFrame({
            "a": [1, 2, 3],
            "const_1": ["x", "x", "x"],
            "const_2": [0, 0, 0],
        })
        issues = check_constant_columns(df)
        constant_issues = [i for i in issues if i["type"] == "constant_column"]
        assert len(constant_issues) == 2
        affected = {i["affected_columns"][0] for i in constant_issues}
        assert affected == {"const_1", "const_2"}

    def test_single_value_with_nulls_still_constant(self):
        df = pd.DataFrame({"col": [5, None, 5, None, 5]})
        issues = check_constant_columns(df)
        assert len(issues) == 1
        assert issues[0]["type"] == "constant_column"


# ===========================================================================
# 5. check_perfect_correlation (multicollinearity)
# ===========================================================================


class TestCheckPerfectCorrelation:
    """Pairs of numeric columns with near-perfect correlation (>=0.99)."""

    def test_detects_perfectly_correlated_pair(self):
        x = np.arange(100, dtype=float)
        df = pd.DataFrame({
            "x": x,
            "x_double": x * 2.0,
            "noise": np.random.default_rng(0).standard_normal(100),
        })
        issues = check_perfect_correlation(df)
        assert len(issues) >= 1
        corr_issue = _find_issue(issues, "perfect_correlation")
        assert corr_issue is not None
        _assert_issue_schema(corr_issue)
        assert corr_issue["severity"] == "warning"
        assert len(corr_issue["affected_columns"]) == 2

    def test_no_issue_with_independent_columns(self, sample_classification_df):
        issues = check_perfect_correlation(sample_classification_df)
        assert len(issues) == 0

    def test_returns_empty_with_single_numeric_column(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "label": ["a", "b", "c"]})
        issues = check_perfect_correlation(df)
        assert issues == []

    def test_custom_threshold(self):
        np.random.seed(42)
        n = 200
        x = np.arange(n, dtype=float)
        y = x + np.random.randn(n) * 0.5  # very high but not 0.99
        df = pd.DataFrame({"x": x, "y": y})
        # With default 0.99 threshold, might not trigger
        issues_strict = check_perfect_correlation(df, threshold=0.99)
        # With relaxed threshold, should trigger
        issues_relaxed = check_perfect_correlation(df, threshold=0.90)
        assert len(issues_relaxed) >= 1

    def test_negative_perfect_correlation_detected(self):
        x = np.arange(100, dtype=float)
        df = pd.DataFrame({"x": x, "neg_x": -x})
        issues = check_perfect_correlation(df)
        assert len(issues) >= 1
        assert abs(float(issues[0]["message"].split("of ")[-1].split(".")[0] + "." +
                        issues[0]["message"].split("of ")[-1].split(".")[1][:4])) >= 0.99

    def test_does_not_report_duplicate_pairs(self):
        x = np.arange(50, dtype=float)
        df = pd.DataFrame({"a": x, "b": x * 3.0, "c": np.random.randn(50)})
        issues = check_perfect_correlation(df)
        pair_types = [i for i in issues if i["type"] == "perfect_correlation"]
        # Should only report (a, b) once, not (a, b) AND (b, a)
        pairs_seen = set()
        for issue in pair_types:
            pair = frozenset(issue["affected_columns"])
            assert pair not in pairs_seen, "Duplicate pair detected"
            pairs_seen.add(pair)


# ===========================================================================
# 6. check_too_many_missing (mixed types proxy -- validates missing data)
# ===========================================================================


class TestCheckTooManyMissing:
    """Columns with more than 50% missing values."""

    def test_detects_column_with_many_missing(self):
        df = pd.DataFrame({
            "good": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "mostly_null": [None, None, None, None, None, None, 7, 8, None, None],
        })
        issues = check_too_many_missing(df)
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "too_many_missing"
        assert issues[0]["severity"] == "warning"
        assert "mostly_null" in issues[0]["affected_columns"]

    def test_no_issue_with_clean_data(self, sample_classification_df):
        issues = check_too_many_missing(sample_classification_df)
        assert len(issues) == 0

    def test_custom_threshold(self):
        df = pd.DataFrame({
            "col": [None, None, None, 4, 5, 6, 7, 8, 9, 10],
        })
        # 30% missing -- should trigger at threshold=0.20 but not 0.50
        issues_strict = check_too_many_missing(df, threshold=0.20)
        assert len(issues_strict) == 1
        issues_lenient = check_too_many_missing(df, threshold=0.50)
        assert len(issues_lenient) == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        issues = check_too_many_missing(df)
        assert issues == []

    def test_all_missing_column(self):
        df = pd.DataFrame({"col": [None, None, None, None, None]})
        issues = check_too_many_missing(df)
        assert len(issues) == 1
        assert "100%" in issues[0]["message"]


# ===========================================================================
# 7. check_too_few_rows
# ===========================================================================


class TestCheckTooFewRows:
    """Dataset has fewer than min_rows rows."""

    def test_detects_too_few_rows(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        issues = check_too_few_rows(df, min_rows=30)
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "too_few_rows"

    def test_critical_severity_under_10_rows(self):
        df = pd.DataFrame({"a": range(5)})
        issues = check_too_few_rows(df)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"

    def test_warning_severity_between_10_and_30(self):
        df = pd.DataFrame({"a": range(15)})
        issues = check_too_few_rows(df)
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_no_issue_with_sufficient_rows(self, sample_classification_df):
        issues = check_too_few_rows(sample_classification_df)
        assert len(issues) == 0

    def test_exact_boundary(self):
        df = pd.DataFrame({"a": range(30)})
        issues = check_too_few_rows(df, min_rows=30)
        assert len(issues) == 0

    def test_custom_min_rows(self):
        df = pd.DataFrame({"a": range(50)})
        issues = check_too_few_rows(df, min_rows=100)
        assert len(issues) == 1
        assert "50" in issues[0]["message"]

    def test_empty_dataframe(self):
        df = pd.DataFrame({"a": pd.Series(dtype=float)})
        issues = check_too_few_rows(df)
        assert len(issues) == 1
        assert issues[0]["severity"] == "critical"


# ===========================================================================
# 8. check_high_cardinality
# ===========================================================================


class TestCheckHighCardinality:
    """Categorical columns where unique values exceed threshold x rows."""

    def test_detects_high_cardinality(self):
        n = 100
        df = pd.DataFrame({
            "id_like": [f"user_{i}" for i in range(n)],
            "normal_cat": np.random.choice(["A", "B", "C"], n),
        })
        issues = check_high_cardinality(df)
        assert len(issues) == 1
        _assert_issue_schema(issues[0])
        assert issues[0]["type"] == "high_cardinality"
        assert issues[0]["severity"] == "warning"
        assert "id_like" in issues[0]["affected_columns"]

    def test_no_issue_with_low_cardinality(self, sample_classification_df):
        issues = check_high_cardinality(sample_classification_df)
        assert len(issues) == 0

    def test_ignores_numeric_columns(self):
        df = pd.DataFrame({"numeric_unique": range(100)})
        issues = check_high_cardinality(df)
        assert len(issues) == 0

    def test_custom_threshold(self):
        n = 100
        # 50 unique values out of 100 = 0.50 ratio
        df = pd.DataFrame({
            "col": [f"val_{i % 50}" for i in range(n)],
        })
        issues_strict = check_high_cardinality(df, threshold=0.40)
        assert len(issues_strict) == 1
        issues_lenient = check_high_cardinality(df, threshold=0.60)
        assert len(issues_lenient) == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame({"col": pd.Series(dtype=str)})
        issues = check_high_cardinality(df)
        assert issues == []

    def test_message_contains_cardinality_stats(self):
        n = 50
        df = pd.DataFrame({"col": [f"v_{i}" for i in range(n)]})
        issues = check_high_cardinality(df)
        assert len(issues) == 1
        assert "50" in issues[0]["message"]


# ===========================================================================
# 9. check_id_like_columns
# ===========================================================================


class TestCheckIdLikeColumns:
    """Detect columns that look like row identifiers."""

    def test_detects_column_named_id(self):
        df = pd.DataFrame({"id": range(10), "value": range(10, 20)})
        issues = check_id_like_columns(df)
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        assert len(id_issues) >= 1
        assert "id" in id_issues[0]["affected_columns"]

    def test_detects_patient_id_pattern(self, sample_healthcare_df):
        issues = check_id_like_columns(sample_healthcare_df)
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        patient_id_found = any(
            "patient_id" in issue["affected_columns"] for issue in id_issues
        )
        assert patient_id_found

    def test_detects_sequential_integers(self):
        df = pd.DataFrame({
            "seq": range(1, 51),
            "value": np.random.randn(50),
        })
        issues = check_id_like_columns(df)
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        assert len(id_issues) >= 1
        seq_issue = _find_issue(id_issues, "id_like_column")
        assert "sequential" in seq_issue["message"]

    def test_detects_all_unique_values(self):
        df = pd.DataFrame({
            "unique_col": [f"item_{i}" for i in range(20)],
            "normal": ["A", "B"] * 10,
        })
        issues = check_id_like_columns(df)
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        unique_found = any(
            "unique_col" in issue["affected_columns"] for issue in id_issues
        )
        assert unique_found

    def test_no_issue_with_non_id_columns(self):
        df = pd.DataFrame({
            "age": [25, 30, 35, 25, 30],
            "category": ["A", "B", "A", "B", "A"],
        })
        issues = check_id_like_columns(df)
        assert len(issues) == 0

    def test_severity_is_info(self):
        df = pd.DataFrame({"row_id": range(20), "value": range(20)})
        issues = check_id_like_columns(df)
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        for issue in id_issues:
            assert issue["severity"] == "info"

    def test_name_patterns_recognized(self):
        """Various ID-like column names should all be detected."""
        for name in ["id", "index", "row_id", "user_pk", "uuid", "order_key"]:
            df = pd.DataFrame({name: range(10), "value": range(10, 20)})
            issues = check_id_like_columns(df)
            id_issues = [i for i in issues if i["type"] == "id_like_column"]
            assert len(id_issues) >= 1, f"Column name '{name}' was not detected as ID-like"

    def test_empty_dataframe(self):
        df = pd.DataFrame({"id": pd.Series(dtype=int)})
        issues = check_id_like_columns(df)
        assert issues == []


# ===========================================================================
# 10. detect_all_edge_cases (aggregate runner)
# ===========================================================================


class TestDetectAllEdgeCases:
    """Aggregate runner that combines all individual checks."""

    def test_clean_data_returns_no_critical_issues(self, sample_classification_df):
        issues = detect_all_edge_cases(sample_classification_df, target_column="churned")
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        assert len(critical_issues) == 0

    def test_returns_list(self, sample_classification_df):
        result = detect_all_edge_cases(sample_classification_df)
        assert isinstance(result, list)

    def test_all_issues_have_valid_schema(self, sample_classification_df):
        issues = detect_all_edge_cases(sample_classification_df, target_column="churned")
        for issue in issues:
            _assert_issue_schema(issue)

    def test_sorted_by_severity_critical_first(self):
        """Critical issues must appear before warning, which must appear before info."""
        np.random.seed(42)
        # Build a dataframe that triggers multiple severity levels:
        # - single_class target (critical)
        # - constant column (warning)
        # - id-like column (info)
        df = pd.DataFrame({
            "id": range(50),
            "constant": [99] * 50,
            "feature": np.random.randn(50),
            "target": [1] * 50,
        })
        issues = detect_all_edge_cases(df, target_column="target")
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(issues) - 1):
            current = severity_order.get(issues[i]["severity"], 3)
            next_val = severity_order.get(issues[i + 1]["severity"], 3)
            assert current <= next_val, (
                f"Issues not sorted: {issues[i]['severity']} before {issues[i + 1]['severity']}"
            )

    def test_target_checks_skipped_when_target_is_none(self, sample_classification_df):
        issues = detect_all_edge_cases(sample_classification_df, target_column=None)
        target_types = {"single_class", "extreme_imbalance", "leakage"}
        for issue in issues:
            assert issue["type"] not in target_types

    def test_target_checks_skipped_when_target_not_in_columns(
        self, sample_classification_df
    ):
        issues = detect_all_edge_cases(
            sample_classification_df, target_column="nonexistent"
        )
        target_types = {"single_class", "extreme_imbalance", "leakage"}
        for issue in issues:
            assert issue["type"] not in target_types

    def test_detects_multiple_issues_simultaneously(self):
        """A deliberately problematic dataset should trigger several checks."""
        df = pd.DataFrame({
            "id": range(5),
            "constant": ["x"] * 5,
            "target": [0, 0, 0, 0, 0],
        })
        issues = detect_all_edge_cases(df, target_column="target")
        issue_types = {i["type"] for i in issues}
        # Should find at least: single_class, constant_column, too_few_rows
        assert "single_class" in issue_types
        assert "constant_column" in issue_types
        assert "too_few_rows" in issue_types

    def test_healthcare_data_detects_id_column(self, sample_healthcare_df):
        issues = detect_all_edge_cases(
            sample_healthcare_df, target_column="readmitted_30day"
        )
        id_issues = [i for i in issues if i["type"] == "id_like_column"]
        patient_id_found = any(
            "patient_id" in issue["affected_columns"] for issue in id_issues
        )
        assert patient_id_found

    def test_leakage_detected_in_aggregate(self):
        np.random.seed(42)
        target = np.random.randint(0, 2, 100).astype(float)
        df = pd.DataFrame({
            "feature": np.random.randn(100),
            "leaked": target * 3.0 + 1.0,
            "target": target,
        })
        issues = detect_all_edge_cases(df, target_column="target")
        leakage_found = any(i["type"] == "leakage" for i in issues)
        assert leakage_found

    def test_empty_dataframe_does_not_crash(self):
        df = pd.DataFrame()
        issues = detect_all_edge_cases(df)
        assert isinstance(issues, list)
