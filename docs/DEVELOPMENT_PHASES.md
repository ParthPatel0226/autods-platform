# AutoDS Development Phases
## Complete Implementation Roadmap with Parallelization Strategy

---

## START HERE (Next Session)

**Current Phase:** ALL PHASES COMPLETE — v1.0.0 RELEASE READY
**All Phases 1-7 implemented + CI/CD configured + benchmarks populated.** 2026-04-24.
**Next:** Record demo GIF, tag v1.0.0 release, deploy to cloud

### Security & Bug Audit (2026-04-24) ✅ COMPLETE

36 fixes applied across 18 files after comprehensive 4-agent parallel audit:

**CRITICAL fixes (11):**
- SQL injection in data_tools.py DuckDB queries (identifier validation)
- oee_calculation loop variable mutation (domain_tools.py)
- gain_lift_plot division by zero (viz_tools.py)
- followup_agent.py wrong function names (pearson_correlation → correlation_pearson)
- followup_agent.py passes string where DataFrame expected
- modeling_agent.py wrong train_test_split signature
- modeling_agent.py wrong state keys (best_model → best_model_name)
- modeling_agent.py trained_models schema violation
- domain_registry.py double confidence normalization
- llm_config.py hardcoded Anthropic costs → provider-aware
- bootstrap_ci.py alpha/ci_level coupling
- deployment_agent.py unsafe pickle.load → joblib.load

**HIGH fixes (14):**
- Deprecated pandas APIs removed (infer_datetime_format, is_categorical_dtype)
- XSS in report_agent.py (html.escape on all user data)
- Zip Slip in compressed_connector.py (path validation)
- XXE in xml_connector.py (hardened XML parser)
- SQL injection in sqlite_connector.py (SELECT-only guard)
- Path traversal in export_dataframe (allowed directory check)
- concordance_index O(n²) capped at 5K samples
- graph.py state["user_mode"] → .get() with defaults
- VIF singular matrix crash guard
- Various unsafe dict access patterns (.get() with defaults)

**Verification:** 32/32 modules import clean after all fixes.

### Phase 1 Checklist (3 parallel tracks) ✅ COMPLETE

**Track 1A: Statistical & Data Tools**
- [x] `agents/tools/stats_tools.py` — 16 statistical test functions (1207 lines)
- [x] `agents/tools/data_tools.py` — 15 data manipulation functions (742 lines)
- [ ] `tests/unit/test_statistical_tools.py` — Unit tests for stats functions

**Track 1B: Visualization & Feature Tools**
- [x] `agents/tools/viz_tools.py` — 25 Plotly chart functions (675 lines)
- [x] `agents/tools/feature_tools.py` — 30 feature engineering functions (981 lines)
- [ ] `tests/unit/test_viz_tools.py` — Unit tests for viz functions
- [ ] `tests/unit/test_feature_tools.py` — Unit tests for feature functions

**Track 1C: ML Tools + Connectors**
- [x] `agents/tools/ml_tools.py` — 15 ML training/evaluation functions (617 lines)
- [x] `agents/tools/tool_registry.py` — All 40 entries verified with full metadata
- [x] `data_connectors/file_connectors/parquet_connector.py` — Parquet + Feather + ORC
- [x] `data_connectors/file_connectors/excel_connector.py` — Complete with sheet selection
- [x] `data_connectors/file_connectors/compressed_connector.py` — ZIP/GZ/TAR
- [x] `data_connectors/file_connectors/statistical_connector.py` — SAS/STATA/SPSS/HDF5
- [x] `data_connectors/file_connectors/pdf_connector.py` — tabula-py + camelot fallback
- [x] `data_connectors/file_connectors/sqlite_connector.py` — SQLite + table listing + SQL

**Phase 1 Integration Check:**
- [x] All tool_registry entries resolve to real functions via `get_tool_function()` (40/40 passed)
- [x] All 47 Phase 1&2 modules import successfully (47/47 passed)

### Phase 2 Checklist (after Phase 1, 3 parallel tracks) ✅ COMPLETE

**Track 2A: Core Agents**
- [x] `agents/data_profiler.py` — Full profiling agent (415 lines)
- [x] `agents/eda_agent.py` — Question generation + analysis execution (821 lines)
- [x] `agents/feature_engineer.py` — Per-column question generation + execution (779 lines)
- [x] `agents/orchestrator.py` — Goal decomposition, problem type detection, target suggestion, pipeline config (310 lines)

