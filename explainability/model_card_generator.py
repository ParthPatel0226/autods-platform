"""Model card generator (Google model card format).

Produces a structured dict, Markdown, and HTML representations of a
model card suitable for documentation and compliance.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def generate_model_card(
    model_name: str,
    problem_type: str,
    domain: str,
    metrics: dict[str, Any],
    features: list[str],
    training_rows: int,
    shap_results: dict[str, Any] | None = None,
    fairness_results: dict[str, Any] | None = None,
    domain_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a structured model card dict.

    Args:
        model_name: Name or identifier of the model.
        problem_type: ``"classification"``, ``"regression"``, etc.
        domain: Detected industry domain.
        metrics: Performance metrics dict (e.g. ``{"accuracy": 0.95}``).
        features: List of feature names used in training.
        training_rows: Number of rows in the training dataset.
        shap_results: Optional SHAP output from ``compute_shap_values``.
        fairness_results: Optional output from ``run_fairness_audit``.
        domain_config: Optional domain configuration dict for
            domain-specific text.

    Returns:
        Structured model card dict.
    """
    dc = domain_config or {}

    # Feature importance summary
    top_features: list[dict[str, Any]] = []
    if shap_results and shap_results.get("top_features"):
        top_features = shap_results["top_features"][:10]

    card: dict[str, Any] = {
        "model_details": {
            "name": model_name,
            "type": problem_type,
            "domain": domain,
            "version": "1.0",
            "date": datetime.now(timezone.utc).isoformat(),
            "framework": "scikit-learn compatible",
        },
        "intended_use": {
            "primary": _domain_intended_use(domain, dc),
            "users": _domain_users(domain, dc),
            "out_of_scope": _domain_out_of_scope(domain, dc),
        },
        "training_data": {
            "rows": training_rows,
            "features_count": len(features),
            "features": features[:50],
        },
        "metrics": _format_metrics(metrics),
        "feature_importance": top_features,
        "limitations": _domain_limitations(domain, dc),
        "ethical_considerations": _ethical_considerations(domain, fairness_results, dc),
        "fairness": _format_fairness(fairness_results),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("Model card generated for '%s' (%s, %s).", model_name, problem_type, domain)
    return card


def model_card_to_markdown(card: dict[str, Any]) -> str:
    """Convert a model card dict to Markdown.

    Args:
        card: Output of ``generate_model_card``.

    Returns:
        Markdown string.
    """
    md = card.get("model_details", {})
    lines = [
        f"# Model Card: {md.get('name', 'Unknown')}",
        "",
        "## Model Details",
        f"- **Type:** {md.get('type', 'N/A')}",
        f"- **Domain:** {md.get('domain', 'N/A')}",
        f"- **Version:** {md.get('version', '1.0')}",
        f"- **Date:** {md.get('date', 'N/A')}",
        f"- **Framework:** {md.get('framework', 'N/A')}",
        "",
        "## Intended Use",
        f"{card.get('intended_use', {}).get('primary', 'N/A')}",
        "",
        f"**Target users:** {card.get('intended_use', {}).get('users', 'N/A')}",
        "",
        f"**Out of scope:** {card.get('intended_use', {}).get('out_of_scope', 'N/A')}",
        "",
        "## Training Data",
    ]

    td = card.get("training_data", {})
    lines.append(f"- **Rows:** {td.get('rows', 'N/A')}")
    lines.append(f"- **Features:** {td.get('features_count', 'N/A')}")
    lines.append("")

    # Metrics
    lines.append("## Performance Metrics")
    metrics = card.get("metrics", {})
    if metrics:
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in metrics.items():
            lines.append(f"| {k} | {v} |")
    else:
        lines.append("No metrics available.")
    lines.append("")

    # Feature importance
    fi = card.get("feature_importance", [])
    if fi:
        lines.append("## Top Features")
        lines.append("")
        lines.append("| Feature | Importance |")
        lines.append("|---------|------------|")
        for item in fi:
            feat = item.get("feature", "")
            imp = item.get("mean_abs_shap", item.get("score", ""))
            lines.append(f"| {feat} | {imp} |")
        lines.append("")

    # Limitations
    lines.append("## Limitations")
    lim = card.get("limitations", "")
    lines.append(lim if lim else "No specific limitations documented.")
    lines.append("")

    # Ethical considerations
    lines.append("## Ethical Considerations")
    eth = card.get("ethical_considerations", "")
    lines.append(eth if eth else "No specific ethical considerations documented.")
    lines.append("")

    # Fairness
    fairness = card.get("fairness", {})
    if fairness and not fairness.get("skipped"):
        lines.append("## Fairness Assessment")
        for attr, data in fairness.items():
            if isinstance(data, dict):
                lines.append(f"- **{attr}:** DPD={data.get('dpd', 'N/A')}, DI={data.get('di', 'N/A')}")
        lines.append("")

    lines.append(f"*Generated at {card.get('generated_at', 'N/A')}*")
    return "\n".join(lines)


def model_card_to_html(card: dict[str, Any]) -> str:
    """Convert a model card dict to a standalone HTML document.

    Args:
        card: Output of ``generate_model_card``.

    Returns:
        HTML string.
    """
    md_content = model_card_to_markdown(card)

    # Simple Markdown-to-HTML conversion for the subset we use
    html_body = _simple_md_to_html(md_content)

    return (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"<title>Model Card: {card.get('model_details', {}).get('name', 'Model')}</title>\n"
        "<style>\n"
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #333; }\n"
        "h1 { border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; }\n"
        "h2 { color: #1e40af; margin-top: 2rem; }\n"
        "table { border-collapse: collapse; width: 100%; margin: 1rem 0; }\n"
        "th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }\n"
        "th { background: #f8f9fa; }\n"
        "</style>\n"
        "</head>\n<body>\n"
        f"{html_body}\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Domain-specific text helpers
# ---------------------------------------------------------------------------

def _domain_intended_use(domain: str, dc: dict[str, Any]) -> str:
    custom = dc.get("intended_use")
    if custom:
        return str(custom)
    defaults = {
        "healthcare": (
            "Clinical decision support. Not a substitute for physician judgment. "
            "Requires clinical review before any action."
        ),
        "finance": (
            "Credit risk or financial outcome prediction. Subject to fair lending "
            "regulations. Requires compliance review before deployment."
        ),
        "hr": (
            "Workforce analytics. Must not be the sole basis for employment decisions. "
            "Requires HR leadership review."
        ),
    }
    return defaults.get(domain, "General purpose predictive modeling.")


def _domain_users(domain: str, dc: dict[str, Any]) -> str:
    custom = dc.get("target_users")
    if custom:
        return str(custom)
    defaults = {
        "healthcare": "Clinicians, clinical data scientists, hospital administrators.",
        "finance": "Risk analysts, compliance officers, data science teams.",
        "hr": "HR analysts, people operations teams, compensation managers.",
    }
    return defaults.get(domain, "Data scientists, analysts, and domain experts.")


def _domain_out_of_scope(domain: str, dc: dict[str, Any]) -> str:
    defaults = {
        "healthcare": "Not for autonomous clinical decisions without physician oversight.",
        "finance": "Not for real-time trading or automated lending without human review.",
        "hr": "Not for automated hiring/firing decisions.",
    }
    return defaults.get(domain, "Not for safety-critical automated decisions without human review.")


def _domain_limitations(domain: str, dc: dict[str, Any]) -> str:
    custom = dc.get("limitations")
    if custom:
        return str(custom)
    defaults = {
        "healthcare": (
            "Performance may degrade for underrepresented patient subgroups. "
            "Not validated outside the training data distribution. "
            "Does not account for temporal drift in clinical guidelines."
        ),
        "finance": (
            "Reflects historical patterns which may contain systemic biases. "
            "Requires ongoing monitoring for population shift and regulatory compliance."
        ),
        "hr": (
            "Correlational predictions only, not causal. "
            "Sensitive to demographic representation in training data."
        ),
    }
    return defaults.get(domain, "Monitor for data drift after deployment.")


def _ethical_considerations(
    domain: str,
    fairness_results: dict[str, Any] | None,
    dc: dict[str, Any],
) -> str:
    parts: list[str] = []
    if domain == "healthcare":
        parts.append("Ensure equitable treatment across patient demographics.")
    elif domain == "finance":
        parts.append("Comply with ECOA and fair lending requirements.")
    elif domain == "hr":
        parts.append("Review for potential discrimination across protected classes.")
    else:
        parts.append("Review model outputs for unintended bias before deployment.")

    if fairness_results and fairness_results.get("recommendations"):
        parts.extend(fairness_results["recommendations"])

    return " ".join(parts)


def _format_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    formatted: dict[str, Any] = {}
    for k, v in metrics.items():
        if isinstance(v, float):
            formatted[k] = round(v, 6)
        else:
            formatted[k] = v
    return formatted


def _format_fairness(fairness_results: dict[str, Any] | None) -> dict[str, Any]:
    if not fairness_results:
        return {"skipped": True}
    summary: dict[str, Any] = {}
    per_attr = fairness_results.get("per_attribute", {})
    for attr, data in per_attr.items():
        summary[attr] = {
            "dpd": data.get("demographic_parity_difference"),
            "di": data.get("disparate_impact_ratio"),
        }
    return summary


def _simple_md_to_html(md: str) -> str:
    """Minimal Markdown to HTML for model card rendering."""
    import html
    import re

    lines = md.split("\n")
    html_lines: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Table separator row
        if re.match(r"^\|[-| ]+\|$", stripped):
            continue

        # Table row
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                html_lines.append("<table>")
                tag = "th"
                in_table = True
            else:
                tag = "td"
            row_html = "<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>"
            html_lines.append(row_html)
            continue

        if in_table:
            html_lines.append("</table>")
            in_table = False

        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("- "):
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith("*") and stripped.endswith("*"):
            html_lines.append(f"<p><em>{stripped.strip('*')}</em></p>")
        elif stripped:
            # Bold markers
            processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            html_lines.append(f"<p>{processed}</p>")
        else:
            html_lines.append("")

    if in_table:
        html_lines.append("</table>")

    return "\n".join(html_lines)
