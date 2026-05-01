"""Quality-at-a-glance — 4 indicator cards with bars and status pills."""
from __future__ import annotations
import streamlit as st
import pandas as pd


def render(df: pd.DataFrame) -> None:
    """4 indicators with status pills."""
    indicators = _compute(df)

    st.markdown(
        '<div class="up-quality">'
        '<h3 class="up-quality-title">\U0001f6e1 Data quality at a glance</h3>'
        '<div class="up-quality-grid">',
        unsafe_allow_html=True,
    )
    for ind in indicators:
        st.markdown(
            f'<div class="up-qg-item">'
            f'  <div class="up-qg-label">{ind["label"]}</div>'
            f'  <div class="up-qg-value">'
            f'    <span class="up-qg-num">{ind["display"]}</span>'
            f'    <span class="up-qg-tag up-qg-{ind["status"]}">{ind["status_label"]}</span>'
            f'  </div>'
            f'  <div class="up-qg-bar"><div class="up-qg-fill up-qg-fill-{ind["status"]}" style="width:{ind["bar_pct"]}%"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div></div>', unsafe_allow_html=True)


def _compute(df: pd.DataFrame) -> list[dict]:
    n = len(df)
    if n == 0:
        return []

    miss_pct = float(df.isna().sum().sum()) / (n * len(df.columns)) * 100
    dups = int(df.duplicated().sum())
    constant_cols = sum(1 for c in df.columns if df[c].nunique(dropna=False) <= 1)
    high_card_cols = sum(1 for c in df.columns
                          if df[c].dtype == "object" and df[c].nunique(dropna=False) > min(1000, n * 0.5))

    return [
        {
            "label": "Missing values",
            "display": f"{miss_pct:.1f}%",
            "status": _missing_status(miss_pct),
            "status_label": _missing_label(miss_pct),
            "bar_pct": min(miss_pct * 2, 100),
        },
        {
            "label": "Duplicates",
            "display": f"{dups:,}",
            "status": "good" if dups == 0 else "warn",
            "status_label": "None" if dups == 0 else f"{dups / n * 100:.1f}%",
            "bar_pct": min(dups / n * 100, 100) if n else 0,
        },
        {
            "label": "Constant columns",
            "display": str(constant_cols),
            "status": "good" if constant_cols == 0 else "warn",
            "status_label": "None" if constant_cols == 0 else "Review",
            "bar_pct": constant_cols / max(len(df.columns), 1) * 100,
        },
        {
            "label": "High cardinality",
            "display": str(high_card_cols),
            "status": "good" if high_card_cols == 0 else "warn",
            "status_label": "None" if high_card_cols == 0 else "Review",
            "bar_pct": high_card_cols / max(len(df.columns), 1) * 100,
        },
    ]


def _missing_status(pct: float) -> str:
    if pct < 5:
        return "good"
    if pct < 20:
        return "warn"
    return "bad"


def _missing_label(pct: float) -> str:
    if pct < 5:
        return "Good"
    if pct < 20:
        return "Review"
    return "High"
