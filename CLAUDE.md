# CLAUDE.md — AutoDS: Autonomous Data Science Platform

## Project Identity

**AutoDS** is an autonomous, multi-agent data science platform that takes any dataset from any source, detects the industry domain, and produces complete data analyst + data scientist level outputs — from EDA reports to deployed ML models — with full user control over every analytical decision.

This is NOT a simple AutoML tool. This is NOT a RAG chatbot. This is a genuine multi-agent system where 8 specialized AI agents collaborate through a LangGraph state machine to execute the entire data science workflow autonomously, with human-in-the-loop checkpoints at every critical decision.

---

## IMPLEMENTATION STATUS (Updated 2026-04-24)

```
OVERALL: 100% complete | Phase 1-7 DONE + AUDITED + CI/CD configured

SECURITY & BUG AUDIT #1 ✅ COMPLETE (2026-04-24)
  36 fixes applied across 18 files:
  - 11 CRITICAL bugs fixed (SQL injection, XSS, wrong function names, state key mismatches, etc.)
  - 14 HIGH bugs fixed (deprecated pandas APIs, path traversal, Zip Slip, XXE, pickle.load, etc.)
  - All deprecated pandas 2.2+ APIs removed (infer_datetime_format, is_categorical_dtype)
  - Provider-aware LLM cost tracking (was hardcoded to Anthropic)
  - 32/32 modules verified import-clean after fixes

COMPREHENSIVE AUDIT #2 ✅ COMPLETE (2026-04-24)
  5-agent parallel audit across ALL phases found 62 bugs. 31 CRITICAL+HIGH fixed:
  CRITICAL fixes (15):
  - AUTO mode graph routing: skipped question nodes → empty analyses (core/graph.py)
  - to_dict() missing eda_questions/feature_questions → domain questions never reached agents (base_domain.py)
  - fairness_config key mismatch: "fairness_config" vs "fairness" → fairness audit never triggered (base_domain.py, orchestrator.py)
  - build_workflow interrupt_before applied to ALL modes → AUTO pipeline hung (core/graph.py)
  - SQL injection in postgres/mysql/redshift get_preview() (3 database connectors)
  - SSRF in rest_api next_url pagination → followed attacker-controlled URLs (rest_api_connector.py)
  - SSRF in web_scraper → no private IP blocking (web_scraper.py)
  - SQL injection in universal_loader load_to_duckdb (universal_loader.py)
  - SSRF in DuckDB connector remote file_path (duckdb_connector.py)
  - Path traversal in session_manager (session_manager.py)
  - Path traversal in download pages (09_download.py, download_buttons.py)
  - XSS in report_agent SHAP/fairness JSON (report_agent.py)
  - XSS in model_card_generator feature names (model_card_generator.py)
  HIGH fixes (16):
  - query_duckdb: added read-only SQL guard (data_tools.py)
  - time_series_plot: NaN guard on first value (viz_tools.py)
  - rfm_segmentation: fallback scoring direction fixed (domain_tools.py)
  - compare_models: wrong arg type + select_best_model return structure (modeling_agent.py)
  - best_model key mismatch: now writes both keys (modeling_agent.py)
  - input_sanitizer: None→"None" string not restored to NaN (input_sanitizer.py)
  - notebook export: pickle.load → joblib.load (report_agent.py)
  - KS decile table: last decile mask dropped lower bound (domain_metrics.py)
  - connector_factory: removed pickle, added 4 public data connectors (connector_factory.py)
  - CI coverage threshold: 60% → 80% (ci.yml)
  - Bandit || true removed → security failures now block CI (ci.yml)
  - SQLite connector: connection leak on exception (sqlite_connector.py)
  - automl_train: f1 → f1_weighted for classification (ml_tools.py)
  - GCS blob.size None: use get_blob() for metadata (gcs_connector.py)
  - Serving API: added optional API key auth (serving/api.py)
  - Serving API: generic error messages, no internal detail leaks (serving/api.py)
  - PLATFORM_VERSION bumped to 1.0.0 (constants.py)
  26/26 modified modules verified import-clean after fixes

CLEANUP AUDIT #3 ✅ COMPLETE (2026-04-24)
  Resolved remaining MEDIUM/LOW bugs from audit #2:
  MEDIUM fixes (12):
  - report_tools.py: populated with re-exports from reports/generators/ (was empty stub)
  - explainability_tools.py: populated with re-exports from explainability/ (was empty stub)
  - configs/loader.py: created YAML config loader for agent_prompts.yaml & domain_configs.yaml
  - orchestrator: multi-word keyword matching now checks phrases before single-word split
  - data_profiler: _classify_cardinality returns "constant" for nunique=0/1 (was "binary")
  - stats_tools: VIF threshold now imports from constants.py instead of hardcoded literal
  - edge_case_detector: NaN guard uses pd.notna() for correlation checks (was `is not None`)
  - multi_source_manager.py: fully implemented (add/remove/list sources, join via pandas merge)
  - schema_matcher.py: fully implemented (name similarity, dtype compat, value overlap scoring)
  - release.yml: Docker images now pushed to ghcr.io with login-action + GITHUB_TOKEN
  - release.yml: added packages:write permission for container registry access
  NOT BUGS (verified working as intended):
  - Generic domain EDA questions: unique, no duplicates with base class
  - SPC control limits: A3 = 3/sqrt(n) is correct X-bar/S chart approximation
  - Mann-Whitney: already computes rank-biserial manually (no SciPy version dep)
  - Dashboard workflow_progress.py: reads completed_steps/current_step matching agent writes

PHASE 1 — FOUNDATION TOOLS ✅ COMPLETE
  [x] agents/tools/stats_tools.py    1207 lines  16 statistical test functions
  [x] agents/tools/data_tools.py      742 lines  15 data manipulation functions
  [x] agents/tools/viz_tools.py       675 lines  25 Plotly chart generators
  [x] agents/tools/feature_tools.py   981 lines  30 feature engineering functions
  [x] agents/tools/ml_tools.py        617 lines  15 ML training/evaluation functions
  [x] agents/tools/domain_tools.py   1487 lines  22 domain-specific calculations
  [x] agents/tools/tool_registry.py   291 lines  Registry + search + import (40 entries verified)
  [x] file_connectors/csv            161 lines  Full auto-detect delimiter/encoding
  [x] file_connectors/excel           59 lines  Sheet selection, multi-sheet
  [x] file_connectors/json            74 lines  JSON/JSONL/nested auto-flatten
  [x] file_connectors/parquet         56 lines  Parquet + Feather + ORC
  [x] file_connectors/compressed     136 lines  ZIP/GZ/TAR extract + scan
  [x] file_connectors/statistical     95 lines  SAS/STATA/SPSS/HDF5
  [x] file_connectors/pdf            116 lines  tabula-py + camelot fallback
  [x] file_connectors/sqlite         110 lines  Table listing + SQL query

PHASE 2 — AGENTS + DOMAINS + INFRASTRUCTURE ✅ COMPLETE
  [x] agents/orchestrator.py         310 lines  Full supervisor: goal decomp, problem type, target detection, pipeline config
  [x] agents/domain_detector.py       40 lines  Domain detection via registry
  [x] agents/data_profiler.py        415 lines  Schema detection, quality scoring, cleaning recs
  [x] agents/eda_agent.py            821 lines  Question generation + analysis execution + LLM summary
  [x] agents/feature_engineer.py     779 lines  Per-column decisions + domain feature creation
  [x] agents/modeling_agent.py       678 lines  Algorithm selection + training + evaluation + MLflow
  [x] agents/explainability_agent.py 517 lines  SHAP + fairness audit + model card
  [x] agents/report_agent.py         522 lines  HTML + executive summary + notebook + ZIP
  [x] agents/deployment_agent.py     428 lines  FastAPI + Pydantic + Dockerfile generation
  [x] agents/followup_agent.py       358 lines  Intent routing + tool dispatch
  [x] domains/healthcare.py          212 lines  Full config + questions + fairness + compliance
  [x] domains/finance.py             187 lines  Full config + KS/Gini + adverse action
  [x] domains/ecommerce.py           166 lines  Full config + RFM/CLV + funnel
  [x] domains/marketing.py           164 lines  Full config + CTR/ROAS + attribution
  [x] domains/hr.py                  188 lines  Full config + diversity + compensation equity
  [x] domains/manufacturing.py       182 lines  Full config + OEE/MTBF + SPC
  [x] domains/generic.py             197 lines  Full fallback config
  [x] logging_audit/structured_logger 201 lines  JSONL timestamped logging
  [x] logging_audit/decision_log      119 lines  Agent decision tracking
  [x] logging_audit/performance_log   142 lines  Step timing + context manager
  [x] logging_audit/cost_tracker      153 lines  Token-based cost tracking
  [x] validation/input_sanitizer      358 lines  Encoding, mixed types, dates
  [x] validation/edge_case_detector   358 lines  9 edge case checks
  [x] validation/schema_validator     303 lines  Schema extraction + validation
  [x] validation/model_validator      359 lines  Performance + integrity checks
  [x] validation/data_drift_checker   285 lines  KS test + PSI calculation
  [x] configs/agent_prompts.yaml      240 lines  Full chain-of-thought prompts per agent
  [x] configs/domain_configs.yaml     207 lines  All 7 domains configured

CORE INFRASTRUCTURE ✅ COMPLETE (unchanged)
  [x] core/state.py          289 lines  Full AutoDSState TypedDict
  [x] core/graph.py          250 lines  LangGraph StateGraph + orchestrator node
  [x] core/llm_config.py     430 lines  Multi-provider LLM + caching
  [x] core/memory.py         288 lines  SQLite + ChromaDB persistence
  [x] core/user_modes.py     119 lines  Auto/Guided/Expert mode logic
  [x] core/constants.py      230 lines  All global constants
  [x] core/exceptions.py     204 lines  30+ custom exceptions
  [x] connectors/base.py      86 lines  Abstract BaseConnector
  [x] connectors/factory.py  144 lines  ConnectorFactory with registry
  [x] connectors/universal.py 204 lines Smart format/encoding detection
  [x] dashboard/question_renderer  192 lines  6 question types
  [x] dashboard/workflow_progress  164 lines  7-step progress UI

PHASE 3 — MODELING PIPELINE + EVALUATION ✅ COMPLETE
  [x] agents/modeling_agent.py       678 lines  Algorithm selection + training + MLflow
  [x] evaluation/model_comparator.py 286 lines  Paired t-test, McNemar's, Wilcoxon, Friedman, Nemenyi
  [x] evaluation/_comparator_utils.py 291 lines  Shared validation + Nemenyi implementation
  [x] evaluation/bootstrap_ci.py     337 lines  Bootstrap CI, BCa correction, paired comparison
  [x] evaluation/domain_metrics.py   972 lines  11 domain-specific metrics (finance/healthcare/ecommerce/mfg/marketing)
  [x] evaluation/agent_evaluator.py  347 lines  Decision quality evaluation + 5 builtin cases
  [x] validation/model_validator.py  359 lines  Performance + integrity checks
  [x] validation/data_drift_checker.py 285 lines  KS test + PSI calculation

PHASE 4 -- EXPLAINABILITY + REPORTS + DASHBOARD ✅ COMPLETE
  Track 4A: Explainability (9 files, ~2090 lines)
  [x] explainability/shap_explainer.py     269 lines  SHAP global + local explanations
  [x] explainability/pdp_ice.py            251 lines  Partial Dependence + ICE plots
  [x] explainability/counterfactual.py     210 lines  Counterfactual explanations
  [x] explainability/fairness_audit.py     255 lines  Disparate impact, demographic parity
  [x] explainability/model_card_generator.py 364 lines  Google model card format
  [x] explainability/plain_english.py      211 lines  Natural language explanations
  [x] explainability/what_if.py            147 lines  Interactive what-if analysis
  [x] explainability/adverse_action.py     163 lines  Finance adverse action notices
  [x] explainability/calibration.py        220 lines  Calibration curves + reliability

  Track 4B: Reports (5 generators + 6 templates, ~1466 lines)
  [x] reports/generators/html_report.py    340 lines  Interactive HTML + Plotly
  [x] reports/generators/pdf_report.py     157 lines  Print-ready PDF via weasyprint
  [x] reports/generators/executive_summary.py 248 lines  1-page executive PDF
  [x] reports/generators/notebook_export.py  482 lines  Runnable Jupyter notebook
  [x] reports/generators/zip_packager.py   124 lines  ZIP package of all outputs
  [x] reports/templates/* (6 files)        353 lines  HTML + CSS templates

  Track 4C: Dashboard Pages + App (9 pages + app, ~2754 lines)
  [x] dashboard/app.py                    190 lines  Main entry + routing + upload
  [x] dashboard/pages/01_upload.py         217 lines  Multi-source data upload
  [x] dashboard/pages/02_configure.py      205 lines  Domain + mode + target config
  [x] dashboard/pages/03_eda_interactive.py 257 lines  Interactive EDA + questions
  [x] dashboard/pages/04_feature_engineering.py 314 lines  Per-column decisions
  [x] dashboard/pages/05_modeling.py       417 lines  Algorithm selection + training + results
  [x] dashboard/pages/06_explainability.py 341 lines  SHAP/PDP/CF/fairness/what-if/card
  [x] dashboard/pages/07_predict.py        248 lines  Batch + single predictions
  [x] dashboard/pages/08_chat.py           222 lines  Follow-up conversational UI
  [x] dashboard/pages/09_download.py       275 lines  Reports/data/model/audit downloads
  [x] dashboard/components/* (8 files)     949 lines  Reusable UI components

PHASE 5 -- SERVING + SESSIONS + TESTS ✅ COMPLETE
  Track 5A: Model Serving API (3 files, 465 lines)
  [x] serving/api.py                   220 lines  FastAPI /predict, /predict/batch, /health, /info, /reload
  [x] serving/schemas.py               107 lines  Pydantic request/response models
  [x] serving/model_loader.py          138 lines  Joblib + MLflow model loading with caching
  [x] serving/Dockerfile                14 lines  Production container

  Track 5B: Session Management (3 files, 518 lines)
  [x] session/session_manager.py       177 lines  SQLite-backed save/load/list/delete
  [x] session/session_compare.py       178 lines  Config, metric, feature, model diff
  [x] session/session_export.py        163 lines  Portable JSON export + import

  Track 5C: Test Suite (12 files, 3774 new lines + 4243 existing = 8017 total)
  [x] tests/unit/test_domain_detection.py  935 lines  74 tests — domain detection + confidence
  [x] tests/unit/test_domain_tools.py      555 lines  41 tests — healthcare/finance/ecommerce/mfg tools
  [x] tests/unit/test_edge_cases.py        650 lines  65 tests — 9 edge case detectors
  [x] tests/unit/test_schema_validation.py 648 lines  46 tests — schema extract/validate/adapt
  [x] tests/unit/test_report_generation.py 260 lines  20 tests — HTML/notebook/exec/zip generators
  [x] tests/unit/test_statistical_tools.py 1046 lines (existing)
  [x] tests/unit/test_feature_tools.py     1248 lines (existing)
  [x] tests/unit/test_ml_tools.py          962 lines (existing)
  [x] tests/unit/test_viz_tools.py         937 lines (existing)
  [x] tests/unit/test_connectors.py        1050 lines (existing)
  [x] tests/integration/test_full_pipeline.py 215 lines  Pipeline + session round-trip
  [x] tests/integration/test_healthcare_path.py 66 lines  Healthcare domain path
  [x] tests/integration/test_finance_path.py   91 lines  Finance domain path
  [x] tests/integration/test_ecommerce_path.py 76 lines  E-commerce domain path
  [x] tests/agent/test_eda_recommendations.py  82 lines  EDA question generation
  [x] tests/agent/test_model_selection.py      91 lines  Algorithm selection
  [x] tests/agent/test_profiler_decisions.py   105 lines  Profiler decisions

PHASE 6 -- EXTENDED CONNECTORS + BENCHMARKS + DOCS ✅ COMPLETE
  Track 6A: Extended Connectors (21 files implemented)
  [x] database_connectors/ — postgres, mysql, sqlserver, duckdb, bigquery, snowflake, redshift
  [x] api_connectors/ — rest_api, web_scraper, kaggle, huggingface, google_sheets
  [x] api_connectors/public_data/ — world_bank, fred, yahoo_finance, census
  [x] cloud_connectors/ — s3, gcs, azure_blob
  [x] direct_input/ — clipboard_parser, manual_entry

  Track 6B: Benchmarks + Evaluation (3 files)
  [x] evaluation/benchmarks/benchmark_runner.py   ~300 lines  BenchmarkRunner class
  [x] scripts/download_sample_datasets.py          ~235 lines  10-dataset catalog (6 domains)
  [x] tests/benchmarks/run_benchmarks.py           ~70 lines   CLI entry point

  Track 6C: Documentation + Scripts (9 files)
  [x] docs/architecture.md                Full system architecture
  [x] docs/api_reference.md               FastAPI endpoint docs
  [x] docs/user_guide.md                  Comprehensive user guide
  [x] docs/developer_guide.md             Adding connectors/tools/domains
  [x] docs/domain_guide.md                Domain detection + adaptation
  [x] docs/deployment_guide.md            Docker/Cloud/HuggingFace deploy
  [x] docs/tool_registry_reference.md     Complete tool reference
  [x] scripts/run_benchmarks.py           Benchmark CLI wrapper
  [x] scripts/generate_demo_gif.py        Playwright-based GIF capture

PHASE 7 — CI/CD + BENCHMARKS + RELEASE ✅ COMPLETE (2026-04-24)
  [x] .github/workflows/ci.yml — Lint, typecheck, test matrix (3.11+3.12), coverage, security scan
  [x] .github/workflows/release.yml — Tag-triggered release with changelog + Docker build
  [x] .github/workflows/benchmark.yml — Weekly benchmark runs + manual dispatch
  [x] evaluation/benchmarks/benchmark_results.json — 10 datasets, 5 domains, all passing
  [x] pyproject.toml version bumped to 1.0.0
  [ ] Demo GIF recording (manual step: python scripts/generate_demo_gif.py)
  [ ] Tag v1.0.0 release (manual step: git tag v1.0.0 && git push --tags)
```

