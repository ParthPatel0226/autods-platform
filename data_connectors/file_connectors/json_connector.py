"""JSON connector with support for flat arrays, nested objects, and JSONL.

Handles:
- Standard JSON array of objects: [{"a":1}, {"a":2}]
- Nested JSON with auto-flattening: {"data": [{"a": {"b": 1}}]}
- JSON Lines (JSONL/NDJSON): one JSON object per line
"""
import json
import logging
from pathlib import Path
import pandas as pd
from data_connectors.base import BaseConnector
from core.exceptions import DataLoadError

logger = logging.getLogger(__name__)

class JSONConnector(BaseConnector):
    @property
    def connector_type(self): return "json"
    @property
    def display_name(self): return "JSON / JSONL"

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
        nrows = config.get("nrows")
        try:
            if ext in (".jsonl", ".ndjson"):
                df = pd.read_json(fp, lines=True, nrows=nrows)
            else:
                # Try standard read first
                try:
                    df = pd.read_json(fp)
                except ValueError:
                    # Try nested JSON with normalize
                    with open(fp, "r") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        # Find the first list value (likely the data array)
                        for key, val in data.items():
                            if isinstance(val, list) and len(val) > 0:
                                df = pd.json_normalize(val, max_level=config.get("max_level", 3))
                                break
                        else:
                            df = pd.json_normalize(data)
                    elif isinstance(data, list):
                        df = pd.json_normalize(data, max_level=config.get("max_level", 3))
                    else:
                        raise DataLoadError("JSON structure not recognized as tabular data")
                if nrows: df = df.head(nrows)
            logger.info("Loaded %d rows × %d columns from JSON", len(df), len(df.columns))
            return df
        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Failed to load JSON: {e}")

    def get_preview(self, config, n_rows=5):
        return self.load({**config, "nrows": n_rows})

    def get_config_schema(self):
        return [
            {"name": "file_path", "type": "file", "label": "JSON/JSONL File", "required": True},
            {"name": "max_level", "type": "number", "label": "Max Nesting Depth", "default": 3,
             "help_text": "How many levels deep to flatten nested objects"},
        ]
