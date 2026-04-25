"""DuckDB connector for remote files and local databases."""

import logging
import re
from urllib.parse import urlparse

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class DuckDBConnector(BaseConnector):
    """Connector for DuckDB — local DB files or remote file queries."""

    @property
    def connector_type(self) -> str:
        return "duckdb"

    @property
    def display_name(self) -> str:
        return "DuckDB"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("query") and not config.get("file_path"):
            return False, "query or file_path is required"
        file_path = config.get("file_path", "")
        if file_path.startswith(("http://", "https://")):
            parsed = urlparse(file_path)
            hostname = parsed.hostname or ""
            if hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
                return False, f"file_path targets blocked host: {hostname}"
            if (re.match(r"^169\.254\.", hostname) or
                    re.match(r"^10\.", hostname) or
                    re.match(r"^192\.168\.", hostname)):
                return False, f"file_path targets private/internal IP: {hostname}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        try:
            import duckdb

            db_path = config.get("database", ":memory:")
            conn = duckdb.connect(db_path, read_only=config.get("read_only", True))

            # Install and load httpfs for remote files
            if config.get("file_path", "").startswith(("http://", "https://", "s3://")):
                conn.execute("INSTALL httpfs; LOAD httpfs;")

            query = config.get("query")
            if not query:
                file_path = config["file_path"]
                query = f"SELECT * FROM '{file_path}'"

            logger.info("Executing DuckDB query (%.50s...)", query[:50])
            df = conn.execute(query).fetchdf()
            conn.close()

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df
        except ImportError:
            raise DataLoadError("Install duckdb: pip install duckdb")
        except Exception as e:
            raise DataLoadError(f"DuckDB load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        query = config.get("query")
        if query:
            config = {**config, "query": f"SELECT * FROM ({query}) sub LIMIT {n_rows}"}
        elif config.get("file_path"):
            fp = config["file_path"]
            config = {**config, "query": f"SELECT * FROM '{fp}' LIMIT {n_rows}"}
        return self.load(config)

    def get_metadata(self, config: dict) -> dict:
        try:
            import duckdb

            db_path = config.get("database", ":memory:")
            conn = duckdb.connect(db_path, read_only=True)
            tables = conn.execute("SHOW TABLES").fetchdf()
            conn.close()
            return {"tables": tables.iloc[:, 0].tolist() if len(tables) else []}
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "database", "type": "text", "label": "Database Path",
             "default": ":memory:",
             "help_text": "Path to .duckdb file or :memory:"},
            {"name": "file_path", "type": "text", "label": "Remote File URL",
             "help_text": "URL to CSV/Parquet (http, https, s3)"},
            {"name": "query", "type": "textarea", "label": "SQL Query",
             "help_text": "Custom SQL query"},
        ]