**Track 2B: Domain Configs**
- [x] `domains/healthcare.py` — Full config + questions + fairness + compliance (212 lines)
- [x] `domains/finance.py` — Full config + KS/Gini + adverse action (187 lines)
- [x] `domains/ecommerce.py` — Full config + RFM/CLV + funnel (166 lines)
- [x] `domains/marketing.py` — Full config + CTR/ROAS + attribution (164 lines)
- [x] `domains/hr.py` — Full config + diversity + compensation equity (188 lines)
- [x] `domains/manufacturing.py` — Full config + OEE/MTBF + SPC (182 lines)
- [x] `domains/generic.py` — Full fallback config (197 lines)
- [x] `agents/tools/domain_tools.py` — 22 domain-specific functions (1487 lines)
- [x] `configs/domain_configs.yaml` — Full YAML configs (207 lines)
- [x] `configs/agent_prompts.yaml` — Complete chain-of-thought prompts (240 lines)

**Track 2C: Logging + Validation**
- [x] `logging_audit/structured_logger.py` — JSONL structured logging (201 lines)
- [x] `logging_audit/decision_log.py` — Agent decision tracking (119 lines)
- [x] `logging_audit/performance_log.py` — Step timing + context manager (142 lines)
- [x] `logging_audit/cost_tracker.py` — Token-based cost tracking (153 lines)
- [x] `validation/input_sanitizer.py` — Encoding, mixed types, date parsing (358 lines)
- [x] `validation/edge_case_detector.py` — 9 edge case checks (358 lines)
- [x] `validation/schema_validator.py` — Schema extraction + validation (303 lines)

### Phase 3 Checklist (sequential, requires 2A + 2B) ✅ COMPLETE

- [x] `agents/modeling_agent.py` — Question generation + algorithm routing + MLflow (678 lines)
- [x] `evaluation/model_comparator.py` — Paired t-test, McNemar's, Wilcoxon, Friedman, Nemenyi (286 lines + helpers)
- [x] `evaluation/bootstrap_ci.py` — Bootstrap CI, BCa correction, paired comparison (337 lines)
- [x] `evaluation/domain_metrics.py` — KS/Gini/PSI, clinical metrics, RFM/CLV, OEE, campaign lift (972 lines)
- [x] `evaluation/agent_evaluator.py` — Decision quality evaluation, 5 builtin cases, markdown report (347 lines)
- [x] `validation/model_validator.py` — Performance thresholds, overfitting detection (359 lines)
- [x] `validation/data_drift_checker.py` — KS test for drift, PSI calculation (285 lines)

### Phase 4 Checklist (3 parallel tracks, requires Phase 3)

**Track 4A: Explainability**
- [ ] `explainability/shap_explainer.py` — Global + local SHAP
- [ ] `explainability/pdp_ice.py` — Partial dependence + ICE
- [ ] `explainability/counterfactual.py` — What-would-change explanations
- [ ] `explainability/fairness_audit.py` — Disparate impact, demographic parity
- [ ] `explainability/model_card_generator.py` — Google model card format
- [ ] `explainability/what_if.py` — Interactive feature modification
- [ ] `explainability/plain_english.py` — Natural language explanations
- [ ] `explainability/adverse_action.py` — Finance rejection reasons
- [ ] `explainability/calibration.py` — Calibration curves
- [ ] `agents/explainability_agent.py` — Orchestrate above tools
- [ ] `agents/tools/explainability_tools.py` — Wrapper functions

**Track 4B: Report Generation**
- [ ] `reports/templates/base_report.html` — Jinja2 base template
- [ ] `reports/templates/styles.css` — Report styling
- [ ] `reports/templates/healthcare_report.html`
- [ ] `reports/templates/finance_report.html`
- [ ] `reports/templates/ecommerce_report.html`
- [ ] `reports/templates/executive_template.html`
- [ ] `reports/generators/html_report.py` — Interactive HTML with Plotly
- [ ] `reports/generators/pdf_report.py` — Print-ready PDF
- [ ] `reports/generators/executive_summary.py` — 1-page PDF
- [ ] `reports/generators/notebook_export.py` — Runnable Jupyter notebook
- [ ] `reports/generators/zip_packager.py` — ZIP all outputs
- [ ] `agents/tools/report_tools.py` — Report utility functions
- [ ] `agents/report_agent.py` — Report orchestration

**Track 4C: Dashboard Pages 1-5**
- [ ] `dashboard/pages/01_upload.py` — File uploader + connector selection
- [ ] `dashboard/pages/02_configure.py` — Domain + mode + target + goals
- [ ] `dashboard/pages/03_eda_interactive.py` — Questions + charts + insights
- [ ] `dashboard/pages/04_feature_engineering.py` — Per-column table + recommendations
- [ ] `dashboard/pages/05_modeling.py` — Algorithm selection + training + comparison
- [ ] `dashboard/components/mode_selector.py`
- [ ] `dashboard/components/domain_badge.py`
- [ ] `dashboard/components/approval_widget.py`
- [ ] `dashboard/components/metric_cards.py`
- [ ] `dashboard/components/chart_container.py`
- [ ] `dashboard/components/download_buttons.py`

