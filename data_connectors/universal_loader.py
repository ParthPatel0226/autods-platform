"""Universal data loader with auto-detection of format, encoding, delimiter.

This is the entry point for all file-based data loading. It auto-detects
file characteristics and delegates to the appropriate connector.
"""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from core.exceptions import DataLoadError, UnsupportedFormatError
from data_connectors.connector_factory import ConnectorFactory

logger = logging.getLogger(__name__)


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Detected encoding string (e.g., 'utf-8', 'latin-1').
    """
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(min(100_000, os.path.getsize(file_path)))
        result = chardet.detect(raw)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)
        logger.info("Detected encoding: %s (confidence: %.2f)", encoding, confidence)
        return encoding if confidence > 0.5 else "utf-8"
    except ImportError:
        return "utf-8"


def detect_delimiter(file_path: str, encoding: str = "utf-8") -> str:
    """Detect CSV delimiter by sampling first few lines.
    
    Args:
        file_path: Path to the CSV file.
        encoding: File encoding.
        
    Returns:
        Detected delimiter character.
    """
    import csv

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            sample = f.read(8192)

        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
        logger.info("Detected delimiter: %r", delimiter)
        return delimiter
    except csv.Error:
        logger.info("Could not detect delimiter, defaulting to comma")
        return ","


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file for reproducibility tracking.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        Hex string of SHA256 hash.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    return os.path.getsize(file_path) / (1024 * 1024)


def smart_load(
    file_path: str,
    config: dict | None = None,
    max_rows: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Smart-load any supported file format.
    
    Auto-detects format, encoding, and delimiter. Returns the loaded
    DataFrame along with metadata about the loading process.
    
    Args:
        file_path: Path to the data file.
        config: Optional override config for the connector.
        max_rows: Maximum rows to load (for large files).
        
    Returns:
        Tuple of (DataFrame, metadata_dict).
        
    Raises:
        DataLoadError: If loading fails.
        UnsupportedFormatError: If file format is not supported.
    """
    path = Path(file_path)

    if not path.exists():
        raise DataLoadError(f"File not found: {file_path}")

    ext = path.suffix.lstrip(".").lower()
    size_mb = get_file_size_mb(file_path)

    logger.info("Loading file: %s (%.1f MB, format: %s)", path.name, size_mb, ext)

    # Build loading config
    load_config = config or {}
    load_config["file_path"] = str(path)

    # For CSV/TSV: auto-detect encoding and delimiter
    if ext in ("csv", "tsv", "txt"):
        if "encoding" not in load_config:
            load_config["encoding"] = detect_encoding(file_path)
        if "delimiter" not in load_config:
            load_config["delimiter"] = detect_delimiter(file_path, load_config["encoding"])

    # For large files: use chunked loading or sampling
    if max_rows:
        load_config["nrows"] = max_rows
    elif size_mb > 500:
        logger.warning(
            "File is %.1f MB. Loading first 1M rows for initial analysis. "
            "Full data will be loaded into DuckDB for queries.", size_mb
        )
        load_config["nrows"] = 1_000_000

    # Get the right connector and load
    try:
        connector = ConnectorFactory.get_connector_for_file(file_path)
        df = connector.load(load_config)
    except ValueError as e:
        raise UnsupportedFormatError(str(e))
    except Exception as e:
        raise DataLoadError(f"Failed to load {path.name}: {e}")

    # Build metadata
    metadata = {
        "source_type": "file",
        "source_name": path.name,
        "source_path": str(path.absolute()),
        "format": ext,
        "row_count": len(df),
        "column_count": len(df.columns),
        "size_mb": round(size_mb, 2),
        "file_hash": compute_file_hash(file_path),
        "encoding": load_config.get("encoding", "unknown"),
        "delimiter": load_config.get("delimiter", "unknown"),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }

    logger.info(
        "Loaded %d rows × %d columns from %s",
        metadata["row_count"], metadata["column_count"], path.name
    )

    return df, metadata


def load_to_duckdb(
    df: pd.DataFrame,
    table_name: str,
    duckdb_path: str = "data/warehouse.duckdb",
) -> str:
    """Load a DataFrame into DuckDB for efficient querying.
    
    Args:
        df: DataFrame to load.
        table_name: Name for the DuckDB table.
        duckdb_path: Path to DuckDB database file.
        
    Returns:
        The table name (for reference in state).
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise DataLoadError(f"Invalid table name: {table_name}")

    import duckdb

    Path(duckdb_path).parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(duckdb_path)
    try:
        # Drop table if exists and recreate
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info("Loaded %d rows into DuckDB table '%s'", row_count, table_name)
    finally:
        conn.close()

    return table_name
