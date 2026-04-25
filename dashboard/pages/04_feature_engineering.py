"""Page 04 -- Feature Engineering.

Per-column decision table for imputation, encoding, scaling, and outlier
handling.  Domain-specific feature checkboxes and a preliminary feature
importance chart.

Premium dark luxury UI with glass morphism cards and gradient accents.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from core.constants import (
    ENCODING_STRATEGIES,
    IMPUTATION_STRATEGIES,
    MODE_AUTO,
    SCALING_STRATEGIES,
)

logger = logging.getLogger(__name__)

_OUTLIER_STRATEGIES: dict[str, str] = {
    "keep": "Keep",
    "cap": "Cap (Winsorize)",
    "remove": "Remove rows",
}


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

_DARK_LUXURY_CSS = """
<style>
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

:root {
    --bg-primary: #0a0a0f;
    --bg-card: #12121a;
    --bg-elevated: #16161f;
    --border-subtle: rgba(99,102,241,0.12);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-primary: #6366f1;
    --accent-secondary: #0ea5e9;
    --accent-success: #22c55e;
    --accent-warning: #f59e0b;
    --accent-danger: #ef4444;
    --gradient-primary: linear-gradient(135deg, #6366f1, #0ea5e9);
    --radius-md: 12px;
    --shadow-card: 0 4px 24px rgba(0,0,0,0.25);
}

.stApp {
    background-color: var(--bg-primary) !important;
}

/* --- Page header --- */
.fe-page-header {
    padding: 32px 0 24px 0;
}
.fe-page-header h1 {
    font-size: 2.25rem;
    font-weight: 700;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.02em;
}
.fe-page-header .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 4px;
}

/* --- Section headers --- */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    margin-bottom: 16px;
    padding-bottom: 8px;
    position: relative;
}
.section-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 48px;
    height: 2px;
    background: var(--gradient-primary);
    border-radius: 1px;
}

/* --- Glass card --- */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 16px;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}

/* --- Glass table --- */
.glass-table-wrapper {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-card);
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}

.glass-table-header {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 2fr 2fr 2fr 2fr;
    gap: 0;
    background: var(--bg-elevated);
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-subtle);
}
.glass-table-header span {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

.glass-table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 2fr 2fr 2fr 2fr;
    gap: 0;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(99,102,241,0.06);
    transition: background-color 0.15s ease;
    align-items: center;
}
.glass-table-row:nth-child(even) {
    background: rgba(22,22,31,0.5);
}
.glass-table-row:hover {
    background: rgba(99,102,241,0.06);
}
.glass-table-row .col-name {
    color: var(--text-primary);
    font-size: 0.85rem;
    font-weight: 500;
}
.glass-table-row .col-type {
    color: var(--text-muted);
    font-size: 0.8rem;
}
.glass-table-row .col-missing {
    font-size: 0.8rem;
}
.missing-low { color: var(--accent-success); }
.missing-med { color: var(--accent-warning); }
.missing-high { color: var(--accent-danger); }

/* --- Domain feature card --- */
.domain-feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    margin-bottom: 12px;
}
.domain-feature-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}
.domain-feature-name {
    color: var(--text-primary);
    font-size: 0.9rem;
    font-weight: 600;
}
.domain-feature-desc {
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-top: 4px;
}

/* --- Importance chart container --- */
.importance-chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-top: 3px solid transparent;
    border-image: var(--gradient-primary) 1;
    border-image-slice: 1 1 0 1;
    border-radius: var(--radius-md);
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    margin-bottom: 16px;
}
.importance-chart-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
}

