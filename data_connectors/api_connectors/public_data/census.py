"""US Census Bureau API connector."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.census.gov/data"


class CensusConnector(BaseConnector):
    """Connector for US Census Bureau data."""

    @property
    def connector_type(self) -> str:
        return "census"

    @property
    def display_name(self) -> str:
        return "US Census Bureau"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("dataset"):
            return False, "dataset is required (e.g. 'acs/acs5')"
        if not config.get("variables"):
            return False, "variables is required (e.g. 'NAME,B01001_001E')"
        if not config.get("api_key"):
            return False, "api_key is required (register at api.census.gov)"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            import requests

            year = config.get("year", 2022)
            dataset = config["dataset"]
            variables = config["variables"]
            api_key = config["api_key"]
            geo = config.get("geography", "state:*")

            url = f"{_BASE_URL}/{year}/{dataset}"
            params = {
                "get": variables,
                "for": geo,
                "key": api_key,
            }

            logger.info("Fetching Census data: %s/%s", year, dataset)
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if len(data) < 2:
                raise DataLoadError("No data returned from Census API")

            df = pd.DataFrame(data[1:], columns=data[0])

            # Convert numeric columns
            for col in df.columns:
                if col not in ("NAME", "state", "county"):
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Install requests: pip install requests")
        except Exception as e:
            raise DataLoadError(f"Census load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "dataset", "type": "text", "label": "Dataset",
             "required": True,
             "help_text": "e.g. acs/acs5, dec/sf1"},
            {"name": "year", "type": "number", "label": "Year",
             "default": 2022},
            {"name": "variables", "type": "text", "label": "Variables",
             "required": True,
             "help_text": "Comma-separated variable codes"},
            {"name": "geography", "type": "text", "label": "Geography",
             "default": "state:*",
             "help_text": "e.g. state:*, county:*&in=state:06"},
            {"name": "api_key", "type": "password", "label": "Census API Key",
             "required": True},
        ]
