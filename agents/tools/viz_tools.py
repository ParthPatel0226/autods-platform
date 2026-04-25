"""Visualization tools using Plotly. Each function returns a structured dict with figure + metadata."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _default_layout(title: str, x_label: str = "", y_label: str = "") -> dict:
    """Return a reusable Plotly layout dict with consistent styling."""
    layout = {
        "template": "plotly_white",
        "title": {"text": title, "x": 0.5, "font": {"size": 18}},
        "font": {"family": "Inter, Arial, sans-serif", "size": 12},
        "margin": {"l": 60, "r": 30, "t": 60, "b": 50},
        "hoverlabel": {"font_size": 12},
    }
    if x_label:
        layout["xaxis"] = {"title": x_label}
    if y_label:
        layout["yaxis"] = {"title": y_label}
    return layout


def _make_result(fig: go.Figure, title: str, description: str, insights: list[str]) -> dict:
    """Standardise return dict."""
    return {
        "figure": fig,
        "title": title,
        "description": description,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# Distribution plots
# ---------------------------------------------------------------------------

def histogram(df: pd.DataFrame, column: str, bins: int = 30, color_by: str | None = None) -> dict:
    """Create an interactive histogram for a numeric column."""
    fig = px.histogram(df, x=column, nbins=bins, color=color_by, barmode="overlay")
    fig.update_layout(**_default_layout(f"Distribution of {column}", column, "Count"))

    # Auto insights
    insights: list[str] = []
    s = df[column].dropna()
    skew = float(s.skew())
    if abs(skew) > 1:
        direction = "right" if skew > 0 else "left"
        insights.append(f"Distribution is {direction}-skewed (skewness={skew:.2f})")
    else:
        insights.append(f"Distribution is approximately symmetric (skewness={skew:.2f})")
    insights.append(f"Range: {s.min():.4g} to {s.max():.4g}, median={s.median():.4g}")

    return _make_result(fig, f"Histogram of {column}", f"Distribution of {column} with {bins} bins", insights)


def box_plot(df: pd.DataFrame, column: str, group_by: str | None = None) -> dict:
    """Create a box plot showing distribution summary statistics."""
    fig = px.box(df, y=column, x=group_by, points="outliers")
    title = f"Box Plot of {column}" + (f" by {group_by}" if group_by else "")
    fig.update_layout(**_default_layout(title, group_by or "", column))

    insights: list[str] = []
    s = df[column].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    n_outliers = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
    insights.append(f"IQR: {iqr:.4g} (Q1={q1:.4g}, Q3={q3:.4g})")
    if n_outliers > 0:
        insights.append(f"{n_outliers} outliers detected ({n_outliers/len(s)*100:.1f}%)")

    return _make_result(fig, title, f"Box plot showing quartiles and outliers for {column}", insights)


def violin_plot(df: pd.DataFrame, column: str, group_by: str | None = None) -> dict:
    """Create a violin plot showing distribution shape and density."""
    fig = px.violin(df, y=column, x=group_by, box=True, points="outliers")
    title = f"Violin Plot of {column}" + (f" by {group_by}" if group_by else "")
    fig.update_layout(**_default_layout(title, group_by or "", column))

    insights: list[str] = []
    s = df[column].dropna()
    insights.append(f"Mean={s.mean():.4g}, Std={s.std():.4g}")

    return _make_result(fig, title, f"Density and distribution shape of {column}", insights)


def qq_plot(df: pd.DataFrame, column: str) -> dict:
    """Create a Q-Q plot to assess normality of a distribution."""
    from scipy import stats

    s = df[column].dropna().values
    (osm, osr), (slope, intercept, _) = stats.probplot(s, dist="norm")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=osm, y=osr, mode="markers", name="Data", marker={"size": 4}))
    theoretical_line = slope * np.array(osm) + intercept
    fig.add_trace(go.Scatter(x=osm, y=theoretical_line, mode="lines", name="Theoretical", line={"dash": "dash", "color": "red"}))
    fig.update_layout(**_default_layout(f"Q-Q Plot of {column}", "Theoretical Quantiles", "Sample Quantiles"))

    _, p_value = stats.shapiro(s[:5000] if len(s) > 5000 else s)
    insights = [
        f"Shapiro-Wilk p-value: {p_value:.4g}",
        "Data appears normal" if p_value > 0.05 else "Data deviates from normality",
    ]

    return _make_result(fig, f"Q-Q Plot of {column}", f"Normality assessment for {column}", insights)


# ---------------------------------------------------------------------------
# Relationship / correlation plots
# ---------------------------------------------------------------------------

def scatter_plot(
    df: pd.DataFrame, x_col: str, y_col: str,
    color_by: str | None = None, size_by: str | None = None,
) -> dict:
    """Create an interactive scatter plot of two numeric columns."""
    fig = px.scatter(df, x=x_col, y=y_col, color=color_by, size=size_by,
                     opacity=0.7, trendline="ols" if color_by is None else None)
    title = f"{y_col} vs {x_col}"
    fig.update_layout(**_default_layout(title, x_col, y_col))

    insights: list[str] = []
    corr = df[[x_col, y_col]].dropna().corr().iloc[0, 1]
    insights.append(f"Pearson r = {corr:.3f}")
    if abs(corr) > 0.7:
        insights.append("Strong linear relationship")
    elif abs(corr) > 0.4:
        insights.append("Moderate linear relationship")
    else:
        insights.append("Weak or no linear relationship")

    return _make_result(fig, title, f"Scatter plot of {y_col} vs {x_col}", insights)


def correlation_heatmap(
    df: pd.DataFrame, columns: list[str] | None = None, method: str = "pearson",
) -> dict:
    """Create a correlation heatmap for numeric columns."""
    if columns is None:
        columns = df.select_dtypes(include="number").columns.tolist()

    corr = df[columns].corr(method=method)
    fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale="RdBu_r", zmid=0, text=np.round(corr.values, 2), texttemplate="%{text}",
        textfont={"size": 10},
    ))
    fig.update_layout(**_default_layout(f"Correlation Heatmap ({method.title()})"))

    # Find top correlations
    insights: list[str] = []
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    upper = corr.where(mask)
    pairs = upper.stack().abs().sort_values(ascending=False)
    if len(pairs) > 0:
        top = pairs.head(3)
        for (c1, c2), val in top.items():
            insights.append(f"{c1} & {c2}: r={corr.loc[c1, c2]:.3f}")

    return _make_result(fig, f"Correlation Heatmap ({method})", f"{method.title()} correlation matrix for {len(columns)} features", insights)


def pair_plot(
    df: pd.DataFrame, columns: list[str], color_by: str | None = None, max_cols: int = 6,
) -> dict:
    """Create a pair plot (scatter matrix) for selected columns."""
    cols = columns[:max_cols]
    if len(columns) > max_cols:
        logger.warning("Limiting pair plot to %d columns (requested %d)", max_cols, len(columns))

    dims = [{"label": c, "values": df[c]} for c in cols]
    fig = px.scatter_matrix(df, dimensions=cols, color=color_by, opacity=0.5)
    fig.update_traces(diagonal_visible=True, showupperhalf=False, marker={"size": 3})
    fig.update_layout(**_default_layout(f"Pair Plot ({len(cols)} features)"))
    fig.update_layout(height=200 * len(cols), width=200 * len(cols))

    insights = [f"Showing {len(cols)} features in scatter matrix"]
    return _make_result(fig, f"Pair Plot", f"Pairwise scatter matrix of {len(cols)} features", insights)


# ---------------------------------------------------------------------------
# Categorical / aggregation plots
# ---------------------------------------------------------------------------

def bar_chart(
    df: pd.DataFrame, x_col: str, y_col: str | None = None, orientation: str = "v",
) -> dict:
    """Create a bar chart with optional value column."""
    if y_col is None:
        counts = df[x_col].value_counts().reset_index()
        counts.columns = [x_col, "count"]
        if orientation == "v":
            fig = px.bar(counts, x=x_col, y="count")
        else:
            fig = px.bar(counts, x="count", y=x_col, orientation="h")
        title = f"Counts of {x_col}"
        desc = f"Frequency distribution of {x_col}"
    else:
        if orientation == "v":
            fig = px.bar(df, x=x_col, y=y_col)
        else:
            fig = px.bar(df, x=y_col, y=x_col, orientation="h")
        title = f"{y_col} by {x_col}"
        desc = f"Bar chart of {y_col} grouped by {x_col}"

    fig.update_layout(**_default_layout(title))

    insights: list[str] = []
    vc = df[x_col].value_counts()
    if len(vc) > 0:
        top_pct = vc.iloc[0] / vc.sum() * 100
        insights.append(f"Top category '{vc.index[0]}' accounts for {top_pct:.1f}%")
        insights.append(f"{len(vc)} unique categories")

    return _make_result(fig, title, desc, insights)


def pie_chart(df: pd.DataFrame, labels_col: str, values_col: str | None = None) -> dict:
    """Create a pie chart for categorical proportions."""
    if values_col is None:
        data = df[labels_col].value_counts().reset_index()
        data.columns = [labels_col, "count"]
        fig = px.pie(data, names=labels_col, values="count")
    else:
        fig = px.pie(df, names=labels_col, values=values_col)

    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(**_default_layout(f"Distribution of {labels_col}"))

    insights: list[str] = []
    vc = df[labels_col].value_counts(normalize=True)
    if len(vc) > 0:
        insights.append(f"Largest segment: '{vc.index[0]}' ({vc.iloc[0]*100:.1f}%)")
        if len(vc) >= 2:
            top2_share = (vc.iloc[0] + vc.iloc[1]) * 100
            insights.append(f"Top 2 categories cover {top2_share:.1f}%")

    return _make_result(fig, f"Pie Chart of {labels_col}", f"Proportional breakdown of {labels_col}", insights)


def heatmap(df: pd.DataFrame, x_col: str, y_col: str, value_col: str) -> dict:
    """Create a heatmap from three columns (x, y, value)."""
    pivot = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="mean")

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=[str(c) for c in pivot.columns], y=[str(r) for r in pivot.index],
        colorscale="Viridis", text=np.round(pivot.values, 2), texttemplate="%{text}",
    ))
    fig.update_layout(**_default_layout(f"Heatmap: {value_col} by {x_col} and {y_col}"))

    insights: list[str] = []
    max_val = np.nanmax(pivot.values)
    min_val = np.nanmin(pivot.values)
    insights.append(f"Range: {min_val:.4g} to {max_val:.4g}")

    return _make_result(fig, f"Heatmap of {value_col}", f"{value_col} aggregated by {x_col} and {y_col}", insights)


# ---------------------------------------------------------------------------
# Time-series plots
# ---------------------------------------------------------------------------

def line_chart(
    df: pd.DataFrame, x_col: str, y_col: str, group_by: str | None = None,
) -> dict:
    """Create a line chart, optionally grouped."""
    fig = px.line(df.sort_values(x_col), x=x_col, y=y_col, color=group_by)
    title = f"{y_col} over {x_col}" + (f" by {group_by}" if group_by else "")
    fig.update_layout(**_default_layout(title, x_col, y_col))

    insights: list[str] = []
    s = df[y_col].dropna()
    insights.append(f"Range: {s.min():.4g} to {s.max():.4g}")

    return _make_result(fig, title, f"Line chart of {y_col} over {x_col}", insights)


def time_series_plot(
    df: pd.DataFrame, date_col: str, value_col: str, resample: str | None = None,
) -> dict:
    """Create a time-series plot with optional resampling."""
    ts = df[[date_col, value_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
    ts = ts.dropna().sort_values(date_col)

    if resample:
        ts = ts.set_index(date_col).resample(resample).mean().reset_index()

    fig = px.line(ts, x=date_col, y=value_col)
    title = f"Time Series: {value_col}"
    if resample:
        title += f" (resampled {resample})"
    fig.update_layout(**_default_layout(title, date_col, value_col))

    insights: list[str] = []
    s = ts[value_col].dropna()
    overall_change = ((s.iloc[-1] - s.iloc[0]) / abs(s.iloc[0]) * 100) if len(s) > 1 and s.iloc[0] != 0 and pd.notna(s.iloc[0]) else 0
    insights.append(f"Overall change: {overall_change:+.1f}%")
    insights.append(f"Mean={s.mean():.4g}, Std={s.std():.4g}")

    return _make_result(fig, title, f"Time series of {value_col}", insights)


# ---------------------------------------------------------------------------
# Model evaluation plots
# ---------------------------------------------------------------------------

def residual_plot(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Create a residual plot for regression model evaluation."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    residuals = y_true - y_pred

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=y_pred, y=residuals, mode="markers", marker={"size": 5, "opacity": 0.6}, name="Residuals"))
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.update_layout(**_default_layout("Residual Plot", "Predicted", "Residual"))

    insights: list[str] = []
    insights.append(f"Mean residual: {residuals.mean():.4g}")
    insights.append(f"Std of residuals: {residuals.std():.4g}")

    return _make_result(fig, "Residual Plot", "Residuals vs predicted values", insights)


def confusion_matrix_plot(
    y_true: np.ndarray, y_pred: np.ndarray, labels: list[str] | None = None,
) -> dict:
    """Create an annotated confusion matrix heatmap."""
    from sklearn.metrics import confusion_matrix, accuracy_score

    cm = confusion_matrix(y_true, y_pred)
    if labels is None:
        labels = [str(i) for i in range(cm.shape[0])]

    # Percentage matrix
    cm_total = cm.sum()
    if cm_total == 0:
        raise ToolExecutionError("Confusion matrix sum is zero; no samples to evaluate.")
    cm_pct = cm / cm_total * 100

    text = [[f"{cm[i][j]}<br>({cm_pct[i][j]:.1f}%)" for j in range(cm.shape[1])] for i in range(cm.shape[0])]

    fig = go.Figure(data=go.Heatmap(
        z=cm, x=labels, y=labels, colorscale="Blues",
        text=text, texttemplate="%{text}", textfont={"size": 12},
    ))
    fig.update_layout(**_default_layout("Confusion Matrix", "Predicted", "Actual"))

    acc = accuracy_score(y_true, y_pred)
    insights = [
        f"Accuracy: {acc:.4f}",
        f"Total samples: {cm.sum()}",
    ]

    return _make_result(fig, "Confusion Matrix", "Classification confusion matrix with counts and percentages", insights)


def roc_curve_plot(
    y_true: np.ndarray, y_scores: np.ndarray, model_names: list[str] | None = None,
) -> dict:
    """Create ROC curve(s) with AUC annotation."""
    from sklearn.metrics import roc_curve, roc_auc_score

    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)

    fig = go.Figure()

    if y_scores.ndim == 1:
        y_scores = y_scores.reshape(-1, 1)
    if model_names is None:
        model_names = [f"Model {i+1}" for i in range(y_scores.shape[1])]

    aucs: list[float] = []
    for i in range(y_scores.shape[1]):
        fpr, tpr, _ = roc_curve(y_true, y_scores[:, i])
        auc_val = roc_auc_score(y_true, y_scores[:, i])
        aucs.append(auc_val)
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"{model_names[i]} (AUC={auc_val:.3f})"))

    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash", "color": "gray"}, name="Random", showlegend=False))
    fig.update_layout(**_default_layout("ROC Curve", "False Positive Rate", "True Positive Rate"))

    insights = [f"{name}: AUC={auc:.3f}" for name, auc in zip(model_names, aucs)]

    return _make_result(fig, "ROC Curve", "Receiver Operating Characteristic curve", insights)


def pr_curve_plot(
    y_true: np.ndarray, y_scores: np.ndarray, model_names: list[str] | None = None,
) -> dict:
    """Create Precision-Recall curve(s) with AP annotation."""
    from sklearn.metrics import precision_recall_curve, average_precision_score

    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)

    fig = go.Figure()

    if y_scores.ndim == 1:
        y_scores = y_scores.reshape(-1, 1)
    if model_names is None:
        model_names = [f"Model {i+1}" for i in range(y_scores.shape[1])]

    aps: list[float] = []
    for i in range(y_scores.shape[1]):
        precision, recall, _ = precision_recall_curve(y_true, y_scores[:, i])
        ap = average_precision_score(y_true, y_scores[:, i])
        aps.append(ap)
        fig.add_trace(go.Scatter(x=recall, y=precision, mode="lines", name=f"{model_names[i]} (AP={ap:.3f})"))

    fig.update_layout(**_default_layout("Precision-Recall Curve", "Recall", "Precision"))

    insights = [f"{name}: AP={ap:.3f}" for name, ap in zip(model_names, aps)]

    return _make_result(fig, "Precision-Recall Curve", "Precision vs Recall tradeoff", insights)


def calibration_curve_plot(
    y_true: np.ndarray, y_probs: np.ndarray, n_bins: int = 10,
) -> dict:
    """Create a calibration (reliability) curve."""
    from sklearn.calibration import calibration_curve

    y_true = np.asarray(y_true)
    y_probs = np.asarray(y_probs)

    fraction_pos, mean_predicted = calibration_curve(y_true, y_probs, n_bins=n_bins)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mean_predicted, y=fraction_pos, mode="lines+markers", name="Model"))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash", "color": "gray"}, name="Perfectly calibrated"))
    fig.update_layout(**_default_layout("Calibration Curve", "Mean Predicted Probability", "Fraction of Positives"))

    # Brier score
    brier = float(np.mean((y_probs - y_true) ** 2))
    insights = [
        f"Brier score: {brier:.4f}",
        "Lower Brier score = better calibration" if brier < 0.1 else "Model may benefit from calibration",
    ]

    return _make_result(fig, "Calibration Curve", "Model probability calibration assessment", insights)


def gain_lift_plot(y_true: np.ndarray, y_scores: np.ndarray) -> dict:
    """Create cumulative gain and lift charts."""
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)

    order = np.argsort(-y_scores)
    y_sorted = y_true[order]

    n = len(y_true)
    total_pos = y_sorted.sum()
    if total_pos == 0:
        raise ToolExecutionError("No positive samples found; cannot compute gain/lift chart.")
    cum_pos = np.cumsum(y_sorted)
    pct_population = np.arange(1, n + 1) / n
    pct_gain = cum_pos / total_pos
    lift = pct_gain / pct_population

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Cumulative Gain", "Lift"))

    fig.add_trace(go.Scatter(x=pct_population, y=pct_gain, mode="lines", name="Model"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash", "color": "gray"}, name="Random", showlegend=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=pct_population, y=lift, mode="lines", name="Lift"), row=1, col=2)
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", row=1, col=2)

    fig.update_layout(**_default_layout("Gain & Lift Chart"))

    top_10_gain = float(pct_gain[int(n * 0.1) - 1]) if n >= 10 else float(pct_gain[-1])
    top_10_lift = float(lift[int(n * 0.1) - 1]) if n >= 10 else float(lift[-1])
    insights = [
        f"Top 10% captures {top_10_gain*100:.1f}% of positives",
        f"Lift at 10%: {top_10_lift:.2f}x",
    ]

    return _make_result(fig, "Gain & Lift Chart", "Cumulative gain and lift analysis", insights)


# ---------------------------------------------------------------------------
# Explainability plots
# ---------------------------------------------------------------------------

def shap_summary_plot(shap_values: np.ndarray, feature_names: list[str]) -> dict:
    """Create a SHAP beeswarm-style summary plot using Plotly."""
    shap_values = np.asarray(shap_values)
    mean_abs = np.abs(shap_values).mean(axis=0)
    order = np.argsort(mean_abs)

    fig = go.Figure()
    for idx in order[-20:]:
        fig.add_trace(go.Box(
            x=shap_values[:, idx], name=feature_names[idx],
            orientation="h", marker={"size": 3},
            boxpoints="outliers",
        ))

    fig.update_layout(**_default_layout("SHAP Feature Importance", "SHAP Value", ""))
    fig.update_layout(showlegend=False, height=max(400, 25 * min(len(feature_names), 20)))

    top_features = [feature_names[i] for i in np.argsort(-mean_abs)[:5]]
    insights = [f"Top feature: {top_features[0]}"]
    if len(top_features) > 1:
        insights.append(f"Top 5: {', '.join(top_features)}")

    return _make_result(fig, "SHAP Summary", "SHAP feature importance summary", insights)


def shap_force_plot(
    shap_values: np.ndarray, base_value: float,
    feature_names: list[str], instance_idx: int,
) -> dict:
    """Create a SHAP force (waterfall) plot for a single prediction."""
    sv = shap_values[instance_idx]
    order = np.argsort(np.abs(sv))[::-1][:15]

    names = [feature_names[i] for i in order]
    values = [float(sv[i]) for i in order]

    colors = ["#ff4444" if v > 0 else "#4444ff" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(**_default_layout(
        f"SHAP Waterfall (Instance {instance_idx})",
        "SHAP Value", "",
    ))
    fig.update_layout(yaxis={"autorange": "reversed"})

    prediction = base_value + sv.sum()
    insights = [
        f"Base value: {base_value:.4f}",
        f"Prediction: {prediction:.4f}",
        f"Top contributor: {names[0]} ({values[0]:+.4f})",
    ]

    return _make_result(fig, f"SHAP Waterfall (Instance {instance_idx})", "Feature contributions for single prediction", insights)


def feature_importance_plot(importances: dict, top_n: int = 20) -> dict:
    """Create a horizontal bar chart of feature importances."""
    sorted_items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:top_n]
    names = [x[0] for x in sorted_items][::-1]
    values = [x[1] for x in sorted_items][::-1]

    fig = go.Figure(go.Bar(x=values, y=names, orientation="h", marker_color="#2196F3"))
    fig.update_layout(**_default_layout(f"Top {len(names)} Feature Importances", "Importance", ""))
    fig.update_layout(height=max(400, 25 * len(names)))

    insights = [f"Most important: {sorted_items[0][0]} ({sorted_items[0][1]:.4f})"]
    if len(sorted_items) > 1:
        total = sum(v for _, v in sorted_items)
        top3_share = sum(v for _, v in sorted_items[:3]) / total * 100 if total > 0 else 0
        insights.append(f"Top 3 features account for {top3_share:.1f}% of total importance")

    return _make_result(fig, "Feature Importance", "Ranked feature importances", insights)


def pdp_plot(model: Any, X: pd.DataFrame, feature: str, feature_name: str) -> dict:
    """Create a Partial Dependence Plot for a single feature."""
    from sklearn.inspection import partial_dependence

    result = partial_dependence(model, X, features=[feature], kind="average")
    pd_values = result["average"][0]
    feature_values = result["values"][0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=feature_values, y=pd_values, mode="lines+markers", name=feature_name))
    fig.update_layout(**_default_layout(f"Partial Dependence: {feature_name}", feature_name, "Partial Dependence"))

    insights = [
        f"PD range: {pd_values.min():.4g} to {pd_values.max():.4g}",
        f"Feature range: {feature_values.min():.4g} to {feature_values.max():.4g}",
    ]

    return _make_result(fig, f"PDP: {feature_name}", f"Partial dependence of prediction on {feature_name}", insights)


# ---------------------------------------------------------------------------
# Business / specialized plots
# ---------------------------------------------------------------------------

def funnel_chart(stages: list[dict]) -> dict:
    """Create a funnel chart for conversion or pipeline stages."""
    names = [s["name"] for s in stages]
    values = [s["value"] for s in stages]

    fig = go.Figure(go.Funnel(y=names, x=values, textinfo="value+percent initial"))
    fig.update_layout(**_default_layout("Conversion Funnel"))

    insights: list[str] = []
    if len(values) >= 2:
        overall_conv = values[-1] / values[0] * 100 if values[0] > 0 else 0
        insights.append(f"Overall conversion: {overall_conv:.1f}%")
        biggest_drop = 0
        drop_stage = ""
        for i in range(1, len(values)):
            drop = (values[i - 1] - values[i]) / values[i - 1] * 100 if values[i - 1] > 0 else 0
            if drop > biggest_drop:
                biggest_drop = drop
                drop_stage = f"{names[i-1]} -> {names[i]}"
        if drop_stage:
            insights.append(f"Biggest drop-off: {drop_stage} ({biggest_drop:.1f}%)")

    return _make_result(fig, "Conversion Funnel", "Stage-by-stage conversion funnel", insights)


def cohort_retention_plot(
    df: pd.DataFrame, cohort_col: str, period_col: str, value_col: str,
) -> dict:
    """Create a cohort retention heatmap."""
    pivot = df.pivot_table(index=cohort_col, columns=period_col, values=value_col, aggfunc="mean")

    # Normalize by first period
    retention = pivot.div(pivot.iloc[:, 0], axis=0) * 100

    fig = go.Figure(data=go.Heatmap(
        z=retention.values,
        x=[str(c) for c in retention.columns],
        y=[str(r) for r in retention.index],
        colorscale="YlOrRd_r",
        text=np.round(retention.values, 1),
        texttemplate="%{text}%",
    ))
    fig.update_layout(**_default_layout("Cohort Retention", "Period", "Cohort"))

    insights: list[str] = []
    if retention.shape[1] >= 2:
        avg_retention = retention.iloc[:, 1].mean()
        insights.append(f"Average period-1 retention: {avg_retention:.1f}%")

    return _make_result(fig, "Cohort Retention", "Cohort retention rates over time", insights)


def survival_curve_plot(survival_data: dict) -> dict:
    """Create a Kaplan-Meier style survival curve."""
    time = survival_data["time"]
    prob = survival_data["survival_prob"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time, y=prob, mode="lines", name="Survival", line={"shape": "hv"}))

    if "ci_lower" in survival_data and "ci_upper" in survival_data:
        fig.add_trace(go.Scatter(
            x=list(time) + list(time)[::-1],
            y=list(survival_data["ci_upper"]) + list(survival_data["ci_lower"])[::-1],
            fill="toself", fillcolor="rgba(68,114,196,0.2)",
            line={"color": "rgba(255,255,255,0)"}, name="95% CI",
        ))

    fig.update_layout(**_default_layout("Survival Curve", "Time", "Survival Probability"))
    fig.update_layout(yaxis={"range": [0, 1.05]})

    insights: list[str] = []
    median_idx = np.searchsorted(-np.array(prob), -0.5)
    if median_idx < len(time):
        insights.append(f"Median survival time: {time[median_idx]:.4g}")
    insights.append(f"Final survival probability: {prob[-1]:.3f}")

    return _make_result(fig, "Survival Curve", "Kaplan-Meier survival curve estimate", insights)
