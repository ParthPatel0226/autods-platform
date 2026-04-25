"""PDF Report Generator.

Creates a print-ready PDF by rendering the HTML report and converting it
via weasyprint. Falls back gracefully when weasyprint is not installed.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _add_print_styles(html_content: str) -> str:
    """Inject print-optimised CSS into an HTML string.

    Adds @page rules, page-break directives, and tweaks that improve
    the PDF rendering quality without altering the screen appearance.

    Args:
        html_content: Original HTML string.

    Returns:
        HTML with print styles injected before </head>.
    """
    print_css = """
<style>
@page {
    size: letter;
    margin: 0.75in 0.6in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #999;
    }
}
@media print {
    body {
        font-size: 10pt;
        max-width: 100%;
        padding: 0;
        margin: 0;
        color: #222;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    h2 {
        page-break-before: always;
        margin-top: 0;
    }
    h2:first-of-type {
        page-break-before: avoid;
    }
    .chart-container,
    table,
    .metric-card,
    .insight-box,
    .warning-box,
    .success-box {
        page-break-inside: avoid;
    }
    .no-print {
        display: none !important;
    }
    a { color: #333; text-decoration: none; }
    pre, code { font-size: 8pt; }
}
</style>
"""
    # Insert before </head> if present, otherwise prepend
    if "</head>" in html_content:
        return html_content.replace("</head>", print_css + "</head>")
    return print_css + html_content


def _strip_plotly_scripts(html_content: str) -> str:
    """Remove Plotly CDN script tags and inline Plotly.newPlot calls.

    Plotly JS does not render in weasyprint. Replacing with a static
    placeholder avoids blank space and JS errors in the PDF.

    Args:
        html_content: HTML string potentially containing Plotly elements.

    Returns:
        Cleaned HTML.
    """
    # Remove Plotly CDN include
    html_content = re.sub(
        r'<script\s+src="[^"]*plotly[^"]*"[^>]*>\s*</script>',
        "",
        html_content,
        flags=re.IGNORECASE,
    )
    # Replace inline Plotly.newPlot script blocks with a placeholder note
    html_content = re.sub(
        r"<script>\s*Plotly\.newPlot\([^)]*\).*?</script>",
        '<p style="color:#888;font-style:italic;">'
        "[Interactive chart — see HTML report]</p>",
        html_content,
        flags=re.DOTALL,
    )
    return html_content


def generate_pdf_report(state: dict, output_dir: str) -> str:
    """Generate a print-ready PDF report.

    Reuses the HTML report generator, injects print styles, and converts
    to PDF via weasyprint. If weasyprint is unavailable the function
    returns an empty string and logs a warning.

    Args:
        state: AutoDS pipeline state dict.
        output_dir: Directory to write the PDF file into.

    Returns:
        Absolute path to the generated PDF, or empty string on failure.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate the HTML first
    from reports.generators.html_report import generate_html_report

    html_path = generate_html_report(state, output_dir)
    html_content = Path(html_path).read_text(encoding="utf-8")

    # Prepare for print
    html_content = _strip_plotly_scripts(html_content)
    html_content = _add_print_styles(html_content)

    pdf_path = out_dir / "report.pdf"

    try:
        import weasyprint  # type: ignore[import-untyped]

        wp_html = weasyprint.HTML(
            string=html_content,
            base_url=str(out_dir),
        )
        wp_html.write_pdf(str(pdf_path))
        logger.info("PDF report generated at %s", pdf_path)
        return str(pdf_path)

    except ImportError:
        logger.warning(
            "weasyprint is not installed. PDF generation skipped. "
            "Install with: pip install weasyprint"
        )
        return ""

    except Exception as exc:
        logger.error("PDF generation failed: %s", exc, exc_info=True)
        return ""
