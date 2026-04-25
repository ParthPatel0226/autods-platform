"""Tool module: report_tools

Re-exports report generation utilities from the actual implementation
modules under ``reports/generators/``.  Agent code can import from here
for a flat namespace.
"""

import logging

logger = logging.getLogger(__name__)

# Re-export public APIs from the canonical implementation modules.
from reports.generators.html_report import generate_html_report  # noqa: F401
from reports.generators.pdf_report import generate_pdf_report  # noqa: F401
from reports.generators.executive_summary import generate_executive_summary  # noqa: F401
from reports.generators.notebook_export import generate_notebook  # noqa: F401
from reports.generators.zip_packager import create_zip_package  # noqa: F401

__all__ = [
    "generate_html_report",
    "generate_pdf_report",
    "generate_executive_summary",
    "generate_notebook",
    "create_zip_package",
]