## PROJECT STATUS: v1.0.0 RELEASE READY

**All 7 phases complete.** See `docs/DEVELOPMENT_PHASES.md` for full roadmap.

Manual steps remaining for release:
```
1. Record demo GIF: python scripts/generate_demo_gif.py
2. Tag release: git tag v1.0.0 && git push --tags
3. Optional: Deploy to Streamlit Cloud / HuggingFace Spaces
```

---

## Architecture Overview

```
User Input (any data source) 
    → Domain Detection (healthcare/finance/ecommerce/hr/manufacturing/marketing/generic)
    → User Mode Selection (Auto/Guided/Expert)
    → Orchestrator Agent (LangGraph StateGraph with conditional routing)
        → Data Profiler Agent (schema detection, quality assessment, cleaning)
        → EDA Agent (domain-aware exploratory analysis with interactive questions)
        → Feature Engineering Agent (domain-aware feature creation with user choices)
        → Modeling Agent (domain-aware model selection, training, evaluation)
        → Explainability Agent (SHAP, counterfactuals, fairness, model cards)
        → Report Agent (HTML/PDF/executive summary/Jupyter notebook generation)
        → Deployment Agent (FastAPI endpoint packaging)
        → Follow-Up Agent (post-pipeline "ask anything" conversational interface)
    → Outputs (dashboard, reports, predictions, downloads)
```

