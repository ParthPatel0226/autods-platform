"""Abstract base class for all data connectors.

Every connector (CSV, PostgreSQL, REST API, etc.) implements this interface,
ensuring consistent behavior across all data sources.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base connector that all data source connectors must implement."""

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return connector type identifier (e.g., 'csv', 'postgresql', 'rest_api')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """Validate connector configuration before loading.
        
        Args:
            config: Connector-specific configuration dict.
            
        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        ...

    @abstractmethod
    def load(self, config: dict) -> pd.DataFrame:
        """Load data from source into a pandas DataFrame.
        
        Args:
            config: Connector-specific configuration.
            
        Returns:
            Loaded DataFrame.
            
        Raises:
            DataLoadError: If loading fails.
        """
        ...

    @abstractmethod
    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        """Get a preview of the data without loading everything.
        
        Args:
            config: Connector-specific configuration.
            n_rows: Number of preview rows.
            
        Returns:
            Preview DataFrame.
        """
        ...

    def get_metadata(self, config: dict) -> dict:
        """Get metadata about the data source without fully loading it.
        
        Returns:
            Dict with keys like 'row_count', 'column_count', 'size_mb', etc.
        """
        return {}

    def get_config_schema(self) -> list[dict]:
        """Return the configuration schema for UI rendering.
        
        Returns:
            List of field definitions for the Streamlit configuration form.
            Each field has: name, type, label, required, default, help_text.
        """
        return []
