# Spec 09 — Diagnostic Charts Panel (Spotify-style)

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section:** the `<div class="md-charts-panel">` block in phase 2
**Lines:** ~1729–1830

A two-column layout: 240px sidebar with 16+ chart links grouped by category, main panel that swaps to show the selected chart. Below the chart, a captioned "what this chart tells you" box.

---

## What this section is

A dense diagnostic-charts explorer. Three groups of charts:

### Group 1 — Training (6 charts)
Diagnostics about the *search and fit process*, per algorithm:
1. **Loss vs trial** — line chart, x: trial #, y: loss
2. **AUC vs trial** — line chart (or RMSE if regression), x: trial #, y: validation score
3. **Learning curve** — train vs validation score over training-set fraction, both ±1σ band
4. **Per-fold variance** — box plot per fold, validation score
5. **HP importance** — horizontal bar, per HP, importance from search algo (Bayesian only)
6. **Training time** — horizontal bar, per algo, total training time

### Group 2 — Testing (7 charts, classification)
Diagnostics about the *trained model on held-out data*:
1. **ROC curve** — TPR vs FPR with AUC label and diagonal baseline
2. **Precision-Recall curve** — Recall vs Precision with AP label
3. **Confusion matrix** — heatmap (counts + percentages)
4. **Calibration curve** — predicted prob vs observed frequency, diagonal baseline
5. **Lift / Cumulative gains** — lift over baseline by decile
6. **Threshold analysis** — Precision/Recall/F1 vs threshold (one line each)
7. **Probability distribution** — predicted probability histogram, split by true class

For regression, swap to:
1. **Predicted vs Actual** — scatter with y=x line
2. **Residuals plot** — residual vs predicted, with horizontal zero line
3. **Residual distribution** — histogram with normal-fit overlay
4. **Q-Q plot** — quantile-quantile of residuals
5. **Error by feature** — abs error vs top-3 features
6. **Calibration intervals** — 95% prediction interval coverage by predicted decile
7. **Per-row error table** (top 10 worst predictions) — table view

### Group 3 — Comparison (5 charts)
Cross-algorithm comparisons:
1. **DNA radar — all models** — same SVG as `md_dna_radar.py` but with all algos overlaid (no focus)
2. **Speed vs accuracy** — same as Pareto (cross-link)
3. **Metric comparison** — grouped bar chart, primary + secondary metrics across algos
4. **Prediction agreement** — pairwise heatmap of correlation between model predictions
5. **Statistical test (paired)** — paired t-test or McNemar across CV folds

Total: 18 charts (6 + 7 + 5). Click on any sidebar item → main panel swaps to that chart.

---

## Hard rules

1. **Each chart is its own file** at `dashboard/components/md_charts/md_chart_<key>.py` with signature:
   ```python
   def render(completed_models: list[str], selected_model: str, problem_type: str, state: dict) -> tuple[plotly.graph_objects.Figure | None, str]:
       """
       Returns: (figure, caption) — caption is plain-English explanation of what the chart shows.
       Returns (None, "Data not yet available.") if data isn't there yet.
       """
   ```
2. **Most charts wrap existing `agents/tools/viz_tools.py` functions** (25+ Plotly generators already exist). The chart module's job is to *select the right viz_tools call and pass MLflow data into it*.
3. **Calibration uses `explainability/calibration.py`** — that module has a `calibration_curve(y_true, y_proba, n_bins)` function.
4. **Per-row error table** uses `evaluation/domain_metrics.py` to surface high-error predictions.
5. **All chart data comes from MLflow run artifacts** — predictions, probabilities, feature values are logged by the modeling agent. Read via `md_mlflow_reader.get_artifact_path()` then `mlflow.artifacts.download_artifacts()`.
6. **Cache aggressively** — `@st.cache_data` on each chart's data load. Key by `(run_id, chart_key)`.
7. **Defensive fallback** — if a viz_tool function doesn't exist or raises, render a stub Plotly figure showing "Chart unavailable" with the error message.
8. **Renderer routes by chart_key** — a single dispatch function `md_chart_renderer.render(chart_key, ...)` that imports the right module and calls its `render()`. This keeps the panel module thin.
9. **Sidebar selection persisted** in session_state — survives reruns.

