# Spec 04 — Results Dashboard Sections

## Goal

Phase 2 renders 6 stacked sections in this order:
1. Insights summary (top, gradient card)
2. Target distribution callout
3. Featured chart (correlation heatmap)
4. Charts grid (2-column)
5. Statistical findings table
6. Quality flags grid (outliers + red flags)

Each section is its own component reading from `st.session_state.eda_results`.

## Backend reuse

`agents.eda_agent.run_analyses(state)` is the canonical run function. It populates:
- `st.session_state["eda_results"]` — dict of analysis outputs
- `st.session_state["eda_charts"]` — list of chart specs (each with type, title, data)
- `st.session_state["eda_insights"]` — list of LLM-summarized insights
- `st.session_state["eda_stats"]` — list of statistical test results
- `st.session_state["eda_quality_flags"]` — dict with outliers + red_flags lists

**Open `agents/eda_agent.py` first** to confirm the actual structure. If the agent stores everything in one nested dict, write a thin adapter `dashboard/components/ed_results_adapter.py` that pulls the right slices — do not modify the agent.

## File: `dashboard/components/ed_insights_summary.py`

```python
"""Top insights summary card with LLM-generated takeaways."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    insights = st.session_state.get("eda_insights", [])
    n_charts = len(st.session_state.get("eda_charts", []))

    if not insights:
        return

    insights_html = ""
    for i, ins in enumerate(insights, start=1):
        text = _html_escape(ins.get("text", ""))
        # Allow simple <strong> from agent-generated text — escape everything else
        text = text.replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")
        text = text.replace("&lt;code&gt;", '<code style="font-family:var(--font-mono);font-size:11px;color:var(--violet);">').replace("&lt;/code&gt;", "</code>")

        confidence = ins.get("confidence", "high")
        conf_class = "high" if confidence == "high" else "medium"
        meta = ins.get("evidence", "")  # e.g., "p<0.001, n=24,380"

        insights_html += (
            f'<div class="ed-insight-card">'
            f'  <div class="ed-insight-num">{i:02d}</div>'
            f'  <div class="ed-insight-body">'
            f'    <div class="ed-insight-text">{text}</div>'
            f'    <div class="ed-insight-meta">'
            f'      <span class="ed-insight-conf {conf_class}">{confidence.title()} confidence</span>'
            f'      {"<span style=\"color:var(--text-muted);\">·</span><span style=\"color:var(--text-muted);\">" + _html_escape(meta) + "</span>" if meta else ""}'
            f'      <span class="ed-insight-drill">Drill into this →</span>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )

    st.markdown(
        f'<section class="ed-insights-summary">'
        f'  <h2>Key <em>insights</em></h2>'
        f'  <div class="ed-insights-meta">'
        f'    <span>{len(insights)} takeaways · LLM-summarized · {n_charts} charts run</span>'
        f'  </div>'
        f'  {insights_html}'
        f'</section>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ed_target_callout.py`

