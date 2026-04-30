# Spec 05 — Validation Strategy (Section 03)

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section:** `<div class="md-sec">` numbered **03** — "Validation strategy"
**Lines:** ~1366–1450 (the `<div class="md-val-grid">` block)

---

## What this section is

A compact 3-column form letting the user pick:
1. **Validation method** (dropdown) — Hold-out / K-Fold / **Stratified K-Fold ★** / Time-Series Split / Group K-Fold / Repeated Stratified K-Fold
2. **Train/test split slider** — 60–90% range, default 80/20, step 5
3. **Random seed** — text/number input, default 42

Plus a cyan tip strip explaining why the auto-selected method was chosen.

---

## Hard rules

1. **Auto-select the method** based on `state["problem_type"]` and other state characteristics:
   - `binary_classification` or `multiclass_classification` → `stratified_kfold` ★
   - `regression` → `kfold` ★
   - `time_series` (or detected datetime target) → `time_series_split` ★
   - `clustering` → `holdout` (CV doesn't apply cleanly to unsupervised)
   - If `state["data_profile"]["group_column"]` is set → `group_kfold` ★
2. **The tip strip explains the auto-choice in plain English** — different message per method.
3. **Random seed is the same as `state["random_seed"]`** by default. User can override.
4. **n_splits defaults to 5.** Hidden when method is "holdout" (no folds).
5. **Test size defaults to 0.2** (the 80/20 split). The slider is shown for ALL methods (used as the holdout split when CV is also done; even for K-Fold we still hold out a final test set).
6. **Validation config writes to `state["modeling_config"]["validation"]`** as a flat dict.

---

## Files to create

```
dashboard/components/
  md_validation_strategy.py       # The full section 03 component
```

No backend files modified.

---

## File 1 — `md_validation_strategy.py`

```python
"""
Section 03 — Validation strategy picker.
Auto-selects the recommended method based on problem type + data characteristics,
shows a plain-English tip explaining the choice, and lets the user override.
"""

import streamlit as st


# ─── method registry ─────────────────────────────────────────────

VALIDATION_METHODS = [
    {
        "key": "holdout",
        "label": "Hold-out (single train/test split)",
        "description": "One split — fast but high variance.",
    },
    {
        "key": "kfold",
        "label": "K-Fold Cross-Validation",
        "description": "K equally-sized folds. Stable estimate.",
    },
    {
        "key": "stratified_kfold",
        "label": "Stratified K-Fold ★",
        "description": "K folds that preserve class proportions. Best for classification.",
    },
    {
        "key": "time_series_split",
        "label": "Time-Series Split",
        "description": "Forward-chaining splits. Use for temporal data.",
    },
    {
        "key": "group_kfold",
        "label": "Group K-Fold",
        "description": "K folds with no group leakage across folds.",
    },
    {
        "key": "repeated_stratified_kfold",
        "label": "Repeated Stratified K-Fold",
        "description": "Stratified K-Fold repeated N times. Lowest variance, slowest.",
    },
]


# ─── session state keys ───────────────────────────────────────────

VAL_METHOD_KEY = "md_val_method"
VAL_NSPLITS_KEY = "md_val_n_splits"
VAL_TEST_SIZE_KEY = "md_val_test_size"
VAL_SEED_KEY = "md_val_seed"


def render(state: dict, project_id: str) -> None:
    """Render section 03 in full. Side-effects: writes to st.session_state."""
    # Decide the recommended method
    recommended_key = _recommend_method(state)
    seed = state.get("random_seed", 42)

    # Initialize session_state on first render
    if VAL_METHOD_KEY not in st.session_state:
        st.session_state[VAL_METHOD_KEY] = recommended_key
    if VAL_NSPLITS_KEY not in st.session_state:
        st.session_state[VAL_NSPLITS_KEY] = 5
    if VAL_TEST_SIZE_KEY not in st.session_state:
        st.session_state[VAL_TEST_SIZE_KEY] = 0.2
    if VAL_SEED_KEY not in st.session_state:
        st.session_state[VAL_SEED_KEY] = seed

    # Header
    st.markdown(
        """
        <div class="md-sec-head">
          <div class="md-sec-num">03</div>
          <div style="flex:1;">
            <div class="md-sec-title">Validation <em>strategy</em></div>
            <div class="md-sec-meta">How AutoDS will measure honest, generalizable performance</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tip strip (auto-explanation of the recommended method)
    tip_text = _tip_text_for(recommended_key, state)
    st.markdown(
        f"""
        <div class="md-sec-tip">
          {tip_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3-column grid
    cols = st.columns([1.2, 1, 1])

    with cols[0]:
        st.markdown("<div class='md-val-label'>Validation method</div>", unsafe_allow_html=True)
        labels = [m["label"] for m in VALIDATION_METHODS]
        keys = [m["key"] for m in VALIDATION_METHODS]
        try:
            current_idx = keys.index(st.session_state[VAL_METHOD_KEY])
        except ValueError:
            current_idx = keys.index(recommended_key)
        chosen_label = st.selectbox(
            label="Validation method",
            label_visibility="collapsed",
            options=labels,
            index=current_idx,
            key=f"val_method_{project_id}",
        )
        st.session_state[VAL_METHOD_KEY] = keys[labels.index(chosen_label)]

        # Show n_splits only when method has folds
        method = st.session_state[VAL_METHOD_KEY]
        if method != "holdout":
            n = st.number_input(
                "Number of folds (k)",
                min_value=2, max_value=20,
                value=int(st.session_state[VAL_NSPLITS_KEY]),
                step=1,
                key=f"val_nsplits_{project_id}",
            )
            st.session_state[VAL_NSPLITS_KEY] = int(n)

    with cols[1]:
        st.markdown("<div class='md-val-label'>Train/test split</div>", unsafe_allow_html=True)
        train_pct = st.slider(
            label="Train/test split",
            label_visibility="collapsed",
            min_value=60, max_value=90,
            value=int((1 - st.session_state[VAL_TEST_SIZE_KEY]) * 100),
            step=5,
            key=f"val_test_size_{project_id}",
        )
        st.session_state[VAL_TEST_SIZE_KEY] = round(1 - train_pct / 100, 2)
        st.markdown(
            f"<div class='md-val-helper'>{train_pct}% train / {100 - train_pct}% test</div>",
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.markdown("<div class='md-val-label'>Random seed</div>", unsafe_allow_html=True)
        seed_val = st.number_input(
            label="Random seed",
            label_visibility="collapsed",
            min_value=0, max_value=999_999,
            value=int(st.session_state[VAL_SEED_KEY]),
            step=1,
            key=f"val_seed_{project_id}",
        )
        st.session_state[VAL_SEED_KEY] = int(seed_val)
        st.markdown(
            f"<div class='md-val-helper'>Reproducibility seed · used everywhere</div>",
            unsafe_allow_html=True,
        )

    # Commit to state right away (this section is cheap to read every render)
    state.setdefault("modeling_config", {})
    state["modeling_config"]["validation"] = {
        "method": st.session_state[VAL_METHOD_KEY],
        "n_splits": st.session_state[VAL_NSPLITS_KEY] if st.session_state[VAL_METHOD_KEY] != "holdout" else None,
        "test_size": st.session_state[VAL_TEST_SIZE_KEY],
        "random_seed": st.session_state[VAL_SEED_KEY],
        "shuffle": st.session_state[VAL_METHOD_KEY] not in ("time_series_split",),
    }


# ─── private helpers ──────────────────────────────────────────────

def _recommend_method(state: dict) -> str:
    """Deterministic rule — never calls the LLM."""
    profile = state.get("data_profile", {})
    pt = state.get("problem_type", "binary_classification")

    # Group-based?
    if profile.get("group_column"):
        return "group_kfold"

    # Time-series?
    if pt == "time_series" or profile.get("has_temporal_target"):
        return "time_series_split"

    # Classification → stratified
    if pt in ("binary_classification", "multiclass_classification"):
        return "stratified_kfold"

    # Regression → plain k-fold
    if pt == "regression":
        return "kfold"

    # Clustering / anomaly / other
    return "holdout"


def _tip_text_for(method_key: str, state: dict) -> str:
    """Plain-English explanation, dataset-aware."""
    profile = state.get("data_profile", {})
    n_rows = profile.get("n_rows", 0)

    if method_key == "stratified_kfold":
        imb = profile.get("target_imbalance_ratio")
        if imb is not None and imb < 0.3:
            return (
                f"Stratified K-Fold is auto-selected because your target is imbalanced "
                f"(minority class ≈ {imb*100:.1f}%). Each fold will preserve class proportions."
            )
        return (
            "Stratified K-Fold is auto-selected because you have a classification target. "
            "Folds preserve class proportions for an honest accuracy estimate."
        )
    if method_key == "kfold":
        return (
            "K-Fold cross-validation is auto-selected for regression. "
            "Predictions are averaged across folds for a stable error estimate."
        )
    if method_key == "time_series_split":
        return (
            "Time-Series Split is auto-selected because your data has a temporal ordering. "
            "Each fold trains on the past and validates on the future — no leakage."
        )
    if method_key == "group_kfold":
        return (
            "Group K-Fold is auto-selected because your data has a group column "
            f"({profile.get('group_column')}). No group will appear in both train and validation."
        )
    if method_key == "repeated_stratified_kfold":
        return "Repeated Stratified K-Fold runs the stratified split N times — lowest variance estimate, slowest training."
    if method_key == "holdout":
        if n_rows < 1000:
            return (
                f"Hold-out is auto-selected because your dataset is small ({n_rows:,} rows) "
                "and a single rigorous split avoids over-fragmenting the training data."
            )
        return "Hold-out is auto-selected. Single train/test split — fastest, but higher variance."
    return "Validation method auto-selected based on problem type."
```

---

## CSS additions

Add to `shared_css.py` (extend `MODELING_CSS`):

```css
.md-val-grid {
  display: grid; grid-template-columns: 1.2fr 1fr 1fr;
  gap: 18px; margin-top: 14px;
}
@media (max-width: 900px) {
  .md-val-grid { grid-template-columns: 1fr; }
}
.md-val-label {
  font-family: var(--font-mono); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.7px;
  color: var(--text-muted); margin-bottom: 6px;
}
.md-val-helper {
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-faint); margin-top: 4px;
}
```

(Use Streamlit columns instead of an actual CSS grid since Streamlit doesn't render arbitrary grids — the CSS above is for the labels and helpers only.)

---

## Edge cases

| Case | Handling |
|---|---|
| `problem_type` missing or `None` | Default to `"holdout"` and show a warning toast: "Problem type not configured — using hold-out validation." |
| Group K-Fold selected but no group column in state | Coerce method to `kfold` at training-launch (spec 07), log a warning. |
| User picks method that conflicts with data (e.g. time-series-split on shuffled data) | Allow it — user override wins. The training launcher (spec 07) will log a warning to the training log. |
| User sets seed to 0 | That's a valid seed, no special handling. |
| User sets n_splits = 2 | Allowed. Sklearn's StratifiedKFold supports k=2. |
| User sets n_splits > number of rows / 2 | The training launcher catches this at coercion time and shows error toast. |

---

## Acceptance criteria

- [ ] Recommended method auto-selected per problem type + data characteristics
- [ ] Tip strip shows plain-English explanation of the chosen method
- [ ] User can override the method in the dropdown
- [ ] n_splits input shown only for non-holdout methods
- [ ] Train/test slider works in 60–90% range, step 5, default 80
- [ ] Random seed defaults to `state["random_seed"]`, user can override
- [ ] All four values commit to `state["modeling_config"]["validation"]` on every render
- [ ] No modifications outside `dashboard/components/` and `shared_css.py`
