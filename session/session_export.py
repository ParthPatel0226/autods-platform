"""Session export -- export session as a portable JSON bundle.

Exports the full session state with metadata, suitable for sharing,
archival, or reproducing an analysis on another machine.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_session(
    state: dict[str, Any],
    output_path: str | Path,
    include_data_sample: bool = True,
    sample_rows: int = 10,
) -> str:
    """Export a session state as a portable JSON file.

    Args:
        state: Full AutoDSState dict.
        output_path: Destination file path.
        include_data_sample: Whether to include a small data preview.
        sample_rows: Number of sample rows to include.

    Returns:
        Path to the exported file.
    """
    export = _build_export(state, include_data_sample, sample_rows)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export, indent=2, default=str), encoding="utf-8")

    logger.info("Session exported to %s", out)
    return str(out)


def _build_export(
    state: dict[str, Any],
    include_data_sample: bool,
    sample_rows: int,
) -> dict[str, Any]:
    """Build the export envelope."""
    export: dict[str, Any] = {
        "format": "autods_session_export",
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "session_id": state.get("session_id", ""),
        "configuration": _extract_config(state),
        "pipeline_summary": _extract_pipeline_summary(state),
        "model_summary": _extract_model_summary(state),
        "data_summary": _extract_data_summary(state),
    }

    if include_data_sample:
        export["data_sample"] = _extract_data_sample(state, sample_rows)

    return export


def _extract_config(state: dict[str, Any]) -> dict[str, Any]:
    """Extract configuration section."""
    return {
        "user_mode": state.get("user_mode", ""),
        "detected_domain": state.get("detected_domain", ""),
        "domain_confirmed": state.get("domain_confirmed", False),
        "problem_type": state.get("problem_type", ""),
        "target_column": state.get("target_column"),
        "time_column": state.get("time_column"),
        "validation_strategy": state.get("validation_strategy", ""),
        "tuning_strategy": state.get("tuning_strategy", ""),
        "random_seed": state.get("random_seed", 42),
    }


def _extract_pipeline_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract pipeline execution summary."""
    return {
        "workflow_status": state.get("workflow_status", ""),
        "completed_steps": state.get("completed_steps", []),
        "start_timestamp": state.get("start_timestamp", ""),
        "end_timestamp": state.get("end_timestamp"),
        "total_duration_seconds": state.get("total_duration_seconds"),
        "api_call_count": state.get("api_call_count", 0),
        "api_token_count": state.get("api_token_count", 0),
        "estimated_cost_usd": state.get("estimated_cost_usd", 0.0),
        "error_count": len(state.get("errors", [])),
        "warning_count": len(state.get("warnings", [])),
    }


def _extract_model_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract model training results summary."""
    trained = state.get("trained_models", {})
    model_names = list(trained.keys())

    model_metrics: dict[str, dict] = {}
    for name, result in trained.items():
        if isinstance(result, dict):
            model_metrics[name] = result.get("metrics", {})

    return {
        "algorithms_trained": model_names,
        "best_model_name": state.get("best_model_name", ""),
        "best_model_metrics": state.get("best_model_metrics", {}),
        "model_metrics": model_metrics,
        "feature_count": len(state.get("feature_list", [])),
        "features_selected": state.get("features_selected", []),
    }


def _extract_data_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract data overview (no raw data)."""
    return {
        "row_count": state.get("row_count", 0),
        "column_count": state.get("column_count", 0),
        "data_hash": state.get("data_hash", ""),
        "quality_issues_count": len(state.get("quality_issues", [])),
        "eda_insights": state.get("eda_insights", []),
    }


def _extract_data_sample(state: dict[str, Any], n: int) -> dict[str, Any] | None:
    """Extract a small sample of the uploaded data."""
    try:
        import pandas as pd

        uploaded = state.get("uploaded_data")
        if uploaded is None:
            return None
        if isinstance(uploaded, pd.DataFrame):
            sample = uploaded.head(n)
            return {
                "columns": list(sample.columns),
                "dtypes": {col: str(dtype) for col, dtype in sample.dtypes.items()},
                "rows": sample.to_dict(orient="records"),
            }
    except Exception:
        pass
    return None


def import_session_config(export_path: str | Path) -> dict[str, Any]:
    """Import configuration from an exported session file.

    Useful for reproducing an analysis with the same settings on new data.

    Returns:
        Configuration dict that can be merged into a new session state.
    """
    path = Path(export_path)
    if not path.is_file():
        raise FileNotFoundError(f"Export file not found: {export_path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("configuration", {})
