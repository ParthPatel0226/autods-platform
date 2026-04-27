"""Orchestrator Agent — the LangGraph supervisor.

This is the brain of the AutoDS platform. It receives user goals,
decomposes them into subtasks, routes work to specialist agents,
and manages the overall workflow state.

The orchestrator does NOT perform any data analysis directly.
It decides WHAT should be done and WHICH agent should do it.
"""

import logging
from datetime import datetime, timezone

from core.constants import (
    MODE_AUTO,
    MODE_GUIDED,
    MODE_EXPERT,
    PROBLEM_CLASSIFICATION,
    PROBLEM_CLUSTERING,
    PROBLEM_REGRESSION,
    PROBLEM_TIME_SERIES,
    VALID_PROBLEM_TYPES,
)
from core.state import AutoDSState
from core.llm_config import invoke_llm_json, get_agent_system_prompt

logger = logging.getLogger(__name__)


# =========================================================================
# Keywords for heuristic problem-type detection
# =========================================================================
_CLASSIFICATION_KEYWORDS = frozenset([
    "predict", "classify", "churn", "fraud", "default", "diagnose",
    "detect", "readmit", "attrition", "spam", "sentiment", "approve",
    "reject", "positive", "negative", "conversion", "click",
    "mortality", "survive", "risk", "defect", "anomaly",
])
_REGRESSION_KEYWORDS = frozenset([
    "price", "cost", "revenue", "salary", "score", "rating",
    "amount", "value", "estimate", "quantity", "demand",
    "sales", "profit", "weight", "duration", "count",
])
_CLUSTERING_KEYWORDS = frozenset([
    "segment", "cluster", "group", "cohort", "profile",
    "persona", "tier", "category", "similar", "pattern",
])
_TIME_SERIES_KEYWORDS = frozenset([
    "forecast", "trend", "seasonal", "time series", "temporal",
    "next month", "next quarter", "next year", "future",
    "predict over time", "daily", "weekly", "monthly",
])

# Columns that strongly suggest a target variable
_TARGET_COLUMN_PATTERNS = [
    "target", "label", "class", "outcome", "status", "result",
    "churn", "fraud", "default", "readmit", "attrition",
    "converted", "purchased", "clicked", "survived", "approved",
    "is_", "has_", "flag_",
]

# Columns that are likely ID columns (exclude from analysis)
_ID_COLUMN_PATTERNS = [
    "id", "uuid", "guid", "index", "key", "identifier",
    "row_num", "row_number", "serial",
]


# =========================================================================
# Main Orchestrator Node
# =========================================================================

def orchestrator_agent(state: AutoDSState) -> AutoDSState:
    """Main orchestrator node — runs at pipeline start.

    Responsibilities:
    1. Decompose user goal into problem type
    2. Detect/suggest target column
    3. Detect time column for time-series
    4. Set pipeline steps based on mode + problem type
    5. Configure evaluation metrics based on domain + problem type
    """
    state["current_step"] = "orchestration"

    # Step 1: Decompose goal → problem type
    _resolve_problem_type(state)

    # Step 2: Suggest target column if not set
    _resolve_target_column(state)

    # Step 3: Detect time column for time-series
    _resolve_time_column(state)

    # Step 4: Determine pipeline steps
    _set_pipeline_steps(state)

    # Step 5: Set default evaluation metrics
    _set_evaluation_metrics(state)

    # Step 6: Log orchestration decisions
    state["completed_steps"] = state.get("completed_steps", []) + ["orchestration"]
    state["decision_log"] = state.get("decision_log", []) + [
        {
            "agent": "orchestrator",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decisions": {
                "problem_type": state.get("problem_type", ""),
                "target_column": state.get("target_column"),
                "time_column": state.get("time_column"),
                "pipeline_steps": state.get("pipeline_steps", []),
                "evaluation_metrics": state.get("evaluation_metrics", []),
            },
        }
    ]

    logger.info(
        "Orchestration complete: problem_type=%s, target=%s, steps=%s",
        state.get("problem_type"),
        state.get("target_column"),
        state.get("pipeline_steps"),
    )

    return state


# =========================================================================
# Goal Decomposition
# =========================================================================

def decompose_user_goal(state: AutoDSState) -> AutoDSState:
    """Decompose a natural language user goal into pipeline steps.

    Examples:
        "Predict customer churn" → classification pipeline
        "Analyze my sales data" → EDA-only pipeline
        "Segment my customers" → clustering pipeline
        "Forecast next month's revenue" → time-series pipeline

    The orchestrator uses LLM to interpret the goal and set:
    - problem_type
    - target_column (if specified)
    - time_column (for time-series)
    - which pipeline steps to run
    """
    return orchestrator_agent(state)


