"""EDA Agent.

Generates domain-aware exploratory data analysis with interactive questions
in Guided/Expert modes. Uses Python tools for computation, LLM for interpretation.

LangGraph nodes: generate_eda_questions and execute_eda.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from core.state import AutoDSState
from core.user_modes import (
    auto_select_best_option,
    filter_questions_for_mode,
    should_ask_questions,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared DataFrame loader (same logic as data_profiler)
# ---------------------------------------------------------------------------

def _get_working_df(state: AutoDSState) -> pd.DataFrame:
    """Retrieve the working DataFrame from DuckDB or the first data source."""
    joined_ref = state.get("joined_data_ref", "")
    if joined_ref:
        try:
            from agents.tools.data_tools import query_duckdb
            df = query_duckdb(f"SELECT * FROM {joined_ref}")
            if not df.empty:
                return df
        except Exception as exc:
            logger.warning("Failed to load from DuckDB table '%s': %s", joined_ref, exc)

    data_sources = state.get("data_sources", [])
    if data_sources:
        src = data_sources[0]
        source_path = src.get("source_path", "")
        fmt = src.get("format", "csv")
        if source_path:
            try:
                if fmt in ("csv", "tsv"):
                    return pd.read_csv(source_path)
                elif fmt in ("xlsx", "xls", "excel"):
                    return pd.read_excel(source_path)
                elif fmt == "parquet":
                    return pd.read_parquet(source_path)
                elif fmt == "json":
                    return pd.read_json(source_path)
                else:
                    return pd.read_csv(source_path)
            except Exception as exc:
                logger.warning("Failed to load data source '%s': %s", source_path, exc)

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Question builders
# ---------------------------------------------------------------------------

def _build_goal_question(state: AutoDSState) -> dict:
    """Build the primary analysis goal question."""
    has_target = bool(state.get("target_column"))
    recommended = "understand_target" if has_target else "comprehensive"

    options = [
        {
            "value": "understand_target",
            "label": "Understand what drives the target variable",
            "recommended": recommended == "understand_target",
        },
        {
            "value": "relationships",
            "label": "Explore relationships between features",
            "recommended": False,
        },
        {
            "value": "quality",
            "label": "Deep data quality investigation",
            "recommended": False,
        },
        {
            "value": "segments",
            "label": "Find natural segments / clusters",
            "recommended": False,
        },
        {
            "value": "comprehensive",
            "label": "Comprehensive analysis (all of the above)",
            "recommended": recommended == "comprehensive",
        },
    ]

    return {
        "id": "eda_q1_goal",
        "step": "eda",
        "question": "What is your primary analysis goal?",
        "type": "single_select",
        "options": options,
        "user_response": None,
    }


def _build_stat_tests_question(state: AutoDSState) -> dict:
    """Build the statistical tests selection question based on column types."""
    numeric_cols = state.get("numeric_columns", [])
    categorical_cols = state.get("categorical_columns", [])
    target = state.get("target_column")
    columns_info = state.get("columns", [])

    options: list[dict] = []

    # T-test: need binary grouping + numeric
    has_binary = any(
        ci.get("cardinality") == "binary" or ci.get("unique_count", 0) == 2
        for ci in columns_info
    )
    if has_binary and numeric_cols:
        options.append({
            "value": "t_test",
            "label": "T-Test (compare means across 2 groups)",
            "recommended": True,
        })

    # Chi-square: need 2+ categorical columns
    if len(categorical_cols) >= 2:
        options.append({
            "value": "chi_square",
            "label": "Chi-Square test (association between categorical variables)",
            "recommended": True,
        })

    # ANOVA: need a grouping col with 3+ levels + numeric
    has_multigroup = any(
        ci.get("unique_count", 0) >= 3 and ci.get("inferred_type") == "categorical"
        for ci in columns_info
    )
    if has_multigroup and numeric_cols:
        options.append({
            "value": "anova",
            "label": "ANOVA (compare means across 3+ groups)",
            "recommended": True,
        })

    # Correlation analysis: need 2+ numeric cols
    if len(numeric_cols) >= 2:
        options.append({
            "value": "correlation",
            "label": "Correlation analysis (Pearson + Spearman)",
            "recommended": True,
        })

    # Normality tests
    if numeric_cols:
        options.append({
            "value": "normality",
            "label": "Normality tests (Shapiro-Wilk)",
            "recommended": False,
        })

    # VIF (multicollinearity) if 3+ numeric cols
    if len(numeric_cols) >= 3:
        options.append({
            "value": "vif",
            "label": "Multicollinearity check (VIF analysis)",
            "recommended": False,
            "expert_only": True,
        })

    if not options:
        options.append({
            "value": "none",
            "label": "No statistical tests applicable",
            "recommended": True,
        })

    return {
        "id": "eda_q2_stat_tests",
        "step": "eda",
        "question": "Which statistical tests should we run?",
        "type": "multi_select",
        "options": options,
        "user_response": None,
    }


def _build_viz_question(state: AutoDSState) -> dict:
    """Build the visualization selection question."""
    numeric_cols = state.get("numeric_columns", [])
    categorical_cols = state.get("categorical_columns", [])
    datetime_cols = state.get("datetime_columns", [])

    options: list[dict] = []

    if numeric_cols:
        options.append({
            "value": "histogram",
            "label": "Histograms (distribution of numeric columns)",
            "recommended": True,
        })
        options.append({
            "value": "box_plot",
            "label": "Box plots (outliers and spread)",
            "recommended": True,
        })

    if len(numeric_cols) >= 2:
        options.append({
            "value": "scatter",
            "label": "Scatter plots (numeric relationships)",
            "recommended": False,
        })
        options.append({
            "value": "correlation_heatmap",
            "label": "Correlation heatmap",
            "recommended": True,
        })

    if len(numeric_cols) >= 3:
        options.append({
            "value": "pair_plot",
            "label": "Pair plot (pairwise numeric relationships)",
            "recommended": False,
            "expert_only": True,
        })

    if categorical_cols:
        options.append({
            "value": "bar_chart",
            "label": "Bar charts (categorical distributions)",
            "recommended": True,
        })

    if datetime_cols:
        options.append({
            "value": "time_series",
            "label": "Time series plots",
            "recommended": True,
        })

    if not options:
        options.append({
            "value": "none",
            "label": "No visualizations applicable",
            "recommended": True,
        })

    return {
        "id": "eda_q3_viz",
        "step": "eda",
        "question": "Which visualizations would you like?",
        "type": "multi_select",
        "options": options,
        "user_response": None,
    }


def _build_distribution_question(state: AutoDSState) -> dict:
    """Build the distribution analysis question (numeric cols only)."""
    return {
        "id": "eda_q4_distribution",
        "step": "eda",
        "question": "Run detailed distribution analysis on numeric columns?",
        "type": "single_select",
        "options": [
            {"value": "yes", "label": "Yes - analyze skewness, kurtosis, normality", "recommended": True},
            {"value": "no", "label": "No - skip distribution analysis", "recommended": False},
        ],
        "user_response": None,
    }


def _build_correlation_deep_dive_question(state: AutoDSState) -> dict:
    """Build the correlation deep-dive question (3+ numeric cols)."""
    return {
        "id": "eda_q5_correlation_deep",
        "step": "eda",
        "question": "Run correlation deep-dive (VIF, multicollinearity flags)?",
        "type": "single_select",
        "options": [
            {"value": "yes", "label": "Yes - full correlation deep-dive", "recommended": True},
            {"value": "no", "label": "No - basic correlation only", "recommended": False},
        ],
        "user_response": None,
        "expert_only": True,
    }


# ---------------------------------------------------------------------------
# Question generation node
# ---------------------------------------------------------------------------

def generate_eda_questions(state: AutoDSState) -> AutoDSState:
    """Generate EDA questions based on data characteristics and domain.

    Builds universal questions, adds domain-specific ones if available,
    filters by user mode, and stores them in state for the dashboard.

    In AUTO mode all questions are auto-answered with recommended defaults.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with ``eda_questions_asked`` populated.
    """
    state["current_step"] = "eda_questions"
    logger.info("Generating EDA questions")

    questions: list[dict] = []

    # Universal questions
    questions.append(_build_goal_question(state))
    questions.append(_build_stat_tests_question(state))
    questions.append(_build_viz_question(state))

    numeric_cols = state.get("numeric_columns", [])
    if numeric_cols:
        questions.append(_build_distribution_question(state))
    if len(numeric_cols) >= 3:
        questions.append(_build_correlation_deep_dive_question(state))

    # Domain-specific questions
    domain_config = state.get("domain_config", {})
    domain_eda_qs = domain_config.get("eda_questions", [])
    for dq in domain_eda_qs:
        dq_copy = dict(dq)
        dq_copy.setdefault("step", "eda")
        dq_copy.setdefault("user_response", None)
        dq_copy["domain_specific"] = True
        questions.append(dq_copy)

    # Filter by user mode
    user_mode = state.get("user_mode", "guided")
    filtered = filter_questions_for_mode(questions, user_mode)

    # In AUTO mode: auto-select all answers
    if user_mode == "auto":
        auto_answers: list[dict] = []
        for q in questions:
            q_answered = dict(q)
            if q["type"] == "multi_select":
                # Select all recommended options
                q_answered["user_response"] = [
                    opt["value"]
                    for opt in q.get("options", [])
                    if opt.get("recommended", False)
                ]
                if not q_answered["user_response"]:
                    q_answered["user_response"] = [
                        opt["value"] for opt in q.get("options", [])[:3]
                    ]
            else:
                q_answered["user_response"] = auto_select_best_option(q, state)
            auto_answers.append(q_answered)

        state["eda_questions_asked"] = auto_answers

        # Also populate eda_analyses_selected from auto answers
        analyses = _extract_analyses_from_answers(auto_answers)
        state["eda_analyses_selected"] = analyses
        logger.info("AUTO mode: auto-selected %d analyses", len(analyses))
    else:
        state["eda_questions_asked"] = filtered
        logger.info("Generated %d EDA questions for mode '%s'", len(filtered), user_mode)

    return state


def _extract_analyses_from_answers(answers: list[dict]) -> list[str]:
    """Convert answered questions into a flat list of analysis names."""
    analyses: list[str] = []
    for q in answers:
        resp = q.get("user_response")
        if resp is None:
            continue
        if isinstance(resp, list):
            analyses.extend(resp)
        elif isinstance(resp, str) and resp not in ("none", "no"):
            analyses.append(resp)
    return analyses


# ---------------------------------------------------------------------------
# EDA execution helpers
# ---------------------------------------------------------------------------

def _safe_execute(label: str, fn, *args, **kwargs) -> Any:
    """Execute a function, returning None on failure instead of crashing."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning("EDA step '%s' failed: %s", label, exc)
        return None