## Tech Stack

| Component | Tool | Version |
|---|---|---|
| Language | Python | 3.11+ |
| Agent Framework | LangGraph | latest |
| LLM | Claude API (Anthropic) | claude-sonnet-4-20250514 |
| LLM Client | langchain-anthropic | latest |
| Data Warehouse | DuckDB | latest |
| Data Profiling | ydata-profiling | latest |
| Data Quality | great-expectations | latest |
| AutoML | FLAML | latest |
| ML Core | scikit-learn | latest |
| Gradient Boosting | xgboost, lightgbm, catboost | latest |
| Explainability | shap | latest |
| Fairness | fairlearn | latest |
| Statistics | scipy, statsmodels, lifelines | latest |
| Visualization | plotly | latest |
| Experiment Tracking | mlflow | latest |
| Vector Store (memory) | chromadb | latest |
| Dashboard | streamlit | latest |
| Model Serving | fastapi, uvicorn | latest |
| Report Generation | jinja2, weasyprint, nbformat | latest |
| PDF Tables | tabula-py, camelot-py | latest |
| Web Scraping | beautifulsoup4, requests | latest |
| Testing | pytest, pytest-cov | latest |

## Directory Structure — EVERY FILE AND ITS PURPOSE

```
autods-platform/
│
├── CLAUDE.md                          # THIS FILE — master instructions for Claude Code
├── README.md                          # Public-facing project documentation
├── requirements.txt                   # Pinned Python dependencies
├── requirements-dev.txt               # Dev/test dependencies
├── setup.py                           # Package setup for pip install -e .
├── Makefile                           # Common commands: make run, make test, make benchmark
├── .env.example                       # Template for environment variables
├── .gitignore                         # Git ignore rules
├── pyproject.toml                     # Project metadata and tool configs
│
├── agents/                            # ALL AI AGENTS
│   ├── __init__.py
│   ├── orchestrator.py                # LangGraph supervisor — the brain
│   ├── domain_detector.py             # Detects industry domain from data
│   ├── data_profiler.py               # Schema detection + quality + cleaning
│   ├── eda_agent.py                   # Domain-aware exploratory data analysis
│   ├── feature_engineer.py            # Domain-aware feature creation
│   ├── modeling_agent.py              # Model selection, training, evaluation
│   ├── explainability_agent.py        # SHAP, counterfactuals, fairness, model cards
│   ├── report_agent.py               # Report generation (HTML/PDF/notebook)
│   ├── deployment_agent.py            # FastAPI endpoint packaging
│   ├── followup_agent.py             # Post-pipeline conversational "ask anything"
│   └── tools/                         # Python tool functions agents call
│       ├── __init__.py
│       ├── data_tools.py              # pandas, DuckDB, file I/O operations
│       ├── viz_tools.py               # 25+ Plotly chart generator functions
│       ├── stats_tools.py             # 20+ statistical test functions
│       ├── ml_tools.py                # sklearn, xgboost, FLAML, model training
│       ├── feature_tools.py           # Feature engineering functions by type
│       ├── domain_tools.py            # Domain-specific calculations (Charlson, RFM, KS, etc.)
│       ├── report_tools.py            # HTML/PDF/notebook generation utilities
│       ├── explainability_tools.py    # SHAP, PDP, counterfactual, fairness tools
│       └── tool_registry.py           # Master registry of ALL available tools with metadata
│
├── core/                              # CORE INFRASTRUCTURE
│   ├── __init__.py
│   ├── graph.py                       # LangGraph workflow definition (StateGraph, nodes, edges)
│   ├── state.py                       # Shared workflow state schema (TypedDict)
│   ├── memory.py                      # SQLite persistence + ChromaDB vector memory
│   ├── llm_config.py                  # Claude API setup and configuration
│   ├── user_modes.py                  # Auto / Guided / Expert mode logic
│   ├── exceptions.py                  # Custom exception classes
│   └── constants.py                   # Global constants, default configs
│
├── data_connectors/                   # CONNECT TO ANY DATA SOURCE
│   ├── __init__.py
│   ├── base.py                        # Abstract base connector interface
│   ├── connector_factory.py           # Factory pattern — returns correct connector
│   ├── universal_loader.py            # Smart loader: auto-detect format, encoding, delimiter
│   ├── multi_source_manager.py        # Manage multiple loaded sources + joins
│   ├── schema_matcher.py              # Match columns across sources for joining
│   │
│   ├── file_connectors/
│   │   ├── __init__.py
│   │   ├── csv_connector.py           # CSV with auto-detect delimiter, encoding, header
│   │   ├── excel_connector.py         # Excel with sheet selection
│   │   ├── parquet_connector.py       # Parquet, Feather, ORC, Arrow
│   │   ├── json_connector.py          # JSON flat + nested auto-flatten + JSONL
│   │   ├── xml_connector.py           # XML table extraction
│   │   ├── compressed_connector.py    # ZIP, GZ, TAR.GZ — extract and find tabular files
│   │   ├── statistical_connector.py   # SAS (.sas7bdat), STATA (.dta), SPSS (.sav), HDF5
│   │   ├── pdf_connector.py           # PDF table extraction via tabula-py / camelot
│   │   └── sqlite_connector.py        # SQLite .db file upload and table selection
│   │
│   ├── database_connectors/
│   │   ├── __init__.py
│   │   ├── postgres_connector.py      # PostgreSQL via psycopg2/sqlalchemy
│   │   ├── mysql_connector.py         # MySQL/MariaDB via pymysql/sqlalchemy
│   │   ├── sqlserver_connector.py     # MS SQL Server via pyodbc/sqlalchemy
│   │   ├── duckdb_connector.py        # DuckDB remote file connection
│   │   ├── bigquery_connector.py      # Google BigQuery via service account
│   │   ├── snowflake_connector.py     # Snowflake via snowflake-connector
│   │   └── redshift_connector.py      # Amazon Redshift via sqlalchemy
│   │
│   ├── api_connectors/
│   │   ├── __init__.py
│   │   ├── rest_api_connector.py      # Generic REST API (URL, method, headers, auth, pagination)
│   │   ├── web_scraper.py             # HTML table extraction via pandas.read_html + BeautifulSoup
│   │   ├── kaggle_connector.py        # Kaggle dataset download via kaggle API
│   │   ├── huggingface_connector.py   # HuggingFace datasets library
│   │   ├── google_sheets_connector.py # Public Google Sheets via CSV export URL
│   │   └── public_data/
│   │       ├── __init__.py
│   │       ├── world_bank.py          # World Bank Open Data API
│   │       ├── fred.py                # Federal Reserve Economic Data API
│   │       ├── yahoo_finance.py       # Stock data via yfinance
│   │       └── census.py              # US Census Bureau API
│   │
│   ├── cloud_connectors/
│   │   ├── __init__.py
│   │   ├── s3_connector.py            # AWS S3 bucket access
│   │   ├── gcs_connector.py           # Google Cloud Storage
│   │   └── azure_blob_connector.py    # Azure Blob Storage
│   │
│   └── direct_input/
│       ├── __init__.py
│       ├── clipboard_parser.py        # Parse pasted table data (tab/comma/HTML)
│       ├── manual_entry.py            # Manual table builder UI
│       └── sample_datasets.py         # Built-in sample datasets for testing/demo
│
├── domains/                           # INDUSTRY DOMAIN CONFIGURATIONS
│   ├── __init__.py
│   ├── base_domain.py                 # Abstract base domain config
│   ├── domain_registry.py             # Registry of all domains + detection logic
│   ├── healthcare.py                  # Healthcare: metrics, ICD handling, clinical thresholds,
│   │                                  #   Charlson/Elixhauser, survival analysis, HIPAA awareness,
│   │                                  #   fairness by demographics, clinical report style
│   ├── finance.py                     # Finance: KS/Gini, PSI, vintage analysis, cost-sensitive
│   │                                  #   learning, adverse action codes, scorecard output,
│   │                                  #   fair lending compliance, financial report style
│   ├── ecommerce.py                   # E-commerce: RFM, CLV, funnel analysis, cohort retention,
│   │                                  #   basket analysis, seasonal decomposition, business style
│   ├── marketing.py                   # Marketing: CTR, ROAS, attribution models, campaign lift,
│   │                                  #   A/B testing, channel analysis
│   ├── hr.py                          # HR: attrition, diversity metrics, compensation equity,
│   │                                  #   sensitivity constraints, anonymization
│   ├── manufacturing.py               # Manufacturing: OEE, MTBF, predictive maintenance,
│   │                                  #   sensor anomaly, quality control, SPC charts
│   └── generic.py                     # Generic: fallback for unknown domains, standard DS practices
│
├── dashboard/                         # STREAMLIT WEB APPLICATION
│   ├── __init__.py
│   ├── app.py                         # Main Streamlit entry point
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── 01_upload.py               # Data upload from any source + multi-source management
│   │   ├── 02_configure.py            # Domain confirmation + mode selection + target + goals
│   │   ├── 03_eda_interactive.py      # Interactive EDA with domain-specific questions
│   │   ├── 04_feature_engineering.py  # Interactive feature engineering with per-column choices
│   │   ├── 05_modeling.py             # Interactive model selection + training + results
│   │   ├── 06_explainability.py       # SHAP, counterfactuals, what-if, fairness, model card
│   │   ├── 07_predict.py             # Upload new data for predictions + single-row prediction
│   │   ├── 08_chat.py                # Follow-up "ask anything" conversational interface
│   │   └── 09_download.py            # Download all reports, data, models, notebooks
│   └── components/
│       ├── __init__.py
│       ├── mode_selector.py           # Auto/Guided/Expert toggle widget
│       ├── domain_badge.py            # Shows detected domain with icon
│       ├── approval_widget.py         # Human-in-the-loop approval UI
│       ├── download_buttons.py        # Download buttons for all output types
│       ├── question_renderer.py       # Renders interactive questions (single-select, multi-select,
│       │                              #   sliders, per-column tables with dropdowns)
│       ├── workflow_progress.py       # Live workflow step progress indicator
│       ├── metric_cards.py            # KPI metric display cards
│       └── chart_container.py         # Plotly chart container with export buttons
│
├── validation/                        # DATA & MODEL VALIDATION
│   ├── __init__.py
│   ├── schema_validator.py            # Validate prediction data matches training schema
│   ├── edge_case_detector.py          # Detect: single-class target, target leakage,
│   │                                  #   too few rows, constant columns, perfect multicollinearity,
│   │                                  #   mixed types, extreme imbalance
│   ├── data_drift_checker.py          # Check feature distributions drift (KS test, PSI)
│   ├── input_sanitizer.py             # Handle encoding issues, mixed types, parse dates
│   └── model_validator.py             # Validate model before deployment (performance thresholds)
│
├── explainability/                    # MODEL EXPLAINABILITY & FAIRNESS
│   ├── __init__.py
│   ├── shap_explainer.py              # SHAP global (summary, bar) + local (force, waterfall)
│   ├── pdp_ice.py                     # Partial Dependence Plots + ICE plots
│   ├── counterfactual.py              # Counterfactual explanations ("what would change prediction")
│   ├── plain_english.py               # Natural language explanation of predictions
│   ├── what_if.py                     # Interactive what-if analysis (change feature → see impact)
│   ├── adverse_action.py              # Finance: top N reasons for negative decision
│   ├── fairness_audit.py              # Disparate impact, equal opportunity, demographic parity
│   ├── model_card_generator.py        # Standardized model documentation (Google model card format)
│   └── calibration.py                 # Calibration curves, reliability diagrams
│
├── evaluation/                        # MODEL EVALUATION & BENCHMARKING
│   ├── __init__.py
│   ├── agent_evaluator.py             # Test agent decision quality on known datasets
│   ├── model_comparator.py            # Statistical comparison: paired t-test, McNemar's,
│   │                                  #   Wilcoxon on CV folds, bootstrap CI
│   ├── bootstrap_ci.py                # Bootstrap confidence intervals for any metric
│   ├── domain_metrics.py              # Domain-specific evaluation (KS, Gini, NNT, etc.)
│   ├── test_datasets/                 # Known datasets for testing agent behavior
│   │   └── .gitkeep
│   └── benchmarks/
│       ├── benchmark_runner.py        # Run full pipeline on standard datasets, record results
│       ├── benchmark_results.json     # Published benchmark results
│       └── benchmark_datasets/
│           └── .gitkeep
│
├── logging_audit/                     # LOGGING & AUDIT TRAIL
│   ├── __init__.py
│   ├── structured_logger.py           # Timestamped structured logging (JSON format)
│   ├── decision_log.py                # Log every agent decision with reasoning
│   ├── performance_log.py             # Timing per step, API call counts, token usage
│   ├── cost_tracker.py                # Track Claude API costs per pipeline run
│   └── audit_trail_export.py          # Export audit trail for compliance (healthcare/finance)
│
├── session/                           # SESSION MANAGEMENT
│   ├── __init__.py
│   ├── session_manager.py             # Save/resume/list/delete sessions (SQLite-backed)
│   ├── session_compare.py             # Compare results from two sessions on same data
│   └── session_export.py              # Export session as JSON for sharing/reproducing
│
├── reports/                           # REPORT GENERATION
│   ├── __init__.py
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── html_report.py             # Interactive HTML with embedded Plotly charts
│   │   ├── pdf_report.py              # Print-ready PDF via weasyprint
│   │   ├── executive_summary.py       # 1-page PDF for senior stakeholders
│   │   ├── notebook_export.py         # Runnable Jupyter notebook with all code + comments
│   │   └── zip_packager.py            # Package all outputs into downloadable ZIP
│   └── templates/
│       ├── base_report.html           # Base HTML report template (Jinja2)
│       ├── healthcare_report.html     # Healthcare-specific report sections
│       ├── finance_report.html        # Finance-specific report sections
│       ├── ecommerce_report.html      # E-commerce-specific report sections
│       ├── executive_template.html    # Executive summary template
│       └── styles.css                 # Report styling
│
├── serving/                           # MODEL SERVING / API
│   ├── __init__.py
│   ├── api.py                         # FastAPI prediction endpoint
│   ├── schemas.py                     # Pydantic request/response schemas
│   ├── model_loader.py                # Load trained model from MLflow / pickle
│   └── Dockerfile                     # Docker containerization for API
│
├── tests/                             # TEST SUITE
│   ├── __init__.py
│   ├── conftest.py                    # Shared pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_statistical_tools.py  # Verify all stat tests produce correct results
│   │   ├── test_feature_tools.py      # Verify feature engineering functions
│   │   ├── test_domain_tools.py       # Verify domain-specific calculations
│   │   ├── test_viz_tools.py          # Verify chart generation doesn't error
│   │   ├── test_connectors.py         # Verify each connector parses correctly
│   │   ├── test_domain_detection.py   # Verify domain detection accuracy
│   │   ├── test_schema_validation.py  # Verify schema mismatch detection
│   │   ├── test_edge_cases.py         # Verify edge case detection (leakage, imbalance, etc.)
│   │   └── test_report_generation.py  # Verify report generation completes
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_full_pipeline.py      # End-to-end: upload CSV → get results
│   │   ├── test_healthcare_path.py    # Full pipeline with healthcare dataset
│   │   ├── test_finance_path.py       # Full pipeline with finance dataset
│   │   └── test_ecommerce_path.py     # Full pipeline with ecommerce dataset
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── test_profiler_decisions.py # Does profiler choose right cleaning?
│   │   ├── test_eda_recommendations.py # Does EDA agent suggest right analyses?
│   │   └── test_model_selection.py    # Does modeling agent pick right algorithms?
│   └── benchmarks/
│       ├── __init__.py
│       ├── run_benchmarks.py          # Run platform on standard datasets
│       └── benchmark_datasets/
│           └── .gitkeep
│
├── scripts/                           # UTILITY SCRIPTS
│   ├── download_sample_datasets.py    # Download benchmark datasets from Kaggle/UCI
│   ├── setup_database.py             # Initialize DuckDB + SQLite schemas
│   ├── run_benchmarks.py             # Run full benchmark suite
│   └── generate_demo_gif.py          # Script to record demo GIF for README
│
├── configs/                           # CONFIGURATION FILES
│   ├── agent_prompts.yaml             # System prompts for every agent
│   ├── domain_configs.yaml            # Domain-specific configurations
│   ├── tool_registry.yaml             # Master registry of all tools (also in Python)
│   ├── default_settings.yaml          # Default platform settings
│   └── logging_config.yaml            # Logging configuration
│
├── docs/                              # DOCUMENTATION
│   ├── architecture.md                # Detailed architecture documentation
│   ├── domain_guide.md                # How domain detection and adaptation works
│   ├── tool_registry_reference.md     # Complete reference of all tools/tests/charts
│   ├── api_reference.md               # FastAPI endpoint documentation
│   ├── user_guide.md                  # How to use the platform (with screenshots)
│   ├── developer_guide.md             # How to add new domains, connectors, tools
│   ├── deployment_guide.md            # How to deploy on Streamlit Cloud / HuggingFace
│   └── images/
│       ├── architecture_diagram.png
│       └── demo.gif
│
├── mlruns/                            # MLflow experiment tracking (gitignored)
├── logs/                              # Structured log files (gitignored)
├── sessions/                          # Saved session files (gitignored)
├── data/                              # User uploaded data (gitignored)
└── outputs/                           # Generated reports and exports (gitignored)
```

