# Technical Documentation
# AutoDS — Autonomous Data Science Platform

**Version:** 1.0.0
**Date:** 2026-04-25
**Latest Changes:** Professional frontend overhaul with dual-theme design system, modern landing page, and 920 passing tests

---

## 1. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Core runtime, type hints, TypedDict |
| Agent Framework | LangGraph | latest | StateGraph orchestration, checkpointing, interrupts |
| LLM | Claude (Anthropic) | claude-sonnet-4-20250514 | Agent decision-making, interpretation, summarization |
| LLM Client | langchain-anthropic | latest | Claude API wrapper with structured output |
| Data Engine | DuckDB | latest | Embedded analytical database, SQL on DataFrames |
| Data Profiling | ydata-profiling | latest | Automated data quality and distribution reports |
| Data Quality | great-expectations | latest | Data validation and expectation suites |
| ML Core | scikit-learn | latest | Models, preprocessing, metrics, pipelines |
| AutoML | FLAML | latest | Time-budgeted automated model selection |
| Gradient Boosting | XGBoost, LightGBM, CatBoost | latest | High-performance tree-based models |
| Explainability | SHAP | latest | Feature importance, force/waterfall plots |
| Fairness | Fairlearn | latest | Disparate impact, demographic parity metrics |
| Statistics | scipy, statsmodels, lifelines | latest | Statistical tests, survival analysis |
| Visualization | Plotly | latest | Interactive charts with export |
| Experiment Tracking | MLflow | latest | Model versioning, metric logging, artifact storage |
| Vector Store | ChromaDB | latest | Semantic search for follow-up queries |
| Dashboard | Streamlit | latest | Web UI with interactive widgets |
| Model Serving | FastAPI + Uvicorn | latest | REST prediction endpoint |
| Reports | Jinja2 + WeasyPrint | latest | HTML/PDF report generation |
| Notebooks | nbformat | latest | Jupyter notebook export |
| PDF Tables | tabula-py, camelot-py | latest | PDF table extraction |
| Web Scraping | BeautifulSoup4, requests | latest | HTML data extraction |
| Testing | pytest, pytest-cov | latest | Unit/integration/agent tests |
| Linting | ruff, black, isort, mypy | latest | Code quality enforcement |
| Frontend Framework | Streamlit + CSS3 | latest | Web UI with custom design system |
| Fonts | Google Fonts | latest | Plus Jakarta Sans, Inter, JetBrains Mono |

---

## 1.1 Design System

The dashboard implements a **professional dual-theme design system** with 80+ CSS custom properties:

### Theme Implementation
- **Light Mode** (default): White backgrounds (#f8f9fb), slate neutrals, high contrast
- **Dark Mode**: Deep navy (#0c0f1a), optimized for reduced eye strain
- **Theme Injection**: Values baked into `:root` CSS via `shared_css.py` — no JavaScript required
- **Toggle**: Sidebar button syncs theme across all pages instantly

### CSS Token Categories
- **Backgrounds** (6 tokens): primary, card, elevated, inset, overlay, sidebar
- **Text Colors** (4 tokens): primary, secondary, muted, inverse
- **Accent Palette** (8 tokens): primary (#2563eb blue), secondary (#0891b2 cyan), success, warning, danger, info, purple
- **Typography** (3 font families): Plus Jakarta Sans (display), Inter (body), JetBrains Mono (code)
- **Spacing** (12 tokens): 1-12 scale (0.25rem to 3rem)
- **Shadows** (8 tokens): xs through lg, plus glow and focus rings
- **Transitions** (3 durations): fast (120ms), normal (200ms), slow (350ms)

### Shared Component Classes
- `.glass-card` — Elevated card with borders, shadows, hover effects
- `.pill-tabs` / `.pill-tab` — Tab-like controls with rounded pill styling
- `.glass-table` — Data table with responsive styling and row hover
- `.badge-primary/success/warning/danger` — Status badges
- `.status-dot-*` — Colored status indicators

### Landing Page Design
- Dark gradient hero banner (135deg: #1e3a5f → #0f172a → #1a1040)
- Animated gradient title with floating stat pills
- Bento-grid feature cards (3 columns, top-border gradient on hover)
- Drag-and-drop file upload with format chips
- Sample dataset quick-start tiles (Titanic, Heart Disease, Credit Risk, etc.)
- 5-column stats strip showing platform metrics

---

## 2. Directory Structure

```
autods-platform/
│
├── CLAUDE.md                    # Master instructions for Claude Code
├── README.md                    # Public documentation
├── requirements.txt             # Pinned production dependencies
├── requirements-dev.txt         # Dev/test dependencies
├── setup.py                     # Editable install (pip install -e .)
├── pyproject.toml               # Project metadata, tool configs (ruff, mypy, pytest)
├── Makefile                     # Common commands: make run/test/lint/format/benchmark
├── docker-compose.yml           # Docker deployment
├── Dockerfile.dashboard         # Dashboard container
│
├── agents/                      # 8 AI agents + tool functions
│   ├── orchestrator.py          # LangGraph supervisor — goal decomposition, routing
│   ├── domain_detector.py       # Industry domain detection from column analysis
│   ├── data_profiler.py         # Schema detection, quality assessment, cleaning
│   ├── eda_agent.py             # Domain-aware exploratory data analysis
│   ├── feature_engineer.py      # Domain-aware feature creation with user choices
│   ├── modeling_agent.py        # Model selection, training, evaluation, comparison
│   ├── explainability_agent.py  # SHAP, counterfactuals, fairness, model cards
│   ├── report_agent.py          # HTML/PDF/notebook report generation
│   ├── deployment_agent.py      # FastAPI endpoint packaging
│   ├── followup_agent.py        # Post-pipeline conversational interface
│   └── tools/                   # Deterministic Python tool functions
│       ├── tool_registry.py     # Master catalog of all 100+ tools
│       ├── data_tools.py        # pandas, DuckDB, file I/O operations
│       ├── viz_tools.py         # 25+ Plotly chart generators
│       ├── stats_tools.py       # 20+ statistical test functions
│       ├── ml_tools.py          # sklearn, XGBoost, FLAML model training
│       ├── feature_tools.py     # Feature engineering by type (encode, scale, etc.)
│       ├── domain_tools.py      # Domain-specific calculations (Charlson, RFM, KS)
│       ├── report_tools.py      # HTML/PDF/notebook utilities
│       └── explainability_tools.py  # SHAP, PDP, counterfactual, fairness
│
├── core/                        # Core infrastructure
│   ├── graph.py                 # LangGraph StateGraph definition (nodes, edges, routing)
│   ├── state.py                 # AutoDSState TypedDict — shared workflow state
│   ├── llm_config.py            # Claude API setup, invoke_llm_json helper
│   ├── memory.py                # SQLite persistence + ChromaDB vector memory
│   ├── user_modes.py            # Auto / Guided / Expert mode logic
│   ├── constants.py             # Global constants, default configs
│   └── exceptions.py            # Custom exception hierarchy
│
├── data_connectors/             # 30+ data source connectors
│   ├── base.py                  # Abstract BaseConnector interface
│   ├── connector_factory.py     # Factory — returns correct connector by type
│   ├── universal_loader.py      # Smart format detection (delimiter, encoding, header)
│   ├── multi_source_manager.py  # Manage multiple sources + join logic
│   ├── schema_matcher.py        # AI-suggested join key detection
│   ├── file_connectors/         # CSV, Excel, Parquet, JSON, XML, PDF, SAS, STATA, SQLite
│   ├── database_connectors/     # PostgreSQL, MySQL, SQL Server, DuckDB, BigQuery, Snowflake, Redshift
│   ├── api_connectors/          # REST, Kaggle, HuggingFace, Google Sheets, web scraping
│   │   └── public_data/         # World Bank, FRED, Yahoo Finance, US Census
│   ├── cloud_connectors/        # S3, GCS, Azure Blob
│   └── direct_input/            # Clipboard parser, manual entry, sample datasets
│
├── domains/                     # Industry domain configurations
│   ├── base_domain.py           # Abstract BaseDomainConfig interface
│   ├── domain_registry.py       # Detection algorithm + config registry
│   ├── generic.py               # Fallback for unrecognized domains
│   ├── healthcare.py            # Clinical metrics, HIPAA, Charlson/Elixhauser, survival
│   ├── finance.py               # KS/Gini, PSI, vintage, fair lending, scorecard
│   ├── ecommerce.py             # RFM, CLV, funnel, cohort retention, basket analysis
│   ├── marketing.py             # CTR, ROAS, attribution, campaign lift, A/B testing
│   ├── hr.py                    # Attrition, diversity, compensation equity, anonymization
│   └── manufacturing.py         # OEE, MTBF, SPC, predictive maintenance, sensor anomaly
│
├── dashboard/                   # Streamlit web application
│   ├── app.py                   # Main entry point + landing page (hero, bento grid, upload zone)
│   ├── pages/                   # 9 sequential pages (all use shared design system)
│   │   ├── 01_upload.py         # Data upload from any source
│   │   ├── 02_configure.py      # Domain + mode + target + goals
│   │   ├── 03_eda_interactive.py    # Interactive EDA with questions
│   │   ├── 04_feature_engineering.py # Per-column feature control
│   │   ├── 05_modeling.py       # Model selection + training + results
│   │   ├── 06_explainability.py # SHAP, fairness, what-if, model card
│   │   ├── 07_predict.py        # Batch + single-row predictions
│   │   ├── 08_chat.py           # Follow-up conversational interface
│   │   └── 09_download.py       # Download all outputs
│   └── components/              # Reusable Streamlit widgets
│       ├── shared_css.py        # Design system: 80+ CSS tokens, dual-theme, component classes
│       ├── mode_selector.py     # Auto/Guided/Expert toggle
│       ├── domain_badge.py      # Domain icon + name display
│       ├── approval_widget.py   # Human-in-the-loop approval UI
│       ├── question_renderer.py # Renders all question types as widgets
│       ├── workflow_progress.py # Step progress indicator
│       ├── metric_cards.py      # KPI metric display cards
│       ├── chart_container.py   # Plotly chart + export buttons
│       ├── llm_selector.py      # LLM provider selector widget
│       └── download_buttons.py  # Download buttons for all formats
│
├── validation/                  # Data & model validation
│   ├── schema_validator.py      # Prediction data vs training schema match
│   ├── edge_case_detector.py    # 10+ edge cases (leakage, imbalance, constants)
│   ├── data_drift_checker.py    # KS test + PSI for distribution drift
│   ├── input_sanitizer.py       # Encoding, mixed types, date parsing
│   └── model_validator.py       # Performance threshold checks before deploy
│
├── explainability/              # Model explainability & fairness
│   ├── shap_explainer.py        # Global (summary, bar) + local (force, waterfall)
│   ├── pdp_ice.py               # Partial Dependence + ICE plots
│   ├── counterfactual.py        # "What would change the prediction?"
│   ├── plain_english.py         # Natural language prediction explanations
│   ├── what_if.py               # Interactive feature modification → prediction
│   ├── adverse_action.py        # Finance: top N reasons for negative decision
│   ├── fairness_audit.py        # Disparate impact, equal opportunity, demographic parity
│   ├── model_card_generator.py  # Google model card format documentation
│   └── calibration.py           # Calibration curves, reliability diagrams
│
├── evaluation/                  # Benchmarking & evaluation
│   ├── agent_evaluator.py       # Test agent decision quality on known datasets
│   ├── model_comparator.py      # Statistical comparison (paired t-test, McNemar, bootstrap)
│   ├── bootstrap_ci.py          # Bootstrap confidence intervals for any metric
│   ├── domain_metrics.py        # Domain-specific metrics (KS, Gini, NNT, OEE)
│   ├── test_datasets/           # Known datasets for testing
│   └── benchmarks/              # Benchmark runner + results
│
├── logging_audit/               # Logging & audit trail
│   ├── structured_logger.py     # JSON-format structured logging
│   ├── decision_log.py          # Every agent decision with reasoning
│   ├── performance_log.py       # Timing per step, API call counts
│   ├── cost_tracker.py          # Claude API cost tracking per run
│   └── audit_trail_export.py    # Export for compliance (healthcare/finance)
│
├── session/                     # Session management
│   ├── session_manager.py       # Save/resume/list/delete (SQLite-backed)
│   ├── session_compare.py       # Compare two sessions on same data
│   └── session_export.py        # Export session as JSON for reproducibility
│
├── reports/                     # Report generation
│   ├── generators/
│   │   ├── html_report.py       # Interactive HTML with embedded Plotly
│   │   ├── pdf_report.py        # Print-ready PDF via WeasyPrint
│   │   ├── executive_summary.py # 1-page stakeholder PDF
│   │   ├── notebook_export.py   # Runnable Jupyter notebook
│   │   └── zip_packager.py      # ZIP all outputs
│   └── templates/               # Jinja2 HTML templates + CSS
│
├── serving/                     # Model serving
│   ├── api.py                   # FastAPI /predict + /health endpoints
│   ├── schemas.py               # Pydantic request/response models
│   ├── model_loader.py          # Load model from MLflow or pickle
│   └── Dockerfile               # Container for API deployment
│
├── tests/                       # Test suite
│   ├── conftest.py              # Shared pytest fixtures
│   ├── unit/                    # 9 test files (tools, connectors, domain, validation)
│   ├── integration/             # 4 test files (full pipeline, domain-specific paths)
│   ├── agent/                   # 3 test files (agent decision quality)
│   └── benchmarks/              # Benchmark runner
│
├── configs/                     # YAML configuration
│   ├── agent_prompts.yaml       # System prompts for all 8 agents
│   ├── domain_configs.yaml      # Domain detection + configuration
│   ├── tool_registry.yaml       # Tool registry (also in Python)
│   ├── default_settings.yaml    # Platform defaults
│   └── logging_config.yaml      # Logging configuration
│
├── scripts/                     # Utility scripts
│   ├── download_sample_datasets.py
│   ├── setup_database.py
│   ├── run_benchmarks.py
│   └── generate_demo_gif.py
│
└── docs/                        # Documentation
    ├── PRD.md                   # Product Requirements Document
    ├── SYSTEM_DESIGN.md         # System Design Document
    ├── TECH_DOC.md              # This file
    ├── architecture.md          # Architecture overview
    ├── domain_guide.md          # Domain detection and adaptation guide
    ├── tool_registry_reference.md # Complete tool reference
    ├── api_reference.md         # FastAPI endpoint docs
    ├── user_guide.md            # User-facing guide
    ├── developer_guide.md       # How to extend the platform
    └── deployment_guide.md      # Deployment instructions
```

---

## 3. Coding Standards

### 3.1 Python Style

| Rule | Standard |
|---|---|
| Python version | 3.11+ |
| Type hints | Required on all public functions |
| Docstrings | Google style on all public functions |
| Line length | 100 characters (configured in `pyproject.toml`) |
| Formatter | Black (line-length 100) |
| Import sorting | isort (black profile) |
| Linter | ruff (rules: E, F, W, I, N, UP, S, B, A, C4, SIM) |
| Type checker | mypy (ignore_missing_imports) |
| Path handling | `pathlib.Path` (never `os.path`) |
| Logging | `logging` module (never `print()` for operational messages) |
| Constants | UPPER_SNAKE_CASE in `core/constants.py` |

### 3.2 File Organization

| Rule | Standard |
|---|---|
| File size | Target 200-400 lines, max 800 |
| One class per file | Major components (agents, connectors) |
| `__init__.py` | Exports public interface only |
| Private functions | Prefix with `_` |
| Feature-organized | Group by domain, not by file type |

### 3.3 Error Handling

| Rule | Standard |
|---|---|
| Bare except | Never (except top-level agent wrapper) |
| Custom exceptions | All in `core/exceptions.py` |
| Error context | Always log before handling |
| Recovery | Graceful degradation over crashing |
| User messages | Clear, actionable error messages in UI |
| Server logs | Detailed with stack traces |

### 3.4 Immutability

| Rule | Standard |
|---|---|
| State updates | Create new dict/list, don't mutate existing |
| Function purity | Prefer pure functions in tool modules |
| Side effects | Isolate to agent wrappers and I/O boundaries |

---

## 4. API Reference

### 4.1 Prediction API (FastAPI)

**Base URL:** `http://localhost:8000`

#### POST /predict

Single-row or batch prediction using trained model.

**Request:**
```json
{
  "features": {
    "age": 45,
    "income": 65000,
    "tenure_months": 24
  }
}
```

**Response:**
```json
{
  "prediction": 1,
  "probability": 0.73,
  "confidence": "high",
  "explanation": {
    "top_features": [
      {"feature": "tenure_months", "contribution": -0.15},
      {"feature": "income", "contribution": 0.08}
    ]
  }
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "model_loaded": true,
  "model_name": "xgboost_v1"
}
```

#### GET /model-info

Model metadata.

**Response:**
```json
{
  "model_name": "xgboost_v1",
  "algorithm": "XGBoost",
  "features": ["age", "income", "tenure_months"],
  "target": "churn",
  "problem_type": "classification",
  "training_metrics": {
    "auc": 0.87,
    "f1": 0.82
  },
  "trained_at": "2026-04-22T15:30:00Z"
}
```

### 4.2 Internal APIs

#### LLM Config (`core/llm_config.py`)

```python
def invoke_llm_json(prompt: str, system_prompt: str, max_tokens: int = 4096) -> dict:
    """Send prompt to Claude, return parsed JSON response."""

def get_agent_system_prompt(agent_name: str, domain_config: dict | None) -> str:
    """Load system prompt for agent from configs/agent_prompts.yaml."""
```

#### Tool Registry (`agents/tools/tool_registry.py`)

```python
def get_tool(tool_name: str) -> dict:
    """Get tool metadata by name."""

def search_tools(query: str, domain: str = "all") -> list[dict]:
    """Search tools by description or use-case keywords."""

def get_tools_for_domain(domain: str, step: str) -> list[dict]:
    """Get all tools appropriate for a domain and pipeline step."""

def execute_tool(tool_name: str, params: dict, state: AutoDSState) -> dict:
    """Execute a tool with full logging and error handling."""
```

---

## 5. Configuration

### 5.1 Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API authentication |
| `AUTODS_LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `AUTODS_RANDOM_SEED` | No | `42` | Default random seed |
| `AUTODS_MAX_ROWS_PROFILE` | No | `100000` | Max rows for full profiling |
| `AUTODS_MLFLOW_URI` | No | `./mlruns` | MLflow tracking URI |
| `AUTODS_SESSION_DIR` | No | `./sessions` | Session storage directory |

### 5.2 YAML Configuration Files

#### `configs/agent_prompts.yaml`
System prompts for each agent. Loaded by `core/llm_config.py`. Each prompt contains:
- Agent role and responsibilities
- Domain-specific instructions (injected at runtime)
- Output format requirements (always JSON)
- Examples of expected behavior

#### `configs/domain_configs.yaml`
Domain detection keywords, metrics, and default parameters. Mirrors Python domain configs for external editing.

#### `configs/tool_registry.yaml`
Master tool catalog. Mirrors `agents/tools/tool_registry.py` for documentation and external tool discovery.

#### `configs/default_settings.yaml`
Platform defaults: max file size, chart theme, report styling, timeout values.

#### `configs/logging_config.yaml`
Python logging configuration: formatters, handlers, log levels per module.

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
           ┌──────────┐
           │ Benchmark│  ← 1 runner: 8+ datasets, end-to-end quality
           │  Tests   │
           ├──────────┤
           │  Agent   │  ← 3 files: decision quality tests
           │  Tests   │
           ├──────────┤
           │ Integra- │  ← 4 files: full pipeline paths
           │  tion    │
           ├──────────┤
           │   Unit   │  ← 9 files: tool functions, connectors, validators
           │  Tests   │
           └──────────┘
```

### 6.2 Test Categories

| Category | Count | What's Tested | Run Command |
|---|---|---|---|
| Unit | 9 files | Tool functions, connectors, domain detection, validators | `make test` |
| Integration | 4 files | Full pipeline: CSV → results, domain-specific paths | `make test-integration` |
| Agent | 3 files | Agent decision quality (right cleaning, right model) | `pytest tests/agent/` |
| Benchmark | 1 runner | Platform vs hand-tuned on 8+ standard datasets | `make benchmark` |

### 6.3 Coverage Target

- **Tool functions:** >= 80% line coverage
- **Core infrastructure:** >= 70% line coverage
- **Agents:** Decision quality tests (not line coverage)
- **Dashboard:** Visual/manual testing (Streamlit limits automated testing)

### 6.4 Test Fixtures

Shared fixtures in `tests/conftest.py`:
- `sample_csv_path` — Small test CSV file
- `sample_dataframe` — pandas DataFrame with mixed types
- `duckdb_connection` — In-memory DuckDB for testing
- `mock_llm` — Mock Claude responses for deterministic tests
- `sample_state` — Pre-populated AutoDSState for agent tests

### 6.5 Running Tests

```bash
make test              # Unit tests only
make test-integration  # Integration tests
make test-all          # All tests + coverage report (HTML)
make test-fast         # Unit tests, stop on first failure
make benchmark         # Benchmark suite on standard datasets
make lint              # ruff + mypy
make format            # black + isort + ruff --fix
```

---

## 7. Development Workflow

### 7.1 Setup

```bash
git clone https://github.com/your-username/autods-platform.git
cd autods-platform
make setup              # Installs deps, initializes DBs, downloads sample data
cp .env.example .env    # Add ANTHROPIC_API_KEY
make run                # Launch Streamlit at localhost:8501
```

### 7.2 Adding a New Domain

1. Create `domains/your_domain.py` extending `BaseDomainConfig`
2. Implement: `detection_keywords`, `primary_metrics`, `eda_questions`, `feature_questions`, `model_questions`, `cost_matrix`, `fairness`, `compliance_notes`, `report_style`, `special_encodings`
3. Add import to `domains/domain_registry.py` in `_get_all_domain_configs()`
4. Add domain-specific tools to `agents/tools/domain_tools.py`
5. Create report template in `reports/templates/your_domain_report.html`
6. Add integration test in `tests/integration/test_your_domain_path.py`

### 7.3 Adding a New Connector

1. Create connector in appropriate subdirectory under `data_connectors/`
2. Extend `BaseConnector` from `data_connectors/base.py`
3. Implement: `connect()`, `load()`, `get_schema()`, `validate()`
4. Register in `data_connectors/connector_factory.py`
5. Add unit test in `tests/unit/test_connectors.py`

### 7.4 Adding a New Tool

1. Add function to appropriate module in `agents/tools/`
2. Register in `agents/tools/tool_registry.py` with full metadata:
   - `name`, `function` (importable path), `description`, `when_to_use`
   - `requirements` (min columns, column types needed)
   - `domains` (which domains this applies to)
   - `parameters` and `output` schemas
3. Add unit test in `tests/unit/`

### 7.5 Git Conventions

| Type | Format | Example |
|---|---|---|
| Feature | `feat: description` | `feat: add KS-test to stats tools` |
| Bug fix | `fix: description` | `fix: handle NaN in correlation matrix` |
| Refactor | `refactor: description` | `refactor: extract domain detection to separate module` |
| Docs | `docs: description` | `docs: add developer guide for new domains` |
| Tests | `test: description` | `test: add edge case tests for single-class target` |
| Chore | `chore: description` | `chore: update requirements.txt` |

Branch naming: `feature/agent-name`, `fix/issue-description`

---

## 8. Key Design Patterns

### 8.1 Agent Pattern

```python
def agent_name(state: AutoDSState) -> AutoDSState:
    """Agent node in LangGraph."""
    # 1. Read state
    # 2. If Guided/Expert → generate questions → interrupt
    # 3. Select tools from registry
    # 4. Execute tools (Python, not LLM)
    # 5. LLM interprets results
    # 6. Update state
    # 7. Return state
```

### 8.2 Tool Execution Pattern

```python
def execute_tool(tool_name, params, state):
    tool = TOOL_REGISTRY[tool_name]
    fn = import_function(tool["function"])
    start = time.time()
    try:
        result = fn(**params)
        log_success(tool_name, params, time.time() - start, state)
        return result
    except Exception as e:
        log_failure(tool_name, params, time.time() - start, e, state)
        raise
```

### 8.3 LLM Degradation Pattern

```python
def get_llm_summary(results, state):
    try:
        return invoke_llm_json(build_prompt(results), ...)
    except LLMAPIError:
        return template_fallback_summary(results)
```

### 8.4 Domain-Aware Question Pattern

```python
def generate_questions(state, step):
    questions = UNIVERSAL_QUESTIONS[step].copy()
    questions += state["domain_config"].get("questions", {}).get(step, [])
    if has_datetime_columns(state):
        questions += TEMPORAL_QUESTIONS[step]
    if len(questions) > 8:
        questions = rank_by_relevance(questions, state)
    return questions
```

### 8.5 Connector Factory Pattern

```python
def get_connector(source_type: str, **kwargs) -> BaseConnector:
    connectors = {
        "csv": CSVConnector,
        "excel": ExcelConnector,
        "parquet": ParquetConnector,
        "postgres": PostgresConnector,
        # ...
    }
    return connectors[source_type](**kwargs)
```

---

## 9. Performance Targets

| Operation | Target | Strategy |
|---|---|---|
| CSV upload (100K rows) | < 5 seconds | DuckDB COPY, not pandas |
| Data profiling (100K rows) | < 30 seconds | Sampling for large datasets |
| EDA (full suite) | < 2 minutes | Parallel tool execution where possible |
| Model training (5 models) | < 5 minutes | FLAML time budget, early stopping |
| Report generation | < 30 seconds | Jinja2 templates, pre-rendered charts |
| Dashboard page load | < 3 seconds | Streamlit caching, lazy loading |
| Prediction API response | < 200ms | Pre-loaded model, no LLM call |

---

## 10. Dependency Management

### 10.1 Production Dependencies (`requirements.txt`)

Core groups:
- **Agent framework:** langgraph, langchain-anthropic, langchain-core
- **Data:** pandas, duckdb, pyarrow, openpyxl, ydata-profiling
- **ML:** scikit-learn, xgboost, lightgbm, catboost, flaml
- **Stats:** scipy, statsmodels, lifelines
- **Explain:** shap, fairlearn
- **Viz:** plotly
- **Dashboard:** streamlit
- **Reports:** jinja2, weasyprint, nbformat
- **Tracking:** mlflow, chromadb
- **API:** fastapi, uvicorn, pydantic

### 10.2 Dev Dependencies (`requirements-dev.txt`)

- pytest, pytest-cov, pytest-mock
- ruff, black, isort, mypy
- pre-commit

### 10.3 Python Version

Requires Python 3.11+ for:
- `TypedDict` with `total=False`
- `list[str]` syntax (PEP 585)
- `str | None` union syntax (PEP 604)
- `tomllib` in stdlib