def _run_histograms(df: pd.DataFrame, numeric_cols: list[str], target: str | None) -> list[dict]:
    """Generate histograms for numeric columns."""
    from agents.tools.viz_tools import histogram
    charts: list[dict] = []
    for col in numeric_cols[:10]:  # cap at 10 to avoid chart overload
        result = _safe_execute(f"histogram_{col}", histogram, df, col, color_by=target)
        if result is not None:
            charts.append(result)
    return charts


def _run_box_plots(df: pd.DataFrame, numeric_cols: list[str], target: str | None) -> list[dict]:
    """Generate box plots for numeric columns."""
    from agents.tools.viz_tools import box_plot
    charts: list[dict] = []
    for col in numeric_cols[:10]:
        result = _safe_execute(f"box_plot_{col}", box_plot, df, col, group_by=target)
        if result is not None:
            charts.append(result)
    return charts


def _run_scatter_plots(
    df: pd.DataFrame, numeric_cols: list[str], target: str | None,
) -> list[dict]:
    """Generate scatter plots for top numeric pairs."""
    from agents.tools.viz_tools import scatter_plot
    charts: list[dict] = []
    pairs = [(numeric_cols[i], numeric_cols[j])
             for i in range(min(len(numeric_cols), 5))
             for j in range(i + 1, min(len(numeric_cols), 5))]
    for col_x, col_y in pairs[:6]:
        result = _safe_execute(
            f"scatter_{col_x}_{col_y}",
            scatter_plot, df, col_x, col_y, color_by=target,
        )
        if result is not None:
            charts.append(result)
    return charts