---

## CRITICAL DESIGN DECISIONS — READ BEFORE CODING

### 1. LangGraph State Machine Design

The entire workflow is a LangGraph `StateGraph`. Each agent is a node. Edges are conditional based on:
- User mode (Auto skips questions, Guided asks questions, Expert lets user specify)
- Domain (healthcare path includes fairness audit, finance includes KS/Gini)
- Data characteristics (time-series data triggers temporal analysis, text columns trigger NLP)
- User decisions at checkpoints

The state is a `TypedDict` defined in `core/state.py`. EVERY agent reads from and writes to this shared state. The state must contain:

```python
class AutoDSState(TypedDict):
    # Session
    session_id: str
    user_mode: str  # "auto" | "guided" | "expert"
    
    # Data
    data_sources: list[dict]        # List of loaded data sources with metadata
    joined_data_ref: str            # DuckDB table name for the working dataset
    data_profile: dict              # ydata-profiling output summary
    schema_info: dict               # Column names, types, cardinality, missing %
    
    # Domain
    detected_domain: str            # "healthcare" | "finance" | "ecommerce" | etc.
    domain_config: dict             # Full domain configuration object
    domain_confirmed: bool          # User confirmed/overrode domain detection
    
    # User Intent
    user_goal: str                  # Natural language description of goal
    target_column: str | None       # Target variable (None for unsupervised)
    problem_type: str               # "classification" | "regression" | "clustering" | "time_series"
    
    # EDA
    eda_questions_asked: list[dict]  # Questions asked + user responses
    eda_results: dict               # Analysis results, chart references, insights
    eda_summary: str                # AI-generated summary of findings
    
    # Feature Engineering
    fe_questions_asked: list[dict]  # Questions asked + user responses
    fe_choices: dict                # Per-column decisions (encoding, imputation, etc.)
    feature_list: list[str]         # Final feature names after engineering
    feature_importance: dict        # Preliminary feature importance scores
    
    # Modeling
    model_questions_asked: list[dict]
    model_choices: dict             # Selected algorithms, metrics, validation strategy
    trained_models: dict            # Model name → MLflow run_id mapping
    model_results: dict             # Model name → metrics dict
    best_model: str                 # Name of selected best model
    best_model_path: str            # Path to saved model artifact
    
    # Explainability
    shap_values: dict | None
    fairness_report: dict | None
    model_card: dict | None
    
    # Reports
    report_paths: dict              # Format → file path mapping
    
    # Pipeline metadata
    random_seed: int                # For reproducibility
    data_hash: str                  # Hash of input data for verification
    pipeline_log: list[dict]        # Timestamped log of all actions
    api_call_count: int             # Claude API calls made
    api_token_count: int            # Total tokens used
    errors: list[dict]              # Any errors encountered
    current_step: str               # Current pipeline step name
    completed_steps: list[str]      # Steps completed so far
```

