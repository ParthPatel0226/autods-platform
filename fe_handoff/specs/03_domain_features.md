# Spec 03 — Domain-Specific Features (Section 02)

## Layout

```
[Section header: "02 · Domain-specific features"]
[Tip strip]
[Stack of feature cards — each with toggle switch + description + requirement status]
[Scoped AI composer: "Ask AI to add a feature"]
```

## File: `dashboard/components/fe_domain_features.py`

```python
"""Domain-specific feature toggle cards + scoped AI composer.

Reads `domains/<domain>.py.feature_questions` (or `feature_options`)
and renders one card per feature with a toggle switch.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    df: pd.DataFrame | None = st.session_state.get("df")
    if not project or df is None:
        return

    domain_key = project.confirmed_domain or "generic"
    domain_features = _load_domain_features(domain_key)
    domain_icon = {
        "healthcare": "🏥", "finance": "💰", "ecommerce": "🛒",
        "marketing": "📣", "hr": "👥", "manufacturing": "🏭",
        "generic": "✦",
    }.get(domain_key, "✦")

    fe_domain_choices = st.session_state.setdefault("fe_domain_choices", {})

    st.markdown(
        f'<div class="fe-sec">'
        f'  <div class="fe-sec-head">'
        f'    <div class="fe-sec-num">02</div>'
        f'    <div style="flex:1;">'
        f'      <div class="fe-sec-title">Domain-specific <em>features</em></div>'
        f'      <div class="fe-sec-meta">{domain_icon} {domain_key.capitalize()} · auto-detected from your domain config</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="fe-sec-tip">'
        f'    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="2" x2="12" y2="6"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="18" x2="12" y2="22"/></svg>'
        f'    Validated {domain_key} features that improve model performance. Toggle off any you don\'t need.'
        f'  </div>',
        unsafe_allow_html=True,
    )

    if not domain_features:
        st.markdown(
            '<div class="fe-reasoning">No domain-specific features defined for this domain. Use the AI composer below to request custom features.</div>',
            unsafe_allow_html=True,
        )
    else:
        for feat in domain_features:
            _render_feature_card(feat, df, fe_domain_choices)

    # Scoped AI composer
    _render_scoped_composer()

    st.markdown('</div>', unsafe_allow_html=True)


def _load_domain_features(domain_key: str) -> list[dict]:
    """Load `feature_questions` (or `feature_options`) from domains/<domain>.py.

    Each entry should have:
      - name (str): column name to be created
      - description (str): one-line plain English
      - required_columns (list[str] | callable): columns this feature needs
      - default_on (bool): whether to enable by default
      - reason (str, optional): "★ suggested · domain knowledge" pill text

    If the actual domain module exports a different shape, write an adapter here
    rather than modifying the domain file.
    """
    try:
        import importlib
        mod = importlib.import_module(f"domains.{domain_key}")
        # Try common attribute names in order
        for attr in ("feature_questions", "feature_options", "FEATURES"):
            features = getattr(mod, attr, None)
            if features:
                return list(features)
    except Exception:
        pass
    return []


def _render_feature_card(feat: dict, df: pd.DataFrame, choices: dict) -> None:
    name = feat.get("name", "unnamed_feature")
    desc = feat.get("description", "")
    required = feat.get("required_columns", []) or []
    default_on = feat.get("default_on", True)
    reason = feat.get("reason", "")

    # Resolve callable required_columns
    if callable(required):
        try:
            required = list(required(df) or [])
        except Exception:
            required = []

    cols_present = [c for c in required if c in df.columns]
    cols_missing = [c for c in required if c not in df.columns]
    requirements_met = len(cols_missing) == 0

    # Initialize toggle state
    if name not in choices:
        choices[name] = default_on if requirements_met else False

    is_on = choices.get(name, False) and requirements_met
    disabled_class = " disabled" if not requirements_met else ""

    if requirements_met:
        if cols_present:
            req_text = f"requires {' + '.join(cols_present)} · detected"
        else:
            req_text = "no specific column requirements"
        req_class = "met"
    else:
        req_text = f"requires {' + '.join(cols_missing) or 'columns not found'} · not found"
        req_class = "missing"

    # Render card HTML + Streamlit toggle button
    st.markdown(
        f'<div class="fe-feat{disabled_class}">'
        f'  <div class="fe-feat-left">'
        f'    <div class="fe-feat-name">{_html_escape(name)}</div>'
        f'    <div class="fe-feat-desc">{_html_escape(desc)}</div>'
        f'    <div class="fe-feat-req {req_class}">{_html_escape(req_text)}</div>'
        f'  </div>'
        f'  <div class="fe-feat-toggle-slot" data-feat="{_html_escape(name)}"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Streamlit toggle (it cannot be embedded into the HTML — render below it,
    # CSS is responsible for visually placing it inside the slot)
    cols = st.columns([10, 1])
    with cols[1]:
        new_state = st.checkbox(
            "Enable",
            value=is_on,
            key=f"fe_feat_{name}",
            disabled=not requirements_met,
            label_visibility="collapsed",
        )
        if new_state != is_on:
            choices[name] = new_state
            st.rerun()


def _render_scoped_composer() -> None:
    """The smaller AI composer SCOPED to adding domain features.

    This is different from the global FE chat (Section 04). This one is scoped:
    "Add a feature" within the domain context.
    """
    st.markdown(
        '<div class="fe-ai-composer">'
        '  <div class="fe-ai-head">'
        '    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        '    Custom request'
        '  </div>'
        '  <div class="fe-ai-title">Ask AI to add a <em>feature.</em></div>'
        '  <div class="fe-ai-sub">Describe what you want — AutoDS proposes the derived column and adds it to your pipeline.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns([6, 1])
    with cols[0]:
        prompt = st.text_input(
            "Custom feature prompt",
            key="fe_domain_ai_prompt",
            placeholder='e.g., "flag first-class women" or "combine Age and Pclass"',
            label_visibility="collapsed",
        )
    with cols[1]:
        if st.button("Generate", key="fe_domain_ai_send", use_container_width=True):
            if prompt:
                _route_domain_ai_request(prompt)


def _route_domain_ai_request(prompt: str) -> None:
    """Route through followup_agent or local fallback."""
    try:
        from agents.followup_agent import handle as followup_handle
        result = followup_handle(intent="add_domain_feature", prompt=prompt,
                                 project=project_service.get_active())
        if result and isinstance(result, dict):
            st.session_state.setdefault("fe_custom_features", []).append(result)
            st.success(f"Added: {result.get('name', 'new feature')}")
            st.rerun()
    except Exception as e:
        st.warning(f"AI feature generation unavailable: {e}")


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* Feature cards */
.fe-feat {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; padding: 16px 18px;
  background: rgba(7,9,26,0.4);
  border: 1px solid var(--border-subtle); border-radius: 12px;
  margin-bottom: 10px; transition: all 0.18s ease;
}
[data-theme="light"] .fe-feat { background: rgba(255,255,255,0.55); }
.fe-feat:hover { border-color: var(--border-default); }
.fe-feat.disabled { opacity: 0.55; }
.fe-feat-left { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.fe-feat-name {
  font-family: var(--font-mono); font-size: 13px; font-weight: 500;
  color: var(--text-primary);
}
.fe-feat-desc { font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; }
.fe-feat-req {
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 4px;
  font-family: var(--font-mono); font-size: 10.5px;
  letter-spacing: 0.4px;
}
.fe-feat-req::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.fe-feat-req.met { color: var(--green); }
.fe-feat-req.missing { color: var(--amber); }

/* AI composer (scoped — used inside Section 02 + Section 04 global) */
.fe-ai-composer {
  margin-top: 16px; padding: 18px 20px;
  background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(99,102,241,0.06));
  border: 1px solid rgba(139,92,246,0.25); border-radius: 14px;
}
.fe-ai-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
  font-family: var(--font-mono); font-size: 11px;
  color: var(--violet); letter-spacing: 0.6px; text-transform: uppercase;
}
.fe-ai-head svg { width: 14px; height: 14px; }
.fe-ai-title {
  font-family: var(--font-display); font-size: 20px;
  color: var(--text-primary); margin: 4px 0 4px;
}
.fe-ai-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.fe-ai-sub { font-size: 12.5px; color: var(--text-muted); margin-bottom: 14px; }
```

## Adapter note

If `domains/<domain>.py` exports `feature_questions` in a different shape (e.g., an LLM prompt list rather than feature definitions), write an adapter at `dashboard/components/fe_domain_adapter.py` to normalize it. Do **not** modify the domain module.