```python
"""Target distribution callout — highlights class imbalance for classification."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    df = st.session_state.get("df")
    if not project or df is None or df.empty:
        return

    target = project.target_column
    if not target or target not in df.columns:
        return

    s = df[target].dropna()
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > 10:
        # Numeric continuous target — render a brief skewness summary instead
        _render_numeric_callout(target, s)
        return

    # Categorical / boolean target → class balance bar
    counts = s.value_counts()
    total = len(s)
    if len(counts) < 2:
        return
    minority_pct = float(counts.min()) / total * 100
    is_imbalanced = minority_pct < 30

    bars_html = ""
    legend_html = ""
    palette = ["rgba(99,102,241,0.6)", "rgba(236,72,153,0.7)",
               "rgba(168,85,247,0.6)", "rgba(34,211,238,0.6)"]
    for i, (val, count) in enumerate(counts.items()):
        pct = count / total * 100
        color = palette[i % len(palette)]
        bars_html += f'<div class="ed-tc-bar" style="flex: {pct}; background: {color};">{_html_escape(str(val))} ({pct:.1f}%)</div>'
        legend_html += (
            f'<span><span class="ed-tc-dot" style="background: {color};"></span>'
            f'{count:,} {_html_escape(str(val))}</span>'
        )

    pill = ('<span class="ed-tc-pill warn">Imbalanced</span>' if is_imbalanced
            else '<span class="ed-tc-pill">Balanced</span>')
    sub = (f"Class imbalance — minority class is {minority_pct:.1f}% of records. "
           "Consider stratified sampling and class weights." if is_imbalanced
           else "Classes appear well-balanced.")

    st.markdown(
        f'<div class="ed-target-callout">'
        f'  <div class="ed-tc-head">'
        f'    <div>'
        f'      <div class="ed-tc-title">🎯 Target distribution: {_html_escape(target)}</div>'
        f'      <div class="ed-tc-sub">{sub}</div>'
        f'    </div>'
        f'    {pill}'
        f'  </div>'
        f'  <div class="ed-tc-bars">{bars_html}</div>'
        f'  <div class="ed-tc-legend">{legend_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_numeric_callout(target: str, s: pd.Series) -> None:
    skew = s.skew()
    skew_label = "Right-skewed" if skew > 1 else ("Left-skewed" if skew < -1 else "Approximately symmetric")
    st.markdown(
        f'<div class="ed-target-callout">'
        f'  <div class="ed-tc-head">'
        f'    <div>'
        f'      <div class="ed-tc-title">🎯 Target distribution: {_html_escape(target)}</div>'
        f'      <div class="ed-tc-sub">{skew_label} (skew = {skew:.2f}). Mean = {s.mean():.2f}, median = {s.median():.2f}.</div>'
        f'    </div>'
        f'    <span class="ed-tc-pill">Continuous</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ed_featured_chart.py`

```python
"""Featured chart — correlation heatmap with target row highlighted."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np

from dashboard.components import project_service


def render() -> None:
    df = st.session_state.get("df")
    project = project_service.get_active()
    if df is None or df.empty:
        return

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return

    # Limit to top N most variant columns + target
    n_cols = min(7, numeric_df.shape[1])
    top_cols = list(numeric_df.var().sort_values(ascending=False).index[:n_cols])
    target = project.target_column if project else None
    if target and target in numeric_df.columns and target not in top_cols:
        top_cols = top_cols[:-1] + [target]

    corr = numeric_df[top_cols].corr().round(2)

    # Render as HTML grid (Streamlit's plotly heatmap is fine too — but HTML matches mockup)
    cells_html = '<div class="ed-heatmap" style="grid-template-columns: 100px repeat(' + str(n_cols) + ', 1fr);">'
    cells_html += '<div></div>'  # corner
    for c in top_cols:
        is_target = c == target
        label_style = ' style="color: var(--violet);"' if is_target else ""
        cells_html += f'<div class="ed-hm-label"{label_style}>{_short(c)}</div>'

    for i, row in enumerate(top_cols):
        cells_html += f'<div class="ed-hm-label">{_short(row)}</div>'
        for col in top_cols:
            v = float(corr.loc[row, col])
            klass = _bucket(v)
            cells_html += f'<div class="ed-hm-cell {klass}">{v:.1f}</div>'
    cells_html += '</div>'

    st.markdown(
        '<section>'
        '  <div class="ed-sec">'
        '    <h3>Featured <em>chart</em></h3>'
        '    <span class="ed-sec-meta">Correlation heatmap · numeric columns</span>'
        '  </div>'
        '  <div class="ed-featured">'
        '    <div class="ed-featured-head">'
        '      <div>'
        '        <div class="ed-featured-title">Pearson correlation matrix</div>'
        f'        <div class="ed-chart-sub" style="margin-top:4px;">{n_cols} numeric columns · target highlighted</div>'
        '      </div>'
        '      <span class="ed-featured-tag">Featured</span>'
        '    </div>'
        f'    {cells_html}'
        '  </div>'
        '</section>',
        unsafe_allow_html=True,
    )


def _short(name: str) -> str:
    return name if len(name) <= 8 else name[:6] + "…"


def _bucket(v: float) -> str:
    """Map -1..1 correlation to a color-bucket CSS class."""
    if v >= 0.95: return "h-100"
    if v >= 0.7:  return "h-80"
    if v >= 0.5:  return "h-60"
    if v >= 0.3:  return "h-40"
    if v >= 0.1:  return "h-20"
    if v >= -0.1: return "h-0"
    if v >= -0.5: return "h-n20"
    return "h-n60"
```

