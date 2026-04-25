"""AWS S3 connector via boto3."""

import logging
import tempfile
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_MAX_SIZE_MB = 500


class S3Connector(BaseConnector):
    """Connector for AWS S3 objects."""

    @property
    def connector_type(self) -> str:
        return "s3"

    @property
    def display_name(self) -> str:
        return "AWS S3"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("bucket"):
            return False, "bucket is required"
        if not config.get("key"):
            return False, "key (object path) is required"
        return True, ""

    def _get_client(self, config: dict):
        import boto3

        kwargs = {}
        if config.get("aws_access_key_id"):
            kwargs["aws_access_key_id"] = config["aws_access_key_id"]
            kwargs["aws_secret_access_key"] = config.get("aws_secret_access_key", "")
        if config.get("region"):
            kwargs["region_name"] = config["region"]
        return boto3.client("s3", **kwargs)

    def _read_file(self, path: Path) -> pd.DataFrame:
        """Read file based on extension."""
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path, low_memory=False)
        elif ext in (".parquet", ".pq"):
            return pd.read_parquet(path)
        elif ext in (".json", ".jsonl"):
            return pd.read_json(path, lines=ext == ".jsonl")
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        else:
            return pd.read_csv(path, low_memory=False)

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)

        try:
            s3 = self._get_client(config)
            bucket = config["bucket"]
            key = config["key"]

            # Check size
            head = s3.head_object(Bucket=bucket, Key=key)
            size_mb = head["ContentLength"] / (1024 * 1024)
            if size_mb > _MAX_SIZE_MB:
                raise DataLoadError(
                    f"File too large: {size_mb:.1f}MB (max {_MAX_SIZE_MB}MB)"
                )

            logger.info("Downloading s3://%s/%s (%.1fMB)", bucket, key, size_mb)

            with tempfile.NamedTemporaryFile(
                suffix=Path(key).suffix, delete=False
            ) as tmp:
                s3.download_file(bucket, key, tmp.name)
                df = self._read_file(Path(tmp.name))

            Path(tmp.name).unlink(missing_ok=True)
            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df

        except ImportError:
            raise DataLoadError("Install boto3: pip install boto3")
        except Exception as e:
            raise DataLoadError(f"S3 load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load(config).head(n_rows)

    def get_metadata(self, config: dict) -> dict:
        try:
            s3 = self._get_client(config)
            head = s3.head_object(Bucket=config["bucket"], Key=config["key"])
            return {
                "size_mb": round(head["ContentLength"] / (1024 * 1024), 2),
                "content_type": head.get("ContentType", ""),
                "last_modified": str(head.get("LastModified", "")),
            }
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "bucket", "type": "text", "label": "S3 Bucket",
             "required": True},
            {"name": "key", "type": "text", "label": "Object Key (path)",
             "required": True,
             "help_text": "e.g. data/sales_2024.csv"},
            {"name": "aws_access_key_id", "type": "text",
             "label": "Access Key ID",
             "help_text": "Leave empty for default credentials"},
            {"name": "aws_secret_access_key", "type": "password",
             "label": "Secret Access Key"},
            {"name": "region", "type": "text", "label": "Region",
             "default": "us-east-1"},
        ]
