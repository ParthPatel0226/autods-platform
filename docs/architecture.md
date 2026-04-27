# AutoDS Architecture

## System Overview

AutoDS is a multi-agent data science platform built on LangGraph. Eight specialized AI agents collaborate through a state machine to execute the complete data science workflow -- from raw data ingestion to deployed ML models.

## Architecture Diagram

```
+-------------------------------------------------------------+
|                     DATA INPUT LAYER                         |
|  Files | Databases | APIs | Cloud | Clipboard | Samples      |
|  (30+ connectors via BaseConnector + ConnectorFactory)       |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|              DOMAIN DETECTION ENGINE                         |
|  Weighted keyword matching across column names               |
|  Three-tier scoring: strong (3x) | moderate (2x) | weak (1x)|
|  Domains: Healthcare | Finance | E-commerce | Marketing      |
|           HR | Manufacturing | Generic (fallback)            |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|         LANGGRAPH ORCHESTRATOR (StateGraph)                   |
|                                                              |
|  +----------+  +-----+  +----------+  +---------+           |
|  | Profiler |->| EDA |->| Features |->| Modeling|           |
|  +----------+  +-----+  +----------+  +---------+           |
|       |            |          |             |                |
|       v            v          v             v                |
|  [Questions]  [Questions] [Questions]  [Questions]           |
|  (Guided/     (Guided/    (Guided/     (Guided/             |
|   Expert)      Expert)     Expert)      Expert)             |
|                                                              |
|  +------------+  +--------+  +----------+                   |
|  | Explainer  |->| Report |->| Deploy   |                   |
|  +------------+  +--------+  +----------+                   |
|                                                              |
|  +------------+                                              |
|  | Follow-Up  | (post-pipeline conversational)               |
|  +------------+                                              |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    OUTPUT LAYER                               |
|  Streamlit Dashboard | HTML/PDF Reports | Jupyter Notebook   |
|  FastAPI Prediction API | Session Export | ZIP Package        |
+-------------------------------------------------------------+
```

## Component Architecture

### 1. Data Connectors (`data_connectors/`)

All connectors extend `BaseConnector` (abstract base class) and are registered in `ConnectorFactory` for lazy-loaded instantiation.

| Category | Connectors | Count |
|----------|-----------|-------|
| File | CSV, Excel, Parquet, JSON, XML, SQLite, PDF, Compressed, Statistical | 9 |
| Database | PostgreSQL, MySQL, SQL Server, DuckDB, BigQuery, Snowflake, Redshift | 7 |
| API | REST API, Web Scraper, Kaggle, HuggingFace, Google Sheets | 5 |
| Cloud | AWS S3, Google Cloud Storage, Azure Blob | 3 |
| Direct | Clipboard, Manual Entry, Sample Datasets | 3 |
| Public Data | World Bank, FRED, Yahoo Finance, Census | 4 |

### 2. Agent System (`agents/`)

Every agent follows the pattern: **LLM decides what to do, Python tools do it.**

```python
def agent_node(state: AutoDSState) -> AutoDSState:
    # 1. Read context from state
    # 2. Use LLM to choose analyses/actions
    # 3. Execute via registered Python tool functions
    # 4. Use LLM to interpret results
    # 5. Write results back to state
    return state
```

| Agent | Lines | Purpose |
|-------|-------|---------|
| Orchestrator | 310 | Goal decomposition, pipeline routing |
| Data Profiler | 415 | Schema detection, quality scoring, cleaning |
| EDA Agent | 821 | Domain-aware analysis, chart generation, insights |
| Feature Engineer | 779 | Per-column decisions, domain features |
| Modeling Agent | 678 | Algorithm selection, training, MLflow logging |
| Explainability | 517 | SHAP, fairness, model cards, counterfactuals |
| Report Agent | 522 | HTML, PDF, executive summary, notebook |
| Deployment | 428 | FastAPI endpoint generation, Dockerfile |
| Follow-Up | 358 | Post-pipeline Q&A, on-demand analysis |

### 3. Tool Registry (`agents/tools/tool_registry.py`)

Central registry of all computation functions. Each entry has:
- Function path, description, when to use
- Required column types and minimum columns
- Valid domains
- Input parameters and output format

Categories: 16 statistical tests, 25+ chart types, 30+ feature techniques, 20+ ML algorithms, domain-specific calculations.

### 4. Domain System (`domains/`)

Each domain provides:
- **Detection keywords** (strong/moderate/weak)
- **Primary metrics** per problem type
- **EDA, feature, and model questions** for guided mode
- **Cost matrix defaults** (e.g., FN=10, FP=1 for healthcare)
- **Fairness requirements** (protected attributes, metric)
- **Compliance notes** (HIPAA, fair lending, etc.)
- **Report terminology** mapping