def _run_correlation(df: pd.DataFrame, numeric_cols: list[str]) -> tuple[dict | None, dict | None]:
    """Run correlation matrix and return heatmap chart + results dict."""
    from agents.tools.viz_tools import correlation_heatmap
    from agents.tools.stats_tools import correlation_matrix

    chart = _safe_execute("correlation_heatmap", correlation_heatmap, df, numeric_cols)
    matrix_result = _safe_execute("correlation_matrix", correlation_matrix, df, numeric_cols)
    return chart, matrix_result


def _run_bar_charts(
    df: pd.DataFrame, categorical_cols: list[str], target: str | None,
) -> list[dict]:
    """Generate bar charts for categorical columns."""
    from agents.tools.viz_tools import bar_chart
    charts: list[dict] = []
    for col in categorical_cols[:8]:
        result = _safe_execute(f"bar_chart_{col}", bar_chart, df, col, group_by=target)
        if result is not None:
            charts.append(result)
    return charts


def _run_time_series(df: pd.DataFrame, datetime_cols: list[str], numeric_cols: list[str]) -> list[dict]:
    """Generate time series plots."""
    from agents.tools.viz_tools import time_series_plot
    charts: list[dict] = []
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        for val_col in numeric_cols[:3]:
            result = _safe_execute(
                f"timeseries_{val_col}",
                time_series_plot, df, date_col, val_col,
            )
            if result is not None:
                charts.append(result)
    return charts


