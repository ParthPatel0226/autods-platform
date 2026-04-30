# Spec 07 — Model Card + Calibration

## Backend reuse

- `explainability/model_card_generator.py` — `generate_model_card(model, X_train, y_train, X_test, y_test, domain_config, metrics)` returns a structured dict. **Open first.**
- `explainability/calibration.py` — `compute_calibration(model, X_test, y_test)` returns calibration curve data + ECE + Brier score. **Open first.**

## File: `dashboard/components/ex_model_card.py`

```python
"""Auto-generated model card rendered as a styled document."""
from __future__ import annotations
import streamlit as st
from dashboard.components import project_service


def render(card_data: dict) -> None:
    """Render the model card document.

    Args:
        card_data: dict with sections — overview, intended_use, metrics,
                   limitations, ethical_considerations, training_data, evaluation_data
    """
    if not card_data:
        st.info("Model card not generated yet.")
        return

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Model <em>card</em></h3>'
        '<span class="ex-sec-meta">Google model card format · auto-generated</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ex-model-card-doc">', unsafe_allow_html=True)

    # Overview
    overview = card_data.get("overview", {})
    _render_section("Model <em>overview</em>", [
        ("Model name", overview.get("name", "—")),
        ("Version", overview.get("version", "—")),
        ("Framework", overview.get("framework", "—")),
        ("Task", overview.get("task", "—")),
        ("Primary metric", overview.get("primary_metric", "—")),
    ])

    # Intended use
    use = card_data.get("intended_use", {})
    _render_section("Intended <em>use</em>", [
        ("Use case", use.get("primary_use", "—")),
        ("Users", use.get("primary_users", "—")),
        ("Out of scope", use.get("out_of_scope", "—")),
    ])

    # Ethical considerations
    ethics = card_data.get("ethical_considerations", {})
    _render_section("Ethical <em>considerations</em>", [
        ("Protected attrs", ", ".join(ethics.get("protected_attributes", []))),
        ("Fairness result", ethics.get("fairness_summary", "—")),
        ("Risks", ethics.get("risks", "—")),
    ])
    # Tags
    tags = ethics.get("tags", ["Human-in-the-loop Required"])
    tags_html = "".join(f'<span class="ex-mc-tag">{_html_escape(t)}</span>' for t in tags)
    st.markdown(f'<div class="ex-mc-tags">{tags_html}</div>', unsafe_allow_html=True)

    # Training data
    data = card_data.get("training_data", {})
    _render_section("Training <em>data</em>", [
        ("Dataset", data.get("name", "—")),
        ("Size", data.get("size", "—")),
        ("Split", data.get("split_strategy", "—")),
        ("Class balance", data.get("class_balance", "—")),
    ])

    st.markdown('</div>', unsafe_allow_html=True)

    # Export buttons
    cols = st.columns(2)
    with cols[0]:
        if st.button("📋 Download as PDF", key="ex_mc_pdf", use_container_width=True):
            st.info("PDF export will be wired to reports/generators/pdf_report.py")
    with cols[1]:
        if st.button("📝 Download as Markdown", key="ex_mc_md", use_container_width=True):
            st.info("Markdown export will be wired to model_card_generator.export_markdown()")


def _render_section(title_html: str, rows: list[tuple[str, str]]) -> None:
    rows_html = "".join(
        f'<div class="ex-mc-kv"><div class="ex-mc-key">{k}</div>'
        f'<div class="ex-mc-val">{_html_escape(str(v))}</div></div>'
        for k, v in rows
    )
    st.markdown(
        f'<div class="ex-mc-section">'
        f'  <div class="ex-mc-section-title">{title_html}</div>'
        f'  {rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/ex_calibration.py`