### 5. State Management (`core/state.py`)

Single `AutoDSState` TypedDict flows through the entire pipeline. Contains:
- Session info (ID, user mode)
- Data references (DuckDB tables, schema info)
- Domain detection results
- Per-step results (EDA, features, models, explanations)
- Pipeline metadata (seed, data hash, API costs, logs)

State is checkpointed to SQLite after every node via LangGraph's `SqliteSaver`.

### 6. Validation Layer (`validation/`)

Five validators run at system boundaries:
- **Input Sanitizer** -- encoding, mixed types, date parsing
- **Edge Case Detector** -- 9 checks (leakage, imbalance, constant columns, etc.)
- **Schema Validator** -- extract, validate, and adapt schemas
- **Model Validator** -- performance thresholds, overfitting detection
- **Data Drift Checker** -- KS test, PSI calculation

## Design System & User Interface

The dashboard features a **professional dual-theme design system** with 80+ CSS custom properties:

### Theme System
- **Light Mode** (default) -- white backgrounds, slate neutrals, high contrast
- **Dark Mode** -- deep navy backgrounds (#0c0f1a), optimized for extended use
- **Implementation** -- theme values baked into `:root` CSS via `shared_css.py`, no JavaScript
- **Toggle** -- sidebar button syncs theme across all pages instantly

### Design Tokens
- **Backgrounds**: primary, card, elevated, inset, overlay
- **Text**: primary, secondary, muted, inverse
- **Accents**: primary (#2563eb blue), secondary (#0891b2 cyan), plus success/warning/danger/info/purple
- **Typography**: Plus Jakarta Sans (display), Inter (body), JetBrains Mono (code) via Google Fonts
- **Spacing**: 1-12 scale (0.25rem to 3rem)
- **Shadows**: xs through lg, plus glow and focus rings
- **Transitions**: fast (120ms), normal (200ms), slow (350ms) with cubic-bezier easing

### Component Library
- `.glass-card` -- elevated card with subtle borders and shadows
- `.pill-tabs` / `.pill-tab` -- tab-like controls with pill styling
- `.glass-table` -- data table with row hover effects
- `.badge-*` / `.status-dot-*` -- status indicators and badges
- Reusable animations: fadeIn, slideUp, shimmer, pulse, borderPulse

### Landing Page Design
- Dark gradient hero banner (135deg: #1e3a5f → #0f172a → #1a1040)
- Animated gradient title text with floating stat pills
- Bento-grid feature cards with top-border gradient on hover
- Drag-and-drop upload zone with format chips
- Sample dataset quick-start chips
- 5-column stats strip showing platform capabilities

### Chart Theming
Helper function `get_plotly_layout(is_dark)` provides theme-aware Plotly configuration with:
- Dynamic background colors matching theme
- Proper text colors and font selections
- Grid and axis colors matching neutrals
- Consistent color palette across 8 chart colors

## Key Design Decisions

1. **LLM decides, Python executes** -- Claude chooses analyses; registered tool functions compute.
2. **Tool Registry** -- every technique registered with metadata, nothing "forgotten."
3. **Domain-aware everything** -- EDA questions to model metrics to report language.
4. **Three user modes** -- Auto (no questions), Guided (recommendations), Expert (full control).
5. **Human-in-the-loop** -- LangGraph interrupts for user decisions in Guided/Expert modes.
6. **Graceful degradation** -- if one analysis fails, skip and continue.
7. **Reproducibility** -- random seed, data hash, requirements snapshot, full state export.
8. **Cost optimization** -- batch LLM decisions, cache responses, temperature 0, token tracking.
9. **Design consistency** -- shared CSS system via `shared_css.py`, zero hardcoded colors in pages.

## Data Flow

1. User uploads data -> Universal Loader detects format -> loads to DuckDB
2. Domain Detector analyzes columns -> loads domain config
3. Data Profiler assesses quality -> recommends cleaning
4. EDA Agent generates analyses -> produces charts + insights
5. Feature Engineer creates domain-specific features
6. Modeling Agent trains + evaluates -> logs to MLflow
7. Explainability Agent generates SHAP, fairness, model cards
8. Report Agent produces HTML/PDF/notebook outputs
9. Follow-Up Agent handles post-pipeline questions

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph StateGraph |
| LLM | Claude API (Anthropic) |
| Data Engine | DuckDB + pandas |
| ML | scikit-learn, XGBoost, LightGBM, CatBoost, FLAML |
| Experiment Tracking | MLflow |
| Explainability | SHAP, fairlearn |
| Dashboard | Streamlit |
| API Serving | FastAPI + Uvicorn |
| Reports | Jinja2 + WeasyPrint + nbformat |
| Vector Memory | ChromaDB |
| Persistence | SQLite |
