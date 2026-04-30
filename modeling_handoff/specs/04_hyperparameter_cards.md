# Spec 04 — Hyperparameter Tuning Cards (Section 02)

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section:** `<div class="md-sec">` numbered **02** — "Hyperparameter tuning"
**Lines:** ~1064–1364 (the entire `<div id="md-hp-stack">` block including the empty-state)

Open the mockup and toggle checkboxes in the section 01 multi-select dropdown — watch how section 02 dynamically shows/hides cards. **That is the exact behavior to reproduce in Streamlit.**

---

## What this section is

Per-algorithm hyperparameter editor, **driven entirely by the algorithms checked in Section 01's multi-select dropdown.**

The user does NOT see all 22 algorithms' HP cards. They see exactly one card per checked algorithm. If they uncheck an algorithm in section 01, its card disappears from section 02. If they check a new algorithm, its card appears.

Each card shows:
1. **Algorithm name** as the card header (with "★ Recommended" pill on the recommended algorithm)
2. **Top 4 most-important hyperparameters** displayed inline as `<input>` and `<select>` widgets — pre-filled with recommended values, ★ markers on the recommended ones
3. An **expander** "All hyperparameters · N more" that reveals the rest of the parameter space (unfolded into a grid below the inline 4)
4. A **Search strategy dropdown** at the card footer (Bayesian/Grid/Random/Optuna/exact) — per-algorithm, defaults to "Bayesian optimization · 50 trials ★"

The cards are collapsible (head click toggles expanded/collapsed). The recommended algorithm's card starts expanded; all others start collapsed.

When **zero** algorithms are checked, an **empty-state** is shown with a crossed-circle icon and message "No algorithms selected · pick at least one in section 01 to configure its hyperparameters."

---

## Hard rules

1. **Driven by Section 01.** The set of cards is `state["modeling_config"]["selected_algorithms"]`. Section 04 multi-select writes this; section 02 reads it. Section 02 NEVER lets the user select/deselect algorithms — that's section 01's job.
2. **Adapter pattern.** All hyperparameter schemas come from a thin adapter `dashboard/components/md_hp_schema_adapter.py` that calls into the existing model registry (or falls back to introspection). Never modify `agents/tools/tool_registry.py`, `agents/tools/ml_tools.py`, or any non-dashboard code.
3. **Templates for top 9 algorithms, generic placeholder for the rest.** Hand-curated templates exist for: XGBoost, LogisticRegression, RandomForest, LightGBM, RidgeClassifier, CatBoost, SVM-RBF, KNN, MLP-Tabular. Any other selected algorithm renders a generic placeholder card with the schema introspected from the model class (or from the registry entry).
4. **Recommended values pre-filled.** ★ markers next to fields and "recommended X · range Y-Z" hints (where applicable) come from a small `RECOMMENDED_DEFAULTS` dict in the adapter.
5. **Per-algorithm search strategy.** Each card has its own search-strategy dropdown. Default is `"bayesian"`. Writes to `state["modeling_config"]["search_strategy"][algo_name]`.
6. **Validation on commit, not on edit.** As the user types in a field, store the raw string. Only when the user clicks "Start Training" (section 04 action bar) do we coerce types and validate ranges. If invalid, show error toast and stay in configure phase. Never silently coerce mid-typing — destroys UX.
7. **Imbalance-aware defaults.** For classifiers, `class_weight` defaults to `"balanced"` if `state["data_profile"]["target_imbalance_ratio"] < 0.3` (i.e. minority class is <30%). For tree models, `scale_pos_weight` is auto-computed from imbalance ratio.

---

## Files to create

```
dashboard/components/
  md_hp_panel.py                  # The orchestrator — renders section 02 in full
  md_hp_card.py                   # Renders a single algorithm's HP card
  md_hp_schema_adapter.py         # Pulls HP schema for an algo from registry or introspection
  md_hp_templates.py              # The 9 hand-curated templates
```

No backend files modified.

---

## File 1 — `md_hp_schema_adapter.py`