def _run_stat_tests(
    df: pd.DataFrame,
    analyses: list[str],
    state: AutoDSState,
) -> dict:
    """Execute selected statistical tests and return results dict."""
    results: dict[str, Any] = {}
    numeric_cols = state.get("numeric_columns", [])
    categorical_cols = state.get("categorical_columns", [])
    target = state.get("target_column")
    columns_info = state.get("columns", [])

    if "t_test" in analyses and target:
        from agents.tools.stats_tools import t_test_independent
        binary_cols = [
            ci["name"] for ci in columns_info
            if ci.get("cardinality") == "binary" and ci["name"] != target
        ]
        for group_col in binary_cols[:3]:
            for num_col in numeric_cols[:5]:
                if num_col == group_col:
                    continue
                key = f"t_test_{num_col}_by_{group_col}"
                result = _safe_execute(key, t_test_independent, df, num_col, group_col)
                if result is not None:
                    results[key] = result

    if "chi_square" in analyses:
        from agents.tools.stats_tools import chi_square_test
        cat_pairs = [(categorical_cols[i], categorical_cols[j])
                     for i in range(min(len(categorical_cols), 4))
                     for j in range(i + 1, min(len(categorical_cols), 4))]
        for col_a, col_b in cat_pairs[:5]:
            key = f"chi_sq_{col_a}_vs_{col_b}"
            result = _safe_execute(key, chi_square_test, df, col_a, col_b)
            if result is not None:
                results[key] = result

    if "anova" in analyses and target and target in categorical_cols:
        from agents.tools.stats_tools import anova_oneway
        for num_col in numeric_cols[:5]:
            key = f"anova_{num_col}_by_{target}"
            result = _safe_execute(key, anova_oneway, df, num_col, target)
            if result is not None:
                results[key] = result

    if "correlation" in analyses and len(numeric_cols) >= 2:
        from agents.tools.stats_tools import correlation_matrix
        result = _safe_execute("correlation_matrix", correlation_matrix, df, numeric_cols)
        if result is not None:
            results["correlation_matrix"] = result

    if "normality" in analyses:
        from agents.tools.stats_tools import shapiro_wilk
        for col in numeric_cols[:8]:
            key = f"shapiro_{col}"
            result = _safe_execute(key, shapiro_wilk, df, col)
            if result is not None:
                results[key] = result

    if "vif" in analyses and len(numeric_cols) >= 2:
        from agents.tools.stats_tools import vif_analysis
        result = _safe_execute("vif", vif_analysis, df, numeric_cols)
        if result is not None:
            results["vif_analysis"] = result

    return results


