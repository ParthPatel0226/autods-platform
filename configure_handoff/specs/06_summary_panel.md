# Spec 06 — Sticky Summary Panel + Pipeline Estimator

## Goal

Right-side sticky **Analysis Plan** card that mirrors all left-side selections live, plus a **pipeline estimate** block (charts / models / runtime / cost) and the **Start Analysis** primary CTA.

## File: `dashboard/components/cf_pipeline_estimator.py`

```python
"""Pure-Python estimator for pipeline runtime, model count, charts, and LLM cost."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PipelineEstimate:
    n_charts: int
    n_stat_tests: int
    n_models: int
    n_shap: int
    runtime_seconds: int
    llm_cost_usd: float

    @property
    def runtime_str(self) -> str:
        m, s = divmod(self.runtime_seconds, 60)
        if m >= 60:
            h, m = divmod(m, 60)
            return f"{h} h {m} min"
        if m == 0:
            return f"{s} s"
        return f"{m} min {s} s"

    @property
    def cost_str(self) -> str:
        if self.llm_cost_usd < 0.01:
            return "<$0.01"
        return f"~${self.llm_cost_usd:.2f}"


def estimate(
    *,
    n_rows: int,
    n_cols_kept: int,
    mode: str,
    problem_type: str,
    domain_key: str,
) -> PipelineEstimate:
    """Compute pipeline estimates from current configuration.

    All numbers are heuristic — they should feel reasonable, not be exact.
    """
    # Charts: scale with column count and mode
    base_charts = min(8 + n_cols_kept // 2, 50)
    if mode == "expert": base_charts += 8
    if mode == "auto":   base_charts -= 4

    # Statistical tests
    base_tests = max(4, n_cols_kept // 3)
    if problem_type in {"classification", "regression"}: base_tests += 4

    # Models
    if problem_type == "clustering":   n_models = 4
    elif problem_type == "anomaly":    n_models = 3
    elif problem_type == "timeseries": n_models = 5
    elif problem_type == "survival":   n_models = 3
    else:                              n_models = 7   # classification / regression / auto

    if mode == "auto":   n_models = max(3, n_models - 2)
    if mode == "expert": n_models += 2

    # SHAP / explainability
    n_shap = 3 if problem_type in {"classification", "regression"} else 1
    if mode == "expert": n_shap += 2

    # Runtime: rough proxy — base + per-row + per-model
    row_time = min(n_rows, 1_000_000) / 5000  # seconds per "unit of data"
    model_time = n_models * 18                # ~18 s per model
    chart_time = base_charts * 0.8
    overhead = 30 if mode == "auto" else 60 if mode == "guided" else 90
    runtime = int(overhead + row_time + model_time + chart_time)

    # LLM cost: depends on mode (more interactive = more LLM calls)
    cost_per_mode = {"auto": 0.06, "guided": 0.18, "expert": 0.45}
    cost = cost_per_mode.get(mode, 0.18)
    if domain_key in {"healthcare", "finance", "hr"}:
        cost *= 1.15  # extra for compliance prompts

    return PipelineEstimate(
        n_charts=base_charts,
        n_stat_tests=base_tests,
        n_models=n_models,
        n_shap=n_shap,
        runtime_seconds=runtime,
        llm_cost_usd=cost,
    )
```

## File: `dashboard/components/cf_summary_panel.py`