```python
"""
Adapter — translates AutoDS's internal model registry into HP schema dicts
that the UI can render. Pure translation, no business logic.

Schema shape returned by `get_schema_for(algo_name, problem_type, state)`:
{
    "algo_name": "XGBoost",                         # canonical name
    "registry_key": "xgboost_classifier",           # key in tool_registry["models"]
    "icon": "✦",
    "is_recommended": False,                        # True only for the one algo
                                                    # state["modeling_config"]["recommended"] points to
    "top_params": [                                 # ordered list, max 4
        {
            "name": "n_estimators",
            "label": "n_estimators",
            "type": "int",                          # int | float | str | bool | choice
            "default": 500,
            "recommended": 500,                     # may equal default; if not, ★ on recommended
            "range": [100, 2000],                   # for numeric only
            "choices": None,                        # for type=="choice" only
            "help": "Number of boosting rounds",
            "is_recommended": True,                 # show ★ in label
        },
        # ... up to 4 entries
    ],
    "all_params": [                                 # FULL schema — top_params is a subset
        # same shape as top_params
        # rendered inside the "All hyperparameters · N more" expander
        # the count "N more" = len(all_params) - len(top_params)
    ],
    "search_strategies": [
        {"key": "bayesian", "label": "Bayesian optimization · 50 trials ★", "is_recommended": True},
        {"key": "grid", "label": "Grid search · full combinations"},
        {"key": "random", "label": "Random search · 100 trials"},
        {"key": "optuna", "label": "Optuna · 200 trials w/ pruning"},
        {"key": "exact", "label": "Use exact values above (no search)"},
    ],
}
"""

import inspect
import importlib
import logging
from typing import Any

from dashboard.components.md_hp_templates import (
    HP_TEMPLATES, RECOMMENDED_DEFAULTS, ICONS_BY_ALGO,
)

logger = logging.getLogger(__name__)


def get_schema_for(algo_name: str, problem_type: str, state: dict) -> dict:
    """
    Return a complete HP schema for one algorithm.
    Tries hand-curated template first, falls back to introspection.
    """
    # 1) Try hand-curated template
    template = HP_TEMPLATES.get(algo_name)
    if template:
        schema = _apply_state_overrides(template, problem_type, state)
        schema["icon"] = ICONS_BY_ALGO.get(algo_name, "◆")
        schema["is_recommended"] = (
            state.get("modeling_config", {}).get("recommended_algorithm") == algo_name
        )
        return schema

    # 2) Fall back to registry introspection
    return _build_schema_from_registry(algo_name, problem_type, state)


def get_search_strategies() -> list[dict]:
    """Static list, same for every algorithm."""
    return [
        {"key": "bayesian", "label": "Bayesian optimization · 50 trials ★", "is_recommended": True},
        {"key": "grid", "label": "Grid search · full combinations"},
        {"key": "random", "label": "Random search · 100 trials"},
        {"key": "optuna", "label": "Optuna · 200 trials w/ pruning"},
        {"key": "exact", "label": "Use exact values above (no search)"},
    ]


# ───────────────── private helpers ─────────────────

def _apply_state_overrides(template: dict, problem_type: str, state: dict) -> dict:
    """
    Mutate a copy of the template with state-aware overrides.
    Examples:
      - class_weight → "balanced" if imbalance ratio is high
      - scale_pos_weight → computed from imbalance ratio
      - random_state → state["random_seed"]
    """
    import copy
    schema = copy.deepcopy(template)

    seed = state.get("random_seed", 42)
    profile = state.get("data_profile", {})
    imbalance_ratio = profile.get("target_imbalance_ratio")
    is_classification = problem_type in ("binary_classification", "multiclass_classification")

    def _patch(param_list):
        for p in param_list:
            if p["name"] in ("random_state", "random_seed"):
                p["default"] = seed
                p["recommended"] = seed
            if is_classification and p["name"] == "class_weight":
                if imbalance_ratio is not None and imbalance_ratio < 0.3:
                    p["default"] = "balanced"
                    p["recommended"] = "balanced"
                    p["is_recommended"] = True
            if is_classification and p["name"] == "scale_pos_weight":
                if imbalance_ratio is not None and imbalance_ratio > 0:
                    # scale_pos_weight = neg / pos
                    spw = round((1 - imbalance_ratio) / imbalance_ratio, 2)
                    p["default"] = spw
                    p["recommended"] = spw
                    p["is_recommended"] = True
                    p["help"] = f"Auto-computed from imbalance ratio ({imbalance_ratio:.2f})"

    _patch(schema["top_params"])
    _patch(schema["all_params"])
    return schema


def _build_schema_from_registry(algo_name: str, problem_type: str, state: dict) -> dict:
    """
    For algorithms without a dedicated template, introspect the model class
    via importlib + inspect.signature. Best-effort schema reconstruction.
    """
    try:
        from agents.tools import tool_registry
        models = getattr(tool_registry, "TOOL_REGISTRY", {}).get("models", {})
        # Find the registry entry whose name matches algo_name (case-insensitive)
        entry = None
        for key, val in models.items():
            if val.get("name", "").lower().replace(" ", "") == algo_name.lower().replace(" ", ""):
                entry = val
                break
        if not entry:
            return _empty_schema(algo_name)

        # Try to load the underlying class from entry["function"]
        fn_path = entry.get("function", "")
        cls = _resolve_model_class(fn_path)
        if cls is None:
            return _empty_schema(algo_name)

        # Introspect __init__ signature
        sig = inspect.signature(cls.__init__)
        all_params = []
        for pname, p in sig.parameters.items():
            if pname in ("self", "args", "kwargs"):
                continue
            default = p.default if p.default is not inspect.Parameter.empty else None
            ptype = _infer_type(default)
            all_params.append({
                "name": pname,
                "label": pname,
                "type": ptype,
                "default": default,
                "recommended": default,
                "range": None,
                "choices": None,
                "help": "",
                "is_recommended": False,
            })

        # Pick top-4 by heuristic (those most often in tutorials)
        top_names = _heuristic_top_names(algo_name, [p["name"] for p in all_params])
        top_params = [p for p in all_params if p["name"] in top_names][:4]

        return {
            "algo_name": algo_name,
            "registry_key": fn_path.split(".")[-1] if fn_path else algo_name.lower(),
            "icon": ICONS_BY_ALGO.get(algo_name, "◆"),
            "is_recommended": (
                state.get("modeling_config", {}).get("recommended_algorithm") == algo_name
            ),
            "top_params": top_params,
            "all_params": all_params,
            "search_strategies": get_search_strategies(),
        }
    except Exception as e:
        logger.warning(f"HP schema introspection failed for {algo_name}: {e}")
        return _empty_schema(algo_name)


def _empty_schema(algo_name: str) -> dict:
    """Last-resort schema when nothing can be introspected."""
    return {
        "algo_name": algo_name,
        "registry_key": algo_name.lower().replace(" ", "_"),
        "icon": "◆",
        "is_recommended": False,
        "top_params": [
            {
                "name": "random_state", "label": "random_state", "type": "int",
                "default": 42, "recommended": 42, "range": None, "choices": None,
                "help": "Random seed for reproducibility", "is_recommended": True,
            },
        ],
        "all_params": [
            {
                "name": "random_state", "label": "random_state", "type": "int",
                "default": 42, "recommended": 42, "range": None, "choices": None,
                "help": "", "is_recommended": True,
            },
        ],
        "search_strategies": get_search_strategies(),
    }


def _resolve_model_class(fn_path: str):
    """Resolve dotted path like 'sklearn.ensemble.RandomForestClassifier' to the class."""
    if not fn_path:
        return None
    try:
        module_path, _, cls_name = fn_path.rpartition(".")
        if not module_path:
            return None
        mod = importlib.import_module(module_path)
        return getattr(mod, cls_name, None)
    except Exception:
        return None


def _infer_type(default):
    if isinstance(default, bool):
        return "bool"
    if isinstance(default, int):
        return "int"
    if isinstance(default, float):
        return "float"
    if default is None:
        return "str"
    return "str"


def _heuristic_top_names(algo_name: str, all_names: list[str]) -> list[str]:
    """Best-effort top-4 picker for unknown algorithms."""
    common = ["n_estimators", "learning_rate", "max_depth", "C", "alpha",
              "n_neighbors", "kernel", "gamma", "criterion", "max_iter",
              "tol", "hidden_layer_sizes"]
    return [n for n in common if n in all_names][:4]
```

