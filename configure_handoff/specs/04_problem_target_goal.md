# Spec 04 — Problem Pills + Target & Goal

## Component A: `dashboard/components/cf_problem_pills.py`

Replace the dropdown with 6 pills. Detected one shows a "Detected" badge.

```python
"""6 problem-type pills."""
from __future__ import annotations
import streamlit as st


PROBLEM_TYPES = [
    {"key": "classification", "label": "Classification", "icon": "🎯"},
    {"key": "regression",     "label": "Regression",     "icon": "📈"},
    {"key": "clustering",     "label": "Clustering",     "icon": "🧩"},
    {"key": "timeseries",     "label": "Time Series",    "icon": "⏱"},
    {"key": "survival",       "label": "Survival",       "icon": "⌛"},
    {"key": "anomaly",        "label": "Anomaly Detection", "icon": "⚠️"},
]


def render(detected_problem: str) -> str:
    """Render the 6 pills. Returns the selected problem type.

    State key: st.session_state["cf_problem_type"]
    """
    selected = st.session_state.get("cf_problem_type", detected_problem)

    st.markdown('<div class="cf-problem-pills">', unsafe_allow_html=True)
    cols = st.columns(6, gap="small")
    for col, p in zip(cols, PROBLEM_TYPES):
        with col:
            _render_pill(p, detected_problem, selected)
    st.markdown('</div>', unsafe_allow_html=True)
    return selected


def _render_pill(p: dict, detected: str, selected: str) -> None:
    is_detected = p["key"] == detected
    is_selected = p["key"] == selected
    classes = ["cf-problem-pill"]
    if is_detected: classes.append("cf-pill-detected")
    if is_selected: classes.append("cf-pill-selected")

    badge = '<span class="cf-pill-detected-tag">Detected</span>' if is_detected else ""

    st.markdown(
        f'<div class="{" ".join(classes)}">'
        f'  {badge}'
        f'  <span class="cf-problem-icon">{p["icon"]}</span>'
        f'  {p["label"]}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button(p["label"], key=f"cf_pp_{p['key']}",
                 use_container_width=True, label_visibility="collapsed"):
        st.session_state["cf_problem_type"] = p["key"]
        st.rerun()
```

## Component B: `dashboard/components/cf_target_goal.py`

Target dropdown + goal dropdown (problem-aware) + manual input.

