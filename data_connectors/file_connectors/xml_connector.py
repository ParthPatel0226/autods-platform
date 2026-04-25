"""XML table extraction connector.

Extracts tabular data from XML files using lxml/ElementTree.
Supports both flat and nested XML structures.
"""

import logging
from pathlib import Path

import pandas as pd
from lxml import etree

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class XMLConnector(BaseConnector):
    """Connector for XML files with tabular data."""

    @property
    def connector_type(self) -> str:
        return "xml"

    @property
    def display_name(self) -> str:
        return "XML File (.xml)"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        fp = config.get("file_path")
        if not fp:
            return False, "file_path is required"
        if not Path(fp).exists():
            return False, f"File not found: {fp}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, err = self.validate_config(config)
        if not valid:
            raise DataLoadError(err)

        fp = config["file_path"]
        xpath = config.get("xpath", None)
        encoding = config.get("encoding", "utf-8")

        try:
            # Pre-parse with hardened lxml parser to prevent XXE attacks,
            # then pass the sanitised tree to pandas via a BytesIO buffer.
            safe_parser = etree.XMLParser(
                resolve_entities=False,
                no_network=True,
                dtd_validation=False,
                load_dtd=False,
            )
            tree = etree.parse(fp, safe_parser)
            from io import BytesIO

            buf = BytesIO(etree.tostring(tree, encoding="utf-8", xml_declaration=True))
            if xpath:
                df = pd.read_xml(buf, xpath=xpath, parser="lxml")
            else:
                df = pd.read_xml(buf, parser="lxml")

            nrows = config.get("nrows")
            if nrows:
                df = df.head(nrows)

            logger.info("Loaded %d rows x %d columns from XML", len(df), len(df.columns))
            return df
        except Exception as e:
            raise DataLoadError(f"Failed to load XML: {e}") from e

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load({**config, "nrows": n_rows})

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "file_path", "type": "file", "label": "XML File", "required": True},
            {"name": "xpath", "type": "text", "label": "XPath Expression", "default": None,
             "help_text": "Optional XPath to select specific elements"},
            {"name": "encoding", "type": "text", "label": "Encoding", "default": "utf-8"},
        ]
