"""CSV file connector with auto-detection of delimiter, encoding, and header.

This is the most commonly used connector. It handles:
- Auto-detect delimiter (comma, semicolon, tab, pipe)
- Auto-detect encoding (UTF-8, Latin-1, etc.)
- Auto-detect header row
- Handle malformed rows gracefully
- Large file support with chunked reading
"""

import logging
import os
from pathlib import Path

import pandas as pd

from data_connectors.base import BaseConnector
from core.exceptions import DataLoadError

logger = logging.getLogger(__name__)


class CSVConnector(BaseConnector):
    """Connector for CSV and TSV files."""

    @property
    def connector_type(self) -> str:
        return "csv"

    @property
    def display_name(self) -> str:
        return "CSV / TSV File"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        """Validate CSV loading configuration."""
        file_path = config.get("file_path")
        if not file_path:
            return False, "file_path is required"
        if not Path(file_path).exists():
            return False, f"File not found: {file_path}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        """Load CSV file into DataFrame.

        Config options:
            file_path (str): Path to CSV file (required)
            delimiter (str): Column delimiter (auto-detected if not set)
            encoding (str): File encoding (auto-detected if not set)
            header (int | None): Header row index (default: 0)
            nrows (int | None): Max rows to load
            skiprows (int | list): Rows to skip
            na_values (list): Additional NA markers
            dtype (dict): Column type overrides
            parse_dates (list | bool): Columns to parse as dates
        """
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        file_path = config["file_path"]
        delimiter = config.get("delimiter", ",")
        encoding = config.get("encoding", "utf-8")
        header = config.get("header", 0)
        nrows = config.get("nrows")

        logger.info(
            "Loading CSV: %s (delimiter=%r, encoding=%s, nrows=%s)",
            Path(file_path).name, delimiter, encoding, nrows,
        )

        try:
            df = pd.read_csv(
                file_path,
                delimiter=delimiter,
                encoding=encoding,
                header=header,
                nrows=nrows,
                skiprows=config.get("skiprows"),
                na_values=config.get("na_values"),
                dtype=config.get("dtype"),
                parse_dates=config.get("parse_dates", False),
                low_memory=False,
                on_bad_lines="warn",
            )

            # Basic cleanup
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()

            # Drop fully empty rows and columns
            df = df.dropna(how="all")
            df = df.dropna(axis=1, how="all")

            logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))
            return df

        except UnicodeDecodeError:
            # Retry with latin-1 encoding
            logger.warning("UTF-8 decode failed, retrying with latin-1")
            try:
                df = pd.read_csv(
                    file_path,
                    delimiter=delimiter,
                    encoding="latin-1",
                    header=header,
                    nrows=nrows,
                    low_memory=False,
                    on_bad_lines="warn",
                )
                df.columns = df.columns.str.strip()
                return df
            except Exception as e2:
                raise DataLoadError(f"Failed to load CSV with both UTF-8 and Latin-1: {e2}")

        except pd.errors.EmptyDataError:
            raise DataLoadError(f"File is empty: {file_path}")

        except Exception as e:
            raise DataLoadError(f"Failed to load CSV: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        """Get a quick preview of the first N rows."""
        preview_config = {**config, "nrows": n_rows}
        return self.load(preview_config)

    def get_metadata(self, config: dict) -> dict:
        """Get file metadata without loading all data."""
        file_path = config.get("file_path", "")
        path = Path(file_path)

        metadata = {
            "file_name": path.name,
            "file_size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
            "extension": path.suffix,
        }

        # Quick row count (read just line count)
        try:
            with open(file_path, "rb") as f:
                metadata["estimated_rows"] = sum(1 for _ in f) - 1  # Subtract header
        except Exception:
            metadata["estimated_rows"] = None

        return metadata

    def get_config_schema(self) -> list[dict]:
        """Return configuration fields for the Streamlit upload form."""
        return [
            {"name": "file_path", "type": "file", "label": "CSV File", "required": True},
            {"name": "delimiter", "type": "select", "label": "Delimiter",
             "options": [",", ";", "\t", "|"], "default": ",",
             "help_text": "Auto-detected if not specified"},
            {"name": "encoding", "type": "select", "label": "Encoding",
             "options": ["utf-8", "latin-1", "cp1252", "iso-8859-1"],
             "default": "utf-8", "help_text": "Auto-detected if not specified"},
            {"name": "header", "type": "number", "label": "Header Row",
             "default": 0, "help_text": "Row number containing column names (0-indexed)"},
            {"name": "nrows", "type": "number", "label": "Max Rows",
             "default": None, "help_text": "Limit rows loaded (leave empty for all)"},
        ]
