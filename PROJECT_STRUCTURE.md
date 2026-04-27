# AutoDS Platform - Complete Project Structure

> Generated: 2026-04-26 | 278+ files | 180+ Python modules | 902 tests passing

---

## ROOT FILES

| File | Description |
|------|-------------|
| `CLAUDE.md` | Master Claude Code instructions (184KB). Implementation rules, deployment plan, tech stack decisions, Phase 1 scope |
| `README.md` | Public project documentation. Feature overview, architecture diagram, tech stack, quickstart |
| `pyproject.toml` | Package metadata v1.0.0. Build config, pytest settings, tool configs |
| `setup.py` | Editable install entrypoint (`pip install -e .`) |
| `requirements.txt` | 200+ pinned production dependencies (LangGraph, anthropic, scikit-learn, pandas, plotly, streamlit) |
| `requirements-dev.txt` | Dev/test deps (pytest, pytest-cov, bandit, mypy, ruff) |
| `Makefile` | Commands: `make run` (start dashboard), `make test`, `make benchmark`, `make lint` |
| `.env.example` | Template for API keys: ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, database creds, S3/GCS/Azure keys |
| `.gitignore` | Excludes .venv, __pycache__, mlruns, .code-review-graph, egg-info, .env, sessions/, outputs/ |
| `docker-compose.yml` | Multi-service Docker deployment: dashboard + API server |
| `Dockerfile.dashboard` | Container image for Streamlit dashboard |
| `DOCUMENTATION_UPDATES.md` | Changelog of documentation modifications |

---

## .streamlit/

Streamlit runtime configuration.