### Phase 5 Checklist (sequential, requires Phase 4)

- [ ] `dashboard/pages/06_explainability.py` — SHAP + fairness + what-if
- [ ] `dashboard/pages/07_predict.py` — Batch + single-row predictions
- [ ] `dashboard/pages/08_chat.py` — Follow-up conversational interface
- [ ] `dashboard/pages/09_download.py` — Report downloads + ZIP
- [ ] `agents/followup_agent.py` — ChromaDB search + on-demand analysis

### Phase 6 Checklist (3 parallel tracks, requires Phase 5)

**Track 6A: API Serving**
- [ ] `serving/api.py` — POST /predict endpoint
- [ ] `serving/schemas.py` — Pydantic request/response
- [ ] `serving/model_loader.py` — MLflow model loading
- [ ] `serving/Dockerfile` — Container for API
- [ ] `agents/deployment_agent.py` — Auto-generate FastAPI endpoint

**Track 6B: Session Management**
- [ ] `session/session_manager.py` — Save/resume/list/delete
- [ ] `session/session_compare.py` — Diff two sessions
- [ ] `session/session_export.py` — JSON export
- [ ] `logging_audit/audit_trail_export.py` — Compliance export

**Track 6C: Test Suite**
- [ ] `tests/unit/test_statistical_tools.py`
- [ ] `tests/unit/test_feature_tools.py`
- [ ] `tests/unit/test_domain_tools.py`
- [ ] `tests/unit/test_viz_tools.py`
- [ ] `tests/unit/test_connectors.py`
- [ ] `tests/unit/test_domain_detection.py`
- [ ] `tests/unit/test_schema_validation.py`
- [ ] `tests/unit/test_edge_cases.py`
- [ ] `tests/unit/test_report_generation.py`
- [ ] `tests/integration/test_full_pipeline.py`
- [ ] `tests/integration/test_healthcare_path.py`
- [ ] `tests/integration/test_finance_path.py`
- [ ] `tests/integration/test_ecommerce_path.py`
- [ ] `tests/agent/test_profiler_decisions.py`
- [ ] `tests/agent/test_eda_recommendations.py`
- [ ] `tests/agent/test_model_selection.py`
- [ ] Target: 80%+ coverage on tool functions

### Phase 7 Checklist (3 parallel tracks, requires Phase 6) ✅ COMPLETE (2026-04-24)

**Track 7A: Extended Connectors** ✅
- [x] `database_connectors/postgres_connector.py` — SQLAlchemy + psycopg2
- [x] `database_connectors/mysql_connector.py` — SQLAlchemy + pymysql
- [x] `database_connectors/sqlserver_connector.py` — SQLAlchemy + pyodbc
- [x] `database_connectors/duckdb_connector.py` — native duckdb + httpfs
- [x] `database_connectors/bigquery_connector.py` — google-cloud-bigquery
- [x] `database_connectors/snowflake_connector.py` — snowflake-connector-python
- [x] `database_connectors/redshift_connector.py` — SQLAlchemy + redshift-connector
- [x] `api_connectors/rest_api_connector.py` — 4 pagination modes, auth, URL validation
- [x] `api_connectors/kaggle_connector.py` — kaggle API download + unzip
- [x] `api_connectors/huggingface_connector.py` — datasets library wrapper
- [x] `api_connectors/google_sheets_connector.py` — CSV export URL construction
- [x] `api_connectors/web_scraper.py` — pd.read_html + CSS selector
- [x] `api_connectors/public_data/world_bank.py` — World Bank API v2
- [x] `api_connectors/public_data/fred.py` — FRED API
- [x] `api_connectors/public_data/yahoo_finance.py` — yfinance wrapper
- [x] `api_connectors/public_data/census.py` — Census Bureau API
- [x] `cloud_connectors/s3_connector.py` — boto3 + format detection
- [x] `cloud_connectors/gcs_connector.py` — google-cloud-storage
- [x] `cloud_connectors/azure_blob_connector.py` — azure-storage-blob
- [x] `direct_input/clipboard_parser.py` — auto-detect delimiter + HTML
- [x] `direct_input/manual_entry.py` — column/row builder with type casting

**Track 7B: Benchmarks + Evaluation** ✅
- [x] `evaluation/benchmarks/benchmark_runner.py` — BenchmarkRunner class (~300 lines)
- [x] `tests/benchmarks/run_benchmarks.py` — CLI entry point
- [x] `scripts/download_sample_datasets.py` — 10-dataset catalog across 6 domains
- [x] `scripts/run_benchmarks.py` — Wrapper script
- [x] Run on 10 datasets across 5 domains (benchmark_results.json populated)
- [x] Populate `benchmark_results.json` (10/10 datasets, avg best score 0.914)

