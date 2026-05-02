"""Upload routes — file upload, sample datasets, connectors, joins, preview.

Prefix : /upload
Tags   : upload

All mutation routes (POST) require Bearer auth.
GET /samples is public (no auth needed — just listing metadata).
"""
from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel

from api.dependencies import get_current_user
from api.schemas.upload import (
    ApplyJoinResponse,
    ConnectorUploadRequest,
    JoinKey,
    JoinPlan,
    SampleDatasetInfo,
    SampleDatasetRequest,
    SuggestJoinResponse,
    UploadFileResponse,
)
from api.services import state_service
from core.exceptions import AutoDSError
from data_connectors.connector_factory import ConnectorFactory
from data_connectors.direct_input.sample_datasets import SampleDatasetConnector
from data_connectors.schema_matcher import suggest_join_keys

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory DataFrame cache  keyed by (project_id, source_id)
# ---------------------------------------------------------------------------

_SOURCE_CACHE: dict[str, dict[str, pd.DataFrame]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cache_source(project_id: str, source_id: str, df: pd.DataFrame) -> None:
    _SOURCE_CACHE.setdefault(project_id, {})[source_id] = df


def _get_cached_df(project_id: str, source_id: str) -> pd.DataFrame:
    df = _SOURCE_CACHE.get(project_id, {}).get(source_id)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{source_id}' not found in session cache. Re-upload or reload it.",
        )
    return df


def _build_schema(df: pd.DataFrame) -> dict[str, Any]:
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def _df_to_response(df: pd.DataFrame, source_id: str, detected_format: str) -> UploadFileResponse:
    return UploadFileResponse(
        source_id=source_id,
        preview=df.head(10).to_dict(orient="records"),
        schema=_build_schema(df),
        n_rows=len(df),
        n_cols=len(df.columns),
        detected_format=detected_format,
    )


