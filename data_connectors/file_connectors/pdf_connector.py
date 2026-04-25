"""PDF table extraction connector.

Extracts tabular data from PDF files using tabula-py.
Falls back to camelot if tabula fails.
"""

import logging
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class PDFConnector(BaseConnector):
    """Connector for extracting tables from PDF files."""

    @property
    def connector_type(self) -> str:
        return "pdf"

    @property
    def display_name(self) -> str:
        return "PDF Table Extraction (.pdf)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        fp = config.get("file_path")
        if not fp:
            return False, "file_path is required"
        if not Path(fp).exists():
            return False, f"File not found: {fp}"
        if not fp.lower().endswith(".pdf"):
            return False, "File must be a PDF"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, err = self.validate_config(config)
        if not valid:
            raise DataLoadError(err)

        fp = config["file_path"]
        pages = config.get("pages", "all")
        table_index = config.get("table_index", 0)

        # Try tabula first
        try:
            import tabula
            tables = tabula.read_pdf(fp, pages=pages, multiple_tables=True)
            if not tables:
                raise DataLoadError("No tables found in PDF")

            if table_index >= len(tables):
                logger.warning(
                    "table_index=%d exceeds available tables (%d), using first",
                    table_index, len(tables),
                )
                table_index = 0

            df = tables[table_index]
            df = df.dropna(how="all").dropna(axis=1, how="all")
            logger.info(
                "Extracted table %d from PDF: %d rows x %d cols (%d tables total)",
                table_index, len(df), len(df.columns), len(tables),
            )
            return df

        except ImportError:
            logger.warning("tabula-py not available, trying camelot")

        # Fallback to camelot
        try:
            import camelot
            tables = camelot.read_pdf(fp, pages=str(pages) if pages != "all" else "all")
            if len(tables) == 0:
                raise DataLoadError("No tables found in PDF (camelot)")

            idx = min(table_index, len(tables) - 1)
            df = tables[idx].df

            # Use first row as header if it looks like one
            if df.iloc[0].str.match(r"^[A-Za-z]").all():
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)

            logger.info("Extracted table from PDF via camelot: %d rows x %d cols", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Neither tabula-py nor camelot is installed. Install one: pip install tabula-py")
        except Exception as e:
            raise DataLoadError(f"Failed to extract tables from PDF: {e}") from e

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        df = self.load(config)
        return df.head(n_rows)

    def get_metadata(self, config: dict) -> dict:
        fp = config.get("file_path", "")
        try:
            import tabula
            tables = tabula.read_pdf(fp, pages="all", multiple_tables=True)
            return {"n_tables": len(tables), "file_size_mb": round(Path(fp).stat().st_size / 1048576, 2)}
        except Exception:
            return {"file_size_mb": round(Path(fp).stat().st_size / 1048576, 2) if Path(fp).exists() else 0}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "file_path", "type": "file", "label": "PDF File", "required": True},
            {"name": "pages", "type": "text", "label": "Pages", "default": "all",
             "help_text": "Page numbers (e.g., '1', '1,3', '1-5', or 'all')"},
            {"name": "table_index", "type": "number", "label": "Table Index", "default": 0,
             "help_text": "Which table to extract (0 = first table)"},
        ]
