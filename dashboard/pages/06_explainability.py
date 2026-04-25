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
# Design tokens
# ---------------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

section[data-testid="stMain"] { background: #0a0a0f; }
.stApp { background: #0a0a0f; color: #f1f5f9; font-family: 'Inter', sans-serif; }
header[data-testid="stHeader"] { background: transparent; }

/* Hide default Streamlit chrome */
.stDeployButton, #MainMenu { display: none; }

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    position: relative;
}
.section-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 48px;
    height: 2px;
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    border-radius: 1px;
}

/* Glass card */
.glass-card {
    background: rgba(18, 18, 26, 0.8);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    transition: border-color 0.2s ease;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.25);
}

/* Glass pill tabs */
.pill-tabs {
    display: flex;
    gap: 0.5rem;
    padding: 0.375rem;
    background: rgba(18, 18, 26, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.pill-tab {
    padding: 0.5rem 1.25rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid transparent;
    background: transparent;
    text-align: center;
    flex: 1;
    min-width: 100px;
}
.pill-tab:hover {
    color: #f1f5f9;
    background: rgba(99,102,241,0.08);
}
.pill-tab.active {
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(14,165,233,0.15));
    color: #f1f5f9;
    border-color: rgba(99,102,241,0.3);
    box-shadow: 0 0 12px rgba(99,102,241,0.15);
}

/* Chart container */
.chart-container {
    background: rgba(22, 22, 31, 0.6);
    border: 1px solid rgba(99,102,241,0.08);
    border-radius: 12px;
    padding: 1rem;
    margin: 0.5rem 0;
}

/* Glass table */
.glass-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
}
.glass-table thead th {
    background: rgba(99,102,241,0.08);
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid rgba(99,102,241,0.12);
    text-align: left;
}
.glass-table thead th:first-child { border-radius: 8px 0 0 0; }
.glass-table thead th:last-child { border-radius: 0 8px 0 0; }
.glass-table tbody td {
    padding: 0.625rem 1rem;
    color: #f1f5f9;
    border-bottom: 1px solid rgba(99,102,241,0.06);
}
.glass-table tbody tr:hover td {
    background: rgba(99,102,241,0.04);
}

/* Status indicators */
.status-pass {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(34,197,94,0.12);
    color: #22c55e;
    border: 1px solid rgba(34,197,94,0.2);
}
.status-fail {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(239,68,68,0.12);
    color: #ef4444;
    border: 1px solid rgba(239,68,68,0.2);
}
.status-warn {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(245,158,11,0.12);
    color: #f59e0b;
    border: 1px solid rgba(245,158,11,0.2);
}

