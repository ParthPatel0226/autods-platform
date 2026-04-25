"""Unit tests for agents/tools/viz_tools.py.

Tests verify that every chart function:
  - Returns a dict with exactly the keys: figure, title, description, insights
  - Returns a go.Figure instance in the "figure" key
  - Returns a list in the "insights" key
  - Does not raise on valid input

Functions are grouped into classes that mirror the source file sections:
  - TestDistributionPlots   (histogram, box_plot, violin_plot, qq_plot)
  - TestRelationshipPlots   (scatter_plot, correlation_heatmap, pair_plot)
  - TestCategoricalPlots    (bar_chart, pie_chart, heatmap)
  - TestTimeSeriesPlots     (line_chart, time_series_plot)
  - TestModelEvalPlots      (residual_plot, confusion_matrix_plot, roc_curve_plot,
                              pr_curve_plot, calibration_curve_plot, gain_lift_plot)
  - TestExplainabilityPlots (shap_summary_plot, shap_force_plot,
                              feature_importance_plot, pdp_plot)
  - TestBusinessPlots       (funnel_chart, cohort_retention_plot, survival_curve_plot)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from sklearn.tree import DecisionTreeClassifier

from agents.tools.viz_tools import (
    bar_chart,
    box_plot,
    calibration_curve_plot,
    cohort_retention_plot,
    confusion_matrix_plot,
    correlation_heatmap,
    feature_importance_plot,
    funnel_chart,
    gain_lift_plot,
    heatmap,
    histogram,
    line_chart,
    pair_plot,
    pdp_plot,
    pie_chart,
    pr_curve_plot,
    qq_plot,
    residual_plot,
    roc_curve_plot,
    scatter_plot,
    shap_force_plot,
    shap_summary_plot,
    survival_curve_plot,
    time_series_plot,
    violin_plot,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"figure", "title", "description", "insights"}


# ---------------------------------------------------------------------------
# Shared assertion helpers
# ---------------------------------------------------------------------------

def _assert_result_shape(result: dict) -> None:
    """Assert the canonical shape every viz function must return."""
    assert isinstance(result, dict), "Result must be a dict"
    assert set(result.keys()) == REQUIRED_KEYS, (
        f"Expected keys {REQUIRED_KEYS}, got {set(result.keys())}"
    )
    assert isinstance(result["figure"], go.Figure), (
        "result['figure'] must be a go.Figure instance"
    )
    assert isinstance(result["title"], str), "result['title'] must be a str"
    assert isinstance(result["description"], str), "result['description'] must be a str"
    assert isinstance(result["insights"], list), "result['insights'] must be a list"


# ---------------------------------------------------------------------------
# Module-level fixtures (shared across all test classes)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def clf_df():
    """500-row classification DataFrame."""
    rng = np.random.default_rng(0)
    n = 500
    return pd.DataFrame({
        "age": rng.integers(18, 80, n),
        "income": rng.lognormal(10, 1, n).astype(int),
        "gender": rng.choice(["M", "F"], n),
        "region": rng.choice(["North", "South", "East", "West"], n),
        "tenure_months": rng.integers(1, 120, n),
        "num_products": rng.integers(1, 5, n),
        "balance": rng.lognormal(8, 2, n),
        "churned": rng.choice([0, 1], n, p=[0.8, 0.2]),
    })


@pytest.fixture(scope="module")
def reg_df():
    """500-row regression DataFrame with a datetime column."""
    rng = np.random.default_rng(1)
    n = 500
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "sqft": rng.integers(500, 5000, n),
        "bedrooms": rng.integers(1, 6, n),
        "bathrooms": rng.integers(1, 4, n),
        "neighborhood": rng.choice(["A", "B", "C", "D"], n),
        "price": rng.lognormal(12, 0.5, n).astype(int),
        "date": dates,
    })


@pytest.fixture(scope="module")
def binary_arrays():
    """Matching y_true / y_scores arrays for classification metric plots."""
    rng = np.random.default_rng(42)
    y_true = rng.integers(0, 2, 200)
    # Scores correlated with labels to produce a non-degenerate ROC / PR curve
    y_scores = np.clip(y_true * 0.6 + rng.uniform(0, 0.4, 200), 0, 1)
    return y_true, y_scores


@pytest.fixture(scope="module")
def regression_arrays():
    """Matching y_true / y_pred arrays for residual plots."""
    rng = np.random.default_rng(7)
    y_true = rng.uniform(0, 100, 300)
    y_pred = y_true + rng.normal(0, 5, 300)
    return y_true, y_pred


@pytest.fixture(scope="module")
def shap_arrays():
    """SHAP values matrix and corresponding feature names."""
    rng = np.random.default_rng(3)
    n_samples, n_features = 100, 8
    feature_names = [f"feat_{i}" for i in range(n_features)]
    shap_values = rng.standard_normal((n_samples, n_features))
    return shap_values, feature_names


@pytest.fixture(scope="module")
def pdp_model_and_data():
    """Fitted DecisionTreeClassifier and the DataFrame it was trained on."""
    rng = np.random.default_rng(5)
    n = 300
    X = pd.DataFrame({
        "age": rng.integers(18, 80, n),
        "income": rng.lognormal(10, 1, n).astype(int),
        "score": rng.uniform(0, 1, n),
    })
    y = (X["income"] > X["income"].median()).astype(int)
    model = DecisionTreeClassifier(max_depth=3, random_state=0)
    model.fit(X, y)
    return model, X


@pytest.fixture(scope="module")
def cohort_df():
    """Small cohort retention DataFrame."""
    rows = []
    for cohort in ["2023-Q1", "2023-Q2", "2023-Q3"]:
        for period in [0, 1, 2, 3]:
            rows.append({
                "cohort": cohort,
                "period": period,
                "retention_rate": max(0.0, 1.0 - period * 0.15 + np.random.default_rng(period).uniform(-0.05, 0.05)),
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def survival_input():
    """Minimal survival curve input dict."""
    t = list(range(0, 60, 5))
    prob = [1.0, 0.95, 0.88, 0.78, 0.65, 0.55, 0.45, 0.38, 0.30, 0.24, 0.18, 0.14]
    return {"time": t, "survival_prob": prob}


@pytest.fixture(scope="module")
def survival_input_with_ci():
    """Survival curve input dict that includes confidence interval bands."""
    t = list(range(0, 60, 5))
    prob = [1.0, 0.95, 0.88, 0.78, 0.65, 0.55, 0.45, 0.38, 0.30, 0.24, 0.18, 0.14]
    ci_upper = [min(1.0, p + 0.05) for p in prob]
    ci_lower = [max(0.0, p - 0.05) for p in prob]
    return {
        "time": t,
        "survival_prob": prob,
        "ci_upper": ci_upper,
        "ci_lower": ci_lower,
    }


# ---------------------------------------------------------------------------
# TestDistributionPlots
# ---------------------------------------------------------------------------

class TestHistogram:
    """Tests for agents.tools.viz_tools.histogram."""

    def test_returns_required_keys(self, clf_df):
        result = histogram(clf_df, "age")
        _assert_result_shape(result)

    def test_insights_is_non_empty_list(self, clf_df):
        result = histogram(clf_df, "age")
        assert len(result["insights"]) >= 1

    def test_custom_bins(self, clf_df):
        result = histogram(clf_df, "income", bins=50)
        _assert_result_shape(result)

    def test_color_by_categorical(self, clf_df):
        result = histogram(clf_df, "age", color_by="gender")
        _assert_result_shape(result)

    def test_title_contains_column_name(self, clf_df):
        result = histogram(clf_df, "balance")
        assert "balance" in result["title"].lower()

    def test_skewness_insight_present(self, clf_df):
        result = histogram(clf_df, "income")
        insight_text = " ".join(result["insights"])
        assert "skew" in insight_text.lower()


class TestBoxPlot:
    """Tests for agents.tools.viz_tools.box_plot."""

    def test_returns_required_keys(self, clf_df):
        result = box_plot(clf_df, "age")
        _assert_result_shape(result)

    def test_without_group_by(self, clf_df):
        result = box_plot(clf_df, "balance")
        _assert_result_shape(result)

    def test_with_group_by(self, clf_df):
        result = box_plot(clf_df, "age", group_by="gender")
        _assert_result_shape(result)

    def test_iqr_insight_present(self, clf_df):
        result = box_plot(clf_df, "age")
        insight_text = " ".join(result["insights"])
        assert "iqr" in insight_text.lower()

    def test_title_contains_column(self, clf_df):
        result = box_plot(clf_df, "age")
        assert "age" in result["title"].lower()


class TestViolinPlot:
    """Tests for agents.tools.viz_tools.violin_plot."""

    def test_returns_required_keys(self, clf_df):
        result = violin_plot(clf_df, "age")
        _assert_result_shape(result)

    def test_without_group(self, clf_df):
        result = violin_plot(clf_df, "income")
        _assert_result_shape(result)

    def test_with_group_by(self, clf_df):
        result = violin_plot(clf_df, "age", group_by="region")
        _assert_result_shape(result)

    def test_insights_contains_mean_std(self, clf_df):
        result = violin_plot(clf_df, "age")
        insight_text = " ".join(result["insights"])
        assert "mean" in insight_text.lower()
        assert "std" in insight_text.lower()


class TestQQPlot:
    """Tests for agents.tools.viz_tools.qq_plot."""

    def test_returns_required_keys(self, clf_df):
        result = qq_plot(clf_df, "age")
        _assert_result_shape(result)

    def test_figure_has_two_traces(self, clf_df):
        # Scatter data points + theoretical line
        result = qq_plot(clf_df, "age")
        assert len(result["figure"].data) == 2

    def test_insights_contain_shapiro_pvalue(self, clf_df):
        result = qq_plot(clf_df, "income")
        insight_text = " ".join(result["insights"])
        assert "shapiro" in insight_text.lower() or "p-value" in insight_text.lower()

    def test_insights_contain_normality_statement(self, clf_df):
        result = qq_plot(clf_df, "age")
        insight_text = " ".join(result["insights"])
        assert "normal" in insight_text.lower()


# ---------------------------------------------------------------------------
# TestRelationshipPlots
# ---------------------------------------------------------------------------

class TestScatterPlot:
    """Tests for agents.tools.viz_tools.scatter_plot."""

    def test_returns_required_keys(self, clf_df):
        result = scatter_plot(clf_df, "age", "income")
        _assert_result_shape(result)

    def test_with_color_by(self, clf_df):
        result = scatter_plot(clf_df, "age", "income", color_by="gender")
        _assert_result_shape(result)

    def test_with_size_by(self, clf_df):
        result = scatter_plot(clf_df, "age", "balance", size_by="num_products")
        _assert_result_shape(result)

    def test_pearson_r_insight(self, clf_df):
        result = scatter_plot(clf_df, "age", "income")
        insight_text = " ".join(result["insights"])
        assert "pearson" in insight_text.lower() or "r =" in insight_text.lower()

    def test_title_contains_both_columns(self, clf_df):
        result = scatter_plot(clf_df, "age", "income")
        assert "income" in result["title"] and "age" in result["title"]


class TestCorrelationHeatmap:
    """Tests for agents.tools.viz_tools.correlation_heatmap."""

    def test_returns_required_keys(self, clf_df):
        result = correlation_heatmap(clf_df)
        _assert_result_shape(result)

    def test_explicit_columns(self, clf_df):
        result = correlation_heatmap(clf_df, columns=["age", "income", "balance"])
        _assert_result_shape(result)

    def test_spearman_method(self, clf_df):
        result = correlation_heatmap(clf_df, method="spearman")
        _assert_result_shape(result)
        assert "spearman" in result["title"].lower()

    def test_kendall_method(self, clf_df):
        result = correlation_heatmap(clf_df, method="kendall")
        _assert_result_shape(result)

    def test_insights_contain_pair_info(self, clf_df):
        result = correlation_heatmap(clf_df, columns=["age", "income", "balance"])
        # Should mention at least one correlation pair
        assert len(result["insights"]) >= 1


class TestPairPlot:
    """Tests for agents.tools.viz_tools.pair_plot."""

    def test_returns_required_keys(self, clf_df):
        result = pair_plot(clf_df, columns=["age", "income", "balance"])
        _assert_result_shape(result)

    def test_with_color_by(self, clf_df):
        result = pair_plot(clf_df, columns=["age", "income", "balance"], color_by="gender")
        _assert_result_shape(result)

    def test_max_cols_respected(self, clf_df):
        # Request more columns than max_cols — function should silently cap
        many_cols = ["age", "income", "balance", "tenure_months", "num_products", "churned", "has_credit_card"]
        result = pair_plot(clf_df, columns=many_cols, max_cols=4)
        _assert_result_shape(result)

    def test_insights_mention_features(self, clf_df):
        result = pair_plot(clf_df, columns=["age", "income", "balance"])
        insight_text = " ".join(result["insights"])
        assert "feature" in insight_text.lower()


# ---------------------------------------------------------------------------
# TestCategoricalPlots
# ---------------------------------------------------------------------------

class TestBarChart:
    """Tests for agents.tools.viz_tools.bar_chart."""

    def test_returns_required_keys_counts_only(self, clf_df):
        result = bar_chart(clf_df, x_col="region")
        _assert_result_shape(result)

    def test_with_value_column(self, clf_df):
        result = bar_chart(clf_df, x_col="region", y_col="income")
        _assert_result_shape(result)

    def test_horizontal_orientation(self, clf_df):
        result = bar_chart(clf_df, x_col="region", orientation="h")
        _assert_result_shape(result)

    def test_insights_mention_top_category(self, clf_df):
        result = bar_chart(clf_df, x_col="region")
        insight_text = " ".join(result["insights"])
        assert "%" in insight_text

    def test_insights_mention_unique_categories(self, clf_df):
        result = bar_chart(clf_df, x_col="region")
        insight_text = " ".join(result["insights"])
        assert "categor" in insight_text.lower()


class TestPieChart:
    """Tests for agents.tools.viz_tools.pie_chart."""

    def test_returns_required_keys(self, clf_df):
        result = pie_chart(clf_df, labels_col="region")
        _assert_result_shape(result)

    def test_with_values_column(self, reg_df):
        # Create a simple aggregated df to use values_col
        agg = reg_df.groupby("neighborhood")["price"].mean().reset_index()
        result = pie_chart(agg, labels_col="neighborhood", values_col="price")
        _assert_result_shape(result)

    def test_insights_contain_largest_segment(self, clf_df):
        result = pie_chart(clf_df, labels_col="region")
        insight_text = " ".join(result["insights"])
        assert "largest" in insight_text.lower() or "%" in insight_text


class TestHeatmap:
    """Tests for agents.tools.viz_tools.heatmap."""

    def test_returns_required_keys(self, reg_df):
        # Build a small df with two categorical axes and a numeric value
        df = pd.DataFrame({
            "x_cat": ["A", "A", "B", "B", "C", "C"],
            "y_cat": ["X", "Y", "X", "Y", "X", "Y"],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        })
        result = heatmap(df, x_col="x_cat", y_col="y_cat", value_col="value")
        _assert_result_shape(result)

    def test_insights_contain_range(self):
        df = pd.DataFrame({
            "x_cat": ["A", "A", "B", "B"],
            "y_cat": ["X", "Y", "X", "Y"],
            "value": [10.0, 20.0, 30.0, 40.0],
        })
        result = heatmap(df, x_col="x_cat", y_col="y_cat", value_col="value")
        insight_text = " ".join(result["insights"])
        assert "range" in insight_text.lower() or "10" in insight_text


# ---------------------------------------------------------------------------
# TestTimeSeriesPlots
# ---------------------------------------------------------------------------

class TestLineChart:
    """Tests for agents.tools.viz_tools.line_chart."""

    def test_returns_required_keys(self, reg_df):
        result = line_chart(reg_df, x_col="sqft", y_col="price")
        _assert_result_shape(result)

    def test_with_group_by(self, reg_df):
        result = line_chart(reg_df, x_col="sqft", y_col="price", group_by="neighborhood")
        _assert_result_shape(result)

    def test_insights_contain_range(self, reg_df):
        result = line_chart(reg_df, x_col="sqft", y_col="price")
        insight_text = " ".join(result["insights"])
        assert "range" in insight_text.lower()

    def test_title_contains_column_names(self, reg_df):
        result = line_chart(reg_df, x_col="sqft", y_col="price")
        assert "price" in result["title"] and "sqft" in result["title"]


class TestTimeSeriesPlot:
    """Tests for agents.tools.viz_tools.time_series_plot."""

    def test_returns_required_keys(self, reg_df):
        result = time_series_plot(reg_df, date_col="date", value_col="price")
        _assert_result_shape(result)

    def test_with_resample(self, reg_df):
        result = time_series_plot(reg_df, date_col="date", value_col="price", resample="ME")
        _assert_result_shape(result)

    def test_insights_contain_overall_change(self, reg_df):
        result = time_series_plot(reg_df, date_col="date", value_col="price")
        insight_text = " ".join(result["insights"])
        assert "change" in insight_text.lower() or "%" in insight_text

    def test_insights_contain_mean_std(self, reg_df):
        result = time_series_plot(reg_df, date_col="date", value_col="price")
        insight_text = " ".join(result["insights"])
        assert "mean" in insight_text.lower()


# ---------------------------------------------------------------------------
# TestModelEvalPlots
# ---------------------------------------------------------------------------

class TestResidualPlot:
    """Tests for agents.tools.viz_tools.residual_plot."""

    def test_returns_required_keys(self, regression_arrays):
        y_true, y_pred = regression_arrays
        result = residual_plot(y_true, y_pred)
        _assert_result_shape(result)

    def test_accepts_lists(self):
        y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_pred = [1.1, 1.9, 3.2, 3.8, 5.1]
        result = residual_plot(y_true, y_pred)
        _assert_result_shape(result)

    def test_insights_contain_mean_residual(self, regression_arrays):
        y_true, y_pred = regression_arrays
        result = residual_plot(y_true, y_pred)
        insight_text = " ".join(result["insights"])
        assert "mean" in insight_text.lower() or "residual" in insight_text.lower()

    def test_figure_has_scatter_trace(self, regression_arrays):
        y_true, y_pred = regression_arrays
        result = residual_plot(y_true, y_pred)
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Scatter" in trace_types


class TestConfusionMatrixPlot:
    """Tests for agents.tools.viz_tools.confusion_matrix_plot."""

    def test_returns_required_keys(self, binary_arrays):
        y_true, y_scores = binary_arrays
        y_pred = (y_scores >= 0.5).astype(int)
        result = confusion_matrix_plot(y_true, y_pred)
        _assert_result_shape(result)

    def test_with_explicit_labels(self, binary_arrays):
        y_true, y_scores = binary_arrays
        y_pred = (y_scores >= 0.5).astype(int)
        result = confusion_matrix_plot(y_true, y_pred, labels=["No", "Yes"])
        _assert_result_shape(result)

    def test_multiclass_input(self):
        rng = np.random.default_rng(9)
        y_true = rng.integers(0, 4, 120)
        y_pred = rng.integers(0, 4, 120)
        result = confusion_matrix_plot(y_true, y_pred)
        _assert_result_shape(result)

    def test_insights_contain_accuracy(self, binary_arrays):
        y_true, y_scores = binary_arrays
        y_pred = (y_scores >= 0.5).astype(int)
        result = confusion_matrix_plot(y_true, y_pred)
        insight_text = " ".join(result["insights"])
        assert "accuracy" in insight_text.lower()


class TestRocCurvePlot:
    """Tests for agents.tools.viz_tools.roc_curve_plot."""

    def test_returns_required_keys(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = roc_curve_plot(y_true, y_scores)
        _assert_result_shape(result)

    def test_insights_contain_auc(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = roc_curve_plot(y_true, y_scores)
        insight_text = " ".join(result["insights"])
        assert "auc" in insight_text.lower()

    def test_with_model_names(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = roc_curve_plot(y_true, y_scores, model_names=["MyModel"])
        _assert_result_shape(result)
        assert "MyModel" in " ".join(result["insights"])

    def test_multiple_models(self, binary_arrays):
        y_true, y_scores = binary_arrays
        rng = np.random.default_rng(11)
        y_scores_2 = np.clip(
            y_true * 0.5 + rng.uniform(0, 0.5, len(y_true)), 0, 1
        )
        two_score_matrix = np.column_stack([y_scores, y_scores_2])
        result = roc_curve_plot(y_true, two_score_matrix, model_names=["M1", "M2"])
        _assert_result_shape(result)
        assert len(result["insights"]) == 2

    def test_figure_has_diagonal_reference_line(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = roc_curve_plot(y_true, y_scores)
        # Random classifier diagonal should be present as a Scatter trace
        assert len(result["figure"].data) >= 2


class TestPRCurvePlot:
    """Tests for agents.tools.viz_tools.pr_curve_plot."""

    def test_returns_required_keys(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = pr_curve_plot(y_true, y_scores)
        _assert_result_shape(result)

    def test_insights_contain_ap(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = pr_curve_plot(y_true, y_scores)
        insight_text = " ".join(result["insights"])
        assert "ap" in insight_text.lower() or "average precision" in insight_text.lower()

    def test_with_model_names(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = pr_curve_plot(y_true, y_scores, model_names=["Classifier"])
        _assert_result_shape(result)

    def test_multiple_models(self, binary_arrays):
        y_true, y_scores = binary_arrays
        rng = np.random.default_rng(13)
        scores2 = np.clip(y_true * 0.4 + rng.uniform(0, 0.6, len(y_true)), 0, 1)
        matrix = np.column_stack([y_scores, scores2])
        result = pr_curve_plot(y_true, matrix, model_names=["A", "B"])
        _assert_result_shape(result)
        assert len(result["insights"]) == 2


class TestCalibrationCurvePlot:
    """Tests for agents.tools.viz_tools.calibration_curve_plot."""

    def test_returns_required_keys(self, binary_arrays):
        y_true, y_probs = binary_arrays
        result = calibration_curve_plot(y_true, y_probs)
        _assert_result_shape(result)

    def test_custom_n_bins(self, binary_arrays):
        y_true, y_probs = binary_arrays
        result = calibration_curve_plot(y_true, y_probs, n_bins=5)
        _assert_result_shape(result)

    def test_insights_contain_brier_score(self, binary_arrays):
        y_true, y_probs = binary_arrays
        result = calibration_curve_plot(y_true, y_probs)
        insight_text = " ".join(result["insights"])
        assert "brier" in insight_text.lower()

    def test_figure_has_model_and_reference_traces(self, binary_arrays):
        y_true, y_probs = binary_arrays
        result = calibration_curve_plot(y_true, y_probs)
        assert len(result["figure"].data) == 2


class TestGainLiftPlot:
    """Tests for agents.tools.viz_tools.gain_lift_plot."""

    def test_returns_required_keys(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = gain_lift_plot(y_true, y_scores)
        _assert_result_shape(result)

    def test_insights_contain_top10_stats(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = gain_lift_plot(y_true, y_scores)
        insight_text = " ".join(result["insights"])
        assert "10%" in insight_text

    def test_figure_has_subplots(self, binary_arrays):
        y_true, y_scores = binary_arrays
        result = gain_lift_plot(y_true, y_scores)
        # Gain + Lift subplots means at least 3 traces (gain, random, lift)
        assert len(result["figure"].data) >= 3


# ---------------------------------------------------------------------------
# TestExplainabilityPlots
# ---------------------------------------------------------------------------

class TestShapSummaryPlot:
    """Tests for agents.tools.viz_tools.shap_summary_plot."""

    def test_returns_required_keys(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_summary_plot(shap_values, feature_names)
        _assert_result_shape(result)

    def test_insights_mention_top_feature(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_summary_plot(shap_values, feature_names)
        assert len(result["insights"]) >= 1
        insight_text = " ".join(result["insights"])
        assert "top" in insight_text.lower() or "feat_" in insight_text

    def test_figure_has_box_traces(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_summary_plot(shap_values, feature_names)
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Box" in trace_types

    def test_caps_at_twenty_features(self):
        rng = np.random.default_rng(17)
        n_features = 30
        shap_values = rng.standard_normal((50, n_features))
        feature_names = [f"f{i}" for i in range(n_features)]
        result = shap_summary_plot(shap_values, feature_names)
        _assert_result_shape(result)
        # At most 20 traces rendered
        assert len(result["figure"].data) <= 20


class TestShapForcePlot:
    """Tests for agents.tools.viz_tools.shap_force_plot."""

    def test_returns_required_keys(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_force_plot(
            shap_values=shap_values,
            base_value=0.42,
            feature_names=feature_names,
            instance_idx=0,
        )
        _assert_result_shape(result)

    def test_insights_contain_base_value(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_force_plot(
            shap_values=shap_values,
            base_value=0.42,
            feature_names=feature_names,
            instance_idx=0,
        )
        insight_text = " ".join(result["insights"])
        assert "base" in insight_text.lower()

    def test_insights_contain_prediction(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_force_plot(
            shap_values=shap_values,
            base_value=0.0,
            feature_names=feature_names,
            instance_idx=5,
        )
        insight_text = " ".join(result["insights"])
        assert "prediction" in insight_text.lower()

    def test_title_contains_instance_idx(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_force_plot(
            shap_values=shap_values,
            base_value=0.0,
            feature_names=feature_names,
            instance_idx=3,
        )
        assert "3" in result["title"]

    def test_figure_has_bar_trace(self, shap_arrays):
        shap_values, feature_names = shap_arrays
        result = shap_force_plot(
            shap_values=shap_values,
            base_value=0.0,
            feature_names=feature_names,
            instance_idx=0,
        )
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Bar" in trace_types


class TestFeatureImportancePlot:
    """Tests for agents.tools.viz_tools.feature_importance_plot."""

    def test_returns_required_keys(self):
        importances = {"age": 0.35, "income": 0.25, "tenure": 0.20, "balance": 0.10, "products": 0.10}
        result = feature_importance_plot(importances)
        _assert_result_shape(result)

    def test_insights_mention_top_feature(self):
        importances = {"age": 0.5, "income": 0.3, "tenure": 0.2}
        result = feature_importance_plot(importances)
        insight_text = " ".join(result["insights"])
        assert "age" in insight_text

    def test_top_n_respected(self):
        importances = {f"feat_{i}": 1.0 / (i + 1) for i in range(30)}
        result = feature_importance_plot(importances, top_n=10)
        _assert_result_shape(result)
        # Only up to 10 bars should appear
        n_bars = len(result["figure"].data[0].x)
        assert n_bars <= 10

    def test_single_feature(self):
        result = feature_importance_plot({"only_feature": 1.0})
        _assert_result_shape(result)
        assert len(result["insights"]) >= 1


class TestPdpPlot:
    """Tests for agents.tools.viz_tools.pdp_plot."""

    def test_returns_required_keys(self, pdp_model_and_data):
        model, X = pdp_model_and_data
        result = pdp_plot(model, X, feature="age", feature_name="Age")
        _assert_result_shape(result)

    def test_insights_contain_pd_range(self, pdp_model_and_data):
        model, X = pdp_model_and_data
        result = pdp_plot(model, X, feature="income", feature_name="Income")
        insight_text = " ".join(result["insights"])
        assert "range" in insight_text.lower() or "pd" in insight_text.lower()

    def test_figure_has_scatter_trace(self, pdp_model_and_data):
        model, X = pdp_model_and_data
        result = pdp_plot(model, X, feature="score", feature_name="Score")
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Scatter" in trace_types

    def test_title_contains_feature_name(self, pdp_model_and_data):
        model, X = pdp_model_and_data
        result = pdp_plot(model, X, feature="age", feature_name="Patient Age")
        assert "Patient Age" in result["title"]


# ---------------------------------------------------------------------------
# TestBusinessPlots
# ---------------------------------------------------------------------------

class TestFunnelChart:
    """Tests for agents.tools.viz_tools.funnel_chart."""

    _STAGES = [
        {"name": "Visitors", "value": 10000},
        {"name": "Sign-ups", "value": 3500},
        {"name": "Activated", "value": 1200},
        {"name": "Converted", "value": 400},
        {"name": "Retained", "value": 150},
    ]

    def test_returns_required_keys(self):
        result = funnel_chart(self._STAGES)
        _assert_result_shape(result)

    def test_insights_contain_overall_conversion(self):
        result = funnel_chart(self._STAGES)
        insight_text = " ".join(result["insights"])
        assert "conversion" in insight_text.lower() or "%" in insight_text

    def test_insights_contain_biggest_dropoff(self):
        result = funnel_chart(self._STAGES)
        insight_text = " ".join(result["insights"])
        assert "drop" in insight_text.lower()

    def test_two_stage_funnel(self):
        stages = [{"name": "Start", "value": 1000}, {"name": "End", "value": 250}]
        result = funnel_chart(stages)
        _assert_result_shape(result)

    def test_figure_has_funnel_trace(self):
        result = funnel_chart(self._STAGES)
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Funnel" in trace_types


class TestCohortRetentionPlot:
    """Tests for agents.tools.viz_tools.cohort_retention_plot."""

    def test_returns_required_keys(self, cohort_df):
        result = cohort_retention_plot(
            cohort_df,
            cohort_col="cohort",
            period_col="period",
            value_col="retention_rate",
        )
        _assert_result_shape(result)

    def test_insights_mention_period1_retention(self, cohort_df):
        result = cohort_retention_plot(
            cohort_df,
            cohort_col="cohort",
            period_col="period",
            value_col="retention_rate",
        )
        insight_text = " ".join(result["insights"])
        assert "retention" in insight_text.lower()

    def test_figure_has_heatmap_trace(self, cohort_df):
        result = cohort_retention_plot(
            cohort_df,
            cohort_col="cohort",
            period_col="period",
            value_col="retention_rate",
        )
        trace_types = {type(t).__name__ for t in result["figure"].data}
        assert "Heatmap" in trace_types

    def test_minimal_two_cohort_two_period(self):
        df = pd.DataFrame({
            "cohort": ["C1", "C1", "C2", "C2"],
            "period": [0, 1, 0, 1],
            "users": [1000, 600, 800, 520],
        })
        result = cohort_retention_plot(df, cohort_col="cohort", period_col="period", value_col="users")
        _assert_result_shape(result)


class TestSurvivalCurvePlot:
    """Tests for agents.tools.viz_tools.survival_curve_plot."""

    def test_returns_required_keys(self, survival_input):
        result = survival_curve_plot(survival_input)
        _assert_result_shape(result)

    def test_with_confidence_intervals(self, survival_input_with_ci):
        result = survival_curve_plot(survival_input_with_ci)
        _assert_result_shape(result)
        # CI band should add an extra trace
        assert len(result["figure"].data) == 2

    def test_insights_contain_final_probability(self, survival_input):
        result = survival_curve_plot(survival_input)
        insight_text = " ".join(result["insights"])
        assert "survival" in insight_text.lower() or "probability" in insight_text.lower()

    def test_insights_contain_median_time(self, survival_input):
        result = survival_curve_plot(survival_input)
        # Median survival time exists because prob crosses 0.5 in the fixture
        insight_text = " ".join(result["insights"])
        assert "median" in insight_text.lower()

    def test_y_axis_range_capped_at_one(self, survival_input):
        result = survival_curve_plot(survival_input)
        y_range = result["figure"].layout.yaxis.range
        assert y_range is not None
        assert y_range[1] <= 1.1  # allow slight padding

    def test_figure_has_step_line_trace(self, survival_input):
        result = survival_curve_plot(survival_input)
        assert len(result["figure"].data) >= 1
