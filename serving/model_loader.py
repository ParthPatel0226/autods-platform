"""Model loading utilities for the prediction API.

Loads trained models from joblib files (primary) or MLflow registry (optional).
Includes metadata loading and feature schema validation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_cached_model: dict[str, Any] | None = None


def load_model(model_path: str) -> Any:
    """Load a trained model from a joblib file.

    Also loads the companion ``.meta.json`` sidecar if present.

    Args:
        model_path: Path to the ``.joblib`` model artifact.

    Returns:
        The deserialized scikit-learn estimator.

    Raises:
        FileNotFoundError: If the model file does not exist.
        RuntimeError: If deserialization fails.
    """
    import joblib

    p = Path(model_path)
    if not p.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    try:
        model = joblib.load(p)
    except Exception as exc:
        raise RuntimeError(f"Failed to load model from {model_path}: {exc}") from exc

    logger.info("Model loaded from %s", model_path)
    return model


def load_model_metadata(model_path: str) -> dict[str, Any]:
    """Load the metadata sidecar for a model.

    Args:
        model_path: Path to the ``.joblib`` model artifact. The metadata
            file is expected at ``<model_path>.meta.json``.

    Returns:
        Metadata dict, or empty dict if no sidecar found.
    """
    meta_path = Path(model_path).with_suffix(".meta.json")
    if not meta_path.is_file():
        return {}

    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read model metadata: %s", exc)
        return {}


def load_model_cached(model_path: str) -> tuple[Any, dict[str, Any]]:
    """Load model with in-process caching (singleton per path).

    Returns:
        Tuple of (model, metadata).
    """
    global _cached_model

    if _cached_model is not None and _cached_model.get("path") == model_path:
        return _cached_model["model"], _cached_model["metadata"]

    model = load_model(model_path)
    metadata = load_model_metadata(model_path)

    _cached_model = {"path": model_path, "model": model, "metadata": metadata}
    return model, metadata


def get_feature_names(metadata: dict[str, Any]) -> list[str]:
    """Extract feature names from model metadata.

    Args:
        metadata: Metadata dict from ``load_model_metadata``.

    Returns:
        List of feature column names, or empty list if unavailable.
    """
    return metadata.get("feature_names", [])


def get_model_info(metadata: dict[str, Any]) -> dict[str, Any]:
    """Extract human-readable model info for the /info endpoint.

    Args:
        metadata: Metadata dict.

    Returns:
        Dict with algorithm, problem_type, trained_at, metrics, etc.
    """
    return {
        "algorithm": metadata.get("algorithm", "unknown"),
        "problem_type": metadata.get("problem_type", "unknown"),
        "trained_at": metadata.get("trained_at", ""),
        "features": len(metadata.get("feature_names", [])),
        "domain": metadata.get("domain", "generic"),
    }


def try_load_mlflow(run_id: str, artifact_path: str = "model") -> Any | None:
    """Attempt to load model from MLflow registry.

    Returns None if MLflow is not available or loading fails.
    """
    try:
        import mlflow.sklearn

        model_uri = f"runs:/{run_id}/{artifact_path}"
        model = mlflow.sklearn.load_model(model_uri)
        logger.info("Model loaded from MLflow run %s", run_id)
        return model
    except Exception as exc:
        logger.warning("MLflow model load failed: %s", exc)
        return None


def clear_cache() -> None:
    """Clear the cached model (useful for reloading after retraining)."""
    global _cached_model
    _cached_model = None