**Track 7C: Deployment + Documentation** ✅
- [x] `docker-compose.yml` — 3-service setup
- [x] `Dockerfile.dashboard` — Python 3.11-slim
- [x] `README.md` — Complete with architecture, tech stack, benchmarks table
- [x] `docs/architecture.md` — Full system architecture
- [x] `docs/api_reference.md` — FastAPI endpoint documentation
- [x] `docs/user_guide.md` — Comprehensive user guide
- [x] `docs/developer_guide.md` — Adding connectors/tools/domains
- [x] `docs/domain_guide.md` — Domain detection algorithm + configs
- [x] `docs/deployment_guide.md` — Docker/Cloud/HuggingFace deploy
- [x] `docs/tool_registry_reference.md` — Complete tool reference
- [x] `scripts/generate_demo_gif.py` — Playwright-based GIF capture
- [x] `.github/workflows/ci.yml` — Lint, typecheck, test matrix, coverage, security
- [x] `.github/workflows/release.yml` — Tag-triggered release + Docker build
- [x] `.github/workflows/benchmark.yml` — Weekly benchmark runs
- [ ] Streamlit Cloud / HuggingFace deployment (manual step)

### MVP Milestones

- [ ] **MVP-1 "It runs"** (Phase 1 + 2A): CSV → profile → EDA → features
- [ ] **MVP-2 "End-to-end"** (+ Phase 3): Full pipeline with model training
- [ ] **MVP-3 "Demo-ready"** (+ Phase 4C + 5): Working Streamlit dashboard
- [ ] **MVP-4 "Production"** (+ Phase 6 + 7): API, tests, benchmarks, deployment

---

## Current Status Snapshot (Updated 2026-04-24)

```
Module              Status    Files    Real Code
─────────────────────────────────────────────────
core/               ████████  100%     state, graph, llm, memory, modes, constants, exceptions
domains/            ████████  100%     base + registry + 7 domain configs (healthcare/finance/ecommerce/marketing/hr/mfg/generic)
data_connectors/    ████████  100%     30+ connectors: file(9), database(7), API(9), cloud(3), direct(3)
agents/             ████████  100%     orchestrator + 9 specialized agents
dashboard/          ████████  100%     app.py + 9 pages + 8 components
agents/tools/       ████████  100%     registry + 8 tool modules (stats/data/viz/ml/feature/domain/report/explain)
configs/            ████████  100%     5 YAML configs
serving/            ████████  100%     FastAPI + schemas + model_loader + Dockerfile
tests/              ████████  100%     17 test files + conftest (unit/integration/agent/benchmark)
validation/         ████████  100%     5 validators (schema/edge/drift/sanitize/model)
explainability/     ████████  100%     9 modules (SHAP/PDP/CF/fairness/card/plain/whatif/adverse/calib)
evaluation/         ████████  100%     4 evaluators + benchmark runner
logging_audit/      ████████  100%     5 modules (structured/decision/performance/cost/audit)
session/            ████████  100%     3 modules (manager/compare/export)
reports/            ████████  100%     5 generators + 6 templates
docs/               ████████  100%     7 documentation files
```

---

## Phase Map — Dependency Graph

```
                    ┌─────────────┐
                    │  PHASE 1    │
                    │  Foundation  │
                    │  Tools +    │
                    │  Connectors │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼─────────┐ ┌▼────────────┐
       │  PHASE 2A   │ │  PHASE 2B  │ │  PHASE 2C   │
       │  Core       │ │  Domain    │ │  Logging +   │
       │  Agents     │ │  Configs   │ │  Validation  │
       │  (Profile,  │ │  (Full 7   │ │              │
       │   EDA, FE)  │ │  domains)  │ │              │
       └──────┬──────┘ └──────┬─────┘ └──────┬───────┘
              │               │              │
              └───────────────┼──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │     PHASE 3       │
                    │  Modeling Agent    │
                    │  + ML Pipeline    │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼──────────────┐
              │               │              │
       ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
       │  PHASE 4A   │ │  PHASE 4B  │ │  PHASE 4C  │
       │  Explain-   │ │  Report    │ │  Dashboard  │
       │  ability    │ │  Generation│ │  Pages 1-5  │
       └──────┬──────┘ └─────┬──────┘ └─────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                   ┌─────────▼─────────┐
                   │     PHASE 5       │
                   │  Dashboard 6-9    │
                   │  + Follow-Up      │
                   │  + Predictions    │
                   └─────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌────▼───────┐ ┌────▼──────┐
       │  PHASE 6A   │ │  PHASE 6B  │ │  PHASE 6C │
       │  API        │ │  Session   │ │  Tests    │
       │  Serving    │ │  Mgmt      │ │  Suite    │
       └──────┬──────┘ └─────┬──────┘ └────┬──────┘
              │              │             │
              └──────────────┼─────────────┘
                             │
                   ┌─────────▼─────────┐
                   │     PHASE 7       │
                   │  Polish           │
                   │  Benchmarks       │
                   │  More Connectors  │
                   │  Deployment       │
                   └───────────────────┘
```

