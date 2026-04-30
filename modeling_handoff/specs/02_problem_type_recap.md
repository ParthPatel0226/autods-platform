# Spec 02 — Problem-Type Recap Card

## What this spec covers

The slim recap strip at the top of the Configure phase. Confirms what kind of problem AutoDS detected and what the target column is, with one-click override.

Renders **before** the algorithm spotlight (which is in spec 03 — they're both inside Section 01 of the configure phase).

## File to create

- `dashboard/components/md_problem_recap.py` (new)

## Visual reference

Mockup lines ~1095–1110: the `.md-problem` flex row with violet pill, target text, meta text, and "Override?" link. Embedded inside `.md-sec` so it sits within the algorithm section.

## State reads

Required keys in `state`:

- `state["problem_type"]` — `"classification"` | `"multiclass"` | `"regression"` | `"clustering"` | `"time_series"`
- `state["target_column"]` — string column name (None for clustering)
- `state["schema_info"]` — dict with `row_count`, per-column types
- `state["feature_list"]` — list of feature names

Computed on the fly from `df_engineered` (read via `st.session_state["df_engineered"]` or fallback to `state["fe_output_path"]`):

- For binary/multiclass classification: number of classes, positive class %
- For regression: target min/max/mean
- For time_series: time column name, frequency
- For clustering: number of features only (no target)

## Implementation

```python
"""Problem-type recap card with override expander."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from services.project_service import get_project_service


def render(state):
    problem_type = state.get("problem_type", "classification")
    target = state.get("target_column", "—")
    n_rows = state.get("schema_info", {}).get("row_count", 0)
    n_features = len(state.get("feature_list", []))

    detail = _compute_detail(state)
    pill_text = _pill_text_for_problem_type(problem_type)

    target_str = f"target = <span>{target}</span>" if target else "<span>unsupervised</span>"

    html = f"""
    <div class="md-problem">
      <span class="md-problem-pill">{pill_text}</span>
      <span class="md-problem-target">{target_str}</span>
      <span class="md-problem-meta">{n_rows:,} rows · {n_features} features · {detail}</span>
      <span class="md-override" id="md-override-link">Override?</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Streamlit-native override (the HTML link is decorative; the expander is interactive)
    with st.expander("⚙️ Override problem type or target column", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            problem_options = ["classification", "multiclass", "regression", "clustering", "time_series"]
            current_idx = problem_options.index(problem_type) if problem_type in problem_options else 0
            new_pt = st.selectbox(
                "Problem type",
                problem_options,
                index=current_idx,
                key="md_override_pt",
                help="Override the auto-detected problem type. Switching to clustering will clear the target.",
            )
        with col2:
            schema = state.get("schema_info", {}).get("columns", {}) or {}
            cols = list(schema.keys()) or [target] if target else []
            target_idx = cols.index(target) if target in cols else 0

            if new_pt == "clustering":
                st.text_input("Target column", value="(no target — unsupervised)", disabled=True)
                new_target = None
            else:
                new_target = st.selectbox(
                    "Target column",
                    cols if cols else [target or ""],
                    index=target_idx,
                    key="md_override_target",
                )

        col_apply, col_cancel = st.columns([1, 4])
        with col_apply:
            if st.button("Apply override", key="md_apply_override", type="primary"):
                _apply_override(state, new_pt, new_target)


def _apply_override(state, new_pt, new_target):
    """Apply the override + invalidate cached recommendation."""
    svc = get_project_service()
    project_id = state.get("project_id")
    svc.update_state(project_id, {
        "problem_type": new_pt,
        "target_column": new_target,
        "modeling_overridden": True,
    })
    # Invalidate cached recommendation so spotlight re-computes
    for k in ("md_recommendation", "md_selected_algos", "md_hp_state"):
        st.session_state.pop(k, None)
    st.toast(f"✓ Switched to {new_pt}" + (f" · target={new_target}" if new_target else ""))
    st.rerun()


def _pill_text_for_problem_type(pt):
    mapping = {
        "classification": "Binary Classification",
        "multiclass": "Multiclass Classification",
        "regression": "Regression",
        "clustering": "Clustering",
        "time_series": "Time Series Forecasting",
    }
    return mapping.get(pt, pt.replace("_", " ").title())


def _compute_detail(state):
    """Right-hand context string based on problem type + target distribution."""
    pt = state.get("problem_type", "classification")
    df = _get_engineered_df(state)
    target = state.get("target_column")

    if pt == "classification" and df is not None and target and target in df.columns:
        try:
            n_classes = int(df[target].nunique())
            if n_classes == 2:
                vc = df[target].value_counts(normalize=True)
                pos_rate = float(vc.iloc[0])
                severity = _imbalance_severity(pos_rate)
                return f"{severity} ({pos_rate*100:.1f}% positive)"
            return f"{n_classes} classes"
        except Exception:
            return "target distribution unknown"

    if pt == "regression" and df is not None and target and target in df.columns:
        try:
            return f"target range [{df[target].min():.2f}, {df[target].max():.2f}]"
        except Exception:
            return "target range unknown"

    if pt == "clustering":
        return "no target — unsupervised"

    if pt == "time_series":
        time_col = state.get("time_column", "—")
        return f"time column = {time_col}"

    if pt == "multiclass" and df is not None and target and target in df.columns:
        try:
            return f"{int(df[target].nunique())} classes"
        except Exception:
            return "multiclass"

    return ""


def _imbalance_severity(positive_rate):
    diff = abs(positive_rate - 0.5)
    if diff < 0.1: return "balanced"
    if diff < 0.2: return "slight imbalance"
    if diff < 0.4: return "moderate imbalance"
    return "severe imbalance"


def _get_engineered_df(state):
    """Pull engineered dataframe from session_state or compute on demand."""
    df = st.session_state.get("df_engineered")
    if df is not None:
        return df

    # Fallback: re-load from feature engineer output
    fe_output_path = state.get("fe_output_path")
    if fe_output_path:
        try:
            return pd.read_parquet(fe_output_path)
        except Exception:
            return None

    return None
```

## Behavior

- **Pill color** comes from CSS — uses violet for classification (`md-problem-pill` class).  Different problem types could use different background colors; for now all use the same violet. This is fine — the pill text is what differs.
- Clicking *Override?* opens the Streamlit expander (the decorative link in the HTML is just visual cue).
- Submitting an override invalidates `md_recommendation`, `md_selected_algos`, `md_hp_state` cached state so the spotlight re-computes.
- The detail string adapts: imbalance % for classification, range for regression, "no target" for clustering, time column for time_series.

## Imbalance thresholds

| Positive rate | Severity label |
|---|---|
| 40%–60% | balanced |
| 30%–40% or 60%–70% | slight imbalance |
| 10%–30% or 70%–90% | moderate imbalance |
| <10% or >90% | severe imbalance |

These thresholds drive the recommendation logic in spec 03 — severe imbalance → recommend `BalancedRandomForest` instead of XGBoost.

## State reads (recap)

```python
state.get("problem_type")
state.get("target_column")
state.get("schema_info", {}).get("row_count", 0)
state.get("schema_info", {}).get("columns", {})
state.get("feature_list", [])
state.get("fe_output_path")
state.get("time_column")  # only for time_series
st.session_state.get("df_engineered")  # primary source for distribution
```

## State writes (only on override)

```python
state["problem_type"]      = new_pt
state["target_column"]     = new_target
state["modeling_overridden"] = True
```

Plus invalidates `st.session_state["md_recommendation"]`, `st.session_state["md_selected_algos"]`, `st.session_state["md_hp_state"]`.

## Smoke test for spec 02

1. Land on Modeling with Titanic dataset (binary classification, 891 rows, target=Survived)
2. ✅ Pill shows "BINARY CLASSIFICATION"
3. ✅ Target = `Survived`
4. ✅ Meta says `891 rows · 7 features · slight imbalance (61.6% positive)` (or whatever post-FE feature count is)
5. ✅ Override expander opens, shows the 5 problem types and all column names
6. ✅ Changing problem_type → Apply → page re-renders, pill changes, recommendation re-computes
7. ✅ For regression dataset: shows target range
8. ✅ For clustering dataset: shows "no target — unsupervised", target dropdown disabled

## Edge cases to handle

- `df_engineered` is None and `fe_output_path` is None → show "target distribution unknown" instead of crashing
- Target column has only 1 unique value (constant target) → still show "1 class" without crashing
- Severe imbalance (≤5% positive) → show "severe imbalance"; spec 03 will use this to recommend `BalancedRandomForest`
- User overrides target to a non-existent column (shouldn't happen via dropdown, but defensive) → toast error
- Multiclass with 50+ classes → just show "50 classes" without crashing

## Why this matters

The recap is small but critical: it confirms what AutoDS understood about the dataset before the user starts picking algorithms. If the user disagrees ("this is regression, not classification!"), the override is a single click. Getting this wrong wastes 10+ minutes of training on the wrong problem.
