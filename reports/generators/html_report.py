"""HTML Report Generator.

Renders an interactive HTML report using Jinja2 templates with embedded
Plotly charts, metric cards, and domain-specific sections.
"""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_DOMAIN_ICONS: dict[str, str] = {
    "healthcare": "H",
    "finance": "F",
    "ecommerce": "E",
    "marketing": "M",
    "hr": "HR",
    "manufacturing": "MF",
    "generic": "DS",
}

_DOMAIN_TEMPLATE_MAP: dict[str, str] = {
    "healthcare": "healthcare_report.html",
    "finance": "finance_report.html",
    "ecommerce": "ecommerce_report.html",
}


def _safe_get(state: dict, *keys: str, default: Any = None) -> Any:
    """Return first key found in state, else default."""
    for key in keys:
        val = state.get(key)
        if val is not None:
            return val
    return default


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment pointing at the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _render_metric_cards(metrics: dict) -> str:
    """Render key metrics as styled HTML card fragments.

    Args:
        metrics: Mapping of label to value (numeric or string).

    Returns:
        HTML string containing a grid of metric cards.
    """
    if not metrics:
        return '<div class="metrics-grid"><p>No metrics available.</p></div>'

    cards: list[str] = []
    for label, value in metrics.items():
        safe_label = html.escape(str(label))
        if isinstance(value, float):
            display_value = f"{value:.4f}"
        else:
            display_value = html.escape(str(value))
        cards.append(
            f'<div class="metric-card">'
            f'<div class="metric-value">{display_value}</div>'
            f'<div class="metric-label">{safe_label}</div>'
            f"</div>"
        )
    return f'<div class="metrics-grid">{"".join(cards)}</div>'


def _render_model_comparison_table(model_results: dict) -> str:
    """Render a comparison table of all trained models.

    Args:
        model_results: Mapping of model name to metrics dict.

    Returns:
        HTML table string.
    """
    if not model_results:
        return "<p>No model results available.</p>"

    # Collect all metric names across models for column headers
    all_metric_names: list[str] = []
    for metrics in model_results.values():
        if isinstance(metrics, dict):
            for key in metrics:
                if key not in all_metric_names:
                    all_metric_names.append(key)

    if not all_metric_names:
        return "<p>No model metrics to display.</p>"

    # Limit to first 6 metric columns for readability
    display_metrics = all_metric_names[:6]

    header_cells = "".join(
        f"<th>{html.escape(str(m))}</th>" for m in display_metrics
    )
    header = f"<tr><th>Model</th>{header_cells}</tr>"

    rows: list[str] = []
    for model_name, metrics in model_results.items():
        safe_name = html.escape(str(model_name))
        if isinstance(metrics, dict):
            cells = ""
            for m in display_metrics:
                val = metrics.get(m)
                if isinstance(val, float):
                    cells += f"<td>{val:.4f}</td>"
                elif val is not None:
                    cells += f"<td>{html.escape(str(val))}</td>"
                else:
                    cells += "<td>N/A</td>"
            rows.append(f"<tr><td><strong>{safe_name}</strong></td>{cells}</tr>")
        else:
            cols = len(display_metrics)
            rows.append(
                f"<tr><td><strong>{safe_name}</strong></td>"
                f"<td colspan='{cols}'>{html.escape(str(metrics))}</td></tr>"
            )

    return (
        '<table class="model-comparison">'
        f"<thead>{header}</thead>"
        f'<tbody>{"".join(rows)}</tbody>'
        "</table>"
    )


def _render_chart_section(charts: list[dict]) -> str:
    """Render a list of Plotly chart specifications as embeddable divs.

    Each chart dict should contain:
        - title (str): Chart heading
        - data (str|list): Plotly data JSON
        - layout (str|dict): Plotly layout JSON

    Args:
        charts: List of chart specification dicts.

    Returns:
        HTML string with Plotly div blocks.
    """
    if not charts:
        return ""

    blocks: list[str] = []
    for idx, chart in enumerate(charts):
        chart_id = f"plotly-chart-{idx}"
        title = html.escape(str(chart.get("title", f"Chart {idx + 1}")))

        data_json = chart.get("data", "[]")
        if not isinstance(data_json, str):
            data_json = json.dumps(data_json, default=str)

        layout_json = chart.get("layout", "{}")
        if not isinstance(layout_json, str):
            layout_json = json.dumps(layout_json, default=str)

        blocks.append(
            f'<div class="chart-container">'
            f"<h3>{title}</h3>"
            f'<div id="{chart_id}" style="width:100%;min-height:400px;"></div>'
            f"<script>Plotly.newPlot('{chart_id}', {data_json}, {layout_json}, "
            f"{{responsive: true}});</script>"
            f"</div>"
        )
    return "\n".join(blocks)


