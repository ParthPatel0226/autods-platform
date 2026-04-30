# Spec 03 — Auto Mode Recommendation Cards

## Goal

When `analysis_mode == "auto"`, the EDA page does NOT show the full questions panel. Instead, it shows:

1. A **mode pill** indicating Auto mode
2. A compact **recommendations card** showing what AutoDS plans to run
3. Each recommendation has a per-row **Accept / Skip** toggle
4. An **"Accept all"** button at the top right
5. A free-text **"Got an idea?"** input below for users who want to add custom analyses

This keeps Auto mode hands-off while still being transparent about what's happening.

## File: `dashboard/components/ed_auto_recommendations.py`

```python
"""Auto mode — compact recommendations + free-text custom add."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service
from domains.domain_registry import DOMAIN_REGISTRY


# Heuristic: derive a default set of recommendations from the project's
# domain + problem type. This mirrors what eda_agent would auto-pick in
# Guided mode, but presented as a single accept/skip block.
def _recommendations_for(project) -> list[dict]:
    domain = project.confirmed_domain or project.detected_domain or "generic"
    problem = project.problem_type or "auto"

    base = [
        {"id": "dist", "name": "Distribution plots for all numeric columns",
         "detail": "Histograms · skewness · kurtosis", "default_on": True},
        {"id": "corr", "name": "Pearson correlation heatmap",
         "detail": "All numeric columns · target highlighted", "default_on": True},
        {"id": "box", "name": "Box plots for outlier detection",
         "detail": "Numeric columns · 1.5×IQR threshold", "default_on": True},
        {"id": "missing", "name": "Missing value patterns",
         "detail": "Heatmap + per-column missing %", "default_on": True},
    ]

    if problem in {"classification", "regression"}:
        base.append({"id": "target", "name": "Target distribution analysis",
                     "detail": "Class balance · density plots · cross-tabs", "default_on": True})
        base.append({"id": "ttest", "name": "T-tests / ANOVA for target relationships",
                     "detail": "All viable feature × target combos", "default_on": True})

    if domain == "healthcare":
        base.append({"id": "comorbidity", "name": "Charlson Comorbidity Index analysis",
                     "detail": "Domain-specific · Healthcare", "default_on": True})
        base.append({"id": "fairness", "name": "Demographic fairness check",
                     "detail": "Domain-specific · age × gender × race", "default_on": True})
    elif domain == "finance":
        base.append({"id": "vintage", "name": "Vintage / cohort analysis",
                     "detail": "Domain-specific · Finance", "default_on": True})
    elif domain == "ecommerce":
        base.append({"id": "rfm", "name": "RFM segmentation",
                     "detail": "Domain-specific · E-commerce", "default_on": True})

    return base


STATE_KEY = "ed_auto_accepted"
CUSTOM_KEY = "ed_auto_custom"


def render(on_run) -> None:
    """Render Auto mode recommendations + Run button. on_run(spec) is called when user runs."""
    project = project_service.get_active()
    if not project:
        return

    domain = project.confirmed_domain or project.detected_domain or "generic"
    domain_cfg = DOMAIN_REGISTRY.get(domain, {})

    # Mode pill
    st.markdown(
        f'<div class="ed-mode-pill">'
        f'  <span class="dot"></span>'
        f'  Auto Mode · {domain_cfg.get("display_name", domain.title())} context'
        f'</div>',
        unsafe_allow_html=True,
    )

    recommendations = _recommendations_for(project)

    # Initialize state — default-on items checked
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = {r["id"]: r["default_on"] for r in recommendations}
    accepted = st.session_state[STATE_KEY]

    # ---- recommendations card ----
    n_total = len(recommendations)
    n_accepted = sum(1 for v in accepted.values() if v)

    head_cols = st.columns([4, 1], gap="medium")
    with head_cols[0]:
        st.markdown(
            f'<div class="ed-auto-block-head">'
            f'  <h3 class="ed-auto-title">We\'ll run <em>{n_total} analyses</em> on your data.</h3>'
            f'  <p class="ed-auto-sub">Review or override individually. {n_accepted} of {n_total} currently accepted.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with head_cols[1]:
        if st.button("Accept all", key="ed_auto_accept_all", use_container_width=True):
            st.session_state[STATE_KEY] = {r["id"]: True for r in recommendations}
            st.rerun()

    st.markdown('<div class="ed-rec-list">', unsafe_allow_html=True)
    for rec in recommendations:
        rec_id = rec["id"]
        is_accepted = accepted.get(rec_id, False)

        st.markdown(
            f'<div class="ed-rec-item">'
            f'  <div class="ed-rec-text">'
            f'    <div class="ed-rec-name">{rec["name"]}</div>'
            f'    <div class="ed-rec-detail">{rec["detail"]}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Per-row Accept / Skip toggle
        toggle_cols = st.columns(2, gap="small")
        with toggle_cols[0]:
            if st.button("Accept", key=f"ed_rec_acc_{rec_id}",
                         use_container_width=True, disabled=is_accepted):
                accepted[rec_id] = True
                st.session_state[STATE_KEY] = accepted
                st.rerun()
        with toggle_cols[1]:
            if st.button("Skip", key=f"ed_rec_skip_{rec_id}",
                         use_container_width=True, disabled=not is_accepted):
                accepted[rec_id] = False
                st.session_state[STATE_KEY] = accepted
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Custom free-text add
    custom = st.text_input(
        "Got an idea? Add a custom analysis request",
        value=st.session_state.get(CUSTOM_KEY, ""),
        placeholder="e.g., distribution of length_of_stay split by gender, with a KS-test p-value",
        key="ed_auto_custom_input",
    )
    if custom != st.session_state.get(CUSTOM_KEY):
        st.session_state[CUSTOM_KEY] = custom

    # Run button
    cols = st.columns([3, 1], gap="medium")
    with cols[0]:
        runtime = max(45, n_accepted * 15) + 30
        m, s = divmod(runtime, 60)
        st.markdown(
            f'<div class="ed-actionbar-text">'
            f'  <strong>{n_accepted}</strong> of <strong>{n_total}</strong> analyses accepted · '
            f'  Estimated runtime: <strong>~{m} min {s}s</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        if st.button("Run Analysis ▶", key="ed_auto_run_btn", type="primary", use_container_width=True):
            spec = {
                "accepted_recommendations": [r["id"] for r in recommendations if accepted.get(r["id"])],
                "custom_request": custom.strip(),
            }
            on_run(spec)
```

