"""Adapter: converts execute_eda() output into session_state shape expected by ed_* components.

The eda_agent stores:
  state["eda_results"]  — dict of raw stat test results
  state["eda_charts"]   — list of chart dicts (figure, title, description, insights)
  state["eda_insights"] — list of plain strings
  state["eda_summary"]  — plain text summary

The ed_* components expect:
  st.session_state["eda_insights"]      — list[dict] with text/confidence/evidence
  st.session_state["eda_stats"]         — list[dict] with test/columns/p_value/effect_size/interpretation
  st.session_state["eda_charts"]        — list[dict] with type/title/subtitle/interpretation/figure/id
  st.session_state["eda_quality_flags"] — dict with outliers (list[dict]) + red_flags (list[dict])
"""
from __future__ import annotations
import re
import streamlit as st


def adapt_results(state: dict) -> None:
    """Read agent output from *state* and write adapted values into session_state."""
    raw_results: dict = state.get("eda_results") or {}
    raw_charts: list[dict] = state.get("eda_charts") or []
    raw_insights: list[str] = state.get("eda_insights") or []

    st.session_state["eda_results"] = raw_results
    st.session_state["eda_charts"] = _adapt_charts(raw_charts)
    st.session_state["eda_stats"] = _adapt_stats(raw_results)
    st.session_state["eda_insights"] = _adapt_insights(raw_insights, raw_results)
    st.session_state["eda_quality_flags"] = _extract_quality_flags(raw_results, raw_charts)


# ---------------------------------------------------------------------------
# Insights: list[str] → list[dict]
# ---------------------------------------------------------------------------

def _adapt_insights(raw: list[str], results: dict) -> list[dict]:
    adapted = []
    for text in raw:
        confidence = _infer_confidence(text, results)
        evidence = _extract_evidence(text)
        adapted.append({
            "text": text,
            "confidence": confidence,
            "evidence": evidence,
        })
    return adapted


def _infer_confidence(text: str, results: dict) -> str:
    """Infer high/medium confidence from text cues."""
    t = text.lower()
    if any(kw in t for kw in ("very strong", "p < 0.001", "p<0.001", "strongly")):
        return "high"
    if any(kw in t for kw in ("significant", "correlation", "r=0.", "p < 0.01", "p<0.01")):
        return "high"
    if any(kw in t for kw in ("marginally", "weak", "may", "might", "possibly")):
        return "medium"
    return "high"