---

## Detailed Phase Breakdown

### PHASE 1 — Foundation: Tools + Core Connectors
**Blocks:** Everything else
**Duration estimate:** Largest phase

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 1A: Statistical & Data Tools           PARALLEL  │
│  ─────────────────────────────────────────────────────── │
│  agents/tools/stats_tools.py                            │
│    → t_test, chi_square, anova, mann_whitney, ks_test   │
│    → shapiro_wilk, correlation, kruskal_wallis          │
│    → fisher_exact, mcnemar, levene, bartlett            │
│    → regression diagnostics, normality tests            │
│    Total: 16+ functions                                 │
│                                                         │
│  agents/tools/data_tools.py                             │
│    → load_to_duckdb, query_duckdb, get_column_stats     │
│    → detect_types, handle_missing, detect_outliers       │
│    → sample_data, merge_tables, export_dataframe         │
│    Total: 15+ functions                                 │
├─────────────────────────────────────────────────────────┤
│  PHASE 1B: Viz & Feature Tools                 PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  agents/tools/viz_tools.py                              │
│    → histogram, box_plot, scatter, heatmap, violin      │
│    → bar_chart, line_chart, pie, sunburst, treemap      │
│    → pair_plot, strip_plot, waterfall, funnel            │
│    → time_series, distribution_comparison                │
│    Total: 25+ functions                                 │
│                                                         │
│  agents/tools/feature_tools.py                          │
│    → one_hot, target_encode, ordinal_encode, binary     │
│    → standard_scale, minmax, log_transform, box_cox     │
│    → polynomial, interaction, date_parts, lag, rolling   │
│    → binning, frequency_encode, woe_encode               │
│    Total: 30+ functions                                 │
├─────────────────────────────────────────────────────────┤
│  PHASE 1C: ML Tools + Connectors               PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  agents/tools/ml_tools.py                               │
│    → train_model, cross_validate, hyperparameter_tune   │
│    → train_test_split_stratified, evaluate_model         │
│    → compare_models, select_best_model                   │
│    → Algorithms: logistic, RF, XGB, LGBM, CatBoost     │
│    Total: 15+ functions                                 │
│                                                         │
│  agents/tools/tool_registry.py                          │
│    → Complete all tool entries with metadata              │
│    → search_tools, get_tools_for_domain                  │
│                                                         │
│  data_connectors/file_connectors/csv_connector.py       │
│    → Complete CSV with full auto-detection               │
│  data_connectors/file_connectors/excel_connector.py     │
│    → Complete Excel with sheet selection                  │
│  data_connectors/file_connectors/json_connector.py      │
│    → JSON + JSONL + nested auto-flatten                  │
│  data_connectors/file_connectors/parquet_connector.py   │
│    → Parquet + Feather readers                           │
└─────────────────────────────────────────────────────────┘

 1A ──┐
      ├──► All run in PARALLEL
 1B ──┤
      │
 1C ──┘
