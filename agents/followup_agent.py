"""Follow-Up Agent.

Handles post-pipeline conversational queries from the user. Detects intent
from the question and routes to the appropriate tool or analysis function.

Supported intents:
    correlation      — Pearson/Spearman correlation between two features
    distribution     — Histogram / value-counts for a feature
    prediction       — Info about the best model + how to predict
    feature_importance — Ranked feature importance from best model
    model_comparison — Side-by-side comparison of all trained models
    data_query       — Run a DuckDB query on the current dataset
    what_if          — (future) What-if scenario analysis
    statistical_test — Run a t-test or chi-square test on two columns
"""

from __future__ import annotations

import logging
import re

from core.state import AutoDSState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[str, list[str]] = {
    "correlation": [
        r"correlat", r"relation(ship)?", r"associat", r"linked?", r"depend",
    ],
    "distribution": [
        r"distribut", r"histogram", r"spread", r"range", r"value.?count",
        r"how.+look", r"show.+column",
    ],
    "prediction": [
        r"predict", r"forecast", r"classif", r"probabilit", r"score",
        r"inference", r"model.+output",
    ],
    "feature_importance": [
        r"feature.+import", r"import.+feature", r"which.+feature",
        r"top.+feature", r"variable.+import", r"most.+important",
    ],
    "model_comparison": [
        r"compare.+model", r"model.+comparison", r"best.+model",
        r"model.+perform", r"all.+model", r"which.+model",
    ],
    "data_query": [
        r"query", r"sql", r"select", r"filter", r"show.+row", r"how.+many",
        r"count", r"average", r"mean", r"sum.+of",
    ],
    "what_if": [
        r"what.+if", r"what.+happen", r"change.+value", r"if.+i.+set",
        r"scenario",
    ],
    "statistical_test": [
        r"t.?test", r"chi.?square", r"significance", r"p.?value",
        r"hypothesis", r"statistic(al)?.+test",
    ],
}

_CAPABILITIES_SUMMARY = (
    "I can help you with:\n"
    "- **Correlations** between features (`correlate age and income`)\n"
    "- **Distributions** of a column (`show distribution of salary`)\n"
    "- **Feature importance** from the trained model\n"
    "- **Model comparison** across all trained models\n"
    "- **Data queries** (`average purchase_amount by region`)\n"
    "- **Statistical tests** (`t-test between age and churn`)\n"
    "- **Prediction info** about the best model\n"
)


def _detect_intent(question: str) -> str:
    """Detect the intent of the user's question using keyword matching."""
    lowered = question.lower()
    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return intent
    return "unknown"


def _extract_columns(question: str, feature_list: list[str]) -> list[str]:
    """Find feature names mentioned in the question."""
    lowered = question.lower()
    return [f for f in feature_list if f.lower() in lowered]


def _format_model_comparison(model_results: dict) -> str:
    """Format model results as a markdown comparison table."""
    if not model_results:
        return "No model results available."

    all_metrics: set[str] = set()
    for res in model_results.values():
        if isinstance(res, dict):
            all_metrics.update(res.get("metrics", {}).keys())

    metric_cols = sorted(all_metrics)
    header = "| Model | " + " | ".join(metric_cols) + " |"
    separator = "|---|" + "|".join(["---"] * len(metric_cols)) + "|"
    rows = [header, separator]

    for model_name, res in model_results.items():
        if not isinstance(res, dict):
            continue
        metrics = res.get("metrics", {})
        values = " | ".join(
            f"{metrics.get(m, 'N/A'):.4f}" if isinstance(metrics.get(m), float) else str(metrics.get(m, "N/A"))
            for m in metric_cols
        )
        rows.append(f"| {model_name} | {values} |")

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------