---

## Files to create

```
dashboard/components/
  md_charts_panel.py                # The 2-col panel container
  md_chart_renderer.py              # Routes chart_key → md_chart_<key>.render()
  md_charts/
    __init__.py
    # ── Training group ──
    md_chart_loss_vs_trial.py
    md_chart_metric_vs_trial.py
    md_chart_learning_curve.py
    md_chart_per_fold_variance.py
    md_chart_hp_importance.py
    md_chart_training_time.py
    # ── Testing group (classification) ──
    md_chart_roc.py
    md_chart_pr.py
    md_chart_confusion_matrix.py
    md_chart_calibration.py
    md_chart_lift_gains.py
    md_chart_threshold_analysis.py
    md_chart_proba_distribution.py
    # ── Testing group (regression) ──
    md_chart_pred_vs_actual.py
    md_chart_residuals.py
    md_chart_residual_dist.py
    md_chart_qq_plot.py
    md_chart_error_by_feature.py
    md_chart_calibration_intervals.py
    md_chart_top_errors.py
    # ── Comparison group ──
    md_chart_dna_radar_all.py
    md_chart_speed_accuracy.py        # Pareto (re-uses md_pareto_frontier internals)
    md_chart_metric_comparison.py
    md_chart_prediction_agreement.py
    md_chart_paired_test.py
```

No backend files modified.

---

## File 1 — `md_charts_panel.py`

