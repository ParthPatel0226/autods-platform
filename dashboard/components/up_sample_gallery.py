"""Curated sample dataset gallery."""
from __future__ import annotations
import streamlit as st

from data_connectors.direct_input.sample_datasets import SampleDatasetConnector


# Adapted to actual SAMPLE_DATASETS keys in the codebase
SAMPLES = [
    # (key,                  display_name,         description,                                                   domain_key,    rows,   cols, size_kb)
    ("customer_churn",       "Customer Churn",      "E-commerce churn prediction — binary classification.",         "ecommerce",   5000,   15,   350),
    ("hospital_readmission", "Hospital Readmission","Healthcare readmission risk — predict 30-day returns.",         "healthcare",  3000,   15,   220),
    ("credit_default",       "Credit Default",      "Finance: predict whether a borrower defaults on a loan.",      "finance",     5000,   12,   410),
    ("employee_attrition",   "Employee Attrition",  "HR: IBM-style attrition — predict who is likely to leave.",    "hr",          3000,   17,   280),
    ("retail_sales",         "Retail Sales",        "Sales forecasting from store / date / product features.",      "ecommerce",   4000,   10,   330),
    ("manufacturing_quality","Mfg. Quality",        "Manufacturing: predict defect rate from process parameters.",  "manufacturing",4000,  12,   360),
]

DOMAIN_PILL_CLASS = {
    "ecommerce":     "up-dom-ecommerce",
    "healthcare":    "up-dom-healthcare",
    "finance":       "up-dom-finance",
    "hr":            "up-dom-hr",
    "manufacturing": "up-dom-classification",
    "classification":"up-dom-classification",
    "regression":    "up-dom-regression",
}
DOMAIN_PILL_LABEL = {
    "ecommerce":     "E-commerce",
    "healthcare":    "Healthcare",
    "finance":       "Finance",
    "hr":            "HR",
    "manufacturing": "Manufacturing",
    "classification":"Classification",
    "regression":    "Regression",
}


def render(on_loaded) -> None:
    """Render the sample gallery. on_loaded(df, meta) called when a sample is chosen."""
    st.markdown(
        '<div class="up-sec-divider">'
        '<span class="up-sec-label">Or start with a sample</span>'
        '<span class="up-sec-line"></span>'
        '</div>'
        '<h2 class="up-sec-title">Curated <em>sample datasets</em></h2>'
        '<p class="up-sec-sub">One-click load. Each dataset is paired with a domain so AutoDS configures itself appropriately.</p>',
        unsafe_allow_html=True,
    )

    rows = [SAMPLES[i:i + 3] for i in range(0, len(SAMPLES), 3)]
    for row in rows:
        cols = st.columns(3, gap="medium")
        for col, sample in zip(cols, row):
            with col:
                _render_sample_card(sample, on_loaded)


def _render_sample_card(sample, on_loaded) -> None:
    key, name, desc, domain, rows, cols, size_kb = sample
    pill_cls = DOMAIN_PILL_CLASS.get(domain, "up-dom-classification")
    pill_lbl = DOMAIN_PILL_LABEL.get(domain, "Generic")
    size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

    st.markdown(
        f'<div class="up-sample-card">'
        f'  <div class="up-sample-head">'
        f'    <div class="up-sample-name">{name}</div>'
        f'    <div class="up-sample-domain {pill_cls}">{pill_lbl}</div>'
        f'  </div>'
        f'  <div class="up-sample-desc">{desc}</div>'
        f'  <div class="up-sample-stats">'
        f'    <div class="up-sample-stat"><span class="v">~{rows:,}</span>rows</div>'
        f'    <div class="up-sample-stat"><span class="v">{cols}</span>cols</div>'
        f'    <div class="up-sample-stat"><span class="v">{size_str}</span></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button(f"Load {name}", key=f"up_sample_{key}", use_container_width=True):
        with st.spinner(f"Loading {name}\u2026"):
            try:
                connector = SampleDatasetConnector()
                df = connector.load({"dataset_name": key})
                meta = {
                    "filename": f"{key}.csv",
                    "format": "csv",
                    "encoding": "UTF-8",
                    "size_bytes": size_kb * 1024,
                    "source_type": "sample",
                    "source_provider": "built-in",
                }
                on_loaded(df, meta)
                st.success(f"Loaded {name}")
            except Exception as e:
                st.error(f"Failed to load sample: {e}")
