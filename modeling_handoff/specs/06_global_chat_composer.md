# Spec 06 — Global Chat Composer + Configure-Phase Action Bar (Section 04)

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section 04:** `<div class="md-sec">` numbered **04** — "Anything else for *modeling?*"
**Action bar:** `<div class="md-action-bar">` near the bottom of phase 1
**Lines:** ~1452–1615

---

## What this section is

Two related components, both at the bottom of phase 1 (configure):

### A) Global chat composer
An open-ended text input where the user can give natural-language instructions about modeling that don't fit into the structured sections above. Examples: *"Optimize for recall, not accuracy"* / *"Only train tree-based models"* / *"Exclude any model with inference > 5ms"* / *"Add a stacked ensemble of the top 3"*.

The instruction is routed through `agents/followup_agent.py` with `intent="modify_modeling_plan"`. The follow-up agent interprets it and updates `state["modeling_config"]` in place. If the agent doesn't recognize the intent, we capture the raw user request to state and proceed (defensive fallback).

Below the composer: 4 quick-suggestion pills. Clicking a pill submits that exact text as the message.

### B) Configure-phase action bar
A sticky bottom strip showing:
- **Status text:** *"4 algorithms queued · stratified 5-fold · bayesian search · ETA ~3 min"*
- **Back to Features** (secondary button — navigates to `pages/04_feature_engineering.py`)
- **Start Training** (primary button — disabled when `len(selected_algorithms) == 0`; on click, switches phase to "results" and kicks off the training orchestrator from spec 07)

---

## Hard rules

1. **The composer is OPTIONAL.** Most users will never use it. The structured sections above are the primary interface. The composer is a power-user escape hatch.
2. **Never block the user.** If `followup_agent.handle()` raises, fails, or doesn't exist, capture the raw request to `state["modeling_config"]["custom_instructions"]` and proceed. Show a non-blocking toast: "Instruction noted — will be applied during training."
3. **Suggestion pills are static text shortcuts** — clicking pill X is exactly the same as typing X and pressing Enter.
4. **Start Training is disabled when zero algorithms selected.** Any other state lets the button fire.
5. **Action bar is sticky** at the bottom of the page. On scroll it stays visible.
6. **ETA estimation is a heuristic** — read formula below.

---

## Files to create

```
dashboard/components/
  md_global_chat.py               # Section 04 composer + suggestion pills
  md_action_bar_configure.py      # Configure-phase sticky action bar
  md_followup_adapter.py          # Thin shim around agents/followup_agent.handle()
```

No backend files modified.

---

## File 1 — `md_followup_adapter.py`

```python
"""
Adapter — wraps agents.followup_agent.handle() with a defensive fallback.
The follow-up agent may not yet support intent='modify_modeling_plan';
when that's the case, we capture the raw request to state and let the
training orchestrator interpret it later.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def submit_modeling_instruction(message: str, state: dict) -> dict:
    """
    Try to route the user's instruction through the follow-up agent.
    On any failure, store it as a custom instruction and return a graceful result.

    Returns:
      {
        "ok": bool,
        "message": str,        # what to show the user
        "applied_changes": dict | None,  # what state keys changed (if any)
      }
    """
    msg = (message or "").strip()
    if not msg:
        return {"ok": False, "message": "Empty instruction.", "applied_changes": None}

    # 1) Try the agent
    try:
        from agents import followup_agent  # noqa: F401
        if hasattr(followup_agent, "handle"):
            try:
                result = followup_agent.handle(
                    intent="modify_modeling_plan",
                    message=msg,
                    state=state,
                )
                if isinstance(result, dict) and result.get("ok"):
                    return {
                        "ok": True,
                        "message": result.get("message", "Instruction applied."),
                        "applied_changes": result.get("applied_changes"),
                    }
            except Exception as e:
                logger.warning(f"followup_agent.handle raised: {e}", exc_info=True)
    except ImportError:
        logger.info("followup_agent not importable; falling back to capture-only.")

    # 2) Fallback — capture the raw instruction
    state.setdefault("modeling_config", {})
    customs = state["modeling_config"].setdefault("custom_instructions", [])
    customs.append(msg)
    return {
        "ok": True,
        "message": "Instruction noted — will be applied during training.",
        "applied_changes": {"modeling_config.custom_instructions": customs},
    }
```

---

## File 2 — `md_global_chat.py`

