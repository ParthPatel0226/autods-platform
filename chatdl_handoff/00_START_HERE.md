# AutoDS Chat + Download Tabs — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_chat.md` → `specs/02_download.md` → `specs/03_integration.md`

These are the final two tabs. Lighter pages — Chat is a conversational interface, Download is an export picker.

## Prerequisites

Handoffs #1–8 deployed. Pipeline complete through Predict.

## Critical Constraints

Same as all previous handoffs — do NOT modify `agents/`, `reports/`, `session/`, etc.

## Tab 9 — Chat (CSS prefix: `ch-`)

Replace `08_chat.py` (222 lines — currently shows "Ask Anything" with 6 suggestion cards + text input) with a properly styled conversational interface:

- **Full chat history** rendered as message bubbles (user messages right-aligned violet, AI responses left-aligned glass cards)
- **6 domain-aware suggestion cards** at the top for first-time users (clickable to auto-fill)
- **Sticky bottom input** with text field + Send button
- **Context sidebar** (collapsed by default) showing analysis context: domain, model, metrics, features
- Wires to `agents/followup_agent.py` for actual conversational responses
- Messages stored in `st.session_state["ch_messages"]`

## Tab 10 — Download (CSS prefix: `dl-`)

Replace `09_download.py` (275 lines — currently shows sections for Reports/Data/Model/Deployment/Audit Trail with placeholder text) with a polished export hub:

- **5 download cards in a grid:** HTML Report · PDF Report · Executive Summary · Jupyter Notebook · ZIP Package
- Each card shows: icon, title, description, file size estimate, Generate + Download buttons
- **Data exports section:** original dataset, engineered features, predictions CSV
- **Model export:** serialized model (.joblib) + model card (.md)
- **Deployment package:** FastAPI code + Dockerfile + requirements
- **Audit trail:** decision log + pipeline log as JSON
- Wires to `reports/generators/` (html_report, pdf_report, executive_summary, notebook_export, zip_packager)
- Wires to `session/session_export.py` for portable JSON export
