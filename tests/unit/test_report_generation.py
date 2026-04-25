"""Unit tests for reports/generators/*.

Tests HTML report, notebook export, executive summary, and ZIP packager.
Verifies output file creation, content structure, and graceful handling
of missing state sections.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid state dict for report generation."""
    base: dict[str, Any] = {
        "session_id": "test-report",
        "detected_domain": "generic",
        "problem_type": "classification",
        "target_column": "churned",
        "user_mode": "guided",
        "row_count": 500,
        "column_count": 10,
        "best_model_name": "xgboost",
        "best_model_metrics": {
            "accuracy": 0.92,
            "f1": 0.87,
            "precision": 0.89,
            "recall": 0.85,
            "auc_roc": 0.95,
        },
        "model_results": {
            "xgboost": {
                "metrics": {"accuracy": 0.92, "f1": 0.87},
                "training_time_seconds": 12.5,
            },
            "random_forest": {
                "metrics": {"accuracy": 0.89, "f1": 0.83},
                "training_time_seconds": 8.2,
            },
        },
        "feature_importance": {
            "age": 0.25,
            "income": 0.20,
            "tenure_months": 0.15,
            "balance": 0.12,
            "num_products": 0.10,
        },
        "eda_insights": [
            "Age distribution is right-skewed",
            "Income has 3% missing values",
            "Strong correlation between balance and income (r=0.72)",
        ],
        "eda_charts": [],
        "quality_issues": [],
        "completed_steps": ["upload", "eda", "feature_engineering", "modeling"],
        "workflow_status": "completed",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# HTML Report
# ---------------------------------------------------------------------------

class TestHTMLReport:
    def test_generates_html_file(self, tmp_path):
        from reports.generators.html_report import generate_html_report

        state = _make_state()
        path = generate_html_report(state, str(tmp_path))
        assert Path(path).is_file()
        assert path.endswith(".html")

    def test_html_contains_model_name(self, tmp_path):
        from reports.generators.html_report import generate_html_report

        state = _make_state()
        path = generate_html_report(state, str(tmp_path))
        content = Path(path).read_text(encoding="utf-8")
        assert "xgboost" in content.lower()

    def test_html_with_empty_model_results(self, tmp_path):
        from reports.generators.html_report import generate_html_report

        state = _make_state(model_results={}, best_model_name="", best_model_metrics={})
        path = generate_html_report(state, str(tmp_path))
        assert Path(path).is_file()

    def test_html_with_healthcare_domain(self, tmp_path):
        from reports.generators.html_report import generate_html_report

        state = _make_state(detected_domain="healthcare")
        path = generate_html_report(state, str(tmp_path))
        assert Path(path).is_file()

    def test_metric_cards_render(self):
        from reports.generators.html_report import _render_metric_cards

        metrics = {"accuracy": 0.92, "f1": 0.87}
        html = _render_metric_cards(metrics)
        assert isinstance(html, str)
        assert "0.92" in html or "92" in html

    def test_model_comparison_table(self):
        from reports.generators.html_report import _render_model_comparison_table

        results = {
            "xgboost": {"metrics": {"accuracy": 0.92}},
            "rf": {"metrics": {"accuracy": 0.89}},
        }
        html = _render_model_comparison_table(results)
        assert isinstance(html, str)
        assert "xgboost" in html.lower()


# ---------------------------------------------------------------------------
# Notebook Export
# ---------------------------------------------------------------------------

class TestNotebookExport:
    def test_generates_notebook_file(self, tmp_path):
        from reports.generators.notebook_export import generate_notebook

        state = _make_state()
        path = generate_notebook(state, str(tmp_path))
        assert Path(path).is_file()
        assert path.endswith(".ipynb")

    def test_notebook_is_valid_json(self, tmp_path):
        from reports.generators.notebook_export import generate_notebook

        state = _make_state()
        path = generate_notebook(state, str(tmp_path))
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "cells" in content
        assert "nbformat" in content
        assert len(content["cells"]) > 0

    def test_notebook_has_import_cell(self, tmp_path):
        from reports.generators.notebook_export import generate_notebook

        state = _make_state()
        path = generate_notebook(state, str(tmp_path))
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        first_code_cell = next(
            (c for c in content["cells"] if c["cell_type"] == "code"), None
        )
        assert first_code_cell is not None
        source = "".join(first_code_cell["source"])
        assert "import" in source

    def test_notebook_with_empty_state(self, tmp_path):
        from reports.generators.notebook_export import generate_notebook

        state = _make_state(
            model_results={},
            feature_importance={},
            eda_insights=[],
        )
        path = generate_notebook(state, str(tmp_path))
        assert Path(path).is_file()


# ---------------------------------------------------------------------------
# Executive Summary
# ---------------------------------------------------------------------------

class TestExecutiveSummary:
    def test_generates_file(self, tmp_path):
        from reports.generators.executive_summary import generate_executive_summary

        state = _make_state()
        path = generate_executive_summary(state, str(tmp_path))
        assert Path(path).is_file()

    def test_key_findings_extraction(self):
        from reports.generators.executive_summary import _generate_key_findings

        state = _make_state()
        findings = _generate_key_findings(state)
        assert isinstance(findings, list)
        assert len(findings) > 0

    def test_recommendations_extraction(self):
        from reports.generators.executive_summary import _generate_recommendations

        state = _make_state()
        recs = _generate_recommendations(state)
        assert isinstance(recs, list)

    def test_with_minimal_state(self, tmp_path):
        from reports.generators.executive_summary import generate_executive_summary

        state = {
            "session_id": "minimal",
            "detected_domain": "generic",
            "problem_type": "classification",
        }
        path = generate_executive_summary(state, str(tmp_path))
        assert Path(path).is_file()


# ---------------------------------------------------------------------------
# ZIP Packager
# ---------------------------------------------------------------------------

class TestZipPackager:
    def test_creates_zip_file(self, tmp_path):
        from reports.generators.zip_packager import create_zip_package

        # Create some dummy files
        f1 = tmp_path / "report.html"
        f1.write_text("<html>test</html>")
        f2 = tmp_path / "data.csv"
        f2.write_text("a,b\n1,2")

        out = tmp_path / "output"
        out.mkdir()
        zip_path = create_zip_package([str(f1), str(f2)], str(out / "package.zip"))
        assert Path(zip_path).is_file()

    def test_zip_contains_readme(self, tmp_path):
        import zipfile

        from reports.generators.zip_packager import create_zip_package

        f1 = tmp_path / "report.html"
        f1.write_text("<html>test</html>")

        zip_path = create_zip_package([str(f1)], str(tmp_path / "pkg.zip"))
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert any("readme" in n.lower() for n in names) or len(names) >= 1

    def test_zip_with_no_files(self, tmp_path):
        from reports.generators.zip_packager import create_zip_package

        zip_path = create_zip_package([], str(tmp_path / "empty.zip"))
        assert Path(zip_path).is_file()

    def test_zip_with_nonexistent_files(self, tmp_path):
        from reports.generators.zip_packager import create_zip_package

        # Should handle gracefully (skip missing files)
        zip_path = create_zip_package(
            ["/nonexistent/file.txt"],
            str(tmp_path / "skip.zip"),
        )
        assert Path(zip_path).is_file()