```python
"""
Section 04 — Global chat composer for power-user instructions.
"""

import streamlit as st
from dashboard.components.md_followup_adapter import submit_modeling_instruction


CHAT_INPUT_KEY = "md_chat_input"
CHAT_SUBMIT_FLAG = "md_chat_submit_flag"
CHAT_LAST_RESPONSE = "md_chat_last_response"

SUGGESTION_PILLS = [
    "Optimize for recall, not accuracy",
    "Only train tree-based models",
    "Exclude any model with inference > 5ms",
    "Add a stacked ensemble of the top 3",
]


def render(state: dict, project_id: str) -> None:
    """Render section 04 in full."""
    st.markdown(
        """
        <div class="md-sec-head">
          <div class="md-sec-num">04</div>
          <div style="flex:1;">
            <div class="md-sec-title">Anything else for <em>modeling?</em></div>
            <div class="md-sec-meta">Open-ended instructions · routed through the follow-up agent</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if CHAT_INPUT_KEY not in st.session_state:
        st.session_state[CHAT_INPUT_KEY] = ""

    # Composer
    msg = st.text_area(
        label="Instruction",
        label_visibility="collapsed",
        placeholder="e.g. 'Optimize for recall, not accuracy' or 'Exclude SVMs'",
        height=80,
        key=f"md_chat_textarea_{project_id}",
    )

    submit_cols = st.columns([0.78, 0.22])
    with submit_cols[1]:
        submit = st.button(
            "Send →",
            key=f"md_chat_submit_{project_id}",
            type="secondary",
            use_container_width=True,
        )

    # Handle submission
    if submit and msg.strip():
        with st.spinner("Routing instruction…"):
            result = submit_modeling_instruction(msg, state)
        st.session_state[CHAT_LAST_RESPONSE] = result
        if result.get("ok"):
            st.toast(result.get("message", "Instruction applied."), icon="✓")
        else:
            st.toast(result.get("message", "Could not apply."), icon="⚠")
        st.rerun()

    # Last response banner (if any)
    last = st.session_state.get(CHAT_LAST_RESPONSE)
    if last and last.get("ok"):
        st.markdown(
            f"""
            <div class="md-chat-response">
              <span class="md-chat-response-icon">✓</span>
              {_escape(last.get("message", ""))}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Suggestion pills
    st.markdown("<div class='md-pill-row'>", unsafe_allow_html=True)
    pill_cols = st.columns(len(SUGGESTION_PILLS))
    for i, pill_text in enumerate(SUGGESTION_PILLS):
        with pill_cols[i]:
            if st.button(
                pill_text,
                key=f"md_pill_{project_id}_{i}",
                use_container_width=True,
            ):
                with st.spinner("Routing instruction…"):
                    result = submit_modeling_instruction(pill_text, state)
                st.session_state[CHAT_LAST_RESPONSE] = result
                if result.get("ok"):
                    st.toast(result.get("message", "Instruction applied."), icon="✓")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _escape(s: str) -> str:
    return (s or "").replace("<", "&lt;").replace(">", "&gt;")
```

---

## File 3 — `md_action_bar_configure.py`

```python
"""
Configure-phase sticky action bar.
Shows: status summary + Back to Features + Start Training.
"""

import streamlit as st


def render(state: dict, project_id: str, on_start_training) -> None:
    """
    Args:
      on_start_training: callable invoked when Start Training is clicked.
                         Receives state. Should switch phase to 'results' and
                         kick off the training orchestrator (see spec 07).
    """
    cfg = state.get("modeling_config", {})
    n_algos = len(cfg.get("selected_algorithms", []))
    val = cfg.get("validation", {})
    method = val.get("method", "stratified_kfold")

    # Pick the recommended search strategy as a representative summary
    strategies = cfg.get("search_strategy", {})
    if strategies:
        # Show "bayesian × N" if all the same, otherwise "mixed"
        unique = set(strategies.values())
        strat_summary = next(iter(unique)) if len(unique) == 1 else "mixed"
    else:
        strat_summary = "bayesian"

    eta_min = _estimate_eta_minutes(state)

    summary = _format_summary(n_algos, method, strat_summary, eta_min)

    st.markdown(
        f"""
        <div class="md-action-bar">
          <div class="md-action-status">{summary}</div>
          <div class="md-action-spacer"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Buttons (Streamlit doesn't render buttons inside arbitrary HTML, so
    # we render them as a column row right after the status strip)
    btn_cols = st.columns([0.55, 0.22, 0.23])
    with btn_cols[1]:
        if st.button("← Back to Features", key=f"md_back_btn_{project_id}", use_container_width=True):
            st.switch_page("pages/04_feature_engineering.py")
    with btn_cols[2]:
        disabled = (n_algos == 0)
        if st.button(
            "Start Training →",
            key=f"md_start_btn_{project_id}",
            type="primary",
            disabled=disabled,
            use_container_width=True,
            help="Select at least one algorithm in section 01" if disabled else None,
        ):
            on_start_training(state)


# ─── private ─────────────────────────────────────────────

def _format_summary(n_algos: int, method: str, strat: str, eta_min: float) -> str:
    if n_algos == 0:
        return "0 algorithms selected · pick at least one in section 01"

    method_display = {
        "holdout": "hold-out",
        "kfold": "K-fold",
        "stratified_kfold": "stratified 5-fold",
        "time_series_split": "time-series split",
        "group_kfold": "group K-fold",
        "repeated_stratified_kfold": "repeated stratified",
    }.get(method, method)

    strat_display = {
        "bayesian": "Bayesian search",
        "grid": "grid search",
        "random": "random search",
        "optuna": "Optuna",
        "exact": "exact (no search)",
        "mixed": "mixed strategies",
    }.get(strat, strat)

    eta_str = _format_eta(eta_min)
    return (
        f"<strong>{n_algos}</strong> algorithm{'s' if n_algos > 1 else ''} queued · "
        f"{method_display} · {strat_display} · "
        f"<span class='md-action-eta'>ETA ~{eta_str}</span>"
    )


def _estimate_eta_minutes(state: dict) -> float:
    """
    Heuristic ETA estimator.
    Per-algorithm cost = base_cost × n_rows_factor × n_features_factor × search_multiplier
    """
    cfg = state.get("modeling_config", {})
    profile = state.get("data_profile", {})
    n_rows = profile.get("n_rows", 1000)
    n_features = profile.get("n_features", 10)

    # Per-algo base cost in minutes (rough)
    BASE_COSTS = {
        "XGBoost": 0.4, "LightGBM": 0.3, "CatBoost": 0.5,
        "RandomForest": 0.3, "ExtraTrees": 0.3, "DecisionTree": 0.05,
        "LogisticRegression": 0.05, "RidgeClassifier": 0.05, "SGDClassifier": 0.05,
        "SVM-RBF": 1.0, "SVM-Linear": 0.3, "KNN": 0.2,
        "GaussianNB": 0.02, "BernoulliNB": 0.02, "QDA": 0.05,
        "MLP-Tabular": 1.5, "TabNet": 4.0, "FT-Transformer": 6.0,
        "VotingClassifier": 0.5, "StackingClassifier": 1.2, "BalancedRandomForest": 0.4,
        "HistGradientBoosting": 0.3,
    }

    n_rows_factor = max(1.0, n_rows / 10_000)
    n_features_factor = max(1.0, n_features / 30)

    search_strategies = cfg.get("search_strategy", {})
    total = 0.0
    for algo in cfg.get("selected_algorithms", []):
        base = BASE_COSTS.get(algo, 0.5)
        strat = search_strategies.get(algo, "bayesian")
        mult = {"bayesian": 4, "grid": 6, "random": 3, "optuna": 5, "exact": 1}.get(strat, 4)
        total += base * n_rows_factor * n_features_factor * mult
    return total


def _format_eta(minutes: float) -> str:
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m}m"
```