---

## File 2 — `md_hp_templates.py`

The hand-curated templates. **You will populate this with 9 templates** matching exactly what's in the mockup. The structure for each is identical — here's XGBoost as the canonical example, the rest follow the same shape:

```python
"""
Hand-curated HP schemas for the 9 most common algorithms.
Each template is a dict matching the schema shape in md_hp_schema_adapter.

Recommended values come from:
  - sklearn / xgboost / lightgbm / catboost docs
  - Bayesian search history on common benchmark datasets
  - Per-algorithm best practice (e.g. XGBoost docs recommend learning_rate=0.05 + n_estimators=500)
"""

ICONS_BY_ALGO = {
    "XGBoost": "✦",
    "LogisticRegression": "◯",
    "RandomForest": "◇",
    "LightGBM": "✦",
    "RidgeClassifier": "◯",
    "CatBoost": "✦",
    "SVM-RBF": "◈",
    "KNN": "◈",
    "MLP-Tabular": "▲",
}

RECOMMENDED_DEFAULTS = {
    # algo_name → param_name → recommended value
    "XGBoost": {
        "n_estimators": 500, "learning_rate": 0.05, "max_depth": 6, "subsample": 0.8,
        "colsample_bytree": 0.8, "min_child_weight": 1, "tree_method": "hist",
        "booster": "gbtree", "eval_metric": "auc", "early_stopping_rounds": 50,
    },
    # ... (one entry per templated algorithm)
}

HP_TEMPLATES = {
    "XGBoost": {
        "algo_name": "XGBoost",
        "registry_key": "xgboost_classifier",
        "top_params": [
            {
                "name": "n_estimators", "label": "n_estimators", "type": "int",
                "default": 500, "recommended": 500, "range": [100, 2000],
                "choices": None, "help": "Number of boosting rounds",
                "is_recommended": True,
            },
            {
                "name": "learning_rate", "label": "learning_rate", "type": "float",
                "default": 0.05, "recommended": 0.05, "range": [0.01, 0.3],
                "choices": None, "help": "Step size shrinkage", "is_recommended": True,
            },
            {
                "name": "max_depth", "label": "max_depth", "type": "int",
                "default": 6, "recommended": 6, "range": [3, 12],
                "choices": None, "help": "Maximum tree depth", "is_recommended": True,
            },
            {
                "name": "subsample", "label": "subsample", "type": "float",
                "default": 0.8, "recommended": 0.8, "range": [0.5, 1.0],
                "choices": None, "help": "Row subsampling ratio", "is_recommended": False,
            },
        ],
        "all_params": [
            # ── start with the same 4 ──
            # ... (copy top_params items)
            # ── then 14 more ──
            {"name": "colsample_bytree", "label": "colsample_bytree", "type": "float",
             "default": 0.8, "recommended": 0.8, "range": [0.5, 1.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "min_child_weight", "label": "min_child_weight", "type": "int",
             "default": 1, "recommended": 1, "range": [1, 10], "choices": None, "help": "", "is_recommended": False},
            {"name": "gamma", "label": "gamma", "type": "float",
             "default": 0.0, "recommended": 0.0, "range": [0.0, 5.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "reg_alpha", "label": "reg_alpha (L1)", "type": "float",
             "default": 0.0, "recommended": 0.0, "range": [0.0, 1.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "reg_lambda", "label": "reg_lambda (L2)", "type": "float",
             "default": 1.0, "recommended": 1.0, "range": [0.0, 1.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "scale_pos_weight", "label": "scale_pos_weight", "type": "float",
             "default": 1.0, "recommended": 1.0, "range": None, "choices": None,
             "help": "Auto-set from imbalance ratio at runtime", "is_recommended": True},
            {"name": "tree_method", "label": "tree_method", "type": "choice",
             "default": "hist", "recommended": "hist", "range": None,
             "choices": ["hist", "auto", "exact", "approx", "gpu_hist"], "help": "", "is_recommended": True},
            {"name": "booster", "label": "booster", "type": "choice",
             "default": "gbtree", "recommended": "gbtree", "range": None,
             "choices": ["gbtree", "dart", "gblinear"], "help": "", "is_recommended": True},
            {"name": "early_stopping_rounds", "label": "early_stopping_rounds", "type": "int",
             "default": 50, "recommended": 50, "range": [10, 200], "choices": None, "help": "", "is_recommended": False},
            {"name": "eval_metric", "label": "eval_metric", "type": "choice",
             "default": "auc", "recommended": "auc", "range": None,
             "choices": ["auc", "logloss", "error", "aucpr"], "help": "", "is_recommended": True},
            {"name": "max_delta_step", "label": "max_delta_step", "type": "int",
             "default": 0, "recommended": 0, "range": [0, 10], "choices": None, "help": "", "is_recommended": False},
            {"name": "colsample_bylevel", "label": "colsample_bylevel", "type": "float",
             "default": 1.0, "recommended": 1.0, "range": [0.5, 1.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "colsample_bynode", "label": "colsample_bynode", "type": "float",
             "default": 1.0, "recommended": 1.0, "range": [0.5, 1.0], "choices": None, "help": "", "is_recommended": False},
            {"name": "random_state", "label": "random_state", "type": "int",
             "default": 42, "recommended": 42, "range": None, "choices": None,
             "help": "Auto-set from state['random_seed']", "is_recommended": True},
        ],
    },

    # ────────────────────────────────────────────────
    # Add the other 8 templates here following the same shape:
    #   "LogisticRegression":  4 top + 6 more = 10 total
    #   "RandomForest":        4 top + 9 more = 13 total
    #   "LightGBM":            4 top + 12 more = 16 total
    #   "RidgeClassifier":     4 top + 4 more = 8 total
    #   "CatBoost":            4 top + 9 more = 13 total
    #   "SVM-RBF":             4 top + 5 more = 9 total
    #   "KNN":                 4 top + 3 more = 7 total
    #   "MLP-Tabular":         4 top + 8 more = 12 total
    # Use the EXACT field names, defaults, and recommended values that appear
    # in reference/modeling_mockup.html (lines 1146–1364). Do not invent new fields.
    # ────────────────────────────────────────────────
}
```

