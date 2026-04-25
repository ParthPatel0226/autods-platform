"""Parquet / Feather / ORC connector.

Handles columnar file formats with efficient loading.
Supports Parquet, Feather (Arrow IPC), and ORC formats.
"""
import logging
from pathlib import Path
import pandas as pd
from data_connectors.base import BaseConnector
from core.exceptions import DataLoadError

logger = logging.getLogger(__name__)

class ParquetConnector(BaseConnector):
    @property
    def connector_type(self): return "parquet"
    @property
    def display_name(self): return "Parquet / Feather / ORC"

    def validate_config(self, config):
        fp = config.get("file_path")
        if not fp: return False, "file_path is required"
        if not Path(fp).exists(): return False, f"File not found: {fp}"
        return True, ""

    def load(self, config):
        valid, err = self.validate_config(config)
        if not valid: raise DataLoadError(err)
        fp = config["file_path"]
        ext = Path(fp).suffix.lower()
        columns = config.get("columns")  # Optional column subset
        try:
            if ext in (".parquet", ".pq"):
                df = pd.read_parquet(fp, columns=columns)
            elif ext in (".feather", ".arrow", ".ipc"):
                df = pd.read_feather(fp, columns=columns)
            elif ext == ".orc":
                df = pd.read_orc(fp, columns=columns)
            else:
                df = pd.read_parquet(fp, columns=columns)  # Default to parquet
            nrows = config.get("nrows")
            if nrows: df = df.head(nrows)
            logger.info("Loaded %d rows × %d columns from %s", len(df), len(df.columns), ext)
            return df
        except Exception as e:
            raise DataLoadError(f"Failed to load {ext} file: {e}")

    def get_preview(self, config, n_rows=5):
        return self.load({**config, "nrows": n_rows})

    def get_config_schema(self):
        return [
            {"name": "file_path", "type": "file", "label": "Parquet/Feather/ORC File", "required": True},
            {"name": "columns", "type": "multi_text", "label": "Select Columns", "default": None,
             "help_text": "Leave empty to load all columns"},
        ]