def _handle_correlation(question: str, state: AutoDSState) -> dict:
    """Compute Pearson/Spearman correlation between two mentioned features."""
    from agents.tools.stats_tools import correlation_pearson, correlation_spearman
    from agents.tools.data_tools import query_duckdb

    feature_list: list[str] = state.get("feature_list", [])
    columns = _extract_columns(question, feature_list)
    table = state.get("joined_data_ref", "")

    if len(columns) < 2:
        return {
            "response": (
                f"Please mention two column names for the correlation. "
                f"Available features: {', '.join(feature_list[:10])}."
            ),
            "charts": [],
            "data": None,
            "action_taken": "correlation_no_columns",
        }

    col_a, col_b = columns[0], columns[1]
    try:
        df = query_duckdb(f"SELECT * FROM {table}") if table else None
        if df is None or df.empty:
            return {"response": "No dataset loaded.", "charts": [], "data": None, "action_taken": "correlation_error"}
        pearson = correlation_pearson(df, col_a, col_b)
        spearman = correlation_spearman(df, col_a, col_b)
        response = (
            f"**Correlation: `{col_a}` vs `{col_b}`**\n\n"
            f"- Pearson r = **{pearson.get('coefficient', 'N/A'):.4f}** "
            f"(p = {pearson.get('p_value', 'N/A'):.4g})\n"
            f"- Spearman \u03c1 = **{spearman.get('coefficient', 'N/A'):.4f}** "
            f"(p = {spearman.get('p_value', 'N/A'):.4g})\n\n"
            f"{pearson.get('interpretation', '')}"
        )
        return {"response": response, "charts": [], "data": {"pearson": pearson, "spearman": spearman}, "action_taken": "correlation"}
    except Exception as exc:
        logger.warning("Correlation failed for %s vs %s: %s", col_a, col_b, exc)
        return {"response": f"Could not compute correlation: {exc}", "charts": [], "data": None, "action_taken": "correlation_error"}


def _handle_distribution(question: str, state: AutoDSState) -> dict:
    """Return distribution chart spec for a feature."""
    feature_list: list[str] = state.get("feature_list", [])
    columns = _extract_columns(question, feature_list)
    table = state.get("joined_data_ref", "")

    if not columns:
        return {
            "response": (
                f"Please mention a column name. "
                f"Available: {', '.join(feature_list[:10])}."
            ),
            "charts": [],
            "data": None,
            "action_taken": "distribution_no_column",
        }

    col = columns[0]
    chart_spec = {
        "type": "histogram",
        "table": table,
        "column": col,
        "title": f"Distribution of {col}",
    }
    response = f"**Distribution of `{col}`**\n\nHistogram chart prepared for `{col}`."
    return {"response": response, "charts": [chart_spec], "data": None, "action_taken": "distribution"}


def _handle_prediction(state: AutoDSState) -> dict:
    """Return info about the best model and how to make predictions."""
    best = state.get("best_model_name", state.get("best_model", ""))
    model_path = state.get("best_model_path", "")
    target = state.get("target_column", "unknown target")
    problem_type = state.get("problem_type", "unknown")

    if not best:
        return {"response": "No trained model found. Run the modeling step first.", "charts": [], "data": None, "action_taken": "prediction_no_model"}

    response = (
        f"**Best Model: {best}** ({problem_type})\n\n"
        f"Target variable: `{target}`\n"
        f"Model saved at: `{model_path}`\n\n"
        f"To make predictions:\n"
        f"1. Go to the **Predict** page in the dashboard\n"
        f"2. Upload a CSV with the same feature columns\n"
        f"3. Download results with predictions appended\n\n"
        f"For single-row prediction, use the what-if tool with specific feature values."
    )
    return {"response": response, "charts": [], "data": {"best_model": best, "model_path": model_path}, "action_taken": "prediction_info"}


def _handle_feature_importance(state: AutoDSState) -> dict:
    """Return feature importance from the best model."""
    best = state.get("best_model_name", state.get("best_model", ""))
    model_results: dict = state.get("model_results", state.get("trained_models", {}))

    if not best:
        return {"response": "Feature importance is not available. Run the modeling step first.", "charts": [], "data": None, "action_taken": "feature_importance_missing"}

    importance: dict = state.get("feature_importance") or {}
    if not importance:
        return {"response": f"Feature importance was not computed for {best}.", "charts": [], "data": None, "action_taken": "feature_importance_empty"}

    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    table_lines = ["| Rank | Feature | Importance |", "|---|---|---|"]
    for rank, (feat, score) in enumerate(sorted_features[:15], start=1):
        table_lines.append(f"| {rank} | {feat} | {score:.4f} |")
    response = f"**Feature Importance -- {best}**\n\n" + "\n".join(table_lines)
    return {"response": response, "charts": [], "data": dict(sorted_features), "action_taken": "feature_importance"}


def _handle_model_comparison(state: AutoDSState) -> dict:
    """Return a formatted comparison table for all trained models."""
    model_results: dict = state.get("model_results", state.get("trained_models", {}))
    table = _format_model_comparison(model_results)
    best = state.get("best_model_name", state.get("best_model", ""))
    response = f"**Model Comparison**\n\n{table}"
    if best:
        response += f"\n\nSelected best model: **{best}**"
    return {"response": response, "charts": [], "data": model_results, "action_taken": "model_comparison"}