## File: `dashboard/components/ed_charts_grid.py`

```python
"""2-column charts grid — renders pre-computed chart specs."""
from __future__ import annotations
import streamlit as st


TYPE_PILL_CLASSES = {
    "histogram": ("dist", "Distribution"),
    "distribution": ("dist", "Distribution"),
    "boxplot": ("box", "Box plot"),
    "box": ("box", "Box plot"),
    "scatter": ("scatter", "Scatter"),
    "bar": ("bar", "Bar"),
    "line": ("dist", "Line"),
}


def render() -> None:
    charts = st.session_state.get("eda_charts", [])
    if not charts:
        return

    # Apply filters from session state
    active_types = st.session_state.get("ed_filter_types", set(TYPE_PILL_CLASSES.keys()))
    visible = [c for c in charts if c.get("type", "histogram").lower() in active_types]

    st.markdown(
        f'<section>'
        f'  <div class="ed-sec">'
        f'    <h3>All <em>charts</em></h3>'
        f'    <span class="ed-sec-meta">{len(visible)} of {len(charts)} visible</span>'
        f'  </div>'
        f'</section>',
        unsafe_allow_html=True,
    )

    # Render in pairs
    for i in range(0, len(visible), 2):
        cols = st.columns(2, gap="medium")
        for col, chart in zip(cols, visible[i:i + 2]):
            with col:
                _render_tile(chart)


def _render_tile(chart: dict) -> None:
    chart_type = chart.get("type", "histogram").lower()
    pill_class, pill_label = TYPE_PILL_CLASSES.get(chart_type, ("dist", chart_type.title()))

    title = _html_escape(chart.get("title", "Untitled"))
    sub = _html_escape(chart.get("subtitle", ""))
    caption = _html_escape(chart.get("interpretation", chart.get("caption", "")))

    # Wrap a Streamlit-native plotly_chart inside a styled tile.
    # If the chart spec includes a Plotly figure, use it; otherwise fall back to a placeholder.
    fig = chart.get("figure")

    st.markdown(
        f'<div class="ed-chart-tile">'
        f'  <div class="ed-chart-head">'
        f'    <div>'
        f'      <div class="ed-chart-title">{title}</div>'
        f'      <div class="ed-chart-sub">{sub}</div>'
        f'    </div>'
        f'    <span class="ed-chart-type-pill {pill_class}">{pill_label}</span>'
        f'  </div>',
        unsafe_allow_html=True,
    )
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=f"ed_chart_{chart.get('id', title)}")
    st.markdown(
        f'  <div class="ed-chart-caption">{caption}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ed_stats_findings.py`