```python
"""Target column dropdown + goal dropdown + manual text input."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from domains.domain_registry import DOMAIN_REGISTRY


# Problem-aware goal templates
GOAL_TEMPLATES = {
    "classification": [
        "Identify top drivers of the target",
        "Find the top 5 predictors with AUC > 0.80",
        "Maximize recall for the positive class",
        "Minimize false negatives",
        "Build a fair model across protected attributes",
    ],
    "regression": [
        "Predict the target value as accurately as possible",
        "Find drivers of the target's variance",
        "Build a model with R² > 0.85",
        "Minimize prediction error (RMSE)",
    ],
    "clustering": [
        "Discover natural segments in the data",
        "Find 3–5 well-separated clusters",
        "Identify customer / patient archetypes",
    ],
    "timeseries": [
        "Forecast the next 30 periods",
        "Identify seasonal patterns",
        "Detect change points in the series",
    ],
    "survival": [
        "Predict time-to-event",
        "Identify risk factors for shortened survival",
        "Compare survival across groups",
    ],
    "anomaly": [
        "Find unusual records in the dataset",
        "Detect outliers in numeric features",
        "Flag rare combinations of values",
    ],
    "auto": [
        "Run a complete analysis appropriate to the data",
        "Build the most accurate model possible",
        "Find the most important patterns",
    ],
}


def render(df: pd.DataFrame, problem_type: str, domain_key: str) -> tuple[str, str]:
    """Render target + goal fields. Returns (target_column, goal_text).

    State keys:
        st.session_state["cf_target"]
        st.session_state["cf_goal"]
        st.session_state["cf_goal_manual"]
    """
    # ---- Target column ----
    target_options = _build_target_options(df, domain_key, problem_type)
    current_target = st.session_state.get("cf_target", "")
    if current_target not in [opt[0] for opt in target_options]:
        current_target = target_options[0][0] if target_options else ""

    target_idx = next(
        (i for i, (val, _) in enumerate(target_options) if val == current_target), 0
    )
    target_choice = st.selectbox(
        "Target column",
        options=range(len(target_options)),
        format_func=lambda i: target_options[i][1],
        index=target_idx,
        key="cf_target_select",
    )
    selected_target = target_options[target_choice][0]
    if selected_target != st.session_state.get("cf_target"):
        st.session_state["cf_target"] = selected_target

    # Helper text below dropdown
    st.markdown(_target_helper(df, selected_target, problem_type),
                unsafe_allow_html=True)

    # ---- Goal dropdown ----
    templates = GOAL_TEMPLATES.get(problem_type, GOAL_TEMPLATES["auto"])
    current_goal = st.session_state.get("cf_goal", templates[0])
    if current_goal not in templates:
        templates = [current_goal, *templates]

    goal_choice = st.selectbox(
        "What do you want to achieve?",
        options=templates,
        index=templates.index(current_goal),
        key="cf_goal_select",
    )
    if goal_choice != st.session_state.get("cf_goal"):
        st.session_state["cf_goal"] = goal_choice

    # ---- Manual goal input ----
    manual = st.text_input(
        "Or describe your goal manually",
        value=st.session_state.get("cf_goal_manual", ""),
        placeholder="e.g., Find readmission predictors with AUC > 0.85, prioritize fairness across age groups",
        key="cf_goal_manual_input",
    )
    if manual != st.session_state.get("cf_goal_manual"):
        st.session_state["cf_goal_manual"] = manual

    # Manual takes precedence if non-empty
    final_goal = manual.strip() if manual.strip() else goal_choice
    return selected_target, final_goal


def _build_target_options(df: pd.DataFrame, domain_key: str, problem_type: str) -> list[tuple[str, str]]:
    """Return list of (value, display_label) tuples."""
    if df is None or df.empty:
        return [("", "— No data —")]

    options = [("", "— None (unsupervised)")]

    # Filter PHI / sensitive columns for sensitive domains
    phi_columns = _detect_phi_columns(df, domain_key)
    visible_cols = [c for c in df.columns if c not in phi_columns]

    # Recommend a column for the current problem type
    recommended = _recommend_target(df, visible_cols, problem_type)

    for col in visible_cols:
        dtype = str(df[col].dtype)
        if pd.api.types.is_bool_dtype(df[col]):
            short_dtype = "bool"
        elif pd.api.types.is_integer_dtype(df[col]):
            short_dtype = "int"
        elif pd.api.types.is_float_dtype(df[col]):
            short_dtype = "float"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            short_dtype = "dt"
        else:
            short_dtype = "str"

        suffix = "  ✨ recommended" if col == recommended else ""
        label = f"{col}  ({short_dtype}){suffix}"
        options.append((col, label))

    if phi_columns:
        options.append(("__phi_hidden__", f"—  {len(phi_columns)} PHI-flagged columns hidden  —"))

    return options


def _detect_phi_columns(df: pd.DataFrame, domain_key: str) -> set[str]:
    """Detect columns that look like PHI / PII for sensitive domains."""
    if domain_key not in {"healthcare", "hr", "finance"}:
        return set()
    phi_keywords = {
        "healthcare": ["name", "ssn", "dob", "address", "phone", "email", "mrn"],
        "hr":         ["name", "ssn", "dob", "address", "phone", "email", "salary_id"],
        "finance":    ["name", "ssn", "card_number", "account_number", "address"],
    }
    keywords = phi_keywords.get(domain_key, [])
    flagged = set()
    for col in df.columns:
        col_lower = col.lower()
        for kw in keywords:
            if kw in col_lower and "id" not in col_lower:
                flagged.add(col)
                break
    return flagged


def _recommend_target(df: pd.DataFrame, candidates: list[str], problem_type: str) -> str | None:
    """Pick a sensible recommended target for the current problem type."""
    if not candidates:
        return None

    if problem_type == "classification":
        for col in candidates:
            if pd.api.types.is_bool_dtype(df[col]):
                return col
        for col in candidates:
            if df[col].dtype == "object" and df[col].nunique(dropna=True) <= 10:
                return col
    elif problem_type == "regression":
        for col in candidates:
            if pd.api.types.is_float_dtype(df[col]):
                return col
        for col in candidates:
            if pd.api.types.is_integer_dtype(df[col]) and df[col].nunique() > 20:
                return col
    elif problem_type == "timeseries":
        for col in candidates:
            if pd.api.types.is_numeric_dtype(df[col]):
                return col
    return None


def _target_helper(df: pd.DataFrame, target: str, problem_type: str) -> str:
    """Generate helper text for the target dropdown."""
    if not target:
        return '<div class="cf-field-helper">No target selected — pipeline will run unsupervised.</div>'
    if target.startswith("__"):
        return ""
    s = df[target]
    if pd.api.types.is_bool_dtype(s):
        return '<div class="cf-field-helper">Boolean target detected — defaulting to binary classification.</div>'
    if s.dtype == "object" and s.nunique(dropna=True) <= 10:
        return f'<div class="cf-field-helper">{s.nunique()} unique values — multi-class classification.</div>'
    if pd.api.types.is_numeric_dtype(s):
        return f'<div class="cf-field-helper">Numeric target — defaulting to regression.</div>'
    return ""
```