### 2. Agent Design Pattern

Every agent follows this exact pattern:

```python
# agents/eda_agent.py (pattern example)

from core.state import AutoDSState
from core.llm_config import get_llm
from agents.tools.stats_tools import run_statistical_test
from agents.tools.viz_tools import create_chart
from agents.tools.tool_registry import get_tools_for_domain

def eda_agent(state: AutoDSState) -> AutoDSState:
    """
    EDA Agent node in the LangGraph.
    
    1. Reads data characteristics + domain from state
    2. If Guided/Expert mode: generates domain-specific questions
    3. Executes selected analyses using PYTHON TOOLS (not LLM)
    4. Uses LLM only for: choosing analyses, interpreting results, writing summaries
    5. Writes results back to state
    6. Returns updated state
    """
    
    llm = get_llm()
    mode = state["user_mode"]
    domain = state["detected_domain"]
    
    # Step 1: Determine which analyses to run
    if mode == "auto":
        # LLM decides best analyses for this domain + data
        analyses = _auto_select_analyses(state, llm)
    elif mode == "guided":
        # Generate questions, wait for user answers (via interrupt)
        questions = _generate_eda_questions(state, llm)
        # LangGraph interrupt — returns to dashboard for user input
        # User answers come back in state["eda_questions_asked"]
        analyses = _parse_user_eda_choices(state)
    else:  # expert
        # User specifies exactly what to run
        analyses = state.get("expert_eda_specs", [])
    
    # Step 2: Execute analyses using Python tools (NOT the LLM)
    results = {}
    for analysis in analyses:
        tool_fn = get_tool_function(analysis["tool_name"])
        result = tool_fn(state["joined_data_ref"], **analysis["params"])
        results[analysis["name"]] = result
    
    # Step 3: LLM interprets results and writes summary
    summary = _generate_eda_summary(results, state, llm)
    
    # Step 4: Update state
    state["eda_results"] = results
    state["eda_summary"] = summary
    state["completed_steps"].append("eda")
    state["current_step"] = "feature_engineering"
    
    return state
```

KEY PRINCIPLE: **LLM decides WHAT to do. Python tools DO it.** The LLM never computes statistics, trains models, or generates charts directly. It routes to registered Python functions that are deterministic and tested.

### 3. Tool Registry Design

The tool registry is the system's "memory" — it ensures no technique is ever "forgotten" regardless of what the LLM remembers. Located in `agents/tools/tool_registry.py`.

