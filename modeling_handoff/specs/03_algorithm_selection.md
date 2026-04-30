# Spec 03 — Recommended Algorithm Spotlight + Multi-Select Picker

## Backend integration overview

The list of available algorithms comes from `agents.tools.tool_registry.TOOL_REGISTRY["models"]`. Each entry has:

```python
TOOL_REGISTRY["models"]["xgboost_classifier"] = {
    "name": "XGBoost",
    "function": "agents.tools.ml_tools.train_xgboost",
    "family": "gradient_boosting",
    "supports_problem_types": ["classification", "regression"],
    "supports_imbalance": True,
    "default_hyperparameters": {...},
    "min_rows": 100,
    ...
}
```

The recommended algorithm comes from `agents.modeling_agent.recommend_algorithm(state) -> dict`. If that method doesn't exist (defensive guard), fall back to a hard-coded mapping by problem_type + imbalance severity.

## Files to create

- `dashboard/components/md_algorithm_registry_adapter.py` (adapter shim)
- `dashboard/components/md_algorithm_spotlight.py` (recommended card)
- `dashboard/components/md_algorithm_picker.py` (multi-select dropdown)

## Visual reference

- Mockup lines ~1115–1170 (the `.md-algo-spot` card with icon, tag, name, description, strengths)
- Mockup lines ~1175–1230 (the `.md-multiselect` panel + 7 family groups + ~22 algorithms)

## The 22 algorithms in the multi-select

Hard-coded fallback list when `tool_registry.get_models_for_problem_type` is unavailable:

```python
FALLBACK_ALGORITHMS = {
    "Linear models": [
        ("LogisticRegression", "L1/L2 baseline",   ["classification", "multiclass"]),
        ("RidgeClassifier",    "L2 regularised",   ["classification", "multiclass"]),
        ("SGDClassifier",      "scalable linear",  ["classification", "multiclass"]),
        ("LinearRegression",   "OLS baseline",     ["regression"]),
        ("Ridge",              "L2 regression",    ["regression"]),
        ("Lasso",              "L1 regression",    ["regression"]),
    ],
    "Tree-based": [
        ("RandomForest",       "bagged trees",        ["classification", "multiclass", "regression"]),
        ("ExtraTrees",         "more random splits",  ["classification", "multiclass", "regression"]),
        ("DecisionTree",       "single tree baseline", ["classification", "multiclass", "regression"]),
    ],
    "Gradient boosting": [
        ("XGBoost",                "tabular winner",         ["classification", "multiclass", "regression"]),
        ("LightGBM",               "fast histogram boosting", ["classification", "multiclass", "regression"]),
        ("CatBoost",               "handles categoricals",   ["classification", "multiclass", "regression"]),
        ("HistGradientBoosting",   "sklearn equivalent",     ["classification", "multiclass", "regression"]),
    ],
    "Kernel & instance": [
        ("SVM (RBF)",     "kernel-based",         ["classification", "multiclass", "regression"]),
        ("SVM (Linear)",  "fast kernel",          ["classification", "multiclass", "regression"]),
        ("KNN",           "k-nearest neighbours", ["classification", "multiclass", "regression"]),
    ],
    "Probabilistic": [
        ("GaussianNB",    "naive bayes",      ["classification", "multiclass"]),
        ("BernoulliNB",   "binary features",  ["classification", "multiclass"]),
        ("QDA",           "quadratic discriminant", ["classification", "multiclass"]),
    ],
    "Neural networks": [
        ("MLP (Tabular)",   "shallow feedforward",      ["classification", "multiclass", "regression"]),
        ("TabNet",          "attention-based tabular",  ["classification", "multiclass", "regression"]),
        ("FT-Transformer",  "tabular transformer",      ["classification", "multiclass", "regression"]),
    ],
    "Ensembles": [
        ("VotingClassifier",      "soft/hard voting",   ["classification", "multiclass"]),
        ("StackingClassifier",    "meta-learner",       ["classification", "multiclass"]),
        ("BalancedRandomForest",  "imbalance-aware",    ["classification", "multiclass"]),
    ],
}
```

After filtering by `state["problem_type"]`, this gives 14–22 options depending on classification vs regression.

## Algorithm icon mapping

