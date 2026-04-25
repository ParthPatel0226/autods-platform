"""Report Agent.

Generates professional, domain-styled reports in multiple formats:
HTML (interactive with Bootstrap), executive summary, Jupyter notebook,
and a ZIP package containing all artifacts.

Each format is generated independently so a failure in one does not
block the others.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.state import AutoDSState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain visual configuration
# ---------------------------------------------------------------------------
_DOMAIN_STYLES: dict[str, dict[str, str]] = {
    "healthcare":    {"color": "#1a7abf", "icon": "H",  "label": "Healthcare"},
    "finance":       {"color": "#1a6b3c", "icon": "F",  "label": "Finance"},
    "ecommerce":     {"color": "#e05c00", "icon": "E",  "label": "E-Commerce"},
    "marketing":     {"color": "#8b1a9e", "icon": "M",  "label": "Marketing"},
    "hr":            {"color": "#b5860a", "icon": "HR", "label": "Human Resources"},
    "manufacturing": {"color": "#4a4a4a", "icon": "MF", "label": "Manufacturing"},
    "generic":       {"color": "#3a3a8c", "icon": "DS", "label": "Data Science"},
}


def _domain_style(domain: str) -> dict[str, str]:
    return _DOMAIN_STYLES.get(domain, _DOMAIN_STYLES["generic"])


def _safe_get(state: AutoDSState, *keys: str, default: Any = None) -> Any:
    """Return the first key that exists in state, else default."""
    for key in keys:
        val = state.get(key)  # type: ignore[arg-type]
        if val is not None:
            return val
    return default


# ---------------------------------------------------------------------------
# HTML Report
# ---------------------------------------------------------------------------
def _build_model_rows(model_results: dict) -> str:
    _esc = html_mod.escape
    if not model_results:
        return "<tr><td colspan='3'>No model results available.</td></tr>"
    rows: list[str] = []
    for name, metrics in model_results.items():
        safe_name = _esc(str(name))
        if isinstance(metrics, dict):
            items = list(metrics.items())
            col1_name, col1_val = (items[0] if items else ("", "N/A"))
            col2_name, col2_val = (items[1] if len(items) > 1 else ("", ""))
            c1 = (f"{_esc(str(col1_name))}: {col1_val:.4f}" if isinstance(col1_val, float)
                  else f"{_esc(str(col1_name))}: {_esc(str(col1_val))}")
            c2 = (f"{_esc(str(col2_name))}: {col2_val:.4f}" if isinstance(col2_val, float)
                  else f"{_esc(str(col2_name))}: {_esc(str(col2_val))}")
            rows.append(f"<tr><td>{safe_name}</td><td>{c1}</td><td>{c2}</td></tr>")
        else:
            rows.append(f"<tr><td>{safe_name}</td><td colspan='2'>{_esc(str(metrics))}</td></tr>")
    return "\n".join(rows)


def _build_html_report(state: AutoDSState, out_dir: Path) -> Path:
    """Build an interactive Bootstrap HTML report from pipeline state.

    Args:
        state: Current pipeline state.
        out_dir: Output directory for the report file.

    Returns:
        Path to the written report.html file.
    """
    _esc = html_mod.escape
    session_id = _esc(str(state.get("session_id", "unknown")))
    domain = state.get("detected_domain", "generic")
    style = _domain_style(domain)
    user_mode = _esc(str(state.get("user_mode", "auto")))
    target = _esc(str(state.get("target_column", "N/A")))
    problem_type = _esc(str(state.get("problem_type", "N/A")))
    row_count = state.get("row_count", 0)
    col_count = state.get("column_count", 0)
    best_model = _esc(str(_safe_get(state, "best_model", "best_model_name", default="N/A")))
    eda_summary = _esc(str(state.get("eda_summary") or "No EDA summary available."))
    model_results = state.get("model_results") or {}
    quality_issues = state.get("quality_issues") or []
    features = _safe_get(state, "feature_list", "features_selected", default=[])
    shap = _safe_get(state, "shap_values", "shap_summary", default=None)
    fairness = state.get("fairness_report")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    shap_section = ""
    if shap:
        shap_snippet = html_mod.escape(json.dumps(shap, default=str)[:2000])
        shap_section = f"""
  <div class="section">
    <h2>SHAP Feature Importance</h2>
    <pre class="code-block">{shap_snippet}</pre>
  </div>"""

    fairness_section = ""
    if fairness:
        fairness_snippet = html_mod.escape(json.dumps(fairness, default=str)[:2000])
        fairness_section = f"""
  <div class="section">
    <h2>Fairness Report</h2>
    <pre class="code-block">{fairness_snippet}</pre>
  </div>"""

    quality_html = "".join(
        f"<li>{_esc(str(q.get('issue', str(q))) if isinstance(q, dict) else str(q))}</li>"
        for q in quality_issues[:10]
    ) or "<li>No significant quality issues detected.</li>"

    feature_html = "".join(
        f"<li><code>{_esc(str(f))}</code></li>" for f in features[:20]
    ) or "<li>Feature list not available.</li>"

    model_rows = _build_model_rows(model_results)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AutoDS Report — {session_id}</title>
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f8f9fa; }}
  .domain-badge {{ background: {style["color"]}; color: #fff; padding: 4px 14px;
    border-radius: 20px; font-weight: 600; font-size: .85rem; display: inline-block; }}
  .header-bar {{ background: {style["color"]}; color: #fff; padding: 2rem;
    margin-bottom: 2rem; }}
  .section {{ background: #fff; border-radius: 8px; padding: 1.5rem;
    margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .metric-card {{ background: {style["color"]}18; border-left: 4px solid {style["color"]};
    padding: 1rem; border-radius: 6px; }}
  .code-block {{ background: #f1f3f5; padding: 1rem; border-radius: 6px;
    font-size: .8rem; overflow-x: auto; max-height: 300px; }}
  footer {{ text-align: center; color: #868e96; margin: 2rem 0; font-size: .8rem; }}
</style>
</head>
<body>
<div class="header-bar">
  <div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <h1 class="mb-1">AutoDS Analysis Report</h1>
        <p class="mb-0 opacity-75">Session: {session_id} &nbsp;|&nbsp; {generated_at}</p>
      </div>
      <span class="domain-badge">{style["icon"]} {style["label"]}</span>
    </div>
  </div>
</div>
<div class="container-fluid px-4">
  <div class="section">
    <h2>Executive Summary</h2>
    <div class="row g-3">
      <div class="col-md-3"><div class="metric-card">
        <small class="text-muted">Domain</small>
        <div class="fw-bold">{style["label"]}</div>
      </div></div>
      <div class="col-md-3"><div class="metric-card">
        <small class="text-muted">Mode</small>
        <div class="fw-bold">{user_mode.title()}</div>
      </div></div>
      <div class="col-md-3"><div class="metric-card">
        <small class="text-muted">Best Model</small>
        <div class="fw-bold">{best_model}</div>
      </div></div>
      <div class="col-md-3"><div class="metric-card">
        <small class="text-muted">Problem Type</small>
        <div class="fw-bold">{problem_type.title()}</div>
      </div></div>
    </div>
  </div>
  <div class="section">
    <h2>Data Overview</h2>
    <table class="table table-sm table-bordered">
      <thead class="table-light">
        <tr><th>Property</th><th>Value</th></tr>
      </thead>
      <tbody>
        <tr><td>Rows</td><td>{row_count:,}</td></tr>
        <tr><td>Columns</td><td>{col_count}</td></tr>
        <tr><td>Target Column</td><td><code>{target}</code></td></tr>
        <tr><td>Problem Type</td><td>{problem_type}</td></tr>
        <tr><td>Features Used</td><td>{len(features)}</td></tr>
      </tbody>
    </table>
    <h5 class="mt-3">Data Quality Issues</h5>
    <ul>{quality_html}</ul>
  </div>
  <div class="section">
    <h2>EDA Findings</h2>
    <p>{eda_summary}</p>
    <h5>Features in Final Model</h5>
    <ul>{feature_html}</ul>
  </div>
  <div class="section">
    <h2>Model Results</h2>
    <p>Best model: <strong>{best_model}</strong></p>
    <table class="table table-sm table-bordered table-hover">
      <thead class="table-light">
        <tr><th>Model</th><th>Primary Metric</th><th>Secondary Metric</th></tr>
      </thead>
      <tbody>{model_rows}</tbody>
    </table>
  </div>
  {shap_section}
  {fairness_section}
</div>
<footer>Generated by AutoDS — Autonomous Data Science Platform</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    out_path = out_dir / "report.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("HTML report written to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Executive Summary
# ---------------------------------------------------------------------------
def _build_executive_summary(state: AutoDSState, out_dir: Path) -> Path:
    """Build a 1-page executive summary HTML for stakeholders.

    Args:
        state: Current pipeline state.
        out_dir: Output directory.

    Returns:
        Path to the written executive_summary.html file.
    """
    _esc = html_mod.escape
    domain = state.get("detected_domain", "generic")
    style = _domain_style(domain)
    best_model = _esc(str(_safe_get(state, "best_model", "best_model_name", default="N/A")))
    model_results = state.get("model_results") or {}
    target = _esc(str(state.get("target_column", "N/A")))
    row_count = state.get("row_count", 0)
    col_count = state.get("column_count", 0)
    eda_insights = state.get("eda_insights") or []
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    domain_cfg = state.get("domain_config") or {}
    term_map = domain_cfg.get("terminology_map", {})
    user_label = _esc(term_map.get("user", "record"))
    prediction_label = _esc(term_map.get("prediction", "prediction"))

    top_metrics_html = ""
    if isinstance(model_results.get(best_model), dict):
        metrics = model_results[best_model]
        top_metrics_html = "".join(
            f"<li><strong>{k}</strong>: {v:.4f}</li>" if isinstance(v, float)
            else f"<li><strong>{k}</strong>: {v}</li>"
            for k, v in list(metrics.items())[:3]
        )

    insights_html = "".join(
        f"<li>{_esc(str(ins))}</li>" for ins in eda_insights[:3]
    ) or "<li>Review the full report for detailed findings.</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Executive Summary — AutoDS</title>
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px;
    margin: 0 auto; padding: 2rem; }}
  .domain-bar {{ background: {style["color"]}; color: #fff; padding: 1rem 2rem;
    border-radius: 8px; margin-bottom: 1.5rem; }}
</style>
</head>
<body>
<div class="domain-bar">
  <h2 class="mb-0">Executive Summary — {style["label"]} Analysis</h2>
  <small>{generated_at}</small>
</div>
<h4>What Was Analyzed</h4>
<p>A dataset of <strong>{row_count:,} {user_label}s</strong> with
   <strong>{col_count} variables</strong> was analysed to predict
   <strong>{target}</strong>.</p>
<h4>Best Model: {best_model}</h4>
<ul>{top_metrics_html or "<li>See full report for metrics.</li>"}</ul>
<h4>Top 3 Actionable Insights</h4>
<ol>{insights_html}</ol>
<h4>Recommended Next Steps</h4>
<ul>
  <li>Review the full HTML report for detailed {prediction_label} analysis.</li>
  <li>Validate model performance on a held-out test set before deployment.</li>
  <li>Examine SHAP values to understand the key drivers of {prediction_label}.</li>
</ul>
<footer class="mt-4 text-muted small">
  Generated by AutoDS — Autonomous Data Science Platform
</footer>
</body>
</html>"""

    out_path = out_dir / "executive_summary.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Executive summary written to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Jupyter Notebook