def _resolve_problem_type(state: AutoDSState):
    """Determine problem type from user goal + data characteristics."""
    # If already set explicitly, keep it
    if state.get("problem_type") and state["problem_type"] in VALID_PROBLEM_TYPES:
        return

    user_goal = state.get("user_goal", "")
    columns = [col.get("name", "") for col in state.get("columns", [])]

    if not user_goal and not state.get("target_column"):
        logger.info("No user goal or target — defaulting to EDA-only pipeline")
        state["problem_type"] = ""
        return

    # Try LLM first
    if user_goal or state.get("target_column"):
        llm_result = _llm_detect_problem_type(state, user_goal, columns)
        if llm_result:
            return

    # Fallback to heuristics
    _heuristic_detect_problem_type(state)


def _llm_detect_problem_type(
    state: AutoDSState, user_goal: str, columns: list[str]
) -> bool:
    """Use LLM to detect problem type. Returns True on success."""
    prompt = f"""Given this user goal and available columns, determine the analysis type.

User goal: "{user_goal}"
Available columns: {columns[:50]}
Target column (if user specified): {state.get("target_column", "not specified")}
Detected domain: {state.get("detected_domain", "generic")}

Return JSON:
{{
  "problem_type": "classification" | "regression" | "clustering" | "time_series" | "",
  "suggested_target": "column_name" or null,
  "suggested_time_column": "column_name" or null,
  "reasoning": "one sentence"
}}

Rules:
- "" means EDA-only (no modeling)
- "classification" when target is binary/categorical
- "regression" when target is continuous numeric
- "clustering" when no target and goal involves grouping
- "time_series" when goal involves forecasting over time"""

    try:
        result = invoke_llm_json(
            prompt=prompt,
            system_prompt=get_agent_system_prompt("orchestrator", state.get("domain_config")),
            state=state,
        )

        problem_type = result.get("problem_type", "")
        if problem_type and problem_type not in VALID_PROBLEM_TYPES and problem_type != "":
            logger.warning("LLM returned invalid problem_type: %s", problem_type)
            return False

        if not state.get("problem_type"):
            state["problem_type"] = problem_type
        if not state.get("target_column") and result.get("suggested_target"):
            state["target_column"] = result["suggested_target"]
        if not state.get("time_column") and result.get("suggested_time_column"):
            state["time_column"] = result["suggested_time_column"]

        logger.info(
            "LLM goal decomposition: problem_type=%s, target=%s, reasoning=%s",
            state.get("problem_type"),
            state.get("target_column"),
            result.get("reasoning", ""),
        )
        return True

    except Exception as e:
        logger.warning("LLM goal decomposition failed: %s. Using heuristics.", e)
        return False


def _heuristic_detect_problem_type(state: AutoDSState):
    """Rule-based fallback for problem type detection."""
    goal = state.get("user_goal", "").lower()

    keyword_sets = {
        PROBLEM_CLASSIFICATION: _CLASSIFICATION_KEYWORDS,
        PROBLEM_REGRESSION: _REGRESSION_KEYWORDS,
        PROBLEM_CLUSTERING: _CLUSTERING_KEYWORDS,
        PROBLEM_TIME_SERIES: _TIME_SERIES_KEYWORDS,
    }

    scores: dict[str, int] = {k: 0 for k in keyword_sets}

    # Check multi-word phrases FIRST (they are more specific)
    for problem_type, keywords in keyword_sets.items():
        for kw in keywords:
            if " " in kw and kw in goal:
                scores[problem_type] += 2

    # Then check single-word matches via set intersection
    goal_words = set(goal.split())
    for problem_type, keywords in keyword_sets.items():
        single_word_kws = frozenset(kw for kw in keywords if " " not in kw)
        scores[problem_type] += len(goal_words & single_word_kws)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score > 0:
        state["problem_type"] = best_type
        logger.info("Heuristic problem_type=%s (score=%d)", best_type, best_score)
        return

    # Fallback: infer from target column data characteristics
    target_col = state.get("target_column")
    df = state.get("uploaded_data")
    if target_col and df is not None and target_col in df.columns:
        series = df[target_col]
        nunique = series.nunique()
        if nunique <= 20 or series.dtype == "object" or series.dtype.name == "category":
            state["problem_type"] = PROBLEM_CLASSIFICATION
            logger.info("Inferred classification from target column (nunique=%d)", nunique)
            return
        state["problem_type"] = PROBLEM_REGRESSION
        logger.info("Inferred regression from target column (nunique=%d)", nunique)
        return

    state["problem_type"] = ""  # EDA only
    logger.info("No keyword matches — defaulting to EDA-only")


# =========================================================================
# Target Column Resolution
# =========================================================================

def _resolve_target_column(state: AutoDSState):
    """Suggest target column if not already set."""
    if state.get("target_column"):
        # Validate it exists in columns
        col_names = {col.get("name", "") for col in state.get("columns", [])}
        if state["target_column"] not in col_names:
            logger.warning(
                "Target column '%s' not found in data. Clearing.",
                state["target_column"],
            )
            state["target_column"] = None
        else:
            return

    # No target needed for clustering or EDA-only
    if state.get("problem_type") in (PROBLEM_CLUSTERING, ""):
        return

    columns = state.get("columns", [])
    if not columns:
        return

    # Heuristic: look for columns matching target patterns
    candidates = []
    for col_info in columns:
        col_name = col_info.get("name", "").lower()
        for pattern in _TARGET_COLUMN_PATTERNS:
            if pattern in col_name:
                # Score by pattern specificity
                score = len(pattern)
                # Bonus if binary
                if col_info.get("cardinality") == "binary":
                    score += 5
                # Bonus if low cardinality for classification
                if (
                    state.get("problem_type") == PROBLEM_CLASSIFICATION
                    and col_info.get("unique_count", 999) <= 20
                ):
                    score += 3
                candidates.append((col_info["name"], score))
                break

    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        state["target_column"] = candidates[0][0]
        logger.info(
            "Auto-suggested target column: %s (score=%d)",
            candidates[0][0],
            candidates[0][1],
        )

    # Infer problem sub-type from target column characteristics
    if state.get("target_column"):
        _infer_problem_type_from_target(state)