/* --- Strategy pills --- */
.strategy-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-right: 8px;
    margin-bottom: 6px;
}
.pill-imputation { background: rgba(99,102,241,0.15); color: #818cf8; }
.pill-encoding { background: rgba(14,165,233,0.15); color: #38bdf8; }
.pill-scaling { background: rgba(34,197,94,0.15); color: #4ade80; }
.pill-outlier { background: rgba(245,158,11,0.15); color: #fbbf24; }

/* --- Divider --- */
.fe-divider {
    border: none;
    border-top: 1px solid var(--border-subtle);
    margin: 32px 0;
}

/* --- Streamlit input overrides --- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div {
    background-color: var(--bg-elevated) !important;
    border-color: var(--border-subtle) !important;
    color: var(--text-primary) !important;
}

/* --- Status dot --- */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-dot.info { background-color: var(--accent-secondary); }

/* --- Info placeholder --- */
.info-placeholder {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recommend_imputation(series: pd.Series) -> str:
    """Heuristic default imputation strategy."""
    if series.isna().sum() == 0:
        return "mean"
    if pd.api.types.is_numeric_dtype(series):
        if series.skew() > 1.5:
            return "median"
        return "mean"
    return "mode"


def _recommend_encoding(series: pd.Series) -> str:
    """Heuristic default encoding strategy."""
    if pd.api.types.is_numeric_dtype(series):
        return "onehot"  # placeholder -- won't be applied to numerics
    nunique = series.nunique()
    if nunique <= 2:
        return "label"
    if nunique <= 10:
        return "onehot"
    if nunique <= 50:
        return "target"
    return "hash"


def _recommend_outlier(series: pd.Series) -> str:
    """Heuristic default outlier strategy."""
    if not pd.api.types.is_numeric_dtype(series):
        return "keep"
    if series.nunique() <= 10:
        return "keep"
    return "cap"


def _missing_class(pct: float) -> str:
    """Return CSS class for missing percentage."""
    if pct < 5:
        return "missing-low"
    if pct < 20:
        return "missing-med"
    return "missing-high"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_progress() -> None:
    from dashboard.components.workflow_progress import render_mini_progress

    state = {
        "completed_steps": st.session_state.get("completed_steps", []),
        "current_step": st.session_state.get("current_step", "feature_engineering"),
        "workflow_status": st.session_state.get("workflow_status", "running"),
    }
    with st.sidebar:
        render_mini_progress(state)


def _render_column_decisions(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Render the per-column decision table and return choices."""
    st.markdown('<div class="section-header">Per-Column Decisions</div>', unsafe_allow_html=True)
    mode = st.session_state.get("user_mode", "guided")
    is_readonly = mode == MODE_AUTO

    if is_readonly:
        st.markdown(
            '<div class="info-placeholder">'
            '<span class="status-dot info"></span>'
            'Auto mode -- the system has chosen optimal settings for each column.'
            '</div>',
            unsafe_allow_html=True,
        )

    existing_choices: dict[str, dict[str, str]] = st.session_state.get("fe_choices", {})

    impute_labels = list(IMPUTATION_STRATEGIES.values())
    impute_keys = list(IMPUTATION_STRATEGIES.keys())
    encode_labels = list(ENCODING_STRATEGIES.values())
    encode_keys = list(ENCODING_STRATEGIES.keys())
    scale_labels = list(SCALING_STRATEGIES.values())
    scale_keys = list(SCALING_STRATEGIES.keys())
    outlier_labels = list(_OUTLIER_STRATEGIES.values())
    outlier_keys = list(_OUTLIER_STRATEGIES.keys())

    target = st.session_state.get("target_column")
    decisions: dict[str, dict[str, str]] = {}

    # Glass table header (visual only)
    st.markdown(
        """
        <div class="glass-table-wrapper">
            <div class="glass-table-header">
                <span>Column</span>
                <span>Type</span>
                <span>Missing %</span>
                <span>Imputation</span>
                <span>Encoding</span>
                <span>Scaling</span>
                <span>Outliers</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit columns for interactive dropdowns
    for col_idx, col in enumerate(df.columns):
        if col == target:
            continue

        series = df[col]
        missing_pct = series.isna().mean() * 100
        prev = existing_choices.get(col, {})
        m_class = _missing_class(missing_pct)

        # Row info (rendered as markdown for context)
        row_cols = st.columns([2, 1, 1, 2, 2, 2, 2])
        row_cols[0].markdown(
            f'<span style="color: var(--text-primary); font-weight: 500; font-size: 0.85rem;">{col}</span>',
            unsafe_allow_html=True,
        )
        row_cols[1].markdown(
            f'<span style="color: var(--text-muted); font-size: 0.8rem;">{series.dtype}</span>',
            unsafe_allow_html=True,
        )
        row_cols[2].markdown(
            f'<span class="{m_class}" style="font-size: 0.8rem;">{missing_pct:.1f}%</span>',
            unsafe_allow_html=True,
        )

        # Imputation
        rec_imp = prev.get("imputation", _recommend_imputation(series))
        imp_idx = impute_keys.index(rec_imp) if rec_imp in impute_keys else 0
        imp = row_cols[3].selectbox(
            "imp", impute_labels, index=imp_idx,
            key=f"fe_imp_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Encoding
        rec_enc = prev.get("encoding", _recommend_encoding(series))
        enc_idx = encode_keys.index(rec_enc) if rec_enc in encode_keys else 0
        enc = row_cols[4].selectbox(
            "enc", encode_labels, index=enc_idx,
            key=f"fe_enc_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Scaling
        rec_scale = prev.get("scaling", "robust")
        sc_idx = scale_keys.index(rec_scale) if rec_scale in scale_keys else 0
        sc = row_cols[5].selectbox(
            "sc", scale_labels, index=sc_idx,
            key=f"fe_sc_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Outlier
        rec_out = prev.get("outlier", _recommend_outlier(series))
        out_idx = outlier_keys.index(rec_out) if rec_out in outlier_keys else 0
        out = row_cols[6].selectbox(
            "out", outlier_labels, index=out_idx,
            key=f"fe_out_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        decisions[col] = {
            "imputation": impute_keys[impute_labels.index(imp)],
            "encoding": encode_keys[encode_labels.index(enc)],
            "scaling": scale_keys[scale_labels.index(sc)],
            "outlier": outlier_keys[outlier_labels.index(out)],
        }

    # Strategy recommendation pills summary
    if decisions:
        st.markdown('<div style="margin-top: 16px;">', unsafe_allow_html=True)
        strategies_used: dict[str, set[str]] = {
            "imputation": set(),
            "encoding": set(),
            "scaling": set(),
            "outlier": set(),
        }
        for d in decisions.values():
            for k, v in d.items():
                strategies_used[k].add(v)

        pill_classes = {
            "imputation": "pill-imputation",
            "encoding": "pill-encoding",
            "scaling": "pill-scaling",
            "outlier": "pill-outlier",
        }
        pills_html = ""
        for category, values in strategies_used.items():
            for v in sorted(values):
                pills_html += f'<span class="strategy-pill {pill_classes[category]}">{category}: {v}</span>'
        st.markdown(pills_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    return decisions


def _render_domain_features() -> list[str]:
    """Render domain-specific feature checkboxes."""
    domain = st.session_state.get("detected_domain", "generic")
    domain_features = st.session_state.get("domain_feature_suggestions", [])

    if not domain_features:
        domain_features = _get_default_domain_features(domain)

    if not domain_features:
        return []

    st.markdown('<div class="section-header">Domain-Specific Features</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 16px;">'
        f'Recommended for the <strong style="color: var(--text-secondary);">{domain}</strong> domain.</p>',
        unsafe_allow_html=True,
    )

    selected: list[str] = []
    for feat in domain_features:
        name = feat if isinstance(feat, str) else feat.get("name", "")
        desc = "" if isinstance(feat, str) else feat.get("description", "")
        recommended = True if isinstance(feat, str) else feat.get("recommended", True)

        # Render feature info above checkbox
        st.markdown(
            f"""
            <div class="domain-feature-card">
                <div class="domain-feature-name">{name}</div>
                {"<div class='domain-feature-desc'>" + desc + "</div>" if desc else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.checkbox(f"Enable {name}", value=recommended, key=f"domain_feat_{name}"):
            selected.append(name)
    return selected


def _get_default_domain_features(domain: str) -> list[dict[str, Any]]:
    """Fallback domain features when none come from the agent."""
    mapping: dict[str, list[dict[str, Any]]] = {
        "healthcare": [
            {"name": "charlson_index", "description": "Charlson Comorbidity Index", "recommended": True},
            {"name": "age_group", "description": "Binned age groups", "recommended": True},
        ],
        "finance": [
            {"name": "debt_to_income", "description": "Debt-to-Income ratio", "recommended": True},
            {"name": "credit_utilization", "description": "Credit utilization ratio", "recommended": True},
        ],
        "ecommerce": [
            {"name": "rfm_scores", "description": "RFM (Recency, Frequency, Monetary)", "recommended": True},
            {"name": "clv_estimate", "description": "Customer lifetime value", "recommended": True},
        ],
        "manufacturing": [
            {"name": "oee", "description": "Overall Equipment Effectiveness", "recommended": True},
        ],
    }
    return mapping.get(domain, [])


def _render_importance_preview() -> None:
    """Show preliminary feature importance if available."""
    importance: dict[str, float] = st.session_state.get("feature_importance_preliminary", {})
    if not importance:
        return

    from dashboard.components.chart_container import render_chart

    st.markdown('<div class="section-header">Preliminary Feature Importance</div>', unsafe_allow_html=True)

    try:
        import plotly.express as px  # type: ignore[import-untyped]

        sorted_imp = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20])
        fig = px.bar(
            x=list(sorted_imp.values()),
            y=list(sorted_imp.keys()),
            orientation="h",
            labels={"x": "Importance", "y": "Feature"},
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(18,18,26,0.8)",
            font=dict(color="#94a3b8"),
            xaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
            yaxis_gridcolor="rgba(99,102,241,0.08)",
        )
        fig.update_traces(marker_color="#6366f1")
        render_chart(fig, title="Preliminary Feature Importance", key="fe_importance")
    except ImportError:
        st.warning("Install plotly to see the importance chart.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()

    # Inject CSS
    st.markdown(_DARK_LUXURY_CSS, unsafe_allow_html=True)

    # Page header
    st.markdown(
        """
        <div class="fe-page-header">
            <h1>Feature Engineering</h1>
            <div class="subtitle">Per-column transformation decisions with domain-aware recommendations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_progress()

    df: pd.DataFrame = st.session_state["uploaded_data"]

    # Per-column decisions
    decisions = _render_column_decisions(df)

    st.markdown('<hr class="fe-divider">', unsafe_allow_html=True)

    # Domain-specific features
    selected_domain_feats = _render_domain_features()

    st.markdown('<hr class="fe-divider">', unsafe_allow_html=True)

    # Importance preview
    _render_importance_preview()

    st.markdown('<hr class="fe-divider">', unsafe_allow_html=True)

    # Approval
    from dashboard.components.approval_widget import render_approval_widget

    flat_summary = {f"{col} imputation": v["imputation"] for col, v in list(decisions.items())[:5]}
    flat_summary["... and more columns"] = f"({len(decisions)} total)"

    approved = render_approval_widget(
        step_name="Feature Engineering",
        decisions=flat_summary,
        reasoning="Recommendations are based on column types, missing rates, and domain best practices.",
        key_prefix="fe",
    )

    if approved:
        st.session_state["fe_choices"] = decisions
        st.session_state["domain_features_selected"] = selected_domain_feats

    # Navigation
    st.markdown('<hr class="fe-divider">', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Back to EDA", use_container_width=True):
            st.switch_page("pages/03_eda_interactive.py")
    with col_next:
        if st.button(
            "Proceed to Modeling",
            type="primary",
            use_container_width=True,
            disabled=not approved,
        ):
            st.switch_page("pages/05_modeling.py")


_page()
