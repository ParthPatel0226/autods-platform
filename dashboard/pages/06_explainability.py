"""Page 06 -- Explainability.

SHAP plots, PDP/ICE, counterfactual examples, fairness audit, what-if
analysis, and model card display.  Integrates with explainability/ modules.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import MODE_AUTO, PROBLEM_CLASSIFICATION

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _guard() -> None:
    if "uploaded_data" not in st.session_state:
        st.warning("Please upload data first.")
        st.stop()
    if not st.session_state.get("model_results"):
        st.warning("Train models first before viewing explainability.")
        st.stop()


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_progress() -> None:
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "explainability"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_shap_section() -> None:
    """SHAP global and local explanations."""
    shap_data: dict[str, Any] = st.session_state.get("shap_values", {})
    explainability: dict[str, Any] = st.session_state.get("explainability_results", {})

    st.subheader("SHAP Feature Explanations")

    if not shap_data and not explainability.get("shap"):
        st.info(
            "SHAP values not computed yet. Connect the Explainability Agent "
            "to generate SHAP explanations."
        )
        return

    shap_info = shap_data or explainability.get("shap", {})

    # Global importance bar
    global_importance: dict[str, float] = shap_info.get("global_importance", {})
    if global_importance:
        from dashboard.components.chart_container import render_chart

        try:
            import plotly.express as px

            sorted_imp = dict(sorted(global_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:20])
            fig = px.bar(
                x=list(sorted_imp.values()),
                y=list(sorted_imp.keys()),
                orientation="h",
                labels={"x": "Mean |SHAP value|", "y": "Feature"},
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), height=450)
            render_chart(fig, title="SHAP Global Feature Importance", key="shap_global")
        except ImportError:
            st.warning("Install plotly for SHAP charts.")

    # SHAP summary chart (if pre-rendered figure stored)
    summary_fig = shap_info.get("summary_figure")
    if summary_fig is not None:
        from dashboard.components.chart_container import render_chart

        render_chart(summary_fig, title="SHAP Summary Plot", key="shap_summary")

    # Local explanation for a single sample
    _render_shap_local(shap_info)


def _render_shap_local(shap_info: dict[str, Any]) -> None:
    """Show SHAP waterfall for a user-selected sample index."""
    sample_explanations: list[dict] = shap_info.get("sample_explanations", [])
    if not sample_explanations:
        return

    with st.expander("Local SHAP Explanation (single sample)"):
        max_idx = len(sample_explanations) - 1
        idx = st.number_input(
            "Sample index",
            min_value=0,
            max_value=max_idx,
            value=0,
            key="shap_local_idx",
        )
        sample = sample_explanations[int(idx)]
        contributions: dict[str, float] = sample.get("contributions", {})
        if contributions:
            sorted_c = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:15])
            rows = [{"Feature": k, "SHAP Value": f"{v:+.4f}"} for k, v in sorted_c.items()]
            st.table(rows)
            base_value = sample.get("base_value")
            prediction = sample.get("prediction")
            if base_value is not None:
                st.caption(f"Base value: {base_value:.4f}  |  Prediction: {prediction}")


def _render_pdp_section() -> None:
    """Partial Dependence & ICE plots."""
    st.subheader("Partial Dependence Plots")

    pdp_data: dict[str, Any] = st.session_state.get("explainability_results", {}).get("pdp", {})
    if not pdp_data:
        feature_list: list[str] = st.session_state.get("feature_list", [])
        if feature_list:
            selected_feat = st.selectbox("Select feature for PDP", feature_list, key="pdp_feature")
            st.info(
                f"PDP for '{selected_feat}' not yet computed. "
                "Connect the Explainability Agent to generate."
            )
        else:
            st.info("Feature list not available. Complete modeling first.")
        return

    # Display pre-computed PDP figures
    for feat_name, fig in pdp_data.items():
        if fig is not None:
            from dashboard.components.chart_container import render_chart

            render_chart(fig, title=f"PDP -- {feat_name}", key=f"pdp_{feat_name}")


def _render_counterfactual_section() -> None:
    """Counterfactual explanations."""
    st.subheader("Counterfactual Explanations")

    examples: list[dict] | None = st.session_state.get("counterfactual_examples")
    if not examples:
        st.info("No counterfactual examples generated yet.")
        return

    st.caption("What minimal changes would flip the prediction?")
    for i, cf in enumerate(examples[:10]):
        with st.expander(f"Example {i + 1}"):
            original = cf.get("original", {})
            changed = cf.get("counterfactual", {})
            changes = cf.get("changes", {})

            if changes:
                rows = []
                for feat, info in changes.items():
                    rows.append({
                        "Feature": feat,
                        "Original": str(info.get("from", original.get(feat, ""))),
                        "Changed To": str(info.get("to", changed.get(feat, ""))),
                    })
                st.table(rows)

            orig_pred = cf.get("original_prediction")
            new_pred = cf.get("counterfactual_prediction")
            if orig_pred is not None:
                st.caption(f"Prediction: {orig_pred} -> {new_pred}")


def _render_fairness_section() -> None:
    """Fairness audit results."""
    st.subheader("Fairness Audit")

    report: dict[str, Any] | None = st.session_state.get("fairness_report")
    if not report:
        st.info("Fairness audit not yet run. Connect the Explainability Agent.")
        return

    # Overall assessment
    overall = report.get("overall_assessment", "")
    if overall:
        if "pass" in overall.lower():
            st.success(f"Fairness Assessment: {overall}")
        elif "fail" in overall.lower() or "violation" in overall.lower():
            st.error(f"Fairness Assessment: {overall}")
        else:
            st.warning(f"Fairness Assessment: {overall}")

    # Per-group metrics
    group_metrics: dict[str, dict] = report.get("group_metrics", {})
    if group_metrics:
        for group_attr, metrics in group_metrics.items():
            with st.expander(f"Attribute: {group_attr}"):
                if isinstance(metrics, dict):
                    rows = [{"Metric": k, "Value": f"{v:.4f}" if isinstance(v, float) else str(v)}
                            for k, v in metrics.items()]
                    st.table(rows)
                elif isinstance(metrics, pd.DataFrame):
                    st.dataframe(metrics, use_container_width=True)

    # Recommendations
    recommendations: list[str] = report.get("recommendations", [])
    if recommendations:
        st.markdown("**Recommendations:**")
        for rec in recommendations:
            st.markdown(f"- {rec}")


def _render_whatif_section() -> None:
    """Interactive what-if analysis: tweak features, see prediction change."""
    st.subheader("What-If Analysis")

    feature_list: list[str] = st.session_state.get("feature_list", [])
    if not feature_list:
        st.info("Feature list not available. Complete modeling first.")
        return

    df: pd.DataFrame = st.session_state["uploaded_data"]
    target = st.session_state.get("target_column")

    # Let user pick a baseline row
    max_row = min(len(df) - 1, 999)
    row_idx = st.number_input("Baseline row index", min_value=0, max_value=max_row, value=0, key="whatif_row")
    baseline = df.iloc[int(row_idx)]

    # Feature sliders/inputs
    st.caption("Adjust feature values and observe predicted outcome changes.")
    modified_values: dict[str, Any] = {}
    cols_per_row = 3

    display_features = [f for f in feature_list if f != target][:12]
    for row_start in range(0, len(display_features), cols_per_row):
        row_feats = display_features[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, feat in zip(cols, row_feats):
            original_val = baseline.get(feat)
            with col:
                if pd.api.types.is_numeric_dtype(df[feat]):
                    feat_min = float(df[feat].min())
                    feat_max = float(df[feat].max())
                    default = float(original_val) if pd.notna(original_val) else feat_min
                    default = max(feat_min, min(feat_max, default))
                    modified_values[feat] = st.slider(
                        feat, feat_min, feat_max, default, key=f"whatif_{feat}",
                    )
                else:
                    options = list(df[feat].dropna().unique()[:50])
                    default_idx = 0
                    if original_val in options:
                        default_idx = options.index(original_val)
                    modified_values[feat] = st.selectbox(
                        feat, options, index=default_idx, key=f"whatif_{feat}",
                    )

    st.caption("Connect the Explainability Agent for live what-if predictions.")


def _render_model_card() -> None:
    """Display generated model card."""
    card: dict[str, Any] | None = st.session_state.get("model_card")
    if not card:
        return

    st.subheader("Model Card")

    sections = [
        ("Model Details", "model_details"),
        ("Intended Use", "intended_use"),
        ("Training Data", "training_data"),
        ("Evaluation Results", "evaluation_results"),
        ("Ethical Considerations", "ethical_considerations"),
        ("Limitations", "limitations"),
    ]

    for title, key in sections:
        content = card.get(key)
        if content:
            with st.expander(title, expanded=key == "model_details"):
                if isinstance(content, dict):
                    for k, v in content.items():
                        st.markdown(f"**{k}:** {v}")
                elif isinstance(content, list):
                    for item in content:
                        st.markdown(f"- {item}")
                else:
                    st.markdown(str(content))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Model Explainability")
    _render_progress()

    tab_shap, tab_pdp, tab_cf, tab_fair, tab_whatif, tab_card = st.tabs([
        "SHAP",
        "PDP / ICE",
        "Counterfactuals",
        "Fairness",
        "What-If",
        "Model Card",
    ])

    with tab_shap:
        _render_shap_section()
    with tab_pdp:
        _render_pdp_section()
    with tab_cf:
        _render_counterfactual_section()
    with tab_fair:
        _render_fairness_section()
    with tab_whatif:
        _render_whatif_section()
    with tab_card:
        _render_model_card()

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Modeling", use_container_width=True):
            st.switch_page("pages/05_modeling.py")
    with col_next:
        if st.button("Proceed to Predictions", type="primary", use_container_width=True):
            st.switch_page("pages/07_predict.py")


_page()
