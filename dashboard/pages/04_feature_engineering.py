"""Page 04 -- Feature Engineering.

Per-column decision table for imputation, encoding, scaling, and outlier
handling.  Domain-specific feature checkboxes and a preliminary feature
importance chart.
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
    st.subheader("Per-Column Decisions")
    mode = st.session_state.get("user_mode", "guided")
    is_readonly = mode == MODE_AUTO

    if is_readonly:
        st.caption("Auto mode -- the system has chosen optimal settings for each column.")

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

    # Header row
    hdr = st.columns([2, 1, 1, 2, 2, 2, 2])
    hdr[0].markdown("**Column**")
    hdr[1].markdown("**Type**")
    hdr[2].markdown("**Missing %**")
    hdr[3].markdown("**Imputation**")
    hdr[4].markdown("**Encoding**")
    hdr[5].markdown("**Scaling**")
    hdr[6].markdown("**Outliers**")

    for col in df.columns:
        if col == target:
            continue

        series = df[col]
        missing_pct = series.isna().mean() * 100
        prev = existing_choices.get(col, {})

        cols = st.columns([2, 1, 1, 2, 2, 2, 2])
        cols[0].write(col)
        cols[1].write(str(series.dtype))
        cols[2].write(f"{missing_pct:.1f}%")

        # Imputation
        rec_imp = prev.get("imputation", _recommend_imputation(series))
        imp_idx = impute_keys.index(rec_imp) if rec_imp in impute_keys else 0
        imp = cols[3].selectbox(
            "imp", impute_labels, index=imp_idx,
            key=f"fe_imp_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Encoding
        rec_enc = prev.get("encoding", _recommend_encoding(series))
        enc_idx = encode_keys.index(rec_enc) if rec_enc in encode_keys else 0
        enc = cols[4].selectbox(
            "enc", encode_labels, index=enc_idx,
            key=f"fe_enc_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Scaling
        rec_scale = prev.get("scaling", "robust")
        sc_idx = scale_keys.index(rec_scale) if rec_scale in scale_keys else 0
        sc = cols[5].selectbox(
            "sc", scale_labels, index=sc_idx,
            key=f"fe_sc_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        # Outlier
        rec_out = prev.get("outlier", _recommend_outlier(series))
        out_idx = outlier_keys.index(rec_out) if rec_out in outlier_keys else 0
        out = cols[6].selectbox(
            "out", outlier_labels, index=out_idx,
            key=f"fe_out_{col}", label_visibility="collapsed", disabled=is_readonly,
        )

        decisions[col] = {
            "imputation": impute_keys[impute_labels.index(imp)],
            "encoding": encode_keys[encode_labels.index(enc)],
            "scaling": scale_keys[scale_labels.index(sc)],
            "outlier": outlier_keys[outlier_labels.index(out)],
        }

    return decisions


def _render_domain_features() -> list[str]:
    """Render domain-specific feature checkboxes."""
    domain = st.session_state.get("detected_domain", "generic")
    domain_features = st.session_state.get("domain_feature_suggestions", [])

    if not domain_features:
        domain_features = _get_default_domain_features(domain)

    if not domain_features:
        return []

    st.subheader("Domain-Specific Features")
    st.caption(f"Recommended for the **{domain}** domain.")

    selected: list[str] = []
    for feat in domain_features:
        name = feat if isinstance(feat, str) else feat.get("name", "")
        desc = "" if isinstance(feat, str) else feat.get("description", "")
        recommended = True if isinstance(feat, str) else feat.get("recommended", True)
        label = f"{name} -- {desc}" if desc else name
        if st.checkbox(label, value=recommended, key=f"domain_feat_{name}"):
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

    try:
        import plotly.express as px  # type: ignore[import-untyped]

        sorted_imp = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20])
        fig = px.bar(
            x=list(sorted_imp.values()),
            y=list(sorted_imp.keys()),
            orientation="h",
            labels={"x": "Importance", "y": "Feature"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=400)
        render_chart(fig, title="Preliminary Feature Importance", key="fe_importance")
    except ImportError:
        st.warning("Install plotly to see the importance chart.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page() -> None:
    _guard()
    st.header("Feature Engineering")
    _render_progress()

    df: pd.DataFrame = st.session_state["uploaded_data"]

    # Per-column decisions
    decisions = _render_column_decisions(df)

    st.divider()

    # Domain-specific features
    selected_domain_feats = _render_domain_features()

    st.divider()

    # Importance preview
    _render_importance_preview()

    st.divider()

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
    st.divider()
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