```python
"""Calibration analysis — reliability diagram + metrics."""
from __future__ import annotations
import streamlit as st


def render(calibration_data: dict) -> None:
    """Render the Calibration tab.

    Args:
        calibration_data: dict with:
            curve_points: list[{"predicted": float, "observed": float}]
            ece: float (Expected Calibration Error)
            brier: float (Brier score)
            mce: float (Maximum Calibration Error)
            hosmer_lemeshow_p: float
    """
    if not calibration_data:
        st.info("Calibration data not computed.")
        return

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Calibration <em>analysis</em></h3>'
        '<span class="ex-sec-meta">Reliability diagram + Brier score</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.2, 1], gap="large")

    with left:
        _render_reliability_diagram(calibration_data.get("curve_points", []))

    with right:
        _render_metrics([
            ("Expected Calibration Error (ECE)", calibration_data.get("ece", 0),
             "Excellent" if calibration_data.get("ece", 1) < 0.05 else "Review",
             calibration_data.get("ece", 0) < 0.05),
            ("Brier Score", calibration_data.get("brier", 0),
             "Good (lower is better)", calibration_data.get("brier", 1) < 0.15),
            ("Maximum Calibration Error", calibration_data.get("mce", 0),
             "Worst-bin deviation", calibration_data.get("mce", 1) < 0.10),
            ("Hosmer-Lemeshow p-value", calibration_data.get("hosmer_lemeshow_p", 0),
             "No significant miscalibration" if calibration_data.get("hosmer_lemeshow_p", 0) > 0.05 else "Possible miscalibration",
             calibration_data.get("hosmer_lemeshow_p", 0) > 0.05),
        ])


def _render_reliability_diagram(points: list[dict]) -> None:
    """Render SVG reliability diagram."""
    if not points:
        st.info("No calibration curve data.")
        return

    # Map points to SVG coordinates (40..280 x, 260..20 y)
    def map_x(v): return 40 + v * 240
    def map_y(v): return 260 - v * 240

    polyline_points = " ".join(f"{map_x(p['predicted']):.0f},{map_y(p['observed']):.0f}" for p in points)
    dots = "".join(
        f'<circle cx="{map_x(p["predicted"]):.0f}" cy="{map_y(p["observed"]):.0f}" r="4" fill="var(--violet)"/>'
        for p in points
    )

    svg = (
        '<svg viewBox="0 0 300 300" style="width:100%;height:280px;">'
        '<line x1="40" y1="260" x2="280" y2="260" stroke="var(--border-subtle)" stroke-width="1"/>'
        '<line x1="40" y1="260" x2="40" y2="20" stroke="var(--border-subtle)" stroke-width="1"/>'
        '<line x1="40" y1="260" x2="280" y2="20" stroke="var(--text-faint)" stroke-width="1" stroke-dasharray="4 3"/>'
        f'<polyline points="{polyline_points}" fill="none" stroke="var(--violet)" stroke-width="2.5" stroke-linejoin="round"/>'
        f'{dots}'
        '<text x="160" y="290" text-anchor="middle" fill="var(--text-muted)" font-family="var(--font-mono)" font-size="10">Predicted probability</text>'
        '<text x="15" y="140" text-anchor="middle" fill="var(--text-muted)" font-family="var(--font-mono)" font-size="10" transform="rotate(-90, 15, 140)">Observed frequency</text>'
        '</svg>'
    )

    st.markdown(
        f'<div class="ex-calibration-chart">'
        f'  <div style="font-size:14px;font-weight:500;margin-bottom:14px;">Reliability diagram</div>'
        f'  {svg}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_metrics(metrics: list[tuple]) -> None:
    for label, value, sub, is_good in metrics:
        color = "var(--green)" if is_good else "var(--amber)"
        bar_pct = min(value * 100 if value < 1 else value, 100)
        bar_color = "linear-gradient(90deg,var(--green),var(--cyan))" if is_good else "linear-gradient(90deg,var(--amber),var(--red))"

        st.markdown(
            f'<div class="ex-cal-card">'
            f'  <div class="ex-cal-label">{label}</div>'
            f'  <div class="ex-cal-value" style="color:{color};">{value:.3f}</div>'
            f'  <div class="ex-cal-sub">{sub}</div>'
            f'  <div class="ex-cal-bar"><div class="ex-cal-fill" style="width:{bar_pct:.0f}%;background:{bar_color};"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


## CSS additions

```css
/* ============ Model Card ============ */
.ex-model-card-doc { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 32px; backdrop-filter: blur(14px); margin-bottom: 24px; }
.ex-mc-section { margin-bottom: 28px; }
.ex-mc-section-title { font-family: var(--font-display); font-size: 22px; margin-bottom: 4px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle); }
.ex-mc-section-title em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.ex-mc-kv { display: grid; grid-template-columns: 160px 1fr; gap: 6px; padding: 6px 0;
  border-bottom: 1px solid rgba(139,92,246,0.06); font-size: 13.5px; }
.ex-mc-kv:last-child { border-bottom: none; }
.ex-mc-key { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);
  letter-spacing: 0.5px; text-transform: uppercase; padding-top: 3px; }
.ex-mc-val { color: var(--text-secondary); }
.ex-mc-tags { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 24px; }
.ex-mc-tag { padding: 4px 10px; background: rgba(139,92,246,0.08); border: 1px solid var(--border-subtle);
  border-radius: 999px; font-family: var(--font-mono); font-size: 10px; color: var(--violet);
  letter-spacing: 0.5px; text-transform: uppercase; }

/* ============ Calibration ============ */
.ex-calibration-chart { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px; backdrop-filter: blur(14px); }
.ex-cal-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; backdrop-filter: blur(14px); margin-bottom: 14px; }
.ex-cal-label { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }
.ex-cal-value { font-family: var(--font-display); font-size: 32px; line-height: 1; margin-bottom: 4px; }
.ex-cal-sub { font-size: 12px; color: var(--text-muted); }
.ex-cal-bar { height: 4px; background: rgba(139,92,246,0.1); border-radius: 2px; margin-top: 8px; overflow: hidden; }
.ex-cal-fill { height: 100%; border-radius: 2px; }
```