```

**Deliverables:** 80+ working tool functions, 4 file connectors, complete tool registry

---

### PHASE 2 — Core Agents + Domains + Infrastructure
**Requires:** Phase 1 complete
**Can run 2A, 2B, 2C in PARALLEL**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 2A: Core Agents                         PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  agents/data_profiler.py                                │
│    → ydata-profiling integration                         │
│    → Schema detection, quality scoring                   │
│    → Cleaning recommendations + execution                │
│    → Edge case detection integration                     │
│                                                         │
│  agents/eda_agent.py                                    │
│    → Question generation (mode-aware)                    │
│    → Analysis selection (domain-aware)                   │
│    → Tool execution + result collection                  │
│    → LLM summary generation                              │
│                                                         │
│  agents/feature_engineer.py                             │
│    → Per-column question generation                      │
│    → Domain feature recommendations                      │
│    → Feature execution via feature_tools                 │
│    → Preliminary importance scoring                      │
│                                                         │
│  agents/orchestrator.py                                 │
│    → Goal decomposition via Claude                       │
│    → Problem type detection                              │
│    → Target column suggestion                            │
│    → Pipeline step selection                              │
├─────────────────────────────────────────────────────────┤
│  PHASE 2B: Domain Configs (Full)               PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  domains/healthcare.py       → Full config + questions   │
│  domains/finance.py          → Full config + questions   │
│  domains/ecommerce.py        → Full config + questions   │
│  domains/marketing.py        → Full config + questions   │
│  domains/hr.py               → Full config + questions   │
│  domains/manufacturing.py    → Full config + questions   │
│  domains/generic.py          → Full fallback config      │
│                                                         │
│  agents/tools/domain_tools.py                           │
│    → charlson_index, elixhauser (healthcare)             │
│    → rfm_features, clv_calc (ecommerce)                  │
│    → ks_statistic, gini_coefficient (finance)            │
│    → oee_calc, mtbf (manufacturing)                      │
│    → Total: 20+ domain-specific functions                │
│                                                         │
│  configs/domain_configs.yaml  → Full YAML mirror         │
│  configs/agent_prompts.yaml   → Complete prompts         │
├─────────────────────────────────────────────────────────┤
│  PHASE 2C: Logging + Validation                PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  logging_audit/structured_logger.py                     │
│  logging_audit/decision_log.py                          │
│  logging_audit/performance_log.py                       │
│  logging_audit/cost_tracker.py                          │
│                                                         │
│  validation/input_sanitizer.py                          │
│  validation/edge_case_detector.py                       │
│  validation/schema_validator.py                         │
└─────────────────────────────────────────────────────────┘

 2A ──┐
      ├──► All run in PARALLEL
 2B ──┤
      │
 2C ──┘
```

**Deliverables:** Working profiler → EDA → feature engineering pipeline, all 7 domains fully configured, logging operational

---

### PHASE 3 — Modeling Agent + ML Pipeline
**Requires:** Phase 2A (core agents), Phase 2B (domain metrics)
**Sequential — integrates everything**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 3: Modeling Pipeline                  SEQUENTIAL │
│  ─────────────────────────────────────────────────────── │
│  agents/modeling_agent.py                               │
│    → Question generation for model selection             │
│    → Algorithm routing based on problem type             │
│    → Cross-validation execution                          │
│    → MLflow integration (log params, metrics, artifacts) │
│    → Statistical model comparison                        │
│    → Best model selection + retraining                   │
│                                                         │
│  evaluation/model_comparator.py                         │
│    → Paired t-test on CV folds                           │
│    → McNemar's test (classification)                     │
│    → Wilcoxon signed-rank                                │
│                                                         │
│  evaluation/bootstrap_ci.py                             │
│    → Bootstrap confidence intervals for any metric       │
│                                                         │
│  evaluation/domain_metrics.py                           │
│    → KS, Gini (finance)                                  │
│    → Sensitivity/Specificity/NNT (healthcare)            │
│    → RFM scores (ecommerce)                              │
│    → OEE (manufacturing)                                 │
│                                                         │
│  validation/model_validator.py                          │
│    → Performance threshold checks                        │
│    → Overfitting detection                               │
│                                                         │
│  validation/data_drift_checker.py                       │
│    → KS test for feature drift                           │
│    → PSI calculation                                     │
└─────────────────────────────────────────────────────────┘
```

**Deliverables:** End-to-end pipeline: data → profiling → EDA → features → trained models with MLflow

---

### PHASE 4 — Explainability + Reports + Dashboard (pages 1-5)
**Requires:** Phase 3 (trained models)
**Can run 4A, 4B, 4C in PARALLEL**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 4A: Explainability                      PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  explainability/shap_explainer.py                       │
│    → Global: summary_plot, bar_plot                      │
│    → Local: force_plot, waterfall_plot                    │
│                                                         │
│  explainability/pdp_ice.py                              │
│    → Partial dependence + ICE plots                      │
│                                                         │
│  explainability/counterfactual.py                       │
│    → "What would change the prediction?"                 │
│                                                         │
│  explainability/fairness_audit.py                       │
│    → Disparate impact, equal opportunity                 │
│    → Demographic parity metrics                          │
│                                                         │
│  explainability/model_card_generator.py                 │
│    → Google model card format                            │
│                                                         │
│  explainability/what_if.py                              │
│    → Interactive feature modification                    │
│                                                         │
│  explainability/plain_english.py                        │
│    → Natural language prediction explanations             │
│                                                         │
│  explainability/adverse_action.py                       │
│    → Finance: top N reasons for rejection                 │
│                                                         │
│  explainability/calibration.py                          │
│    → Calibration curves, reliability diagrams             │
│                                                         │
│  agents/explainability_agent.py                         │
│    → Orchestrate above tools based on domain              │
│                                                         │
│  agents/tools/explainability_tools.py                   │
│    → Wrapper functions for agent access                   │
├─────────────────────────────────────────────────────────┤
│  PHASE 4B: Report Generation                   PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  reports/templates/base_report.html                     │
│  reports/templates/styles.css                           │
│  reports/templates/healthcare_report.html               │
│  reports/templates/finance_report.html                  │
│  reports/templates/ecommerce_report.html                │
│  reports/templates/executive_template.html              │
│                                                         │
│  reports/generators/html_report.py                      │
│  reports/generators/pdf_report.py                       │
│  reports/generators/executive_summary.py                │
│  reports/generators/notebook_export.py                  │
│  reports/generators/zip_packager.py                     │
│                                                         │
│  agents/tools/report_tools.py                           │
│  agents/report_agent.py                                 │
├─────────────────────────────────────────────────────────┤
│  PHASE 4C: Dashboard Pages 1-5                 PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  dashboard/pages/01_upload.py                           │
│    → File uploader, connector selection, data preview    │
│    → Multi-source management, join UI                    │
│                                                         │
│  dashboard/pages/02_configure.py                        │
│    → Domain badge, mode selector, target picker          │
│    → Goal input, problem type confirmation               │
│                                                         │
│  dashboard/pages/03_eda_interactive.py                  │
│    → Question renderer integration                       │
│    → Chart container + Plotly charts                      │
│    → Statistical results table                            │
│    → AI insights display                                  │
│                                                         │
│  dashboard/pages/04_feature_engineering.py              │
│    → Per-column table with dropdowns                     │
│    → Domain recommendation badges                         │
│    → Feature importance preview chart                     │
│                                                         │
│  dashboard/pages/05_modeling.py                         │
│    → Algorithm selection (Guided/Expert)                  │
│    → Training progress display                            │
│    → Model comparison table + charts                      │
│    → Statistical comparison results                       │
│                                                         │
│  dashboard/components/ (remaining)                      │
│    → Complete: mode_selector, domain_badge                │
│    → Complete: approval_widget, metric_cards              │
│    → Complete: chart_container, download_buttons          │
└─────────────────────────────────────────────────────────┘

 4A ──┐
      ├──► All run in PARALLEL
 4B ──┤
      │
 4C ──┘
```

