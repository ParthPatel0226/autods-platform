"""Executive Summary Generator.

Produces a concise, 1-page executive summary aimed at senior
stakeholders. Uses domain-specific terminology and focuses on
actionable findings rather than technical detail.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_DOMAIN_LABELS: dict[str, str] = {
    "healthcare": "Healthcare",
    "finance": "Finance",
    "ecommerce": "E-Commerce",
    "marketing": "Marketing",
    "hr": "Human Resources",
    "manufacturing": "Manufacturing",
    "generic": "Data Science",
}

_DOMAIN_ICONS: dict[str, str] = {
    "healthcare": "H",
    "finance": "F",
    "ecommerce": "E",
    "marketing": "M",
    "hr": "HR",
    "manufacturing": "MF",
    "generic": "DS",
}


def _safe_get(state: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        val = state.get(key)
        if val is not None:
            return val
    return default


def _generate_key_findings(state: dict) -> list[str]:
    """Extract the top 3-5 actionable insights from pipeline state.

    Pulls from eda_insights, eda_summary, and model results to compile
    a short list of the most important findings.

    Args:
        state: Pipeline state dict.

    Returns:
        List of finding strings (3-5 items).
    """
    findings: list[str] = []

    # Pull explicit insights first
    eda_insights = state.get("eda_insights") or []
    for insight in eda_insights[:3]:
        findings.append(str(insight))

    # Add model performance finding if available
    best_model = _safe_get(state, "best_model", "best_model_name", default=None)
    model_results = state.get("model_results") or {}
    if best_model and isinstance(model_results.get(best_model), dict):
        metrics = model_results[best_model]
        top_metric = next(iter(metrics.items()), None)
        if top_metric:
            name, val = top_metric
            val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
            findings.append(
                f"The best model ({best_model}) achieved {name} = {val_str}."
            )

    # Add feature count finding
    features = _safe_get(state, "feature_list", "features_selected", default=[])
    if features:
        findings.append(
            f"{len(features)} features were selected for the final model."
        )

    # Add data quality finding
    quality_issues = state.get("quality_issues") or []
    if quality_issues:
        findings.append(
            f"{len(quality_issues)} data quality issue(s) were identified and addressed."
        )
    elif not findings:
        findings.append("No significant data quality issues were detected.")

    # Ensure we have at least 3 findings
    while len(findings) < 3:
        findings.append("Refer to the full report for additional details.")

    return findings[:5]


def _generate_recommendations(state: dict) -> list[str]:
    """Generate actionable next-step recommendations.

    Tailors language to the detected domain using the domain configuration
    terminology map when available.

    Args:
        state: Pipeline state dict.

    Returns:
        List of recommendation strings (3 items).
    """
    domain_cfg = state.get("domain_config") or {}
    term_map = domain_cfg.get("terminology_map", {})
    prediction_label = term_map.get("prediction", "prediction")
    user_label = term_map.get("user", "record")

    recs: list[str] = []

    # Always recommend validation
    recs.append(
        f"Validate {prediction_label} performance on a held-out or prospective "
        f"{user_label} cohort before production deployment."
    )

    # SHAP / explainability recommendation
    shap_data = _safe_get(state, "shap_values", "shap_summary", default=None)
    if shap_data:
        recs.append(
            f"Review SHAP feature importance to confirm that top drivers of "
            f"{prediction_label} align with domain expertise."
        )
    else:
        recs.append(
            f"Generate SHAP explanations to understand key drivers of "
            f"{prediction_label}."
        )

    # Fairness recommendation for sensitive domains
    domain = state.get("detected_domain", "generic")
    fairness = state.get("fairness_report")
    if domain in ("healthcare", "finance", "hr"):
        if fairness:
            recs.append(
                "Review the fairness audit and ensure compliance with "
                "applicable regulations before deployment."
            )
        else:
            recs.append(
                "Conduct a fairness audit on protected attributes before "
                "deploying the model."
            )
    else:
        recs.append(
            "Monitor model performance over time and retrain when data "
            "drift is detected."
        )

    return recs[:3]


def generate_executive_summary(state: dict, output_dir: str) -> str:
    """Generate a 1-page executive summary HTML document.

    Uses domain-specific terminology (e.g. "patient" instead of "user"
    for healthcare) and keeps the output concise enough for a single
    printed page.

    Args:
        state: AutoDS pipeline state dict.
        output_dir: Directory to write the summary file into.

    Returns:
        Absolute path to the generated executive_summary.html file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("executive_template.html")

    domain = state.get("detected_domain", "generic")
    domain_cfg = state.get("domain_config") or {}
    term_map = domain_cfg.get("terminology_map", {})

    best_model_name = _safe_get(
        state, "best_model", "best_model_name", default="N/A"
    )
    model_results = state.get("model_results") or {}
    best_metrics = {}
    if isinstance(model_results.get(best_model_name), dict):
        raw = model_results[best_model_name]
        # model_results may nest metrics under a "metrics" key or be flat
        best_metrics = raw.get("metrics", raw) if isinstance(raw, dict) else raw
        # Filter to only numeric values for display
        best_metrics = {k: v for k, v in best_metrics.items() if isinstance(v, (int, float))}

    # Build top metrics for the summary boxes (max 4)
    top_metrics = [
        {"label": html.escape(str(k)),
         "value": f"{v:.3f}" if isinstance(v, float) else html.escape(str(v))}
        for k, v in list(best_metrics.items())[:4]
    ]

    key_findings = [html.escape(f) for f in _generate_key_findings(state)]
    recommendations = [html.escape(r) for r in _generate_recommendations(state)]

    user_label = html.escape(term_map.get("user", "record"))

    # Build best_model object for template
    best_model_obj = None
    if best_model_name != "N/A" and best_metrics:
        best_model_obj = {
            "name": html.escape(str(best_model_name)),
            "metrics": {
                html.escape(str(k)): v
                for k, v in list(best_metrics.items())[:4]
            },
        }

    context = {
        "title": f"{_DOMAIN_LABELS.get(domain, 'Data Science')} Analysis Summary",
        "domain_name": _DOMAIN_LABELS.get(domain, "Data Science"),
        "domain_icon": _DOMAIN_ICONS.get(domain, "DS"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "top_metrics": top_metrics,
        "key_findings": key_findings,
        "best_model": best_model_obj,
        "recommendations": recommendations,
        "data_source": html.escape(
            str(state.get("session_id", "uploaded dataset"))
        ),
        "row_count": f"{state.get('row_count', 0):,}",
        "random_seed": state.get("random_seed", 42),
    }

    rendered = template.render(**context)

    out_path = out_dir / "executive_summary.html"
    out_path.write_text(rendered, encoding="utf-8")
    logger.info("Executive summary generated at %s", out_path)
    return str(out_path)