def _extract_evidence(text: str) -> str:
    """Pull a short evidence snippet (p-value, r-value) from insight text."""
    patterns = [
        r'p[<>=\s]*[\d\.]+',
        r'r[\s]*=[\s]*-?[\d\.]+',
        r'n=[\d,]+',
        r'skewness=[\d\.\-]+',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""


# ---------------------------------------------------------------------------
# Stats: dict → list[dict]
# ---------------------------------------------------------------------------

def _adapt_stats(results: dict) -> list[dict]:
    rows = []
    for key, val in results.items():
        if not isinstance(val, dict):
            continue
        p_value = val.get("p_value")
        if p_value is None:
            continue
        test_name, columns = _parse_key(key)
        rows.append({
            "test": test_name,
            "columns": columns,
            "p_value": float(p_value),
            "effect_size": _fmt_effect(val),
            "interpretation": val.get("interpretation", ""),
        })
    return rows


def _parse_key(key: str) -> tuple[str, str]:
    """Convert a result dict key like 't_test_age_by_gender' → (display_name, columns_str)."""
    if key.startswith("t_test_"):
        rest = key[len("t_test_"):]
        parts = rest.split("_by_")
        col, group = (parts[0], parts[1]) if len(parts) == 2 else (rest, "")
        return "Independent t-test", f"{col} by {group}" if group else col
    if key.startswith("chi_sq_"):
        rest = key[len("chi_sq_"):]
        parts = rest.split("_vs_")
        return "Chi-square test", " vs ".join(parts)
    if key.startswith("anova_"):
        rest = key[len("anova_"):]
        parts = rest.split("_by_")
        col, group = (parts[0], parts[1]) if len(parts) == 2 else (rest, "")
        return "One-way ANOVA", f"{col} by {group}" if group else col
    if key.startswith("shapiro_"):
        col = key[len("shapiro_"):]
        return "Shapiro-Wilk normality", col
    if key == "correlation_matrix":
        return "Correlation matrix", "numeric columns"
    if key == "vif_analysis":
        return "VIF analysis", "numeric predictors"
    return key.replace("_", " ").title(), ""


def _fmt_effect(val: dict) -> str:
    """Format effect size as a short string."""
    es = val.get("effect_size")
    if es is None:
        return "—"
    if isinstance(es, float):
        label = ""
        if "cohen" in str(val.get("effect_size_label", "")).lower():
            label = "Cohen's d"
        elif "eta" in str(val.get("effect_size_label", "")).lower():
            label = "η²"
        elif "cramer" in str(val.get("effect_size_label", "")).lower():
            label = "Cramér's V"
        return f"{es:.3f}" + (f" ({label})" if label else "")
    return str(es)


# ---------------------------------------------------------------------------
# Charts: add type / subtitle / interpretation / id
# ---------------------------------------------------------------------------

_TYPE_MAP = [
    ("histogram", "histogram"),
    ("box plot", "box"),
    ("scatter", "scatter"),
    ("bar chart", "bar"),
    ("bar", "bar"),
    ("heatmap", "heatmap"),
    ("correlation", "heatmap"),
    ("time series", "line"),
    ("line", "line"),
    ("violin", "box"),
    ("pair plot", "scatter"),
]


def _infer_type(title: str, description: str) -> str:
    combined = (title + " " + description).lower()
    for keyword, chart_type in _TYPE_MAP:
        if keyword in combined:
            return chart_type
    return "histogram"


def _adapt_charts(raw: list[dict]) -> list[dict]:
    adapted = []
    for i, c in enumerate(raw):
        title = c.get("title", f"Chart {i+1}")
        description = c.get("description", "")
        insights = c.get("insights", [])
        adapted.append({
            "id": f"chart_{i}",
            "type": _infer_type(title, description),
            "title": title,
            "subtitle": description,
            "interpretation": insights[0] if insights else "",
            "figure": c.get("figure"),
            # Pass through raw fields so consumers can access them
            "insights": insights,
        })
    return adapted


# ---------------------------------------------------------------------------
# Quality flags: extract from results + charts
# ---------------------------------------------------------------------------

def _extract_quality_flags(results: dict, charts: list[dict]) -> dict:
    outliers: list[dict] = []
    red_flags: list[dict] = []

    # Outliers from box plot insights
    for c in charts:
        title: str = c.get("title", "")
        if "box" not in title.lower() and "violin" not in title.lower():
            continue
        for ins in c.get("insights", []):
            m = re.search(r'(\d+) outliers? detected', ins, re.IGNORECASE)
            if m:
                col = re.sub(r'(?i)^box\s*plot\s*of\s*', '', title).split(" by ")[0].strip()
                outliers.append({
                    "column": col,
                    "description": ins,
                })

    # Red flags from VIF (multicollinearity)
    vif = results.get("vif_analysis")
    if isinstance(vif, dict):
        high_vif = vif.get("high_vif_columns", [])
        for col in high_vif:
            red_flags.append({
                "column": col,
                "description": f"VIF > threshold — potential multicollinearity",
            })

    # Red flags from shapiro (non-normal, may affect parametric tests)
    for key, val in results.items():
        if not key.startswith("shapiro_"):
            continue
        if isinstance(val, dict) and val.get("p_value", 1.0) < 0.05:
            col = key[len("shapiro_"):]
            red_flags.append({
                "column": col,
                "description": f"Non-normal distribution (Shapiro-Wilk p={val['p_value']:.3f}) — use non-parametric alternatives",
            })

    return {"outliers": outliers, "red_flags": red_flags}
