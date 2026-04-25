"""Web scraper connector for HTML table extraction."""

import logging
import re
from urllib.parse import urlparse

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_TIMEOUT = 30


class WebScraperConnector(BaseConnector):
    """Extract tables from web pages using pd.read_html."""

    @property
    def connector_type(self) -> str:
        return "web_scrape"

    @property
    def display_name(self) -> str:
        return "Web Scraper (HTML Tables)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        url = config.get("url", "")
        if not url:
            return False, "url is required"
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "URL must use http or https"
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False, f"URL targets blocked host: {hostname}"
        if (re.match(r"^169\.254\.", hostname) or
                re.match(r"^10\.", hostname) or
                re.match(r"^192\.168\.", hostname)):
            return False, f"URL targets private/internal IP: {hostname}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        url = config["url"]
        table_index = config.get("table_index", 0)
        css_selector = config.get("css_selector")
        headers = {"User-Agent": "AutoDS/1.0 (Table Extraction)"}

        try:
            import requests

            resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            html = resp.text

            kwargs = {"io": html}
            if css_selector:
                kwargs["attrs"] = {"class": css_selector}

            tables = pd.read_html(**kwargs)
            if not tables:
                raise DataLoadError(f"No tables found at {url}")

            if table_index >= len(tables):
                raise DataLoadError(
                    f"Table index {table_index} out of range "
                    f"(found {len(tables)} tables)"
                )

            df = tables[table_index]
            logger.info(
                "Extracted table %d: %d rows x %d columns from %s",
                table_index, len(df), len(df.columns), url,
            )
            return df

        except ImportError:
            raise DataLoadError(
                "Install lxml and html5lib: pip install lxml html5lib"
            )
        except ValueError as e:
            raise DataLoadError(f"No tables found: {e}")
        except Exception as e:
            raise DataLoadError(f"Web scraping failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_metadata(self, config: dict) -> dict:
        try:
            import requests

            resp = requests.get(
                config["url"],
                headers={"User-Agent": "AutoDS/1.0"},
                timeout=_TIMEOUT,
            )
            tables = pd.read_html(resp.text)
            return {
                "table_count": len(tables),
                "table_shapes": [
                    {"index": i, "rows": len(t), "columns": len(t.columns)}
                    for i, t in enumerate(tables)
                ],
            }
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "url", "type": "text", "label": "Web Page URL",
             "required": True},
            {"name": "table_index", "type": "number", "label": "Table Index",
             "default": 0,
             "help_text": "Which table on the page (0 = first)"},
            {"name": "css_selector", "type": "text",
             "label": "CSS Class Selector",
             "help_text": "Filter tables by CSS class"},
        ]
