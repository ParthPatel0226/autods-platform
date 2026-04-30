# AutoDS Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_project_model.md` → `specs/02_auth_placeholder.md` → `specs/03_sidebar.md` → `specs/04_home_page.md` → `specs/05_integration.md` → `reference/home_mockup.html` (visual reference, do not import directly).

---

## Goal

Restructure the AutoDS dashboard around a Claude-style **project model** with a context-aware home page, slim grouped sidebar, and login placeholder — while keeping all existing backend infrastructure intact (agents, connectors, pipeline pages, session_manager, shared_css.py).

This is **UI/UX refactor only**. No agent logic, no LLM code, no model training code is changed.

## Critical Constraints

1. **Do NOT modify** any file in `agents/`, `data_connectors/`, `domains/`, `validation/`, `explainability/`, `serving/`, `evaluation/`, `reports/`. They are stable.
2. **Reuse `dashboard/components/shared_css.py`** as the theme source of truth — extend it, don't fork it. All new components must consume CSS variables from it (`var(--violet)`, `var(--bg-card)`, etc.).
3. **Preserve `session/session_manager.py`** SQLite backend — wrap it with the new `project_service.py` rather than replacing it. The "project" concept maps onto sessions: each project is one session record, with project metadata stored in extra columns or a JSON blob.
4. **No backend auth yet** — `auth_service.py` writes to `st.session_state` only. All callers go through the service so wiring real auth later is a one-file change.
5. **Streamlit-native** — no React, no custom JS frameworks. Custom HTML/CSS via `st.markdown(unsafe_allow_html=True)` is fine and already standard in this codebase.
6. **All 9 pipeline pages must continue working** unchanged. New project routing reads/writes `st.session_state.active_project_id`; pages that already use session_state stay as-is.

## What "Done" Looks Like

A user can:

1. Open the Streamlit app and hit a login screen first (mock auth, any input passes).
2. Land on a home page that detects: no projects → first-time onboarding view with checklist + data source launcher. Has projects → grid of project cards.
3. Click "New Project" → name modal → routes into existing upload page with a fresh project context.
4. See a slim grouped sidebar (Workspace / Pipeline / Tools). When idle, Pipeline section is muted. When inside a project, Pipeline transforms into a live workflow tracker with status dots (done / active-pulse / pending).
5. Toggle between dark and light themes via a top-right button (already supported in shared_css.py via the existing dual-theme system — just expose the toggle on the home page topbar).
6. Resume any project by clicking its card → routes to the next incomplete step in the pipeline.
7. All existing pipeline pages function exactly as before.

## File Plan

### NEW files to create

```
dashboard/components/auth_service.py          # session_state-backed auth abstraction
dashboard/components/project_service.py       # Project CRUD wrapping session_manager
dashboard/components/sidebar_nav.py           # New sidebar (replaces default Streamlit nav)
dashboard/components/data_source_launcher.py  # 4-tile data source grid (used on home)
dashboard/components/onboarding_checklist.py  # Interactive checklist component
dashboard/components/home_first_time.py       # State A renderer
dashboard/components/home_returning.py        # State B renderer (project grid)
dashboard/pages/00_login.py                   # Login + signup screens
```

### Files to MODIFY

```
dashboard/app.py                              # Strip current marketing, add auth gate, route to home states
dashboard/components/shared_css.py            # Add CSS rules for new components (sidebar, project cards, checklist, source tiles)
dashboard/components/__init__.py              # Re-export new components if package uses __all__
.streamlit/config.toml                        # Hide default sidebar nav, show only custom
```

Optional cleanup (can defer):
- Remove unused marketing markup from app.py once new home is verified working.

### Files NOT to touch

- `agents/**`
- `data_connectors/**`
- `domains/**`
- `validation/**`, `explainability/**`, `evaluation/**`, `reports/**`, `serving/**`
- `dashboard/pages/01_upload.py` through `09_download.py` (only project_id wiring, see specs/05)
- `landing-site/index.html` (already done)
- All test files (run them after to confirm nothing broke)

## Build Order

Each step is independently shippable. Test before moving to the next.

1. **`project_service.py`** — schema, CRUD, localStorage-then-SQLite migration path. Read spec 01.
2. **`auth_service.py` + `pages/00_login.py`** — login gate. Read spec 02.
3. **`sidebar_nav.py` + config.toml hide default nav** — new sidebar in both states. Read spec 03.
4. **`shared_css.py` additions** — extend with new component styles (no removals — additive only).
5. **`onboarding_checklist.py` + `data_source_launcher.py`** — small components used in home_first_time.
6. **`home_first_time.py` + `home_returning.py`** — two state renderers.
7. **`app.py` refactor** — replace marketing content with auth gate + home state router.
8. **Pipeline page wiring (`specs/05`)** — minimal session_state.active_project_id reads in each pipeline page so writes go to the correct project record.
9. **End-to-end smoke test** — fresh user flow → login → empty home → new project → upload → … → return home → see project card → resume → finish.
10. **Run pytest** — must show 920+ passing, 0 failures (matching the existing baseline).

## Visual Reference

`reference/home_mockup.html` is a self-contained HTML preview of the home page (both states + sidebar + theme toggle). It is NOT to be imported into the Streamlit app. Use it as the visual target — copy CSS values from it where helpful, but keep the actual implementation as Streamlit components consuming `shared_css.py` tokens.

## Handoff Checklist

After implementation, verify:

- [ ] `streamlit run dashboard/app.py` boots without errors
- [ ] Without login → login page renders, any non-empty email/password proceeds to home
- [ ] Empty state home shows checklist + data source tiles + sample chips
- [ ] "New Project" modal accepts name → routes to upload page
- [ ] After upload, project appears in returning-state home grid with "Configuring" status
- [ ] Sidebar pipeline tracker activates with correct step status
- [ ] Theme toggle works (dark ↔ light), persists across reloads
- [ ] All 9 pipeline pages still render and run without errors
- [ ] `pytest tests/` passes
- [ ] Light mode has zero hardcoded dark colors leaking through (visual check on home, login, sidebar, project cards)