## CSS additions

```css
/* ============ Auto mode block ============ */
.ed-auto-block-head { margin-bottom: 18px; }
.ed-auto-title {
  font-family: var(--font-display); font-size: 26px;
  line-height: 1.15; margin-bottom: 4px;
}
.ed-auto-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ed-auto-sub { font-size: 13px; color: var(--text-muted); }

[data-testid="stMain"] .stButton > button[key="ed_auto_accept_all"] {
  background: rgba(139,92,246,0.1) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: 999px !important;
  color: var(--violet) !important;
  font-size: 12px !important; font-weight: 500 !important;
  padding: 8px 16px !important;
  box-shadow: none !important;
}
[data-testid="stMain"] .stButton > button[key="ed_auto_accept_all"]:hover {
  background: rgba(139,92,246,0.18) !important;
}

.ed-rec-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; }
.ed-rec-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: rgba(139,92,246,0.04);
  border: 1px solid var(--border-subtle); border-radius: 10px;
}
.ed-rec-text { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.ed-rec-name { font-size: 13.5px; color: var(--text-primary); }
.ed-rec-detail { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted); }

/* Per-row Accept/Skip buttons restyled */
[data-testid="stMain"] .stButton > button[key^="ed_rec_acc_"],
[data-testid="stMain"] .stButton > button[key^="ed_rec_skip_"] {
  padding: 5px 14px !important;
  background: rgba(7,9,26,0.4) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 8px !important;
  color: var(--text-muted) !important;
  font-size: 11px !important; font-weight: 500 !important;
  box-shadow: none !important;
}
[data-testid="stMain"] .stButton > button[key^="ed_rec_acc_"]:disabled,
[data-testid="stMain"] .stButton > button[key^="ed_rec_skip_"]:disabled {
  background: linear-gradient(135deg, var(--indigo) 0%, var(--purple) 100%) !important;
  color: white !important;
  border-color: var(--violet) !important;
  opacity: 1 !important;
  box-shadow: 0 0 8px rgba(139,92,246,0.4) !important;
}
```

## Implementation note

- The "default-on" recommendations are conservative — distribution / correlation / box / missing for everyone, target-related additions for supervised problems, and one or two domain-specific recommendations.
- The recommendations list is generated locally rather than calling the agent. If you'd rather have the agent generate them, expose a new helper in `agents/eda_agent.py` named `auto_recommendations(state) -> list[dict]` and import it here.
- The Run button submits both the accepted list and the custom request — the page integration (spec 07) wires this to `eda_agent.run_analyses(...)`.
