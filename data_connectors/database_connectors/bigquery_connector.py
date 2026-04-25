"""Google BigQuery connector via google-cloud-bigquery."""

import logging

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class BigQueryConnector(BaseConnector):
    """Connector for Google BigQuery."""

    @property
    def connector_type(self) -> str:
        return "bigquery"

    @property
    def display_name(self) -> str:
        return "Google BigQuery"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("project"):
            return False, "project is required"
        if not config.get("query") and not config.get("table"):
            return False, "query or table is required"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        try:
            from google.cloud import bigquery

            credentials_path = config.get("credentials_json")
            if credentials_path:
                client = bigquery.Client.from_service_account_json(
                    credentials_path, project=config["project"]
                )
            else:
                client = bigquery.Client(project=config["project"])

            query = config.get("query")
            if not query:
                table = config["table"]
                query = f"SELECT * FROM `{table}`"

            logger.info("Executing BigQuery (%.50s...)", query[:50])
            job_config = bigquery.QueryJobConfig(
                maximum_bytes_billed=config.get("max_bytes", 10 * 1024**3)
            )
            df = client.query(query, job_config=job_config).to_dataframe()

            logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))
            return df
        except ImportError:
            raise DataLoadError(
                "Install google-cloud-bigquery: "
                "pip install google-cloud-bigquery db-dtypes"
            )
        except Exception as e:
            raise DataLoadError(f"BigQuery load failed: {e}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        query = config.get("query")
        if query:
            config = {**config, "query": f"SELECT * FROM ({query}) LIMIT {n_rows}"}
        elif config.get("table"):
            config = {
                **config,
                "query": f"SELECT * FROM `{config['table']}` LIMIT {n_rows}",
            }
        return self.load(config)

    def get_metadata(self, config: dict) -> dict:
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=config["project"])
            dataset = config.get("dataset", "")
            if dataset:
                tables = list(client.list_tables(dataset))
                return {"tables": [t.table_id for t in tables]}
            return {}
        except Exception:
            return {}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "project", "type": "text", "label": "GCP Project ID",
             "required": True},
            {"name": "credentials_json", "type": "file",
             "label": "Service Account JSON",
             "help_text": "Path to service account key file"},
            {"name": "dataset", "type": "text", "label": "Dataset"},
            {"name": "table", "type": "text", "label": "Table",
             "help_text": "project.dataset.table format"},
            {"name": "query", "type": "textarea", "label": "SQL Query"},
            {"name": "max_bytes", "type": "number",
             "label": "Max Bytes Billed", "default": 10737418240},
        ]
