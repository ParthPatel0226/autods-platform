# Spec 02 — Download Tab (page 09_download.py)

## Backend reuse

- `reports/generators/html_report.py` (340 lines) — `generate_html_report(state) -> path`
- `reports/generators/pdf_report.py` (157 lines) — `generate_pdf_report(state) -> path`
- `reports/generators/executive_summary.py` (248 lines) — `generate_executive_summary(state) -> path`
- `reports/generators/notebook_export.py` (482 lines) — `generate_notebook(state) -> path`
- `reports/generators/zip_packager.py` (124 lines) — `package_all(state) -> path`
- `session/session_export.py` (163 lines) — `export_session(session_id) -> json_path`
- `logging_audit/decision_log.py` + `logging_audit/audit_trail_export.py`

**Open each first** to confirm API signatures.

## File Plan

```
dashboard/components/dl_report_cards.py        # 5 report download cards grid
dashboard/components/dl_data_exports.py        # Data + model + deployment exports
dashboard/components/dl_audit_trail.py         # Decision + pipeline log exports
dashboard/pages/09_download.py                 # Full rewrite
```

## File: `dashboard/components/dl_report_cards.py`

```python
"""5 report download cards in a grid."""
from __future__ import annotations
import streamlit as st


REPORTS = [
    {
        "key": "html",
        "icon": "🌐",
        "title": "Interactive HTML Report",
        "desc": "Full interactive report with Plotly charts, filterable tables, and drill-down sections.",
        "size": "~2-5 MB",
        "generator": "reports.generators.html_report.generate_html_report",
        "filename": "autods_report.html",
        "mime": "text/html",
    },
    {
        "key": "pdf",
        "icon": "📄",
        "title": "PDF Report",
        "desc": "Print-ready PDF with all charts, tables, and findings. Share with stakeholders.",
        "size": "~1-3 MB",
        "generator": "reports.generators.pdf_report.generate_pdf_report",
        "filename": "autods_report.pdf",
        "mime": "application/pdf",
    },
    {
        "key": "exec",
        "icon": "📊",
        "title": "Executive Summary",
        "desc": "One-page executive PDF with key metrics, top insights, and recommendations.",
        "size": "~500 KB",
        "generator": "reports.generators.executive_summary.generate_executive_summary",
        "filename": "autods_executive_summary.pdf",
        "mime": "application/pdf",
    },
    {
        "key": "notebook",
        "icon": "📓",
        "title": "Jupyter Notebook",
        "desc": "Fully runnable notebook with all code, visualizations, and markdown narrative.",
        "size": "~1-2 MB",
        "generator": "reports.generators.notebook_export.generate_notebook",
        "filename": "autods_analysis.ipynb",
        "mime": "application/x-ipynb+json",
    },
    {
        "key": "zip",
        "icon": "📦",
        "title": "Complete ZIP Package",
        "desc": "Everything in one download: reports, data, model, notebook, config, audit trail.",
        "size": "~10-50 MB",
        "generator": "reports.generators.zip_packager.package_all",
        "filename": "autods_package.zip",
        "mime": "application/zip",
    },
]


def render() -> None:
    st.markdown(
        '<div class="dl-sec-header">'
        '<h3 style="font-family:var(--font-display);font-size:26px;">Reports</h3>'
        '<span class="dl-sec-meta">5 output formats</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 3-column grid for first 3, then 2-column for remaining
    for i in range(0, len(REPORTS), 3):
        row = REPORTS[i:i+3]
        cols = st.columns(len(row), gap="medium")
        for col, rpt in zip(cols, row):
            with col:
                _render_card(rpt)


def _render_card(rpt: dict) -> None:
    generated = st.session_state.get(f"dl_generated_{rpt['key']}")

    st.markdown(
        f'<div class="dl-report-card">'
        f'  <div class="dl-report-icon">{rpt["icon"]}</div>'
        f'  <div class="dl-report-title">{rpt["title"]}</div>'
        f'  <div class="dl-report-desc">{rpt["desc"]}</div>'
        f'  <div class="dl-report-size">Est. size: {rpt["size"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if generated:
        with open(generated, "rb") as f:
            st.download_button(
                f"⬇ Download {rpt['title']}",
                data=f.read(),
                file_name=rpt["filename"],
                mime=rpt["mime"],
                key=f"dl_btn_{rpt['key']}",
                use_container_width=True,
            )
    else:
        if st.button(f"Generate {rpt['title']}", key=f"dl_gen_{rpt['key']}",
                     use_container_width=True):
            with st.spinner(f"Generating {rpt['title']}..."):
                try:
                    module_path, func_name = rpt["generator"].rsplit(".", 1)
                    import importlib
                    mod = importlib.import_module(module_path)
                    fn = getattr(mod, func_name)
                    path = fn(st.session_state)
                    st.session_state[f"dl_generated_{rpt['key']}"] = path
                    st.rerun()
                except Exception as e:
                    st.error(f"Generation failed: {e}")
```

## File: `dashboard/components/dl_data_exports.py`

