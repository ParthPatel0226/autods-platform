"""LangGraph workflow definition for the AutoDS pipeline.

This is the central nervous system of the platform. It defines the state machine
that routes data through agents based on user mode, domain, and data characteristics.
"""

import logging
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from core.constants import MODE_AUTO, MODE_GUIDED, MODE_EXPERT
from core.state import AutoDSState, create_initial_state

logger = logging.getLogger(__name__)


# =============================================================================
# Routing Functions (Conditional Edges)
# =============================================================================

def route_after_profiling(state: AutoDSState) -> str:
    """Route after data profiling step."""
    if state.get("errors") and any(e.get("type") == "critical" for e in state["errors"]):
        return "error_handler"
    return "eda_questions"


def route_after_eda_questions(state: AutoDSState) -> str:
    """Route after EDA questions are generated — pause for user in guided/expert."""
    return "eda_execute"


def route_after_eda(state: AutoDSState) -> str:
    """Route after EDA execution."""
    if state.get("problem_type") == "":
        # No target specified — EDA only, skip to report
        return "report"
    return "fe_questions"


def route_after_fe_questions(state: AutoDSState) -> str:
    """Route after feature engineering questions."""
    return "fe_execute"


def route_after_fe(state: AutoDSState) -> str:
    """Route after feature engineering."""
    return "model_questions"


def route_after_model_questions(state: AutoDSState) -> str:
    """Route after modeling questions."""
    return "model_execute"


def route_after_modeling(state: AutoDSState) -> str:
    """Route after model training."""
    if state.get("errors") and any(e.get("type") == "model_failure" for e in state["errors"]):
        return "error_handler"
    return "explain"


def route_after_explain(state: AutoDSState) -> str:
    """Route after explainability."""
    return "report"


def route_after_report(state: AutoDSState) -> str:
    """Route after report generation — workflow complete."""
    return END


# =============================================================================
# Placeholder Agent Node Functions
# These import and call the actual agent implementations.
# Each returns updated state.
# =============================================================================

def orchestrator_node(state: AutoDSState) -> AutoDSState:
    """Run orchestrator: goal decomposition, problem type, pipeline config."""
    from agents.orchestrator import orchestrator_agent
    return orchestrator_agent(state)


def domain_detection_node(state: AutoDSState) -> AutoDSState:
    """Detect industry domain from data characteristics."""
    from agents.domain_detector import run_domain_detection
    return run_domain_detection(state)


def data_profiling_node(state: AutoDSState) -> AutoDSState:
    """Profile data quality and detect issues."""
    from agents.data_profiler import run_data_profiling
    return run_data_profiling(state)


def eda_questions_node(state: AutoDSState) -> AutoDSState:
    """Generate EDA questions for user (Guided/Expert modes)."""
    from agents.eda_agent import generate_eda_questions
    return generate_eda_questions(state)


def eda_execute_node(state: AutoDSState) -> AutoDSState:
    """Execute EDA analyses."""
    from agents.eda_agent import execute_eda
    return execute_eda(state)


def fe_questions_node(state: AutoDSState) -> AutoDSState:
    """Generate feature engineering questions."""
    from agents.feature_engineer import generate_fe_questions
    return generate_fe_questions(state)


def fe_execute_node(state: AutoDSState) -> AutoDSState:
    """Execute feature engineering."""
    from agents.feature_engineer import execute_feature_engineering
    return execute_feature_engineering(state)


def model_questions_node(state: AutoDSState) -> AutoDSState:
    """Generate modeling questions."""
    from agents.modeling_agent import generate_model_questions
    return generate_model_questions(state)


def model_execute_node(state: AutoDSState) -> AutoDSState:
    """Train and evaluate models."""
    from agents.modeling_agent import execute_modeling
    return execute_modeling(state)


def explain_node(state: AutoDSState) -> AutoDSState:
    """Generate explainability outputs."""
    from agents.explainability_agent import run_explainability
    return run_explainability(state)


def report_node(state: AutoDSState) -> AutoDSState:
    """Generate reports in all formats."""
    from agents.report_agent import generate_reports
    return generate_reports(state)


