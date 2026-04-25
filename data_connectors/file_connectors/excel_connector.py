"""Excel file connector (.xlsx, .xls) with sheet selection.

Handles multi-sheet workbooks, auto-detects data range,
and supports both .xlsx (openpyxl) and .xls (xlrd) formats.
"""
import logging
from pathlib import Path
import pandas as pd
from data_connectors.base import BaseConnector
from core.exceptions import DataLoadError

logger = logging.getLogger(__name__)

class ExcelConnector(BaseConnector):
    @property
    def connector_type(self): return "excel"
    @property
    def display_name(self): return "Excel Workbook (.xlsx / .xls)"

    def validate_config(self, config):
        fp = config.get("file_path")
        if not fp: return False, "file_path is required"
        if not Path(fp).exists(): return False, f"File not found: {fp}"
        return True, ""

    def load(self, config):
        valid, err = self.validate_config(config)
        if not valid: raise DataLoadError(err)
        fp = config["file_path"]
        sheet = config.get("sheet_name", 0)
        header = config.get("header", 0)
        nrows = config.get("nrows")
        try:
            df = pd.read_excel(fp, sheet_name=sheet, header=header, nrows=nrows)
            df.columns = df.columns.astype(str).str.strip()
            df = df.dropna(how="all").dropna(axis=1, how="all")
            logger.info("Loaded %d rows × %d columns from Excel sheet '%s'", len(df), len(df.columns), sheet)
            return df
        except Exception as e:
            raise DataLoadError(f"Failed to load Excel: {e}")

    def get_preview(self, config, n_rows=5):
        return self.load({**config, "nrows": n_rows})

    def get_metadata(self, config):
        fp = config.get("file_path", "")
        try:
            xl = pd.ExcelFile(fp)
            return {"sheets": xl.sheet_names, "file_size_mb": round(Path(fp).stat().st_size / 1048576, 2)}
        except Exception:
            return {}

    def get_config_schema(self):
        return [
            {"name": "file_path", "type": "file", "label": "Excel File", "required": True},
            {"name": "sheet_name", "type": "text", "label": "Sheet Name", "default": "0",
             "help_text": "Sheet name or index (0 for first sheet)"},
            {"name": "header", "type": "number", "label": "Header Row", "default": 0},
        ]