```python
ALGORITHM_ICONS = {
    "XGBoost":              "scatter-chart",
    "LightGBM":             "zap",
    "CatBoost":             "boxes",
    "HistGradientBoosting": "bar-chart-3",
    "RandomForest":         "trees",
    "ExtraTrees":           "trees",
    "DecisionTree":         "git-branch",
    "BalancedRandomForest": "scale",
    "LogisticRegression":   "trending-up",
    "RidgeClassifier":      "minimize-2",
    "SGDClassifier":        "fast-forward",
    "LinearRegression":     "trending-up",
    "Ridge":                "minimize-2",
    "Lasso":                "minimize",
    "SVM (RBF)":            "circle",
    "SVM (Linear)":         "slash",
    "KNN":                  "users",
    "GaussianNB":           "activity",
    "BernoulliNB":          "binary",
    "QDA":                  "trending-up",
    "MLP (Tabular)":        "network",
    "TabNet":               "layers",
    "FT-Transformer":       "boxes",
    "VotingClassifier":     "users",
    "StackingClassifier":   "layers-3",
}
```

## Adapter shim — `md_algorithm_registry_adapter.py`

```python
"""Adapter shim — translates between dashboard and modeling_agent / tool_registry.

Backend contract may change. This file isolates the dashboard from those changes.
Falls back to hard-coded defaults if backend methods are missing.
"""
from __future__ import annotations
import logging
import streamlit as st

logger = logging.getLogger(__name__)


# ── Public API ───────────────────────────────────────────────────────────────

def get_recommendation(state):
    """Return the recommended algorithm dict, falling back gracefully.

    Returns: {
        "name": str (canonical algorithm name),
        "display_name": str,
        "tag": str (e.g. "Recommended for binary classification"),
        "description": str (1-3 sentences),
        "strengths": list[str] (5 short chips),
        "default_hyperparameters": dict,
        "suggested_search_strategy": str,
        "suggested_validation": str,
    }
    """
    try:
        from agents import modeling_agent
        if hasattr(modeling_agent, "recommend_algorithm"):
            rec = modeling_agent.recommend_algorithm(state)
            if rec and "name" in rec:
                return _normalize_rec(rec, state)
    except Exception as e:
        logger.warning(f"recommend_algorithm failed: {e}, using fallback")

    return _fallback_recommendation(state)


def get_available_algorithms(problem_type, n_rows=None):
    """Return {family: [algo_dicts]} grouped, filtered to problem_type and dataset size."""
    try:
        from agents.tools import tool_registry
        if hasattr(tool_registry, "get_models_for_problem_type"):
            algos = tool_registry.get_models_for_problem_type(problem_type)
            return _group_by_family(algos, n_rows)
    except Exception as e:
        logger.warning(f"get_models_for_problem_type failed: {e}, using fallback")

    return _filter_fallback(problem_type, n_rows)


def get_icon_svg(algo_name):
    """Return the SVG markup for the algorithm icon (white-on-gradient inside the spotlight)."""
    icon_id = ALGORITHM_ICONS.get(algo_name, "cpu")
    return _ICON_SVGS.get(icon_id, _ICON_SVGS["cpu"])


# ── Fallback recommendation logic ────────────────────────────────────────────

def _fallback_recommendation(state):
    pt = state.get("problem_type", "classification")
    n_rows = state.get("schema_info", {}).get("row_count", 1000)

    if pt == "classification" or pt == "multiclass":
        # Determine severity from session_state's df_engineered
        severity = "balanced"
        df = st.session_state.get("df_engineered")
        target = state.get("target_column")
        if df is not None and target and target in df.columns:
            try:
                pos_rate = float(df[target].value_counts(normalize=True).iloc[0])
                diff = abs(pos_rate - 0.5)
                if diff >= 0.4: severity = "severe_imbalance"
                elif diff >= 0.2: severity = "imbalanced"
            except Exception:
                pass

        if severity == "severe_imbalance":
            name = "BalancedRandomForest"
            tag = "Recommended for severely imbalanced classification"
        else:
            name = "XGBoost"
            tag = f"Recommended for {pt.replace('_', ' ')}"

    elif pt == "regression":
        name = "RandomForest" if n_rows < 1000 else "LightGBM"
        tag = "Recommended for regression"

    elif pt == "clustering":
        name = "KMeans"
        tag = "Recommended for clustering"

    elif pt == "time_series":
        name = "Prophet"
        tag = "Recommended for time series forecasting"

    else:
        name = "XGBoost"
        tag = "Recommended"

    return {
        "name": name,
        "display_name": name,
        "tag": tag,
        "description": _DEFAULT_DESCRIPTIONS.get(name, "A solid baseline for this problem type."),
        "strengths": _DEFAULT_STRENGTHS.get(name, ["solid baseline"]),
        "default_hyperparameters": _DEFAULT_HYPERPARAMS.get(name, {}),
        "suggested_search_strategy": "Bayesian · 50 trials",
        "suggested_validation": "Stratified 5-fold" if pt in ("classification", "multiclass") else "K-Fold 5",
    }


def _normalize_rec(rec, state):
    """Ensure all expected keys are present."""
    rec.setdefault("display_name", rec["name"])
    rec.setdefault("tag", f"Recommended for {state.get('problem_type', '')}")
    rec.setdefault("description", _DEFAULT_DESCRIPTIONS.get(rec["name"], ""))
    rec.setdefault("strengths", _DEFAULT_STRENGTHS.get(rec["name"], ["solid baseline"]))
    rec.setdefault("default_hyperparameters", _DEFAULT_HYPERPARAMS.get(rec["name"], {}))
    rec.setdefault("suggested_search_strategy", "Bayesian · 50 trials")
    rec.setdefault("suggested_validation", "Stratified 5-fold")
    return rec


# ── Algorithm catalog (fallback) ─────────────────────────────────────────────

FALLBACK_ALGORITHMS = { ... }  # (paste the full dict from the top of this spec)

ALGORITHM_ICONS = { ... }  # (paste the full dict from the top of this spec)


def _group_by_family(algos, n_rows=None):
    """Group a flat list of algos into families. n_rows used to filter unsuitable ones."""
    families = {
        "Linear models": [], "Tree-based": [], "Gradient boosting": [],
        "Kernel & instance": [], "Probabilistic": [], "Neural networks": [],
        "Ensembles": [],
    }
    for a in algos:
        if n_rows is not None and a.get("min_rows", 0) > n_rows:
            continue  # Skip algorithms that need more data
        f = a.get("family", "Other").replace("_", " ").title()
        f = _family_to_display(f)
        families.setdefault(f, []).append({
            "name": a["name"],
            "short_desc": a.get("short_desc", a.get("description", "")[:30]),
            "supports": a.get("supports_problem_types", []),
        })
    return {k: v for k, v in families.items() if v}


def _family_to_display(raw):
    """Convert registry family enum to display name."""
    mapping = {
        "Linear": "Linear models",
        "Tree Based": "Tree-based",
        "Gradient Boosting": "Gradient boosting",
        "Kernel": "Kernel & instance",
        "Instance": "Kernel & instance",
        "Probabilistic": "Probabilistic",
        "Neural Network": "Neural networks",
        "Neural": "Neural networks",
        "Ensemble": "Ensembles",
    }
    return mapping.get(raw, raw)


def _filter_fallback(problem_type, n_rows=None):
    """Return FALLBACK_ALGORITHMS filtered to algorithms supporting problem_type."""
    out = {}
    for family, algos in FALLBACK_ALGORITHMS.items():
        filtered = [
            {"name": name, "short_desc": desc, "supports": supports}
            for name, desc, supports in algos
            if problem_type in supports
        ]
        if filtered:
            out[family] = filtered
    return out


# ── Default descriptions / strengths / hyperparameters ───────────────────────

_DEFAULT_DESCRIPTIONS = {
    "XGBoost": "Gradient-boosted decision trees consistently dominate tabular classification on datasets of this size. Robust to mixed feature types, handles imbalance well via scale_pos_weight, and ships built-in feature importance for explainability downstream.",
    "LightGBM": "Histogram-based gradient boosting with native handling of categorical features. Fastest training of the boosting family, especially on wide datasets.",
    "CatBoost": "Boosting that handles categorical features natively without one-hot encoding. Strong defaults, robust to overfitting.",
    "RandomForest": "Bagged ensemble of decision trees. Excellent baseline, robust to outliers, no scaling required.",
    "BalancedRandomForest": "Random forest variant that resamples each bootstrap to balance class weights. Recommended when positive class rate is below 10%.",
    "LogisticRegression": "Linear baseline with interpretable coefficients. Fast inference, well-calibrated probabilities, great for explainability.",
    "KMeans": "Partitions data into K clusters by minimising within-cluster variance. Simple, fast, scales to millions of points.",
    "Prophet": "Decomposable time-series model from Meta. Handles seasonality, holidays, and missing data gracefully.",
    "MLP (Tabular)": "Shallow feedforward neural network. Useful when there's a non-linear relationship that trees can't capture.",
    "SVM (RBF)": "Support vector machine with RBF kernel. Strong for medium-sized datasets with non-linear boundaries.",
    "KNN": "K-nearest neighbours. Non-parametric, simple to interpret, slower at inference but often a useful baseline.",
}

_DEFAULT_STRENGTHS = {
    "XGBoost": ["tabular winner", "handles missing values", "fast inference (~2ms)", "SHAP-friendly", "imbalance-aware"],
    "LightGBM": ["fast training", "categorical-native", "low memory", "high accuracy", "scales well"],
    "CatBoost": ["categorical-native", "robust defaults", "GPU-friendly", "feature importance"],
    "RandomForest": ["robust baseline", "no scaling needed", "feature importance", "handles missing values"],
    "BalancedRandomForest": ["imbalance-first", "robust to noise", "feature importance"],
    "LogisticRegression": ["interpretable", "fast", "well-calibrated", "tiny model size"],
    "KMeans": ["fast", "scalable", "interpretable centroids"],
    "Prophet": ["handles seasonality", "robust to missing data", "interpretable components"],
    "MLP (Tabular)": ["non-linear", "flexible", "GPU-accelerated"],
    "SVM (RBF)": ["non-linear boundaries", "robust to outliers"],
    "KNN": ["simple", "non-parametric", "interpretable"],
}

_DEFAULT_HYPERPARAMS = {
    "XGBoost": {
        "n_estimators": 500, "learning_rate": 0.05, "max_depth": 6, "subsample": 0.8,
        "colsample_bytree": 0.8, "min_child_weight": 1, "gamma": 0.0,
        "reg_alpha": 0.0, "reg_lambda": 1.0, "scale_pos_weight": 1.0,
        "tree_method": "hist", "booster": "gbtree", "early_stopping_rounds": 50,
        "eval_metric": "auc", "random_state": 42,
    },
    "LightGBM": {
        "num_leaves": 31, "learning_rate": 0.05, "n_estimators": 500,
        "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 5,
        "min_child_samples": 20, "max_depth": -1, "reg_alpha": 0.0, "reg_lambda": 0.0,
        "boosting_type": "gbdt", "objective": "binary", "metric": "auc",
        "scale_pos_weight": 1.0, "early_stopping_rounds": 50, "random_state": 42,
    },
    "RandomForest": {
        "n_estimators": 500, "max_depth": None, "min_samples_split": 2, "max_features": "sqrt",
        "min_samples_leaf": 1, "class_weight": "balanced", "n_jobs": -1, "random_state": 42,
    },
    "LogisticRegression": {
        "C": 1.0, "penalty": "l2", "solver": "lbfgs", "class_weight": "balanced",
        "max_iter": 1000, "tol": 1e-4, "random_state": 42,
    },
    # ... add more as the schema introspection in spec 04 will fill gaps
}


_ICON_SVGS = {
    "cpu":           '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="2" x2="9" y2="4"/><line x1="15" y1="2" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="22"/><line x1="15" y1="20" x2="15" y2="22"/></svg>',
    "scatter-chart": '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0z"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>',
    "trees":         '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 13v8M12 3v3M8 6l4-3 4 3M5 13l3-3 4 3 4-3 3 3"/></svg>',
    "trending-up":   '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    "zap":           '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "network":       '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="5" r="2"/><circle cx="5" cy="12" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="12" cy="19" r="2"/><line x1="12" y1="7" x2="12" y2="17"/><line x1="7" y1="12" x2="17" y2="12"/></svg>',
    "circle":        '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>',
    # ... add a few more for completeness; default to "cpu" for unknown
}
```

