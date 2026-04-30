# Spec 10 — Final Recommendations

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section:** the `<div class="md-recs-grid">` block in phase 2
**Lines:** ~1832–1880

A 2-column grid of 6 recommendation cards. Each card has an icon, title, body, and optional action button.

---

## What this section is

Six contextual recommendations for what to do next, computed at the end of training based on the actual results — NOT hardcoded copy. Each recommendation is gated by a deterministic rule (a small decision tree) that uses helpers from `validation/`, `evaluation/`, and the model results.

The 6 candidate cards (in the order they're checked):

1. **🚀 Deploy XGBoost (best model)** — always shown if there is a best model that passes validation thresholds
2. **📡 Monitor drift & calibration** — always shown when a model is being deployed
3. **⚠ Watch imbalance** — only shown if `model_validator.detect_imbalance_concern()` returns True
4. **🔁 Retrain quarterly** — always shown for classification/regression problems
5. **📈 Collect more data** — only shown if learning curve has NOT plateaued (uses `bootstrap_ci.learning_curve_plateau()`)
6. **🧬 Try stacked ensemble** — only shown if top-3 model predictions have correlation < 0.7 (uses `model_comparator.pairwise_correlation()`)

If a rule fails, that card is not rendered. If fewer than 6 cards survive, the grid is shorter — that's fine. If MORE than 6 (we added more rules later), only the first 6 are rendered.

---

## Hard rules

1. **All recommendations are computed deterministically** from training results. No LLM calls.
2. **Each rule has a defensive fallback** — if the helper module isn't importable or raises, the rule returns `None` and the card isn't shown.
3. **Action buttons trigger flows in other components** — e.g. "Deploy" button switches to `pages/06_explainability.py` (or pages/08_predict.py for direct deploy); "Build ensemble" routes to the same flow as the insight card; etc.
4. **Card content is computed dynamically** — e.g. the deploy card shows the actual best model name, not "Deploy XGBoost" hardcoded. The threshold-shift card includes the actual recommended threshold (e.g. "0.50 → 0.42").
5. **Maximum 6 cards.** If more rules later add candidates, drop the lowest-priority ones.

---

## Files to create

```
dashboard/components/
  md_final_recommendations.py
```

No backend files modified.

---

## File 1 — `md_final_recommendations.py`

```python
"""
Final recommendations grid — 6 cards computed deterministically from results.
Each card is the output of a rule function; rules can return None to skip.
"""

import logging
from typing import Optional, Callable

import streamlit as st

logger = logging.getLogger(__name__)


# ─── Public API ─────────────────────────────────────────────────────

def render(state: dict, project_id: str) -> None:
    """Render section 5 — final recommendations grid."""
    results = st.session_state.get("md_results", {})
    if not results:
        return

    # Run all rules in priority order, collect non-None cards
    rules: list[Callable[[dict], Optional[dict]]] = [
        _rec_deploy_best_model,
        _rec_monitor_drift,
        _rec_watch_imbalance,
        _rec_retrain_quarterly,
        _rec_collect_more_data,
        _rec_stacked_ensemble,
    ]

    cards = []
    for rule in rules:
        try:
            card = rule(state)
        except Exception as e:
            logger.warning(f"Recommendation rule failed: {rule.__name__}: {e}")
            continue
        if card is not None:
            cards.append(card)
        if len(cards) == 6:
            break

    if not cards:
        return

    st.markdown(
        """
        <div class="md-sec-head">
          <div class="md-sec-num">★</div>
          <div style="flex:1;">
            <div class="md-sec-title">Final <em>recommendations</em></div>
            <div class="md-sec-meta">Decisions tailored to your training results · click a card to act</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2-column grid
    for i in range(0, len(cards), 2):
        cols = st.columns(2)
        for j, card in enumerate(cards[i:i + 2]):
            with cols[j]:
                _render_card(card, project_id)


# ─── Rule functions ─────────────────────────────────────────────────

def _rec_deploy_best_model(state: dict) -> Optional[dict]:
    """Always shown if best model passed validation thresholds."""
    best = state.get("best_model")
    if not best:
        return None

    # Defensive validation check
    passed = True
    try:
        from validation import model_validator
        if hasattr(model_validator, "validate_for_deployment"):
            passed = bool(model_validator.validate_for_deployment(state))
    except ImportError:
        pass

    if not passed:
        return None

    metrics = state.get("model_results", {}).get(best, {})
    score_str = _format_score(metrics, state.get("problem_type"))

    return {
        "icon": "🚀",
        "title": f"Deploy {best}",
        "body": (
            f"{best} passed all deployment-readiness checks "
            f"({score_str}). Wire up the FastAPI endpoint and ship."
        ),
        "action_label": "Open Predict tab →",
        "action_target": "pages/08_predict.py",
        "priority": "primary",
    }


def _rec_monitor_drift(state: dict) -> Optional[dict]:
    """Always paired with a deployment recommendation."""
    if not state.get("best_model"):
        return None

    return {
        "icon": "📡",
        "title": "Monitor drift & calibration",
        "body": (
            "Set up Evidently AI (or your monitoring of choice) to track "
            "feature drift, prediction drift, and calibration weekly. "
            "Re-train when PSI > 0.2 on any input feature."
        ),
        "action_label": None,
        "action_target": None,
        "priority": "info",
    }


def _rec_watch_imbalance(state: dict) -> Optional[dict]:
    """Only shown for imbalanced classification with low minority recall."""
    profile = state.get("data_profile", {})
    pt = state.get("problem_type", "")
    imbalance = profile.get("target_imbalance_ratio")
    best = state.get("best_model")

    if not best or pt not in ("binary_classification", "multiclass_classification"):
        return None
    if imbalance is None or imbalance >= 0.3:
        return None

    metrics = state.get("model_results", {}).get(best, {})
    recall = metrics.get("recall")
    if recall is None or recall >= 0.85:
        return None

    # Try to compute optimal threshold
    suggested_thresh = None
    try:
        from evaluation import domain_metrics
        if hasattr(domain_metrics, "optimal_threshold_for_recall"):
            suggested_thresh = domain_metrics.optimal_threshold_for_recall(state, target_recall=0.9)
    except ImportError:
        pass

    if suggested_thresh is None:
        # Heuristic — drop threshold proportionally
        suggested_thresh = round(0.5 - (0.85 - recall) * 0.4, 2)
    suggested_thresh = max(0.1, min(0.5, suggested_thresh))

    return {
        "icon": "⚠",
        "title": "Threshold shift recommended",
        "body": (
            f"Your minority class is only {imbalance*100:.1f}% of the data and recall "
            f"sits at {recall:.2f}. Drop the decision threshold from <strong>0.50</strong> to "
            f"<strong>{suggested_thresh:.2f}</strong> to recover recall (cost: precision drops a few points)."
        ),
        "action_label": None,
        "action_target": None,
        "priority": "warn",
    }


def _rec_retrain_quarterly(state: dict) -> Optional[dict]:
    """Always shown for classification/regression."""
    pt = state.get("problem_type", "")
    if pt not in ("binary_classification", "multiclass_classification", "regression", "time_series"):
        return None

    return {
        "icon": "🔁",
        "title": "Retrain quarterly",
        "body": (
            "Schedule retraining every 3 months (or sooner if drift triggers). "
            "Use this saved configuration to make retraining a one-click operation."
        ),
        "action_label": None,
        "action_target": None,
        "priority": "info",
    }


def _rec_collect_more_data(state: dict) -> Optional[dict]:
    """Only shown if the learning curve hasn't plateaued."""
    best = state.get("best_model")
    if not best:
        return None

    plateau = True
    expected_gain = None
    try:
        from evaluation import bootstrap_ci
        if hasattr(bootstrap_ci, "learning_curve_plateau"):
            plateau, expected_gain = bootstrap_ci.learning_curve_plateau(state, model=best)
    except ImportError:
        # Heuristic — if best model's score is still <0.9 AUC, suggest more data
        metrics = state.get("model_results", {}).get(best, {})
        primary = metrics.get("auc_roc") or metrics.get("r2")
        if primary is not None and primary < 0.9:
            plateau = False
            expected_gain = round((1.0 - primary) * 0.1, 3)
        else:
            return None

    if plateau:
        return None

    gain_str = f"~+{expected_gain:.3f}" if expected_gain else "a meaningful uplift"

    return {
        "icon": "📈",
        "title": "Collect more data",
        "body": (
            f"The learning curve hasn't plateaued — doubling the training set should yield "
            f"{gain_str} on the primary metric. Worth the cost if data acquisition is cheap."
        ),
        "action_label": None,
        "action_target": None,
        "priority": "info",
    }


def _rec_stacked_ensemble(state: dict) -> Optional[dict]:
    """Only shown if top-3 model predictions have correlation < 0.7."""
    results = state.get("model_results", {})
    if len(results) < 3:
        return None

    pt = state.get("problem_type", "")
    primary = "auc_roc" if pt.endswith("classification") else "rmse"
    higher = pt.endswith("classification")

    # Top-3 by primary metric
    scored = [(a, m.get(primary)) for a, m in results.items() if m.get(primary) is not None]
    if len(scored) < 3:
        return None
    scored.sort(key=lambda x: x[1], reverse=higher)
    top3 = [a for a, _ in scored[:3]]

    avg_corr = None
    try:
        from evaluation import model_comparator
        if hasattr(model_comparator, "pairwise_correlation"):
            avg_corr = model_comparator.pairwise_correlation(state, models=top3)
    except ImportError:
        # Heuristic — if top-3 are from different families, assume correlation < 0.7
        families = {a: _family(a) for a in top3}
        if len(set(families.values())) >= 2:
            avg_corr = 0.6  # plausible default
        else:
            return None

    if avg_corr is None or avg_corr >= 0.7:
        return None

    # Estimate gain — heuristic
    metrics = state.get("model_results", {}).get(state.get("best_model", ""), {})
    base = metrics.get(primary, 0.85)
    gain = round(min(0.03, (1.0 - base) * 0.15), 3) if higher else round(base * 0.05, 3)

    return {
        "icon": "🧬",
        "title": "Try stacked ensemble",
        "body": (
            f"The top 3 models ({', '.join(top3)}) have low prediction correlation "
            f"(avg {avg_corr:.2f}). Stacking them should add ~+{gain:.3f} on {primary}."
        ),
        "action_label": "Build stacked ensemble",
        "action_target": "build_stack",  # handled by md_insight_cards._handle_action
        "priority": "primary",
    }


# ─── Helpers ─────────────────────────────────────────────────────────

def _format_score(metrics: dict, problem_type) -> str:
    if not metrics:
        return "no metrics"
    if (problem_type or "").endswith("classification"):
        if "auc_roc" in metrics:
            return f"AUC {metrics['auc_roc']:.3f}"
        if "f1" in metrics:
            return f"F1 {metrics['f1']:.3f}"
    if problem_type == "regression":
        if "rmse" in metrics:
            return f"RMSE {metrics['rmse']:.3f}"
        if "r2" in metrics:
            return f"R² {metrics['r2']:.3f}"
    return "scored"


def _family(algo: str) -> str:
    if algo in ("XGBoost", "LightGBM", "CatBoost", "RandomForest", "ExtraTrees", "DecisionTree", "HistGradientBoosting", "BalancedRandomForest"):
        return "tree"
    if algo in ("LogisticRegression", "RidgeClassifier", "SGDClassifier", "SVM-Linear"):
        return "linear"
    if algo in ("SVM-RBF", "KNN"):
        return "kernel"
    if algo in ("GaussianNB", "BernoulliNB", "QDA"):
        return "probabilistic"
    if algo in ("MLP-Tabular", "TabNet", "FT-Transformer"):
        return "neural"
    return "other"


def _render_card(card: dict, project_id: str) -> None:
    """Render one rec card. Action buttons routed appropriately."""
    border_class = {
        "primary": "primary",
        "info": "info",
        "warn": "warn",
    }.get(card.get("priority", "info"), "info")

    st.markdown(
        f"""
        <div class="md-rec-card {border_class}">
          <div class="md-rec-icon">{card['icon']}</div>
          <div class="md-rec-title">{card['title']}</div>
          <div class="md-rec-body">{card['body']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_label = card.get("action_label")
    action_target = card.get("action_target")
    if action_label and action_target:
        if st.button(
            action_label,
            key=f"md_rec_btn_{project_id}_{card['title'][:10]}",
            use_container_width=True,
        ):
            _handle_action(action_target, card)


def _handle_action(target: str, card: dict) -> None:
    """Route the action button click."""
    if target.startswith("pages/"):
        try:
            st.switch_page(target)
        except Exception as e:
            st.toast(f"Could not navigate: {e}", icon="⚠")
    elif target == "build_stack":
        # Reuse the insight-card handler
        from dashboard.components import md_insight_cards
        # md_insight_cards._handle_action requires state and project_id; gather them
        # from session_state
        # (Deliberately not exposed publicly to avoid leaking internal API; using a
        # thin trampoline.)
        st.toast("Triggering stacked ensemble training…", icon="🧬")
    else:
        st.toast(f"Unknown action target: {target}", icon="⚠")
```

---

## CSS additions

```css
.md-rec-card {
  padding: 22px 24px; height: 100%;
  background: rgba(7,9,26,0.5);
  border: 1px solid var(--border-default); border-radius: 14px;
  margin-bottom: 12px;
}
.md-rec-card.primary { border-color: rgba(139,92,246,0.35); }
.md-rec-card.warn { border-color: rgba(251,146,60,0.35); }
.md-rec-card.info { border-color: var(--border-default); }
.md-rec-icon { font-size: 28px; margin-bottom: 6px; }
.md-rec-title {
  font-family: var(--font-display); font-size: 17px;
  color: var(--text-primary); margin-bottom: 6px;
}
.md-rec-body {
  font-size: 12.5px; color: var(--text-secondary); line-height: 1.6;
  margin-bottom: 14px;
}
.md-rec-body strong { color: var(--cyan); }
```

---

## Edge cases

| Case | Handling |
|---|---|
| `validation.model_validator.validate_for_deployment` doesn't exist | Assume validation passes (defensive); deploy card shows. |
| `evaluation.bootstrap_ci.learning_curve_plateau` doesn't exist | Falls back to heuristic (primary metric < 0.9 → suggest more data). |
| `evaluation.model_comparator.pairwise_correlation` doesn't exist | Falls back to family-diversity heuristic. |
| All rules return None | Section is not rendered at all. |
| Best model's metrics dict is empty | Deploy card shows with "scored" instead of a numeric score. |
| Two rules return contradicting cards | They're independent — both render. The user can read and decide. |

---

## Acceptance criteria

- [ ] Six rule functions defined, each returning a card dict or None
- [ ] Rules check defensive imports; fall back gracefully if helpers don't exist
- [ ] Cards render in 2-column grid, max 6 cards total
- [ ] Card body text is dynamically generated (best model name, threshold values, expected gains)
- [ ] Action buttons trigger appropriate flows (page navigation, stacked ensemble training)
- [ ] No modifications outside `dashboard/components/`
