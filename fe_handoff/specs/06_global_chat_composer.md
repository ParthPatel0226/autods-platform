# Spec 06 — Global FE Chat Composer & Sticky Action Bar

## Layout

The global chat composer renders at the **bottom of Section 04**, before the action bar. Visually similar to the scoped composer in Section 02 but with a different headline + 4 suggestion pills + scoped to the entire FE plan.

```
[Section 04: Interaction features]
  [Interaction toggle cards]
  [── Global FE chat composer ──]
  [eyebrow "Ask anything about this plan"]
  [Headline "Anything else for *feature engineering?*"]
  [Subtitle]
  [Input + Send button]
  [4 suggestion pills]
[/Section 04]

[Sticky action bar: status text + Back to EDA + Review & Approve →]
```

## File: `dashboard/components/fe_global_chat.py`

```python
"""Global Feature Engineering chat composer.

This is the OPEN-ENDED chat that operates on the entire FE plan.
Distinct from `fe_domain_features._render_scoped_composer` (Section 02) which
only adds new domain-style features.

Sending a message routes through `agents.followup_agent.handle(intent="modify_fe_plan",...)`
which interprets the request and updates `st.session_state["fe_choices"]`,
`fe_domain_choices`, `fe_interaction_choices`, or `fe_custom_features` accordingly.
"""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service


SUGGESTIONS = [
    "Try KNN imputation everywhere",
    "Add polynomial features for Age & Fare",
    "Use one-hot for all categoricals",
    "Drop columns with >50% missing",
]


def render() -> None:
    """Render the global chat composer at the bottom of Section 04.

    The page (Spec 08) inserts this BEFORE closing the Section 04 `<div class="fe-sec">`,
    so the composer visually sits inside the same card as the interaction features.
    """
    st.markdown(
        '<div class="fe-ai-composer fe-ai-composer-global">'
        '  <div class="fe-ai-head">'
        '    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        '    Ask anything about this plan'
        '  </div>'
        '  <div class="fe-ai-title">Anything else for <em>feature engineering?</em></div>'
        '  <div class="fe-ai-sub">Describe any change in plain English — column-level, domain features, scaling strategy, drops. AutoDS will update the plan and you can review before approving.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([6, 1])
    with cols[0]:
        prompt = st.text_input(
            "Global FE prompt",
            key="fe_global_prompt",
            placeholder='e.g., "use KNN imputation for all numeric columns" or "drop columns with >50% missing"',
            label_visibility="collapsed",
        )
    with cols[1]:
        if st.button("Send", key="fe_global_send", use_container_width=True):
            if prompt:
                _route_global_request(prompt)

    # Suggestion pills row
    st.markdown('<div class="fe-suggestion-row">', unsafe_allow_html=True)
    sug_cols = st.columns(len(SUGGESTIONS), gap="small")
    for col, sug in zip(sug_cols, SUGGESTIONS):
        with col:
            if st.button(f"↗ {sug}", key=f"fe_sug_{sug}", use_container_width=True):
                _route_global_request(sug)
    st.markdown('</div>', unsafe_allow_html=True)


def _route_global_request(prompt: str) -> None:
    """Send the prompt to the followup agent and apply the resulting plan diff."""
    project = project_service.get_active()
    try:
        from agents.followup_agent import handle as followup_handle
        result = followup_handle(
            intent="modify_fe_plan",
            prompt=prompt,
            project=project,
            current_choices={
                "per_column": st.session_state.get("fe_choices", {}),
                "domain": st.session_state.get("fe_domain_choices", {}),
                "interactions": st.session_state.get("fe_interaction_choices", {}),
                "custom": st.session_state.get("fe_custom_features", []),
            },
        )
        if not result:
            st.warning("No update produced from your request. Try rephrasing.")
            return

        # Apply diff
        diff = result.get("diff", {})
        applied = []
        if "per_column" in diff:
            st.session_state.setdefault("fe_choices", {}).update(diff["per_column"])
            applied.append(f"{len(diff['per_column'])} column decisions")
        if "domain" in diff:
            st.session_state.setdefault("fe_domain_choices", {}).update(diff["domain"])
            applied.append(f"{len(diff['domain'])} domain features")
        if "interactions" in diff:
            st.session_state.setdefault("fe_interaction_choices", {}).update(diff["interactions"])
            applied.append(f"{len(diff['interactions'])} interactions")
        if "custom" in diff:
            for new_feat in diff["custom"]:
                st.session_state.setdefault("fe_custom_features", []).append(new_feat)
            applied.append(f"{len(diff['custom'])} custom features")

        if applied:
            st.success(f"Plan updated: {', '.join(applied)}")
            st.rerun()
        else:
            st.info(result.get("message", "Plan unchanged."))
    except Exception as e:
        st.warning(f"AI plan update unavailable: {e}")
```