Structure:
```python
TOOL_REGISTRY = {
    "statistical_tests": {
        "t_test_independent": {
            "name": "Independent Samples T-Test",
            "function": "agents.tools.stats_tools.t_test_independent",
            "description": "Compare means of continuous variable between 2 groups",
            "when_to_use": "Binary grouping variable + continuous outcome + approximately normal",
            "requirements": {"min_columns": 2, "column_types": ["numeric", "binary"]},
            "domains": ["all"],
            "parameters": {
                "data_ref": "DuckDB table reference",
                "numeric_column": "Column to compare",
                "group_column": "Binary grouping column",
                "alpha": "Significance level (default 0.05)"
            },
            "output": {
                "statistic": "t-statistic value",
                "p_value": "p-value",
                "effect_size": "Cohen's d",
                "ci_lower": "95% CI lower bound",
                "ci_upper": "95% CI upper bound",
                "interpretation": "Plain English interpretation"
            }
        },
        # ... 20+ more statistical tests
    },
    "visualizations": {
        # ... 25+ chart types
    },
    "feature_engineering": {
        # ... 50+ feature techniques with domain tags
    },
    "models": {
        # ... all supported ML algorithms
    }
}
```

Every entry has: name, function path, description, when to use, requirements, valid domains, parameters, and output format. The Follow-Up Agent searches this registry when users ask for specific analyses.

### 4. Domain Configuration Design

Each domain file in `domains/` exports a configuration dict and a set of domain-specific tool functions.

```python
# domains/healthcare.py (structure)

HEALTHCARE_CONFIG = {
    "domain_name": "healthcare",
    "display_name": "Healthcare",
    "icon": "🏥",
    
    # How to detect this domain from column names
    "detection_keywords": {
        "strong": ["patient_id", "diagnosis", "icd", "admission", "discharge",
                   "hemoglobin", "creatinine", "mortality", "readmission"],
        "moderate": ["age", "gender", "bmi", "blood_pressure", "heart_rate",
                    "medication", "procedure", "lab", "vitals"],
        "weak": ["id", "date", "status", "type", "code"]
    },
    "detection_threshold": 3,  # Need 3+ strong matches or 5+ moderate
    
    # Domain-specific metrics
    "primary_metrics": {
        "classification": ["sensitivity", "specificity", "auc", "npv", "ppv"],
        "regression": ["mae", "rmse", "r2"],
        "survival": ["concordance_index", "brier_score"]
    },
    
    # Domain-specific EDA questions
    "eda_questions": [ ... ],  # See dashboard design in conversation history
    
    # Domain-specific feature engineering questions
    "feature_questions": [ ... ],
    
    # Domain-specific model configuration questions
    "model_questions": [ ... ],
    
    # Cost matrix defaults
    "default_cost_matrix": {
        "false_negative": 10,  # Missing a sick patient
        "false_positive": 1    # Unnecessary follow-up
    },
    
    # Fairness requirements
    "fairness": {
        "required": True,
        "protected_attributes": ["race", "gender", "age_group", "insurance_type"],
        "metric": "equal_opportunity"
    },
    
    # Compliance
    "compliance_notes": [
        "Check for PHI (Protected Health Information) in columns",
        "HIPAA considerations for data handling",
        "Model decisions must be explainable for clinical use"
    ],
    
    # Report style
    "report_style": "clinical",
    "terminology_map": {
        "user": "patient",
        "prediction": "risk assessment",
        "positive_class": "event (readmission/mortality)",
        "feature": "clinical variable"
    },
    
    # Special encodings
    "special_encodings": {
        "icd_codes": ["charlson_index", "elixhauser_index", "ccs_category"],
        "cpt_codes": ["procedure_grouper"],
        "ndc_codes": ["drug_class"]
    }
}
```

### 5. Interactive Question Flow (Guided Mode)

When in Guided mode, agents generate questions using a structured format that the Streamlit dashboard renders as interactive widgets.

Question format:
```python
{
    "id": "eda_q1_analysis_goal",
    "step": "eda",
    "question": "What's your primary analysis goal?",
    "type": "single_select",  # single_select | multi_select | slider | per_column_table | text_input | number_input
    "options": [
        {"value": "understand_target", "label": "Understand what drives the target variable", "recommended": True},
        {"value": "relationships", "label": "Understand relationships between features"},
        {"value": "quality", "label": "Deep data quality investigation"},
        {"value": "segments", "label": "Find natural segments/clusters"},
        {"value": "temporal", "label": "Understand temporal patterns"},
        {"value": "comprehensive", "label": "All of the above"},
        {"value": "custom", "label": "Custom — I'll describe what I want"}
    ],
    "recommendation_reason": "Since you have a clear target variable (readmitted_30day), understanding its drivers is the most actionable analysis.",
    "domain_specific": False
}
```

The `per_column_table` type is used for decisions like missing value strategy, encoding strategy, and outlier handling — where the user sees a table of columns and selects a strategy for each one via dropdowns.

### 6. Error Handling Strategy

Every agent wraps its execution in try/except with structured error logging:

```python
try:
    result = execute_analysis(params)
except DataLeakageDetected as e:
    state["errors"].append({"step": "feature_engineering", "type": "leakage", "detail": str(e)})
    # Don't crash — flag the issue, skip the leaking feature, continue
except InsufficientDataError as e:
    state["errors"].append({"step": "modeling", "type": "insufficient_data", "detail": str(e)})
    # Suggest sampling strategy or simpler model
except LLMAPIError as e:
    state["errors"].append({"step": "eda", "type": "llm_failure", "detail": str(e)})
    # Gracefully degrade — run analyses without LLM summaries
except Exception as e:
    state["errors"].append({"step": state["current_step"], "type": "unexpected", "detail": str(e)})
    logger.exception(f"Unexpected error in {state['current_step']}")
    # Log full traceback, continue with next step if possible
```

Custom exceptions are defined in `core/exceptions.py`.

### 7. Reproducibility

Every pipeline run captures:
- `random_seed` — used for ALL random operations (train/test split, model training, sampling)
- `data_hash` — SHA256 hash of input data
- `requirements_snapshot` — `pip freeze` output at run time
- `workflow_state` — complete state exported as JSON
- All of these are included in the session export and Jupyter notebook

### 8. Claude API Usage Optimization

To minimize API costs and maximize speed:
- **Batch decisions** — ask Claude to make multiple decisions in one call (e.g., all missing value strategies in one prompt, not one per column)
- **Cache responses** — if the same question is asked for similar data, use cached response
- **Structured output** — always request JSON output from Claude, never free-form text that needs parsing
- **Temperature 0** — deterministic responses for reproducible analysis decisions
- **Token tracking** — log input/output tokens per call, display estimated cost in dashboard

### 9. Human-in-the-Loop via LangGraph Interrupt

LangGraph supports `interrupt_before` and `interrupt_after` on nodes. In Guided/Expert mode:

```python
# core/graph.py
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

workflow = StateGraph(AutoDSState)

# Add nodes
workflow.add_node("domain_detection", domain_detector_agent)
workflow.add_node("data_profiling", data_profiler_agent)
workflow.add_node("eda_questions", eda_generate_questions)  # Generates questions
workflow.add_node("eda_execute", eda_execute_analyses)       # Runs after user answers
workflow.add_node("fe_questions", fe_generate_questions)
workflow.add_node("fe_execute", fe_execute_engineering)
workflow.add_node("model_questions", model_generate_questions)
workflow.add_node("model_execute", model_train_evaluate)
workflow.add_node("explain", explainability_agent)
workflow.add_node("report", report_agent)

# In Guided mode, interrupt after question generation to get user input
# The Streamlit dashboard resumes the graph after user answers

checkpointer = SqliteSaver.from_conn_string("sessions/checkpoints.db")
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["eda_execute", "fe_execute", "model_execute"])
```

### 10. Multi-Source Data Joining

When users load multiple data sources, the system:
1. Shows all loaded sources with their schemas
2. Uses Claude to suggest join keys based on column names and types
3. Shows the user the suggested join and lets them confirm/modify
4. Executes the join in DuckDB (efficient for large data)
5. Validates the joined result (check for row explosion from bad joins)

---

## CODING STANDARDS

### Python Style
- Python 3.11+ with type hints everywhere
- Docstrings on every public function (Google style)
- Max line length: 100 characters
- Use `pathlib.Path` not `os.path`
- Use `logging` module, never `print()` for operational messages
- Constants in UPPER_SNAKE_CASE in `core/constants.py`

### File Organization
- One class per file for major components (each agent, each connector)
- `__init__.py` exports public interface
- Private functions prefixed with `_`
- Keep files under 300 lines — split if larger

