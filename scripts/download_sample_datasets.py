"""Download sample/benchmark datasets for testing and demos.

Usage:
    python scripts/download_sample_datasets.py [--all | --dataset NAME]

Downloads from sklearn, OpenML, and public URLs to:
  - evaluation/test_datasets/
  - evaluation/benchmarks/benchmark_datasets/
"""

import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Dataset catalog: maps name -> download spec + metadata
DATASET_CATALOG = {
    # Healthcare
    "breast_cancer": {
        "source": "sklearn",
        "loader": "load_breast_cancer",
        "domain": "healthcare",
        "target": "target",
        "problem_type": "classification",
    },
    "heart_disease": {
        "source": "url",
        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data",
        "columns": [
            "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal", "target",
        ],
        "domain": "healthcare",
        "target": "target",
        "problem_type": "classification",
    },
    # Finance
    "credit_default": {
        "source": "openml",
        "openml_id": 42477,
        "domain": "finance",
        "target": "default",
        "problem_type": "classification",
    },
    # E-commerce (synthetic from sklearn)
    "california_housing": {
        "source": "sklearn",
        "loader": "fetch_california_housing",
        "domain": "generic",
        "target": "MedHouseVal",
        "problem_type": "regression",
    },
    # Manufacturing
    "steel_plates_faults": {
        "source": "openml",
        "openml_id": 1504,
        "domain": "manufacturing",
        "target": "target",
        "problem_type": "classification",
    },
    # Marketing
    "bank_marketing": {
        "source": "openml",
        "openml_id": 1461,
        "domain": "marketing",
        "target": "Class",
        "problem_type": "classification",
    },
    # Generic
    "iris": {
        "source": "sklearn",
        "loader": "load_iris",
        "domain": "generic",
        "target": "target",
        "problem_type": "classification",
    },
    "diabetes": {
        "source": "sklearn",
        "loader": "load_diabetes",
        "domain": "healthcare",
        "target": "target",
        "problem_type": "regression",
    },
    "wine": {
        "source": "sklearn",
        "loader": "load_wine",
        "domain": "generic",
        "target": "target",
        "problem_type": "classification",
    },
    # Public URLs
    "titanic": {
        "source": "url",
        "url": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
        "domain": "generic",
        "target": "Survived",
        "problem_type": "classification",
    },
}

OUTPUT_DIRS = [
    Path("evaluation/test_datasets"),
    Path("evaluation/benchmarks/benchmark_datasets"),
]


def _download_sklearn(spec: dict, save_path: Path) -> None:
    """Download dataset from sklearn.datasets."""
    import pandas as pd
    from sklearn import datasets

    loader_fn = getattr(datasets, spec["loader"])
    data = loader_fn(as_frame=True)
    df = data.frame
    df.to_csv(save_path, index=False)


def _download_openml(spec: dict, save_path: Path) -> None:
    """Download dataset from OpenML."""
    import pandas as pd
    from sklearn.datasets import fetch_openml

    data = fetch_openml(data_id=spec["openml_id"], as_frame=True, parser="auto")
    df = data.frame
    # Rename target if needed
    if "target" in data and spec.get("target") == "target":
        if "target" not in df.columns:
            df["target"] = data.target
    df.to_csv(save_path, index=False)


def _download_url(spec: dict, save_path: Path) -> None:
    """Download dataset from URL."""
    import requests

    resp = requests.get(spec["url"], timeout=60)
    resp.raise_for_status()

    if spec.get("columns"):
        import pandas as pd
        import io

        df = pd.read_csv(
            io.StringIO(resp.text), header=None, names=spec["columns"]
        )
        df.to_csv(save_path, index=False)
    else:
        save_path.write_bytes(resp.content)


def download_dataset(name: str, spec: dict) -> bool:
    """Download a single dataset. Returns True on success."""
    save_path = OUTPUT_DIRS[1] / f"{name}.csv"
    test_path = OUTPUT_DIRS[0] / f"{name}.csv"

    if save_path.exists():
        logger.info("Already exists: %s", save_path)
        return True

    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        source = spec["source"]
        if source == "sklearn":
            _download_sklearn(spec, save_path)
        elif source == "openml":
            _download_openml(spec, save_path)
        elif source == "url":
            _download_url(spec, save_path)
        else:
            logger.error("Unknown source type: %s", source)
            return False

        # Copy to test_datasets too
        if not test_path.exists():
            test_path.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(save_path, test_path)

        logger.info("Downloaded %s -> %s", name, save_path)
        return True

    except Exception as e:
        logger.error("Failed to download %s: %s", name, e)
        return False


def save_catalog_metadata() -> None:
    """Save dataset catalog metadata as JSON."""
    meta_path = OUTPUT_DIRS[1] / "catalog.json"
    meta = {
        name: {
            "domain": spec["domain"],
            "target": spec["target"],
            "problem_type": spec["problem_type"],
            "file": f"{name}.csv",
        }
        for name, spec in DATASET_CATALOG.items()
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    logger.info("Saved catalog metadata to %s", meta_path)


def main(datasets: list[str] | None = None) -> None:
    """Download datasets."""
    for d in OUTPUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    targets = datasets or list(DATASET_CATALOG.keys())
    success = 0
    for name in targets:
        spec = DATASET_CATALOG.get(name)
        if not spec:
            logger.warning("Unknown dataset: %s", name)
            continue
        if download_dataset(name, spec):
            success += 1

    save_catalog_metadata()
    logger.info("Downloaded %d/%d datasets successfully.", success, len(targets))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download AutoDS benchmark datasets")
    parser.add_argument(
        "--dataset", nargs="*", help="Specific datasets to download"
    )
    args = parser.parse_args()
    main(args.dataset)
