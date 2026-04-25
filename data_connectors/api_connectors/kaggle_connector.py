"""Kaggle dataset connector via the Kaggle API."""

import logging
import tempfile
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class KaggleConnector(BaseConnector):
    """Connector for Kaggle datasets."""

    @property
    def connector_type(self) -> str:
        return "kaggle"

    @property
    def display_name(self) -> str:
        return "Kaggle Dataset"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        dataset = config.get("dataset", "")
        if not dataset or "/" not in dataset:
            return False, "dataset required in 'owner/dataset-name' format"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        dataset = config["dataset"]
        file_name = config.get("file_name")

        try:
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()

            with tempfile.TemporaryDirectory() as tmpdir:
                logger.info("Downloading Kaggle dataset: %s", dataset)
                api.dataset_download_files(dataset, path=tmpdir, unzip=True)

                csv_files = list(Path(tmpdir).rglob("*.csv"))
                if not csv_files:
                    raise DataLoadError(f"No CSV files in dataset {dataset}")

                if file_name:
                    target = [f for f in csv_files if f.name == file_name]
                    if not target:
                        available = [f.name for f in csv_files]
                        raise DataLoadError(
                            f"File '{file_name}' not found. "
                            f"Available: {available}"
                        )
                    chosen = target[0]
                else:
                    chosen = max(csv_files, key=lambda f: f.stat().st_size)

                df = pd.read_csv(chosen, low_memory=False)
                logger.info(
                    "Loaded %s: %d rows x %d columns",
                    chosen.name, len(df), len(df.columns),
                )
                return df

        except ImportError:
            raise DataLoadError(
                "Install kaggle: pip install kaggle\n"
                "Set up ~/.kaggle/kaggle.json with your API token"
            )
        except Exception as e:
            raise DataLoadError(f"Kaggle load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "dataset", "type": "text", "label": "Dataset",
             "required": True,
             "help_text": "Format: owner/dataset-name (e.g. zillow/zecon)"},
            {"name": "file_name", "type": "text", "label": "File Name",
             "help_text": "Specific CSV file (largest used if empty)"},
        ]
