"""Upload service — data ingestion for the AutoDS API layer.

Wraps backend data-connector modules.  Never modifies backend files.

Backend name notes (verified against SIGNATURES.md):
  - smart_load        → data_connectors.universal_loader.smart_load
  - sanitize_dataframe→ validation.input_sanitizer.sanitize_dataframe
  - ConnectorFactory  → data_connectors.connector_factory.ConnectorFactory
  - MultiSourceManager→ data_connectors.multi_source_manager.MultiSourceManager
  - suggest_join_keys → data_connectors.schema_matcher.suggest_join_keys
  - SAMPLE_DATASETS   → data_connectors.direct_input.sample_datasets.SAMPLE_DATASETS
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_log_entry(
    step: str,
    tool: str,
    params: dict,
    duration: float,
    status: str,
    error: str | None = None,
) -> dict:
    entry: dict[str, Any] = {
        "timestamp": _now_iso(),
        "step": step,
        "tool": tool,
        "params": params,
        "duration_seconds": round(duration, 3),
        "status": status,
    }
    if error:
        entry["error"] = error
    return entry


def _df_preview(df, n: int = 10) -> list[dict]:  # type: ignore[type-arg]
    """Return first *n* rows as a list of dicts (JSON-safe)."""
    preview = df.head(n).copy()
    # Convert non-JSON-serialisable types (e.g. Timestamp, numpy int64)
    for col in preview.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        preview[col] = preview[col].astype(str)
    return preview.to_dict(orient="records")


def _load_bytes_as_df(file_bytes: bytes, source_id: str):  # type: ignore[return]
    """Write *file_bytes* to a temp file and call smart_load.

    *source_id* carries the original file extension (e.g. ``abc.csv``).
    """
    from data_connectors.universal_loader import smart_load  # type: ignore[import]

    ext = Path(source_id).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        df = smart_load(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_file(
    file_bytes: bytes,
    filename: str,
    project_id: str,
    user_id: str,
) -> dict:
    """Ingest raw file bytes, sanitise, store, and return upload metadata.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original filename (used for extension detection).
        project_id: Project to associate the source with.
        user_id: Owning user (for pipeline log stamping).

    Returns:
        Dict with keys: source_id, preview, schema, n_rows, n_cols,
        detected_format, sanitization_issues.

    Raises:
        DataLoadError: If smart_load cannot parse the file.
    """
    from core.exceptions import DataLoadError  # type: ignore[import]
    from data_connectors.universal_loader import smart_load  # type: ignore[import]
    from validation.input_sanitizer import sanitize_dataframe  # type: ignore[import]
    from api.services.state_service import append_to_pipeline_log
    from api.storage.file_storage import upload_dataset

    ext = Path(filename).suffix or ".bin"
    t0 = time.time()

    # Write to temp file for smart_load (takes a path, not bytes)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        df = smart_load(tmp_path)
    except Exception as exc:
        duration = time.time() - t0
        try:
            append_to_pipeline_log(
                project_id,
                _build_log_entry("upload", "smart_load", {"filename": filename},
                                 duration, "error", str(exc)),
            )
        except Exception:
            pass
        raise DataLoadError(f"Could not parse '{filename}': {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Sanitise
    try:
        df, issues = sanitize_dataframe(df)
    except Exception as exc:
        logger.warning("sanitize_dataframe failed for '%s': %s", filename, exc)
        issues = []

    # Persist raw bytes
    source_id = upload_dataset(file_bytes, filename, project_id)

    duration = time.time() - t0
    try:
        append_to_pipeline_log(
            project_id,
            _build_log_entry(
                "upload", "smart_load",
                {"filename": filename, "source_id": source_id},
                duration, "success",
            ),
        )
    except Exception:
        pass

    return {
        "source_id": source_id,
        "preview": _df_preview(df),
        "schema": _df_schema(df),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "detected_format": ext.lstrip("."),
        "sanitization_issues": issues,
    }


def list_sample_datasets() -> list[dict]:
    """Return metadata for all built-in sample datasets.

    Returns:
        List of dicts with keys: key, name, description, domain,
        problem_type, rows, icon.
    """
    from data_connectors.direct_input.sample_datasets import SampleDatasetConnector  # type: ignore[import]

    return SampleDatasetConnector.list_available()


def load_sample_dataset(
    dataset_name: str,
    project_id: str,
    user_id: str,
) -> dict:
    """Generate a built-in sample dataset, store it, and return metadata.

    Args:
        dataset_name: Key from SAMPLE_DATASETS (e.g. ``"customer_churn"``).
        project_id: Project to associate the source with.
        user_id: Owning user (for pipeline log stamping).

    Returns:
        Same shape as ``upload_file`` return value.

    Raises:
        DataLoadError: If *dataset_name* is unknown.
    """
    from core.exceptions import DataLoadError  # type: ignore[import]
    from data_connectors.direct_input.sample_datasets import (  # type: ignore[import]
        SAMPLE_DATASETS,
        SampleDatasetConnector,
    )
    from validation.input_sanitizer import sanitize_dataframe  # type: ignore[import]
    from api.services.state_service import append_to_pipeline_log
    from api.storage.file_storage import upload_dataset

    if dataset_name not in SAMPLE_DATASETS:
        available = ", ".join(SAMPLE_DATASETS.keys())
        raise DataLoadError(
            f"Unknown sample dataset '{dataset_name}'. Available: {available}"
        )

    t0 = time.time()
    connector = SampleDatasetConnector()
    df = connector.load({"dataset_name": dataset_name})

    try:
        df, issues = sanitize_dataframe(df)
    except Exception as exc:
        logger.warning("sanitize_dataframe failed for sample '%s': %s", dataset_name, exc)
        issues = []

    # Serialise to parquet for storage
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    file_bytes = buf.getvalue()
    filename = f"{dataset_name}.parquet"

    source_id = upload_dataset(file_bytes, filename, project_id)

    duration = time.time() - t0
    try:
        append_to_pipeline_log(
            project_id,
            _build_log_entry(
                "upload", "load_sample_dataset",
                {"dataset_name": dataset_name, "source_id": source_id},
                duration, "success",
            ),
        )
    except Exception:
        pass

    return {
        "source_id": source_id,
        "preview": _df_preview(df),
        "schema": _df_schema(df),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "detected_format": "parquet",
        "sanitization_issues": issues,
    }


def load_via_connector(
    connector_type: str,
    config: dict,
    project_id: str,
    user_id: str,
) -> dict:
    """Load data through a named connector, store it, and return metadata.

    Args:
        connector_type: Connector identifier (e.g. ``"postgres"``, ``"s3"``).
        config: Connector-specific configuration dict.
        project_id: Project to associate the source with.
        user_id: Owning user (for pipeline log stamping).

    Returns:
        Same shape as ``upload_file`` return value.

    Raises:
        UnsupportedFileTypeError: If *connector_type* is not registered.
        DataLoadError: If the connector fails to load data.
    """
    from core.exceptions import DataLoadError, UnsupportedFileTypeError  # type: ignore[import]
    from data_connectors.connector_factory import ConnectorFactory  # type: ignore[import]
    from validation.input_sanitizer import sanitize_dataframe  # type: ignore[import]
    from api.services.state_service import append_to_pipeline_log
    from api.storage.file_storage import upload_dataset

    available = ConnectorFactory.list_available_connectors()
    if connector_type not in available:
        raise UnsupportedFileTypeError(
            f"Connector '{connector_type}' not registered. "
            f"Available: {', '.join(available)}"
        )

    t0 = time.time()
    try:
        connector = ConnectorFactory.get_connector(connector_type)
        df = connector.load(config)
    except (DataLoadError, UnsupportedFileTypeError):
        raise
    except Exception as exc:
        duration = time.time() - t0
        try:
            append_to_pipeline_log(
                project_id,
                _build_log_entry("upload", f"connector:{connector_type}",
                                 {"connector_type": connector_type},
                                 duration, "error", str(exc)),
            )
        except Exception:
            pass
        raise DataLoadError(
            f"Connector '{connector_type}' failed to load data: {exc}"
        ) from exc

    try:
        df, issues = sanitize_dataframe(df)
    except Exception as exc:
        logger.warning("sanitize_dataframe failed for connector '%s': %s", connector_type, exc)
        issues = []

    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    file_bytes = buf.getvalue()
    filename = f"{connector_type}_data.parquet"

    source_id = upload_dataset(file_bytes, filename, project_id)

    duration = time.time() - t0
    try:
        append_to_pipeline_log(
            project_id,
            _build_log_entry(
                "upload", f"connector:{connector_type}",
                {"connector_type": connector_type, "source_id": source_id},
                duration, "success",
            ),
        )
    except Exception:
        pass

    return {
        "source_id": source_id,
        "preview": _df_preview(df),
        "schema": _df_schema(df),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "detected_format": "parquet",
        "sanitization_issues": issues,
    }


def suggest_join_keys(
    left_source_id: str,
    right_source_id: str,
    project_id: str,
) -> dict:
    """Suggest join keys between two stored sources.

    Downloads both sources, runs schema matching, and returns ranked
    join-key suggestions.

    Args:
        left_source_id: source_id of the left dataset.
        right_source_id: source_id of the right dataset.
        project_id: Project owning the sources.

    Returns:
        Dict with keys: suggestions (list of dicts with left_col, right_col,
        name_similarity, value_overlap, score), confidence (best score),
        reasoning (human-readable summary).
    """
    from data_connectors.schema_matcher import suggest_join_keys as _suggest  # type: ignore[import]
    from api.storage.file_storage import download_dataset

    left_bytes = download_dataset(left_source_id, project_id)
    right_bytes = download_dataset(right_source_id, project_id)

    left_df = _load_bytes_as_df(left_bytes, left_source_id)
    right_df = _load_bytes_as_df(right_bytes, right_source_id)

    suggestions = _suggest(left_df, right_df)

    confidence = suggestions[0]["score"] if suggestions else 0.0
    if suggestions:
        top = suggestions[0]
        reasoning = (
            f"Best match: '{top['left_col']}' ↔ '{top['right_col']}' "
            f"(name similarity {top['name_similarity']:.2f}, "
            f"value overlap {top['value_overlap']:.2f})"
        )
    else:
        reasoning = "No join key candidates found."

    return {
        "suggestions": suggestions,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def apply_join(
    plan: dict,
    project_id: str,
    user_id: str,
) -> dict:
    """Join two sources according to *plan* and store the result.

    Args:
        plan: Dict with keys left_source_id, right_source_id,
              join_keys (list of {left_column, right_column}), join_type.
        project_id: Project owning the sources.
        user_id: Owning user (for pipeline log stamping).

    Returns:
        Dict with keys: joined_source_id, n_rows, n_cols, columns.

    Raises:
        DataLoadError: If either source cannot be loaded or join fails.
    """
    from core.exceptions import DataLoadError  # type: ignore[import]
    from data_connectors.multi_source_manager import MultiSourceManager  # type: ignore[import]
    from api.services.state_service import append_to_pipeline_log
    from api.storage.file_storage import download_dataset, upload_dataset

    left_source_id = plan["left_source_id"]
    right_source_id = plan["right_source_id"]
    join_keys = plan["join_keys"]          # list of {left_column, right_column}
    join_type = plan.get("join_type", "inner")

    t0 = time.time()

    try:
        left_bytes = download_dataset(left_source_id, project_id)
        right_bytes = download_dataset(right_source_id, project_id)

        left_df = _load_bytes_as_df(left_bytes, left_source_id)
        right_df = _load_bytes_as_df(right_bytes, right_source_id)
    except Exception as exc:
        raise DataLoadError(f"Failed to load sources for join: {exc}") from exc

    # Build the join key mapping: list of (left_col, right_col) tuples
    key_pairs = [(jk["left_column"], jk["right_column"]) for jk in join_keys]

    try:
        mgr = MultiSourceManager()
        mgr.add_source("left", left_df)
        mgr.add_source("right", right_df)
        joined_df = mgr.join("left", "right", on=key_pairs, how=join_type)
    except Exception as exc:
        duration = time.time() - t0
        try:
            append_to_pipeline_log(
                project_id,
                _build_log_entry(
                    "upload", "apply_join",
                    {"left": left_source_id, "right": right_source_id},
                    duration, "error", str(exc),
                ),
            )
        except Exception:
            pass
        raise DataLoadError(f"Join failed: {exc}") from exc

    buf = io.BytesIO()
    joined_df.to_parquet(buf, index=False)
    file_bytes = buf.getvalue()
    joined_source_id = upload_dataset(file_bytes, "joined.parquet", project_id)

    duration = time.time() - t0
    try:
        append_to_pipeline_log(
            project_id,
            _build_log_entry(
                "upload", "apply_join",
                {
                    "left": left_source_id,
                    "right": right_source_id,
                    "joined_source_id": joined_source_id,
                    "join_type": join_type,
                },
                duration, "success",
            ),
        )
    except Exception:
        pass

    return {
        "joined_source_id": joined_source_id,
        "n_rows": len(joined_df),
        "n_cols": len(joined_df.columns),
        "columns": list(joined_df.columns),
    }


def get_preview(
    source_id: str,
    project_id: str,
    n_rows: int = 50,
) -> dict:
    """Return a preview of a stored source.

    Args:
        source_id: Identifier returned by upload_file / load_sample_dataset.
        project_id: Project owning the source.
        n_rows: Number of rows to include in the preview.

    Returns:
        Dict with keys: preview (list of row dicts), schema, n_rows, n_cols.

    Raises:
        DataLoadError: If the source cannot be found or parsed.
    """
    from core.exceptions import DataLoadError  # type: ignore[import]
    from api.storage.file_storage import download_dataset

    try:
        file_bytes = download_dataset(source_id, project_id)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Source '{source_id}' not found.") from exc

    try:
        df = _load_bytes_as_df(file_bytes, source_id)
    except Exception as exc:
        raise DataLoadError(f"Could not parse source '{source_id}': {exc}") from exc

    return {
        "preview": _df_preview(df, n_rows),
        "schema": _df_schema(df),
        "n_rows": len(df),
        "n_cols": len(df.columns),
    }


# ---------------------------------------------------------------------------
# Private helper (defined after public API to avoid forward-ref issues)
# ---------------------------------------------------------------------------

def _df_schema(df) -> dict[str, str]:  # type: ignore[type-arg]
    """Alias kept close to callers."""
    return {col: str(dtype) for col, dtype in df.dtypes.items()}