# ---------------------------------------------------------------------------
def _build_notebook(state: AutoDSState, out_dir: Path) -> Path:
    """Build a runnable Jupyter notebook from pipeline state.

    Args:
        state: Current pipeline state.
        out_dir: Output directory.

    Returns:
        Path to the written .ipynb file.
    """
    try:
        import nbformat
    except ImportError as exc:
        raise ImportError(
            "nbformat is required for notebook generation. Install: pip install nbformat"
        ) from exc

    target = state.get("target_column", "target")
    features: list[str] = _safe_get(state, "feature_list", "features_selected", default=[])
    best_model = _safe_get(state, "best_model", "best_model_name", default="best_model")
    model_path = state.get("best_model_path", "model.pkl")
    problem_type = state.get("problem_type", "classification")
    model_results = state.get("model_results") or {}

    eval_code = (
        "    from sklearn.metrics import classification_report\n"
        "    print(classification_report(y_test, preds))"
        if problem_type == "classification"
        else
        "    from sklearn.metrics import mean_absolute_error, r2_score\n"
        "    print(f'MAE: {mean_absolute_error(y_test, preds):.4f}')\n"
        "    print(f'R2:  {r2_score(y_test, preds):.4f}')"
    )

    cells = [
        nbformat.v4.new_markdown_cell(
            f"# AutoDS Analysis Notebook\n\n"
            f"Session: `{state.get('session_id', 'N/A')}`  \n"
            f"Domain: **{state.get('detected_domain', 'generic').title()}** | "
            f"Problem: **{problem_type.title()}** | Target: `{target}`"
        ),
        nbformat.v4.new_code_cell(
            "import pandas as pd\nimport numpy as np\nimport joblib\n"
            "import matplotlib.pyplot as plt\nimport warnings\n"
            "warnings.filterwarnings('ignore')\n%matplotlib inline"
        ),
        nbformat.v4.new_markdown_cell("## 1. Data Loading"),
        nbformat.v4.new_code_cell(
            "# Replace with your actual data path\n"
            "df = pd.read_csv('data/dataset.csv')\n"
            "print(f'Shape: {df.shape}')\ndf.head()"
        ),
        nbformat.v4.new_markdown_cell("## 2. Data Profiling"),
        nbformat.v4.new_code_cell(
            "print('=== Data Types ===')\nprint(df.dtypes)\n"
            "print('\\n=== Missing Values ===')\nprint(df.isnull().sum())\n"
            "print('\\n=== Descriptive Statistics ===')\ndf.describe()"
        ),
        nbformat.v4.new_markdown_cell("## 3. EDA"),
        nbformat.v4.new_code_cell(
            f"if '{target}' in df.columns:\n"
            f"    df['{target}'].value_counts().plot(kind='bar', title='Target Distribution')\n"
            "    plt.tight_layout()\n    plt.show()"
        ),
        nbformat.v4.new_markdown_cell("## 4. Feature Engineering"),
        nbformat.v4.new_code_cell(
            f"FEATURES = {json.dumps(features[:30])}\n"
            f"TARGET = '{target}'\n\n"
            "available = [c for c in FEATURES if c in df.columns]\n"
            "X = df[available]\n"
            "y = df[TARGET] if TARGET in df.columns else None\n"
            "print(f'Features: {len(available)}, Rows: {len(X)}')"
        ),
        nbformat.v4.new_markdown_cell("## 5. Model Loading and Evaluation"),
        nbformat.v4.new_code_cell(
            f"model_path = r'{model_path}'\n"
            "try:\n"
            "    model = joblib.load(model_path)\n"
            "    print(f'Loaded: {type(model).__name__}')\n"
            "except FileNotFoundError:\n"
            "    print('Model file not found — train the model first.')\n"
            "    model = None"
        ),
        nbformat.v4.new_code_cell(
            "if model is not None and y is not None:\n"
            "    from sklearn.model_selection import train_test_split\n"
            "    X_train, X_test, y_train, y_test = train_test_split(\n"
            "        X, y, test_size=0.2, random_state=42)\n"
            "    preds = model.predict(X_test)\n" + eval_code
        ),
        nbformat.v4.new_markdown_cell("## 6. AutoDS Model Comparison"),
        nbformat.v4.new_code_cell(
            f"model_results = {json.dumps(model_results, default=str)}\n"
            "for name, metrics in model_results.items():\n"
            "    print(f'{name}: {metrics}')"
        ),
    ]

    nb = nbformat.v4.new_notebook(cells=cells)
    out_path = out_dir / "analysis_notebook.ipynb"
    with open(out_path, "w", encoding="utf-8") as fh:
        nbformat.write(nb, fh)
    logger.info("Jupyter notebook written to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# ZIP Package
# ---------------------------------------------------------------------------
def _build_zip(paths: list[Path], out_dir: Path) -> Path:
    """Bundle all generated report files into a ZIP archive.

    Args:
        paths: List of file paths to include.
        out_dir: Output directory for the ZIP file.

    Returns:
        Path to the written ZIP file.
    """
    zip_path = out_dir / "analysis_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            if p.exists():
                zf.write(p, arcname=p.name)
    logger.info("ZIP package written to %s", zip_path)
    return zip_path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_reports(state: AutoDSState) -> AutoDSState:
    """Generate all report formats and update state with file paths.

    Each format (HTML, executive summary, notebook, ZIP) is attempted
    independently — a failure in one does not prevent the others.

    Writes to: outputs/{session_id}/reports/

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with report_paths, report_generated, and workflow_status.
    """
    state["current_step"] = "report"
    state["completed_steps"] = state.get("completed_steps", []) + ["report"]

    session_id = state.get("session_id", "session_unknown")
    out_dir = Path("outputs") / session_id / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    report_paths: dict[str, str] = {}
    generated_files: list[Path] = []

    try:
        html_path = _build_html_report(state, out_dir)
        report_paths["html"] = str(html_path)
        generated_files.append(html_path)
    except Exception as exc:
        logger.error("HTML report failed: %s", exc, exc_info=True)
        state["errors"] = state.get("errors", []) + [
            {"step": "report", "type": "html_report_failed", "detail": str(exc)}
        ]

    try:
        exec_path = _build_executive_summary(state, out_dir)
        report_paths["executive_summary"] = str(exec_path)
        generated_files.append(exec_path)
    except Exception as exc:
        logger.error("Executive summary failed: %s", exc, exc_info=True)
        state["errors"] = state.get("errors", []) + [
            {"step": "report", "type": "executive_summary_failed", "detail": str(exc)}
        ]

    try:
        nb_path = _build_notebook(state, out_dir)
        report_paths["notebook"] = str(nb_path)
        generated_files.append(nb_path)
    except Exception as exc:
        logger.error("Notebook generation failed: %s", exc, exc_info=True)
        state["errors"] = state.get("errors", []) + [
            {"step": "report", "type": "notebook_failed", "detail": str(exc)}
        ]

    if generated_files:
        try:
            zip_path = _build_zip(generated_files, out_dir)
            report_paths["zip"] = str(zip_path)
        except Exception as exc:
            logger.error("ZIP packaging failed: %s", exc, exc_info=True)
            state["errors"] = state.get("errors", []) + [
                {"step": "report", "type": "zip_failed", "detail": str(exc)}
            ]

    state["report_paths"] = report_paths
    state["report_generated"] = bool(report_paths)
    state["workflow_status"] = "completed"
    logger.info("Report generation complete. Formats: %s", list(report_paths.keys()))
    return state