## CSS additions

```css
/* ============ Problem pills ============ */
.cf-problem-pills {
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;
}
@media (max-width: 700px) {
  .cf-problem-pills { display: grid; grid-template-columns: 1fr 1fr; }
}
.cf-problem-pill {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 16px; background: var(--bg-card);
  border: 1px solid var(--border-default); border-radius: 12px;
  font-size: 13px; color: var(--text-secondary); cursor: pointer;
  backdrop-filter: blur(8px); transition: all 0.2s ease;
  position: relative; min-height: 42px;
}
.cf-problem-pill:hover {
  border-color: var(--border-strong); color: var(--text-primary);
}
.cf-pill-detected {
  background: rgba(139,92,246,0.12);
  border-color: var(--violet);
  color: var(--text-primary);
}
.cf-pill-selected {
  background: rgba(139,92,246,0.18) !important;
  border-color: var(--violet) !important;
  color: var(--text-primary);
  box-shadow: 0 0 14px -4px var(--violet);
}
.cf-pill-detected-tag {
  position: absolute; top: -6px; right: -4px;
  font-family: var(--font-mono); font-size: 8.5px;
  padding: 2px 6px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  color: white; border-radius: 999px;
  letter-spacing: 0.5px; text-transform: uppercase;
}
.cf-problem-icon { font-size: 14px; }

/* ============ Form fields ============ */
.cf-field { margin-bottom: 20px; }
.cf-field-label {
  display: block; font-size: 12.5px; color: var(--text-secondary);
  margin-bottom: 8px; font-weight: 500; letter-spacing: 0.3px;
}
.cf-field-helper {
  font-size: 11.5px; color: var(--text-muted); margin-top: 4px;
}

/* Streamlit's default selectbox/text_input restyled */
[data-testid="stMain"] .stSelectbox > div > div,
[data-testid="stMain"] .stTextInput > div > div > input,
[data-testid="stMain"] .stTextArea > div > div > textarea {
  background: rgba(7,9,26,0.4) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 10px !important;
  color: var(--text-primary) !important;
  font-family: var(--font-body) !important;
  font-size: 13.5px !important;
  transition: all 0.18s ease !important;
}
[data-theme="light"] [data-testid="stMain"] .stSelectbox > div > div,
[data-theme="light"] [data-testid="stMain"] .stTextInput > div > div > input,
[data-theme="light"] [data-testid="stMain"] .stTextArea > div > div > textarea {
  background: rgba(255,255,255,0.6) !important;
}
[data-testid="stMain"] .stSelectbox > div > div:focus-within,
[data-testid="stMain"] .stTextInput > div > div:focus-within,
[data-testid="stMain"] .stTextArea > div > div:focus-within {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 3px rgba(139,92,246,0.15) !important;
}
```