def _handle_data_query(question: str, state: AutoDSState) -> dict:
    """Run a data query against DuckDB, selecting mentioned columns."""
    from agents.tools.data_tools import query_duckdb

    table = state.get("joined_data_ref", "")
    if not table:
        return {"response": "No dataset is currently loaded. Please upload data first.", "charts": [], "data": None, "action_taken": "data_query_no_table"}

    feature_list: list[str] = state.get("feature_list", [])
    columns = _extract_columns(question, feature_list)
    col_select = ", ".join(columns[:5]) if columns else "*"
    sql = f"SELECT {col_select} FROM {table} LIMIT 20"
    try:
        df = query_duckdb(sql, table_name=table)
        response = (
            f"**Query Results** (up to 20 rows)\n\n"
            f"SQL: `{sql}`\n\n"
            f"Returned {len(df)} rows and {len(df.columns)} columns."
        )
        return {"response": response, "charts": [], "data": df.to_dict(orient="records"), "action_taken": "data_query"}
    except Exception as exc:
        logger.warning("Data query failed: %s", exc)
        return {"response": f"Query failed: {exc}", "charts": [], "data": None, "action_taken": "data_query_error"}


def _handle_statistical_test(question: str, state: AutoDSState) -> dict:
    """Route to t-test or chi-square based on question content."""
    from agents.tools.stats_tools import t_test_independent, chi_square_test
    from agents.tools.data_tools import query_duckdb

    feature_list: list[str] = state.get("feature_list", [])
    columns = _extract_columns(question, feature_list)
    table = state.get("joined_data_ref", "")

    if len(columns) < 2:
        return {
            "response": f"Please mention two column names for the test. Available: {', '.join(feature_list[:10])}.",
            "charts": [], "data": None, "action_taken": "statistical_test_no_columns",
        }

    col_a, col_b = columns[0], columns[1]
    lowered = question.lower()
    try:
        df = query_duckdb(f"SELECT * FROM {table}") if table else None
        if df is None or df.empty:
            return {"response": "No dataset loaded.", "charts": [], "data": None, "action_taken": "statistical_test_error"}
        if "chi" in lowered or "categor" in lowered:
            result = chi_square_test(df, col_a, col_b)
            action = "chi_square_test"
        else:
            result = t_test_independent(df, col_a, col_b)
            action = "t_test"
        response = f"**Statistical Test: `{col_a}` vs `{col_b}`**\n\n{result.get('interpretation', str(result))}"
        return {"response": response, "charts": [], "data": result, "action_taken": action}
    except Exception as exc:
        logger.warning("Statistical test failed: %s", exc)
        return {"response": f"Statistical test failed: {exc}", "charts": [], "data": None, "action_taken": "statistical_test_error"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def handle_followup(state: AutoDSState, user_question: str) -> dict:
    """Handle a follow-up question from the user after the pipeline completes.

    Detects the user's intent via keyword matching and routes to the
    appropriate tool. Returns a structured response with optional chart
    specs and raw data.

    Args:
        state: Current AutoDS workflow state with all pipeline results.
        user_question: Raw question string from the user.

    Returns:
        Dict with keys:
            response (str): Markdown-formatted answer.
            charts (list): Chart specification dicts (may be empty).
            data (Any): Raw result data (may be None).
            action_taken (str): Identifier of the action performed.
    """
    logger.info("Follow-up question received: %s", user_question[:120])

    if not user_question or not user_question.strip():
        return {
            "response": "Please ask a question and I will do my best to help.\n\n" + _CAPABILITIES_SUMMARY,
            "charts": [], "data": None, "action_taken": "empty_question",
        }

    intent = _detect_intent(user_question)
    logger.debug("Detected intent: %s", intent)

    dispatch = {
        "correlation": lambda: _handle_correlation(user_question, state),
        "distribution": lambda: _handle_distribution(user_question, state),
        "prediction": lambda: _handle_prediction(state),
        "feature_importance": lambda: _handle_feature_importance(state),
        "model_comparison": lambda: _handle_model_comparison(state),
        "data_query": lambda: _handle_data_query(user_question, state),
        "statistical_test": lambda: _handle_statistical_test(user_question, state),
    }

    if intent in dispatch:
        return dispatch[intent]()

    # Default: return helpful overview with session context
    domain = state.get("detected_domain", "generic")
    best = state.get("best_model_name", state.get("best_model", ""))
    target = state.get("target_column", "")
    context_lines: list[str] = []
    if domain:
        context_lines.append(f"- Detected domain: **{domain}**")
    if target:
        context_lines.append(f"- Target variable: **{target}**")
    if best:
        context_lines.append(f"- Best model: **{best}**")
    context_block = "\n".join(context_lines) + "\n\n" if context_lines else ""
    response = f"I am not sure what you are looking for.\n\n{context_block}{_CAPABILITIES_SUMMARY}"
    return {"response": response, "charts": [], "data": None, "action_taken": "default_help"}