```python
"""Statistical findings table with color-coded p-values."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    stats = st.session_state.get("eda_stats", [])
    if not stats:
        return

    sig_threshold = st.session_state.get("ed_filter_significance", 0.05)
    visible = [s for s in stats if s.get("p_value", 1.0) <= sig_threshold or sig_threshold >= 0.10]
    n_sig = sum(1 for s in stats if s.get("p_value", 1.0) < 0.05)

    rows_html = ""
    for s in visible:
        p = s.get("p_value", 1.0)
        if p < 0.01:   pclass = "signif"; ptext = "&lt; 0.001" if p < 0.001 else f"{p:.3f}"
        elif p < 0.05: pclass = "signif"; ptext = f"{p:.3f}"
        elif p < 0.10: pclass = "weak";   ptext = f"{p:.3f}"
        else:          pclass = "ns";     ptext = f"{p:.3f}"

        rows_html += (
            f'<tr>'
            f'  <td>'
            f'    <div class="ed-test-name">{_html_escape(s.get("test", "—"))}</div>'
            f'    <div class="ed-test-cols">{_html_escape(s.get("columns", ""))}</div>'
            f'  </td>'
            f'  <td><span class="ed-pval {pclass}">{ptext}</span></td>'
            f'  <td class="ed-effect">{_html_escape(s.get("effect_size", "—"))}</td>'
            f'  <td class="ed-interp">{_html_escape(s.get("interpretation", ""))}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<section>'
        f'  <div class="ed-sec">'
        f'    <h3>Statistical <em>findings</em></h3>'
        f'    <span class="ed-sec-meta">{len(stats)} tests · {n_sig} significant at p &lt; 0.05</span>'
        f'  </div>'
        f'  <div class="ed-stats-wrap">'
        f'    <table class="ed-stats">'
        f'      <thead><tr><th>Test</th><th>p-value</th><th>Effect size</th><th>Interpretation</th></tr></thead>'
        f'      <tbody>{rows_html}</tbody>'
        f'    </table>'
        f'  </div>'
        f'</section>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ed_quality_flags.py`