**Deliverables:** SHAP explanations, fairness audits, HTML/PDF reports, working dashboard pages 1-5

---

### PHASE 5 — Dashboard Pages 6-9 + Follow-Up + Predictions
**Requires:** Phase 4 (all three)
**Sequential — integrates UI with explain + reports**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 5: Advanced Dashboard                 SEQUENTIAL │
│  ─────────────────────────────────────────────────────── │
│  dashboard/pages/06_explainability.py                   │
│    → SHAP visualization (global + local)                 │
│    → Fairness audit display                              │
│    → What-if interactive controls                        │
│    → Model card rendering                                │
│                                                         │
│  dashboard/pages/07_predict.py                          │
│    → New data upload for batch predictions               │
│    → Single-row prediction form                          │
│    → Real-time explanation display                       │
│    → Schema validation feedback                          │
│                                                         │
│  dashboard/pages/08_chat.py                             │
│    → Chat interface (st.chat_input / st.chat_message)    │
│    → Follow-up agent integration                         │
│    → Tool registry search for on-demand analysis         │
│    → Chart generation from natural language               │
│                                                         │
│  dashboard/pages/09_download.py                         │
│    → Report format selector                              │
│    → Download buttons for all output types                │
│    → ZIP package generator                                │
│                                                         │
│  agents/followup_agent.py                               │
│    → ChromaDB semantic search                            │
│    → Tool registry lookup                                │
│    → On-demand analysis execution                        │
│    → Conversational context management                    │
└─────────────────────────────────────────────────────────┘
```

**Deliverables:** Complete dashboard (all 9 pages functional), conversational follow-up working

---

### PHASE 6 — API Serving + Sessions + Tests
**Requires:** Phase 5 (full pipeline)
**Can run 6A, 6B, 6C in PARALLEL**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 6A: API Serving                         PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  serving/api.py         → POST /predict endpoint         │
│  serving/schemas.py     → Pydantic request/response      │
│  serving/model_loader.py → MLflow model loading          │
│  serving/Dockerfile     → Container for API              │
│                                                         │
│  agents/deployment_agent.py                             │
│    → Auto-generate FastAPI endpoint from trained model    │
├─────────────────────────────────────────────────────────┤
│  PHASE 6B: Session Management                  PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  session/session_manager.py  → Save/resume/list/delete   │
│  session/session_compare.py  → Diff two sessions         │
│  session/session_export.py   → JSON export for sharing   │
│                                                         │
│  logging_audit/audit_trail_export.py                    │
│    → Compliance export (HIPAA, model risk)                │
├─────────────────────────────────────────────────────────┤
│  PHASE 6C: Test Suite                          PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  tests/conftest.py           → Complete fixtures         │
│  tests/unit/ (9 files)       → All tool function tests   │
│  tests/integration/ (4 files)→ Full pipeline tests       │
│  tests/agent/ (3 files)      → Decision quality tests    │
│  Target: 80%+ coverage on tools                          │
└─────────────────────────────────────────────────────────┘

 6A ──┐
      ├──► All run in PARALLEL
 6B ──┤
      │
 6C ──┘
```

