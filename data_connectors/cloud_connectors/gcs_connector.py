"""Google Cloud Storage connector."""

import logging
import tempfile
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_MAX_SIZE_MB = 500


class GCSConnector(BaseConnector):
    """Connector for Google Cloud Storage."""

    @property
    def connector_type(self) -> str:
        return "gcs"

    @property
    def display_name(self) -> str:
        return "Google Cloud Storage"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("bucket"):
            return False, "bucket is required"
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
            from google.cloud import storage

            credentials_path = config.get("credentials_json")
            if credentials_path:
                client = storage.Client.from_service_account_json(credentials_path)
            else:
                client = storage.Client()

            bucket = client.bucket(config["bucket"])
            blob = bucket.get_blob(config["blob_name"])
            if blob is None:
                raise DataLoadError(
                    f"Blob '{config['blob_name']}' not found in bucket '{config['bucket']}'"
                )

            size_mb = (blob.size or 0) / (1024 * 1024)
            if size_mb > _MAX_SIZE_MB:
                raise DataLoadError(
                    f"File too large: {size_mb:.1f}MB (max {_MAX_SIZE_MB}MB)"
                )

            logger.info(
                "Downloading gs://%s/%s", config["bucket"], config["blob_name"]
            )

            with tempfile.NamedTemporaryFile(
                suffix=Path(config["blob_name"]).suffix, delete=False
            ) as tmp:
                blob.download_to_filename(tmp.name)
                df = self._read_file(Path(tmp.name))

            Path(tmp.name).unlink(missing_ok=True)
            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError(
                "Install google-cloud-storage: pip install google-cloud-storage"
            )
        except Exception as e:
            raise DataLoadError(f"GCS load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "bucket", "type": "text", "label": "GCS Bucket",
             "required": True},
            {"name": "blob_name", "type": "text", "label": "Blob Path",
             "required": True,
             "help_text": "e.g. data/sales_2024.csv"},
            {"name": "credentials_json", "type": "file",
             "label": "Service Account JSON"},
        ]
