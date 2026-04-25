"""Federal Reserve Economic Data (FRED) connector."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FREDConnector(BaseConnector):
    """Connector for FRED economic time series data."""

    @property
    def connector_type(self) -> str:
        return "fred"

    @property
    def display_name(self) -> str:
        return "FRED (Federal Reserve)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("series_id"):
            return False, "series_id is required (e.g. 'GDP', 'UNRATE')"
        if not config.get("api_key"):
            return False, "api_key is required (register at fred.stlouisfed.org)"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            import requests

            series_id = config["series_id"]
            api_key = config["api_key"]

            params = {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": config.get("start_date", "2000-01-01"),
                "observation_end": config.get("end_date", "2025-12-31"),
            }

            logger.info("Fetching FRED series: %s", series_id)
            resp = requests.get(_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            observations = data.get("observations", [])
            if not observations:
                raise DataLoadError(f"No data for series {series_id}")

            df = pd.DataFrame(observations)
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df[["date", "value"]].rename(columns={"value": series_id})

            logger.info("Loaded %d observations", len(df))
            return df

        except ImportError:
            raise DataLoadError("Install requests: pip install requests")
        except Exception as e:
            raise DataLoadError(f"FRED load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "series_id", "type": "text", "label": "Series ID",
             "required": True,
             "help_text": "e.g. GDP, UNRATE, CPIAUCSL"},
            {"name": "api_key", "type": "password", "label": "FRED API Key",
             "required": True},
            {"name": "start_date", "type": "text", "label": "Start Date",
             "default": "2000-01-01"},
            {"name": "end_date", "type": "text", "label": "End Date",
             "default": "2025-12-31"},
        ]