def _build_domain_context(state: dict) -> dict[str, Any]:
    """Extract domain-specific template variables from state."""
    domain = state.get("detected_domain", "generic")
    context: dict[str, Any] = {}

    if domain == "healthcare":
        context["survival_curves"] = state.get("survival_curves", "")
        context["comorbidity_analysis"] = state.get("comorbidity_analysis", "")
        context["disparity_analysis"] = state.get("disparity_analysis", "")
        context["fairness_report_html"] = ""
        fairness = state.get("fairness_report")
        if fairness:
            context["fairness_report_html"] = (
                f'<pre class="code-block">'
                f"{html.escape(json.dumps(fairness, default=str, indent=2)[:3000])}"
                f"</pre>"
            )
    elif domain == "finance":
        context["ks_gini_analysis"] = state.get("ks_gini_analysis", "")
        context["gain_lift_charts"] = state.get("gain_lift_charts", "")
        context["score_distribution"] = state.get("score_distribution", "")
        context["adverse_action"] = state.get("adverse_action", "")
        context["vintage_analysis"] = state.get("vintage_analysis", "")
    elif domain == "ecommerce":
        context["rfm_analysis"] = state.get("rfm_analysis", "")
        context["cohort_retention"] = state.get("cohort_retention", "")
        context["funnel_analysis"] = state.get("funnel_analysis", "")
        context["clv_analysis"] = state.get("clv_analysis", "")
        context["seasonal_analysis"] = state.get("seasonal_analysis", "")

    return context


def generate_html_report(state: dict, output_dir: str) -> str:
    """Generate an interactive HTML report from pipeline state.

    Loads the base Jinja2 template (or domain-specific child template when
    available) and injects all pipeline results including Plotly charts.

    Args:
        state: AutoDS pipeline state dict.
        output_dir: Directory to write the report file into.

    Returns:
        Absolute path to the generated HTML file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _get_jinja_env()

    domain = state.get("detected_domain", "generic")
    domain_template = _DOMAIN_TEMPLATE_MAP.get(domain)

    # Decide which template to use
    if domain_template:
        try:
            template = env.get_template(domain_template)
        except Exception:
            logger.warning(
                "Domain template %s not found, falling back to base.",
                domain_template,
            )
            template = env.get_template("base_report.html")
    else:
        template = env.get_template("base_report.html")

    # Build key metrics dict
    best_model_name = _safe_get(
        state, "best_model", "best_model_name", default="N/A"
    )
    model_results = state.get("model_results") or {}
    best_metrics = {}
    if isinstance(model_results.get(best_model_name), dict):
        best_metrics = model_results[best_model_name]

    key_metrics_list = [
        {"label": k, "value": f"{v:.4f}" if isinstance(v, float) else str(v)}
        for k, v in list(best_metrics.items())[:6]
    ]

    # Charts
    eda_charts = state.get("eda_charts") or state.get("charts") or []
    charts_html = _render_chart_section(eda_charts)
    model_table_html = _render_model_comparison_table(model_results)

    # SHAP section
    shap_data = _safe_get(state, "shap_values", "shap_summary", default=None)
    shap_html = ""
    if shap_data:
        shap_html = (
            f'<pre class="code-block">'
            f"{html.escape(json.dumps(shap_data, default=str, indent=2)[:3000])}"
            f"</pre>"
        )

    # Fairness section
    fairness = state.get("fairness_report")
    fairness_html = ""
    if fairness:
        fairness_html = (
            f'<pre class="code-block">'
            f"{html.escape(json.dumps(fairness, default=str, indent=2)[:3000])}"
            f"</pre>"
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build domain context
    domain_ctx = _build_domain_context(state)

    context: dict[str, Any] = {
        "title": f"AutoDS Analysis Report - {html.escape(str(state.get('session_id', '')))}",
        "domain_name": domain.title(),
        "domain_icon": _DOMAIN_ICONS.get(domain, "DS"),
        "timestamp": timestamp,
        "executive_summary": html.escape(
            str(state.get("eda_summary") or "Analysis summary not available.")
        ),
        "key_metrics": key_metrics_list,
        "eda_summary": html.escape(
            str(state.get("eda_summary") or "")
        ),
        "eda_charts": eda_charts,
        "charts_html": charts_html,
        "model_results": model_results,
        "model_summary": model_table_html,
        "best_model_name": html.escape(str(best_model_name)),
        "shap_summary": shap_html,
        "explainability_content": shap_html,
        "fairness_report": fairness_html,
        "recommendations": html.escape(
            str(state.get("recommendations", "Complete the pipeline for recommendations."))
        ),
        "random_seed": state.get("random_seed", 42),
        "data_hash": html.escape(str(state.get("data_hash", "N/A"))),
        "duration": html.escape(str(state.get("pipeline_duration", "N/A"))),
        "api_calls": state.get("api_call_count", 0),
        "cost": f"{state.get('estimated_cost', 0):.2f}",
        **domain_ctx,
    }

    rendered = template.render(**context)

    out_path = out_dir / "report.html"
    out_path.write_text(rendered, encoding="utf-8")

    # Copy styles.css alongside the report
    styles_src = _TEMPLATES_DIR / "styles.css"
    if styles_src.exists():
        styles_dst = out_dir / "styles.css"
        styles_dst.write_text(styles_src.read_text(encoding="utf-8"), encoding="utf-8")

    logger.info("HTML report generated at %s", out_path)
    return str(out_path)