def _register_source(
    project_id: str,
    user_id: str,
    source_id: str,
    df: pd.DataFrame,
    name: str,
    origin: str,
) -> None:
    """Cache df and persist source metadata to project state."""
    _cache_source(project_id, source_id, df)

    new_entry = {
        "source_id": source_id,
        "name": name,
        "origin": origin,
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "columns": list(df.columns),
    }

    try:
        # Read current state to merge data_sources list
        state = state_service.load_state(project_id, user_id)
        existing: list[dict] = list(state.get("data_sources") or [])
        existing = [s for s in existing if s.get("source_id") != source_id]
        existing.append(new_entry)
        state_service.update_state(project_id, user_id, data_sources=existing)
    except AutoDSError:
        # Non-fatal: state update failure doesn't block the upload response
        logger.warning("Failed to persist source metadata for project %s", project_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/file", response_model=UploadFileResponse)
async def upload_file(
    project_id: Annotated[str, Query(description="Project to attach this source to")],
    current_user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> UploadFileResponse:
    """Upload a file and load it into the session source cache."""
    filename = file.filename or "upload"
    suffix = Path(filename).suffix or ".csv"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        connector = ConnectorFactory.get_connector_for_file(tmp_path)
        df: pd.DataFrame = connector.load({"file_path": tmp_path})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {exc}",
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    source_id = str(uuid.uuid4())
    detected_format = Path(filename).suffix.lstrip(".").upper() or "UNKNOWN"
    _register_source(project_id, current_user["user_id"], source_id, df, filename, "file_upload")
    return _df_to_response(df, source_id, detected_format)


@router.get("/samples", response_model=list[SampleDatasetInfo])
async def list_samples() -> list[SampleDatasetInfo]:
    """List all built-in sample datasets (no auth required)."""
    available = SampleDatasetConnector.list_available()
    return [
        SampleDatasetInfo(
            name=item["key"],
            display_name=item["name"],
            domain=item["domain"],
            n_rows=item["rows"],
            n_cols=0,  # count unknown without loading
            description=item["description"],
        )
        for item in available
    ]


@router.post("/samples", response_model=UploadFileResponse)
async def load_sample(
    body: SampleDatasetRequest,
    project_id: Annotated[str, Query(description="Project to attach this source to")],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UploadFileResponse:
    """Load a built-in sample dataset into the session source cache."""
    connector = SampleDatasetConnector()
    try:
        df = connector.load({"dataset_name": body.dataset_name})
    except AutoDSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    source_id = str(uuid.uuid4())
    _register_source(
        project_id, current_user["user_id"], source_id, df, body.dataset_name, "sample"
    )
    return _df_to_response(df, source_id, "sample")


@router.post("/connector", response_model=UploadFileResponse)
async def load_connector(
    body: ConnectorUploadRequest,
    project_id: Annotated[str, Query(description="Project to attach this source to")],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UploadFileResponse:
    """Load data via a named connector (database, API, cloud, etc.)."""
    try:
        connector = ConnectorFactory.get_connector(body.connector_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        df = connector.load(body.config)
    except AutoDSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Connector load failed: {exc}",
        ) from exc

    source_id = str(uuid.uuid4())
    label = body.config.get("name") or body.connector_type
    _register_source(
        project_id, current_user["user_id"], source_id, df, label, body.connector_type
    )
    return _df_to_response(df, source_id, body.connector_type)


# ---------------------------------------------------------------------------
# Join: suggest
# ---------------------------------------------------------------------------

class _JoinSuggestRequest(BaseModel):
    project_id: str
    left_source_id: str
    right_source_id: str


@router.post("/join/suggest", response_model=SuggestJoinResponse)
async def suggest_join(
    body: _JoinSuggestRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuggestJoinResponse:
    """Suggest join keys for two cached sources."""
    left_df = _get_cached_df(body.project_id, body.left_source_id)
    right_df = _get_cached_df(body.project_id, body.right_source_id)

    candidates = suggest_join_keys(left_df, right_df)

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No candidate join keys found between the two sources.",
        )

    best = candidates[0]
    confidence = float(min(best["score"], 1.0))

    plan = JoinPlan(
        left_source_id=body.left_source_id,
        right_source_id=body.right_source_id,
        join_keys=[
            JoinKey(
                left_column=best["left_col"],
                right_column=best["right_col"],
            )
        ],
        join_type="inner",
    )

    other = candidates[1:3]
    reasoning = (
        f"Best match: '{best['left_col']}' ↔ '{best['right_col']}' "
        f"(name_sim={best['name_similarity']:.2f}, dtype_match={best['dtype_match']}, "
        f"value_overlap={best['value_overlap']:.2f}, score={best['score']:.2f})"
    )
    if other:
        alts = ", ".join(f"'{c['left_col']}↔{c['right_col']}'" for c in other)
        reasoning += f". Alternatives considered: {alts}."

    return SuggestJoinResponse(plan=plan, confidence=confidence, reasoning=reasoning)


# ---------------------------------------------------------------------------
# Join: apply
# ---------------------------------------------------------------------------

@router.post("/join/apply", response_model=ApplyJoinResponse)
async def apply_join(
    body: JoinPlan,
    project_id: Annotated[str, Query(description="Project that owns these sources")],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ApplyJoinResponse:
    """Execute a join between two cached sources and cache the result."""
    left_df = _get_cached_df(project_id, body.left_source_id)
    right_df = _get_cached_df(project_id, body.right_source_id)

    left_on = [k.left_column for k in body.join_keys]
    right_on = [k.right_column for k in body.join_keys]

    try:
        joined = left_df.merge(
            right_df,
            left_on=left_on,
            right_on=right_on,
            how=body.join_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Join failed: {exc}",
        ) from exc

    joined_source_id = str(uuid.uuid4())
    _register_source(
        project_id,
        current_user["user_id"],
        joined_source_id,
        joined,
        f"joined_{body.left_source_id[:8]}_{body.right_source_id[:8]}",
        "join",
    )

    return ApplyJoinResponse(
        joined_source_id=joined_source_id,
        n_rows=len(joined),
        n_cols=len(joined.columns),
        columns=list(joined.columns),
    )


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

@router.get("/preview/{source_id}")
async def preview_source(
    source_id: str,
    project_id: Annotated[str, Query(description="Project that owns this source")],
    n: Annotated[int, Query(ge=1, le=1000)] = 50,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> dict:
    """Return the first N rows of a cached source as JSON records."""
    df = _get_cached_df(project_id, source_id)
    return {
        "source_id": source_id,
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "columns": list(df.columns),
        "rows": df.head(n).to_dict(orient="records"),
    }