**The full list of fields per template is exactly what's in `reference/modeling_mockup.html`** between the `<div class="md-hp-card" data-algo="...">` markers. Copy them faithfully — labels, defaults, choice options, ★ markers.

---

## File 3 — `md_hp_card.py`

```python
"""
Renders one algorithm's HP card. Returns nothing — writes directly to st.session_state
under state['modeling_config']['hyperparameters'][algo_name].
"""

import streamlit as st
from dashboard.components.md_hp_schema_adapter import get_search_strategies


HP_VALUES_KEY = "md_hp_values"          # session_state[HP_VALUES_KEY][algo][param] = raw_str_value
HP_STRATEGY_KEY = "md_hp_strategy"      # session_state[HP_STRATEGY_KEY][algo] = strategy_key
HP_EXPANDED_KEY = "md_hp_expanded"      # session_state[HP_EXPANDED_KEY][algo] = bool (card open)


def render_card(schema: dict, project_id: str) -> None:
    """
    Render a single HP card. Reads/writes to st.session_state.
    `project_id` is used to namespace widget keys so different projects don't collide.
    """
    algo = schema["algo_name"]
    is_recommended = schema["is_recommended"]

    _ensure_state(algo, schema)

    # Card head
    head_cols = st.columns([0.85, 0.15])
    with head_cols[0]:
        prefix = f"{schema['icon']} " if schema['icon'] else ""
        rec_pill = " ★ Recommended" if is_recommended else ""
        st.markdown(
            f"<div class='md-hp-card-head'>{prefix}<strong>{algo}</strong>"
            f"<span class='md-hp-tag-inline'>{rec_pill}</span></div>",
            unsafe_allow_html=True,
        )
    with head_cols[1]:
        if st.button("▾" if st.session_state[HP_EXPANDED_KEY][algo] else "▸",
                     key=f"hp_toggle_{project_id}_{algo}"):
            st.session_state[HP_EXPANDED_KEY][algo] = not st.session_state[HP_EXPANDED_KEY][algo]
            st.rerun()

    if not st.session_state[HP_EXPANDED_KEY][algo]:
        return

    # Body — top-4 inline
    grid_cols = st.columns(2)
    for i, p in enumerate(schema["top_params"]):
        with grid_cols[i % 2]:
            _render_param(algo, p, project_id, prefix="top")

    # All hyperparameters — expander
    extras_count = len(schema["all_params"]) - len(schema["top_params"])
    if extras_count > 0:
        with st.expander(f"All hyperparameters · {extras_count} more", expanded=False):
            extra_grid = st.columns(2)
            top_names = {p["name"] for p in schema["top_params"]}
            extras = [p for p in schema["all_params"] if p["name"] not in top_names]
            for i, p in enumerate(extras):
                with extra_grid[i % 2]:
                    _render_param(algo, p, project_id, prefix="all")

    # Search strategy
    strategies = schema["search_strategies"]
    labels = [s["label"] for s in strategies]
    keys = [s["key"] for s in strategies]
    current = st.session_state[HP_STRATEGY_KEY].get(algo, "bayesian")
    try:
        idx = keys.index(current)
    except ValueError:
        idx = 0
    selected_label = st.selectbox(
        "Search strategy",
        options=labels,
        index=idx,
        key=f"hp_strategy_{project_id}_{algo}",
    )
    st.session_state[HP_STRATEGY_KEY][algo] = keys[labels.index(selected_label)]


# ───────────────── private ─────────────────

def _ensure_state(algo: str, schema: dict):
    if HP_VALUES_KEY not in st.session_state:
        st.session_state[HP_VALUES_KEY] = {}
    if HP_STRATEGY_KEY not in st.session_state:
        st.session_state[HP_STRATEGY_KEY] = {}
    if HP_EXPANDED_KEY not in st.session_state:
        st.session_state[HP_EXPANDED_KEY] = {}

    if algo not in st.session_state[HP_VALUES_KEY]:
        # Initialize with defaults
        st.session_state[HP_VALUES_KEY][algo] = {
            p["name"]: _stringify(p["default"]) for p in schema["all_params"]
        }
    if algo not in st.session_state[HP_STRATEGY_KEY]:
        # Default to recommended strategy
        for s in schema["search_strategies"]:
            if s.get("is_recommended"):
                st.session_state[HP_STRATEGY_KEY][algo] = s["key"]
                break
        else:
            st.session_state[HP_STRATEGY_KEY][algo] = "bayesian"
    if algo not in st.session_state[HP_EXPANDED_KEY]:
        st.session_state[HP_EXPANDED_KEY][algo] = schema.get("is_recommended", False)


def _render_param(algo: str, p: dict, project_id: str, prefix: str):
    """Render a single param widget and persist the value to session_state."""
    label = p["label"] + (" ★" if p.get("is_recommended") else "")
    key = f"hp_{project_id}_{algo}_{prefix}_{p['name']}"
    current_raw = st.session_state[HP_VALUES_KEY][algo].get(p["name"], _stringify(p["default"]))

    if p["type"] == "choice":
        choices = p["choices"] or []
        try:
            idx = choices.index(_unstringify(current_raw, "str"))
        except (ValueError, KeyError):
            idx = 0
        new_val = st.selectbox(label, options=choices, index=idx, key=key, help=p.get("help") or None)
        st.session_state[HP_VALUES_KEY][algo][p["name"]] = _stringify(new_val)
    elif p["type"] == "bool":
        try:
            idx = ["True", "False"].index(current_raw)
        except ValueError:
            idx = 0
        new_val = st.selectbox(label, options=["True", "False"], index=idx, key=key, help=p.get("help") or None)
        st.session_state[HP_VALUES_KEY][algo][p["name"]] = new_val
    else:
        new_val = st.text_input(label, value=current_raw, key=key, help=p.get("help") or None)
        st.session_state[HP_VALUES_KEY][algo][p["name"]] = new_val

    # Recommendation hint
    if p.get("recommended") is not None and p.get("range"):
        rec_str = f"recommended {_stringify(p['recommended'])} · range {p['range'][0]}-{p['range'][1]}"
        st.markdown(f"<div class='md-rec-hint'>{rec_str}</div>", unsafe_allow_html=True)


def _stringify(v: Any) -> str:
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v)


def _unstringify(s: str, target_type: str) -> Any:
    if s == "None":
        return None
    if target_type == "int":
        return int(float(s))
    if target_type == "float":
        return float(s)
    if target_type == "bool":
        return s.lower() in ("true", "1", "yes")
    return s
```

