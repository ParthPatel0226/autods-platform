"""Factory for creating the correct data connector based on source type.

Usage:
    connector = ConnectorFactory.get_connector("csv")
    df = connector.load({"file_path": "data.csv"})
"""

import logging
from typing import Type

from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# Registry of all available connectors (lazy-loaded)
_CONNECTOR_REGISTRY: dict[str, str] = {
    # File connectors
    "csv": "data_connectors.file_connectors.csv_connector.CSVConnector",
    "tsv": "data_connectors.file_connectors.csv_connector.CSVConnector",
    "excel": "data_connectors.file_connectors.excel_connector.ExcelConnector",
    "xlsx": "data_connectors.file_connectors.excel_connector.ExcelConnector",
    "xls": "data_connectors.file_connectors.excel_connector.ExcelConnector",
    "parquet": "data_connectors.file_connectors.parquet_connector.ParquetConnector",
    "feather": "data_connectors.file_connectors.parquet_connector.ParquetConnector",
    "json": "data_connectors.file_connectors.json_connector.JSONConnector",
    "jsonl": "data_connectors.file_connectors.json_connector.JSONConnector",
    "xml": "data_connectors.file_connectors.xml_connector.XMLConnector",
    "zip": "data_connectors.file_connectors.compressed_connector.CompressedConnector",
    "gz": "data_connectors.file_connectors.compressed_connector.CompressedConnector",
    "sqlite": "data_connectors.file_connectors.sqlite_connector.SQLiteConnector",
    "db": "data_connectors.file_connectors.sqlite_connector.SQLiteConnector",
    "pdf": "data_connectors.file_connectors.pdf_connector.PDFConnector",
    "sas7bdat": "data_connectors.file_connectors.statistical_connector.StatisticalConnector",
    "dta": "data_connectors.file_connectors.statistical_connector.StatisticalConnector",
    "sav": "data_connectors.file_connectors.statistical_connector.StatisticalConnector",
    "h5": "data_connectors.file_connectors.statistical_connector.StatisticalConnector",
    # Database connectors
    "postgresql": "data_connectors.database_connectors.postgres_connector.PostgresConnector",
    "mysql": "data_connectors.database_connectors.mysql_connector.MySQLConnector",
    "sqlserver": "data_connectors.database_connectors.sqlserver_connector.SQLServerConnector",
    "duckdb": "data_connectors.database_connectors.duckdb_connector.DuckDBConnector",
    "bigquery": "data_connectors.database_connectors.bigquery_connector.BigQueryConnector",
    "snowflake": "data_connectors.database_connectors.snowflake_connector.SnowflakeConnector",
    "redshift": "data_connectors.database_connectors.redshift_connector.RedshiftConnector",
    # API connectors
    "rest_api": "data_connectors.api_connectors.rest_api_connector.RESTAPIConnector",
    "web_scrape": "data_connectors.api_connectors.web_scraper.WebScraperConnector",
    "kaggle": "data_connectors.api_connectors.kaggle_connector.KaggleConnector",
    "huggingface": "data_connectors.api_connectors.huggingface_connector.HuggingFaceConnector",
    "google_sheets": "data_connectors.api_connectors.google_sheets_connector.GoogleSheetsConnector",
    "world_bank": "data_connectors.api_connectors.public_data.world_bank.WorldBankConnector",
    "fred": "data_connectors.api_connectors.public_data.fred.FREDConnector",
    "yahoo_finance": "data_connectors.api_connectors.public_data.yahoo_finance.YahooFinanceConnector",
    "census": "data_connectors.api_connectors.public_data.census.CensusConnector",
    # Cloud connectors
    "s3": "data_connectors.cloud_connectors.s3_connector.S3Connector",
    "gcs": "data_connectors.cloud_connectors.gcs_connector.GCSConnector",
    "azure_blob": "data_connectors.cloud_connectors.azure_blob_connector.AzureBlobConnector",
    # Direct input
    "clipboard": "data_connectors.direct_input.clipboard_parser.ClipboardConnector",
    "manual": "data_connectors.direct_input.manual_entry.ManualEntryConnector",
    "sample": "data_connectors.direct_input.sample_datasets.SampleDatasetConnector",
}


class ConnectorFactory:
    """Factory for creating data connectors."""

    @staticmethod
    def get_connector(connector_type: str) -> BaseConnector:
        """Get a connector instance by type.
        
        Args:
            connector_type: Type identifier (e.g., "csv", "postgresql").
            
        Returns:
            Connector instance.
            
        Raises:
            ValueError: If connector type is not supported.
        """
        class_path = _CONNECTOR_REGISTRY.get(connector_type.lower())
        if not class_path:
            available = ", ".join(sorted(set(_CONNECTOR_REGISTRY.keys())))
            raise ValueError(
                f"Unsupported connector type: '{connector_type}'. "
                f"Available types: {available}"
            )

        # Dynamic import
        module_path, class_name = class_path.rsplit(".", 1)
        try:
            import importlib
            module = importlib.import_module(module_path)
            connector_class = getattr(module, class_name)
            return connector_class()
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to load connector '{connector_type}': {e}. "
                f"You may need to install additional dependencies."
            )

    @staticmethod
    def get_connector_for_file(file_path: str) -> BaseConnector:
        """Auto-detect connector type from file extension.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            Appropriate connector instance.
        """
        from pathlib import Path
        ext = Path(file_path).suffix.lstrip(".").lower()

        # Map extensions to connector types
        ext_map = {
            "csv": "csv", "tsv": "tsv",
            "xlsx": "excel", "xls": "excel",
            "parquet": "parquet", "feather": "feather",
            "json": "json", "jsonl": "jsonl",
            "xml": "xml",
            "zip": "zip", "gz": "gz", "tar": "zip",
            "sqlite": "sqlite", "db": "sqlite",
            "pdf": "pdf",
            "sas7bdat": "sas7bdat", "dta": "dta", "sav": "sav",
            "h5": "h5", "hdf5": "h5",
            "orc": "parquet",
        }

        connector_type = ext_map.get(ext)
        if not connector_type:
            raise ValueError(f"Unsupported file extension: '.{ext}'")

        return ConnectorFactory.get_connector(connector_type)

    @staticmethod
    def list_available_connectors() -> dict[str, list[str]]:
        """List all available connectors grouped by category."""
        categories = {
            "File Upload": ["csv", "excel", "parquet", "json", "xml", "sqlite", "pdf", "zip"],
            "Database": ["postgresql", "mysql", "duckdb", "sqlserver", "bigquery", "snowflake", "redshift"],
            "API / Web": ["rest_api", "web_scrape", "kaggle", "huggingface", "google_sheets"],
            "Cloud Storage": ["s3", "gcs", "azure_blob"],
            "Direct Input": ["clipboard", "manual", "sample"],
        }
        return categories
