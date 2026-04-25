"""Compressed file connector (ZIP, GZ, TAR.GZ).

Extracts archive contents, scans for tabular files, and loads them.
"""

import gzip
import logging
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from core.exceptions import DataLoadError
from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

TABULAR_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl"}


class CompressedConnector(BaseConnector):
    """Connector for compressed/archived files."""

    @property
    def connector_type(self) -> str:
        return "compressed"

    @property
    def display_name(self) -> str:
        return "Compressed Archive (.zip / .gz / .tar.gz)"

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

        fp = Path(config["file_path"])
        target_file = config.get("target_file")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                extracted = self._extract(fp, tmpdir)

                if not extracted:
                    raise DataLoadError(f"No tabular files found in archive: {fp.name}")

                if target_file:
                    matches = [f for f in extracted if Path(f).name == target_file]
                    if not matches:
                        raise DataLoadError(
                            f"Target file '{target_file}' not found. Available: {[Path(f).name for f in extracted]}"
                        )
                    chosen = matches[0]
                else:
                    chosen = extracted[0]
                    if len(extracted) > 1:
                        logger.warning(
                            "Multiple tabular files found, loading first: %s", Path(chosen).name
                        )

                df = self._load_file(chosen)
                logger.info("Loaded %d rows x %d columns from %s", len(df), len(df.columns), Path(chosen).name)
                return df

        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Failed to process archive: {e}") from e

    def _extract(self, fp: Path, tmpdir: str) -> list[str]:
        """Extract archive and return paths to tabular files."""
        suffix = "".join(fp.suffixes).lower()

        if suffix.endswith(".gz") and ".tar" not in suffix:
            # Single gzipped file
            out_path = Path(tmpdir) / fp.stem
            with gzip.open(fp, "rb") as f_in, open(out_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            return [str(out_path)]

        if ".tar" in suffix or suffix in (".tar.gz", ".tgz"):
            with tarfile.open(fp, "r:*") as tar:
                tar.extractall(tmpdir, filter="data")
        elif suffix == ".zip":
            with zipfile.ZipFile(fp, "r") as zf:
                # Validate against Zip Slip: ensure no entry escapes tmpdir
                tmp_resolved = Path(tmpdir).resolve()
                for entry in zf.namelist():
                    target = (tmp_resolved / entry).resolve()
                    if not str(target).startswith(str(tmp_resolved)):
                        raise DataLoadError(
                            f"Zip Slip detected: entry '{entry}' escapes target directory"
                        )
                zf.extractall(tmpdir)
        else:
            raise DataLoadError(f"Unsupported archive format: {suffix}")

        # Scan for tabular files
        tabular = []
        for f in Path(tmpdir).rglob("*"):
            if f.is_file() and f.suffix.lower() in TABULAR_EXTENSIONS:
                tabular.append(str(f))

        return sorted(tabular)

    def _load_file(self, path: str) -> pd.DataFrame:
        """Load a single extracted file."""
        ext = Path(path).suffix.lower()
        if ext in (".csv", ".tsv"):
            sep = "\t" if ext == ".tsv" else ","
            return pd.read_csv(path, sep=sep)
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        if ext == ".parquet":
            return pd.read_parquet(path)
        if ext in (".json", ".jsonl"):
            return pd.read_json(path, lines=ext == ".jsonl")
        raise DataLoadError(f"Cannot load extracted file type: {ext}")

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        df = self.load(config)
        return df.head(n_rows)

    def get_metadata(self, config: dict) -> dict:
        fp = Path(config.get("file_path", ""))
        return {"file_size_mb": round(fp.stat().st_size / 1048576, 2) if fp.exists() else 0}

    def get_config_schema(self) -> list[dict]:
        return [
            {"name": "file_path", "type": "file", "label": "Archive File", "required": True},
            {"name": "target_file", "type": "text", "label": "Target File Name", "default": None,
             "help_text": "Specific file to load from archive (optional)"},
        ]