Type imports needed at top: `from typing import Any`.

---

## File 4 — `md_hp_panel.py`

```python
"""
Section 02 panel — orchestrates the whole HP step.
Reads selected algorithms from state, renders one card per algorithm,
shows empty-state when zero are selected.
"""

import streamlit as st
from dashboard.components.md_hp_schema_adapter import get_schema_for
from dashboard.components.md_hp_card import render_card


def render(state: dict, project_id: str) -> None:
    """Render section 02 in full."""
    selected = state.get("modeling_config", {}).get("selected_algorithms", [])
    problem_type = state.get("problem_type", "binary_classification")

    # ── Header ──
    n = len(selected)
    if n == 0:
        meta_text = "No models selected · pick at least one in section 01"
    else:
        meta_text = (
            f"Configuring {n} selected model{'' if n == 1 else 's'} · "
            f"pre-filled with recommended values"
        )

    st.markdown(
        f"""
        <div class="md-sec-head">
          <div class="md-sec-num">02</div>
          <div style="flex:1;">
            <div class="md-sec-title">Hyperparameter <em>tuning</em></div>
            <div class="md-sec-meta">{meta_text}</div>
          </div>
        </div>
        <div class="md-sec-tip">
          Cards appear here only for the algorithms you select above. Each row marked
          <strong style="color:var(--violet);">★</strong> is the recommended value ·
          expand for the full parameter list.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Empty state ──
    if not selected:
        st.markdown(
            """
            <div class="md-hp-empty">
              <div class="md-hp-empty-title">No algorithms selected</div>
              <div class="md-hp-empty-sub">
                Choose at least one model in section 01 to configure its hyperparameters.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Render one card per selected algorithm ──
    # Recommended algorithm always rendered first
    recommended = state.get("modeling_config", {}).get("recommended_algorithm")
    ordered = sorted(selected, key=lambda a: 0 if a == recommended else 1)

    for algo in ordered:
        try:
            schema = get_schema_for(algo, problem_type, state)
            render_card(schema, project_id)
        except Exception as e:
            st.warning(f"Could not load HP schema for {algo}: {e}")
            continue
```