## File: `dashboard/components/fe_action_bar.py`

```python
"""Sticky action bar at the bottom of the Configure phase."""
from __future__ import annotations
import streamlit as st

from dashboard.components import project_service, fe_phase_router


def render() -> None:
    df = st.session_state.get("df")
    fe_choices = st.session_state.get("fe_choices", {})
    fe_domain = st.session_state.get("fe_domain_choices", {})
    fe_interact = st.session_state.get("fe_interaction_choices", {})
    fe_custom = st.session_state.get("fe_custom_features", [])

    n_cols = 0 if df is None else len(df.columns)
    n_configured = sum(1 for c, ch in fe_choices.items()
                       if ch.get("action") == "drop" or any(
                           ch.get(k) and ch.get(k) != "none" for k in
                           ("imputation", "encoding", "scaling", "outliers")))

    n_new = sum(1 for v in fe_domain.values() if v) \
          + sum(1 for v in fe_interact.values() if v) \
          + len(fe_custom)

    estimate = _estimate_runtime(n_configured, n_new)

    st.markdown(
        f'<div class="fe-action-bar">'
        f'  <div class="fe-action-status">'
        f'    <strong>{n_configured} of {n_cols}</strong> columns configured · '
        f'<strong>{n_new}</strong> new features queued · '
        f'estimated runtime {estimate}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([6, 1, 1.2])
    with cols[1]:
        if st.button("← Back to EDA", key="fe_back_eda", use_container_width=True):
            from streamlit import switch_page
            try:
                switch_page("pages/03_eda_interactive.py")
            except Exception:
                pass
    with cols[2]:
        if st.button("Review & Approve →", key="fe_to_review",
                     type="primary", use_container_width=True):
            fe_phase_router.set_phase("review")
            st.rerun()


def _estimate_runtime(n_configured: int, n_new: int) -> str:
    seconds = max(15, n_configured * 2 + n_new * 4)
    if seconds < 60:
        return f"~{seconds}s"
    m, s = divmod(seconds, 60)
    return f"~{m}m {s}s"
```

## CSS additions

```css
/* Global composer variant */
.fe-ai-composer-global {
  margin-top: 18px;
}

/* Suggestion pills row */
.fe-suggestion-row {
  display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;
}
.fe-suggestion-row [data-testid="stButton"] > button {
  padding: 7px 12px; border-radius: 999px;
  background: rgba(139,92,246,0.08);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-secondary); letter-spacing: 0.4px;
}
.fe-suggestion-row [data-testid="stButton"] > button:hover {
  background: rgba(139,92,246,0.15); color: var(--text-primary);
  border-color: var(--border-default);
}

/* Sticky action bar */
.fe-action-bar {
  position: sticky; bottom: 18px;
  margin-top: 28px;
  display: flex; align-items: center; gap: 14px;
  padding: 14px 20px;
  background: var(--bg-card-strong);
  border: 1px solid var(--border-default); border-radius: 14px;
  backdrop-filter: blur(18px);
  box-shadow: 0 8px 30px -10px rgba(0,0,0,0.4);
  z-index: 5;
}
.fe-action-status {
  flex: 1; font-size: 12.5px; color: var(--text-secondary);
  font-family: var(--font-mono); letter-spacing: 0.4px;
}
.fe-action-status strong { color: var(--text-primary); font-weight: 500; }
```

## Followup agent contract

The global chat composer assumes `agents.followup_agent.handle(intent="modify_fe_plan", ...)` returns a dict like:

```python
{
    "diff": {
        "per_column": {"col_name": {"imputation": "knn", ...}, ...},
        "domain": {"feature_name": True, ...},
        "interactions": {"name": True, ...},
        "custom": [{"name": "...", "expression": "..."}, ...]
    },
    "message": "Optional human-readable summary",
}
```

If the agent doesn't support the `modify_fe_plan` intent yet, the try/except in `_route_global_request` catches the failure and shows a graceful warning. Do **not** modify the agent — coordinate the contract change with the backend owner separately.
