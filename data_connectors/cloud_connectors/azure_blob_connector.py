"""Azure Blob Storage connector."""

import logging
import tempfile
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_MAX_SIZE_MB = 500


class AzureBlobConnector(BaseConnector):
    """Connector for Azure Blob Storage."""

    @property
    def connector_type(self) -> str:
        return "azure_blob"

    @property
    def display_name(self) -> str:
        return "Azure Blob Storage"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("connection_string"):
            return False, "connection_string is required"
        if not config.get("container"):
            return False, "container is required"
        if not config.get("blob_name"):
            return False, "blob_name is required"
        return True, ""

    def _read_file(self, path: Path) -> pd.DataFrame:
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path, low_memory=False)
        elif ext in (".parquet", ".pq"):
            return pd.read_parquet(path)
        elif ext in (".json", ".jsonl"):
            return pd.read_json(path, lines=ext == ".jsonl")
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        return pd.read_csv(path, low_memory=False)

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            from azure.storage.blob import BlobServiceClient

            client = BlobServiceClient.from_connection_string(
                config["connection_string"]
            )
            container = client.get_container_client(config["container"])
            blob_client = container.get_blob_client(config["blob_name"])

            props = blob_client.get_blob_properties()
            size_mb = props.size / (1024 * 1024)
            if size_mb > _MAX_SIZE_MB:
                raise DataLoadError(
                    f"Blob too large: {size_mb:.1f}MB (max {_MAX_SIZE_MB}MB)"
                )

            logger.info(
                "Downloading %s/%s (%.1fMB)",
                config["container"], config["blob_name"], size_mb,
            )

            with tempfile.NamedTemporaryFile(
                suffix=Path(config["blob_name"]).suffix, delete=False
            ) as tmp:
                download = blob_client.download_blob()
                tmp.write(download.readall())
                tmp.flush()
                df = self._read_file(Path(tmp.name))

            Path(tmp.name).unlink(missing_ok=True)
            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError(
                "Install azure-storage-blob: pip install azure-storage-blob"
            )
        except Exception as e:
            raise DataLoadError(f"Azure Blob load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "connection_string", "type": "password",
             "label": "Connection String", "required": True},
            {"name": "container", "type": "text", "label": "Container",
             "required": True},
            {"name": "blob_name", "type": "text", "label": "Blob Name",
             "required": True,
             "help_text": "e.g. data/sales_2024.csv"},
        ]
