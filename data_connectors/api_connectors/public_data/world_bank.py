"""World Bank Open Data API connector."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.worldbank.org/v2"


class WorldBankConnector(BaseConnector):
    """Connector for World Bank Open Data indicators."""

    @property
    def connector_type(self) -> str:
        return "world_bank"

    @property
    def display_name(self) -> str:
        return "World Bank Open Data"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("indicator"):
            return False, "indicator code is required (e.g. 'NY.GDP.MKTP.CD')"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            import requests

            indicator = config["indicator"]
            countries = config.get("countries", "all")
            start_year = config.get("start_year", 2000)
            end_year = config.get("end_year", 2024)
            per_page = config.get("per_page", 1000)

            url = (
                f"{_BASE_URL}/country/{countries}/indicator/{indicator}"
                f"?date={start_year}:{end_year}&format=json&per_page={per_page}"
            )

            logger.info("Fetching World Bank indicator: %s", indicator)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if len(data) < 2 or not data[1]:
                raise DataLoadError(f"No data for indicator {indicator}")

            records = [
                {
                    "country": r["country"]["value"],
                    "country_code": r["countryiso3code"],
                    "year": int(r["date"]),
                    "value": r["value"],
                    "indicator": r["indicator"]["value"],
                }
                for r in data[1]
                if r.get("value") is not None
            ]

            df = pd.DataFrame(records)
            logger.info("Loaded %d records", len(df))
            return df

        except ImportError:
            raise DataLoadError("Install requests: pip install requests")
        except Exception as e:
            raise DataLoadError(f"World Bank load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "indicator", "type": "text", "label": "Indicator Code",
             "required": True,
             "help_text": "e.g. NY.GDP.MKTP.CD (GDP), SP.POP.TOTL (Population)"},
            {"name": "countries", "type": "text", "label": "Countries",
             "default": "all",
             "help_text": "ISO3 codes separated by ; or 'all'"},
            {"name": "start_year", "type": "number", "label": "Start Year",
             "default": 2000},
            {"name": "end_year", "type": "number", "label": "End Year",
             "default": 2024},
        ]