```python
"""Quality flags grid — outliers (amber) + modeling red flags (red)."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    flags = st.session_state.get("eda_quality_flags", {})
    outliers = flags.get("outliers", [])
    red_flags = flags.get("red_flags", [])
    if not outliers and not red_flags:
        return

    st.markdown(
        '<section>'
        '  <div class="ed-sec">'
        '    <h3>Quality <em>flags</em></h3>'
        '    <span class="ed-sec-meta">Issues to address before modeling</span>'
        '  </div>'
        '</section>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2, gap="medium")
    with cols[0]:
        _render_flag_card(
            kind="outliers",
            title="Outliers detected",
            count_label=f"{len(outliers)} columns",
            items=outliers,
            icon_svg='<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        )
    with cols[1]:
        _render_flag_card(
            kind="redflags",
            title="Modeling red flags",
            count_label=f"{len(red_flags)} issues",
            items=red_flags,
            icon_svg='<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
        )


def _render_flag_card(kind: str, title: str, count_label: str, items: list[dict], icon_svg: str) -> None:
    items_html = ""
    for it in items:
        col = _html_escape(it.get("column", "—"))
        stat = _html_escape(it.get("description", ""))
        items_html += (
            f'<div class="ed-flag-item">'
            f'  <span class="ed-flag-col">{col}</span>'
            f'  <span class="ed-flag-stat">{stat}</span>'
            f'  <span class="ed-flag-action">{"Investigate →" if kind == "outliers" else "Review →"}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="ed-flag-card {kind}">'
        f'  <div class="ed-flag-head">'
        f'    {icon_svg}'
        f'    <div class="ed-flag-title">{title}</div>'
        f'    <span class="ed-flag-count">{count_label}</span>'
        f'  </div>'
        f'  <div class="ed-flag-list">{items_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Insights summary ============ */
.ed-insights-summary {
  background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(168,85,247,0.04));
  border: 1px solid var(--border-default); border-radius: 18px;
  padding: 24px 26px; margin-bottom: 28px;
  backdrop-filter: blur(14px);
  position: relative; overflow: hidden;
}
.ed-insights-summary::before {
  content: ""; position: absolute; right: -40px; top: -40px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(168,85,247,0.18), transparent 60%);
  pointer-events: none;
}
.ed-insights-summary h2 {
  font-family: var(--font-display); font-size: 24px; margin-bottom: 4px;
}
.ed-insights-summary h2 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ed-insights-meta {
  font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);
  margin-bottom: 18px;
}
.ed-insight-card {
  display: flex; gap: 14px; padding: 14px 16px; margin-bottom: 8px;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: 12px; cursor: pointer; transition: all 0.18s ease;
}
.ed-insight-card:hover {
  transform: translateX(2px); border-color: var(--border-strong);
  background: rgba(139,92,246,0.08);
}
.ed-insight-num {
  width: 26px; height: 26px; flex-shrink: 0;
  background: rgba(139,92,246,0.12); border: 1px solid var(--border-default);
  border-radius: 50%; display: grid; place-items: center;
  color: var(--violet); font-family: var(--font-mono); font-size: 11px;
}
.ed-insight-body { flex: 1; }
.ed-insight-text {
  font-size: 13.5px; color: var(--text-primary); line-height: 1.5; margin-bottom: 6px;
}
.ed-insight-meta {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono); font-size: 10px;
}
.ed-insight-conf {
  padding: 2px 8px; border-radius: 999px;
  letter-spacing: 0.5px; text-transform: uppercase;
}
.ed-insight-conf.high   { color: var(--green); background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.ed-insight-conf.medium { color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.ed-insight-drill { color: var(--violet); cursor: pointer; margin-left: auto; }

/* ============ Section headers ============ */
.ed-sec {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin: 36px 0 18px;
}
.ed-sec h3 { font-family: var(--font-display); font-size: 26px; line-height: 1.1; }
.ed-sec h3 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ed-sec-meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

/* ============ Target callout ============ */
.ed-target-callout {
  background: linear-gradient(135deg, rgba(34,211,238,0.06), rgba(99,102,241,0.04));
  border: 1px solid rgba(34,211,238,0.3);
  border-radius: 16px; padding: 20px;
  margin-bottom: 24px; backdrop-filter: blur(14px);
}
.ed-tc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 14px; }
.ed-tc-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.ed-tc-sub { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.ed-tc-pill {
  font-family: var(--font-mono); font-size: 10px;
  padding: 3px 10px; border-radius: 999px;
  color: var(--cyan); background: rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.3);
  letter-spacing: 0.6px; text-transform: uppercase;
}
.ed-tc-pill.warn { color: var(--amber); background: rgba(251,191,36,0.1); border-color: rgba(251,191,36,0.3); }
.ed-tc-bars { display: flex; gap: 4px; height: 28px; margin-bottom: 8px; }
.ed-tc-bar {
  border-radius: 4px;
  display: grid; place-items: center;
  color: white; font-family: var(--font-mono); font-size: 10.5px;
}
.ed-tc-legend { display: flex; gap: 18px; font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }
.ed-tc-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }

/* ============ Featured chart (heatmap) ============ */
.ed-featured {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px; margin-bottom: 24px;
  backdrop-filter: blur(14px);
}
.ed-featured-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 14px; gap: 14px;
}
.ed-featured-title { font-size: 16px; font-weight: 500; color: var(--text-primary); }
.ed-featured-tag {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 3px 10px; background: rgba(168,85,247,0.1);
  border: 1px solid rgba(168,85,247,0.3); border-radius: 999px;
  color: var(--purple); letter-spacing: 0.6px; text-transform: uppercase;
}
.ed-heatmap { display: grid; gap: 2px; padding: 12px 0; }
.ed-hm-label {
  font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); padding: 6px 8px; text-align: right;
}
.ed-hm-cell {
  aspect-ratio: 1; border-radius: 4px; display: grid; place-items: center;
  font-family: var(--font-mono); font-size: 10px; color: white;
  cursor: pointer; transition: transform 0.15s ease;
}
.ed-hm-cell:hover { transform: scale(1.1); z-index: 1; box-shadow: 0 0 12px rgba(139,92,246,0.5); }
.ed-hm-cell.h-100 { background: #6366F1; }
.ed-hm-cell.h-80  { background: rgba(99,102,241,0.85); }
.ed-hm-cell.h-60  { background: rgba(99,102,241,0.65); }
.ed-hm-cell.h-40  { background: rgba(99,102,241,0.45); color: var(--text-primary); }
.ed-hm-cell.h-20  { background: rgba(99,102,241,0.25); color: var(--text-primary); }
.ed-hm-cell.h-0   { background: rgba(139,92,246,0.08); color: var(--text-muted); }
.ed-hm-cell.h-n20 { background: rgba(236,72,153,0.3); color: var(--text-primary); }
.ed-hm-cell.h-n60 { background: rgba(236,72,153,0.6); }

/* ============ Charts grid ============ */
.ed-chart-tile {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; margin-bottom: 16px;
  cursor: pointer; transition: all 0.22s ease; backdrop-filter: blur(14px);
}
.ed-chart-tile:hover {
  transform: translateY(-2px); border-color: var(--border-strong);
  box-shadow: 0 8px 22px -10px rgba(139,92,246,0.4);
}
.ed-chart-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 10px; margin-bottom: 12px;
}
.ed-chart-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.ed-chart-sub { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); margin-top: 2px; }
.ed-chart-type-pill {
  font-family: var(--font-mono); font-size: 9px;
  padding: 2px 7px; border-radius: 999px; letter-spacing: 0.5px;
  text-transform: uppercase; flex-shrink: 0;
}
.ed-chart-type-pill.dist    { color: var(--violet); background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); }
.ed-chart-type-pill.box     { color: var(--cyan);   background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.3); }
.ed-chart-type-pill.scatter { color: var(--green);  background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.ed-chart-type-pill.bar     { color: var(--amber);  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.ed-chart-caption {
  font-size: 12px; color: var(--text-muted); line-height: 1.4;
  padding-top: 8px; border-top: 1px solid var(--border-subtle);
}

/* ============ Stats table ============ */
.ed-stats-wrap {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; overflow: hidden; backdrop-filter: blur(14px);
}
table.ed-stats { width: 100%; border-collapse: collapse; font-size: 13px; }
table.ed-stats thead {
  background: rgba(139,92,246,0.06);
  border-bottom: 1px solid var(--border-subtle);
}
table.ed-stats th {
  text-align: left; padding: 12px 18px;
  font-family: var(--font-mono); font-size: 10px;
  font-weight: 600; letter-spacing: 1.2px;
  text-transform: uppercase; color: var(--text-muted);
}
table.ed-stats td { padding: 12px 18px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); }
table.ed-stats tr:last-child td { border-bottom: none; }
table.ed-stats tr:hover { background: rgba(139,92,246,0.04); }
.ed-test-name { color: var(--text-primary); font-weight: 500; }
.ed-test-cols { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.ed-pval {
  font-family: var(--font-mono); font-size: 12px;
  padding: 2px 8px; border-radius: 6px;
}
.ed-pval.signif { color: var(--green); background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); }
.ed-pval.weak   { color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); }
.ed-pval.ns     { color: var(--text-muted); background: rgba(139,92,246,0.05); border: 1px solid var(--border-subtle); }
.ed-effect { font-family: var(--font-mono); font-size: 11px; }
.ed-interp { font-size: 12px; color: var(--text-secondary); font-style: italic; }

/* ============ Quality flags ============ */
.ed-flag-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; backdrop-filter: blur(14px);
  margin-bottom: 16px;
}
.ed-flag-head {
  display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
}
.ed-flag-head svg { width: 16px; height: 16px; }
.ed-flag-card.outliers .ed-flag-head svg { color: var(--amber); }
.ed-flag-card.redflags .ed-flag-head svg { color: var(--red); }
.ed-flag-title { font-size: 14px; font-weight: 600; }
.ed-flag-count {
  font-family: var(--font-mono); font-size: 10px;
  padding: 2px 8px; border-radius: 999px; margin-left: auto;
}
.ed-flag-card.outliers .ed-flag-count {
  color: var(--amber); background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
}
.ed-flag-card.redflags .ed-flag-count {
  color: var(--red); background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3);
}
.ed-flag-list { display: flex; flex-direction: column; gap: 6px; }
.ed-flag-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  background: rgba(139,92,246,0.04); border: 1px solid var(--border-subtle);
  border-radius: 8px; font-size: 12.5px;
}
.ed-flag-col {
  font-family: var(--font-mono); font-size: 11.5px; color: var(--violet);
  padding: 2px 8px; background: rgba(139,92,246,0.08); border-radius: 6px;
}
.ed-flag-stat { color: var(--text-muted); flex: 1; }
.ed-flag-action { font-size: 11px; color: var(--violet); cursor: pointer; }
```
