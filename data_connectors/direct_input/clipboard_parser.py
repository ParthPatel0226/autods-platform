"""Clipboard/paste text parser connector."""

import io
import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ClipboardConnector(BaseConnector):
    """Parse pasted table data (tab, comma, HTML) into a DataFrame."""

    @property
    def connector_type(self) -> str:
        return "clipboard"

    @property
    def display_name(self) -> str:
        return "Paste from Clipboard"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        text = config.get("text", "").strip()
        if not text:
            return False, "text content is required"
        return True, ""

    def _detect_delimiter(self, text: str) -> str:
        """Auto-detect delimiter from pasted text."""
        first_line = text.split("\n")[0]
        tab_count = first_line.count("\t")
        comma_count = first_line.count(",")
        pipe_count = first_line.count("|")
        semicolon_count = first_line.count(";")

        counts = {
            "\t": tab_count,
            ",": comma_count,
            "|": pipe_count,
            ";": semicolon_count,
        }
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        text = config["text"].strip()

        # Try HTML table first
        if "<table" in text.lower():
            try:
                tables = pd.read_html(io.StringIO(text))
                if tables:
                    logger.info("Parsed HTML table: %d rows", len(tables[0]))
                    return tables[0]
            except Exception:
                pass

        # Detect delimiter and parse
        delimiter = config.get("delimiter") or self._detect_delimiter(text)
        try:
            df = pd.read_csv(
                io.StringIO(text),
                delimiter=delimiter,
                skipinitialspace=True,
            )
            if df.empty:
                raise DataLoadError("Parsed text produced empty DataFrame")

            df.columns = df.columns.str.strip()
            logger.info(
                "Parsed clipboard: %d rows x %d columns (delimiter=%r)",
                len(df), len(df.columns), delimiter,
            )
            return df

        except Exception as e:
            raise DataLoadError(f"Failed to parse pasted text: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "text", "type": "textarea", "label": "Paste Data Here",
             "required": True,
             "help_text": "Tab-separated, comma-separated, or HTML table"},
            {"name": "delimiter", "type": "select", "label": "Delimiter",
             "options": ["auto", ",", "\t", "|", ";"],
             "default": "auto",
             "help_text": "Auto-detected if not specified"},
        ]
