# Spec 04 — Prediction History + API Deployment Snippet

## File: `dashboard/components/pr_prediction_history.py`

```python
"""Recent single predictions strip."""
from __future__ import annotations
import streamlit as st

HISTORY_KEY = "pr_prediction_history"


def add_to_history(prediction: float, label: str, feature_summary: str) -> None:
    """Add a prediction to the history strip (max 10)."""
    history = st.session_state.get(HISTORY_KEY, [])
    history.insert(0, {
        "prediction": prediction,
        "label": label,
        "summary": feature_summary,
    })
    st.session_state[HISTORY_KEY] = history[:10]


def render() -> None:
    """Render the horizontal history strip."""
    history = st.session_state.get(HISTORY_KEY, [])
    if not history:
        return

    st.markdown(
        '<div class="pr-history">'
        '  <div class="pr-history-title">Recent predictions</div>'
        '  <div class="pr-history-strip">',
        unsafe_allow_html=True,
    )

    for i, item in enumerate(history):
        pct = int(item["prediction"] * 100) if item["prediction"] <= 1 else int(item["prediction"])
        if pct > 60:
            color, icon = "var(--red)", "⚠"
        elif pct > 35:
            color, icon = "var(--amber)", "⚡"
        else:
            color, icon = "var(--green)", "✓"

        st.markdown(
            f'<div class="pr-history-item">'
            f'  <div class="pr-history-pct" style="color:{color};">{icon} {pct}%</div>'
            f'  <div class="pr-history-summary">{_html_escape(item["summary"][:40])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div></div>', unsafe_allow_html=True)


def _html_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## File: `dashboard/components/pr_api_snippet.py`

```python
"""API deployment snippet card — curl/Python code for the FastAPI endpoint."""
from __future__ import annotations
import json
import streamlit as st

from dashboard.components import project_service


def render(feature_names: list[str]) -> None:
    """Render the API deployment snippet card."""
    project = project_service.get_active()
    if not project:
        return

    sample_payload = {feat: 0 for feat in feature_names[:5]}
    payload_json = json.dumps(sample_payload, indent=2)

    curl_snippet = (
        f'curl -X POST http://localhost:8000/predict \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -d \'{json.dumps({"features": sample_payload})}\''
    )

    python_snippet = (
        f'import requests\n\n'
        f'response = requests.post(\n'
        f'    "http://localhost:8000/predict",\n'
        f'    json={{"features": {payload_json}}}\n'
        f')\n'
        f'print(response.json())\n'
        f'# {{"prediction": 0.84, "class": "high_risk", "shap_values": [...]}}'
    )

    st.markdown(
        '<div class="pr-api-card">'
        '  <div class="pr-api-header">'
        '    <div>'
        '      <h4 class="pr-api-title">🚀 Deploy this model</h4>'
        '      <p class="pr-api-sub">AutoDS generated a FastAPI endpoint at <code>serving/api.py</code>. '
        '         Run it locally or deploy to any cloud.</p>'
        '    </div>'
        '    <div class="pr-api-status">'
        '      <span class="pr-api-dot"></span> Ready to deploy'
        '    </div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_curl, tab_python, tab_docker = st.tabs(["curl", "Python", "Docker"])
    with tab_curl:
        st.code(curl_snippet, language="bash")
    with tab_python:
        st.code(python_snippet, language="python")
    with tab_docker:
        st.code(
            "# Build and run\n"
            "docker build -t autods-predict -f serving/Dockerfile .\n"
            "docker run -p 8000:8000 autods-predict\n\n"
            "# Endpoints:\n"
            "# POST /predict        — single prediction\n"
            "# POST /predict/batch  — batch predictions\n"
            "# GET  /health         — health check\n"
            "# GET  /info           — model info + features",
            language="bash"
        )
```

## CSS additions

```css
/* ============ Prediction history ============ */
.pr-history { margin: 28px 0; }
.pr-history-title { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; }
.pr-history-strip { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 6px; }
.pr-history-item { flex-shrink: 0; padding: 10px 16px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 10px; min-width: 120px; backdrop-filter: blur(14px); }
.pr-history-pct { font-family: var(--font-display); font-size: 20px; margin-bottom: 2px; }
.pr-history-summary { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ============ API snippet card ============ */
.pr-api-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 22px; margin: 28px 0; backdrop-filter: blur(14px); }
.pr-api-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; }
.pr-api-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.pr-api-sub { font-size: 12.5px; color: var(--text-muted); }
.pr-api-sub code { font-family: var(--font-mono); font-size: 11px; color: var(--violet);
  padding: 1px 5px; background: rgba(139,92,246,0.08); border-radius: 4px; }
.pr-api-status { display: flex; align-items: center; gap: 6px;
  font-family: var(--font-mono); font-size: 11px; color: var(--green);
  padding: 4px 12px; background: rgba(52,211,153,0.08);
  border: 1px solid rgba(52,211,153,0.3); border-radius: 999px; white-space: nowrap; }
.pr-api-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green);
  box-shadow: 0 0 6px var(--green); }
```