## Spotlight component — `md_algorithm_spotlight.py`

```python
"""Recommended-algorithm spotlight card."""
from __future__ import annotations
import streamlit as st

from dashboard.components import md_algorithm_registry_adapter as reg
from services.project_service import get_project_service

CACHE_KEY = "md_recommendation"


def render(state):
    rec = _get_or_compute_recommendation(state)
    if rec is None:
        st.error("Could not generate algorithm recommendation. Check that modeling_agent is loaded.")
        return

    # Open Section 01 wrapper
    st.markdown("""
    <div class="md-sec">
      <div class="md-sec-head">
        <div class="md-sec-num">01</div>
        <div style="flex:1;">
          <div class="md-sec-title">Problem & <em>algorithm</em></div>
          <div class="md-sec-meta">Detected from your target column · auto-recommended best fit</div>
        </div>
      </div>
    """, unsafe_allow_html=True)

    # The problem-type recap (spec 02) was already rendered just before this — we render
    # its closing elements separately. To keep things clean, the section wrapper opens here
    # and closes at the end of md_algorithm_picker.render() (next component in chain).

    icon_svg = reg.get_icon_svg(rec["name"])
    strengths_html = "".join(
        f'<span class="md-algo-strength">{s}</span>' for s in rec.get("strengths", [])
    )

    st.markdown(f"""
    <div class="md-algo-spot">
      <div class="md-algo-icon">{icon_svg}</div>
      <div class="md-algo-body">
        <div class="md-algo-tag">{rec["tag"]}</div>
        <div class="md-algo-name"><em>{rec["display_name"]}</em></div>
        <div class="md-algo-desc">{rec["description"]}</div>
        <div class="md-algo-strengths">{strengths_html}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Persist into modeling_config so HP cards can read it
    cfg = state.get("modeling_config", {}) or {}
    if cfg.get("recommended_algorithm") != rec["name"]:
        svc = get_project_service()
        cfg["recommended_algorithm"] = rec["name"]
        cfg["recommended_default_hp"] = rec.get("default_hyperparameters", {})
        cfg.setdefault("suggested_search_strategy", rec.get("suggested_search_strategy"))
        cfg.setdefault("suggested_validation", rec.get("suggested_validation"))
        svc.update_state(state["project_id"], {"modeling_config": cfg})


def _get_or_compute_recommendation(state):
    """Cache so we don't re-call the LLM on every Streamlit rerun."""
    cache_inputs = (
        state.get("problem_type"),
        state.get("target_column"),
        state.get("detected_domain"),
        state.get("modeling_overridden", False),
    )
    cached = st.session_state.get(CACHE_KEY)
    if cached and cached.get("inputs") == cache_inputs:
        return cached["rec"]

    rec = reg.get_recommendation(state)
    st.session_state[CACHE_KEY] = {"inputs": cache_inputs, "rec": rec}
    return rec
```

