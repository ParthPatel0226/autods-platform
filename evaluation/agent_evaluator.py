"""Evaluation: agent_evaluator

Evaluates agent decision quality on known datasets with expected outcomes.
Accepts plain dicts — compatible with AutoDSState without a hard import.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

_ERROR_METRICS = frozenset(
    {"rmse", "mae", "mape", "mse", "median_absolute_error", "max_error"}
)


@dataclass(frozen=True)
class EvaluationCase:
    """Immutable ground-truth spec for one benchmark dataset.

    Attributes:
        dataset_name: Human-readable label.
        dataset_path: Path under ``evaluation/test_datasets/``.
        domain: Expected industry domain string.
        problem_type: "classification", "regression", or "clustering".
        expected_target: Target column the orchestrator should propose.
        expected_issues: Quality issues the profiler must detect.
        expected_algorithms: Acceptable algorithm keys (at least one required).
        baseline_metric: Known-good metric value from a hand-tuned pipeline.
        baseline_metric_name: Metric key (e.g. "f1", "roc_auc", "rmse").
    """

    dataset_name: str
    dataset_path: str
    domain: str
    problem_type: str
    expected_target: str
    expected_issues: list[str]
    expected_algorithms: list[str]
    baseline_metric: float
    baseline_metric_name: str


def evaluate_orchestrator(state: dict[str, Any], case: EvaluationCase) -> dict[str, Any]:
    """Evaluate orchestrator problem-type and target-column decisions.

    Args:
        state: Pipeline state after orchestrator ran. Keys: ``problem_type``,
            ``target_column``.
        case: Known-good evaluation case.

    Returns:
        Dict: problem_type_correct, target_correct, detected values, expected
        values, dataset_name, agent, score (0-100, 50 pts per dimension).
    """
    det_type: str = state.get("problem_type", "")
    det_target: str | None = state.get("target_column")
    type_ok = det_type == case.problem_type
    target_ok = (
        det_target is not None
        and det_target.strip().lower() == case.expected_target.strip().lower()
    )
    score = (50.0 if type_ok else 0.0) + (50.0 if target_ok else 0.0)
    logger.info(
        "Orchestrator eval [%s]: type=%s target=%s score=%.0f",
        case.dataset_name, "OK" if type_ok else "MISS",
        "OK" if target_ok else "MISS", score,
    )
    return {
        "dataset_name": case.dataset_name, "agent": "orchestrator",
        "problem_type_correct": type_ok, "target_correct": target_ok,
        "detected_problem_type": det_type, "detected_target": det_target,
        "expected_problem_type": case.problem_type,
        "expected_target": case.expected_target, "score": score,
    }


def evaluate_profiler(state: dict[str, Any], case: EvaluationCase) -> dict[str, Any]:
    """Evaluate profiler issue-detection quality via precision/recall/F1.

    Args:
        state: Pipeline state after data_profiler ran. Expects
            ``data_profile["issues"]`` — list of detected issue strings.
        case: Known-good evaluation case.

    Returns:
        Dict: issues_detected, issues_missed, false_positives, precision,
        recall, score (0-100 F1-scaled), dataset_name, agent.
    """
    raw: list[str] = (state.get("data_profile") or {}).get("issues", [])
    det = {i.strip().lower() for i in raw}
    exp = {i.strip().lower() for i in case.expected_issues}
    tp = det & exp
    issues_detected = [i for i in raw if i.strip().lower() in tp]
    false_positives = [i for i in raw if i.strip().lower() in (det - exp)]
    issues_missed = list(exp - det)
    precision = len(tp) / len(det) if det else 0.0
    recall = len(tp) / len(exp) if exp else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    score = round(f1 * 100.0, 2)
    logger.info(
        "Profiler eval [%s]: p=%.2f r=%.2f score=%.0f",
        case.dataset_name, precision, recall, score,
    )
    return {
        "dataset_name": case.dataset_name, "agent": "data_profiler",
        "issues_detected": issues_detected, "issues_missed": issues_missed,
        "false_positives": false_positives,
        "precision": round(precision, 4), "recall": round(recall, 4), "score": score,
    }


def evaluate_model_selection(state: dict[str, Any], case: EvaluationCase) -> dict[str, Any]:
    """Evaluate modeling agent algorithm selection and metric vs. baseline.

    Args:
        state: Pipeline state after modeling ran. Expected keys:
            ``model_choices["algorithms"]``, ``model_results``, ``best_model``.
        case: Known-good evaluation case.

    Returns:
        Dict: algorithms_selected, reasonable, beats_baseline, metric_value,
        baseline_value, baseline_metric_name, score (0-100), dataset_name,
        agent.
    """
    choices: dict[str, Any] = state.get("model_choices") or {}
    results: dict[str, Any] = state.get("model_results") or {}
    best: str = state.get("best_model") or ""
    algos: list[str] = choices.get("algorithms", []) or list(results.keys())
    reasonable = bool(
        {a.strip().lower() for a in algos}
        & {a.strip().lower() for a in case.expected_algorithms}
    )
    metric: float | None = None
    if best and best in results:
        m = results[best]
        if isinstance(m, dict):
            metric = m.get(case.baseline_metric_name)
    if metric is None:
        for m in results.values():
            if isinstance(m, dict) and case.baseline_metric_name in m:
                c = m[case.baseline_metric_name]
                metric = c if metric is None or c > metric else metric
    is_err = case.baseline_metric_name.lower() in _ERROR_METRICS
    beats = (
        (metric <= case.baseline_metric if is_err else metric >= case.baseline_metric)
        if metric is not None else False
    )
    score = (50.0 if reasonable else 0.0) + (50.0 if beats else 0.0)
    logger.info(
        "Model eval [%s]: reasonable=%s beats=%s score=%.0f",
        case.dataset_name, reasonable, beats, score,
    )
    return {
        "dataset_name": case.dataset_name, "agent": "modeling_agent",
        "algorithms_selected": algos, "reasonable": reasonable,
        "beats_baseline": beats, "metric_value": metric,
        "baseline_value": case.baseline_metric,
        "baseline_metric_name": case.baseline_metric_name, "score": score,
    }


def run_evaluation_suite(
    cases: list[EvaluationCase],
    pipeline_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Run the full evaluation suite across multiple test cases.

    Args:
        cases: Evaluation cases to test.
        pipeline_fn: Callable(dataset_path) -> state dict. Exceptions are
            caught, logged, and recorded as failures (score 0).

    Returns:
        Dict: overall_score, per_case_results, summary_table, total_cases,
        successful_cases, evaluated_at (ISO-8601 UTC).
    """
    per_case: list[dict[str, Any]] = []
    table: list[dict[str, Any]] = []
    total_score = 0.0
    successful = 0
    for case in cases:
        logger.info("Evaluating: %s", case.dataset_name)
        cr: dict[str, Any] = {
            "dataset_name": case.dataset_name, "domain": case.domain,
            "problem_type": case.problem_type, "error": None,
        }
        try:
            st = pipeline_fn(case.dataset_path)
            orch = evaluate_orchestrator(st, case)
            prof = evaluate_profiler(st, case)
            mod = evaluate_model_selection(st, case)
            cs = round((orch["score"] + prof["score"] + mod["score"]) / 3.0, 2)
            cr.update({"orchestrator": orch, "profiler": prof,
                        "model_selection": mod, "case_score": cs})
            total_score += cs
            successful += 1
        except Exception as exc:
            logger.exception("Failed [%s]: %s", case.dataset_name, exc)
            cr["error"] = str(exc)
            cr["case_score"] = 0.0
        per_case.append(cr)
        table.append({
            "Dataset": case.dataset_name, "Domain": case.domain,
            "Problem Type": case.problem_type,
            "Score": cr.get("case_score", 0.0),
            "Orchestrator Score": cr.get("orchestrator", {}).get("score", "—"),
            "Profiler Score": cr.get("profiler", {}).get("score", "—"),
            "Model Score": cr.get("model_selection", {}).get("score", "—"),
            "Error": cr.get("error") or "",
        })
    overall = round(total_score / len(cases), 2) if cases else 0.0
    logger.info("Suite done: %d/%d ok, overall=%.1f", successful, len(cases), overall)
    return {
        "overall_score": overall, "per_case_results": per_case,
        "summary_table": table, "total_cases": len(cases),
        "successful_cases": successful,
        "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# Compact tuple format: (name, path, domain, ptype, target, issues, algos, baseline, metric)
_BUILTIN_CASES_DATA: list[tuple] = [
    ("Titanic (Survival)", "evaluation/test_datasets/titanic.csv",
     "generic", "classification", "survived",
     ["high_missing", "class_imbalance"],
     ["logistic_regression", "random_forest", "xgboost", "gradient_boosting", "decision_tree"],
     0.80, "f1"),
    ("Heart Disease (UCI)", "evaluation/test_datasets/heart_disease.csv",
     "healthcare", "classification", "target",
     ["class_imbalance", "outliers"],
     ["logistic_regression", "random_forest", "xgboost", "lightgbm", "svm"],
     0.85, "roc_auc"),
    ("Boston Housing", "evaluation/test_datasets/boston_housing.csv",
     "generic", "regression", "medv",
     ["outliers", "skewed_features"],
     ["random_forest", "xgboost", "gradient_boosting", "linear_regression", "ridge"],
     3.5, "rmse"),
    ("Customer Churn (Telco)", "evaluation/test_datasets/customer_churn.csv",
     "ecommerce", "classification", "churn",
     ["class_imbalance", "high_cardinality"],
     ["xgboost", "lightgbm", "random_forest", "logistic_regression", "gradient_boosting"],
     0.78, "f1"),
    ("Credit Default (UCI)", "evaluation/test_datasets/credit_default.csv",
     "finance", "classification", "default",
     ["class_imbalance", "high_missing", "outliers"],
     ["logistic_regression", "xgboost", "lightgbm", "random_forest", "gradient_boosting"],
     0.77, "roc_auc"),
]


def get_builtin_cases() -> list[EvaluationCase]:
    """Return the five built-in benchmark evaluation cases.

    Covers Titanic, Heart Disease, Boston Housing, Customer Churn, and Credit
    Default. Dataset files under ``evaluation/test_datasets/`` are not required
    on disk — cases define expected outcomes only.

    Returns:
        List of frozen EvaluationCase instances.
    """
    return [
        EvaluationCase(
            dataset_name=d[0], dataset_path=d[1], domain=d[2],
            problem_type=d[3], expected_target=d[4], expected_issues=d[5],
            expected_algorithms=d[6], baseline_metric=d[7],
            baseline_metric_name=d[8],
        )
        for d in _BUILTIN_CASES_DATA
    ]


def _fmt_val(v: Any) -> str:
    """Format a table cell value for markdown output."""
    return f"{v:.1f}" if isinstance(v, float) else ("—" if v is None else str(v))


def _case_detail_lines(cr: dict[str, Any]) -> list[str]:
    """Build per-case detail lines for the markdown report."""
    o = cr.get("orchestrator", {})
    p = cr.get("profiler", {})
    m = cr.get("model_selection", {})
    mv = m.get("metric_value")
    return [
        "**Orchestrator**",
        f"- Problem type: {o.get('problem_type_correct')} "
        f"(`{o.get('detected_problem_type')}` vs `{o.get('expected_problem_type')}`)",
        f"- Target: {o.get('target_correct')} "
        f"(`{o.get('detected_target')}` vs `{o.get('expected_target')}`)",
        f"- Score: {o.get('score', 0.0):.0f} / 100", "",
        "**Data Profiler**",
        f"- Precision: {p.get('precision', 0.0):.2f}  Recall: {p.get('recall', 0.0):.2f}",
        f"- Detected: {', '.join(p.get('issues_detected', [])) or 'none'}",
        f"- Missed: {', '.join(p.get('issues_missed', [])) or 'none'}",
        f"- False positives: {', '.join(p.get('false_positives', [])) or 'none'}",
        f"- Score: {p.get('score', 0.0):.0f} / 100", "",
        "**Modeling Agent**",
        f"- Algorithms: {', '.join(m.get('algorithms_selected', [])) or 'none'}",
        f"- Reasonable: {m.get('reasonable')}  Beats baseline: {m.get('beats_baseline')}",
        f"- {m.get('baseline_metric_name')} "
        f"{f'{mv:.4f}' if mv is not None else 'N/A'} vs "
        f"baseline {m.get('baseline_value', 0.0):.4f}",
        f"- Score: {m.get('score', 0.0):.0f} / 100", "",
    ]


def generate_report(results: dict[str, Any]) -> str:
    """Generate a markdown summary of evaluation suite results.

    Args:
        results: Output of :func:`run_evaluation_suite`.

    Returns:
        Markdown-formatted string for display or file export.
    """
    overall = results.get("overall_score", 0.0)
    rating = ("EXCELLENT" if overall >= 85 else "GOOD" if overall >= 70
              else "FAIR" if overall >= 50 else "NEEDS IMPROVEMENT")
    lines = [
        "# AutoDS Agent Evaluation Report", "",
        f"**Evaluated at:** {results.get('evaluated_at', '')}",
        f"**Cases run:** {results.get('successful_cases', 0)} / {results.get('total_cases', 0)}",
        f"**Overall Score:** {overall:.1f} / 100  ({rating})",
        "", "---", "", "## Summary Table", "",
        "| Dataset | Domain | Problem Type | Score | Orchestrator | Profiler | Model |",
        "|---------|--------|-------------|-------|-------------|---------|-------|",
    ]
    for row in results.get("summary_table", []):
        lines.append(
            f"| {row.get('Dataset','')} | {row.get('Domain','')} "
            f"| {row.get('Problem Type','')} | {_fmt_val(row.get('Score'))} "
            f"| {_fmt_val(row.get('Orchestrator Score'))} "
            f"| {_fmt_val(row.get('Profiler Score'))} "
            f"| {_fmt_val(row.get('Model Score'))} |"
        )
    lines += ["", "---", "", "## Per-Case Details", ""]
    for cr in results.get("per_case_results", []):
        lines.append(f"### {cr.get('dataset_name','?')}  (score: {cr.get('case_score',0.0):.1f})\n")
        if cr.get("error"):
            lines += [f"**ERROR:** {cr['error']}", ""]
        else:
            lines += _case_detail_lines(cr)
    lines += ["---", "", "*Report generated by AutoDS Agent Evaluator*"]
    return "\n".join(lines)
