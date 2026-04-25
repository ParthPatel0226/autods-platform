"""SQLite database file connector.

Loads tables from .db / .sqlite files with table listing and SQL query support.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class SQLiteConnector(BaseConnector):
    """Connector for SQLite database files."""

    @property
    def connector_type(self) -> str:
        return "sqlite"

    @property
    def display_name(self) -> str:
        return "SQLite Database (.db / .sqlite)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        fp = config.get("file_path")
        if not fp:
            return False, "file_path is required"
        if not Path(fp).exists():
            return False, f"File not found: {fp}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, err = self.validate_config(config)
        if not valid:
            raise DataLoadError(err)

        fp = config["file_path"]
        table_name = config.get("table_name")
        query = config.get("query")

        try:
            conn = sqlite3.connect(fp)
            try:
                if query:
                    # Only allow SELECT statements to prevent destructive SQL
                    stripped = query.strip()
                    if not stripped.upper().startswith("SELECT"):
                        raise DataLoadError(
                            "Only SELECT queries are allowed. "
                            "The provided query does not start with SELECT."
                        )
                    df = pd.read_sql_query(query, conn)
                    logger.info("Executed query on SQLite: %d rows x %d cols", len(df), len(df.columns))
                elif table_name:
                    df = pd.read_sql_query(f"SELECT * FROM [{table_name}]", conn)
                    logger.info("Loaded table '%s': %d rows x %d cols", table_name, len(df), len(df.columns))
                else:
                    # Auto-select first table
                    tables = self._list_tables(conn)
                    if not tables:
                        raise DataLoadError("No tables found in SQLite database")
                    table_name = tables[0]
                    df = pd.read_sql_query(f"SELECT * FROM [{table_name}]", conn)
                    logger.info("Auto-loaded first table '%s': %d rows x %d cols", table_name, len(df), len(df.columns))
            finally:
                conn.close()

            nrows = config.get("nrows")
            if nrows:
                df = df.head(nrows)

            return df

        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Failed to load SQLite database: {e}") from e

    def _list_tables(self, conn: sqlite3.Connection) -> list[str]:
        """List all user tables in the database."""
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load({**config, "nrows": n_rows})

    def get_metadata(self, config: dict) -> dict:
        fp = config.get("file_path", "")
        try:
            conn = sqlite3.connect(fp)
            tables = self._list_tables(conn)
            table_info = {}
            for t in tables:
                count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                table_info[t] = {"row_count": count}
            conn.close()
            return {
                "tables": tables,
                "table_info": table_info,
                "file_size_mb": round(Path(fp).stat().st_size / 1048576, 2),
            }
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "file_path", "type": "file", "label": "SQLite File", "required": True},
            {"name": "table_name", "type": "text", "label": "Table Name", "default": None,
             "help_text": "Table to load (auto-selects first if empty)"},
            {"name": "query", "type": "text", "label": "Custom SQL Query", "default": None,
             "help_text": "Optional SQL query (overrides table_name)"},
        ]