def _generate_summary_with_llm(
    eda_results: dict,
    charts_count: int,
    state: AutoDSState,
) -> str:
    """Use LLM to generate an EDA summary, with template fallback."""
    try:
        from core.llm_config import invoke_llm, get_agent_system_prompt

        # Build a compact results digest for the LLM
        digest_parts: list[str] = []
        for name, result in list(eda_results.items())[:15]:
            if isinstance(result, dict):
                # Keep only key scalar values
                summary_fields = {
                    k: v for k, v in result.items()
                    if isinstance(v, (int, float, str, bool)) and k != "interpretation"
                }
                interpretation = result.get("interpretation", "")
                digest_parts.append(f"- {name}: {summary_fields}")
                if interpretation:
                    digest_parts.append(f"  Interpretation: {interpretation}")
            else:
                digest_parts.append(f"- {name}: {result}")

        digest = "\n".join(digest_parts)

        domain = state.get("detected_domain", "generic")
        target = state.get("target_column", "N/A")
        n_rows = state.get("row_count", 0)
        n_cols = state.get("column_count", 0)

        prompt = (
            f"You are summarizing an exploratory data analysis for a {domain} dataset.\n\n"
            f"Dataset: {n_rows} rows, {n_cols} columns. Target: {target}.\n"
            f"Number of charts generated: {charts_count}.\n\n"
            f"Key analysis results:\n{digest}\n\n"
            f"Write a concise 3-5 paragraph EDA summary covering:\n"
            f"1. Data characteristics and quality\n"
            f"2. Key statistical findings\n"
            f"3. Notable patterns and relationships\n"
            f"4. Recommendations for next steps\n\n"
            f"Use clear, business-friendly language."
        )

        system_prompt = get_agent_system_prompt(
            "eda_agent", state.get("domain_config"),
        )
        summary = invoke_llm(prompt, system_prompt=system_prompt, state=state)
        return summary

    except Exception as exc:
        logger.warning("LLM summary generation failed: %s. Using template fallback.", exc)
        return _template_summary(eda_results, charts_count, state)


def _template_summary(eda_results: dict, charts_count: int, state: AutoDSState) -> str:
    """Rule-based fallback summary when LLM is unavailable."""
    n_rows = state.get("row_count", 0)
    n_cols = state.get("column_count", 0)
    target = state.get("target_column", "N/A")
    n_tests = len(eda_results)

    significant_tests = [
        name for name, r in eda_results.items()
        if isinstance(r, dict) and r.get("significant") is True
    ]

    lines = [
        f"EDA Summary for dataset with {n_rows} rows and {n_cols} columns.",
        f"Target variable: {target}.",
        f"Executed {n_tests} statistical analyses and generated {charts_count} visualizations.",
    ]
    if significant_tests:
        lines.append(
            f"Statistically significant results found in: {', '.join(significant_tests[:5])}."
        )
    else:
        lines.append("No statistically significant results were found at the 0.05 level.")

    return "\n".join(lines)


def _extract_insights(eda_results: dict, charts: list[dict]) -> list[str]:
    """Extract key insights from results and chart metadata."""
    insights: list[str] = []

    # From statistical test results
    for name, result in eda_results.items():
        if not isinstance(result, dict):
            continue

        interpretation = result.get("interpretation")
        if interpretation and result.get("significant"):
            insights.append(interpretation)

        # Correlation insights
        if name == "correlation_matrix" and "top_pairs" in result:
            for pair in result.get("top_pairs", [])[:3]:
                r_val = pair.get("r", 0)
                if abs(r_val) > 0.7:
                    insights.append(
                        f"Strong correlation (r={r_val:.3f}) between "
                        f"{pair.get('col1', '?')} and {pair.get('col2', '?')}"
                    )

    # From chart insights
    for chart in charts:
        chart_insights = chart.get("insights", [])
        insights.extend(chart_insights[:2])

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ins in insights:
        normalized = ins.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)

    return unique[:15]


# ---------------------------------------------------------------------------
# EDA execution node
# ---------------------------------------------------------------------------