## Multi-select component — `md_algorithm_picker.py`

```python
"""'Or compare against:' multi-select dropdown."""
from __future__ import annotations
import streamlit as st

from dashboard.components import md_algorithm_registry_adapter as reg
from services.project_service import get_project_service

SELECTED_KEY = "md_selected_algos"


def render(state):
    problem_type = state.get("problem_type", "classification")
    n_rows = state.get("schema_info", {}).get("row_count", 1000)
    available = reg.get_available_algorithms(problem_type, n_rows=n_rows)
    rec_name = state.get("modeling_config", {}).get("recommended_algorithm")

    # Initialise selection — recommended is always included
    if SELECTED_KEY not in st.session_state:
        st.session_state[SELECTED_KEY] = [rec_name] if rec_name else []
    elif rec_name and rec_name not in st.session_state[SELECTED_KEY]:
        st.session_state[SELECTED_KEY].insert(0, rec_name)

    selected = st.session_state[SELECTED_KEY]

    # Compose summary text
    if not selected:
        summary = "<strong>0 selected</strong> · pick at least one"
    else:
        names = selected[:3]
        more = f" +{len(selected) - 3}" if len(selected) > 3 else ""
        summary = f"<strong>{len(selected)} selected</strong> · {', '.join(names)}{more}"

    # Render label + summary (visual only — actual interaction via expander below)
    st.markdown(f"""
    <div class="md-compare">
      <label class="md-compare-label">Or compare against:</label>
      <div class="md-multiselect-trigger" style="cursor:default;">
        <span class="md-multiselect-summary">{summary}</span>
        <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit-native expander — styled via CSS to match the panel
    with st.expander("Choose algorithms (click to expand)", expanded=False):
        search = st.text_input(
            "Search",
            key="md_ms_search",
            placeholder="Search algorithms…",
            label_visibility="collapsed",
        )

        new_selection = []
        for family, algos in available.items():
            st.markdown(f'<div class="md-multiselect-group-label">{family}</div>',
                        unsafe_allow_html=True)
            for algo in algos:
                name = algo["name"]
                if search and search.lower() not in name.lower():
                    continue
                is_recommended = (name == rec_name)
                cb_key = f"md_algo_cb_{name}"

                checked = st.checkbox(
                    f"{name} · {algo['short_desc']}" + (" ★ recommended (locked)" if is_recommended else ""),
                    value=(name in selected) or is_recommended,
                    disabled=is_recommended,
                    key=cb_key,
                )
                if checked:
                    new_selection.append(name)

        # Diff + persist
        if set(new_selection) != set(selected):
            # Always keep the recommended at index 0
            if rec_name and rec_name not in new_selection:
                new_selection.insert(0, rec_name)
            elif rec_name and new_selection[0] != rec_name:
                new_selection.remove(rec_name)
                new_selection.insert(0, rec_name)

            st.session_state[SELECTED_KEY] = new_selection

            svc = get_project_service()
            cfg = state.get("modeling_config", {}) or {}
            cfg["selected_algorithms"] = new_selection
            svc.update_state(state["project_id"], {"modeling_config": cfg})
            st.rerun()

    # Close the .md-sec wrapper opened in the spotlight
    st.markdown("</div>", unsafe_allow_html=True)
```

