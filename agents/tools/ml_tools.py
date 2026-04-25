"""ML training, evaluation, and model management tools."""

from __future__ import annotations

import importlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported algorithms registry
# ---------------------------------------------------------------------------
ALGORITHMS: dict[str, dict[str, dict]] = {
    "classification": {
        "logistic_regression": {
            "class": "sklearn.linear_model.LogisticRegression",
            "default_params": {"max_iter": 1000, "random_state": 42},
            "display_name": "Logistic Regression",
        },
        "random_forest": {
            "class": "sklearn.ensemble.RandomForestClassifier",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "display_name": "Random Forest",
        },
        "gradient_boosting": {
            "class": "sklearn.ensemble.GradientBoostingClassifier",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "display_name": "Gradient Boosting",
        },
        "xgboost": {
            "class": "xgboost.XGBClassifier",
            "default_params": {
                "n_estimators": 100,
                "random_state": 42,
                "eval_metric": "logloss",
                "verbosity": 0,
            },
            "display_name": "XGBoost",
        },
        "lightgbm": {
            "class": "lightgbm.LGBMClassifier",
            "default_params": {
                "n_estimators": 100,
                "random_state": 42,
                "verbose": -1,
            },
            "display_name": "LightGBM",
        },
        "svm": {
            "class": "sklearn.svm.SVC",
            "default_params": {"probability": True, "random_state": 42},
            "display_name": "Support Vector Machine",
        },
        "knn": {
            "class": "sklearn.neighbors.KNeighborsClassifier",
            "default_params": {"n_neighbors": 5},
            "display_name": "K-Nearest Neighbors",
        },
    },
    "regression": {
        "linear_regression": {
            "class": "sklearn.linear_model.LinearRegression",
            "default_params": {},
            "display_name": "Linear Regression",
        },
        "ridge": {
            "class": "sklearn.linear_model.Ridge",
            "default_params": {"random_state": 42},
            "display_name": "Ridge Regression",
        },
        "lasso": {
            "class": "sklearn.linear_model.Lasso",
            "default_params": {"random_state": 42},
            "display_name": "Lasso Regression",
        },
        "random_forest": {
            "class": "sklearn.ensemble.RandomForestRegressor",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "display_name": "Random Forest",
        },
        "gradient_boosting": {
            "class": "sklearn.ensemble.GradientBoostingRegressor",
            "default_params": {"n_estimators": 100, "random_state": 42},
            "display_name": "Gradient Boosting",
        },
        "xgboost": {
            "class": "xgboost.XGBRegressor",
            "default_params": {
                "n_estimators": 100,
                "random_state": 42,
                "verbosity": 0,
            },
            "display_name": "XGBoost",
        },
        "lightgbm": {
            "class": "lightgbm.LGBMRegressor",
            "default_params": {
                "n_estimators": 100,
                "random_state": 42,
                "verbose": -1,
            },
            "display_name": "LightGBM",
        },
        "svr": {
            "class": "sklearn.svm.SVR",
            "default_params": {},
            "display_name": "Support Vector Regression",
        },
    },
    "clustering": {
        "kmeans": {
            "class": "sklearn.cluster.KMeans",
            "default_params": {"n_clusters": 5, "random_state": 42},
            "display_name": "K-Means",
        },
        "dbscan": {
            "class": "sklearn.cluster.DBSCAN",
            "default_params": {"eps": 0.5, "min_samples": 5},
            "display_name": "DBSCAN",
        },
        "agglomerative": {
            "class": "sklearn.cluster.AgglomerativeClustering",
            "default_params": {"n_clusters": 5},
            "display_name": "Agglomerative Clustering",
        },
        "gaussian_mixture": {
            "class": "sklearn.mixture.GaussianMixture",
            "default_params": {"n_components": 5, "random_state": 42},
            "display_name": "Gaussian Mixture",
        },
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_estimator(algorithm: str, problem_type: str | None = None, params: dict | None = None) -> Any:
    """Resolve algorithm string to an instantiated estimator."""
    # Search for the algorithm across problem types
    algo_info = None
    if problem_type and problem_type in ALGORITHMS:
        algo_info = ALGORITHMS[problem_type].get(algorithm)

    if algo_info is None:
        for pt, algos in ALGORITHMS.items():
            if algorithm in algos:
                algo_info = algos[algorithm]
                break

    if algo_info is None:
        raise ValueError(f"Unknown algorithm: '{algorithm}'. Available: {_list_all_algorithms()}")

    class_path = algo_info["class"]
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    merged_params = {**algo_info.get("default_params", {})}
    if params:
        merged_params.update(params)

    return cls(**merged_params)


def _list_all_algorithms() -> list[str]:
    """Return all known algorithm keys."""
    seen: set[str] = set()
    for algos in ALGORITHMS.values():
        seen.update(algos.keys())
    return sorted(seen)


def _infer_problem_type(y: pd.Series) -> str:
    """Infer classification vs regression from target."""
    if y.dtype == "object" or y.dtype.name == "category":
        return "classification"
    if y.nunique() <= 20 and y.nunique() / max(len(y), 1) < 0.05:
        return "classification"
    return "regression"


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    algorithm: str,
    params: dict | None = None,
) -> dict:
    """Train a single model on the provided data.

    Returns
    -------
    dict
        Keys: model, algorithm, train_time_s, n_samples, n_features.
    """
    problem_type = _infer_problem_type(y_train)
    estimator = _resolve_estimator(algorithm, problem_type, params)

    start = time.perf_counter()
    estimator.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    logger.info(
        "Trained %s in %.2fs on %d samples, %d features",
        algorithm, elapsed, len(X_train), X_train.shape[1],
    )

    return {
        "model": estimator,
        "algorithm": algorithm,
        "problem_type": problem_type,
        "train_time_s": round(elapsed, 4),
        "n_samples": len(X_train),
        "n_features": X_train.shape[1],
    }


def cross_validate_model(
    X: pd.DataFrame,
    y: pd.Series,
    algorithm: str,
    cv: int = 5,
    scoring: str | None = None,
) -> dict:
    """Run k-fold cross-validation and return aggregated scores."""
    from sklearn.model_selection import cross_val_score

    problem_type = _infer_problem_type(y)
    estimator = _resolve_estimator(algorithm, problem_type)

    if scoring is None:
        scoring = "f1_weighted" if problem_type == "classification" else "r2"

    start = time.perf_counter()
    scores = cross_val_score(estimator, X, y, cv=cv, scoring=scoring)
    elapsed = time.perf_counter() - start

    logger.info(
        "CV %s: mean=%.4f std=%.4f (%d folds, %.2fs)",
        algorithm, scores.mean(), scores.std(), cv, elapsed,
    )

    return {
        "algorithm": algorithm,
        "scoring": scoring,
        "cv": cv,
        "scores": scores.tolist(),
        "mean": round(float(scores.mean()), 6),
        "std": round(float(scores.std()), 6),
        "elapsed_s": round(elapsed, 4),
    }


def hyperparameter_tune(
    X: pd.DataFrame,
    y: pd.Series,
    algorithm: str,
    param_grid: dict,
    cv: int = 5,
    method: str = "random",
) -> dict:
    """Search for optimal hyperparameters using grid or random search."""
    from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

    problem_type = _infer_problem_type(y)
    estimator = _resolve_estimator(algorithm, problem_type)
    scoring = "f1_weighted" if problem_type == "classification" else "r2"

    if method == "grid":
        searcher = GridSearchCV(
            estimator, param_grid, cv=cv, scoring=scoring,
            n_jobs=-1, refit=True,
        )
    else:
        n_iter = min(50, max(10, len(param_grid) * 5))
        searcher = RandomizedSearchCV(
            estimator, param_grid, n_iter=n_iter, cv=cv,
            scoring=scoring, n_jobs=-1, refit=True, random_state=42,
        )

    start = time.perf_counter()
    searcher.fit(X, y)
    elapsed = time.perf_counter() - start

    logger.info(
        "Tuned %s via %s search: best_score=%.4f in %.2fs",
        algorithm, method, searcher.best_score_, elapsed,
    )

    return {
        "algorithm": algorithm,
        "method": method,
        "best_params": searcher.best_params_,
        "best_score": round(float(searcher.best_score_), 6),
        "best_model": searcher.best_estimator_,
        "cv": cv,
        "scoring": scoring,
        "elapsed_s": round(elapsed, 4),
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_model(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    problem_type: str,
) -> dict:
    """Evaluate a trained model on held-out test data."""
    from sklearn import metrics

    y_pred = model.predict(X_test)
    result: dict[str, Any] = {"problem_type": problem_type}

    if problem_type == "classification":
        result["accuracy"] = round(float(metrics.accuracy_score(y_test, y_pred)), 6)
        avg = "binary" if y_test.nunique() == 2 else "weighted"
        result["precision"] = round(float(metrics.precision_score(y_test, y_pred, average=avg, zero_division=0)), 6)
        result["recall"] = round(float(metrics.recall_score(y_test, y_pred, average=avg, zero_division=0)), 6)
        result["f1"] = round(float(metrics.f1_score(y_test, y_pred, average=avg, zero_division=0)), 6)
        result["confusion_matrix"] = metrics.confusion_matrix(y_test, y_pred).tolist()

        # ROC AUC for binary classification
        if y_test.nunique() == 2 and hasattr(model, "predict_proba"):
            try:
                y_proba = model.predict_proba(X_test)[:, 1]
                result["roc_auc"] = round(float(metrics.roc_auc_score(y_test, y_proba)), 6)
            except Exception:
                pass

    elif problem_type == "regression":
        result["mse"] = round(float(metrics.mean_squared_error(y_test, y_pred)), 6)
        result["rmse"] = round(float(np.sqrt(metrics.mean_squared_error(y_test, y_pred))), 6)
        result["mae"] = round(float(metrics.mean_absolute_error(y_test, y_pred)), 6)
        result["r2"] = round(float(metrics.r2_score(y_test, y_pred)), 6)
        # MAPE (avoid division by zero)
        mask = y_test != 0
        if mask.sum() > 0:
            mape = float(np.mean(np.abs((y_test[mask] - y_pred[mask]) / y_test[mask])) * 100)
            result["mape"] = round(mape, 4)

    logger.info("Evaluated model: %s", {k: v for k, v in result.items() if k != "confusion_matrix"})
    return result


def compare_models(results: list[dict]) -> dict:
    """Compare evaluation results across multiple models."""
    if not results:
        return {"ranking": [], "summary": "No models to compare."}

    problem_type = results[0].get("problem_type", "classification")
    primary_metric = "f1" if problem_type == "classification" else "r2"

    ranking = sorted(
        [r for r in results if primary_metric in r],
        key=lambda r: r[primary_metric],
        reverse=True,
    )

    comparison = []
    for i, r in enumerate(ranking):
        entry = {"rank": i + 1}
        entry.update({k: v for k, v in r.items() if k not in ("confusion_matrix", "model")})
        comparison.append(entry)

    return {
        "ranking": comparison,
        "primary_metric": primary_metric,
        "best": comparison[0] if comparison else None,
        "n_models": len(comparison),
    }


def select_best_model(results: list[dict], metric: str = "f1") -> dict:
    """Select the best model from a list of evaluation results."""
    valid = [r for r in results if metric in r]
    if not valid:
        raise ValueError(f"No results contain metric '{metric}'")

    best = max(valid, key=lambda r: r[metric])
    logger.info("Selected best model by %s=%.4f", metric, best[metric])

    return {
        "best_result": best,
        "metric": metric,
        "best_value": best[metric],
        "n_candidates": len(valid),
    }


# ---------------------------------------------------------------------------
# Data splitting
# ---------------------------------------------------------------------------


def train_test_split_stratified(
    df: pd.DataFrame,
    target_col: str,
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple:
    """Split a DataFrame into stratified train/test sets.

    Returns (X_train, X_test, y_train, y_test).
    """
    from sklearn.model_selection import train_test_split

    X = df.drop(columns=[target_col])
    y = df[target_col]

    stratify = y if y.nunique() <= 50 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=stratify,
    )

    logger.info(
        "Split: train=%d, test=%d (%.0f%% test)",
        len(X_train), len(X_test), test_size * 100,
    )

    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Interpretability
# ---------------------------------------------------------------------------


def get_feature_importance(model: Any, feature_names: list[str]) -> dict:
    """Extract feature importance scores from a fitted model."""
    importances: np.ndarray | None = None

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        coef = model.coef_
        if coef.ndim > 1:
            importances = np.abs(coef).mean(axis=0)
        else:
            importances = np.abs(coef)

    if importances is None:
        logger.warning("Model does not expose feature importances")
        return {"importances": {}, "sorted_features": []}

    imp_dict = {
        name: round(float(val), 6)
        for name, val in zip(feature_names, importances)
    }
    sorted_features = sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)

    return {
        "importances": imp_dict,
        "sorted_features": [{"feature": k, "importance": v} for k, v in sorted_features],
        "top_5": [k for k, _ in sorted_features[:5]],
    }


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def predict(model: Any, X: pd.DataFrame) -> Any:
    """Generate predictions from a fitted model."""
    return model.predict(X)


def predict_proba(model: Any, X: pd.DataFrame) -> Any:
    """Generate class-probability predictions from a fitted model."""
    if not hasattr(model, "predict_proba"):
        logger.warning("Model does not support predict_proba, using decision_function")
        if hasattr(model, "decision_function"):
            return model.decision_function(X)
        raise AttributeError(f"{type(model).__name__} has no predict_proba or decision_function")
    return model.predict_proba(X)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_model(model: Any, path: str, metadata: dict | None = None) -> str:
    """Serialize a trained model to disk with optional metadata sidecar."""
    import joblib

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, p)

    if metadata:
        meta_path = p.with_suffix(".meta.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    logger.info("Saved model to %s", p)
    return str(p.resolve())


def load_model(path: str) -> Any:
    """Deserialize a model from disk, with metadata if available."""
    import joblib

    p = Path(path)
    model = joblib.load(p)

    meta_path = p.with_suffix(".meta.json")
    metadata = None
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = json.load(f)

    if metadata:
        return {"model": model, "metadata": metadata}
    return model


# ---------------------------------------------------------------------------
# Algorithm discovery
# ---------------------------------------------------------------------------


def get_supported_algorithms(problem_type: str) -> list[dict]:
    """Return the list of supported algorithms for a given problem type."""
    if problem_type not in ALGORITHMS:
        raise ValueError(f"Unknown problem type: '{problem_type}'. Choose from: {list(ALGORITHMS.keys())}")

    result = []
    for key, info in ALGORITHMS[problem_type].items():
        result.append({
            "key": key,
            "display_name": info.get("display_name", key),
            "class": info["class"],
            "default_params": info.get("default_params", {}),
        })

    return result


# ---------------------------------------------------------------------------
# AutoML
# ---------------------------------------------------------------------------


def automl_train(
    X: pd.DataFrame,
    y: pd.Series,
    time_budget: int = 60,
    metric: str = "auto",
) -> dict:
    """Run FLAML AutoML for automated model selection and tuning."""
    from flaml import AutoML

    problem_type = _infer_problem_type(y)

    if metric == "auto":
        metric = "f1_weighted" if problem_type == "classification" else "r2"

    automl = AutoML()

    start = time.perf_counter()
    automl.fit(
        X, y,
        task=problem_type,
        metric=metric,
        time_budget=time_budget,
        verbose=0,
    )
    elapsed = time.perf_counter() - start

    logger.info(
        "AutoML complete: best=%s, score=%.4f in %.2fs",
        automl.best_estimator, automl.best_loss, elapsed,
    )

    return {
        "best_model": automl.model,
        "best_estimator": automl.best_estimator,
        "best_config": automl.best_config,
        "best_loss": round(float(automl.best_loss), 6),
        "metric": metric,
        "time_budget": time_budget,
        "elapsed_s": round(elapsed, 4),
    }


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------


def create_pipeline(steps: list[tuple]) -> Any:
    """Build an sklearn-compatible pipeline from a list of steps."""
    from sklearn.pipeline import Pipeline

    return Pipeline(steps)