**Deliverables:** Prediction API, session management, 80%+ test coverage

---

### PHASE 7 — Polish + Extended Connectors + Deployment
**Requires:** Phase 6 complete
**Can run 7A, 7B, 7C in PARALLEL**

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 7A: Extended Connectors                 PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  database_connectors/                                   │
│    → postgres, mysql, sqlserver, bigquery, snowflake     │
│  api_connectors/                                        │
│    → rest_api, kaggle, huggingface, google_sheets        │
│    → web_scraper                                         │
│  cloud_connectors/                                      │
│    → s3, gcs, azure_blob                                 │
│  file_connectors/ (remaining)                           │
│    → compressed, pdf, xml, statistical, sqlite           │
│  direct_input/                                          │
│    → clipboard_parser, manual_entry, sample_datasets     │
├─────────────────────────────────────────────────────────┤
│  PHASE 7B: Benchmarks + Evaluation            PARALLEL  │
│  ─────────────────────────────────────────────────────── │
│  evaluation/agent_evaluator.py                          │
│  tests/benchmarks/run_benchmarks.py                     │
│  scripts/download_sample_datasets.py (complete)         │
│  scripts/run_benchmarks.py (complete)                   │
│  Run on 8+ datasets across 6 domains                     │
│  Populate benchmark_results.json                         │
├─────────────────────────────────────────────────────────┤
│  PHASE 7C: Deployment + Documentation          PARALLEL │
│  ─────────────────────────────────────────────────────── │
│  docker-compose.yml     → Verify working                 │
│  Dockerfile.dashboard   → Complete                       │
│  README.md              → Final version with demo GIF    │
│  docs/                  → Update all doc files            │
│  scripts/generate_demo_gif.py                            │
│  Streamlit Cloud / HuggingFace deployment                │
└─────────────────────────────────────────────────────────┘

 7A ──┐
      ├──► All run in PARALLEL
 7B ──┤
      │
 7C ──┘
```

**Deliverables:** 30+ connectors, benchmark results, deployment-ready platform

---

## Parallelization Summary

```
PHASE    SUB-PHASES     PARALLEL?    DEPENDS ON
──────────────────────────────────────────────────
  1      1A, 1B, 1C     ✅ YES       Nothing (foundation)
  2      2A, 2B, 2C     ✅ YES       Phase 1
  3      (single)       ❌ NO        Phase 2A + 2B
  4      4A, 4B, 4C     ✅ YES       Phase 3
  5      (single)       ❌ NO        Phase 4 (all)
  6      6A, 6B, 6C     ✅ YES       Phase 5
  7      7A, 7B, 7C     ✅ YES       Phase 6
```

**Maximum parallelism per phase:**

| Phase | Parallel Tracks | Workers |
|-------|----------------|---------|
| 1     | Stats+Data / Viz+Feature / ML+Connectors | 3 |
| 2     | Agents / Domains / Logging+Validation | 3 |
| 3     | Single track (integrates 2A+2B) | 1 |
| 4     | Explainability / Reports / Dashboard | 3 |
| 5     | Single track (integrates 4A+4B+4C) | 1 |
| 6     | API / Sessions / Tests | 3 |
| 7     | Connectors / Benchmarks / Deploy | 3 |

---

## Critical Path (Minimum Sequential Chain)

```
Phase 1 (any track) → Phase 2A → Phase 3 → Phase 4C → Phase 5
```

This is the longest dependency chain. Everything else branches off and runs parallel.

---

## MVP Milestones

### MVP-1: "It runs" (Phase 1 + 2A)
CSV upload → auto profiling → EDA with charts → feature engineering
No modeling, no reports, no dashboard pages

### MVP-2: "End-to-end" (+ Phase 3)
Full pipeline: upload → profile → EDA → features → train → evaluate
CLI/notebook only, no dashboard

### MVP-3: "Demo-ready" (+ Phase 4C + 5)
Working Streamlit dashboard with all 9 pages
Explainability + reports downloadable

### MVP-4: "Production" (+ Phase 6 + 7)
API serving, session management, test coverage, benchmarks, deployment