```python
"""
Two-column container — sidebar (240px) with grouped chart links + main panel.
"""

import streamlit as st
from dashboard.components import md_chart_renderer


CHARTS_SELECTED_KEY = "md_charts_selected_chart"
CHARTS_SELECTED_MODEL = "md_charts_selected_model"


def render(state: dict, project_id: str) -> None:
    results = st.session_state.get("md_results", {})
    completed = [a for a, info in results.items() if info.get("status") == "done"]
    if not completed:
        st.markdown(
            """<div class="md-empty-card">Charts will appear once at least one model finishes training.</div>""",
            unsafe_allow_html=True,
        )
        return

    pt = state.get("problem_type", "binary_classification")
    is_class = pt in ("binary_classification", "multiclass_classification")

    if CHARTS_SELECTED_KEY not in st.session_state:
        st.session_state[CHARTS_SELECTED_KEY] = "roc" if is_class else "pred_vs_actual"
    if CHARTS_SELECTED_MODEL not in st.session_state:
        st.session_state[CHARTS_SELECTED_MODEL] = state.get("best_model") or completed[0]

    # Header
    st.markdown(
        """
        <div class="md-sec-head">
          <div class="md-sec-num">📊</div>
          <div style="flex:1;">
            <div class="md-sec-title">Diagnostic <em>charts</em></div>
            <div class="md-sec-meta">Click any chart in the sidebar · select a model to focus</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    panel_cols = st.columns([0.28, 0.72])

    # ── Sidebar ──
    with panel_cols[0]:
        st.markdown("<div class='md-charts-sidebar'>", unsafe_allow_html=True)
        # Model focus dropdown
        choices = ["All models"] + completed
        try:
            idx = choices.index(st.session_state[CHARTS_SELECTED_MODEL])
        except ValueError:
            idx = 1
        chosen = st.selectbox(
            "Focus model",
            options=choices,
            index=idx,
            key=f"md_charts_model_{project_id}",
        )
        st.session_state[CHARTS_SELECTED_MODEL] = chosen

        # Group: Training
        st.markdown("<div class='md-charts-group-title'>Training</div>", unsafe_allow_html=True)
        for k, label in TRAINING_CHARTS:
            _link_button(k, label, project_id)

        # Group: Testing (classification or regression set)
        st.markdown("<div class='md-charts-group-title'>Testing</div>", unsafe_allow_html=True)
        chart_set = TESTING_CLASSIFICATION if is_class else TESTING_REGRESSION
        for k, label in chart_set:
            _link_button(k, label, project_id)

        # Group: Comparison
        st.markdown("<div class='md-charts-group-title'>Comparison</div>", unsafe_allow_html=True)
        for k, label in COMPARISON_CHARTS:
            _link_button(k, label, project_id)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Main panel ──
    with panel_cols[1]:
        chart_key = st.session_state[CHARTS_SELECTED_KEY]
        selected_model = st.session_state[CHARTS_SELECTED_MODEL]
        fig, caption = md_chart_renderer.render(
            chart_key=chart_key,
            completed_models=completed,
            selected_model=selected_model,
            problem_type=pt,
            state=state,
        )
        if fig is None:
            st.markdown(
                f"""<div class="md-charts-empty">{caption or "Data not yet available."}</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.plotly_chart(fig, use_container_width=True)
            if caption:
                st.markdown(
                    f"""<div class="md-charts-caption">{_escape(caption)}</div>""",
                    unsafe_allow_html=True,
                )


# ─── chart catalog ────────────────────────────────────────

TRAINING_CHARTS = [
    ("loss_vs_trial",       "Loss vs trial"),
    ("metric_vs_trial",     "AUC vs trial"),
    ("learning_curve",      "Learning curve"),
    ("per_fold_variance",   "Per-fold variance"),
    ("hp_importance",       "HP importance"),
    ("training_time",       "Training time"),
]

TESTING_CLASSIFICATION = [
    ("roc",                 "ROC curve"),
    ("pr",                  "PR curve"),
    ("confusion_matrix",    "Confusion matrix"),
    ("calibration",         "Calibration curve"),
    ("lift_gains",          "Lift / Gains"),
    ("threshold_analysis",  "Threshold analysis"),
    ("proba_distribution",  "Probability distribution"),
]

TESTING_REGRESSION = [
    ("pred_vs_actual",      "Predicted vs Actual"),
    ("residuals",           "Residuals plot"),
    ("residual_dist",       "Residual distribution"),
    ("qq_plot",             "Q-Q plot"),
    ("error_by_feature",    "Error by feature"),
    ("calibration_intervals", "Calibration intervals"),
    ("top_errors",          "Top errors (table)"),
]

COMPARISON_CHARTS = [
    ("dna_radar_all",       "DNA radar — all"),
    ("speed_accuracy",      "Speed vs accuracy"),
    ("metric_comparison",   "Metric comparison"),
    ("prediction_agreement","Prediction agreement"),
    ("paired_test",         "Statistical test"),
]


def _link_button(key: str, label: str, project_id: str):
    is_active = (st.session_state.get(CHARTS_SELECTED_KEY) == key)
    if st.button(
        label,
        key=f"md_chart_link_{project_id}_{key}",
        type=("primary" if is_active else "secondary"),
        use_container_width=True,
    ):
        st.session_state[CHARTS_SELECTED_KEY] = key
        st.rerun()


def _escape(s: str) -> str:
    return (s or "").replace("<", "&lt;").replace(">", "&gt;")
```

---

## File 2 — `md_chart_renderer.py`

```python
"""
Single dispatch — chart_key → import the right module and call its render().
"""

import importlib
import logging
from typing import Any

import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def render(chart_key: str, completed_models: list[str], selected_model: str,
           problem_type: str, state: dict) -> tuple[Any, str]:
    """Return (plotly figure, caption) or (None, error_message)."""
    module_path = f"dashboard.components.md_charts.md_chart_{chart_key}"
    try:
        mod = importlib.import_module(module_path)
        fig, caption = mod.render(completed_models, selected_model, problem_type, state)
        return fig, caption
    except ModuleNotFoundError:
        return _stub("Chart not yet implemented.")
    except Exception as e:
        logger.exception(f"Chart {chart_key} render failed")
        return _stub(f"Chart error: {type(e).__name__}: {e}")


def _stub(message: str):
    return None, message
```

