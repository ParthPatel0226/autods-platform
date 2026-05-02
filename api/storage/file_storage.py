"""File storage helpers for datasets, models, and reports.

Uses Supabase Storage buckets when credentials are available; otherwise
falls back to local /tmp/autods_storage/{project_id}/.

Return shapes are identical in both modes so callers need no branching.

Bucket layout (Supabase):
    datasets/{project_id}/{source_id}
    models/{project_id}/{model_id}
    reports/{project_id}/{report_id}
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from api.storage.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_LOCAL_ROOT = Path(os.getenv("AUTODS_LOCAL_STORAGE", "/tmp/autods_storage"))

_BUCKET_DATASETS = "autods-datasets"
_BUCKET_MODELS = "autods-models"
_BUCKET_REPORTS = "autods-reports"
_SIGNED_URL_TTL = 3600  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _local_path(project_id: str, bucket: str, file_id: str) -> Path:
    p = _LOCAL_ROOT / bucket / project_id / file_id
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _supabase_key(project_id: str, file_id: str) -> str:
    return f"{project_id}/{file_id}"


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

def upload_dataset(file_bytes: bytes, filename: str, project_id: str) -> str:
    """Store raw dataset bytes; return a stable source_id."""
    ext = Path(filename).suffix or ".bin"
    source_id = f"{uuid.uuid4().hex}{ext}"
    sb = get_supabase()

    if sb is not None:
        try:
            sb.storage.from_(_BUCKET_DATASETS).upload(
                path=_supabase_key(project_id, source_id),
                file=file_bytes,
                file_options={"content-type": "application/octet-stream"},
            )
            return source_id
        except Exception as exc:
            logger.warning("Supabase dataset upload failed: %s — using local.", exc)

    _local_path(project_id, "datasets", source_id).write_bytes(file_bytes)
    return source_id


def download_dataset(source_id: str, project_id: str) -> bytes:
    """Return raw bytes for a previously uploaded dataset."""
    sb = get_supabase()

    if sb is not None:
        try:
            return sb.storage.from_(_BUCKET_DATASETS).download(
                _supabase_key(project_id, source_id)
            )
        except Exception as exc:
            logger.warning("Supabase dataset download failed: %s — trying local.", exc)

    local = _local_path(project_id, "datasets", source_id)
    if not local.exists():
        raise FileNotFoundError(f"Dataset {source_id!r} not found.")
    return local.read_bytes()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def upload_model(model_bytes: bytes, project_id: str) -> str:
    """Store serialised model bytes; return a stable model_id."""
    model_id = f"{uuid.uuid4().hex}.joblib"
    sb = get_supabase()

    if sb is not None:
        try:
            sb.storage.from_(_BUCKET_MODELS).upload(
                path=_supabase_key(project_id, model_id),
                file=model_bytes,
                file_options={"content-type": "application/octet-stream"},
            )
            return model_id
        except Exception as exc:
            logger.warning("Supabase model upload failed: %s — using local.", exc)

    _local_path(project_id, "models", model_id).write_bytes(model_bytes)
    return model_id


def download_model(model_id: str, project_id: str) -> bytes:
    """Return raw bytes for a previously uploaded model."""
    sb = get_supabase()

    if sb is not None:
        try:
            return sb.storage.from_(_BUCKET_MODELS).download(
                _supabase_key(project_id, model_id)
            )
        except Exception as exc:
            logger.warning("Supabase model download failed: %s — trying local.", exc)

    local = _local_path(project_id, "models", model_id)
    if not local.exists():
        raise FileNotFoundError(f"Model {model_id!r} not found.")
    return local.read_bytes()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def upload_report(
    report_bytes: bytes,
    project_id: str,
    format: str,
) -> tuple[str, str]:
    """Store report bytes; return (report_id, signed_url).

    signed_url is a time-limited download link (Supabase) or a
    ``file://`` path indicator (local fallback).
    """
    ext_map = {"html": ".html", "pdf": ".pdf", "zip": ".zip", "notebook": ".ipynb"}
    ext = ext_map.get(format, ".bin")
    report_id = f"{uuid.uuid4().hex}{ext}"
    sb = get_supabase()

    if sb is not None:
        try:
            key = _supabase_key(project_id, report_id)
            sb.storage.from_(_BUCKET_REPORTS).upload(
                path=key,
                file=report_bytes,
                file_options={"content-type": "application/octet-stream"},
            )
            signed = sb.storage.from_(_BUCKET_REPORTS).create_signed_url(
                key, _SIGNED_URL_TTL
            )
            url = signed.get("signedURL") or signed.get("signed_url", "")
            return report_id, url
        except Exception as exc:
            logger.warning("Supabase report upload failed: %s — using local.", exc)

    local = _local_path(project_id, "reports", report_id)
    local.write_bytes(report_bytes)
    return report_id, f"file://{local}"
