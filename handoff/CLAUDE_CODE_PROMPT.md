# Prompt to give to Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The handoff folder must be present at the project root (or update the paths in the prompt to match where you put it).

---

```
Read the AutoDS restructure handoff in `handoff/` thoroughly before writing any code:

1. Start with handoff/00_START_HERE.md — read all of it.
2. Read every spec file in handoff/specs/ in order (01 → 05).
3. Open handoff/reference/home_mockup.html in a browser as the visual target.

Then implement the restructure in this exact build order:

1. handoff/specs/01_project_model.md → create dashboard/components/project_service.py
   - Inspect dashboard/components/__init__.py and session/session_manager.py first to confirm the actual API surface before writing the wrapper. Adapt the _persist payload in the spec to match session_manager's real save_session signature.
   - Write tests/unit/test_project_service.py (8–12 tests as listed in the spec).
   - Run pytest tests/unit/test_project_service.py and confirm green.
   - Run pytest tests/integration/test_full_pipeline.py and confirm session round-trip still passes.

2. handoff/specs/02_auth_placeholder.md → create dashboard/components/auth_service.py and dashboard/pages/00_login.py.

3. handoff/specs/03_sidebar.md → create dashboard/components/sidebar_nav.py and add the sidebar CSS rules to dashboard/components/shared_css.py (additive — do NOT remove any existing rules). Also update .streamlit/config.toml to set showSidebarNavigation = false.

4. handoff/specs/04_home_page.md → create:
   - dashboard/components/onboarding_checklist.py
   - dashboard/components/data_source_launcher.py
   - dashboard/components/home_first_time.py
   - dashboard/components/home_returning.py
   - Add the home / checklist / source-tile / project-card CSS to shared_css.py.

5. Refactor dashboard/app.py per spec 04 — strip the existing marketing content, add the auth gate, route between first-time and returning home views.

6. handoff/specs/05_integration.md → wire each pipeline page (01 through 09):
   - Add the auth + project gate header pattern.
   - Insert step_status updates at the right spots in each page (the spec lists the exact transitions).
   - Add session_state hydration in 01_upload.py so resuming projects works.
   - Auto-handle st.session_state["pending_sample_dataset"] and st.session_state["upload_panel"] in 01_upload.py.

7. Smoke test end-to-end:
   - Boot: streamlit run dashboard/app.py
   - Confirm: login screen → fake credentials accepted → empty home → checklist → new project modal → upload → … → finish pipeline → home shows project card with "Complete · METRIC X.XX"
   - Refresh and re-log in → project still listed → click Open → resumes at last incomplete step.

8. Run full test suite: pytest tests/ — confirm 920+ passing, 0 failing. If any integration tests in tests/integration/ break because they assume no project context, fix the test fixtures (don't change product code to accommodate them).

Hard rules:
- Do NOT modify anything in agents/, data_connectors/, domains/, validation/, explainability/, evaluation/, reports/, serving/.
- Do NOT remove or rename any existing CSS variable in shared_css.py — additive changes only.
- Do NOT change Streamlit version or any dependency in requirements.txt.
- The 9 pipeline pages keep all their existing logic — you are only adding a header block (auth + project gate + sidebar render) and a few step_status update lines at the natural pipeline transitions.
- Use the cosmic theme tokens already defined in shared_css.py — never hardcode colors.

Quality bar:
- Every new Python file has a module docstring.
- Type hints throughout (this codebase uses them).
- New components must work in both light and dark theme without visual regressions (shared_css already supports both via CSS variables).
- Streamlit reruns are idempotent — no functions with side effects on import.

When you finish, report back with:
- A list of files created and modified.
- The pytest output (pass/fail counts).
- Any spec ambiguities you resolved + how you resolved them.
- Any deviations from the spec + the reason.
```

---

## Optional: do it in stages

If 7 steps in one shot is too much, run Claude Code on one spec at a time. Paste this stripped-down version with the spec number filled in:

```
Read handoff/00_START_HERE.md and handoff/specs/0X_<spec_name>.md.
Implement only that spec. Run the tests it prescribes. Report files changed and test results.
Do not touch anything outside the scope of this spec.
```

Replace `0X_<spec_name>` with the spec you're targeting (`01_project_model`, `02_auth_placeholder`, etc.).