def _infer_problem_type_from_target(state: AutoDSState):
    """Refine problem type based on target column characteristics."""
    if state.get("problem_type") and state["problem_type"] in VALID_PROBLEM_TYPES:
        return  # Already set, don't override

    target = state["target_column"]
    for col_info in state.get("columns", []):
        if col_info.get("name") == target:
            inferred_type = col_info.get("inferred_type", "")
            unique_count = col_info.get("unique_count", 0)
            cardinality = col_info.get("cardinality", "")

            if cardinality == "binary" or (
                inferred_type == "categorical" and unique_count <= 20
            ):
                state["problem_type"] = PROBLEM_CLASSIFICATION
            elif inferred_type == "numeric" and unique_count > 20:
                state["problem_type"] = PROBLEM_REGRESSION
            break


# =========================================================================
# Time Column Resolution
# =========================================================================

def _resolve_time_column(state: AutoDSState):
    """Detect time/date column for time-series problems."""
    if state.get("time_column"):
        return

    # Only relevant for time-series
    if state.get("problem_type") != PROBLEM_TIME_SERIES:
        return

    datetime_cols = state.get("datetime_columns", [])
    if datetime_cols:
        state["time_column"] = datetime_cols[0]
        logger.info("Auto-detected time column: %s", datetime_cols[0])
        return

    # Fallback: look for date-like column names
    date_keywords = {"date", "time", "timestamp", "datetime", "period", "month", "year"}
    for col_info in state.get("columns", []):
        col_name = col_info.get("name", "").lower()
        if any(kw in col_name for kw in date_keywords):
            state["time_column"] = col_info["name"]
            logger.info("Heuristic time column: %s", col_info["name"])
            return


# =========================================================================
# Pipeline Step Configuration
# =========================================================================

def _set_pipeline_steps(state: AutoDSState):
    """Determine which pipeline steps to run based on mode + problem type."""
    problem_type = state.get("problem_type", "")
    mode = state.get("user_mode", MODE_GUIDED)
    domain_config = state.get("domain_config", {})

    # Core steps always run
    steps = ["domain_detection", "data_profiling", "eda"]

    # Feature engineering + modeling only if we have a target or clustering goal
    if problem_type in VALID_PROBLEM_TYPES:
        steps.append("feature_engineering")
        steps.append("modeling")

        # Explainability for supervised problems
        if problem_type in (PROBLEM_CLASSIFICATION, PROBLEM_REGRESSION):
            steps.append("explainability")

            # Fairness audit if domain requires it
            if domain_config.get("fairness", {}).get("required", False):
                steps.append("fairness_audit")

    # Reports always generated
    steps.append("report")

    state["pipeline_steps"] = steps

    logger.info(
        "Pipeline steps for mode=%s, problem=%s: %s",
        mode, problem_type, steps,
    )


# =========================================================================
# Evaluation Metrics Configuration
# =========================================================================

def _set_evaluation_metrics(state: AutoDSState):
    """Set default evaluation metrics based on problem type + domain."""
    if state.get("evaluation_metrics"):
        return  # Already set by user

    problem_type = state.get("problem_type", "")
    domain_config = state.get("domain_config", {})

    # Get domain-specific primary metrics if available
    domain_metrics = domain_config.get("primary_metrics", {})
    domain_specific = domain_metrics.get(problem_type, [])

    if problem_type == PROBLEM_CLASSIFICATION:
        base_metrics = ["accuracy", "precision", "recall", "f1", "auc_roc"]
        metrics = domain_specific if domain_specific else base_metrics
    elif problem_type == PROBLEM_REGRESSION:
        base_metrics = ["rmse", "mae", "r2", "mape"]
        metrics = domain_specific if domain_specific else base_metrics
    elif problem_type == PROBLEM_CLUSTERING:
        metrics = ["silhouette_score", "calinski_harabasz", "davies_bouldin"]
    elif problem_type == PROBLEM_TIME_SERIES:
        metrics = ["rmse", "mae", "mape", "r2"]
    else:
        metrics = []

    state["evaluation_metrics"] = metrics

    # Set cost matrix from domain defaults if not set
    if not state.get("cost_matrix") and domain_config.get("default_cost_matrix"):
        state["cost_matrix"] = domain_config["default_cost_matrix"]

    logger.info("Evaluation metrics set: %s", metrics)
