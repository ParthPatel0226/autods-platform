# AutoDS Upload Tab Restructure — Implementation Handoff for Claude Code

> **Read order:** This file → `specs/01_layout_and_panels.md` → `specs/02_multisource_join.md` → `specs/03_post_upload_preview.md` → `specs/04_sample_gallery.md` → `specs/05_integration.md` → `reference/upload_mockup.html` (visual target).

---

## Goal

Replace the current `dashboard/pages/01_upload.py` with a redesigned upload tab that exposes all 4 connector categories (Manual / Cloud / Database / API & Web) as a tab switcher, surfaces a richer post-upload preview (file metadata, data quality glance, schema with sample values, detected domain), and properly promotes multi-source joining with explicit primary/secondary role selection.

This is **UI/UX refactor only** for the upload page. All existing data_connectors/ code is reused — no connector logic changes.

## Prerequisites

- Home tab restructure (previous handoff) **must already be deployed** — this spec assumes:
  - `dashboard/components/auth_service.py` exists
  - `dashboard/components/project_service.py` exists with `Project` dataclass and `set_active`/`get_active`
  - `dashboard/components/sidebar_nav.py` exists
  - `dashboard/components/shared_css.py` has the cosmic theme tokens
  - The home page sample dataset chips have been **slimmed to name-only** (the full sample gallery moves to the upload tab)

If the home handoff isn't done yet, do that first.

## Critical Constraints

1. **Do NOT modify** anything in `data_connectors/`, `domains/`, `validation/`, `agents/` — all backend connector code is reused as-is.
2. **Reuse the existing factory pattern**: `data_connectors.connector_factory.get_connector(...)` and `data_connectors.universal_loader.load(...)` are the entry points.
3. **Reuse `data_connectors.multi_source_manager`** for joining and `data_connectors.schema_matcher` for join key detection.
4. **Reuse `data_connectors.direct_input.sample_datasets`** for the curated sample gallery.
5. **Reuse `domains.domain_registry.detect_domain(df)`** for the post-upload domain auto-detection display.
6. **Extend `shared_css.py` additively** — do not remove existing rules. New rules are namespaced with `up-` prefix (upload page) so they don't collide with the home `home-` prefix.
7. The page must remain **project-aware** — read `project_service.get_active()` at the top, redirect to home if none, write upload state back to the project on success.

## What "Done" Looks Like

A user can:

1. Navigate to the upload tab (sidebar Pipeline → Upload, when an active project exists).
2. See 4 source tabs at the top: Manual / Cloud / Database / API & Web. The default tab is whatever was preselected on home (`session_state["upload_panel"]`) or "manual" if none.
3. **Manual:** drop or browse a file (any of 9 supported formats), preview, and confirm.
4. **Cloud:** pick a provider (S3 / GCS / Azure), fill connection fields, test, preview, load.
5. **Database:** pick a provider (Postgres / MySQL / SQL Server / DuckDB / BigQuery / Snowflake / Redshift), fill credentials, run query or pick a table, load.
6. **API & Web:** pick a source (REST / scrape / Kaggle / HuggingFace / Sheets / World Bank / FRED / Yahoo Finance / Census), configure, fetch.
7. See a **Recent uploads** strip above the panels for fast re-pick.
8. Open the **Multi-source join** section, add additional files, mark one as **Primary**, others as **Secondary**, see auto-detected join keys (with confidence pills), pick join type.
9. Browse a curated **sample dataset gallery** (8 samples) below the panels and load with one click.
10. After upload, see the post-upload preview:
    - Header with file name + detected domain pill (with confidence)
    - File metadata strip (format, encoding, separator, size, load time, memory)
    - Metric cards (rows / columns / sources joined / memory)
    - Data quality glance (missing %, duplicates, constant cols, high cardinality)
    - Schema preview table (column / type / missing bar / unique count / sample values)
    - "Continue to Configure" CTA at the bottom
11. After successful upload, the active project's `step_status["upload"]` becomes `done` and `step_status["configure"]` becomes `active` — the sidebar tracker updates accordingly.

## File Plan

### NEW files to create