/* Model card section */
.model-card-section {
    background: rgba(22, 22, 31, 0.5);
    border-left: 3px solid rgba(99,102,241,0.4);
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.model-card-section h4 {
    color: #f1f5f9;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* Before/after comparison */
.compare-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 1rem;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(99,102,241,0.06);
}
.compare-arrow {
    color: #6366f1;
    font-weight: 700;
    font-size: 1.1rem;
}
.compare-original { color: #94a3b8; }
.compare-changed { color: #0ea5e9; font-weight: 500; }

/* Override Streamlit widgets */
div[data-testid="stExpander"] {
    background: rgba(18, 18, 26, 0.6);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 12px;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    color: #f1f5f9;
    font-weight: 500;
}

.stNumberInput > div, .stSelectbox > div {
    background: rgba(18, 18, 26, 0.6);
    border-radius: 8px;
}
.stNumberInput input, .stSelectbox select {
    color: #f1f5f9 !important;
    background: rgba(22, 22, 31, 0.8) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 8px !important;
}

.stSlider > div > div { background: rgba(99,102,241,0.2); }
.stSlider > div > div > div { background: #6366f1; }

/* Navigation buttons */
.nav-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.625rem 1.5rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    width: 100%;
    text-align: center;
}
.nav-btn-secondary {
    background: rgba(18, 18, 26, 0.8);
    border: 1px solid rgba(99,102,241,0.15);
    color: #94a3b8;
}
.nav-btn-secondary:hover { border-color: rgba(99,102,241,0.3); color: #f1f5f9; }
.nav-btn-primary {
    background: linear-gradient(135deg, #6366f1, #0ea5e9);
    border: none;
    color: #ffffff;
}
.nav-btn-primary:hover { box-shadow: 0 0 20px rgba(99,102,241,0.3); }

/* Info/warning/success/error overrides */
div[data-testid="stAlert"] {
    background: rgba(18, 18, 26, 0.6) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}

/* Streamlit tab overrides to hide defaults */
.stTabs [data-baseweb="tab-list"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding: 0; }

/* Caption style */
.glass-caption {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.25rem;
}

/* Page title */
.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
}
.page-subtitle {
    font-size: 0.9rem;
    color: #64748b;
    margin-bottom: 1.5rem;
}
</style>
"""


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

    st.markdown('<div class="section-header">SHAP Feature Explanations</div>', unsafe_allow_html=True)

    if not shap_data and not explainability.get("shap"):
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:#94a3b8; margin:0;">SHAP values not computed yet. '
            'Connect the Explainability Agent to generate SHAP explanations.</p>'
            '</div>',
            unsafe_allow_html=True,
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
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                height=450,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(22,22,31,0.6)",
                font=dict(color="#94a3b8"),
            )
            st.markdown('<div class="glass-card"><div class="chart-container">', unsafe_allow_html=True)
            render_chart(fig, title="SHAP Global Feature Importance", key="shap_global")
            st.markdown('</div></div>', unsafe_allow_html=True)
        except ImportError:
            st.warning("Install plotly for SHAP charts.")

    # SHAP summary chart (if pre-rendered figure stored)
    summary_fig = shap_info.get("summary_figure")
    if summary_fig is not None:
        from dashboard.components.chart_container import render_chart

        st.markdown('<div class="glass-card"><div class="chart-container">', unsafe_allow_html=True)
        render_chart(summary_fig, title="SHAP Summary Plot", key="shap_summary")
        st.markdown('</div></div>', unsafe_allow_html=True)

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
            # Render as glass table
            rows_html = ""
            for feat, val in sorted_c.items():
                val_color = "#22c55e" if val >= 0 else "#ef4444"
                rows_html += (
                    f'<tr><td>{feat}</td>'
                    f'<td style="color:{val_color}; font-weight:500;">{val:+.4f}</td></tr>'
                )
            table_html = (
                '<div class="glass-card">'
                '<table class="glass-table"><thead><tr>'
                '<th>Feature</th><th>SHAP Value</th>'
                '</tr></thead><tbody>'
                f'{rows_html}'
                '</tbody></table>'
                '</div>'
            )
            st.markdown(table_html, unsafe_allow_html=True)

            base_value = sample.get("base_value")
            prediction = sample.get("prediction")
            if base_value is not None:
                st.markdown(
                    f'<p class="glass-caption">Base value: {base_value:.4f}  |  Prediction: {prediction}</p>',
                    unsafe_allow_html=True,
                )


def _render_pdp_section() -> None:
    """Partial Dependence & ICE plots."""
    st.markdown('<div class="section-header">Partial Dependence Plots</div>', unsafe_allow_html=True)

    pdp_data: dict[str, Any] = st.session_state.get("explainability_results", {}).get("pdp", {})
    if not pdp_data:
        feature_list: list[str] = st.session_state.get("feature_list", [])
        if feature_list:
            selected_feat = st.selectbox("Select feature for PDP", feature_list, key="pdp_feature")
            st.markdown(
                f'<div class="glass-card">'
                f'<p style="color:#94a3b8; margin:0;">PDP for \'{selected_feat}\' not yet computed. '
                f'Connect the Explainability Agent to generate.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="glass-card">'
                '<p style="color:#94a3b8; margin:0;">Feature list not available. Complete modeling first.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        return

    for feat_name, fig in pdp_data.items():
        if fig is not None:
            from dashboard.components.chart_container import render_chart

            st.markdown('<div class="glass-card"><div class="chart-container">', unsafe_allow_html=True)
            render_chart(fig, title=f"PDP -- {feat_name}", key=f"pdp_{feat_name}")
            st.markdown('</div></div>', unsafe_allow_html=True)


def _render_counterfactual_section() -> None:
    """Counterfactual explanations."""
    st.markdown('<div class="section-header">Counterfactual Explanations</div>', unsafe_allow_html=True)

    examples: list[dict] | None = st.session_state.get("counterfactual_examples")
    if not examples:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:#94a3b8; margin:0;">No counterfactual examples generated yet.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<p class="glass-caption">What minimal changes would flip the prediction?</p>', unsafe_allow_html=True)

    for i, cf in enumerate(examples[:10]):
        with st.expander(f"Example {i + 1}"):
            original = cf.get("original", {})
            changed = cf.get("counterfactual", {})
            changes = cf.get("changes", {})

            if changes:
                rows_html = ""
                for feat, info in changes.items():
                    orig_val = str(info.get("from", original.get(feat, "")))
                    new_val = str(info.get("to", changed.get(feat, "")))
                    rows_html += (
                        f'<div class="compare-row">'
                        f'<div class="compare-original">{orig_val}</div>'
                        f'<div class="compare-arrow">--></div>'
                        f'<div class="compare-changed">{new_val}</div>'
                        f'</div>'
                    )
                header_html = (
                    '<div class="compare-row" style="border-bottom: 1px solid rgba(99,102,241,0.15);">'
                    '<div style="color:#64748b; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Original</div>'
                    '<div style="color:#64748b; font-size:0.7rem;">Feature: ' + feat + '</div>'
                    '<div style="color:#64748b; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">Changed To</div>'
                    '</div>'
                )
                # Build a proper table instead
                table_rows = ""
                for feat, info in changes.items():
                    orig_val = str(info.get("from", original.get(feat, "")))
                    new_val = str(info.get("to", changed.get(feat, "")))
                    table_rows += (
                        f'<tr><td style="font-weight:500;">{feat}</td>'
                        f'<td class="compare-original">{orig_val}</td>'
                        f'<td style="color:#6366f1; font-weight:700; text-align:center;">--></td>'
                        f'<td class="compare-changed">{new_val}</td></tr>'
                    )
                st.markdown(
                    '<div class="glass-card">'
                    '<table class="glass-table"><thead><tr>'
                    '<th>Feature</th><th>Original</th><th></th><th>Changed To</th>'
                    '</tr></thead><tbody>'
                    f'{table_rows}'
                    '</tbody></table></div>',
                    unsafe_allow_html=True,
                )

            orig_pred = cf.get("original_prediction")
            new_pred = cf.get("counterfactual_prediction")
            if orig_pred is not None:
                st.markdown(
                    f'<p class="glass-caption">Prediction: '
                    f'<span style="color:#ef4444;">{orig_pred}</span> --> '
                    f'<span style="color:#22c55e;">{new_pred}</span></p>',
                    unsafe_allow_html=True,
                )


def _render_fairness_section() -> None:
    """Fairness audit results."""
    st.markdown('<div class="section-header">Fairness Audit</div>', unsafe_allow_html=True)

    report: dict[str, Any] | None = st.session_state.get("fairness_report")
    if not report:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:#94a3b8; margin:0;">Fairness audit not yet run. Connect the Explainability Agent.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Overall assessment
    overall = report.get("overall_assessment", "")
    if overall:
        if "pass" in overall.lower():
            badge = '<span class="status-pass">PASS</span>'
        elif "fail" in overall.lower() or "violation" in overall.lower():
            badge = '<span class="status-fail">FAIL</span>'
        else:
            badge = '<span class="status-warn">REVIEW</span>'

        st.markdown(
            f'<div class="glass-card" style="display:flex; align-items:center; gap:1rem;">'
            f'{badge}'
            f'<span style="color:#f1f5f9; font-weight:500;">{overall}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Per-group metrics
    group_metrics: dict[str, dict] = report.get("group_metrics", {})
    if group_metrics:
        for group_attr, metrics in group_metrics.items():
            with st.expander(f"Attribute: {group_attr}"):
                if isinstance(metrics, dict):
                    rows_html = ""
                    for k, v in metrics.items():
                        val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                        rows_html += f'<tr><td>{k}</td><td style="color:#0ea5e9;">{val_str}</td></tr>'
                    st.markdown(
                        '<div class="glass-card">'
                        '<table class="glass-table"><thead><tr>'
                        '<th>Metric</th><th>Value</th>'
                        '</tr></thead><tbody>'
                        f'{rows_html}'
                        '</tbody></table></div>',
                        unsafe_allow_html=True,
                    )
                elif isinstance(metrics, pd.DataFrame):
                    st.dataframe(metrics, use_container_width=True)

    # Recommendations
    recommendations: list[str] = report.get("recommendations", [])
    if recommendations:
        recs_html = '<div class="glass-card"><div class="section-header">Recommendations</div>'
        for rec in recommendations:
            recs_html += f'<p style="color:#94a3b8; margin:0.4rem 0; padding-left:0.75rem; border-left:2px solid rgba(99,102,241,0.3);">{rec}</p>'
        recs_html += '</div>'
        st.markdown(recs_html, unsafe_allow_html=True)


def _render_whatif_section() -> None:
    """Interactive what-if analysis: tweak features, see prediction change."""
    st.markdown('<div class="section-header">What-If Analysis</div>', unsafe_allow_html=True)

    feature_list: list[str] = st.session_state.get("feature_list", [])
    if not feature_list:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:#94a3b8; margin:0;">Feature list not available. Complete modeling first.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    df: pd.DataFrame = st.session_state["uploaded_data"]
    target = st.session_state.get("target_column")

    # Let user pick a baseline row
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    max_row = min(len(df) - 1, 999)
    row_idx = st.number_input("Baseline row index", min_value=0, max_value=max_row, value=0, key="whatif_row")
    baseline = df.iloc[int(row_idx)]
    st.markdown('</div>', unsafe_allow_html=True)

    # Feature sliders/inputs
    st.markdown('<p class="glass-caption">Adjust feature values and observe predicted outcome changes.</p>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<p class="glass-caption">Connect the Explainability Agent for live what-if predictions.</p>',
        unsafe_allow_html=True,
    )


def _render_model_card() -> None:
    """Display generated model card."""
    card: dict[str, Any] | None = st.session_state.get("model_card")
    if not card:
        st.markdown(
            '<div class="glass-card">'
            '<p style="color:#94a3b8; margin:0;">Model card not yet generated.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="section-header">Model Card</div>', unsafe_allow_html=True)

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
            inner = ""
            if isinstance(content, dict):
                for k, v in content.items():
                    inner += f'<p style="color:#94a3b8; margin:0.3rem 0;"><span style="color:#f1f5f9; font-weight:500;">{k}:</span> {v}</p>'
            elif isinstance(content, list):
                for item in content:
                    inner += f'<p style="color:#94a3b8; margin:0.2rem 0; padding-left:0.75rem; border-left:2px solid rgba(99,102,241,0.2);">{item}</p>'
            else:
                inner = f'<p style="color:#94a3b8; margin:0;">{content}</p>'

            st.markdown(
                f'<div class="model-card-section">'
                f'<h4>{title}</h4>'
                f'{inner}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tab navigation helper
# ---------------------------------------------------------------------------

_TAB_NAMES = ["SHAP", "PDP / ICE", "Counterfactuals", "Fairness", "What-If", "Model Card"]
_TAB_KEYS = ["shap", "pdp", "cf", "fair", "whatif", "card"]


def _render_pill_tabs() -> str:
    """Render glass pill tab navigation and return active tab key."""
    if "explain_active_tab" not in st.session_state:
        st.session_state["explain_active_tab"] = "shap"

    # Render buttons as columns to capture clicks
    cols = st.columns(len(_TAB_NAMES))
    for i, (name, key) in enumerate(zip(_TAB_NAMES, _TAB_KEYS)):
        with cols[i]:
            if st.button(name, key=f"extab_{key}", use_container_width=True):
                st.session_state["explain_active_tab"] = key
                st.rerun()

    # Visual indicator via HTML
    active = st.session_state["explain_active_tab"]
    pills_html = '<div class="pill-tabs">'
    for name, key in zip(_TAB_NAMES, _TAB_KEYS):
        active_cls = " active" if key == active else ""
        pills_html += f'<div class="pill-tab{active_cls}">{name}</div>'
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    return active


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Model Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Understand model decisions through SHAP, counterfactuals, fairness audits, and more</div>', unsafe_allow_html=True)
    _render_progress()

    active_tab = _render_pill_tabs()

    # Use Streamlit tabs under the hood but only show the active one
    tab_shap, tab_pdp, tab_cf, tab_fair, tab_whatif, tab_card = st.tabs(_TAB_NAMES)

    if active_tab == "shap":
        with tab_shap:
            _render_shap_section()
    elif active_tab == "pdp":
        with tab_pdp:
            _render_pdp_section()
    elif active_tab == "cf":
        with tab_cf:
            _render_counterfactual_section()
    elif active_tab == "fair":
        with tab_fair:
            _render_fairness_section()
    elif active_tab == "whatif":
        with tab_whatif:
            _render_whatif_section()
    elif active_tab == "card":
        with tab_card:
            _render_model_card()

    # Navigation
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1px; background:rgba(99,102,241,0.1); margin:0.5rem 0 1.5rem;"></div>', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to Modeling", use_container_width=True):
            st.switch_page("pages/05_modeling.py")
    with col_next:
        if st.button("Proceed to Predictions", type="primary", use_container_width=True):
            st.switch_page("pages/07_predict.py")


_page()