| File | Description |
|------|-------------|
| `config.toml` | Cosmic dark theme colors (primaryColor=#8B5CF6, backgroundColor=#07091A, textColor=#E2E8F0). Server port 8501, headless mode |

---

## .github/workflows/

CI/CD pipeline definitions.

| File | Description |
|------|-------------|
| `ci.yml` | Linting (ruff), type checking (mypy), test matrix (Python 3.11-3.12), coverage threshold 80%, Bandit security scan |
| `release.yml` | Tag-triggered release: changelog generation, Docker image push to ghcr.io |
| `benchmark.yml` | Weekly scheduled + manual dispatch benchmark runs on 10 standard datasets |

---

## agents/

**8 specialized AI agents** that form the autonomous pipeline. Each agent is a LangGraph node that receives `AutoDSState`, performs its task, and returns updated state.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init, exports all agent classes |
| `orchestrator.py` | 310 | **Pipeline supervisor**. Goal decomposition, problem type detection (classification/regression/clustering), target column identification, pipeline configuration. Routes to other agents |
| `domain_detector.py` | 40 | Detects industry domain (healthcare/finance/ecommerce/marketing/hr/manufacturing/generic) from column names + data characteristics |
| `data_profiler.py` | 415 | Schema detection, missing value analysis, data quality scoring (0-100), cleaning recommendations, type inference, outlier detection |
| `eda_agent.py` | 821 | Domain-aware exploratory data analysis. Generates interactive questions (single-select, multi-select, slider, per-column table). Produces distribution plots, correlation analysis, domain-specific charts |
| `feature_engineer.py` | 779 | Per-column feature engineering decisions. Encoding (one-hot, target, ordinal), scaling (standard, robust, minmax), transformations (log, sqrt, box-cox), interactions, polynomial features. Domain-aware (e.g., RFM for ecommerce) |
| `modeling_agent.py` | 678 | Algorithm selection based on problem type + data characteristics. Trains scikit-learn/XGBoost/LightGBM/CatBoost models. Hyperparameter tuning via FLAML. MLflow experiment tracking. Cross-validation |
| `explainability_agent.py` | 517 | SHAP global+local explanations, fairness audit (disparate impact, demographic parity), model card generation, counterfactual examples, plain-English summaries |
| `report_agent.py` | 522 | Generates HTML interactive report, PDF print-ready report, 1-page executive summary, runnable Jupyter notebook. Domain-specific report sections |
| `deployment_agent.py` | 428 | Packages trained model as FastAPI endpoint. Generates Pydantic schemas, Dockerfile, requirements.txt, README for deployment |
| `followup_agent.py` | 358 | Post-pipeline conversational interface. Answers questions about results, re-runs analysis, explains decisions using context from full pipeline state |

### agents/tools/

**Foundation tools** used by agents. 40+ registered functions totaling 5,600+ lines.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `tool_registry.py` | 291 | Master registry of ALL tools with metadata (name, description, category, parameters). Search by name/category. Used by agents for tool discovery |
| `data_tools.py` | 742 | **15 data manipulation functions**: load_csv, load_excel, load_parquet, filter_rows, sort_data, group_aggregate, pivot_table, merge_datasets, sample_data, describe_data, detect_duplicates, handle_missing, convert_types, create_duckdb_query, export_data |
| `stats_tools.py` | 1207 | **16 statistical tests**: t_test, paired_t_test, welch_t_test, one_way_anova, kruskal_wallis, mann_whitney, chi_square, fisher_exact, shapiro_wilk, levene, kolmogorov_smirnov, correlation_matrix, vif_analysis, point_biserial, spearman_rank, anderson_darling |
| `viz_tools.py` | 675 | **25 Plotly chart generators**: scatter, bar, histogram, box, violin, heatmap, line, area, pie, sunburst, treemap, funnel, waterfall, parallel_coordinates, pair_plot, qq_plot, time_series, candlestick, radar, gauge, bullet, indicator, map_choropleth, sankey, distribution_overlay |
| `ml_tools.py` | 617 | **15 ML functions**: train_classifier, train_regressor, train_clusterer, cross_validate, hyperparameter_tune, evaluate_model, feature_importance, learning_curve, confusion_matrix_plot, roc_curve_plot, precision_recall_curve, calibration_curve, prediction_error_plot, residual_plot, compare_models |
| `feature_tools.py` | 981 | **30 feature engineering functions**: one_hot_encode, target_encode, ordinal_encode, label_encode, standard_scale, robust_scale, minmax_scale, log_transform, sqrt_transform, box_cox, yeo_johnson, polynomial_features, interaction_features, binning, date_features, text_tfidf, text_count_vectorize, pca_reduce, ica_reduce, umap_reduce, handle_outliers_iqr, handle_outliers_zscore, winsorize, impute_knn, impute_iterative, lag_features, rolling_features, diff_features, target_lag, custom_formula |
| `domain_tools.py` | 1487 | **22 domain-specific calculations**: charlson_comorbidity_index, elixhauser_index, survival_analysis, ks_statistic, gini_coefficient, psi, vintage_analysis, adverse_action_codes, rfm_scoring, clv_calculation, basket_analysis, cohort_retention, funnel_analysis, campaign_lift, ab_test_analysis, channel_attribution, attrition_prediction, compensation_equity, diversity_metrics, oee_calculation, mtbf_analysis, spc_control_charts |
| `report_tools.py` | - | Re-exports from `reports/generators/` (HTML, PDF, notebook, executive summary) |
| `explainability_tools.py` | - | Re-exports from `explainability/` (SHAP, PDP, counterfactual, fairness, what-if) |

---

## core/

**Platform infrastructure**. State management, graph definition, LLM config, memory, constants.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `state.py` | 289 | `AutoDSState` TypedDict - complete workflow state schema. Fields: session_id, raw_data, cleaned_data, domain, problem_type, target_column, user_mode, eda_results, feature_plan, trained_models, best_model, explanations, reports, questions, answers, metadata, error_log |
| `graph.py` | 250 | LangGraph `StateGraph` definition. Nodes: orchestrator, profiler, domain_detector, eda, feature_engineer, modeler, explainer, reporter, deployer, followup. Conditional edges based on user_mode and pipeline stage |
| `llm_config.py` | 430 | Multi-provider LLM setup. Supports Claude (primary), Gemini, OpenAI. Prompt caching, cost tracking per call, retry logic, rate limiting. Provider selection per agent |
| `memory.py` | 288 | Dual memory: SQLite for structured session data + ChromaDB for vector similarity search across past analyses. Enables "remember similar datasets" feature |
| `user_modes.py` | 119 | Three modes: **Auto** (full autonomy, no questions), **Guided** (asks domain-specific questions at each stage), **Expert** (fine-grained per-column/per-step control). Mode determines which graph edges fire |
| `constants.py` | 230 | Global thresholds and defaults: VIF_THRESHOLD=10, CORR_THRESHOLD=0.95, MISSING_THRESHOLD=0.5, MIN_ROWS=50, MAX_CATEGORIES=50, CLASS_IMBALANCE_RATIO=10, OUTLIER_IQR_MULTIPLIER=1.5, supported file types, model hyperparameter grids |
| `exceptions.py` | 204 | 30+ custom exceptions: DataValidationError, DomainDetectionError, ModelTrainingError, ConnectorError, SchemaValidationError, ExplainabilityError, ReportGenerationError, SessionError, CostLimitExceeded, etc. |

---

## dashboard/

**Streamlit web application**. Cosmic dark theme with aurora gradients. 9 interactive pages + 10 reusable components.

### dashboard/app.py
| Lines | Description |
|-------|-------------|
| 190 | Main entry point. Page config, cosmic CSS injection, landing page with animated hero, sidebar navigation, session state init, upload routing |

### dashboard/pages/

Sequential workflow pages. Each page reads/writes `st.session_state` mapped to `AutoDSState`.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `01_upload.py` | 217 | Multi-source data upload. File upload (CSV, Excel, Parquet, JSON, etc.), database connection form, API connector, clipboard paste, sample datasets. Source preview table, multi-source management |
| `02_configure.py` | 205 | Domain confirmation (auto-detected, user can override), mode selection (Auto/Guided/Expert), target column picker, analysis goal text input. Validates minimum requirements before proceeding |
| `03_eda_interactive.py` | 257 | Interactive EDA. Renders domain-specific questions (e.g., "Which time column for seasonality?" for ecommerce). Shows distribution plots, correlation heatmap, missing value summary, outlier detection. User can add manual analysis specs |
| `04_feature_engineering.py` | 314 | Per-column feature decisions. Table showing each column with recommended encoding/scaling/transformation. User can override in Guided/Expert mode. Shows feature importance preview, multicollinearity warnings |
| `05_modeling.py` | 417 | Algorithm selection grid. Shows recommended algorithms with reasoning. Training progress bar. Results: metrics table, confusion matrix, ROC curve, feature importance, learning curves. Model comparison if multiple trained |
| `06_explainability.py` | 341 | Tabs: SHAP summary + force plots, PDP/ICE curves, counterfactual examples, fairness audit results (disparate impact ratios), what-if simulator, model card preview |
| `07_predict.py` | 248 | Two modes: single-row prediction (form with all features) and batch prediction (upload CSV). Shows prediction + confidence + top contributing features per row |
| `08_chat.py` | 222 | Follow-up Q&A. Chat interface using followup_agent. Context-aware: knows full pipeline state. Can re-run analyses, explain decisions, suggest improvements |
| `09_download.py` | 275 | Download center. Buttons for: HTML report, PDF report, executive summary, Jupyter notebook, ZIP bundle, trained model, audit trail (JSONL), session file (JSON) |

### dashboard/components/

Reusable UI widgets used across pages.

| File | Description |
|------|-------------|
| `__init__.py` | Package init, exports all components |
| `shared_css.py` | **Design system**. 80+ CSS custom properties: cosmic navy (#07091A) palette, violet/indigo/purple accents, aurora gradient overlays, glass morphism effects. Three fonts (Inter Tight, Instrument Serif, JetBrains Mono). Dark/light mode toggle. Responsive breakpoints |
| `mode_selector.py` | Radio button group: Auto / Guided / Expert. Shows description of each mode. Persists to session state |
| `domain_badge.py` | Colored badge showing detected domain (Healthcare, Finance, etc.) with icon and confidence score |
| `approval_widget.py` | Human-in-the-loop approval UI. Shows agent recommendation + reasoning. Approve/Modify/Reject buttons. Used in Guided mode at each pipeline stage |
| `download_buttons.py` | Styled download buttons for each report format. Handles file generation on click |
| `question_renderer.py` | Renders 6 interactive question types from agent: single-select (radio), multi-select (checkboxes), slider (range), per-column table (editable dataframe), text input, number input. Collects answers into state |
| `workflow_progress.py` | 7-step horizontal progress bar: Upload > Configure > EDA > Features > Model > Explain > Report. Highlights current step, shows completion status |
| `metric_cards.py` | KPI display cards. Shows metric name, value, delta, sparkline. Used for model performance metrics |
| `llm_selector.py` | Dropdown to select LLM provider (Claude/Gemini/OpenAI) and specific model. Shows estimated cost per analysis |
| `chart_container.py` | Wrapper for Plotly charts. Adds export buttons (PNG, SVG, HTML), fullscreen toggle, dark theme styling |

---

## data_connectors/

**30+ data source connectors**. All inherit from `BaseConnector` with standard `connect()`, `load()`, `validate()` interface.

### Root Files

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init, exports factory |
| `base.py` | 86 | Abstract `BaseConnector` class. Interface: `connect(config) -> bool`, `load(query) -> DataFrame`, `validate() -> list[str]`, `get_schema() -> dict` |
| `connector_factory.py` | 144 | Factory pattern. Takes source type string, returns correct connector instance. Supports 30+ types |
| `universal_loader.py` | 204 | Smart loader. Auto-detects file format from extension + magic bytes, encoding from chardet, delimiter from csv.Sniffer. Falls back through connectors |
| `multi_source_manager.py` | - | Manages multiple loaded DataFrames. Join/merge logic with user-specified or auto-detected keys |
| `schema_matcher.py` | - | Cross-source join key detection. Compares column names (fuzzy match), dtypes, value overlap to suggest join columns |

### data_connectors/file_connectors/

Local file format parsers.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `csv_connector.py` | 161 | CSV/TSV. Auto-detect delimiter (comma, tab, pipe, semicolon), encoding (utf-8, latin-1, cp1252), header row. Handles quoted fields, multiline values |
| `excel_connector.py` | 59 | Excel (.xlsx, .xls). Sheet selection, multi-sheet loading, header row detection |
| `parquet_connector.py` | 56 | Parquet, Feather, ORC, Arrow IPC formats via pyarrow |
| `json_connector.py` | 74 | JSON flat arrays + nested auto-flatten (pd.json_normalize) + JSONL (line-delimited) |
| `xml_connector.py` | - | XML table extraction. Safe lxml parser with BytesIO buffer to prevent XXE |
| `compressed_connector.py` | 136 | ZIP, GZ, TAR.GZ extraction. Scans archive for tabular files, loads first match or lets user choose |
| `statistical_connector.py` | 95 | SAS (.sas7bdat), STATA (.dta), SPSS (.sav), HDF5 (.h5) via pandas readers |
| `pdf_connector.py` | 116 | PDF table extraction. Primary: tabula-py (Java-based). Fallback: camelot. Returns list of DataFrames (one per detected table) |
| `sqlite_connector.py` | 110 | SQLite .db file. Lists tables, executes SQL queries, returns DataFrame. Read-only mode |

### data_connectors/database_connectors/

Remote database connections. All use parameterized queries (SQL injection safe).

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `postgres_connector.py` | PostgreSQL via psycopg2 + SQLAlchemy. Connection string builder, SSL support, schema browsing |
| `mysql_connector.py` | MySQL/MariaDB via pymysql + SQLAlchemy. Charset handling, connection pooling |
| `sqlserver_connector.py` | MS SQL Server via pyodbc + SQLAlchemy. Windows auth + SQL auth support |
| `duckdb_connector.py` | DuckDB in-process or remote. Can query Parquet/CSV files directly via SQL |
| `bigquery_connector.py` | Google BigQuery via service account JSON key. Project/dataset/table selection |
| `snowflake_connector.py` | Snowflake via snowflake-connector-python. Warehouse/database/schema selection |
| `redshift_connector.py` | Amazon Redshift via SQLAlchemy + redshift_connector. IAM auth support |

### data_connectors/api_connectors/

External API data sources.

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `rest_api_connector.py` | Generic REST API client. Configurable URL, method, headers, auth (Bearer/Basic/API key), pagination (offset, cursor, link-header), response JSON path extraction |
| `web_scraper.py` | HTML table extraction via `pandas.read_html` + BeautifulSoup. URL allowlist validation (SSRF protection) |
| `kaggle_connector.py` | Kaggle dataset download via kaggle CLI/API. Dataset search, download, extract |
| `huggingface_connector.py` | HuggingFace datasets library. Load by name, split selection, streaming support |
| `google_sheets_connector.py` | Public Google Sheets via CSV export URL. Sheet ID + GID extraction |

### data_connectors/api_connectors/public_data/

Pre-configured public data API clients.

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `world_bank.py` | World Bank Open Data API. Country/indicator selection, date range |
| `fred.py` | Federal Reserve Economic Data (FRED) API. Series ID lookup, frequency selection |
| `yahoo_finance.py` | Stock/crypto data via yfinance. Ticker, date range, interval selection |
| `census.py` | US Census Bureau API. Dataset/year/variables/geography selection |

### data_connectors/cloud_connectors/

Cloud storage access.

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `s3_connector.py` | AWS S3. Bucket/key selection, IAM credentials, CSV/Parquet/JSON auto-detect |
| `gcs_connector.py` | Google Cloud Storage. Bucket/blob selection, service account auth |
| `azure_blob_connector.py` | Azure Blob Storage. Container/blob selection, connection string auth |

### data_connectors/direct_input/

Manual data entry and built-in samples.

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `clipboard_parser.py` | Parse pasted table data. Detects tab-separated, comma-separated, or HTML table format |
| `manual_entry.py` | Manual table builder. Define columns + types, enter rows via form |
| `sample_datasets.py` | Built-in sample datasets for demo/testing: Iris, Titanic, Boston Housing, California Housing, Wine Quality, Credit Card Fraud |

---

## domains/

**7 industry-specific domain configurations**. Each domain provides: detection keywords, recommended metrics, domain-specific questions, fairness config, compliance notes, terminology mapping, special encodings.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `base_domain.py` | - | Abstract `BaseDomain` class. Interface: `detect(df) -> float` (confidence 0-1), `get_metrics()`, `get_questions()`, `get_fairness_config()`, `get_compliance_notes()` |
| `domain_registry.py` | - | Registry of all 7 domains. Detection logic: scores each domain by keyword match in column names + data patterns, returns highest confidence above threshold |
| `healthcare.py` | 212 | **Healthcare**: Keywords (patient, diagnosis, ICD, CPT, lab_result). Metrics (Charlson, Elixhauser, survival curves). Fairness (race, sex, age groups). Compliance (HIPAA awareness, PHI detection). Special: clinical outcome stratification |
| `finance.py` | 187 | **Finance**: Keywords (loan, credit_score, interest_rate, default). Metrics (KS statistic, Gini coefficient, PSI, vintage analysis). Compliance (fair lending, adverse action codes, ECOA protected classes). Special: reject inference, WOE/IV binning |
| `ecommerce.py` | 166 | **E-commerce**: Keywords (order, product, cart, revenue, customer_id). Metrics (RFM scoring, CLV, funnel analysis, cohort retention, basket analysis). Special: seasonal decomposition, promotion impact |
| `marketing.py` | 164 | **Marketing**: Keywords (campaign, click, impression, conversion, channel). Metrics (CTR, ROAS, attribution models, campaign lift). Special: A/B test analysis, channel comparison, multi-touch attribution |
| `hr.py` | 188 | **HR**: Keywords (employee, salary, department, tenure, attrition). Metrics (attrition rate, diversity index, compensation equity). Fairness (gender, race, age in all models). Special: anonymization rules, sensitivity constraints |
| `manufacturing.py` | 182 | **Manufacturing**: Keywords (machine, sensor, temperature, pressure, defect, production). Metrics (OEE, MTBF, MTTR). Special: SPC control charts, predictive maintenance, anomaly detection |
| `generic.py` | 197 | **Generic fallback**: Standard data science practices when no specific domain detected. Covers regression, classification, clustering with standard metrics |

---

## validation/

**Data and model validation**. Runs pre-checks before each pipeline stage.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `schema_validator.py` | 303 | Extract training data schema (column names, types, ranges, categories). Validate new prediction data matches schema. Adapt schema for minor mismatches (column order, missing optional columns) |
| `edge_case_detector.py` | 358 | Detect 9 edge cases before modeling: (1) single-class target, (2) target leakage, (3) too few rows (<50), (4) constant columns, (5) perfect multicollinearity, (6) mixed types in column, (7) extreme class imbalance (>10:1), (8) high cardinality categoricals (>50 levels), (9) date columns mistyped as string |
| `data_drift_checker.py` | 285 | Compare training vs prediction data distributions. KS test per numeric feature, PSI per feature. Flags significant drift (p < 0.05 or PSI > 0.2) |
| `input_sanitizer.py` | 358 | Handle encoding issues (UTF-8 BOM, Latin-1 fallback), mixed types in columns, date string parsing (50+ formats), whitespace stripping, null value normalization (NA, N/A, null, None, -, empty string) |
| `model_validator.py` | 359 | Pre-deployment validation. Checks: (1) model loads successfully, (2) predictions match expected shape, (3) performance above minimum threshold, (4) no data leakage detected, (5) fairness metrics within bounds |

---

## explainability/

**Model explanation and fairness tools**. Used by `explainability_agent.py`.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `shap_explainer.py` | 269 | SHAP explanations. Global: summary plot (beeswarm), bar plot (mean abs SHAP). Local: force plot, waterfall plot for individual predictions. Supports tree, linear, kernel explainers |
| `pdp_ice.py` | 251 | Partial Dependence Plots (PDP) + Individual Conditional Expectation (ICE). Shows marginal effect of each feature on prediction. 1D and 2D PDP support |
| `counterfactual.py` | 210 | Counterfactual explanations. "What minimal changes to input would flip the prediction?" Uses DiCE-style approach. Returns top-K counterfactuals with feature changes highlighted |
| `plain_english.py` | 211 | Natural language explanation of any prediction. "This loan was rejected because credit score (620) is below the decision boundary (650) and debt-to-income ratio (45%) is in the high-risk range" |
| `what_if.py` | 147 | Interactive what-if analysis. Change any feature value, see updated prediction + confidence + SHAP values in real-time |
| `adverse_action.py` | 163 | Finance-specific: Top N reasons for adverse decision (loan denial). Required by ECOA/Reg B. Uses SHAP values to rank contributing factors |
| `fairness_audit.py` | 255 | Fairness metrics: disparate impact ratio, demographic parity difference, equal opportunity difference, equalized odds. Per protected group. Flags violations (DI < 0.8) |
| `model_card_generator.py` | 364 | Google Model Cards format. Auto-generates: model details, intended use, training data, evaluation metrics, ethical considerations, fairness analysis, limitations, recommendations |
| `calibration.py` | 220 | Probability calibration analysis. Reliability diagrams, Brier score, expected calibration error (ECE). Platt scaling and isotonic regression recalibration |

---

## evaluation/

**Agent and model evaluation**. Benchmark datasets, statistical model comparison, bootstrap confidence intervals.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `agent_evaluator.py` | 347 | Tests agent decision quality on 5 built-in known datasets. Checks: did profiler choose right cleaning? Did EDA suggest right analyses? Did modeler pick appropriate algorithm? Scores each agent 0-100 |
| `model_comparator.py` | 286 | Statistical comparison of trained models. Paired t-test, McNemar's test (classification), Wilcoxon signed-rank, Friedman test (3+ models), Nemenyi post-hoc. Uses cross-validation fold results |
| `bootstrap_ci.py` | 337 | Bootstrap confidence intervals for any metric. BCa (bias-corrected accelerated) correction. Paired comparison CIs. Configurable n_bootstrap (default 1000) |
| `domain_metrics.py` | 972 | 11 domain-specific evaluation metrics beyond standard sklearn: (finance) KS statistic, Gini, PSI; (healthcare) Charlson-adjusted C-statistic; (ecommerce) revenue-weighted accuracy; (marketing) lift curves; etc. |
| `_comparator_utils.py` | - | Internal utility functions for model_comparator |

### evaluation/benchmarks/

| File | Description |
|------|-------------|
| `benchmark_runner.py` | ~300 lines. Runs full pipeline on 10 standard datasets across 5 domains. Records accuracy, F1, RMSE, runtime, token usage |
| `benchmark_results.json` | Published results: all 10 datasets passing, with metrics |
| `benchmark_datasets/.gitkeep` | Placeholder for user-supplied benchmark data |

### evaluation/test_datasets/

| File | Description |
|------|-------------|
| `.gitkeep` | Placeholder for known test datasets used by agent_evaluator |

---

## logging_audit/

**Structured logging, decision tracking, cost monitoring**. All logs in JSONL format.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `structured_logger.py` | 201 | JSONL timestamped logging. Fields: timestamp, level, agent, action, details, session_id. Writes to `logs/` directory |
| `decision_log.py` | 119 | Logs every agent decision with full reasoning chain. Fields: agent, decision, alternatives_considered, reasoning, confidence, data_evidence |
| `performance_log.py` | 142 | Step timing + API call counts + token usage per agent per step. Enables pipeline bottleneck identification |
| `cost_tracker.py` | 153 | Token-based cost tracking per LLM provider. Tracks input/output tokens, calculates USD cost, enforces configurable budget limits |
| `audit_trail_export.py` | - | Exports complete audit trail for compliance. Healthcare (HIPAA audit logs), Finance (model governance), General (full decision lineage). Formats: JSON, CSV |

---

## session/

**Session persistence**. Save/load/compare analysis sessions.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `session_manager.py` | 177 | Save/load/list/delete sessions. SQLite-backed. Stores full `AutoDSState` as JSON blob. Session metadata: name, created_at, domain, dataset_name, status |
| `session_compare.py` | 178 | Side-by-side comparison of 2 sessions. Compares: config differences, feature engineering choices, model metrics, selected features, hyperparameters |
| `session_export.py` | 163 | Portable JSON export. Strips large objects (trained model bytes), keeps config + metrics + decisions. Import into another AutoDS instance |

---

## reports/

**Report generation**. Multiple output formats with domain-specific templates.

### reports/generators/

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `html_report.py` | 340 | Interactive HTML report. Embedded Plotly charts (zoom, hover, pan). Sections: data summary, EDA findings, feature engineering, model results, explanations. Uses Jinja2 templates |
| `pdf_report.py` | 157 | Print-ready PDF via weasyprint. Same content as HTML but static charts (PNG). Pagination, headers, footers |
| `executive_summary.py` | 248 | 1-page PDF for senior stakeholders. Key findings, model performance, business recommendations, risk flags. No technical jargon |
| `notebook_export.py` | 482 | Runnable Jupyter notebook (.ipynb). All code cells with comments + markdown explanations. User can re-run, modify, extend the analysis |
| `zip_packager.py` | 124 | Bundle all outputs: HTML report, PDF, executive summary, notebook, trained model, audit trail, session file into single .zip download |

### reports/templates/

Jinja2 HTML templates for report rendering.

| File | Description |
|------|-------------|
| `base_report.html` | Base template. Header, navigation, sections, footer. Plotly.js CDN inclusion |
| `healthcare_report.html` | Healthcare-specific sections: clinical outcomes, fairness by demographics, HIPAA compliance notes, Charlson index distribution |
| `finance_report.html` | Finance-specific sections: KS/Gini curves, adverse action summary, fair lending compliance, vintage analysis, PSI monitoring |
| `ecommerce_report.html` | E-commerce sections: RFM distribution, CLV analysis, funnel visualization, cohort heatmap, seasonal patterns |
| `executive_template.html` | 1-page executive template. Logo placeholder, key metrics grid, single recommendation paragraph |
| `styles.css` | Report stylesheet. Print-friendly, responsive, dark/light mode, chart containers, metric cards |

---

## serving/

**Model serving API**. FastAPI-based prediction endpoint.

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | - | Package init |
| `api.py` | 220 | FastAPI app. Endpoints: `POST /predict` (single), `POST /predict/batch` (multiple rows), `GET /health`, `GET /info` (model metadata), `POST /reload` (hot-reload model). Input validation via Pydantic. CORS enabled |
| `schemas.py` | 107 | Pydantic request/response models. `PredictionRequest` (features dict), `PredictionResponse` (prediction, confidence, explanation). `BatchPredictionRequest/Response` |
| `model_loader.py` | 138 | Load trained model from MLflow artifact store or local file. Caches loaded model in memory. Validates model compatibility with schema |
| `Dockerfile` | 14 | Production container. Python 3.11-slim, uvicorn server, healthcheck endpoint |

---

## configs/

**YAML configuration files** loaded at startup.

| File | Lines | Description |
|------|-------|-------------|
| `agent_prompts.yaml` | 240 | System prompts for all 8 agents. Chain-of-thought instructions, output format specs, guardrails. Each prompt ~30 lines |
| `domain_configs.yaml` | 207 | Per-domain configuration: detection keywords, thresholds, recommended metrics, fairness protected attributes, compliance rules |
| `tool_registry.yaml` | - | YAML mirror of Python tool registry. Tool names, descriptions, parameter schemas. Used for LLM tool-calling |
| `default_settings.yaml` | - | Platform defaults: max_rows=1_000_000, default_mode=guided, default_llm=claude, cost_budget=5.00, cache_ttl=3600 |
| `logging_config.yaml` | - | Logging configuration: log level, format, rotation, max file size |
| `loader.py` | - | YAML config loader utility. Reads + validates + caches config files. Environment variable substitution support |

---

## tests/

**902 tests passing** (2 skipped, 0 failures). Python 3.14.2.

### tests/conftest.py
Shared pytest fixtures: sample DataFrames (numeric, categorical, mixed, timeseries), sample trained models (classifier, regressor), mock LLM responses, temp directories.

### tests/unit/ (10 test files)

| File | Lines | Tests | Description |
|------|-------|-------|-------------|
| `test_statistical_tools.py` | 1046 | ~80 | Verifies all 16 stat tests produce correct p-values, test statistics, effect sizes |
| `test_feature_tools.py` | 1248 | ~100 | Verifies all 30 feature engineering functions handle edge cases (empty df, single row, all null) |
| `test_domain_tools.py` | 555 | ~45 | Verifies 22 domain-specific calculations against known results |
| `test_viz_tools.py` | 937 | ~70 | Verifies all 25 chart generators return valid Plotly figures without errors |
| `test_connectors.py` | 1050 | ~80 | Verifies each connector parses correctly. Uses temp files + mocked APIs |
| `test_domain_detection.py` | 935 | 74 | Verifies domain detection accuracy across diverse column name patterns |
| `test_schema_validation.py` | 648 | 46 | Verifies schema extraction, validation, adaptation logic |
| `test_edge_cases.py` | 650 | 65 | Verifies all 9 edge case detectors (leakage, imbalance, constant cols, etc.) |
| `test_report_generation.py` | 260 | ~20 | Verifies report generators produce valid HTML/PDF without errors |
| `test_ml_tools.py` | - | ~50 | Verifies ML training/evaluation functions |

### tests/integration/ (4 files)

| File | Lines | Description |
|------|-------|-------------|
| `test_full_pipeline.py` | 215 | End-to-end: upload CSV -> profile -> detect domain -> EDA -> features -> model -> explain -> report |
| `test_healthcare_path.py` | 66 | Full pipeline with healthcare dataset. Verifies Charlson index calculated, HIPAA notes present |
| `test_finance_path.py` | 91 | Full pipeline with finance dataset. Verifies KS/Gini computed, adverse action codes generated |
| `test_ecommerce_path.py` | 76 | Full pipeline with ecommerce dataset. Verifies RFM scoring, cohort analysis included |

### tests/agent/ (3 files)

| File | Lines | Description |
|------|-------|-------------|
| `test_profiler_decisions.py` | 105 | Verifies data_profiler agent makes correct cleaning recommendations for various data quality issues |
| `test_eda_recommendations.py` | 82 | Verifies eda_agent suggests appropriate analyses for different domain/data combinations |
| `test_model_selection.py` | 91 | Verifies modeling_agent picks appropriate algorithms based on problem type + data characteristics |

### tests/benchmarks/

| File | Description |
|------|-------------|
| `run_benchmarks.py` | CLI entry for benchmark suite |
| `benchmark_datasets/.gitkeep` | User-supplied benchmark data placeholder |

---

## scripts/

**Utility scripts** for setup, demo, benchmarks.

| File | Lines | Description |
|------|-------|-------------|
| `download_sample_datasets.py` | ~235 | Downloads 10-dataset catalog across 6 domains from Kaggle/UCI |
| `generate_demo_gif.py` | - | Playwright-based animated GIF capture of full dashboard workflow for README |
| `run_benchmarks.py` | - | CLI wrapper for `evaluation/benchmarks/benchmark_runner.py` |
| `setup_database.py` | - | Initialize local DuckDB + SQLite schemas for session storage and vector memory |

---

## docs/

**Project documentation**.

| File | Description |
|------|-------------|
| `PRD.md` | Product Requirements Document. User stories, acceptance criteria, non-functional requirements |
| `SYSTEM_DESIGN.md` | Complete system architecture. Component diagram, data flow, state machine, LLM integration design |
| `APPLICATION_ARCHITECTURE.md` | High-level application structure and module relationships |
| `TECH_DOC.md` | Technical documentation. API contracts, module interfaces, data formats, configuration reference |
| `architecture.md` | Architecture overview with diagrams |
| `architecture-visual.html` | Interactive architecture diagram (HTML/JS) |
| `DEVELOPMENT_PHASES.md` | 7-phase implementation guide (all phases complete) |
| `BUILD_NEXT.md` | Roadmap for future development (Phase 1 deployment, then advanced features) |
| `FRONTEND_OVERHAUL_SUMMARY.md` | Summary of cosmic theme + landing page implementation |
| `api_reference.md` | FastAPI serving endpoint documentation. Request/response examples |
| `user_guide.md` | End-user guide. Step-by-step dashboard walkthrough with screenshots |
| `developer_guide.md` | Developer guide. How to add new connectors, tools, domains, agents |
| `domain_guide.md` | Domain system documentation. How detection works, how to add new domains |
| `deployment_guide.md` | Deployment options: Docker, Streamlit Cloud, Hugging Face Spaces, bare metal |
| `tool_registry_reference.md` | Complete tool registry. All 40+ tools with parameters, return types, examples |
| `images/.gitkeep` | Placeholder for documentation images |

---

## Landing/

**Landing page source files** (reference/development). Production copy at `landing-site/`.

| File | Description |
|------|-------------|
| `CLAUDE.md` | Design constraints: fonts (Inter Tight, Instrument Serif), colors (#07091A cosmic navy), animations (Framer Motion), must NOT change |
| `INTEGRATION_GUIDE.md` | Step-by-step: how landing page connects to Streamlit dashboard. Port mapping, CTA button URL, CORS notes |
| `README.md` | Landing page overview documentation |
| `QUICK_REFERENCE.md` | Quick reference for landing page customization |

### Landing/landing page/

| File | Description |
|------|-------------|
| `index.html` | Single-file React + Framer Motion marketing page (~2185 lines). CDN-loaded React 18 + Framer Motion. Components: LogoMarquee, PlatformTabs, Agents section, Architecture diagram, CTA. SVG animations |
| `package.json` | Optional Vite dev setup for local development |
| `vercel.json` | Vercel deployment config (rewrites, headers) |
| `netlify.toml` | Netlify deployment config (redirects, headers) |
| `README.md` | Landing page README |

### Landing/streamlit/

| File | Description |
|------|-------------|
| `theme.py` | CSS theme module for Streamlit injection |
| `example_app.py` | Example Streamlit app demonstrating theme usage |
| `.streamlit/config.toml` | Streamlit cosmic theme config (reference copy) |
| `requirements-theme.txt` | Theme-specific dependencies |
| `README.md` | Theme usage documentation |

---

## landing-site/

**Production landing page**. Served on port 3000 via static server.

| File | Description |
|------|-------------|
| `index.html` | Copy of `Landing/landing page/index.html`. Single-file React + Framer Motion page. "Launch App" button points to localhost:8501 (Streamlit dashboard) |

---

## Screenshots/

**30 dashboard screenshots** (2026-04-26) showing all pages, cosmic theme, landing page. Used for documentation and README.

---

## Runtime Directories (gitignored, created at runtime)

| Directory | Description |
|-----------|-------------|
| `data/` | User-uploaded datasets. Cleared between sessions |
| `outputs/` | Generated reports, exports, model artifacts |
| `logs/` | JSONL structured logs from logging_audit |
| `sessions/` | Saved session state files (SQLite + JSON) |
| `mlruns/` | MLflow experiment tracking data (metrics, artifacts, model registry) |

---

## Summary

| Category | Count |
|----------|-------|
| Python modules | 180+ |
| AI agents | 8 |
| Foundation tools | 40+ functions |
| Data connectors | 30+ sources |
| Industry domains | 7 |
| Dashboard pages | 9 |
| UI components | 10 |
| Report formats | 5 (HTML, PDF, Executive, Notebook, ZIP) |
| Test files | 20+ |
| Tests passing | 902 |
| Config files | 10 |
| Documentation files | 15+ |
| Total files | 278+ |
