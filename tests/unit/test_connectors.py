"""Unit tests for all file connectors in data_connectors/file_connectors/.

Coverage:
    - CSVConnector
    - JSONConnector
    - ExcelConnector
    - ParquetConnector
    - XMLConnector
    - SQLiteConnector
    - CompressedConnector
    - StatisticalConnector
    - PDFConnector

Each connector is tested for:
    - connector_type property returns expected string
    - validate_config rejects missing file_path
    - validate_config rejects nonexistent file path
    - get_config_schema returns a non-empty list of dicts with required keys
    - load() round-trips representative data (where creatable without special tooling)

PDFConnector and StatisticalConnector load() tests are skipped — they require
Java (tabula) or proprietary binary formats (pyreadstat).
"""

import gzip
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from core.exceptions import DataLoadError
from data_connectors.file_connectors.compressed_connector import CompressedConnector
from data_connectors.file_connectors.csv_connector import CSVConnector
from data_connectors.file_connectors.excel_connector import ExcelConnector
from data_connectors.file_connectors.json_connector import JSONConnector
from data_connectors.file_connectors.parquet_connector import ParquetConnector
from data_connectors.file_connectors.pdf_connector import PDFConnector
from data_connectors.file_connectors.sqlite_connector import SQLiteConnector
from data_connectors.file_connectors.statistical_connector import StatisticalConnector
from data_connectors.file_connectors.xml_connector import XMLConnector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA_REQUIRED_KEYS = {"name", "type", "label"}


def _assert_schema(schema: list) -> None:
    """Assert get_config_schema() returns a valid non-empty list of field dicts."""
    assert isinstance(schema, list), "get_config_schema must return a list"
    assert len(schema) > 0, "get_config_schema must return at least one field"
    for field in schema:
        assert isinstance(field, dict), "Each schema entry must be a dict"
        for key in _SCHEMA_REQUIRED_KEYS:
            assert key in field, f"Schema field missing required key '{key}': {field}"


def _assert_dataframe(df: pd.DataFrame, min_rows: int = 1, min_cols: int = 1) -> None:
    """Assert the returned object is a DataFrame with at least the given dimensions."""
    assert isinstance(df, pd.DataFrame), "load() must return a pandas DataFrame"
    assert len(df) >= min_rows, f"Expected at least {min_rows} row(s), got {len(df)}"
    assert len(df.columns) >= min_cols, f"Expected at least {min_cols} column(s), got {len(df.columns)}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def _sample_df() -> pd.DataFrame:
    """Minimal 3-row DataFrame used to build temp files."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Carol"],
        "score": [88.5, 92.0, 76.3],
    })


@pytest.fixture
def tmp_csv(tmp_path, _sample_df):
    """Write sample data to a CSV file and return path string."""
    path = tmp_path / "sample.csv"
    _sample_df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def tmp_json(tmp_path, _sample_df):
    """Write sample data to a JSON file (array of records) and return path string."""
    path = tmp_path / "sample.json"
    _sample_df.to_json(path, orient="records", indent=2)
    return str(path)


@pytest.fixture
def tmp_jsonl(tmp_path, _sample_df):
    """Write sample data to a JSONL file and return path string."""
    path = tmp_path / "sample.jsonl"
    _sample_df.to_json(path, orient="records", lines=True)
    return str(path)


@pytest.fixture
def tmp_excel(tmp_path, _sample_df):
    """Write sample data to an xlsx file and return path string."""
    path = tmp_path / "sample.xlsx"
    _sample_df.to_excel(path, index=False)
    return str(path)


@pytest.fixture
def tmp_parquet(tmp_path, _sample_df):
    """Write sample data to a Parquet file and return path string."""
    path = tmp_path / "sample.parquet"
    _sample_df.to_parquet(path, index=False)
    return str(path)


@pytest.fixture
def tmp_xml(tmp_path):
    """Write a minimal XML file with tabular records and return path string."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <row>
    <id>1</id>
    <name>Alice</name>
    <score>88.5</score>
  </row>
  <row>
    <id>2</id>
    <name>Bob</name>
    <score>92.0</score>
  </row>
  <row>
    <id>3</id>
    <name>Carol</name>
    <score>76.3</score>
  </row>
