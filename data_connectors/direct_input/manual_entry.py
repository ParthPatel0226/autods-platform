"""Manual data entry connector — build a DataFrame from scratch."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ManualEntryConnector(BaseConnector):
    """Build a DataFrame from manual column/row definitions."""

    @property
    def connector_type(self) -> str:
        return "manual"

    @property
    def display_name(self) -> str:
        return "Manual Data Entry"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        columns = config.get("columns", [])
        rows = config.get("rows", [])
        if not columns:
            return False, "columns list is required"
        if not rows:
            return False, "at least one row is required"
        n_cols = len(columns)
        for i, row in enumerate(rows):
            if len(row) != n_cols:
                return False, (
                    f"Row {i} has {len(row)} values, expected {n_cols}"
                )
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        columns = config["columns"]
        rows = config["rows"]

        # Extract column names (support dict or string format)
        col_names = []
        col_types = {}
        for col in columns:
            if isinstance(col, dict):
                col_names.append(col["name"])
                if col.get("type"):
                    col_types[col["name"]] = col["type"]
            else:
                col_names.append(str(col))

        df = pd.DataFrame(rows, columns=col_names)

        # Apply type hints
        type_map = {
            "int": "int64",
            "float": "float64",
            "str": "object",
            "string": "object",
            "bool": "bool",
            "date": "datetime64[ns]",
            "datetime": "datetime64[ns]",
        }
        for col_name, col_type in col_types.items():
            mapped = type_map.get(col_type, col_type)
            try:
                df[col_name] = df[col_name].astype(mapped)
            except (ValueError, TypeError):
                logger.warning("Could not cast %s to %s", col_name, mapped)

        logger.info(
            "Created manual DataFrame: %d rows x %d columns",
            len(df), len(df.columns),
        )
        return df

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "columns", "type": "json", "label": "Columns",
             "required": True,
             "help_text": 'List of {"name": "col", "type": "str"} dicts'},
            {"name": "rows", "type": "json", "label": "Rows",
             "required": True,
             "help_text": "List of lists, each inner list = one row"},
        ]
