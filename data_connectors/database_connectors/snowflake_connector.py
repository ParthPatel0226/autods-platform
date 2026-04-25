"""Snowflake connector via snowflake-connector-python."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class SnowflakeConnector(BaseConnector):
    """Connector for Snowflake Data Cloud."""

    @property
    def connector_type(self) -> str:
        return "snowflake"

    @property
    def display_name(self) -> str:
        return "Snowflake"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("account"):
            return False, "account is required"
        if not config.get("user"):
            return False, "user is required"
        if not config.get("password"):
            return False, "password is required"
        if not config.get("query") and not config.get("table"):
            return False, "query or table is required"
        return True, ""

    def _connect(self, config: dict):
        import snowflake.connector

        return snowflake.connector.connect(
            account=config["account"],
            user=config["user"],
            password=config["password"],
            warehouse=config.get("warehouse"),
            database=config.get("database"),
            schema=config.get("schema"),
            login_timeout=30,
        )

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        try:
            conn = self._connect(config)
            query = config.get("query")
            if not query:
                table = config["table"]
                if not all(c.isalnum() or c in "_." for c in table):
                    raise DataLoadError(f"Invalid table name: {table}")
                query = f"SELECT * FROM {table}"

            logger.info("Executing Snowflake query (%.50s...)", query[:50])
            cursor = conn.cursor()
            cursor.execute(query)
            df = cursor.fetch_pandas_all()
            cursor.close()
            conn.close()

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df
        except ImportError:
            raise DataLoadError(
                "Install snowflake-connector-python: "
                "pip install snowflake-connector-python[pandas]"
            )
        except Exception as e:
            raise DataLoadError(f"Snowflake load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        query = config.get("query")
        if query:
            config = {**config, "query": f"SELECT * FROM ({query}) LIMIT {n_rows}"}
        elif config.get("table"):
            config = {
                **config,
                "query": f"SELECT * FROM {config['table']} LIMIT {n_rows}",
            }
        return self.load(config)

    def get_metadata(self, config: dict) -> dict:
        try:
            conn = self._connect(config)
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return {"tables": [r[1] for r in rows]}
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "account", "type": "text", "label": "Account",
             "required": True,
             "help_text": "e.g., xy12345.us-east-1"},
            {"name": "user", "type": "text", "label": "Username",
             "required": True},
            {"name": "password", "type": "password", "label": "Password",
             "required": True},
            {"name": "warehouse", "type": "text", "label": "Warehouse"},
            {"name": "database", "type": "text", "label": "Database"},
            {"name": "schema", "type": "text", "label": "Schema"},
            {"name": "query", "type": "textarea", "label": "SQL Query"},
            {"name": "table", "type": "text", "label": "Table Name"},
        ]