</root>
"""
    path = tmp_path / "sample.xml"
    path.write_text(xml_content, encoding="utf-8")
    return str(path)


@pytest.fixture
def tmp_sqlite(tmp_path, _sample_df):
    """Create a SQLite .db file with one table and return path string."""
    path = tmp_path / "sample.db"
    conn = sqlite3.connect(str(path))
    _sample_df.to_sql("records", conn, index=False, if_exists="replace")
    conn.close()
    return str(path)


@pytest.fixture
def tmp_zip_with_csv(tmp_path, _sample_df):
    """Create a ZIP archive containing a CSV and return path string."""
    csv_bytes = _sample_df.to_csv(index=False).encode("utf-8")
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.csv", csv_bytes)
    return str(zip_path)


@pytest.fixture
def tmp_gz_csv(tmp_path, _sample_df):
    """Create a gzip-compressed CSV and return path string."""
    csv_bytes = _sample_df.to_csv(index=False).encode("utf-8")
    gz_path = tmp_path / "data.csv.gz"
    with gzip.open(str(gz_path), "wb") as f:
        f.write(csv_bytes)
    return str(gz_path)


@pytest.fixture
def tmp_fake_pdf(tmp_path):
    """Create a file named sample.pdf (not real PDF, for validate_config tests)."""
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return str(path)


@pytest.fixture
def tmp_fake_sas(tmp_path):
    """Create a file with .sas7bdat extension for validate_config tests."""
    path = tmp_path / "sample.sas7bdat"
    path.write_bytes(b"fake sas content")
    return str(path)


# ===========================================================================
# CSVConnector
# ===========================================================================

class TestCSVConnector:
    """Tests for CSVConnector."""

    def setup_method(self):
        self.connector = CSVConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "csv"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)
        assert len(self.connector.display_name) > 0

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, msg = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.csv")}
        )
        assert valid is False
        assert len(msg) > 0

    def test_validate_config_accepts_existing_file(self, tmp_csv):
        valid, msg = self.connector.validate_config({"file_path": tmp_csv})
        assert valid is True
        assert msg == ""

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    def test_get_config_schema_has_file_path_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "file_path" in names

    # -- load ----------------------------------------------------------------

    def test_load_returns_dataframe(self, tmp_csv):
        df = self.connector.load({"file_path": tmp_csv})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_correct_row_count(self, tmp_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_csv})
        assert len(df) == len(_sample_df)

    def test_load_correct_columns(self, tmp_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_csv})
        assert list(df.columns) == list(_sample_df.columns)

    def test_load_values_match(self, tmp_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_csv})
        assert list(df["id"]) == list(_sample_df["id"])
        assert list(df["name"]) == list(_sample_df["name"])

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    def test_load_raises_data_load_error_on_nonexistent_file(self, tmp_path):
        with pytest.raises(DataLoadError):
            self.connector.load({"file_path": str(tmp_path / "ghost.csv")})

    def test_load_nrows_limits_output(self, tmp_csv):
        df = self.connector.load({"file_path": tmp_csv, "nrows": 2})
        assert len(df) == 2

    def test_load_semicolon_delimiter(self, tmp_path, _sample_df):
        path = tmp_path / "semi.csv"
        _sample_df.to_csv(path, index=False, sep=";")
        df = self.connector.load({"file_path": str(path), "delimiter": ";"})
        assert list(df.columns) == list(_sample_df.columns)

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_returns_at_most_n_rows(self, tmp_csv):
        preview = self.connector.get_preview({"file_path": tmp_csv}, n_rows=2)
        assert len(preview) <= 2

    # -- get_metadata --------------------------------------------------------

    def test_get_metadata_returns_dict(self, tmp_csv):
        meta = self.connector.get_metadata({"file_path": tmp_csv})
        assert isinstance(meta, dict)

    def test_get_metadata_has_file_name(self, tmp_csv):
        meta = self.connector.get_metadata({"file_path": tmp_csv})
        assert "file_name" in meta


# ===========================================================================
# JSONConnector
# ===========================================================================

class TestJSONConnector:
    """Tests for JSONConnector."""

    def setup_method(self):
        self.connector = JSONConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "json"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, msg = self.connector.validate_config(
            {"file_path": str(tmp_path / "missing.json")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_file(self, tmp_json):
        valid, _ = self.connector.validate_config({"file_path": tmp_json})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load (JSON array of records) ----------------------------------------

    def test_load_json_returns_dataframe(self, tmp_json):
        df = self.connector.load({"file_path": tmp_json})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_json_correct_row_count(self, tmp_json, _sample_df):
        df = self.connector.load({"file_path": tmp_json})
        assert len(df) == len(_sample_df)

    def test_load_json_correct_columns(self, tmp_json, _sample_df):
        df = self.connector.load({"file_path": tmp_json})
        for col in _sample_df.columns:
            assert col in df.columns

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    # -- load (JSONL) --------------------------------------------------------

    def test_load_jsonl_returns_dataframe(self, tmp_jsonl):
        df = self.connector.load({"file_path": tmp_jsonl})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_jsonl_correct_row_count(self, tmp_jsonl, _sample_df):
        df = self.connector.load({"file_path": tmp_jsonl})
        assert len(df) == len(_sample_df)

    def test_load_jsonl_nrows(self, tmp_jsonl):
        df = self.connector.load({"file_path": tmp_jsonl, "nrows": 1})
        assert len(df) == 1

    # -- load (nested JSON) --------------------------------------------------

    def test_load_nested_json_with_wrapper_key(self, tmp_path):
        """Connector must find the list under a wrapper key and flatten it."""
        payload = {
            "meta": {"source": "test"},
            "data": [
                {"a": 1, "b": "x"},
                {"a": 2, "b": "y"},
            ],
        }
        path = tmp_path / "nested.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        df = self.connector.load({"file_path": str(path)})
        _assert_dataframe(df, min_rows=2, min_cols=2)

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_json):
        preview = self.connector.get_preview({"file_path": tmp_json}, n_rows=2)
        assert len(preview) <= 2


# ===========================================================================
# ExcelConnector
# ===========================================================================

class TestExcelConnector:
    """Tests for ExcelConnector."""

    def setup_method(self):
        self.connector = ExcelConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "excel"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, msg = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.xlsx")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_file(self, tmp_excel):
        valid, _ = self.connector.validate_config({"file_path": tmp_excel})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load ----------------------------------------------------------------

    def test_load_returns_dataframe(self, tmp_excel):
        df = self.connector.load({"file_path": tmp_excel})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_correct_row_count(self, tmp_excel, _sample_df):
        df = self.connector.load({"file_path": tmp_excel})
        assert len(df) == len(_sample_df)

    def test_load_correct_columns(self, tmp_excel, _sample_df):
        df = self.connector.load({"file_path": tmp_excel})
        for col in _sample_df.columns:
            assert col in df.columns

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    def test_load_nrows_limits_output(self, tmp_excel):
        df = self.connector.load({"file_path": tmp_excel, "nrows": 1})
        assert len(df) == 1

    def test_load_named_sheet(self, tmp_path, _sample_df):
        path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(str(path), engine="openpyxl") as writer:
            _sample_df.to_excel(writer, sheet_name="Sheet1", index=False)
            _sample_df.assign(id=[10, 11, 12]).to_excel(
                writer, sheet_name="Sheet2", index=False
            )
        df = self.connector.load({"file_path": str(path), "sheet_name": "Sheet2"})
        assert list(df["id"]) == [10, 11, 12]

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_excel):
        preview = self.connector.get_preview({"file_path": tmp_excel}, n_rows=2)
        assert len(preview) <= 2

    # -- get_metadata --------------------------------------------------------

    def test_get_metadata_returns_dict(self, tmp_excel):
        meta = self.connector.get_metadata({"file_path": tmp_excel})
        assert isinstance(meta, dict)

    def test_get_metadata_has_sheets_key(self, tmp_excel):
        meta = self.connector.get_metadata({"file_path": tmp_excel})
        assert "sheets" in meta
        assert isinstance(meta["sheets"], list)


# ===========================================================================
# ParquetConnector
# ===========================================================================

class TestParquetConnector:
    """Tests for ParquetConnector."""

    def setup_method(self):
        self.connector = ParquetConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "parquet"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.parquet")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_file(self, tmp_parquet):
        valid, _ = self.connector.validate_config({"file_path": tmp_parquet})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load ----------------------------------------------------------------

    def test_load_returns_dataframe(self, tmp_parquet):
        df = self.connector.load({"file_path": tmp_parquet})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_correct_row_count(self, tmp_parquet, _sample_df):
        df = self.connector.load({"file_path": tmp_parquet})
        assert len(df) == len(_sample_df)

    def test_load_correct_columns(self, tmp_parquet, _sample_df):
        df = self.connector.load({"file_path": tmp_parquet})
        for col in _sample_df.columns:
            assert col in df.columns

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    def test_load_nrows_limits_output(self, tmp_parquet):
        df = self.connector.load({"file_path": tmp_parquet, "nrows": 2})
        assert len(df) == 2

    def test_load_column_subset(self, tmp_parquet):
        df = self.connector.load({"file_path": tmp_parquet, "columns": ["id"]})
        assert list(df.columns) == ["id"]

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_parquet):
        preview = self.connector.get_preview({"file_path": tmp_parquet}, n_rows=2)
        assert len(preview) <= 2


# ===========================================================================
# XMLConnector
# ===========================================================================

class TestXMLConnector:
    """Tests for XMLConnector."""

    def setup_method(self):
        self.connector = XMLConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "xml"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.xml")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_file(self, tmp_xml):
        valid, _ = self.connector.validate_config({"file_path": tmp_xml})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load ----------------------------------------------------------------

    def test_load_returns_dataframe(self, tmp_xml):
        df = self.connector.load({"file_path": tmp_xml})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_correct_row_count(self, tmp_xml):
        df = self.connector.load({"file_path": tmp_xml})
        assert len(df) == 3

    def test_load_expected_columns_present(self, tmp_xml):
        df = self.connector.load({"file_path": tmp_xml})
        for col in ("id", "name", "score"):
            assert col in df.columns

    def test_load_correct_values(self, tmp_xml):
        df = self.connector.load({"file_path": tmp_xml})
        assert list(df["name"]) == ["Alice", "Bob", "Carol"]

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    def test_load_raises_data_load_error_on_malformed_xml(self, tmp_path):
        bad = tmp_path / "bad.xml"
        bad.write_text("<unclosed>", encoding="utf-8")
        with pytest.raises(DataLoadError):
            self.connector.load({"file_path": str(bad)})

    def test_load_nrows_limits_output(self, tmp_xml):
        df = self.connector.load({"file_path": tmp_xml, "nrows": 2})
        assert len(df) == 2

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_xml):
        preview = self.connector.get_preview({"file_path": tmp_xml}, n_rows=2)
        assert len(preview) <= 2


# ===========================================================================
# SQLiteConnector
# ===========================================================================

class TestSQLiteConnector:
    """Tests for SQLiteConnector."""

    def setup_method(self):
        self.connector = SQLiteConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "sqlite"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.db")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_file(self, tmp_sqlite):
        valid, _ = self.connector.validate_config({"file_path": tmp_sqlite})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load (auto-select first table) -------------------------------------

    def test_load_auto_selects_first_table(self, tmp_sqlite):
        df = self.connector.load({"file_path": tmp_sqlite})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_correct_row_count(self, tmp_sqlite, _sample_df):
        df = self.connector.load({"file_path": tmp_sqlite})
        assert len(df) == len(_sample_df)

    def test_load_correct_columns(self, tmp_sqlite, _sample_df):
        df = self.connector.load({"file_path": tmp_sqlite})
        for col in _sample_df.columns:
            assert col in df.columns

    def test_load_correct_values(self, tmp_sqlite, _sample_df):
        df = self.connector.load({"file_path": tmp_sqlite})
        assert sorted(df["name"].tolist()) == sorted(_sample_df["name"].tolist())

    # -- load (explicit table_name) ------------------------------------------

    def test_load_with_explicit_table_name(self, tmp_sqlite):
        df = self.connector.load({"file_path": tmp_sqlite, "table_name": "records"})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    # -- load (custom query) -------------------------------------------------

    def test_load_with_custom_query(self, tmp_sqlite):
        df = self.connector.load({
            "file_path": tmp_sqlite,
            "query": "SELECT id, name FROM records WHERE id > 1",
        })
        assert len(df) == 2
        assert set(df.columns) == {"id", "name"}

    def test_load_nrows_limits_output(self, tmp_sqlite):
        df = self.connector.load({"file_path": tmp_sqlite, "nrows": 1})
        assert len(df) == 1

    # -- load (empty database raises DataLoadError) --------------------------

    def test_load_raises_on_empty_database(self, tmp_path):
        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        conn.close()
        with pytest.raises(DataLoadError):
            self.connector.load({"file_path": str(empty_db)})

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    # -- multiple tables -----------------------------------------------------

    def test_load_second_table_by_name(self, tmp_path, _sample_df):
        db_path = tmp_path / "multi.db"
        conn = sqlite3.connect(str(db_path))
        _sample_df.to_sql("table_a", conn, index=False, if_exists="replace")
        _sample_df.assign(id=[10, 11, 12]).to_sql(
            "table_b", conn, index=False, if_exists="replace"
        )
        conn.close()
        df = self.connector.load({"file_path": str(db_path), "table_name": "table_b"})
        assert list(df["id"]) == [10, 11, 12]

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_sqlite):
        preview = self.connector.get_preview({"file_path": tmp_sqlite}, n_rows=2)
        assert len(preview) <= 2

    # -- get_metadata --------------------------------------------------------

    def test_get_metadata_returns_dict(self, tmp_sqlite):
        meta = self.connector.get_metadata({"file_path": tmp_sqlite})
        assert isinstance(meta, dict)

    def test_get_metadata_has_tables_key(self, tmp_sqlite):
        meta = self.connector.get_metadata({"file_path": tmp_sqlite})
        assert "tables" in meta
        assert "records" in meta["tables"]

    def test_get_metadata_row_count_matches(self, tmp_sqlite, _sample_df):
        meta = self.connector.get_metadata({"file_path": tmp_sqlite})
        assert meta["table_info"]["records"]["row_count"] == len(_sample_df)


# ===========================================================================
# CompressedConnector
# ===========================================================================

class TestCompressedConnector:
    """Tests for CompressedConnector (ZIP and GZ archives)."""

    def setup_method(self):
        self.connector = CompressedConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "compressed"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.zip")}
        )
        assert valid is False

    def test_validate_config_accepts_existing_zip(self, tmp_zip_with_csv):
        valid, _ = self.connector.validate_config({"file_path": tmp_zip_with_csv})
        assert valid is True

    def test_validate_config_accepts_existing_gz(self, tmp_gz_csv):
        valid, _ = self.connector.validate_config({"file_path": tmp_gz_csv})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    # -- load (ZIP containing CSV) -------------------------------------------

    def test_load_zip_returns_dataframe(self, tmp_zip_with_csv):
        df = self.connector.load({"file_path": tmp_zip_with_csv})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_zip_correct_row_count(self, tmp_zip_with_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_zip_with_csv})
        assert len(df) == len(_sample_df)

    def test_load_zip_correct_columns(self, tmp_zip_with_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_zip_with_csv})
        for col in _sample_df.columns:
            assert col in df.columns

    def test_load_zip_with_target_file(self, tmp_zip_with_csv):
        df = self.connector.load(
            {"file_path": tmp_zip_with_csv, "target_file": "data.csv"}
        )
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_zip_raises_on_missing_target_file(self, tmp_zip_with_csv):
        with pytest.raises(DataLoadError):
            self.connector.load(
                {"file_path": tmp_zip_with_csv, "target_file": "nonexistent.csv"}
            )

    # -- load (GZ compressed CSV) --------------------------------------------

    def test_load_gz_returns_dataframe(self, tmp_gz_csv):
        df = self.connector.load({"file_path": tmp_gz_csv})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_gz_correct_row_count(self, tmp_gz_csv, _sample_df):
        df = self.connector.load({"file_path": tmp_gz_csv})
        assert len(df) == len(_sample_df)

    # -- load (ZIP with no tabular files) ------------------------------------

    def test_load_zip_with_no_tabular_files_raises(self, tmp_path):
        zip_path = tmp_path / "no_tables.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("readme.txt", "no tabular data here")
        with pytest.raises(DataLoadError):
            self.connector.load({"file_path": str(zip_path)})

    # -- load (multiple CSV in ZIP — picks first) ----------------------------

    def test_load_zip_multiple_files_picks_first(self, tmp_path, _sample_df):
        csv_a = _sample_df.to_csv(index=False).encode("utf-8")
        csv_b = _sample_df.assign(id=[10, 11, 12]).to_csv(index=False).encode("utf-8")
        zip_path = tmp_path / "multi.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("a.csv", csv_a)
            zf.writestr("b.csv", csv_b)
        # Should not raise; loads first alphabetically
        df = self.connector.load({"file_path": str(zip_path)})
        _assert_dataframe(df, min_rows=1, min_cols=1)

    def test_load_raises_data_load_error_on_missing_path(self):
        with pytest.raises(DataLoadError):
            self.connector.load({})

    # -- get_preview ---------------------------------------------------------

    def test_get_preview_limited_rows(self, tmp_zip_with_csv):
        preview = self.connector.get_preview(
            {"file_path": tmp_zip_with_csv}, n_rows=2
        )
        assert len(preview) <= 2

    # -- get_metadata --------------------------------------------------------

    def test_get_metadata_returns_dict(self, tmp_zip_with_csv):
        meta = self.connector.get_metadata({"file_path": tmp_zip_with_csv})
        assert isinstance(meta, dict)


# ===========================================================================
# StatisticalConnector
# ===========================================================================

class TestStatisticalConnector:
    """Tests for StatisticalConnector.

    load() is not tested here because SAS/SPSS/Stata files require either
    pyreadstat or binary-format sample files that are not generated at test time.
    validate_config and schema are verified instead.
    """

    def setup_method(self):
        self.connector = StatisticalConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "statistical"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.sas7bdat")}
        )
        assert valid is False

    def test_validate_config_rejects_unsupported_extension(self, tmp_path):
        path = tmp_path / "data.unsupported"
        path.write_bytes(b"fake")
        valid, msg = self.connector.validate_config({"file_path": str(path)})
        assert valid is False
        assert len(msg) > 0

    def test_validate_config_accepts_sas_extension(self, tmp_fake_sas):
        valid, _ = self.connector.validate_config({"file_path": tmp_fake_sas})
        assert valid is True

    def test_validate_config_accepts_dta_extension(self, tmp_path):
        path = tmp_path / "sample.dta"
        path.write_bytes(b"fake stata")
        valid, _ = self.connector.validate_config({"file_path": str(path)})
        assert valid is True

    def test_validate_config_accepts_sav_extension(self, tmp_path):
        path = tmp_path / "sample.sav"
        path.write_bytes(b"fake spss")
        valid, _ = self.connector.validate_config({"file_path": str(path)})
        assert valid is True

    def test_validate_config_accepts_h5_extension(self, tmp_path):
        path = tmp_path / "sample.h5"
        path.write_bytes(b"fake hdf5")
        valid, _ = self.connector.validate_config({"file_path": str(path)})
        assert valid is True

    def test_validate_config_accepts_hdf5_extension(self, tmp_path):
        path = tmp_path / "sample.hdf5"
        path.write_bytes(b"fake hdf5")
        valid, _ = self.connector.validate_config({"file_path": str(path)})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    def test_get_config_schema_has_file_path_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "file_path" in names

    def test_get_config_schema_has_hdf_key_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "hdf_key" in names

    # -- load raises DataLoadError on bad file content -----------------------

    @pytest.mark.parametrize("extension", [".sas7bdat", ".sav", ".zsav"])
    def test_load_raises_data_load_error_on_corrupt_content(self, tmp_path, extension):
        path = tmp_path / f"corrupt{extension}"
        path.write_bytes(b"this is not a real statistical file")
        with pytest.raises(DataLoadError):
            self.connector.load({"file_path": str(path)})


# ===========================================================================
# PDFConnector
# ===========================================================================

class TestPDFConnector:
    """Tests for PDFConnector.

    load() tests are skipped — tabula-py requires a Java runtime and a real PDF
    with tables, which cannot be reliably created in unit test fixtures.
    """

    def setup_method(self):
        self.connector = PDFConnector()

    # -- Properties ----------------------------------------------------------

    def test_connector_type(self):
        assert self.connector.connector_type == "pdf"

    def test_display_name_is_string(self):
        assert isinstance(self.connector.display_name, str)

    # -- validate_config -----------------------------------------------------

    def test_validate_config_rejects_missing_file_path(self):
        valid, msg = self.connector.validate_config({})
        assert valid is False
        assert "file_path" in msg.lower()

    def test_validate_config_rejects_nonexistent_file(self, tmp_path):
        valid, _ = self.connector.validate_config(
            {"file_path": str(tmp_path / "ghost.pdf")}
        )
        assert valid is False

    def test_validate_config_rejects_non_pdf_extension(self, tmp_path):
        path = tmp_path / "report.docx"
        path.write_bytes(b"not a pdf")
        valid, msg = self.connector.validate_config({"file_path": str(path)})
        assert valid is False
        assert len(msg) > 0

    def test_validate_config_accepts_existing_pdf(self, tmp_fake_pdf):
        valid, _ = self.connector.validate_config({"file_path": tmp_fake_pdf})
        assert valid is True

    # -- get_config_schema ---------------------------------------------------

    def test_get_config_schema_structure(self):
        _assert_schema(self.connector.get_config_schema())

    def test_get_config_schema_has_file_path_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "file_path" in names

    def test_get_config_schema_has_pages_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "pages" in names

    def test_get_config_schema_has_table_index_field(self):
        names = [f["name"] for f in self.connector.get_config_schema()]
        assert "table_index" in names

    # -- load is skipped (requires Java / real PDF) --------------------------

    @pytest.mark.skip(reason="tabula-py requires a Java runtime; cannot run in unit tests")
    def test_load_skipped(self):
        pass
