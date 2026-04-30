# Spec 08 — Chat Composer + Action Bar

## Same pattern as EDA/FE tabs. Abbreviated spec.

## File: `dashboard/components/ex_chat_composer.py`

Same pattern as `ed_chat_composer.py` from the EDA handoff, but with explainability-specific suggestions:

```python
SUGGESTIONS = [
    {"icon": "📊", "label": "PDP for top feature",
     "prompt": "Show partial dependence plot for the most important SHAP feature"},
    {"icon": "👥", "label": "Compare groups",
     "prompt": "Compare predictions between male and female patients"},
    {"icon": "📈", "label": "ICE plots",
     "prompt": "Show Individual Conditional Expectation plots for age"},
    {"icon": "🛡", "label": "Adversarial check",
     "prompt": "Run adversarial robustness check on the top 5 features"},
]
INPUT_KEY = "ex_chat_input"
```

All other logic identical to `ed_chat_composer.py`. The `on_submit` callback wires to `agents/explainability_agent` or `agents/followup_agent`.

## File: `dashboard/components/ex_action_bar.py`

```python
"""Bottom action bar for explainability — Continue to Predict + summary."""
from __future__ import annotations
import streamlit as st
from dashboard.components import project_service


def render(on_continue, on_export_report, on_export_card) -> None:
    cols = st.columns([1.4, 1], gap="medium")

    with cols[0]:
        st.markdown('<div class="ex-action-card"><h4>Next steps</h4></div>',
                    unsafe_allow_html=True)
        if st.button("Continue to Predict →", key="ex_continue",
                     type="primary", use_container_width=True):
            on_continue()
        if st.button("⬇ Export explainability report", key="ex_export_report",
                     use_container_width=True):
            on_export_report()
        if st.button("📋 Download model card as PDF", key="ex_export_card",
                     use_container_width=True):
            on_export_card()

    with cols[1]:
        shap_n = st.session_state.get("ex_shap_n_samples", 500)
        n_interactions = st.session_state.get("ex_n_interactions", 0)
        n_cf = st.session_state.get("ex_n_counterfactuals", 0)
        n_fair_attrs = st.session_state.get("ex_n_fair_attrs", 0)
        runtime = st.session_state.get("ex_runtime_str", "—")
        cost = st.session_state.get("ex_cost_str", "—")

        st.markdown(
            f'<div class="ex-action-card ex-action-summary">'
            f'  <h4>Explainability summary</h4>'
            f'  <div class="ex-run-summary">'
            f'    <div>SHAP computed for {shap_n} samples</div>'
            f'    <div>{n_interactions} feature interactions analyzed</div>'
            f'    <div>{n_cf} counterfactuals generated</div>'
            f'    <div>Fairness audit: {n_fair_attrs} attributes</div>'
            f'    <div>Model card: auto-generated</div>'
            f'    <div>Runtime: {runtime}</div>'
            f'    <div>LLM cost: {cost}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
```

## CSS additions

```css
/* ============ Chat composer (explainability) ============ */
.ex-chat { background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(168,85,247,0.04));
  border: 1px solid var(--border-default); border-radius: 18px;
  padding: 22px 24px; margin: 28px 0; backdrop-filter: blur(14px);
  position: relative; overflow: hidden; }
.ex-chat::before { content: ""; position: absolute; left: -30px; top: -30px;
  width: 180px; height: 180px;
  background: radial-gradient(circle, rgba(168,85,247,0.18), transparent 60%);
  pointer-events: none; }
.ex-chat-head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.ex-chat-head svg { width: 18px; height: 18px; color: var(--violet); }
.ex-chat-title { font-family: var(--font-display); font-size: 22px; }
.ex-chat-title em { font-style: italic; background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.ex-chat-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }
.ex-chat-suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; align-items: center; }
.ex-chat-sug-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1px;
  text-transform: uppercase; color: var(--text-faint); margin-right: 4px; }
.ex-chat-sug { padding: 6px 12px; background: var(--bg-card);
  border: 1px solid var(--border-subtle); border-radius: 999px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer; transition: all 0.18s ease; }
.ex-chat-sug:hover { border-color: var(--violet); color: var(--text-primary); transform: translateY(-1px); }

/* ============ Bottom action bar ============ */
.ex-action-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; backdrop-filter: blur(14px); }
.ex-action-card h4 { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.2px;
  text-transform: uppercase; color: var(--text-faint); margin-bottom: 10px; }
.ex-action-summary { background: rgba(139,92,246,0.04) !important; border-style: dashed !important; }
.ex-action-summary h4 { color: var(--violet) !important; }
.ex-run-summary { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); line-height: 1.6; }

[data-testid="stMain"] .stButton > button[key="ex_continue"] {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 10px !important;
  padding: 12px 16px !important; font-size: 14px !important; font-weight: 500 !important;
  box-shadow: 0 0 20px rgba(139,92,246,0.4) !important; margin-bottom: 8px; }
[data-testid="stMain"] .stButton > button[key="ex_continue"]:hover {
  transform: translateY(-1px); box-shadow: 0 0 28px rgba(139,92,246,0.6) !important; }
[data-testid="stMain"] .stButton > button[key="ex_export_report"],
[data-testid="stMain"] .stButton > button[key="ex_export_card"] {
  background: transparent !important; color: var(--text-secondary) !important;
  border: 1px solid var(--border-default) !important; border-radius: 10px !important;
  padding: 10px 16px !important; font-size: 13px !important; margin-top: 8px; }
```