---

## CSS additions

Add to `shared_css.py`:

```css
.md-pill-row {
  display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px;
}

.md-chat-response {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; margin-top: 12px;
  background: rgba(34,211,238,0.06);
  border: 1px solid rgba(34,211,238,0.22);
  border-radius: 10px;
  font-size: 12.5px;
  color: var(--text-secondary);
}
.md-chat-response-icon { color: var(--cyan); font-size: 14px; }

.md-action-bar {
  position: sticky; bottom: 0; z-index: 50;
  display: flex; align-items: center; gap: 16px;
  padding: 14px 22px; margin-top: 28px;
  background: linear-gradient(180deg, rgba(7,9,26,0.92), rgba(7,9,26,0.98));
  border-top: 1px solid var(--border-default);
  backdrop-filter: blur(12px);
}
.md-action-status {
  flex: 1;
  font-family: var(--font-mono); font-size: 12px;
  color: var(--text-secondary);
}
.md-action-eta { color: var(--cyan); }
.md-action-spacer { flex: 0 0 auto; }
```

---

## Edge cases

| Case | Handling |
|---|---|
| `agents.followup_agent` doesn't exist (early dev) | Caught in import — falls back to custom_instructions capture. |
| `followup_agent.handle()` exists but doesn't accept `intent="modify_modeling_plan"` | `handle()` may raise NotImplementedError or return `{ok: False}`. Either way, falls back to custom_instructions. |
| User sends 50 instructions | All appended to `custom_instructions` list. No deduplication — duplicates may exist; the training orchestrator interprets the latest. |
| User clicks Start Training while text is in the composer | The text is ignored; only submitted instructions count. Composer text is NOT auto-submitted on Start. |
| User clicks Start Training without selecting an algorithm | Button is disabled; click does nothing. |
| `data_profile.n_rows` is missing or 0 | ETA uses 1000 as a floor — better to under-estimate than crash. |

---

## Acceptance criteria

- [ ] Composer renders with placeholder text and Send button
- [ ] Send button submits the message via `md_followup_adapter.submit_modeling_instruction`
- [ ] If the agent route succeeds, the response message is shown in a cyan banner
- [ ] If the agent route fails or doesn't exist, message is captured to `state["modeling_config"]["custom_instructions"]` (a list)
- [ ] Each suggestion pill submits its label as the message
- [ ] Action bar shows live status: "N algorithms queued · validation · search · ETA"
- [ ] Action bar is sticky at bottom
- [ ] Back to Features navigates correctly
- [ ] Start Training disabled when 0 algorithms; enabled otherwise
- [ ] Start Training fires the `on_start_training` callback (caller's responsibility — typically in the page integration spec 11)
- [ ] No modifications outside `dashboard/components/` and `shared_css.py`
