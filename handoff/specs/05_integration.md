# Spec 05 — Pipeline Integration

## Goal

Make all 9 pipeline pages (`01_upload.py` through `09_download.py`) project-aware so they:

1. Verify a user is authenticated (redirect to login if not)
2. Verify an active project exists (redirect to home if not, except for upload which can create one on the fly)
3. Render the new sidebar
4. Update the project's `step_status` as the user progresses
5. Read/write user choices to the active project's record (so resuming works)

## The minimal page header pattern

At the top of every pipeline page (after `st.set_page_config` and `inject_shared_css()`), add:

```python
from dashboard.components import auth_service, project_service
from dashboard.components.sidebar_nav import render as render_sidebar

# Auth gate
if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py")
    st.stop()

render_sidebar()

# Project gate (skip for upload — it's where projects get attached to data)
project = project_service.get_active()
if project is None:
    st.warning("Open a project from the home page to continue.")
    if st.button("← Go to home"):
        st.switch_page("app.py")
    st.stop()
```

## Step status updates per page

After each page completes its main action (upload finishes, config saved, EDA run, etc.), update the project state:

### `pages/01_upload.py` — when dataset is loaded

```python
# When upload succeeds and dataset is in session_state:
if project_service.get_active_id():
    p = project_service.get_active()
    p.dataset_name = uploaded_file.name if uploaded_file else dataset_name
    p.n_rows = len(df)
    p.n_cols = len(df.columns)
    p.step_status["upload"] = "done"
    p.step_status["configure"] = "active"
    project_service.update(p)
else:
    # No active project yet — create one named after the dataset
    name = f"Analysis of {dataset_name}"
    p = project_service.create(name)
    p.dataset_name = dataset_name
    p.n_rows = len(df)
    p.n_cols = len(df.columns)
    p.step_status["upload"] = "done"
    p.step_status["configure"] = "active"
    project_service.update(p)
```

### `pages/02_configure.py` — when "Start Analysis" is clicked

```python
p = project_service.get_active()
p.confirmed_domain = selected_domain
p.detected_domain = detected_domain
p.analysis_mode = mode  # "auto" / "guided" / "expert"
p.target_column = target_col
p.problem_type = problem_type
p.step_status["configure"] = "done"
p.step_status["eda"] = "active"
project_service.update(p)
```

### `pages/03_eda_interactive.py` — when EDA "Run Analysis" is executed

```python
p = project_service.get_active()
p.step_status["eda"] = "done"
p.step_status["features"] = "active"
project_service.update(p)
```

### `pages/04_feature_engineering.py` — when feature decisions are approved

```python
p = project_service.get_active()
p.step_status["features"] = "done"
p.step_status["modeling"] = "active"
project_service.update(p)
```

### `pages/05_modeling.py` — when training completes

```python
p = project_service.get_active()
p.step_status["modeling"] = "done"
p.step_status["explainability"] = "active"
# Stash a metric summary for the project card
p.metric_summary = f"{primary_metric_name.upper()} {primary_metric_value:.3f}"
project_service.update(p)
```

### `pages/06_explainability.py` — when SHAP / fairness etc. complete

```python
p = project_service.get_active()
p.step_status["explainability"] = "done"
p.step_status["predict"] = "active"
project_service.update(p)
```

### `pages/07_predict.py` — when first prediction is made

```python
p = project_service.get_active()
p.step_status["predict"] = "done"
project_service.update(p)
```

### `pages/08_chat.py`, `pages/09_download.py`

No step updates needed — these are post-pipeline tools.

## Reading project state on page load

Pages should restore their UI state from the project record so resuming works:

```python
project = project_service.get_active()

# In configure page — pre-select previously chosen values
default_domain = project.confirmed_domain or project.detected_domain or ""
default_mode = project.analysis_mode or "guided"
default_target = project.target_column or ""
```

## Critical: do NOT break existing session_state keys

The current pages use a bunch of `st.session_state` keys (`df`, `domain`, `analysis_mode`, `target_column`, `problem_type`, `eda_results`, `eda_charts`, etc.). **Keep them.** The project record is additive — write to both `st.session_state` and the project, so existing logic that reads from session_state continues to work.

When loading a project (clicking "Open" on a project card), populate `session_state` from the project record:

In `home_returning.py`'s `_render_project_card` Open button:

```python
if st.button("Open", key=f"proj_open_{p.id}", ...):
    project_service.set_active(p.id)
    # Hydrate session state for backward-compat with pipeline pages
    st.session_state["domain"] = p.confirmed_domain or p.detected_domain
    st.session_state["analysis_mode"] = p.analysis_mode
    st.session_state["target_column"] = p.target_column
    st.session_state["problem_type"] = p.problem_type
    # Note: df is NOT restored — it's recomputed on the upload page if needed
    # by re-loading from p.dataset_path. The 01_upload page should handle this.
    st.switch_page(_resume_target(p))
```

If the resume target needs the dataframe and it's not in session_state, the upload page should detect this and re-load from `project.dataset_path`. Add this to `01_upload.py`:

```python
if project and project.dataset_path and "df" not in st.session_state:
    # Auto-reload the dataset from its saved path so pipeline can continue
    try:
        from data_connectors.universal_loader import load
        df = load(project.dataset_path)
        st.session_state["df"] = df
        st.success(f"Resumed project: reloaded {project.dataset_name}")
    except Exception as e:
        st.warning(f"Couldn't auto-reload dataset for this project: {e}")
```

(Adapt the import path to match the actual `data_connectors` module.)

## Sample dataset routing

`home_first_time.py` and the quick-start strip set `st.session_state["pending_sample_dataset"]` and route to the upload page. In `01_upload.py`, near the top:

```python
pending_sample = st.session_state.pop("pending_sample_dataset", None)
if pending_sample:
    # Trigger the existing sample-dataset loader for this key.
    # Look at the current 01_upload.py to find the function name; likely _load_sample(key) or similar.
    _load_sample(pending_sample)
```

Same for `st.session_state["upload_panel"]` — when set to "cloud" / "database" / "api" / "manual", auto-expand or auto-focus the matching panel/expander on the upload page.

## Test plan

1. **Smoke test:** fresh user → login → empty home → click checklist "Start" → name modal → upload page → upload Titanic → return home → see project card → click Open → resumes at Configure → finish full pipeline → return home → see "Complete · AUC 0.8x".

2. **Regression test:** `pytest tests/` should pass at the existing baseline (920+ tests). Pipeline integration tests in `tests/integration/test_*_path.py` may need a small fixture update to seed an active project before they run pages 02–09 — coordinate with whoever maintains those tests.

3. **Sidebar tracker test:** verify pulse animation appears on the correct step at each page, and dots flip green as steps complete.

4. **Project resume test:** start a project, get to EDA, refresh browser, log back in, click the project card → should land on EDA page with previous selections restored.
