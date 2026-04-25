"""Unit tests for agents/tools/ml_tools.py.

Coverage targets:
  - train_model (classification + regression)
  - cross_validate_model
  - hyperparameter_tune
  - evaluate_model (classification + regression)
  - compare_models / select_best_model
  - train_test_split_stratified
  - get_feature_importance
  - predict / predict_proba
  - save_model / load_model (round-trip)
  - get_supported_algorithms
  - create_pipeline
  - automl_train (import-error guard only)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from agents.tools.ml_tools import (
    ALGORITHMS,
    compare_models,
    create_pipeline,
    cross_validate_model,
    evaluate_model,
    get_feature_importance,
    get_supported_algorithms,
    hyperparameter_tune,
    load_model,
    predict,
    predict_proba,
    save_model,
    select_best_model,
    train_model,
    train_test_split_stratified,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clf_X_y(sample_classification_df: pd.DataFrame):
    """Return numeric-only feature matrix and binary target from the churn fixture."""
    numeric_cols = ["age", "income", "tenure_months", "num_products",
                    "has_credit_card", "is_active", "balance"]
    X = sample_classification_df[numeric_cols].copy()
    y = sample_classification_df["churned"].copy()
    return X, y


@pytest.fixture
def reg_X_y(sample_regression_df: pd.DataFrame):
    """Return numeric-only feature matrix and continuous target from the price fixture."""
    numeric_cols = ["sqft", "bedrooms", "bathrooms", "year_built",
                    "has_garage", "lot_size"]
    X = sample_regression_df[numeric_cols].copy()
    y = sample_regression_df["price"].copy()
    return X, y


@pytest.fixture
def trained_rf_clf(clf_X_y):
    """A fitted RandomForestClassifier for use in prediction / interpretability tests."""
    X, y = clf_X_y
    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    clf.fit(X, y)
    return clf, X, y


@pytest.fixture
def trained_lr_reg(reg_X_y):
    """A fitted LinearRegression for use in regression-specific tests."""
    X, y = reg_X_y
    reg = LinearRegression()
    reg.fit(X, y)
    return reg, X, y


# ---------------------------------------------------------------------------
# 1. train_model — classification
# ---------------------------------------------------------------------------


class TestTrainModelClassification:
    def test_returns_dict_with_model_key(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert isinstance(result, dict)
        assert "model" in result, "Result must contain a 'model' key."

    def test_algorithm_key_reflects_requested_algorithm(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert result["algorithm"] == "random_forest"

    def test_n_samples_matches_input_length(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert result["n_samples"] == len(X)

    def test_n_features_matches_input_columns(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert result["n_features"] == X.shape[1]

    def test_train_time_s_is_non_negative_float(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert isinstance(result["train_time_s"], float)
        assert result["train_time_s"] >= 0.0

    def test_problem_type_inferred_as_classification(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        assert result["problem_type"] == "classification"

    def test_model_can_predict(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest")

        preds = result["model"].predict(X)
        assert len(preds) == len(y)

    def test_logistic_regression_variant(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="logistic_regression")

        assert "model" in result
        assert result["algorithm"] == "logistic_regression"

    def test_custom_params_are_forwarded(self, clf_X_y):
        X, y = clf_X_y
        result = train_model(X, y, algorithm="random_forest",
                             params={"n_estimators": 5})

        assert result["model"].n_estimators == 5

    def test_unknown_algorithm_raises_value_error(self, clf_X_y):
        X, y = clf_X_y
        with pytest.raises(ValueError, match="Unknown algorithm"):
            train_model(X, y, algorithm="nonexistent_algo")


# ---------------------------------------------------------------------------
# 2. train_model — regression
# ---------------------------------------------------------------------------


class TestTrainModelRegression:
    def test_returns_dict_with_model_key(self, reg_X_y):
        X, y = reg_X_y
        result = train_model(X, y, algorithm="linear_regression")

        assert "model" in result

    def test_algorithm_key_correct(self, reg_X_y):
        X, y = reg_X_y
        result = train_model(X, y, algorithm="linear_regression")

        assert result["algorithm"] == "linear_regression"

    def test_problem_type_inferred_as_regression(self, reg_X_y):
        X, y = reg_X_y
        result = train_model(X, y, algorithm="linear_regression")

        assert result["problem_type"] == "regression"

    def test_n_samples_and_features_correct(self, reg_X_y):
        X, y = reg_X_y
        result = train_model(X, y, algorithm="linear_regression")

        assert result["n_samples"] == len(X)
        assert result["n_features"] == X.shape[1]

    def test_ridge_regression_variant(self, reg_X_y):
        X, y = reg_X_y
        result = train_model(X, y, algorithm="ridge")

        assert "model" in result
        assert result["algorithm"] == "ridge"


# ---------------------------------------------------------------------------
# 3. cross_validate_model
# ---------------------------------------------------------------------------


class TestCrossValidateModel:
    def test_returns_dict_with_mean_key(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="random_forest", cv=3)

        assert isinstance(result, dict)
        assert "mean" in result

    def test_mean_score_is_float_between_0_and_1(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="random_forest", cv=3)

        assert isinstance(result["mean"], float)
        assert 0.0 <= result["mean"] <= 1.0

    def test_scores_length_equals_cv_folds(self, clf_X_y):
        X, y = clf_X_y
        cv = 3
        result = cross_validate_model(X, y, algorithm="random_forest", cv=cv)

        assert len(result["scores"]) == cv

    def test_std_is_non_negative(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="random_forest", cv=3)

        assert result["std"] >= 0.0

    def test_cv_key_reflects_requested_folds(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="logistic_regression", cv=4)

        assert result["cv"] == 4

    def test_algorithm_key_in_result(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="logistic_regression", cv=3)

        assert result["algorithm"] == "logistic_regression"

    def test_custom_scoring_accepted(self, clf_X_y):
        X, y = clf_X_y
        result = cross_validate_model(X, y, algorithm="logistic_regression",
                                      cv=3, scoring="accuracy")

        assert result["scoring"] == "accuracy"

    def test_regression_scoring_defaults_to_r2(self, reg_X_y):
        X, y = reg_X_y
        result = cross_validate_model(X, y, algorithm="linear_regression", cv=3)

        assert result["scoring"] == "r2"


# ---------------------------------------------------------------------------
# 4. hyperparameter_tune
# ---------------------------------------------------------------------------


class TestHyperparameterTune:
    def test_returns_best_params_and_best_score(self, clf_X_y):
        X, y = clf_X_y
        param_grid = {"n_estimators": [5, 10], "max_depth": [2, 3]}
        result = hyperparameter_tune(X, y, algorithm="random_forest",
                                     param_grid=param_grid, cv=2,
                                     method="grid")

        assert "best_params" in result
        assert "best_score" in result
        assert isinstance(result["best_params"], dict)

    def test_best_model_is_fitted_estimator(self, clf_X_y):
        X, y = clf_X_y
        param_grid = {"n_estimators": [5, 10]}
        result = hyperparameter_tune(X, y, algorithm="random_forest",
                                     param_grid=param_grid, cv=2,
                                     method="random")

        assert hasattr(result["best_model"], "predict")

    def test_best_score_within_0_1_range_for_classification(self, clf_X_y):
        X, y = clf_X_y
        param_grid = {"n_estimators": [5, 10]}
        result = hyperparameter_tune(X, y, algorithm="random_forest",
                                     param_grid=param_grid, cv=2)

        assert 0.0 <= result["best_score"] <= 1.0

    def test_method_key_reflects_search_type(self, clf_X_y):
        X, y = clf_X_y
        param_grid = {"n_estimators": [5, 10]}
        result = hyperparameter_tune(X, y, algorithm="random_forest",
                                     param_grid=param_grid, cv=2,
                                     method="grid")

        assert result["method"] == "grid"


# ---------------------------------------------------------------------------
# 5. evaluate_model — classification
# ---------------------------------------------------------------------------


class TestEvaluateModelClassification:
    def test_accuracy_present_and_valid(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        assert "accuracy" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0

    def test_precision_recall_f1_present(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        for key in ("precision", "recall", "f1"):
            assert key in metrics, f"Expected metric '{key}' missing from result."
            assert 0.0 <= metrics[key] <= 1.0

    def test_roc_auc_present_for_binary_target(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        # The churned target is binary (0/1)
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        assert "roc_auc" in metrics
        assert 0.0 <= metrics["roc_auc"] <= 1.0

    def test_confusion_matrix_present_and_correct_shape(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        cm = metrics["confusion_matrix"]
        assert isinstance(cm, list)
        # Binary classification → 2x2
        assert len(cm) == 2
        assert all(len(row) == 2 for row in cm)

    def test_problem_type_key_set_correctly(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        assert metrics["problem_type"] == "classification"

    def test_no_regression_keys_leaked_into_classification_result(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        metrics = evaluate_model(clf, X, y, problem_type="classification")

        for key in ("mse", "rmse", "mae", "r2"):
            assert key not in metrics


# ---------------------------------------------------------------------------
# 6. evaluate_model — regression
# ---------------------------------------------------------------------------


class TestEvaluateModelRegression:
    def test_mse_rmse_mae_r2_present(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        metrics = evaluate_model(reg, X, y, problem_type="regression")

        for key in ("mse", "rmse", "mae", "r2"):
            assert key in metrics, f"Expected metric '{key}' missing."

    def test_rmse_equals_sqrt_of_mse(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        metrics = evaluate_model(reg, X, y, problem_type="regression")

        expected_rmse = round(float(np.sqrt(metrics["mse"])), 6)
        assert abs(metrics["rmse"] - expected_rmse) < 1e-4

    def test_mse_and_mae_are_non_negative(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        metrics = evaluate_model(reg, X, y, problem_type="regression")

        assert metrics["mse"] >= 0.0
        assert metrics["mae"] >= 0.0

    def test_problem_type_key_set_correctly(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        metrics = evaluate_model(reg, X, y, problem_type="regression")

        assert metrics["problem_type"] == "regression"

    def test_no_classification_keys_leaked_into_regression_result(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        metrics = evaluate_model(reg, X, y, problem_type="regression")

        for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            assert key not in metrics


# ---------------------------------------------------------------------------
# 7. train_test_split_stratified
# ---------------------------------------------------------------------------


class TestTrainTestSplitStratified:
    def test_returns_four_element_tuple(self, sample_classification_df):
        result = train_test_split_stratified(
            sample_classification_df, target_col="churned", test_size=0.2
        )
        assert len(result) == 4

    def test_x_train_and_x_test_row_counts_sum_to_total(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned", test_size=0.2
        )
        total = len(sample_classification_df)
        assert len(X_train) + len(X_test) == total

    def test_test_proportion_approximately_correct(self, sample_classification_df):
        test_size = 0.2
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned", test_size=test_size
        )
        actual_test_ratio = len(X_test) / (len(X_train) + len(X_test))
        assert abs(actual_test_ratio - test_size) < 0.02

    def test_target_column_excluded_from_feature_matrix(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned"
        )
        assert "churned" not in X_train.columns
        assert "churned" not in X_test.columns

    def test_y_train_y_test_are_series(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned"
        )
        assert isinstance(y_train, pd.Series)
        assert isinstance(y_test, pd.Series)

    def test_x_train_x_test_are_dataframes(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned"
        )
        assert isinstance(X_train, pd.DataFrame)
        assert isinstance(X_test, pd.DataFrame)

    def test_feature_columns_consistent_between_train_and_test(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned"
        )
        assert list(X_train.columns) == list(X_test.columns)

    def test_y_series_length_matches_x_rows(self, sample_classification_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_classification_df, target_col="churned"
        )
        assert len(X_train) == len(y_train)
        assert len(X_test) == len(y_test)

    def test_works_with_regression_target(self, sample_regression_df):
        X_train, X_test, y_train, y_test = train_test_split_stratified(
            sample_regression_df, target_col="price", test_size=0.2
        )
        assert len(X_train) + len(X_test) == len(sample_regression_df)


# ---------------------------------------------------------------------------
# 8. get_feature_importance
# ---------------------------------------------------------------------------


class TestGetFeatureImportance:
    def test_returns_importances_dict(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        assert isinstance(result, dict)
        assert "importances" in result
        assert isinstance(result["importances"], dict)

    def test_all_feature_names_present_in_importances(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        for col in X.columns:
            assert col in result["importances"]

    def test_sorted_features_list_present_and_ordered(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        sorted_feats = result["sorted_features"]
        assert isinstance(sorted_feats, list)
        # Verify descending order
        importances = [item["importance"] for item in sorted_feats]
        assert importances == sorted(importances, reverse=True)

    def test_sorted_features_length_equals_number_of_features(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        assert len(result["sorted_features"]) == X.shape[1]

    def test_top_5_list_present_with_at_most_five_items(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        assert "top_5" in result
        assert len(result["top_5"]) <= 5

    def test_importance_values_are_non_negative(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        result = get_feature_importance(clf, list(X.columns))

        for val in result["importances"].values():
            assert val >= 0.0

    def test_model_with_coef_attribute_also_works(self, trained_lr_reg):
        reg, X, _ = trained_lr_reg
        result = get_feature_importance(reg, list(X.columns))

        assert "importances" in result
        assert len(result["importances"]) == X.shape[1]

    def test_unsupported_model_returns_empty_dicts(self):
        """A model with neither feature_importances_ nor coef_ returns empty dicts."""
        from sklearn.neighbors import KNeighborsClassifier
        X = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        y = pd.Series([0, 1, 0])
        knn = KNeighborsClassifier()
        knn.fit(X, y)

        result = get_feature_importance(knn, list(X.columns))

        assert result["importances"] == {}
        assert result["sorted_features"] == []


# ---------------------------------------------------------------------------
# 9. predict / predict_proba
# ---------------------------------------------------------------------------


class TestPredict:
    def test_predict_returns_array_with_correct_length(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        preds = predict(clf, X)

        assert len(preds) == len(y)

    def test_predict_returns_numpy_array(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        preds = predict(clf, X)

        assert isinstance(preds, np.ndarray)

    def test_predict_values_are_in_target_classes(self, trained_rf_clf):
        clf, X, y = trained_rf_clf
        preds = predict(clf, X)

        assert set(preds).issubset({0, 1})

    def test_predict_regression_model(self, trained_lr_reg):
        reg, X, y = trained_lr_reg
        preds = predict(reg, X)

        assert len(preds) == len(y)
        assert isinstance(preds, np.ndarray)


class TestPredictProba:
    def test_predict_proba_returns_array_with_correct_shape(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        proba = predict_proba(clf, X)

        assert proba.shape == (len(X), 2), (
            f"Expected shape ({len(X)}, 2), got {proba.shape}"
        )

    def test_predict_proba_values_sum_to_one_per_row(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        proba = predict_proba(clf, X)

        row_sums = proba.sum(axis=1)
        np.testing.assert_allclose(row_sums, np.ones(len(X)), atol=1e-6)

    def test_predict_proba_values_between_0_and_1(self, trained_rf_clf):
        clf, X, _ = trained_rf_clf
        proba = predict_proba(clf, X)

        assert np.all(proba >= 0.0)
        assert np.all(proba <= 1.0)

    def test_predict_proba_raises_for_model_without_proba_or_decision(self):
        """A bare model without predict_proba or decision_function must raise AttributeError."""
        # Use LinearRegression — has neither predict_proba nor decision_function
        X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        y = pd.Series([10.0, 20.0, 30.0])
        reg = LinearRegression()
        reg.fit(X, y)

        with pytest.raises(AttributeError):
            predict_proba(reg, X)


# ---------------------------------------------------------------------------
# 10. save_model / load_model (round-trip)
# ---------------------------------------------------------------------------


class TestSaveLoadModelRoundTrip:
    def test_save_returns_string_path(self, trained_rf_clf, tmp_path):
        clf, _, _ = trained_rf_clf
        model_path = str(tmp_path / "model.joblib")
        returned_path = save_model(clf, model_path)

        assert isinstance(returned_path, str)

    def test_saved_file_exists_on_disk(self, trained_rf_clf, tmp_path):
        clf, _, _ = trained_rf_clf
        model_path = str(tmp_path / "model.joblib")
        returned_path = save_model(clf, model_path)

        assert Path(returned_path).exists()

    def test_load_returns_fitted_model(self, trained_rf_clf, tmp_path):
        clf, X, _ = trained_rf_clf
        model_path = str(tmp_path / "model.joblib")
        save_model(clf, model_path)

        loaded = load_model(model_path)
        assert hasattr(loaded, "predict"), "Loaded object must be a fitted estimator."

    def test_loaded_model_produces_same_predictions(self, trained_rf_clf, tmp_path):
        clf, X, _ = trained_rf_clf
        model_path = str(tmp_path / "model.joblib")
        save_model(clf, model_path)

        loaded = load_model(model_path)
        original_preds = clf.predict(X)
        loaded_preds = loaded.predict(X)
        np.testing.assert_array_equal(original_preds, loaded_preds)

    def test_save_with_metadata_creates_sidecar_json(self, trained_rf_clf, tmp_path):
        clf, _, _ = trained_rf_clf
        model_path = str(tmp_path / "model_meta.joblib")
        metadata = {"version": "1.0", "algorithm": "random_forest"}
        save_model(clf, model_path, metadata=metadata)

        meta_file = tmp_path / "model_meta.meta.json"
        assert meta_file.exists(), "Metadata sidecar .meta.json should be created."

    def test_load_with_metadata_returns_dict_with_model_and_metadata_keys(
        self, trained_rf_clf, tmp_path
    ):
        clf, X, _ = trained_rf_clf
        model_path = str(tmp_path / "model_meta.joblib")
        metadata = {"version": "1.0", "algorithm": "random_forest"}
        save_model(clf, model_path, metadata=metadata)

        result = load_model(model_path)
        assert isinstance(result, dict)
        assert "model" in result
        assert "metadata" in result

    def test_load_with_metadata_preserves_metadata_content(
        self, trained_rf_clf, tmp_path
    ):
        clf, _, _ = trained_rf_clf
        model_path = str(tmp_path / "model_meta.joblib")
        metadata = {"version": "1.0", "algorithm": "random_forest"}
        save_model(clf, model_path, metadata=metadata)

        result = load_model(model_path)
        assert result["metadata"]["version"] == "1.0"
        assert result["metadata"]["algorithm"] == "random_forest"

    def test_save_creates_parent_directories(self, trained_rf_clf, tmp_path):
        clf, _, _ = trained_rf_clf
        nested_path = str(tmp_path / "models" / "v1" / "model.joblib")
        returned_path = save_model(clf, nested_path)

        assert Path(returned_path).exists()

    def test_round_trip_with_regression_model(self, trained_lr_reg, tmp_path):
        reg, X, _ = trained_lr_reg
        model_path = str(tmp_path / "reg_model.joblib")
        save_model(reg, model_path)

        loaded = load_model(model_path)
        original_preds = reg.predict(X)
        loaded_preds = loaded.predict(X)
        np.testing.assert_allclose(original_preds, loaded_preds, rtol=1e-5)


# ---------------------------------------------------------------------------
# 11. get_supported_algorithms
# ---------------------------------------------------------------------------


class TestGetSupportedAlgorithms:
    def test_returns_list_for_classification(self):
        result = get_supported_algorithms("classification")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_returns_list_for_regression(self):
        result = get_supported_algorithms("regression")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_returns_list_for_clustering(self):
        result = get_supported_algorithms("clustering")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_entry_has_required_keys(self):
        result = get_supported_algorithms("classification")

        required_keys = {"key", "display_name", "class", "default_params"}
        for entry in result:
            assert required_keys.issubset(entry.keys()), (
                f"Entry missing required keys: {required_keys - entry.keys()}"
            )

    def test_classification_contains_random_forest(self):
        result = get_supported_algorithms("classification")
        keys = [entry["key"] for entry in result]

        assert "random_forest" in keys

    def test_classification_contains_logistic_regression(self):
        result = get_supported_algorithms("classification")
        keys = [entry["key"] for entry in result]

        assert "logistic_regression" in keys

    def test_regression_contains_linear_regression(self):
        result = get_supported_algorithms("regression")
        keys = [entry["key"] for entry in result]

        assert "linear_regression" in keys

    def test_count_matches_algorithms_registry(self):
        for problem_type in ("classification", "regression", "clustering"):
            result = get_supported_algorithms(problem_type)
            expected_count = len(ALGORITHMS[problem_type])
            assert len(result) == expected_count

    def test_unknown_problem_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown problem type"):
            get_supported_algorithms("time_series")


# ---------------------------------------------------------------------------
# 12. compare_models / select_best_model
# ---------------------------------------------------------------------------


class TestCompareModels:
    @pytest.fixture
    def mock_clf_results(self):
        return [
            {"algorithm": "random_forest", "problem_type": "classification",
             "accuracy": 0.85, "f1": 0.83, "precision": 0.84, "recall": 0.82},
            {"algorithm": "logistic_regression", "problem_type": "classification",
             "accuracy": 0.80, "f1": 0.79, "precision": 0.80, "recall": 0.78},
            {"algorithm": "gradient_boosting", "problem_type": "classification",
             "accuracy": 0.88, "f1": 0.87, "precision": 0.86, "recall": 0.88},
        ]

    @pytest.fixture
    def mock_reg_results(self):
        return [
            {"algorithm": "linear_regression", "problem_type": "regression",
             "mse": 5000.0, "rmse": 70.7, "mae": 55.0, "r2": 0.72},
            {"algorithm": "random_forest", "problem_type": "regression",
             "mse": 3500.0, "rmse": 59.2, "mae": 45.0, "r2": 0.85},
        ]

    def test_compare_returns_dict_with_ranking_key(self, mock_clf_results):
        result = compare_models(mock_clf_results)

        assert isinstance(result, dict)
        assert "ranking" in result

    def test_ranking_sorted_by_f1_descending(self, mock_clf_results):
        result = compare_models(mock_clf_results)

        f1_scores = [entry["f1"] for entry in result["ranking"]]
        assert f1_scores == sorted(f1_scores, reverse=True)

    def test_best_entry_has_rank_1(self, mock_clf_results):
        result = compare_models(mock_clf_results)

        assert result["ranking"][0]["rank"] == 1

    def test_n_models_equals_input_length(self, mock_clf_results):
        result = compare_models(mock_clf_results)

        assert result["n_models"] == len(mock_clf_results)

    def test_best_field_matches_rank_1_entry(self, mock_clf_results):
        result = compare_models(mock_clf_results)

        assert result["best"]["rank"] == 1

    def test_regression_uses_r2_as_primary_metric(self, mock_reg_results):
        result = compare_models(mock_reg_results)

        assert result["primary_metric"] == "r2"

    def test_empty_input_returns_empty_ranking(self):
        result = compare_models([])

        assert result["ranking"] == []

    def test_confusion_matrix_excluded_from_ranking_entries(self):
        results_with_cm = [
            {"algorithm": "rf", "problem_type": "classification",
             "f1": 0.85, "accuracy": 0.88,
             "confusion_matrix": [[80, 10], [5, 5]]},
        ]
        result = compare_models(results_with_cm)

        assert "confusion_matrix" not in result["ranking"][0]


class TestSelectBestModel:
    @pytest.fixture
    def mock_results(self):
        return [
            {"algorithm": "random_forest", "f1": 0.83, "accuracy": 0.85},
            {"algorithm": "logistic_regression", "f1": 0.79, "accuracy": 0.80},
            {"algorithm": "gradient_boosting", "f1": 0.87, "accuracy": 0.88},
        ]

    def test_returns_dict_with_best_result_key(self, mock_results):
        result = select_best_model(mock_results, metric="f1")

        assert isinstance(result, dict)
        assert "best_result" in result

    def test_best_result_has_highest_f1(self, mock_results):
        result = select_best_model(mock_results, metric="f1")

        assert result["best_result"]["algorithm"] == "gradient_boosting"
        assert result["best_value"] == 0.87

    def test_metric_key_reflects_selected_metric(self, mock_results):
        result = select_best_model(mock_results, metric="accuracy")

        assert result["metric"] == "accuracy"

    def test_best_value_by_accuracy(self, mock_results):
        result = select_best_model(mock_results, metric="accuracy")

        assert result["best_value"] == 0.88
        assert result["best_result"]["algorithm"] == "gradient_boosting"

    def test_n_candidates_equals_valid_results_count(self, mock_results):
        result = select_best_model(mock_results, metric="f1")

        assert result["n_candidates"] == len(mock_results)

    def test_raises_value_error_when_metric_absent_from_all_results(self, mock_results):
        with pytest.raises(ValueError, match="No results contain metric"):
            select_best_model(mock_results, metric="roc_auc")

    def test_works_with_single_candidate(self):
        results = [{"algorithm": "rf", "f1": 0.90}]
        result = select_best_model(results, metric="f1")

        assert result["best_value"] == 0.90
        assert result["n_candidates"] == 1


# ---------------------------------------------------------------------------
# 13. create_pipeline
# ---------------------------------------------------------------------------


class TestCreatePipeline:
    def test_returns_sklearn_pipeline_instance(self):
        steps = [("scaler", StandardScaler()), ("clf", LogisticRegression())]
        pipeline = create_pipeline(steps)

        assert isinstance(pipeline, Pipeline)

    def test_pipeline_steps_match_input(self):
        steps = [("scaler", StandardScaler()), ("clf", LogisticRegression())]
        pipeline = create_pipeline(steps)

        step_names = [name for name, _ in pipeline.steps]
        assert step_names == ["scaler", "clf"]

    def test_pipeline_can_fit_and_predict(self, clf_X_y):
        X, y = clf_X_y
        steps = [("scaler", StandardScaler()),
                 ("clf", LogisticRegression(max_iter=500))]
        pipeline = create_pipeline(steps)
        pipeline.fit(X, y)

        preds = pipeline.predict(X)
        assert len(preds) == len(y)

    def test_single_step_pipeline_works(self):
        steps = [("clf", RandomForestClassifier(n_estimators=5))]
        pipeline = create_pipeline(steps)

        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.steps) == 1

    def test_pipeline_preserves_step_estimators(self):
        scaler = StandardScaler()
        clf = LogisticRegression()
        steps = [("scaler", scaler), ("clf", clf)]
        pipeline = create_pipeline(steps)

        # The estimators inside the pipeline must be the same objects
        assert pipeline.named_steps["scaler"] is scaler
        assert pipeline.named_steps["clf"] is clf


# ---------------------------------------------------------------------------
# 14. automl_train — import-error guard
# ---------------------------------------------------------------------------


class TestAutomlTrainImportGuard:
    """Verify that the module itself can be imported even when FLAML is absent."""

    def test_ml_tools_module_importable_regardless_of_flaml(self):
        """The module must import cleanly; FLAML absence only affects automl_train()."""
        spec = importlib.util.find_spec("agents.tools.ml_tools")
        assert spec is not None, (
            "agents.tools.ml_tools must be importable without FLAML installed."
        )

    def test_automl_train_raises_import_error_when_flaml_missing(
        self, monkeypatch
    ):
        """If FLAML is not installed, calling automl_train() should raise ImportError."""
        flaml_missing = importlib.util.find_spec("flaml") is None

        if not flaml_missing:
            pytest.skip("FLAML is installed; cannot test import-error guard.")

        from agents.tools.ml_tools import automl_train

        X = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        y = pd.Series([0, 1, 0])

        with pytest.raises(ImportError):
            automl_train(X, y, time_budget=1)