### Error Handling
- Never catch bare `Exception` except at top-level agent wrapper
- Custom exceptions in `core/exceptions.py`
- Always log errors with full context before handling
- Graceful degradation over crashing — if one analysis fails, continue with others

### Testing
- Every tool function has at least one unit test
- Integration tests use sample datasets in `evaluation/test_datasets/`
- Use pytest fixtures for common setup
- Target 80%+ code coverage on tool functions

### Git Conventions
- Commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Branch naming: `feature/agent-name`, `fix/issue-description`
- PR descriptions reference the agent/component being changed

---

## IMPLEMENTATION ORDER (for Claude Code)

This is the recommended order to build the project:

### Phase 1: Foundation (get a working skeleton)
1. `core/state.py` — Define the full state schema
2. `core/llm_config.py` — Claude API setup
3. `core/constants.py` — All constants
4. `core/exceptions.py` — All custom exceptions
5. `core/graph.py` — Basic LangGraph with 3 nodes (profiler → eda → model)
6. `data_connectors/base.py` — Abstract connector interface
7. `data_connectors/file_connectors/csv_connector.py` — CSV loading
8. `data_connectors/universal_loader.py` — Smart format detection
9. `agents/tools/tool_registry.py` — Tool registry structure
10. `dashboard/app.py` — Basic Streamlit app that loads data

### Phase 2: Core Agents
11. `domains/domain_registry.py` + `domains/generic.py` — Domain detection
12. `agents/data_profiler.py` — Full data profiling agent
13. `agents/tools/data_tools.py` — Data manipulation tools
14. `agents/tools/stats_tools.py` — All statistical test functions
15. `agents/tools/viz_tools.py` — All chart generation functions
16. `agents/eda_agent.py` — Interactive EDA agent
17. `agents/tools/feature_tools.py` — Feature engineering functions
18. `agents/feature_engineer.py` — Interactive feature engineering agent
19. `agents/tools/ml_tools.py` — Model training functions
20. `agents/modeling_agent.py` — Interactive modeling agent

### Phase 3: Domain Intelligence
21. `domains/healthcare.py` — Full healthcare config + tools
22. `domains/finance.py` — Full finance config + tools
23. `domains/ecommerce.py` — Full ecommerce config + tools
24. `agents/tools/domain_tools.py` — Domain-specific calculations
25. Update all agents to use domain configs

### Phase 4: Explainability & Reports
26. `explainability/shap_explainer.py`
27. `explainability/fairness_audit.py`
28. `explainability/counterfactual.py`
29. `explainability/model_card_generator.py`
30. `agents/explainability_agent.py`
31. `reports/generators/html_report.py`
32. `reports/generators/pdf_report.py`
33. `reports/generators/notebook_export.py`
34. `agents/report_agent.py`

### Phase 5: Advanced Features
35. `agents/followup_agent.py` — Conversational follow-up
36. `agents/deployment_agent.py` — FastAPI packaging
37. `validation/` — All validation modules
38. `logging_audit/` — All logging modules
39. `session/` — Session management
40. More connectors (database, API, cloud)

### Phase 6: Polish
41. Complete Streamlit dashboard (all pages)
42. `tests/` — Full test suite
43. `evaluation/benchmarks/` — Benchmark runner
44. `README.md` — Full documentation with demo GIF
45. `docs/` — All documentation files
46. Deployment to Streamlit Cloud / HuggingFace Spaces

---

## KEY PATTERNS TO FOLLOW

### Pattern: Domain-Aware Question Generation
```python
def generate_questions(state: AutoDSState, step: str) -> list[dict]:
    """Generate interactive questions based on domain + data + step."""
    domain_config = state["domain_config"]
    
    # Start with universal questions for this step
    questions = UNIVERSAL_QUESTIONS[step].copy()
    
    # Add domain-specific questions
    if step in domain_config.get("questions", {}):
        questions.extend(domain_config["questions"][step])
    
    # Add data-specific questions (e.g., if datetime columns exist, ask about temporal features)
    schema = state["schema_info"]
    if any(col["type"] == "datetime" for col in schema["columns"]):
        questions.extend(TEMPORAL_QUESTIONS[step])
    if any(col["type"] == "text" for col in schema["columns"]):
        questions.extend(TEXT_QUESTIONS[step])
    
    # Use Claude to rank/filter questions by relevance
    if len(questions) > 8:
        questions = _rank_questions_by_relevance(questions, state, llm)
    
    return questions
```

### Pattern: Tool Execution with Logging
```python
def execute_tool(tool_name: str, params: dict, state: AutoDSState) -> dict:
    """Execute a registered tool with full logging."""
    import time
    
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise ToolNotFoundError(f"Tool '{tool_name}' not in registry")
    
    start_time = time.time()
    
    try:
        fn = import_function(tool["function"])
        result = fn(**params)
        
        duration = time.time() - start_time
        state["pipeline_log"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "step": state["current_step"],
            "tool": tool_name,
            "params": params,
            "duration_seconds": round(duration, 2),
            "status": "success"
        })
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        state["pipeline_log"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "step": state["current_step"],
            "tool": tool_name,
            "params": params,
            "duration_seconds": round(duration, 2),
            "status": "error",
            "error": str(e)
        })
        raise
```

### Pattern: Graceful LLM Degradation
```python
def get_llm_summary(results: dict, state: AutoDSState) -> str:
    """Get LLM summary of results, with fallback if API fails."""
    try:
        llm = get_llm()
        response = llm.invoke(build_summary_prompt(results, state))
        state["api_call_count"] += 1
        return response.content
    except Exception as e:
        logger.warning(f"LLM summary failed: {e}. Using template fallback.")
        return _template_summary(results)  # Rule-based fallback summary
```

---

## WHAT SUCCESS LOOKS LIKE

When this project is complete, a user should be able to:

1. Upload ANY tabular dataset (CSV, Excel, Parquet, database, API, clipboard)
2. Have the system auto-detect the industry domain (or manually select)
3. Choose their expertise level (Auto/Guided/Expert)
4. Go through an interactive, domain-aware EDA with intelligent questions
5. Configure feature engineering with per-column control and domain recommendations
6. Select and train models with domain-appropriate metrics and evaluation
7. Get SHAP explanations, fairness audits, and model cards
8. Download reports in HTML, PDF, executive summary, and Jupyter notebook
9. Make predictions on new data via dashboard or API
10. Ask follow-up questions and get additional analyses on demand
11. Resume previous sessions and compare results

The portfolio metric: **"Multi-agent platform tested on 8+ datasets across 6 industry domains, achieving within 5% of hand-tuned models with zero code from the user."**

---

## AVAILABLE SKILLS — USE THESE LIBERALLY

The developer (Parth) has many skills installed in `/mnt/skills/`. Claude Code should **always check for and use relevant skills** before writing code from scratch. Skills contain battle-tested patterns, templates, and best practices.

### Skills Directly Relevant to This Project

| Skill | Location | When to Use in AutoDS |
|-------|----------|----------------------|
| **ui-ux-pro-max** | `/mnt/skills/user/ui-ux-pro-max/SKILL.md` | **ALWAYS read before building any dashboard page or component.** Contains design system generation, color theory, layout patterns, accessibility guidelines. Use for ALL Streamlit UI work. |
| **firecrawl** | `/mnt/skills/user/firecrawl/SKILL.md` | Use for the web scraping data connector (`data_connectors/api_connectors/web_scraper.py`). Firecrawl is self-hosted at `http://localhost:3002` — no API key needed. Superior to BeautifulSoup for JS-heavy pages. |
| **skill-navigator** | `/mnt/skills/user/skill-navigator/SKILL.md` | Use to discover additional skills that might help. Run `scripts/update_registry.py` if new skills are added. |
| **repo-threat-scanner** | `/mnt/skills/user/repo-threat-scanner/SKILL.md` | Use before accepting user-uploaded pickle files or executing user-provided code. Scan for malicious content. |
| **doc-coauthoring** | `/mnt/skills/examples/doc-coauthoring/SKILL.md` | Use when building the Report Agent — has structured workflows for co-authoring documentation. |
| **mcp-builder** | `/mnt/skills/examples/mcp-builder/SKILL.md` | If we need to build MCP servers for external service integration. |
| **skill-creator** | `/mnt/skills/examples/skill-creator/SKILL.md` | If we want to package AutoDS components as reusable skills. |
| **web-artifacts-builder** | `/mnt/skills/examples/web-artifacts-builder/SKILL.md` | For building complex multi-component web UIs. May help with advanced dashboard features. |
| **theme-factory** | `/mnt/skills/examples/theme-factory/SKILL.md` | For styling reports and dashboard with consistent themes. Has 10 pre-set themes. |
| **canvas-design** | `/mnt/skills/examples/canvas-design/SKILL.md` | For generating visual assets (architecture diagrams, etc.) for docs and README. |
| **brand-guidelines** | `/mnt/skills/examples/brand-guidelines/SKILL.md` | If we want to apply consistent branding to AutoDS outputs. |