def execute_eda(state: AutoDSState) -> AutoDSState:
    """Execute EDA analyses based on user selections or auto-choices.

    Steps:
      1. Load working DataFrame.
      2. Read selected analyses from state.
      3. Run statistical tests.
      4. Generate visualizations.
      5. Produce LLM-generated summary (with fallback).
      6. Extract key insights.
      7. Write all results back to state.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with EDA results, charts, summary, and insights.
    """
    state["current_step"] = "eda_execute"
    logger.info("Starting EDA execution")

    df = _get_working_df(state)
    if df.empty:
        state["errors"] = state.get("errors", []) + [{
            "step": "eda",
            "type": "no_data",
            "detail": "No working DataFrame available for EDA",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        state["completed_steps"] = state.get("completed_steps", []) + ["eda"]
        return state

    # Determine which analyses to run
    analyses = state.get("eda_analyses_selected", [])
    if not analyses:
        # Derive from answered questions
        answers = state.get("eda_questions_asked", [])
        analyses = _extract_analyses_from_answers(answers)
        state["eda_analyses_selected"] = analyses

    numeric_cols = state.get("numeric_columns", [])
    categorical_cols = state.get("categorical_columns", [])
    datetime_cols = state.get("datetime_columns", [])
    target = state.get("target_column")

    eda_results: dict[str, Any] = {}
    eda_charts: list[dict] = []

    # ------------------------------------------------------------------
    # Statistical tests
    # ------------------------------------------------------------------
    try:
        stat_results = _run_stat_tests(df, analyses, state)
        eda_results.update(stat_results)
        logger.info("Completed %d statistical tests", len(stat_results))
    except Exception as exc:
        logger.error("Statistical tests failed: %s", exc)
        state["errors"] = state.get("errors", []) + [{
            "step": "eda",
            "type": "stat_tests",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]

    # ------------------------------------------------------------------
    # Visualizations
    # ------------------------------------------------------------------
    if "histogram" in analyses and numeric_cols:
        charts = _run_histograms(df, numeric_cols, target)
        eda_charts.extend(charts)

    if "box_plot" in analyses and numeric_cols:
        charts = _run_box_plots(df, numeric_cols, target)
        eda_charts.extend(charts)

    if "scatter" in analyses and len(numeric_cols) >= 2:
        charts = _run_scatter_plots(df, numeric_cols, target)
        eda_charts.extend(charts)

    if "correlation_heatmap" in analyses and len(numeric_cols) >= 2:
        chart, corr_result = _run_correlation(df, numeric_cols)
        if chart is not None:
            eda_charts.append(chart)
        if corr_result is not None:
            eda_results["correlation_matrix"] = corr_result

    if "bar_chart" in analyses and categorical_cols:
        charts = _run_bar_charts(df, categorical_cols, target)
        eda_charts.extend(charts)

    if "time_series" in analyses and datetime_cols:
        charts = _run_time_series(df, datetime_cols, numeric_cols)
        eda_charts.extend(charts)

    if "pair_plot" in analyses and len(numeric_cols) >= 3:
        from agents.tools.viz_tools import pair_plot
        result = _safe_execute(
            "pair_plot", pair_plot, df, numeric_cols[:5], color_by=target,
        )
        if result is not None:
            eda_charts.append(result)

    logger.info("Generated %d visualizations", len(eda_charts))

    # ------------------------------------------------------------------
    # Distribution analysis (if selected)
    # ------------------------------------------------------------------
    if "yes" in analyses or "understand_target" in analyses or "comprehensive" in analyses:
        if numeric_cols:
            from agents.tools.data_tools import get_column_stats
            try:
                col_stats = get_column_stats(df[numeric_cols])
                eda_results["distribution_stats"] = col_stats
            except Exception as exc:
                logger.warning("Distribution analysis failed: %s", exc)

    # ------------------------------------------------------------------
    # LLM summary
    # ------------------------------------------------------------------
    eda_summary = _generate_summary_with_llm(eda_results, len(eda_charts), state)

    # ------------------------------------------------------------------
    # Extract insights
    # ------------------------------------------------------------------
    eda_insights = _extract_insights(eda_results, eda_charts)

    # ------------------------------------------------------------------
    # Update state
    # ------------------------------------------------------------------
    state["eda_results"] = eda_results
    state["eda_charts"] = eda_charts
    state["eda_summary"] = eda_summary
    state["eda_insights"] = eda_insights
    state["completed_steps"] = state.get("completed_steps", []) + ["eda"]

    logger.info(
        "EDA completed: %d results, %d charts, %d insights",
        len(eda_results), len(eda_charts), len(eda_insights),
    )
    return state