## State writes

```python
state["modeling_config"]["recommended_algorithm"]  # str
state["modeling_config"]["recommended_default_hp"] # dict
state["modeling_config"]["suggested_search_strategy"]  # str (if not overridden)
state["modeling_config"]["suggested_validation"]   # str (if not overridden)
state["modeling_config"]["selected_algorithms"]    # list[str]
```

## Smoke test for spec 03

1. Land on Modeling with Titanic
2. ✅ Spotlight card renders with XGBoost + glowing border + 5 strength chips
3. ✅ Multi-select trigger reads "1 selected · XGBoost"
4. ✅ Open the expander → see 6 family groups, ~14 algorithms (filtered to classification + n_rows≥100)
5. ✅ XGBoost is checked + disabled (locked-in) with "★ recommended (locked)" suffix
6. ✅ Search "tree" → only RandomForest, ExtraTrees, DecisionTree, BalancedRandomForest visible
7. ✅ Check LogisticRegression + RandomForest → trigger updates to "3 selected · XGBoost, LogisticRegression, RandomForest"
8. ✅ State has `modeling_config.selected_algorithms = ["XGBoost", "LogisticRegression", "RandomForest"]` (XGBoost always first)
9. ✅ Override problem_type to regression in spec 02 → spotlight changes to LightGBM (or RandomForest if small data), multi-select repopulates with regression-supporting algorithms

## Edge cases to handle

- `recommend_algorithm` returns `None` or raises → use fallback, log warning
- `tool_registry` doesn't have `get_models_for_problem_type` → use FALLBACK_ALGORITHMS dict
- Recommendation name doesn't match any registry entry → still render spotlight, but the multi-select panel might not have it; the picker auto-adds it if missing
- User has previous `selected_algorithms` in state from an earlier session → respect that selection on re-entry, ensure recommended is still in the list at index 0
- Severe class imbalance + recommendation = `BalancedRandomForest` → that's correct, don't override to XGBoost
- Tiny dataset (<100 rows) → `min_rows` filter excludes deep learning models from picker
- All algorithms unchecked except recommended (which is locked) → still has 1 algorithm; the action bar's "Start Training" button is enabled; spec 06 handles this