---

## File 3 — Per-chart modules (representative examples)

Each chart module is small (50–100 lines). Here are 3 representative examples; the rest follow the same pattern.

### `md_charts/md_chart_roc.py`

```python
"""
ROC curve — TPR vs FPR with AUC label.
Wraps agents/tools/viz_tools.create_roc_curve() if present.
"""

import logging
import plotly.graph_objects as go
import streamlit as st
from dashboard.components.md_mlflow_reader import get_run_metrics, get_artifact_path

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, hash_funcs={dict: lambda d: hash(frozenset(d.items()) if d else 0)})
def _load_roc_points(run_id: str):
    """Load fpr/tpr arrays from the MLflow artifact directory."""
    try:
        import mlflow
        import json
        artifact_uri = get_artifact_path(run_id, "evaluation/roc_data.json")
        local = mlflow.artifacts.download_artifacts(artifact_uri)
        with open(local) as f:
            data = json.load(f)
        return data.get("fpr", []), data.get("tpr", []), data.get("auc")
    except Exception as e:
        logger.warning(f"_load_roc_points({run_id}) failed: {e}")
        return None, None, None


def render(completed_models, selected_model, problem_type, state):
    if problem_type not in ("binary_classification", "multiclass_classification"):
        return None, "ROC is only meaningful for classification."

    results = st.session_state.get("md_results", {})

    fig = go.Figure()
    # Diagonal baseline
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                              line=dict(color="rgba(160,160,170,0.4)", dash="dash"),
                              name="random", showlegend=True))

    # Each model gets its own line; selected_model is bolded
    for algo in completed_models:
        info = results.get(algo, {})
        run_id = info.get("run_id")
        if not run_id:
            continue
        fpr, tpr, auc = _load_roc_points(run_id)
        if fpr is None or tpr is None:
            continue
        is_focus = (algo == selected_model) or (selected_model == "All models")
        line_props = dict(width=3 if is_focus else 1.6,
                          color="#ec4899" if algo == selected_model else None)
        label = f"{algo}" + (f" · AUC {auc:.3f}" if auc is not None else "")
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=label, line=line_props))

    fig.update_layout(
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,9,26,0.4)",
        height=420,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=40, r=20, t=20, b=80),
    )

    caption = (
        f"Diagonal is the random-classifier baseline. The closer the curve hugs the upper-left, "
        f"the better the model. {selected_model} is the highlighted curve."
    )
    return fig, caption
```

### `md_charts/md_chart_confusion_matrix.py`

```python
"""
Confusion matrix heatmap — counts and percentages.
"""

import logging
import plotly.graph_objects as go
import streamlit as st
from dashboard.components.md_mlflow_reader import get_run_metrics, get_artifact_path

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def _load_cm(run_id: str):
    try:
        import mlflow
        import json
        local = mlflow.artifacts.download_artifacts(
            get_artifact_path(run_id, "evaluation/confusion_matrix.json")
        )
        with open(local) as f:
            d = json.load(f)
        return d.get("matrix"), d.get("classes", [])
    except Exception as e:
        logger.warning(f"_load_cm({run_id}) failed: {e}")
        return None, None


def render(completed_models, selected_model, problem_type, state):
    if problem_type not in ("binary_classification", "multiclass_classification"):
        return None, "Confusion matrix only applies to classification."

    if selected_model == "All models" or selected_model not in completed_models:
        return None, "Pick a single model in the sidebar to see its confusion matrix."

    results = st.session_state.get("md_results", {})
    run_id = results.get(selected_model, {}).get("run_id")
    if not run_id:
        return None, "No MLflow run for this model."

    matrix, classes = _load_cm(run_id)
    if matrix is None:
        return None, "Confusion matrix data not available for this run."

    # Build label text combining count + percent
    total = sum(sum(row) for row in matrix) or 1
    text = [
        [f"{val}<br>{val/total*100:.1f}%" for val in row]
        for row in matrix
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[f"Predicted {c}" for c in classes],
        y=[f"Actual {c}" for c in classes],
        text=text,
        texttemplate="%{text}",
        colorscale=[[0, "rgba(7,9,26,0.4)"], [1, "rgba(236,72,153,0.7)"]],
        showscale=False,
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=80, r=20, t=20, b=60),
    )
    caption = (
        f"Diagonal = correct predictions. Off-diagonal = mistakes. "
        f"Brighter cells indicate more samples in that bucket."
    )
    return fig, caption
```

