# Prompt to give Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The `upload_handoff/` folder must be present at the project root (or update paths to where you placed it).

> **Prerequisite:** The home tab restructure (previous handoff bundle) must already be deployed. This bundle assumes `dashboard/components/auth_service.py`, `project_service.py`, `sidebar_nav.py`, and the cosmic theme tokens in `shared_css.py` are in place.

---

```
Read the AutoDS upload restructure handoff in `upload_handoff/` thoroughly before writing any code:

1. Start with upload_handoff/00_START_HERE.md — read all of it.
2. Read every spec file in upload_handoff/specs/ in order (01 → 05).
3. Open upload_handoff/reference/upload_mockup.html in a browser as the visual target.

Then implement the restructure in this exact build order:

1. upload_handoff/specs/01_layout_and_panels.md
   Before writing the connector forms, OPEN these files and confirm the actual interface:
     - data_connectors/connector_factory.py — confirm get_connector(category, provider) signature
     - data_connectors/universal_loader.py — confirm load(path) returns (df, meta) and what meta contains
     - data_connectors/file_connectors/, database_connectors/, api_connectors/, cloud_connectors/ — confirm provider keys
   Then create:
     - dashboard/components/up_source_tabs.py
     - dashboard/components/up_panel_manual.py
     - dashboard/components/up_panel_cloud.py
     - dashboard/components/up_panel_database.py
     - dashboard/components/up_panel_api.py
   Add the matching CSS rules from spec 01 to dashboard/components/shared_css.py (additive only — do NOT remove any existing rule).

2. upload_handoff/specs/02_multisource_join.md
   Before writing this component, OPEN:
     - data_connectors/multi_source_manager.py — confirm method names
     - data_connectors/schema_matcher.py — confirm join detection function name and return shape
   If the actual interface differs from what the spec assumes, create an adapter at dashboard/components/up_ms_adapter.py — do NOT modify multi_source_manager.py or schema_matcher.py.
   Then create:
     - dashboard/components/up_multisource_join.py
   Add the matching CSS rules from spec 02 to shared_css.py.

3. upload_handoff/specs/03_post_upload_preview.md
   Before writing the preview, OPEN:
     - domains/domain_registry.py — confirm detect_domain(df) return shape
   Then create:
     - dashboard/components/up_post_preview.py
     - dashboard/components/up_quality_glance.py
     - dashboard/components/up_schema_table.py
   Add CSS from spec 03.

4. upload_handoff/specs/04_sample_gallery.md
   Before writing this component, OPEN:
     - data_connectors/direct_input/sample_datasets.py — find the actual loader function name
   Then create:
     - dashboard/components/up_sample_gallery.py
     - dashboard/components/up_recent_uploads.py
   Add `get_recent_files(limit, user_id)` to dashboard/components/project_service.py per the spec.
   Add CSS from spec 04.

5. upload_handoff/specs/05_integration.md
   Rewrite dashboard/pages/01_upload.py end-to-end using the new components.
   Honor st.session_state["upload_panel"] (from home page tile clicks) and st.session_state["pending_sample_dataset"] (from home sample chips).
   Add hero/breadcrumb CSS from spec 05.

6. Smoke test end-to-end:
   - streamlit run dashboard/app.py
   - Login → New Project → home → click "Manual upload" tile → routed to upload tab with manual panel active.
   - Upload Titanic → post-upload preview renders with file metadata, 4 metric cards, quality glance, schema table.
   - Detected domain shows on the result header.
   - Click "Continue to Configure" → sidebar shows Upload ✅, Configure ⏳ (pulsing).
   - Return to home → project card shows correct status.

7. Each-panel test:
   - Cloud: select S3, fill placeholder values, "Test connection" should show error gracefully (no real bucket configured).
   - Database: select PostgreSQL, fill values, "Test connection" gracefully fails.
   - API & Web: select REST, fill placeholder URL, "Test request" gracefully fails.
   - All panels render fully and switch between tabs without losing form state.

8. Multi-source test:
   - Upload a primary CSV.
   - Expand multi-source, add another CSV via the "Add another file" uploader.
   - Confirm the second file becomes Secondary.
   - Click "Primary" on the secondary file — primary swaps correctly.
   - Confirm detected join keys appear with confidence pills.
   - Click "Build joined dataset" — joined frame replaces the working df.

9. Theme test:
   - Toggle to light mode.
   - All four panels render correctly.
   - Provider tiles, drop zone, multi-source files, sample cards, preview elements all show light backgrounds with adequate contrast.
   - Toggle back to dark — everything reverts cleanly.

10. Regression test:
    - pytest tests/
    - Confirm 920+ passing, 0 failing.
    - If tests/integration/test_full_pipeline.py breaks because it accesses st.session_state["df"] directly without an active project, fix the test fixture to seed an active project + active panel — do NOT change product code.

Hard rules:
- Do NOT modify anything in data_connectors/, agents/, domains/, validation/, evaluation/, explainability/, reports/, serving/.
- Do NOT modify other dashboard pages (00_login, app.py, 02–09).
- Do NOT remove or rename any existing CSS variable in shared_css.py — additive only.
- All new CSS rules use the up- prefix to avoid collisions with home- prefix from the previous handoff.
- All new component files under dashboard/components/ use the up_ prefix.
- All Streamlit session_state keys use the up_ prefix.

Quality bar:
- Module docstring on every new file.
- Type hints throughout.
- Light + dark theme parity verified visually.
- Streamlit reruns are idempotent — no side effects on import.

When finished, report back with:
- Files created and modified.
- pytest output (pass/fail counts).
- Any spec assumption mismatches resolved (e.g., "schema_matcher uses detect_join_pairs() not detect_join_keys() — adapted via up_ms_adapter.py").
- Any deviations and the reason.
```

---

## Optional: stage-by-stage runs

If running the whole handoff at once is too much, run one spec at a time:

```
Read upload_handoff/00_START_HERE.md and upload_handoff/specs/0X_<spec_name>.md.
Implement only that spec. Run the smoke tests it prescribes.
Report files changed and test results.
Do not touch anything outside the scope of this spec.
```

Replace `0X_<spec_name>` with the spec you want to run (`01_layout_and_panels`, `02_multisource_join`, etc.).