```
dashboard/components/up_source_tabs.py           # 4-tab source switcher
dashboard/components/up_panel_manual.py          # Manual upload + drop zone
dashboard/components/up_panel_cloud.py           # Cloud connector form
dashboard/components/up_panel_database.py        # Database connector form
dashboard/components/up_panel_api.py             # API & Web connector form
dashboard/components/up_multisource_join.py      # Multi-source files + primary/secondary + joins
dashboard/components/up_sample_gallery.py        # Curated sample dataset cards
dashboard/components/up_recent_uploads.py        # Recent uploads pill strip
dashboard/components/up_post_preview.py          # File meta + metrics + quality + schema
dashboard/components/up_quality_glance.py        # Quality at-a-glance bars
dashboard/components/up_schema_table.py          # Schema preview table with sample values
```

### Files to MODIFY

```
dashboard/pages/01_upload.py                     # Full rewrite using new components
dashboard/components/shared_css.py               # Add `up-*` rules (additive only)
dashboard/components/project_service.py          # Add `recent_files` helper (used by recent strip)
```

### Files NOT to touch

- `data_connectors/**` (all connector logic stays unchanged)
- `agents/**`, `domains/**`, `validation/**`, `explainability/**`, `evaluation/**`, `reports/**`, `serving/**`
- All other pipeline pages (02–09)
- Tests

## Build Order

Each step is independently shippable. Test after each.

1. **`up_source_tabs.py`** — 4-tab switcher reading from / writing to `st.session_state["upload_panel"]`. Read spec 01.
2. **`up_panel_manual.py`** — drop zone + format chips. Wire to `universal_loader.load`. Spec 01.
3. **`up_panel_cloud.py` / `up_panel_database.py` / `up_panel_api.py`** — connector forms. Each calls `connector_factory.get_connector(...)`. Spec 01.
4. **`up_multisource_join.py`** — multi-file management with primary/secondary toggle, auto-detected joins via `schema_matcher`, executed via `multi_source_manager`. Spec 02.
5. **`up_post_preview.py`**, **`up_quality_glance.py`**, **`up_schema_table.py`** — post-upload preview blocks. Spec 03.
6. **`up_sample_gallery.py`** — 8 sample cards reading from `direct_input.sample_datasets`. Spec 04.
7. **`up_recent_uploads.py`** — pill strip from `project_service.get_recent_files()`. Spec 04.
8. **Rewrite `pages/01_upload.py`** — orchestrate all components. Spec 05.
9. **Add CSS** to `shared_css.py` — see each spec's CSS section. Additive only.
10. **End-to-end smoke test** — upload Titanic via Manual → see post-preview → Continue to Configure → sidebar tracker updates.
11. **Multi-source test** — load 2 sample files, mark one as primary, accept join, verify joined dataframe has the expected row count.
12. **Run pytest** — confirm 920+ passing, 0 failing. The integration tests in `tests/integration/test_full_pipeline.py` may need a small fixture update (see spec 05).

## Visual Reference

`reference/upload_mockup.html` is a self-contained HTML preview of the entire upload page. It is **NOT to be imported** into the Streamlit app. Use it as the visual target — copy CSS values, layout proportions, animation curves. The actual implementation uses Streamlit components consuming `shared_css.py` tokens.

## Handoff Checklist

After implementation:

- [ ] `streamlit run dashboard/app.py` boots without errors
- [ ] Source tab switching is instant and preserves form state per tab
- [ ] Manual upload accepts all 9 formats listed (CSV, TSV, XLSX, XLS, PARQUET, JSON, JSONL, FEATHER, ORC)
- [ ] Cloud / Database / API panels render correct provider tiles with the existing connector list
- [ ] "Test connection" button on each non-manual panel calls the right connector and shows success/failure
- [ ] Multi-source join: adding 2nd file → primary auto-set on first, secondary on second; reassigning primary works; detected joins render with confidence pills
- [ ] Sample gallery loads each dataset successfully via `direct_input.sample_datasets`
- [ ] Recent uploads strip appears only when project history has files
- [ ] Post-upload preview shows: file metadata strip, 4 metric cards, quality glance with 4 indicators, schema table with sample values
- [ ] Detected domain pill shows correct domain + confidence percentage
- [ ] "Continue to Configure" advances to `02_configure.py` with project step_status updated
- [ ] Theme toggle works (dark ↔ light) — every component renders correctly in both
- [ ] No light-mode color leaks (no hardcoded dark backgrounds anywhere)
- [ ] `pytest tests/` passes