### `md_charts/md_chart_calibration.py`

```python
"""
Calibration curve — predicted probability vs observed frequency.
Uses explainability/calibration.py.
"""

import logging
import plotly.graph_objects as go
import streamlit as st
from dashboard.components.md_mlflow_reader import get_artifact_path

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def _load_calibration(run_id: str, n_bins: int = 10):
    try:
        from explainability import calibration
        import mlflow
        import json
        local = mlflow.artifacts.download_artifacts(
            get_artifact_path(run_id, "evaluation/probabilities.json")
        )
        with open(local) as f:
            d = json.load(f)
        y_true = d.get("y_true", [])
        y_proba = d.get("y_proba", [])
        if not y_true or not y_proba:
            return None
        prob_true, prob_pred = calibration.calibration_curve(y_true, y_proba, n_bins=n_bins)
        return list(prob_true), list(prob_pred)
    except Exception as e:
        logger.warning(f"_load_calibration({run_id}) failed: {e}")
        return None


def render(completed_models, selected_model, problem_type, state):
    if problem_type not in ("binary_classification",):
        return None, "Calibration curves apply to binary classification."

    results = st.session_state.get("md_results", {})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                              line=dict(color="rgba(160,160,170,0.4)", dash="dash"),
                              name="perfect", showlegend=True))

    for algo in completed_models:
        run_id = results.get(algo, {}).get("run_id")
        if not run_id:
            continue
        out = _load_calibration(run_id)
        if out is None:
            continue
        prob_true, prob_pred = out
        is_focus = (algo == selected_model)
        fig.add_trace(go.Scatter(
            x=prob_pred, y=prob_true, mode="lines+markers",
            name=algo,
            line=dict(width=3 if is_focus else 1.5,
                      color="#ec4899" if is_focus else None),
        ))

    fig.update_layout(
        xaxis_title="Mean predicted probability",
        yaxis_title="Observed frequency of positive class",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,9,26,0.4)",
        height=420,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=40, r=20, t=20, b=80),
    )
    caption = (
        "If the curve hugs the diagonal, the model's predicted probabilities are well-calibrated "
        "(a prediction of 0.7 actually corresponds to ~70% of cases being positive). "
        "Above the line means under-confident; below means over-confident."
    )
    return fig, caption
```

### Pattern for the remaining charts

Each follows the same template:

```python
import plotly.graph_objects as go
import streamlit as st
from dashboard.components.md_mlflow_reader import get_artifact_path

@st.cache_data(show_spinner=False)
def _load(run_id: str):
    """Pull the raw data from MLflow artifacts."""
    # ... mlflow.artifacts.download + json.load
    # Return data structures needed by the chart.

def render(completed_models, selected_model, problem_type, state):
    """Return (fig, caption)."""
    # 1. Sanity-check problem_type
    # 2. For comparison charts: iterate all completed_models
    # 3. For per-model charts: just selected_model
    # 4. Wrap viz_tools.<existing> if applicable
    # 5. Return Plotly Figure with cosmic dark theme
```

**Charts that wrap existing `viz_tools` functions** (search for these in `agents/tools/viz_tools.py`):

| Chart | viz_tools function (if exists) |
|---|---|
| pr | `create_pr_curve` |
| confusion_matrix | `create_confusion_matrix` |
| residuals | `create_residual_plot` |
| pred_vs_actual | `create_pred_vs_actual` |
| qq_plot | `create_qq_plot` |
| metric_comparison | `create_metric_comparison_bars` |

If any function doesn't exist in viz_tools, build the chart from scratch using `plotly.graph_objects` directly — don't add new functions to `viz_tools.py`.

