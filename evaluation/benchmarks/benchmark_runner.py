"""Benchmark runner for AutoDS platform.

Runs the full pipeline on standard datasets and records results.
Results saved to evaluation/benchmarks/benchmark_results.json.
"""

import json
import logging
import time
import traceback
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_BENCHMARK_DIR = Path("evaluation/benchmarks/benchmark_datasets")
_RESULTS_PATH = Path("evaluation/benchmarks/benchmark_results.json")
_CATALOG_PATH = _BENCHMARK_DIR / "catalog.json"


class BenchmarkRunner:
    """Run AutoDS pipeline on standard datasets and record metrics."""

    def __init__(self, datasets_dir: Path | None = None):
        self.datasets_dir = datasets_dir or _BENCHMARK_DIR
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> dict:
        """Load dataset catalog metadata."""
        catalog_path = self.datasets_dir / "catalog.json"
        if catalog_path.exists():
            return json.loads(catalog_path.read_text())
        return {}

    def run_single(
        self,
        dataset_name: str,
        dataset_path: Path | str,
        domain: str = "generic",
        target_column: str = "target",
        problem_type: str = "classification",
    ) -> dict:
        """Run pipeline on a single dataset.

        Args:
            dataset_name: Name identifier for the dataset.
            dataset_path: Path to CSV file.
            domain: Expected domain.
            target_column: Target variable name.
            problem_type: classification, regression, or clustering.

        Returns:
            Dict with benchmark results.
        """
        result = {
            "dataset": dataset_name,
            "domain": domain,
            "problem_type": problem_type,
            "target_column": target_column,
            "status": "pending",
            "error": None,
        }

        start_time = time.time()

        try:
            # Load data
            df = pd.read_csv(dataset_path, low_memory=False)
            result["n_rows"] = len(df)
            result["n_cols"] = len(df.columns)

            # Validate target exists
            if target_column not in df.columns:
                # Try common alternatives
                for alt in ["target", "Target", "class", "Class", "label"]:
                    if alt in df.columns:
                        target_column = alt
                        result["target_column"] = alt
                        break
                else:
                    result["status"] = "error"
                    result["error"] = f"Target '{target_column}' not found"
                    return result

            # Separate features and target
            y = df[target_column]
            X = df.drop(columns=[target_column])

            # Drop non-numeric for quick benchmark
            X_numeric = X.select_dtypes(include=["number"])
            if X_numeric.empty:
                result["status"] = "error"
                result["error"] = "No numeric features"
                return result

            # Fill missing values
            X_numeric = X_numeric.fillna(X_numeric.median())

            # Train/test split
            from sklearn.model_selection import train_test_split

            X_train, X_test, y_train, y_test = train_test_split(
                X_numeric, y, test_size=0.2, random_state=42
            )

            # Train models based on problem type
            if problem_type == "regression":
                metrics = self._benchmark_regression(
                    X_train, X_test, y_train, y_test
                )
            else:
                metrics = self._benchmark_classification(
                    X_train, X_test, y_train, y_test
                )

            result["metrics"] = metrics
            result["best_model"] = max(
                metrics, key=lambda m: m.get("primary_score", 0)
            )["model"]
            result["best_score"] = max(
                m.get("primary_score", 0) for m in metrics
            )
            result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(
                "Benchmark failed for %s: %s\n%s",
                dataset_name, e, traceback.format_exc(),
            )

        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    def _benchmark_classification(
        self, X_train, X_test, y_train, y_test
    ) -> list[dict]:
        """Run classification benchmarks."""
        from sklearn.ensemble import (
            GradientBoostingClassifier,
            RandomForestClassifier,
        )
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

        models = {
            "logistic_regression": LogisticRegression(
                max_iter=1000, random_state=42
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1
            ),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=100, random_state=42
            ),
        }

        results = []
        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                acc = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred, average="weighted")

                auc = None
                if hasattr(model, "predict_proba"):
                    try:
                        y_proba = model.predict_proba(X_test)
                        if y_proba.shape[1] == 2:
                            auc = roc_auc_score(y_test, y_proba[:, 1])
                        else:
                            auc = roc_auc_score(
                                y_test, y_proba, multi_class="ovr",
                                average="weighted",
                            )
                    except Exception:
                        pass

                results.append({
                    "model": name,
                    "accuracy": round(acc, 4),
                    "f1_weighted": round(f1, 4),
                    "auc": round(auc, 4) if auc else None,
                    "primary_score": round(f1, 4),
                })
            except Exception as e:
                results.append({
                    "model": name, "error": str(e), "primary_score": 0,
                })
        return results

    def _benchmark_regression(
        self, X_train, X_test, y_train, y_test
    ) -> list[dict]:
        """Run regression benchmarks."""
        from sklearn.ensemble import (
            GradientBoostingRegressor,
            RandomForestRegressor,
        )
        from sklearn.linear_model import Ridge
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        models = {
            "ridge": Ridge(random_state=42),
            "random_forest": RandomForestRegressor(
                n_estimators=100, random_state=42, n_jobs=-1
            ),
            "gradient_boosting": GradientBoostingRegressor(
                n_estimators=100, random_state=42
            ),
        }

        results = []
        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                r2 = r2_score(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                rmse = mean_squared_error(y_test, y_pred, squared=False)

                results.append({
                    "model": name,
                    "r2": round(r2, 4),
                    "mae": round(mae, 4),
                    "rmse": round(rmse, 4),
                    "primary_score": round(r2, 4),
                })
            except Exception as e:
                results.append({
                    "model": name, "error": str(e), "primary_score": 0,
                })
        return results

    def run_all(self, datasets: list[str] | None = None) -> list[dict]:
        """Run benchmarks on all catalog datasets.

        Args:
            datasets: Optional list of dataset names to run. None = all.

        Returns:
            List of result dicts.
        """
        if not self.catalog:
            logger.warning("No catalog found. Run download_sample_datasets.py first.")
            return []

        targets = datasets or list(self.catalog.keys())
        results = []

        for name in targets:
            meta = self.catalog.get(name)
            if not meta:
                logger.warning("Dataset %s not in catalog, skipping", name)
                continue

            dataset_path = self.datasets_dir / meta["file"]
            if not dataset_path.exists():
                logger.warning("Dataset file missing: %s", dataset_path)
                continue

            logger.info("Benchmarking: %s (%s)", name, meta["domain"])
            result = self.run_single(
                dataset_name=name,
                dataset_path=dataset_path,
                domain=meta["domain"],
                target_column=meta["target"],
                problem_type=meta["problem_type"],
            )
            results.append(result)
            logger.info(
                "  -> %s (%.1fs) best=%s score=%.4f",
                result["status"],
                result.get("duration_seconds", 0),
                result.get("best_model", "N/A"),
                result.get("best_score", 0),
            )

        return results

    def save_results(
        self, results: list[dict], output_path: Path | None = None
    ) -> None:
        """Save benchmark results to JSON."""
        path = output_path or _RESULTS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_datasets": len(results),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "error"),
            "results": results,
        }

        path.write_text(json.dumps(summary, indent=2, default=str))
        logger.info("Results saved to %s", path)