```python
"""Sticky right-side Analysis Plan summary + Start Analysis CTA."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service
from dashboard.components.cf_pipeline_estimator import estimate
from domains.domain_registry import DOMAIN_REGISTRY


PROBLEM_DISPLAY = {
    "classification": ("🎯", "Classification"),
    "regression":     ("📈", "Regression"),
    "clustering":     ("🧩", "Clustering"),
    "timeseries":     ("⏱", "Time Series"),
    "survival":       ("⌛", "Survival"),
    "anomaly":        ("⚠️", "Anomaly Detection"),
    "auto":           ("🤖", "Auto"),
}
MODE_DISPLAY = {
    "auto":    ("⚡", "Auto",    "0 prompts · ~2 min"),
    "guided":  ("🎯", "Guided",  "~7 prompts · ~5 min"),
    "expert":  ("🛠", "Expert",  "~20 prompts · ~15 min"),
}
COMPLIANCE_KEYS = {"healthcare", "finance", "hr"}


def render(df: pd.DataFrame, on_start) -> None:
    """Render the sticky summary panel."""
    domain = st.session_state.get("cf_selected_domain", "generic")
    mode = st.session_state.get("cf_mode", "guided")
    problem = st.session_state.get("cf_problem_type", "auto")
    target = st.session_state.get("cf_target", "")
    goal = st.session_state.get("cf_goal_manual", "").strip() or st.session_state.get("cf_goal", "")
    excluded: set = st.session_state.get("cf_excluded", set())

    domain_cfg = DOMAIN_REGISTRY.get(domain, {})
    domain_label = f'{domain_cfg.get("icon", "📊")} {domain_cfg.get("display_name", domain.title())}'
    domain_conf = st.session_state.get("cf_domain_confidence", 0.94)

    mode_icon, mode_name, mode_meta = MODE_DISPLAY.get(mode, MODE_DISPLAY["guided"])
    problem_icon, problem_label = PROBLEM_DISPLAY.get(problem, ("🤖", "Auto"))
    is_compliance = domain in COMPLIANCE_KEYS

    n_rows = len(df) if df is not None else 0
    n_cols_kept = (len(df.columns) if df is not None else 0) - len(excluded)

    est = estimate(
        n_rows=n_rows, n_cols_kept=max(n_cols_kept, 1),
        mode=mode, problem_type=problem, domain_key=domain,
    )

    # Validation — Start button enabled only when minimums are met
    start_enabled = _validate_ready(domain, mode, problem, target, df)
    blocker = _blocker_message(domain, mode, problem, target, df)

    st.markdown(
        '<aside class="cf-summary">'
        '  <h3>Analysis <em>plan</em></h3>'
        '  <p class="cf-summary-tagline">Live preview of your configuration.</p>'
        f'{_row("Domain", f"{domain_label}<br/><span class=\\"cf-summary-pill cf-pill-conf\\">{int(domain_conf * 100)}% confident</span>")}'
        f'{_row("Mode", f"{mode_icon} {mode_name}<br/><span class=\\"cf-mono-sub\\">{mode_meta}</span>")}'
        f'{_row("Problem", f"{problem_icon} {problem_label}")}'
        f'{_row("Target", f"<span class=\\"cf-mono\\">{_html_escape(target) if target else "— None —"}</span>")}'
        f'{_row("Goal", f"<span class=\\"cf-summary-goal\\">{_html_escape(goal[:80] + ("…" if len(goal) > 80 else ""))}</span>")}'
        f'{_row("Excluded", _excluded_html(excluded))}'
        + (f'{_row("Compliance", "<span class=\\"cf-summary-pill cf-pill-comp\\">" + domain_label.split()[1] + "-aware</span>")}'
           if is_compliance else "")
        + '</aside>',
        unsafe_allow_html=True,
    )

    # Estimate block (rendered separately because it has dynamic numbers)
    st.markdown(
        f'<div class="cf-estimate-block">'
        f'  <div class="cf-estimate-title">Pipeline estimate</div>'
        f'  <div class="cf-estimate-row"><span class="l">Charts</span><span class="v">~{est.n_charts}</span></div>'
        f'  <div class="cf-estimate-row"><span class="l">Statistical tests</span><span class="v">~{est.n_stat_tests}</span></div>'
        f'  <div class="cf-estimate-row"><span class="l">Models trained</span><span class="v">{est.n_models}</span></div>'
        f'  <div class="cf-estimate-row"><span class="l">SHAP explanations</span><span class="v">{est.n_shap}</span></div>'
        f'  <div class="cf-estimate-row"><span class="l">Est. runtime</span><span class="v">{est.runtime_str}</span></div>'
        f'  <div class="cf-estimate-row"><span class="l">Est. LLM cost</span><span class="v">{est.cost_str}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not start_enabled and blocker:
        st.markdown(
            f'<div class="cf-blocker">⚠ {blocker}</div>',
            unsafe_allow_html=True,
        )

    if st.button("Start Analysis →", key="cf_start_btn",
                 use_container_width=True, type="primary", disabled=not start_enabled):
        on_start({
            "domain": domain, "mode": mode, "problem_type": problem,
            "target": target, "goal": goal,
            "excluded_columns": list(excluded),
        })


def _row(label: str, value: str) -> str:
    return (f'<div class="cf-summary-row">'
            f'  <span class="cf-summary-label">{label}</span>'
            f'  <span class="cf-summary-value">{value}</span>'
            f'</div>')


def _excluded_html(excluded: set) -> str:
    if not excluded:
        return '<span class="cf-mono-sub">None</span>'
    n = len(excluded)
    preview = " · ".join(list(excluded)[:3])
    if n > 3:
        preview += f" · +{n - 3} more"
    return (f'{n} column{"s" if n != 1 else ""}<br/>'
            f'<span class="cf-mono-sub">{_html_escape(preview)}</span>')


def _validate_ready(domain, mode, problem, target, df) -> bool:
    if df is None or df.empty:
        return False
    if not domain:
        return False
    if not mode:
        return False
    # Clustering / anomaly / explore can run unsupervised
    if problem in {"clustering", "anomaly"}:
        return True
    # All other problem types need a target
    return bool(target)


def _blocker_message(domain, mode, problem, target, df) -> str:
    if df is None or df.empty:
        return "No data loaded — return to Upload."
    if problem not in {"clustering", "anomaly"} and not target:
        return "Pick a target column to continue."
    return ""


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Summary panel (sticky right) ============ */
.cf-summary {
  position: sticky; top: 28px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 24px;
  backdrop-filter: blur(14px);
  height: fit-content; max-height: calc(100vh - 56px);
  overflow-y: auto;
}
.cf-summary::before {
  content: ""; display: block; width: 28px; height: 2px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%);
  border-radius: 2px; margin-bottom: 16px;
}
.cf-summary h3 {
  font-family: var(--font-display); font-size: 22px; margin-bottom: 4px;
}
.cf-summary h3 em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.cf-summary-tagline {
  font-size: 12.5px; color: var(--text-muted); margin-bottom: 22px;
}

.cf-summary-row {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 12px 0; border-bottom: 1px solid var(--border-subtle); gap: 12px;
}
.cf-summary-row:last-child { border-bottom: none; }
.cf-summary-label {
  font-family: var(--font-mono); font-size: 10px;
  color: var(--text-faint); letter-spacing: 0.8px;
  text-transform: uppercase; padding-top: 3px; flex-shrink: 0;
}
.cf-summary-value {
  font-size: 13px; color: var(--text-primary);
  text-align: right; line-height: 1.4;
}
.cf-summary-goal { font-size: 12.5px; }
.cf-summary-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border: 1px solid var(--border-subtle);
  border-radius: 999px; font-size: 11.5px; font-weight: 500;
  margin-top: 4px;
}
.cf-pill-conf {
  color: var(--green);
  border-color: rgba(52,211,153,0.3); background: rgba(52,211,153,0.08);
}
.cf-pill-comp {
  color: var(--cyan);
  border-color: rgba(34,211,238,0.3); background: rgba(34,211,238,0.08);
}
.cf-mono { font-family: var(--font-mono); font-size: 12.5px; }
.cf-mono-sub {
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted);
}

/* Estimate block */
.cf-estimate-block {
  margin-top: -6px; padding: 18px 20px;
  background: rgba(139,92,246,0.06);
  border: 1px solid var(--border-subtle);
  border-top: none;
  border-radius: 0 0 18px 18px;
  position: sticky; top: calc(100vh - 280px);
}
.cf-estimate-title {
  font-family: var(--font-mono); font-size: 10px;
  color: var(--text-faint); letter-spacing: 1px;
  text-transform: uppercase; margin-bottom: 10px;
}
.cf-estimate-row {
  display: flex; justify-content: space-between; gap: 8px;
  padding: 4px 0; font-size: 13px;
}
.cf-estimate-row .v {
  color: var(--text-primary); font-family: var(--font-mono); font-weight: 500;
}
.cf-estimate-row .l { color: var(--text-secondary); }

/* Blocker message */
.cf-blocker {
  margin-top: 14px; padding: 10px 14px;
  background: rgba(251,191,36,0.08);
  border: 1px solid rgba(251,191,36,0.3);
  border-radius: 10px;
  font-size: 12.5px; color: var(--amber);
}

/* Start Analysis primary CTA */
[data-testid="stMain"] .stButton > button[key="cf_start_btn"] {
  width: 100% !important; margin-top: 16px;
  padding: 14px 18px !important;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 12px !important;
  font-family: var(--font-body) !important; font-size: 14px !important; font-weight: 500 !important;
  cursor: pointer; box-shadow: 0 0 24px rgba(139,92,246,0.4) !important;
  transition: all 0.22s ease !important;
}
[data-testid="stMain"] .stButton > button[key="cf_start_btn"]:hover {
  transform: translateY(-1px); box-shadow: 0 0 32px rgba(139,92,246,0.6) !important;
}
[data-testid="stMain"] .stButton > button[key="cf_start_btn"]:disabled {
  opacity: 0.5 !important; cursor: not-allowed; box-shadow: none !important;
  transform: none !important;
}
```

## Implementation note

The estimator is intentionally heuristic — it should feel reasonable to users but doesn't need to be exact. If you want more accurate estimates later, instrument the actual pipeline runs to record (n_charts, n_models, runtime) and average them.

The "Start Analysis" button is the only validation gate. If validation fails, a yellow blocker message appears above the button explaining what's missing.