def error_handler_node(state: AutoDSState) -> AutoDSState:
    """Handle critical errors gracefully."""
    logger.error("Pipeline entered error handler. Errors: %s", state.get("errors"))
    state["workflow_status"] = "error"
    # Still try to generate a partial report
    state["current_step"] = "error_recovery"
    return state


# =============================================================================
# Build the Graph
# =============================================================================

def build_workflow(checkpoint_path: str = "sessions/checkpoints.db", user_mode: str = MODE_GUIDED) -> StateGraph:
    """Build the complete LangGraph workflow.

    Args:
        checkpoint_path: Path to SQLite file for checkpointing.
        user_mode: User mode — "auto", "guided", or "expert". Interrupts are
            only applied for non-auto modes so AUTO runs end-to-end unattended.

    Returns:
        Compiled LangGraph application.
    """
    workflow = StateGraph(AutoDSState)

    # Add all nodes
    workflow.add_node("domain_detection", domain_detection_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("data_profiling", data_profiling_node)
    workflow.add_node("eda_questions", eda_questions_node)
    workflow.add_node("eda_execute", eda_execute_node)
    workflow.add_node("fe_questions", fe_questions_node)
    workflow.add_node("fe_execute", fe_execute_node)
    workflow.add_node("model_questions", model_questions_node)
    workflow.add_node("model_execute", model_execute_node)
    workflow.add_node("explain", explain_node)
    workflow.add_node("report", report_node)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("domain_detection")

    # Add edges — domain detection → orchestrator → profiling
    workflow.add_edge("domain_detection", "orchestrator")
    workflow.add_edge("orchestrator", "data_profiling")
    workflow.add_conditional_edges("data_profiling", route_after_profiling)
    workflow.add_edge("eda_questions", "eda_execute")
    workflow.add_conditional_edges("eda_execute", route_after_eda)
    workflow.add_edge("fe_questions", "fe_execute")
    workflow.add_conditional_edges("fe_execute", route_after_fe)
    workflow.add_edge("model_questions", "model_execute")
    workflow.add_conditional_edges("model_execute", route_after_modeling)
    workflow.add_conditional_edges("explain", route_after_explain)
    workflow.add_conditional_edges("report", route_after_report)
    workflow.add_edge("error_handler", "report")  # Try to generate partial report even on error

    # Compile with checkpointer for human-in-the-loop
    checkpointer = SqliteSaver.from_conn_string(checkpoint_path)

    # In Guided/Expert mode, interrupt before execute steps to get user input.
    # In Auto mode, no interrupts — the workflow runs end-to-end unattended.
    if user_mode != MODE_AUTO:
        app = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["eda_execute", "fe_execute", "model_execute"],
        )
    else:
        app = workflow.compile(checkpointer=checkpointer)

    return app


def build_auto_workflow(checkpoint_path: str = "sessions/checkpoints.db") -> StateGraph:
    """Build a simplified workflow for Auto mode (no interrupts).
    
    In Auto mode, no user questions are asked — the system makes all decisions.
    """
    workflow = StateGraph(AutoDSState)

    workflow.add_node("domain_detection", domain_detection_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("data_profiling", data_profiling_node)
    workflow.add_node("eda_execute", eda_execute_node)
    workflow.add_node("fe_execute", fe_execute_node)
    workflow.add_node("model_execute", model_execute_node)
    workflow.add_node("explain", explain_node)
    workflow.add_node("report", report_node)
    workflow.add_node("error_handler", error_handler_node)

    workflow.set_entry_point("domain_detection")

    workflow.add_edge("domain_detection", "orchestrator")
    workflow.add_edge("orchestrator", "data_profiling")
    workflow.add_conditional_edges("data_profiling", route_after_profiling)
    workflow.add_conditional_edges("eda_execute", route_after_eda)
    workflow.add_conditional_edges("fe_execute", route_after_fe)
    workflow.add_conditional_edges("model_execute", route_after_modeling)
    workflow.add_edge("explain", "report")
    workflow.add_edge("report", END)
    workflow.add_edge("error_handler", "report")

    checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
    app = workflow.compile(checkpointer=checkpointer)

    return app
