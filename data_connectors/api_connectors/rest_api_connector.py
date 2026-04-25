"""Generic REST API connector with pagination support."""

import logging
import re
from urllib.parse import urlparse

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_MAX_PAGES = 1000
_TIMEOUT = 30


class RESTAPIConnector(BaseConnector):
    """Connector for generic REST API endpoints."""

    @property
    def connector_type(self) -> str:
        return "rest_api"

    @property
    def display_name(self) -> str:
        return "REST API"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        url = config.get("url", "")
        if not url:
            return False, "url is required"
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "URL must use http or https"
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            if not config.get("allow_localhost"):
                return False, "localhost URLs blocked (set allow_localhost=True)"
        return True, ""

    def _build_headers(self, config: dict) -> dict:
        headers = config.get("headers", {})
        auth_type = config.get("auth_type")
        auth_token = config.get("auth_token", "")
        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth_token}"
        elif auth_type == "api_key":
            key_name = config.get("api_key_header", "X-API-Key")
            headers[key_name] = auth_token
        headers.setdefault("User-Agent", "AutoDS/1.0")
        return headers

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        try:
            import requests

            url = config["url"]
            method = config.get("method", "GET").upper()
            headers = self._build_headers(config)
            params = config.get("params", {})
            json_body = config.get("json_body")
            data_path = config.get("data_path", "")

            all_records: list[dict] = []
            page = 0

            while page < _MAX_PAGES:
                resp = requests.request(
                    method, url, headers=headers, params=params,
                    json=json_body, timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()

                # Navigate to data path (e.g. "results.items")
                if data_path:
                    for key in data_path.split("."):
                        data = data[key]

                if isinstance(data, list):
                    all_records.extend(data)
                elif isinstance(data, dict):
                    all_records.append(data)
                    break
                else:
                    break

                # Pagination
                pagination = config.get("pagination")
                if not pagination:
                    break

                if pagination == "offset":
                    limit = config.get("page_size", 100)
                    offset = (page + 1) * limit
                    params[config.get("offset_param", "offset")] = offset
                    if len(data) < limit:
                        break
                elif pagination == "cursor":
                    cursor_field = config.get("cursor_field", "next_cursor")
                    raw = resp.json()
                    cursor = raw.get(cursor_field)
                    if not cursor:
                        break
                    params[config.get("cursor_param", "cursor")] = cursor
                elif pagination == "page":
                    page_param = config.get("page_param", "page")
                    params[page_param] = page + 2
                    if len(data) == 0:
                        break
                elif pagination == "next_url":
                    raw = resp.json()
                    next_url = raw.get(config.get("next_url_field", "next"))
                    if not next_url:
                        break
                    # Validate next_url with the same SSRF checks as the initial URL
                    _parsed_next = urlparse(next_url)
                    if _parsed_next.scheme not in ("http", "https"):
                        raise DataLoadError(f"next_url has invalid scheme: {_parsed_next.scheme}")
                    _next_host = _parsed_next.hostname or ""
                    if _next_host in ("localhost", "127.0.0.1", "0.0.0.0"):
                        raise DataLoadError(f"next_url targets blocked host: {_next_host}")
                    if (re.match(r"^169\.254\.", _next_host) or
                            re.match(r"^10\.", _next_host) or
                            re.match(r"^192\.168\.", _next_host)):
                        raise DataLoadError(f"next_url targets private/internal IP: {_next_host}")
                    url = next_url
                else:
                    break

                page += 1

            if not all_records:
                raise DataLoadError("API returned no data")

            df = pd.json_normalize(all_records)
            logger.info("Loaded %d rows x %d columns from API", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Install requests: pip install requests")
        except Exception as e:
            raise DataLoadError(f"REST API load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        preview_config = {**config}
        if config.get("pagination"):
            preview_config["pagination"] = None
        df = self.load(preview_config)
        return df.head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "url", "type": "text", "label": "API URL", "required": True},
            {"name": "method", "type": "select", "label": "HTTP Method",
             "options": ["GET", "POST"], "default": "GET"},
            {"name": "auth_type", "type": "select", "label": "Auth Type",
             "options": ["none", "bearer", "api_key", "basic"]},
            {"name": "auth_token", "type": "password", "label": "Token / API Key"},
            {"name": "data_path", "type": "text", "label": "JSON Data Path",
             "help_text": "Dot-separated path to data array (e.g. results.items)"},
            {"name": "pagination", "type": "select", "label": "Pagination",
             "options": ["none", "offset", "cursor", "page", "next_url"]},
        ]
