"""Workflow Progress Component — shows live pipeline progress in Streamlit.

Displays which steps are completed, which is currently running,
and which are pending, with timing information.
"""

import logging
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


# Step definitions with display info
PIPELINE_STEPS = [
    {"id": "domain_detection", "name": "Domain Detection", "icon": "🔍", "description": "Identifying industry domain"},
    {"id": "data_profiling", "name": "Data Profiling", "icon": "📋", "description": "Assessing data quality"},
    {"id": "eda", "name": "Exploratory Analysis", "icon": "📊", "description": "Analyzing patterns and distributions"},
    {"id": "feature_engineering", "name": "Feature Engineering", "icon": "⚙️", "description": "Creating predictive features"},
    {"id": "modeling", "name": "Model Training", "icon": "🤖", "description": "Training and evaluating models"},
    {"id": "explainability", "name": "Explainability", "icon": "🔬", "description": "Generating SHAP and fairness analysis"},
    {"id": "report", "name": "Report Generation", "icon": "📄", "description": "Creating downloadable reports"},
]


def render_workflow_progress(state: dict):
    """Render the workflow progress indicator.
    
    Args:
        state: Current AutoDSState dict.
    """
    completed = state.get("completed_steps", [])
    current = state.get("current_step", "")
    status = state.get("workflow_status", "running")
    errors = state.get("errors", [])

    st.subheader("📋 Pipeline Progress")

    for step in PIPELINE_STEPS:
        step_id = step["id"]

        if step_id in completed:
            # Completed step
            duration = _get_step_duration(state, step_id)
            summary = _get_step_summary(state, step_id)
            duration_str = f" ({duration:.0f}s)" if duration else ""

            st.markdown(
                f"✅ **{step['icon']} {step['name']}** — Complete{duration_str}"
            )
            if summary:
                st.caption(f"    → {summary}")

        elif step_id == current and status == "running":
            # Currently running step
            st.markdown(
                f"🔄 **{step['icon']} {step['name']}** — In Progress..."
            )
            st.caption(f"    {step['description']}")

        elif step_id == current and status == "paused":
            # Paused for user input
            st.markdown(
                f"⏸️ **{step['icon']} {step['name']}** — Waiting for your input"
            )

        elif step_id == current and status == "error":
            # Error state
            st.markdown(
                f"❌ **{step['icon']} {step['name']}** — Error"
            )
            for err in errors:
                if err.get("step") == step_id:
                    st.error(f"    {err.get('detail', 'Unknown error')}")

        else:
            # Pending step
            st.markdown(
                f"⬜ {step['icon']} {step['name']} — Waiting"
            )

    # Overall status
    st.divider()
    if status == "completed":
        total_duration = state.get("total_duration_seconds", 0)
        api_calls = state.get("api_call_count", 0)
        cost = state.get("estimated_cost_usd", 0)
        st.success(
            f"✅ Pipeline complete! "
            f"Duration: {total_duration:.0f}s | "
            f"API calls: {api_calls} | "
            f"Est. cost: ${cost:.2f}"
        )
    elif status == "error":
        st.error("Pipeline encountered an error. Check error details above.")
    elif status == "paused":
        st.info("Pipeline is paused — waiting for your input above.")


def _get_step_duration(state: dict, step_id: str) -> float | None:
    """Extract step duration from pipeline log."""
    log = state.get("pipeline_log", [])
    step_entries = [e for e in log if e.get("step") == step_id]
    if step_entries:
        return sum(e.get("duration_seconds", 0) for e in step_entries)
    return None


def _get_step_summary(state: dict, step_id: str) -> str:
    """Generate a one-line summary of what a completed step produced."""
    if step_id == "domain_detection":
        domain = state.get("detected_domain", "generic")
        conf = state.get("domain_detection_confidence", 0)
        return f"Detected: {domain} (confidence: {conf:.0%})"

    elif step_id == "data_profiling":
        issues = len(state.get("quality_issues", []))
        actions = len(state.get("cleaning_actions", []))
        return f"{issues} issues found, {actions} cleaning actions applied"

    elif step_id == "eda":
        charts = len(state.get("eda_charts", []))
        insights = len(state.get("eda_insights", []))
        return f"{charts} visualizations, {insights} key insights"

    elif step_id == "feature_engineering":
        created = len(state.get("features_created", []))
        selected = len(state.get("features_selected", []))
        return f"{created} features created, {selected} selected"

    elif step_id == "modeling":
        n_models = len(state.get("trained_models", {}))
        best = state.get("best_model_name", "")
        metrics = state.get("best_model_metrics", {})
        if best and metrics:
            top_metric = list(metrics.items())[0] if metrics else ("", "")
            return f"{n_models} models trained, best: {best} ({top_metric[0]}: {top_metric[1]:.3f})"
        return f"{n_models} models trained"

    elif step_id == "explainability":
        has_shap = state.get("shap_summary") is not None
        has_fairness = state.get("fairness_report") is not None
        parts = []
        if has_shap:
            parts.append("SHAP")
        if has_fairness:
            parts.append("fairness audit")
        return ", ".join(parts) if parts else "Completed"

    elif step_id == "report":
        formats = list(state.get("report_paths", {}).keys())
        return f"Generated: {', '.join(formats)}" if formats else "Completed"

    return ""


def render_mini_progress(state: dict):
    """Render a compact progress bar for the sidebar."""
    completed = len(state.get("completed_steps", []))
    total = len(PIPELINE_STEPS)
    progress = completed / total if total > 0 else 0

    st.progress(progress, text=f"Step {completed}/{total}")