### Skills for Potential Future Extensions

| Skill | When Useful |
|-------|------------|
| **n8n-workflow-patterns** | If we want to add n8n integration for pipeline orchestration |
| **n8n-code-python** | Python code patterns for n8n nodes |
| **n8n-mcp-tools-expert** | MCP tool integration patterns |
| **job-autopilot** | If we add a feature that auto-applies analysis to job-related datasets |
| **algorithmic-art** | For generating unique visualizations using p5.js |

### How to Use Skills in Claude Code

**Before writing code for any component, check if a relevant skill exists:**

```
1. Read the SKILL.md file for the relevant skill
2. Follow its patterns, templates, and best practices
3. Adapt to AutoDS context (don't copy blindly)
```

**Critical skill usage rules:**
- **Dashboard/UI work** → ALWAYS read `ui-ux-pro-max/SKILL.md` first
- **Web scraping connector** → ALWAYS read `firecrawl/SKILL.md` first
- **Report styling** → Check `theme-factory/SKILL.md` for themes
- **Documentation generation** → Check `doc-coauthoring/SKILL.md`
- **Security scanning uploads** → Check `repo-threat-scanner/SKILL.md`
- **Any new skill discovery** → Run `skill-navigator` to check what's available

**Skills are NOT locked-in.** If a skill doesn't fit, write custom code. But check first — skills contain condensed wisdom from trial and error that saves hours of debugging.

---

## COMPLETE FILE INVENTORY — NOTHING SHOULD BE MISSING

### Root Files (8 files)
- [x] `CLAUDE.md` — Master instructions for Claude Code
- [x] `README.md` — Public-facing project documentation
- [x] `requirements.txt` — Pinned Python dependencies
- [x] `requirements-dev.txt` — Dev/test dependencies
- [x] `setup.py` — Package setup for editable install
- [x] `pyproject.toml` — Project metadata and tool configs (v1.0.0)
- [x] `Makefile` — Common commands
- [x] `.env.example` — Environment variable template
- [x] `.gitignore` — Git ignore rules
- [x] `docker-compose.yml` — Full Docker deployment
- [x] `Dockerfile.dashboard` — Dashboard container

### .github/workflows/ (3 files)
- [x] `ci.yml` — Lint + typecheck + test matrix + coverage + security scan
- [x] `release.yml` — Tag-triggered release with changelog + Docker build
- [x] `benchmark.yml` — Weekly benchmark runs + manual dispatch

### agents/ (11 files)
- [x] `__init__.py`
- [x] `orchestrator.py` — LangGraph supervisor
- [x] `domain_detector.py` — Industry domain detection
- [x] `data_profiler.py` — Data quality assessment
- [x] `eda_agent.py` — Exploratory data analysis
- [x] `feature_engineer.py` — Feature creation
- [x] `modeling_agent.py` — Model training
- [x] `explainability_agent.py` — SHAP, fairness, model cards
- [x] `report_agent.py` — Report generation
- [x] `deployment_agent.py` — FastAPI packaging
- [x] `followup_agent.py` — Post-pipeline chat

### agents/tools/ (10 files)
- [x] `__init__.py`
- [x] `tool_registry.py` — Master registry of ALL tools
- [x] `data_tools.py` — Data manipulation functions
- [x] `viz_tools.py` — 25+ chart generators
- [x] `stats_tools.py` — 16+ statistical tests
- [x] `ml_tools.py` — Model training functions
- [x] `feature_tools.py` — Feature engineering functions
- [x] `domain_tools.py` — Domain-specific calculations
- [x] `report_tools.py` — Report generation utilities
- [x] `explainability_tools.py` — SHAP, PDP, fairness tools

### core/ (8 files)
- [x] `__init__.py`
- [x] `graph.py` — LangGraph workflow definition
- [x] `state.py` — Shared state schema
- [x] `llm_config.py` — Claude API configuration
- [x] `memory.py` — SQLite + ChromaDB memory
- [x] `user_modes.py` — Auto/Guided/Expert logic
- [x] `constants.py` — All constants
- [x] `exceptions.py` — Custom exceptions

### data_connectors/ (30+ files)
- [x] `base.py` — Abstract connector interface
- [x] `connector_factory.py` — Factory pattern
- [x] `universal_loader.py` — Smart format detection
- [x] `multi_source_manager.py` — Multi-source joining
- [x] `schema_matcher.py` — Join key detection
- [x] `file_connectors/` — 9 file format connectors
- [x] `database_connectors/` — 7 database connectors
- [x] `api_connectors/` — 5 API connectors + 4 public data APIs
- [x] `cloud_connectors/` — 3 cloud storage connectors
- [x] `direct_input/` — 3 direct input methods

### domains/ (9 files)
- [x] `base_domain.py` — Abstract domain interface
- [x] `domain_registry.py` — Detection + registry
- [x] `generic.py` — Fallback domain
- [x] `healthcare.py`
- [x] `finance.py`
- [x] `ecommerce.py`
- [x] `marketing.py`
- [x] `hr.py`
- [x] `manufacturing.py`

### dashboard/ (19 files)
- [x] `app.py` — Main Streamlit entry
- [x] 9 page files in `pages/`
- [x] 8 component files in `components/`

### validation/ (5 files)
- [x] `schema_validator.py`
- [x] `edge_case_detector.py`
- [x] `data_drift_checker.py`
- [x] `input_sanitizer.py`
- [x] `model_validator.py`

### explainability/ (9 files)
- [x] `shap_explainer.py`
- [x] `pdp_ice.py`
- [x] `counterfactual.py`
- [x] `plain_english.py`
- [x] `what_if.py`
- [x] `adverse_action.py`
- [x] `fairness_audit.py`
- [x] `model_card_generator.py`
- [x] `calibration.py`

### evaluation/ (4 files + test datasets)
- [x] `agent_evaluator.py`
- [x] `model_comparator.py`
- [x] `bootstrap_ci.py`
- [x] `domain_metrics.py`

### logging_audit/ (5 files)
- [x] `structured_logger.py`
- [x] `decision_log.py`
- [x] `performance_log.py`
- [x] `cost_tracker.py`
- [x] `audit_trail_export.py`

### session/ (3 files)
- [x] `session_manager.py`
- [x] `session_compare.py`
- [x] `session_export.py`

### reports/ (5 generators + 5 templates)
- [x] `generators/html_report.py`
- [x] `generators/pdf_report.py`
- [x] `generators/executive_summary.py`
- [x] `generators/notebook_export.py`
- [x] `generators/zip_packager.py`
- [x] `templates/base_report.html`
- [x] `templates/healthcare_report.html`
- [x] `templates/finance_report.html`
- [x] `templates/ecommerce_report.html`
- [x] `templates/executive_template.html`
- [x] `templates/styles.css`

### serving/ (4 files + Dockerfile)
- [x] `api.py`
- [x] `schemas.py`
- [x] `model_loader.py`
- [x] `Dockerfile`

### tests/ (17 test files + conftest)
- [x] `conftest.py` — Shared fixtures
- [x] 9 unit tests
- [x] 4 integration tests
- [x] 3 agent tests
- [x] 1 benchmark runner

### configs/ (5 files)
- [x] `agent_prompts.yaml`
- [x] `default_settings.yaml`
- [x] `logging_config.yaml`
- [x] `domain_configs.yaml`
- [x] `tool_registry.yaml`

### scripts/ (4 files)
- [x] `download_sample_datasets.py`
- [x] `setup_database.py`
- [x] `run_benchmarks.py`
- [x] `generate_demo_gif.py`

### docs/ (7 files + images dir)
- [x] `architecture.md`
- [x] `domain_guide.md`
- [x] `tool_registry_reference.md`
- [x] `api_reference.md`
- [x] `user_guide.md`
- [x] `developer_guide.md`
- [x] `deployment_guide.md`

### Empty directories with .gitkeep
- [x] `data/`
- [x] `outputs/`
- [x] `logs/`
- [x] `sessions/`
- [x] `mlruns/`
- [x] `evaluation/test_datasets/`
- [x] `evaluation/benchmarks/benchmark_datasets/`
- [x] `tests/benchmarks/benchmark_datasets/`
- [x] `docs/images/`
