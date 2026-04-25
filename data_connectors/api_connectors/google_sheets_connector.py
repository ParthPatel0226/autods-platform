"""Google Sheets connector for public spreadsheets via CSV export."""

import logging
import re

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class GoogleSheetsConnector(BaseConnector):
    """Connector for public Google Sheets."""

    @property
    def connector_type(self) -> str:
        return "google_sheets"

    @property
    def display_name(self) -> str:
        return "Google Sheets (Public)"

    def _extract_sheet_id(self, url_or_id: str) -> str:
        """Extract sheet ID from URL or return as-is."""
        # Match Google Sheets URL patterns
        match = re.search(
            r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url_or_id
        )
        if match:
            return match.group(1)
        # Assume raw ID if no URL pattern
        if re.match(r"^[a-zA-Z0-9_-]+$", url_or_id):
            return url_or_id
        raise DataLoadError(f"Invalid Google Sheets URL or ID: {url_or_id}")

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("sheet_id") and not config.get("url"):
            return False, "sheet_id or url is required"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        url_or_id = config.get("sheet_id") or config.get("url", "")
        sheet_id = self._extract_sheet_id(url_or_id)
        gid = config.get("gid", "0")

        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/export?format=csv&gid={gid}"
        )

        try:
            logger.info("Fetching Google Sheet: %s (gid=%s)", sheet_id, gid)
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip()
            logger.info(
                "Loaded %d rows x %d columns", len(df), len(df.columns)
            )
            return df
        except Exception as e:
            raise DataLoadError(
                f"Google Sheets load failed: {e}. "
                "Ensure the sheet is published/shared as 'Anyone with link'."
            )

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "sheet_id", "type": "text", "label": "Sheet ID or URL",
             "required": True,
             "help_text": "Google Sheets URL or spreadsheet ID"},
            {"name": "gid", "type": "text", "label": "Sheet Tab (gid)",
             "default": "0",
             "help_text": "Tab index (0 = first sheet)"},
        ]
