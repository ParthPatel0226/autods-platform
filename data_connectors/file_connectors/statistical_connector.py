"""Statistical file format connector.

Loads SAS (.sas7bdat), Stata (.dta), SPSS (.sav), and HDF5 (.h5) files.
Uses pyreadstat for SAS/Stata/SPSS and pandas for HDF5.
"""

import logging
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class StatisticalConnector(BaseConnector):
    """Connector for statistical software file formats."""

    @property
    def connector_type(self) -> str:
        return "statistical"

    @property
    def display_name(self) -> str:
        return "Statistical Format (SAS / Stata / SPSS / HDF5)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        fp = config.get("file_path")
        if not fp:
            return False, "file_path is required"
        if not Path(fp).exists():
            return False, f"File not found: {fp}"
        ext = Path(fp).suffix.lower()
        supported = {".sas7bdat", ".dta", ".sav", ".zsav", ".h5", ".hdf5"}
        if ext not in supported:
            return False, f"Unsupported format: {ext}. Supported: {supported}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, err = self.validate_config(config)
        if not valid:
            raise DataLoadError(err)

        fp = config["file_path"]
        ext = Path(fp).suffix.lower()

        try:
            if ext == ".sas7bdat":
                import pyreadstat
                df, meta = pyreadstat.read_sas7bdat(fp)
                logger.info("Loaded SAS file: %d rows x %d cols", len(df), len(df.columns))

            elif ext == ".dta":
                df = pd.read_stata(fp)
                logger.info("Loaded Stata file: %d rows x %d cols", len(df), len(df.columns))

            elif ext in (".sav", ".zsav"):
                import pyreadstat
                df, meta = pyreadstat.read_sav(fp)
                logger.info("Loaded SPSS file: %d rows x %d cols", len(df), len(df.columns))

            elif ext in (".h5", ".hdf5"):
                key = config.get("hdf_key", None)
                if key:
                    df = pd.read_hdf(fp, key=key)
                else:
                    df = pd.read_hdf(fp)
                logger.info("Loaded HDF5 file: %d rows x %d cols", len(df), len(df.columns))

            else:
                raise DataLoadError(f"Unsupported extension: {ext}")

            nrows = config.get("nrows")
            if nrows:
                df = df.head(nrows)

            return df

        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Failed to load {ext} file: {e}") from e

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load({**config, "nrows": n_rows})

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "file_path", "type": "file", "label": "Statistical File", "required": True,
             "help_text": "SAS (.sas7bdat), Stata (.dta), SPSS (.sav), or HDF5 (.h5)"},
            {"name": "hdf_key", "type": "text", "label": "HDF5 Key", "default": None,
             "help_text": "Dataset key for HDF5 files (optional)"},
        ]
