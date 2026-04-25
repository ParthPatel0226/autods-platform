"""PostgreSQL connector via SQLAlchemy.

Connects to PostgreSQL databases and loads query results into DataFrames.
"""

import logging
import re
from typing import Any

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class PostgresConnector(BaseConnector):
    """Connector for PostgreSQL databases."""

    @property
    def connector_type(self) -> str:
        return "postgresql"

    @property
    def display_name(self) -> str:
        return "PostgreSQL"

    def _build_url(self, config: dict) -> str:
        """Build SQLAlchemy connection URL from config."""
        if conn_str := config.get("connection_string"):
            return conn_str
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "")
        user = config.get("user", "")
        password = config.get("password", "")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        """Validate PostgreSQL connection config."""
        if config.get("connection_string"):
            return True, ""
        if not config.get("host"):
            return False, "host is required"
        if not config.get("database"):
            return False, "database is required"
        if not config.get("query") and not config.get("table"):
            return False, "query or table is required"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        """Load data from PostgreSQL."""
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            from sqlalchemy import create_engine, text

            url = self._build_url(config)
            engine = create_engine(url, connect_args={"connect_timeout": 30})

            query = config.get("query")
            if not query:
                table = config["table"]
                # Validate table name: alphanumeric + underscores only
                if not all(c.isalnum() or c == "_" for c in table):
                    raise DataLoadError(f"Invalid table name: {table}")
                query = f"SELECT * FROM {table}"

            logger.info("Executing PostgreSQL query (%.50s...)", query[:50])
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Install psycopg2-binary: pip install psycopg2-binary")
        except Exception as e:
            raise DataLoadError(f"PostgreSQL load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        """Get preview with LIMIT clause."""
        query = config.get("query")
        if query:
            config = {**config, "query": f"SELECT * FROM ({query}) sub LIMIT {n_rows}"}
        elif config.get("table"):
            table = config["table"]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
                raise DataLoadError(f"Invalid table name: {table}")
            config = {**config, "query": f"SELECT * FROM {table} LIMIT {n_rows}"}
        return self.load(config)

    def get_metadata(self, config: dict) -> dict:
        """Get table list and row counts."""
        try:
            from sqlalchemy import create_engine, text

            url = self._build_url(config)
            engine = create_engine(url, connect_args={"connect_timeout": 30})
            with engine.connect() as conn:
                tables = pd.read_sql(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ), conn)
            return {"tables": tables["table_name"].tolist()}
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "host", "type": "text", "label": "Host",
             "default": "localhost", "required": True},
            {"name": "port", "type": "number", "label": "Port",
             "default": 5432, "required": True},
            {"name": "database", "type": "text", "label": "Database",
             "required": True},
            {"name": "user", "type": "text", "label": "Username",
             "required": True},
            {"name": "password", "type": "password", "label": "Password",
             "required": True},
            {"name": "query", "type": "textarea", "label": "SQL Query",
             "help_text": "SELECT query or leave empty and set table name"},
            {"name": "table", "type": "text", "label": "Table Name",
             "help_text": "Used if query is empty"},
        ]
