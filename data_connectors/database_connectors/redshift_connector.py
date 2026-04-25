"""Amazon Redshift connector via SQLAlchemy + redshift-connector."""

import logging
import re

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class RedshiftConnector(BaseConnector):
    """Connector for Amazon Redshift."""

    @property
    def connector_type(self) -> str:
        return "redshift"

    @property
    def display_name(self) -> str:
        return "Amazon Redshift"

    def _build_url(self, config: dict) -> str:
        if conn_str := config.get("connection_string"):
            return conn_str
        host = config.get("host", "")
        port = config.get("port", 5439)
        database = config.get("database", "")
        user = config.get("user", "")
        password = config.get("password", "")
        return (
            f"redshift+redshift_connector://{user}:{password}"
            f"@{host}:{port}/{database}"
        )

    def validate_config(self, config: dict) -> tuple[bool, str]:
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
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        try:
            from sqlalchemy import create_engine, text

            url = self._build_url(config)
            engine = create_engine(url, connect_args={"timeout": 30})
            query = config.get("query")
            if not query:
                table = config["table"]
                if not all(c.isalnum() or c in "_." for c in table):
                    raise DataLoadError(f"Invalid table name: {table}")
                query = f"SELECT * FROM {table}"

            logger.info("Executing Redshift query (%.50s...)", query[:50])
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn)

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df
        except ImportError:
            raise DataLoadError(
                "Install redshift-connector: "
                "pip install redshift-connector sqlalchemy-redshift"
            )
        except Exception as e:
            raise DataLoadError(f"Redshift load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        query = config.get("query")
        if query:
            config = {**config, "query": f"SELECT * FROM ({query}) sub LIMIT {n_rows}"}
        elif config.get("table"):
            table = config["table"]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
                raise DataLoadError(f"Invalid table name: {table}")
            config = {
                **config,
                "query": f"SELECT * FROM {table} LIMIT {n_rows}",
            }
        return self.load(config)

    def get_metadata(self, config: dict) -> dict:
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(
                self._build_url(config), connect_args={"timeout": 30}
            )
            with engine.connect() as conn:
                tables = pd.read_sql(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ), conn)
            return {"tables": tables["tablename"].tolist()}
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "host", "type": "text", "label": "Cluster Endpoint",
             "required": True,
             "help_text": "e.g., my-cluster.abc123.us-east-1.redshift.amazonaws.com"},
            {"name": "port", "type": "number", "label": "Port",
             "default": 5439, "required": True},
            {"name": "database", "type": "text", "label": "Database",
             "required": True},
            {"name": "user", "type": "text", "label": "Username",
             "required": True},
            {"name": "password", "type": "password", "label": "Password",
             "required": True},
            {"name": "query", "type": "textarea", "label": "SQL Query"},
            {"name": "table", "type": "text", "label": "Table Name"},
        ]