```python
"""Data, model, and deployment exports."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import json

from dashboard.components import project_service


def render() -> None:
    project = project_service.get_active()
    if not project:
        return

    st.markdown(
        '<div class="dl-sec-header">'
        '<h3 style="font-family:var(--font-display);font-size:26px;">Data & Model</h3>'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3, gap="medium")

    # Original dataset
    with cols[0]:
        st.markdown(
            '<div class="dl-data-card">'
            '  <div class="dl-data-icon">📊</div>'
            '  <div class="dl-data-title">Original Dataset</div>'
            '  <div class="dl-data-desc">The uploaded raw dataset</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        df = st.session_state.get("df")
        if df is not None:
            csv = df.to_csv(index=False)
            st.download_button("⬇ Download CSV", csv, "original_data.csv", "text/csv",
                              key="dl_orig_csv", use_container_width=True)

    # Engineered features
    with cols[1]:
        st.markdown(
            '<div class="dl-data-card">'
            '  <div class="dl-data-icon">🔧</div>'
            '  <div class="dl-data-title">Engineered Features</div>'
            '  <div class="dl-data-desc">Post-feature-engineering dataset</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        df_eng = st.session_state.get("df_engineered")
        if df_eng is not None:
            csv = df_eng.to_csv(index=False)
            st.download_button("⬇ Download CSV", csv, "engineered_features.csv", "text/csv",
                              key="dl_eng_csv", use_container_width=True)

    # Model artifact
    with cols[2]:
        st.markdown(
            '<div class="dl-data-card">'
            '  <div class="dl-data-icon">🤖</div>'
            '  <div class="dl-data-title">Trained Model</div>'
            '  <div class="dl-data-desc">Serialized model + model card</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        model_path = getattr(project, "best_model_path", None)
        if model_path:
            try:
                with open(model_path, "rb") as f:
                    st.download_button("⬇ Download .joblib", f.read(), "model.joblib",
                                      "application/octet-stream", key="dl_model",
                                      use_container_width=True)
            except Exception:
                st.info("Model file not found on disk.")

    # Deployment package
    st.markdown(
        '<div class="dl-sec-header" style="margin-top:28px;">'
        '<h3 style="font-family:var(--font-display);font-size:26px;">Deployment</h3>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="dl-deploy-card">'
        '  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        '    <span style="font-size:20px;">🚀</span>'
        '    <span style="font-size:15px;font-weight:500;">FastAPI Deployment Package</span>'
        '    <span class="dl-deploy-status">Ready</span>'
        '  </div>'
        '  <p style="font-size:12.5px;color:var(--text-muted);">'
        '    Contains: api.py, schemas.py, model_loader.py, Dockerfile, requirements.txt</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("📦 Generate deployment package", key="dl_deploy", use_container_width=True):
        try:
            from agents.deployment_agent import package_deployment
            path = package_deployment(st.session_state)
            st.success(f"Deployment package saved to {path}")
        except Exception as e:
            st.warning(f"Deployment packaging not wired: {e}")
```

## File: `dashboard/components/dl_audit_trail.py`

```python
"""Audit trail exports — decision log + pipeline log."""
from __future__ import annotations
import json
import streamlit as st


def render() -> None:
    st.markdown(
        '<div class="dl-sec-header" style="margin-top:28px;">'
        '<h3 style="font-family:var(--font-display);font-size:26px;">Audit Trail</h3>'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2, gap="medium")

    with cols[0]:
        st.markdown(
            '<div class="dl-data-card">'
            '  <div class="dl-data-icon">📋</div>'
            '  <div class="dl-data-title">Decision Log</div>'
            '  <div class="dl-data-desc">Every AI decision with reasoning</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        decision_log = st.session_state.get("decision_log", [])
        if decision_log:
            st.download_button(
                "⬇ Download JSON", json.dumps(decision_log, indent=2, default=str),
                "decision_log.json", "application/json",
                key="dl_decision", use_container_width=True,
            )
        else:
            st.info("No decision log available yet.")

    with cols[1]:
        st.markdown(
            '<div class="dl-data-card">'
            '  <div class="dl-data-icon">⏱</div>'
            '  <div class="dl-data-title">Pipeline Log</div>'
            '  <div class="dl-data-desc">Timestamped execution trace</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        pipeline_log = st.session_state.get("pipeline_log", [])
        if pipeline_log:
            st.download_button(
                "⬇ Download JSON", json.dumps(pipeline_log, indent=2, default=str),
                "pipeline_log.json", "application/json",
                key="dl_pipeline", use_container_width=True,
            )
        else:
            st.info("No pipeline log available yet.")

    # Session export
    st.markdown('<div style="margin-top:18px;">', unsafe_allow_html=True)
    if st.button("💾 Export full session as portable JSON", key="dl_session", use_container_width=True):
        try:
            from session.session_export import export_session
            path = export_session(st.session_state.get("session_id", "current"))
            st.success(f"Session exported to {path}")
        except Exception as e:
            st.warning(f"Session export not wired: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
```

## CSS additions

```css
/* ============ Download ============ */
.dl-sec-header { display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin: 28px 0 18px; }
.dl-sec-meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

.dl-report-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 16px; padding: 22px; backdrop-filter: blur(14px);
  margin-bottom: 10px; text-align: center; min-height: 180px;
  display: flex; flex-direction: column; justify-content: center; }
.dl-report-icon { font-size: 32px; margin-bottom: 10px; }
.dl-report-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.dl-report-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; line-height: 1.4; }
.dl-report-size { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint); }

.dl-data-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; text-align: center; margin-bottom: 10px;
  backdrop-filter: blur(14px); }
.dl-data-icon { font-size: 24px; margin-bottom: 8px; }
.dl-data-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.dl-data-desc { font-size: 11.5px; color: var(--text-muted); }

.dl-deploy-card { background: rgba(52,211,153,0.04); border: 1px solid rgba(52,211,153,0.3);
  border-radius: 14px; padding: 18px; margin-bottom: 14px; }
.dl-deploy-status { font-family: var(--font-mono); font-size: 10px; color: var(--green);
  padding: 3px 10px; background: rgba(52,211,153,0.1);
  border: 1px solid rgba(52,211,153,0.3); border-radius: 999px;
  letter-spacing: 0.6px; text-transform: uppercase; }
```
