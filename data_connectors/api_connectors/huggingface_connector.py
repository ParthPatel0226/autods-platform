"""HuggingFace Datasets connector via the datasets library."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class HuggingFaceConnector(BaseConnector):
    """Connector for HuggingFace datasets."""

    @property
    def connector_type(self) -> str:
        return "huggingface"

    @property
    def display_name(self) -> str:
        return "HuggingFace Dataset"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("dataset"):
            return False, "dataset name is required (e.g. 'imdb', 'squad')"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        dataset_name = config["dataset"]
        subset = config.get("subset")
        split = config.get("split", "train")

        try:
            from datasets import load_dataset

            logger.info("Loading HuggingFace dataset: %s", dataset_name)
            kwargs = {"path": dataset_name, "split": split}
            if subset:
                kwargs["name"] = subset

            ds = load_dataset(**kwargs)
            df = ds.to_pandas()

            # Limit rows if very large
            max_rows = config.get("max_rows", 100_000)
            if len(df) > max_rows:
                logger.warning(
                    "Dataset has %d rows, sampling %d", len(df), max_rows
                )
                df = df.sample(n=max_rows, random_state=42)

            logger.info(
                "Loaded %d rows x %d columns from %s",
                len(df), len(df.columns), dataset_name,
            )
            return df

        except ImportError:
            raise DataLoadError("Install datasets: pip install datasets")
        except Exception as e:
            raise DataLoadError(f"HuggingFace load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        preview_config = {**config, "max_rows": n_rows * 10}
        return self.load(preview_config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "dataset", "type": "text", "label": "Dataset Name",
             "required": True,
             "help_text": "HuggingFace dataset ID (e.g. 'imdb')"},
            {"name": "subset", "type": "text", "label": "Subset/Config",
             "help_text": "Dataset configuration name (if applicable)"},
            {"name": "split", "type": "select", "label": "Split",
             "options": ["train", "test", "validation"],
             "default": "train"},
            {"name": "max_rows", "type": "number", "label": "Max Rows",
             "default": 100000},
        ]