**Charts that need helpers from other modules:**

| Chart | Module |
|---|---|
| calibration | `explainability/calibration.py` |
| top_errors | `evaluation/domain_metrics.py` |
| paired_test | `evaluation/model_comparator.py` |
| learning_curve | `evaluation/bootstrap_ci.py` |

**Charts that compute on the fly (no external module needed):**
- loss_vs_trial, metric_vs_trial — read MLflow run history
- per_fold_variance — read MLflow tags `cv_fold_*_score`
- training_time — read MLflow run duration
- prediction_agreement — pairwise correlation of `y_proba` arrays
- speed_accuracy — exact reuse of `md_pareto_frontier` logic
- dna_radar_all — exact reuse of `md_dna_radar` logic but with no focus

---

## CSS additions

```css
.md-charts-sidebar {
  padding: 14px;
  background: rgba(7,9,26,0.5);
  border: 1px solid var(--border-default); border-radius: 12px;
  max-height: 720px; overflow-y: auto;
}
.md-charts-group-title {
  font-family: var(--font-mono); font-size: 10.5px;
  text-transform: uppercase; letter-spacing: 0.7px;
  color: var(--text-muted); margin: 14px 0 6px;
  padding-bottom: 4px; border-bottom: 1px dashed var(--border-default);
}
.md-charts-group-title:first-child { margin-top: 6px; }
.md-charts-empty {
  padding: 64px 24px; text-align: center;
  background: rgba(7,9,26,0.4);
  border: 1px dashed var(--border-default); border-radius: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono); font-size: 12.5px;
}
.md-charts-caption {
  margin-top: 12px; padding: 12px 16px;
  background: rgba(34,211,238,0.04);
  border-left: 3px solid var(--cyan); border-radius: 0 8px 8px 0;
  font-size: 12.5px; color: var(--text-secondary);
  line-height: 1.55;
}
.md-empty-card {
  padding: 28px; text-align: center;
  background: rgba(7,9,26,0.4);
  border: 1px dashed var(--border-default); border-radius: 12px;
  color: var(--text-muted); margin-bottom: 24px;
}
```

---

## Edge cases

| Case | Handling |
|---|---|
| User selects "All models" but the chart only supports one model (e.g. confusion matrix) | Caption shows: "Pick a single model in the sidebar to see its confusion matrix." Returns `(None, ...)`. |
| MLflow artifact `roc_data.json` doesn't exist (modeling agent didn't log it) | Chart shows empty-state with caption: "ROC data not logged for this run — re-run the model with `log_evaluation_artifacts=True`." |
| User clicks a regression chart on a classification problem | Chart returns `(None, "Chart only applies to <problem_type> problems.")`. |
| Chart module's `render()` raises | Caught in `md_chart_renderer.render()` — returns `(None, "Chart error: ...")`. |
| `plotly.cache_data` invalidates between rerenders during training | Acceptable — re-load is cheap. |
| Selected model gets removed from `completed_models` (shouldn't happen but defensive) | Reset selection to first available model. |
| `viz_tools.create_<chart>` exists but has different signature | Wrap with try/except in the chart module; fall back to building the chart directly with plotly. |

---

## Acceptance criteria

- [ ] Sidebar shows 3 grouped sections: Training (6), Testing (7 — set varies by problem type), Comparison (5)
- [ ] Clicking a sidebar item swaps the main panel chart
- [ ] Selected chart and selected model both persist across reruns via session_state
- [ ] Each chart has a captioned "what this tells you" box below
- [ ] Charts render via Plotly with cosmic dark theme (`paper_bgcolor` transparent, `plot_bgcolor` `rgba(7,9,26,0.4)`)
- [ ] Selected model line is highlighted in pink/`#ec4899`
- [ ] Charts cached by run_id — fast switching
- [ ] Chart that lacks data shows empty state with explanation
- [ ] Comparison charts iterate ALL completed models
- [ ] No modifications outside `dashboard/components/`
