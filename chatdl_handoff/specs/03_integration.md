# Spec 03 — Integration + Claude Code Prompt

## `dashboard/pages/09_download.py` (full rewrite)

```python
"""Download tab — reports, data, model, deployment, audit trail."""
from __future__ import annotations
import streamlit as st

from dashboard.components import auth_service, project_service
from dashboard.components.shared_css import inject_shared_css
from dashboard.components.sidebar_nav import render as render_sidebar
from dashboard.components.dl_report_cards import render as render_reports
from dashboard.components.dl_data_exports import render as render_data
from dashboard.components.dl_audit_trail import render as render_audit

st.set_page_config(page_title="AutoDS — Download", page_icon="⬇",
                   layout="wide", initial_sidebar_state="expanded")
inject_shared_css()

if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py"); st.stop()
render_sidebar()
project = project_service.get_active()
if not project:
    st.warning("Open a project first.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

# Hero
st.markdown(
    '<section style="margin-bottom:28px;">'
    '  <div class="dl-eyebrow" style="display:inline-flex;align-items:center;gap:8px;'
    '    padding:4px 12px;background:var(--bg-card);border:1px solid var(--border-default);'
    '    border-radius:999px;font-size:11.5px;color:var(--text-secondary);margin-bottom:16px;'
    '    font-family:var(--font-mono);letter-spacing:0.6px;text-transform:uppercase;">⬇ Downloads</div>'
    '  <h1 style="font-family:var(--font-display);font-size:56px;line-height:1;margin-bottom:12px;">'
    '    Export <em style="font-style:italic;background:var(--gradient-text);'
    '    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">'
    '    everything.</em></h1>'
    '  <p style="font-size:16px;color:var(--text-muted);max-width:720px;">'
    '    Reports, datasets, model artifacts, deployment packages, and audit trails — '
    '    all ready to download in your preferred format.</p>'
    '</section>',
    unsafe_allow_html=True,
)

render_reports()
render_data()
render_audit()

# Bottom
st.markdown('<div style="margin-top:36px;">', unsafe_allow_html=True)
cols = st.columns([1, 1])
with cols[0]:
    if st.button("← Back to Chat", key="dl_back", use_container_width=True):
        st.switch_page("pages/08_chat.py")
with cols[1]:
    st.markdown(
        '<div style="padding:14px;text-align:center;background:rgba(52,211,153,0.06);'
        'border:1px solid rgba(52,211,153,0.3);border-radius:12px;">'
        '<div style="font-size:18px;margin-bottom:4px;">🎉</div>'
        '<div style="font-size:14px;font-weight:500;color:var(--green);">Pipeline complete!</div>'
        '<div style="font-size:12px;color:var(--text-muted);">All 7 steps finished. Your analysis is ready.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
st.markdown('</div>', unsafe_allow_html=True)
```

---

## Claude Code Prompt (for both Chat + Download)

```
Read chatdl_handoff/00_START_HERE.md and all specs (01–03) in order.

BEFORE writing, OPEN:
  - agents/followup_agent.py — confirm handle() signature
  - reports/generators/html_report.py — confirm generate_html_report() signature
  - reports/generators/pdf_report.py — confirm generate_pdf_report()
  - reports/generators/executive_summary.py — confirm generate_executive_summary()
  - reports/generators/notebook_export.py — confirm generate_notebook()
  - reports/generators/zip_packager.py — confirm package_all()
  - session/session_export.py — confirm export_session()

Build order:
1. specs/01_chat.md → ch_message_bubble.py + ch_suggestions.py + rewrite 08_chat.py + CSS
2. specs/02_download.md → dl_report_cards.py + dl_data_exports.py + dl_audit_trail.py + CSS
3. specs/03_integration.md → rewrite 09_download.py

Hard rules:
- Do NOT modify agents/followup_agent.py, reports/generators/*, session/*.
- Chat CSS: ch-* prefix. Download CSS: dl-* prefix.
- All session_state keys: ch_* for chat, dl_* for download.
- Additive CSS only in shared_css.py.

Test:
- Chat: suggestions render → click one → message appears → AI responds → history persists.
- Download: 5 report cards render → click Generate → file appears → Download button works.
- Data exports: original CSV + engineered CSV + model .joblib download.
- Audit trail: decision log + pipeline log JSON download.
- Session export button works.
- Pipeline complete banner on Download page.
- Theme toggle works on both pages.
- pytest passes.
```