---

## State writes

### When user types/selects in any HP field
Writes to `st.session_state["md_hp_values"][algo][param_name] = raw_string_value`.
**No type coercion at this point** — values stay as strings. Coercion happens at training-launch time (spec 07).

### When user changes search strategy dropdown
Writes to `st.session_state["md_hp_strategy"][algo] = strategy_key`.

### What gets committed to `state["modeling_config"]` (not in this spec — happens in spec 07)
When the user clicks Start Training (section 04), the orchestrator reads `md_hp_values` and `md_hp_strategy` from session_state, coerces types using each param's declared `type`, validates ranges, and writes:

```python
state["modeling_config"]["hyperparameters"][algo] = {
    "n_estimators": 500,           # int, coerced
    "learning_rate": 0.05,         # float, coerced
    # ...
}
state["modeling_config"]["search_strategy"][algo] = "bayesian"
```

---

## Edge cases to handle

| Case | Handling |
|---|---|
| User checks an algo with no template AND no registry entry | Render `_empty_schema` (just `random_state` field) with a non-blocking warning toast: "Limited HP options for this algorithm — defaults will be used." |
| Imbalance ratio is `None` in state (e.g. regression problem) | Skip the `class_weight` and `scale_pos_weight` overrides — leave defaults as-is. |
| User types nonsense (e.g. `"abc"` into `n_estimators`) | Don't validate during typing. At training launch, raise `ValueError` with a clear toast: "n_estimators must be int, got 'abc'." |
| User pastes a list-as-string (e.g. `"(128, 64)"` into `hidden_layer_sizes`) | The HP schema declares this field as `type: "str"` so we don't try to coerce. The training adapter (spec 07) uses `ast.literal_eval` for tuple/list params. |
| User opens 5+ HP cards | Performance is fine — Streamlit re-renders on every interaction anyway. No need for virtualization. |
| User unchecks the recommended algo in section 01 | Section 02 still works — just renders the remaining selected algos. The recommended one's card disappears like any other. |
| State has `selected_algorithms = ["XGBoost"]` but XGBoost is also `recommended_algorithm` | Render with the ★ Recommended pill. Card starts expanded. |
| User checks 22 algorithms | All 22 render. Performance acceptable for Streamlit. The training launch may rate-limit/queue them; that's spec 07's problem. |

---

## CSS additions

Add to `dashboard/components/shared_css.py` (extend `MODELING_CSS`, do not modify existing styles):

```css
/* HP empty-state */
.md-hp-empty {
  padding: 36px 28px; text-align: center;
  background: rgba(7,9,26,0.4);
  border: 1px dashed var(--border-default); border-radius: 12px;
  color: var(--text-muted);
}
[data-theme="light"] .md-hp-empty { background: rgba(255,255,255,0.55); }
.md-hp-empty-title {
  font-family: var(--font-display); font-size: 19px;
  color: var(--text-secondary); margin-bottom: 4px;
}
.md-hp-empty-sub { font-size: 12.5px; color: var(--text-muted); }

/* HP card head with inline pill */
.md-hp-card-head {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--font-display); font-size: 18px;
  color: var(--text-primary);
}
.md-hp-tag-inline {
  display: inline-block; padding: 2px 9px; margin-left: 4px;
  background: linear-gradient(135deg, rgba(139,92,246,0.16), rgba(34,211,238,0.16));
  border: 1px solid rgba(139,92,246,0.28); border-radius: 999px;
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.4px;
  color: var(--violet); text-transform: uppercase;
}

/* Recommended hint under a field */
.md-rec-hint {
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-faint); margin-top: 2px;
}
```

---

## Acceptance criteria

- [ ] Section 02 renders ONLY cards for algorithms checked in section 01
- [ ] Toggling a section 01 checkbox immediately adds/removes its card on the next rerun
- [ ] Empty state shows when nothing is checked
- [ ] Recommended algorithm's card is rendered first AND starts expanded
- [ ] All other cards start collapsed
- [ ] Each card shows top-4 params inline + "All hyperparameters · N more" expander
- [ ] ★ markers appear on recommended values (label + recommendation hint)
- [ ] Per-algorithm search-strategy dropdown defaults to "Bayesian optimization · 50 trials ★"
- [ ] For classifiers with imbalance ratio < 0.3, `class_weight` defaults to "balanced" and `scale_pos_weight` is auto-computed
- [ ] random_state fields default to `state["random_seed"]`
- [ ] Algorithms outside the 9 templates render via registry introspection (or fallback empty schema with a warning toast)
- [ ] User edits persist in `st.session_state["md_hp_values"][algo]` as raw strings
- [ ] Search strategy persists in `st.session_state["md_hp_strategy"][algo]`
- [ ] No modifications to `agents/`, `agents/tools/`, `core/`, or any non-dashboard module
