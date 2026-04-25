# Application Architecture Design
# AutoDS — Autonomous Data Science Platform

**Version:** 1.0
**Date:** 2026-04-22

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layered Architecture](#2-layered-architecture)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Data Architecture](#5-data-architecture)
6. [Agent Orchestration Architecture](#6-agent-orchestration-architecture)
7. [Integration Architecture](#7-integration-architecture)
8. [UI/UX Design Architecture](#8-uiux-design-architecture)
9. [Security Architecture](#9-security-architecture)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Observability Architecture](#11-observability-architecture)

---

## 1. System Overview

AutoDS is a local-first, multi-agent data science platform with three main interfaces:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AutoDS Platform                                     │
│                                                                              │
│   ┌─────────────┐    ┌──────────────────┐    ┌───────────────────────────┐  │
│   │  Streamlit   │    │  FastAPI          │    │  CLI (future)             │  │
│   │  Dashboard   │    │  Prediction API   │    │  make run / make test     │  │
│   │  (primary)   │    │  (serving)        │    │  (ops only today)        │  │
│   └──────┬───────┘    └────────┬─────────┘    └────────────┬────────────┘  │
│          │                     │                            │               │
│          └─────────────────────┼────────────────────────────┘               │
│                                │                                            │
│                    ┌───────────▼──────────────┐                             │
│                    │    Core Engine            │                             │
│                    │    (LangGraph + Agents    │                             │
│                    │     + Tool Registry       │                             │
│                    │     + Domain Configs)     │                             │
│                    └───────────┬──────────────┘                             │
│                                │                                            │
│          ┌─────────────────────┼─────────────────────────┐                 │
│          │                     │                          │                  │
│   ┌──────▼──────┐    ┌────────▼───────┐    ┌────────────▼─────────────┐   │
│   │  DuckDB      │    │  SQLite +       │    │  MLflow + File System    │   │
│   │  (data)      │    │  ChromaDB       │    │  (experiments + reports) │   │
│   └─────────────┘    │  (state+memory) │    └────────────────────────┘   │
│                       └────────────────┘                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layered Architecture

### 2.1 Four-Layer Stack

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION                                            │
│                                                                   │
│  Streamlit Dashboard          FastAPI Prediction API              │
│  ├── 9 sequential pages       ├── POST /predict                  │
│  ├── 8 reusable components    ├── GET /health                    │
│  ├── Session state mgmt       └── GET /model-info                │
│  └── Widget-based interaction                                     │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2: ORCHESTRATION                                           │
│                                                                   │
│  LangGraph StateGraph                                             │
│  ├── 10 nodes (agents + question generators)                     │
│  ├── Conditional routing (mode × domain × data)                  │
│  ├── Interrupt mechanism (human-in-the-loop)                     │
│  ├── SQLite checkpointing (crash recovery)                       │
│  └── AutoDSState (shared TypedDict)                              │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3: INTELLIGENCE                                            │
│                                                                   │
│  8 AI Agents            Tool Registry (100+ tools)                │
│  ├── Orchestrator        ├── 20+ stat tests                      │
│  ├── Domain Detector     ├── 25+ chart types                     │
│  ├── Data Profiler       ├── 50+ feature techniques              │
│  ├── EDA Agent           ├── 20+ ML algorithms                   │
│  ├── Feature Engineer    └── Domain-specific tools               │
│  ├── Modeling Agent                                               │
│  ├── Explainability      7 Domain Configs                        │
│  ├── Report Agent        ├── Healthcare                          │
│  └── Follow-Up Agent     ├── Finance                             │
│                           ├── E-commerce                          │
│  Claude API (LLM)        ├── Marketing                           │
│  └── Decision-making     ├── HR                                  │
│      + interpretation    ├── Manufacturing                       │
│                           └── Generic                             │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4: DATA                                                    │
│                                                                   │
│  DuckDB           SQLite          ChromaDB        MLflow          │
│  (warehouse)      (checkpoints)   (vector mem)    (experiments)   │
│                                                                   │
│  30+ Data Connectors                                              │
│  ├── File: CSV, Excel, Parquet, JSON, XML, PDF, SAS, STATA, SQLite│
│  ├── Database: Postgres, MySQL, SQL Server, BigQuery, Snowflake  │
│  ├── API: REST, Kaggle, HuggingFace, Google Sheets, scraping     │
│  ├── Cloud: S3, GCS, Azure Blob                                  │
│  └── Direct: Clipboard, manual entry, sample datasets            │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Interaction Rules

| From → To | Allowed | Mechanism |
|---|---|---|
| Presentation → Orchestration | Yes | `st.session_state` ↔ LangGraph state |
| Presentation → Intelligence | No | Must go through Orchestration layer |
| Presentation → Data | Read-only for display | DuckDB queries for chart data |
| Orchestration → Intelligence | Yes | Agent function calls within graph nodes |
| Intelligence → Data | Yes | Tool functions read/write DuckDB, MLflow |
| Intelligence → External | Yes (Claude only) | LLM API calls for decisions |

---

## 3. Backend Architecture

### 3.1 Core Engine Components

```
core/
├── graph.py          ← Central nervous system
│   ├── StateGraph definition
│   ├── Node registration (10 nodes)
│   ├── Edge routing functions (5 routers)
│   ├── Interrupt configuration
│   └── Checkpointer setup
│
├── state.py          ← Single source of truth
│   ├── AutoDSState TypedDict (35+ fields)
│   ├── DataSourceInfo, ColumnInfo, QuestionResponse, ModelResult subtypes
│   └── create_initial_state() factory
│
├── llm_config.py     ← LLM abstraction
│   ├── get_llm() → ChatAnthropic instance
│   ├── invoke_llm_json() → parsed JSON from Claude
│   ├── get_agent_system_prompt() → YAML-loaded prompts
│   └── Token counting + cost estimation
│
├── memory.py         ← Persistence layer
│   ├── SQLite for session state
│   └── ChromaDB for semantic search (follow-up agent)
│
├── user_modes.py     ← Mode behavior logic
│   ├── should_show_questions(mode, step) → bool
│   ├── get_default_choices(mode, domain, step) → dict
│   └── Mode-specific routing helpers
│
├── constants.py      ← Global constants
│   ├── MODE_AUTO, MODE_GUIDED, MODE_EXPERT
│   ├── SUPPORTED_FORMATS, MAX_FILE_SIZE
│   ├── DEFAULT_SEED, DEFAULT_CV_FOLDS
│   └── PIPELINE_STEPS list
│
└── exceptions.py     ← Exception hierarchy
    ├── BaseAutoDSError
    ├── DataIngestionError (+ subtypes)
    ├── DataQualityError (+ subtypes)
    ├── AgentError (+ subtypes)
    ├── ModelingError (+ subtypes)
    └── ReportError (+ subtypes)
```

### 3.2 Agent Component Model

Each agent is a standalone module that:

```
┌──────────────────────────────────────────────┐
│               Agent Module                    │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Main Function (LangGraph node)         │  │
│  │ def agent_name(state) -> state:        │  │
│  │   1. Read state                        │  │
│  │   2. Generate questions (if Guided)    │  │
│  │   3. Select tools from registry        │  │
│  │   4. Execute tools                     │  │
│  │   5. LLM interprets results            │  │
│  │   6. Update state                      │  │
│  │   7. Return state                      │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Question Gen  │  │ Private Helpers      │  │
│  │ _generate_*   │  │ _auto_select_*       │  │
│  │ _parse_user_* │  │ _generate_summary    │  │
│  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
  ┌──────────────┐    ┌──────────────┐
  │ Tool Registry │    │ Domain Config │
  │ (execute)     │    │ (customize)   │
  └──────────────┘    └──────────────┘
```

### 3.3 Data Connector Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Connector Factory                    │
│  connector_factory.get_connector(type, **kwargs)     │
└────────────────────────┬─────────────────────────────┘
                         │
           ┌─────────────┼─────────────────────┐
           │             │                     │
     ┌─────▼──────┐ ┌───▼──────────┐  ┌──────▼────────┐
     │ File        │ │ Database      │  │ API            │
     │ Connectors  │ │ Connectors    │  │ Connectors     │
     ├─────────────┤ ├──────────────┤  ├───────────────┤
     │ CSV         │ │ PostgreSQL   │  │ REST API       │
     │ Excel       │ │ MySQL        │  │ Kaggle         │
     │ Parquet     │ │ SQL Server   │  │ HuggingFace    │
     │ JSON        │ │ DuckDB       │  │ Google Sheets  │
     │ XML         │ │ BigQuery     │  │ Web Scraper    │
     │ PDF         │ │ Snowflake    │  │ Public Data:   │
     │ SAS/STATA   │ │ Redshift     │  │  World Bank    │
     │ SQLite      │ └──────────────┘  │  FRED          │
     │ Compressed  │                    │  Yahoo Finance │
     └─────────────┘                    │  US Census     │
                                        └───────────────┘
           │
           │ All implement BaseConnector:
           │   connect() → validate connection
           │   load() → DataFrame
           │   get_schema() → column metadata
           │   validate() → data quality checks
           │
           ▼
     ┌─────────────────┐
     │ Universal Loader │ ← Smart auto-detection layer
     │  - format        │
     │  - encoding      │
     │  - delimiter     │
     │  - header row    │
     └─────────────────┘
           │
           ▼
     ┌─────────────────┐
     │ Multi-Source Mgr  │ ← Join multiple sources
     │ + Schema Matcher  │ ← AI-suggested join keys
     └─────────────────┘
           │
           ▼
     ┌─────────────────┐
     │ DuckDB Table     │ ← All data lives here
     └─────────────────┘
```

---

## 4. Frontend Architecture

### 4.1 Streamlit Application Structure

```
dashboard/
├── app.py                     ← Main entry point + global layout
│   ├── Page config (title, icon, layout)
│   ├── Sidebar (mode selector, session management)
│   └── Tab routing (placeholder for page system)
│
├── pages/                     ← Sequential workflow pages
│   ├── 01_upload.py           ← Data source selection + upload
│   ├── 02_configure.py        ← Domain + mode + target + goals
│   ├── 03_eda_interactive.py  ← Interactive EDA with questions
│   ├── 04_feature_engineering.py ← Per-column feature control
│   ├── 05_modeling.py         ← Model training + comparison
│   ├── 06_explainability.py   ← SHAP, fairness, what-if
│   ├── 07_predict.py          ← Batch + single predictions
│   ├── 08_chat.py             ← Follow-up conversational UI
│   └── 09_download.py         ← Download all outputs
│
└── components/                ← Reusable UI components
    ├── mode_selector.py       ← Auto/Guided/Expert toggle
    ├── domain_badge.py        ← Domain icon + confidence
    ├── approval_widget.py     ← Human-in-the-loop approval
    ├── question_renderer.py   ← 6 question types → widgets
    ├── workflow_progress.py   ← Step progress indicator
    ├── metric_cards.py        ← KPI display cards
    ├── chart_container.py     ← Plotly chart + export
    └── download_buttons.py    ← Format-specific downloads
```

### 4.2 Page Flow Architecture

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│ 01 Upload  │───▶│02 Configure│───▶│  03 EDA   │───▶│04 Features │
│            │    │            │    │Interactive│    │Engineering │
│ • File     │    │ • Domain   │    │           │    │            │
│ • Database │    │ • Mode     │    │ • Charts  │    │ • Per-col  │
│ • API      │    │ • Target   │    │ • Stats   │    │   control  │
│ • Clipboard│    │ • Goals    │    │ • Q&A     │    │ • Domain   │
│ • Sample   │    │            │    │           │    │   recs     │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
                                                          │
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌──────▼────┐
│09 Download │◀───│  08 Chat  │◀───│07 Predict  │◀───│05 Modeling │
│            │    │           │    │            │    │           │
│ • HTML     │    │ • NL Q&A  │    │ • Batch    │    │ • Train   │
│ • PDF      │    │ • Chart   │    │ • Single   │    │ • Compare │
│ • Exec Sum │    │   request │    │   row      │    │ • Select  │
│ • Notebook │    │ • Tool    │    │ • Explain  │    │ • Evaluate│
│ • ZIP all  │    │   search  │    │            │    │           │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
                                                          │
                                                   ┌──────▼────┐
                                                   │06 Explain  │
                                                   │           │
                                                   │ • SHAP    │
                                                   │ • Fairness│
                                                   │ • What-if │
                                                   │ • Model   │
                                                   │   card    │
                                                   └───────────┘
```

### 4.3 State Management

```
Streamlit Session State (st.session_state)
│
├── user_mode: str              ← "auto" | "guided" | "expert"
├── session_id: str             ← Unique session identifier
├── pipeline_state: AutoDSState ← Full LangGraph state (synced)
├── current_page: str           ← Active page for routing
│
├── UI-specific state:
│   ├── uploaded_files: list    ← File upload widgets
│   ├── chart_configs: dict     ← User chart customizations
│   ├── expanded_sections: set  ← Accordion state
│   └── pending_answers: dict   ← Unsaved question responses
│
└── Sync mechanism:
    ├── Dashboard → LangGraph: on question submit / approval
    ├── LangGraph → Dashboard: on step completion / interrupt
    └── Checkpointed: after every LangGraph node execution
```

### 4.4 Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Page (e.g., 03_eda_interactive)            │
│                                                              │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │  workflow_progress        │  │  domain_badge             │ │
│  │  (sidebar or top)         │  │  (header area)            │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Main Content Area                                        ││
│  │                                                           ││
│  │  ┌─────────────────┐  ┌────────────────────────────────┐ ││
│  │  │ question_renderer│  │ chart_container                 │ ││
│  │  │ (Guided/Expert)  │  │ ├── Plotly chart               │ ││
│  │  │                  │  │ ├── Export PNG button           │ ││
│  │  │ • single_select  │  │ └── Fullscreen toggle          │ ││
│  │  │ • multi_select   │  └────────────────────────────────┘ ││
│  │  │ • slider         │                                     ││
│  │  │ • per_column_tbl │  ┌────────────────────────────────┐ ││
│  │  │ • text_input     │  │ metric_cards                    │ ││
│  │  │ • number_input   │  │ ├── KPI Card 1                 │ ││
│  │  └─────────────────┘  │ ├── KPI Card 2                 │ ││
│  │                        │ └── KPI Card N                 │ ││
│  │  ┌─────────────────┐  └────────────────────────────────┘ ││
│  │  │ approval_widget  │                                     ││
│  │  │ (human-in-loop)  │  ┌────────────────────────────────┐ ││
│  │  │ [Approve][Modify]│  │ Insights / Summary text         │ ││
│  │  └─────────────────┘  │ (LLM-generated)                 │ ││
│  │                        └────────────────────────────────┘ ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  download_buttons (bottom)                                ││
│  │  [HTML Report] [PDF] [CSV Data] [Notebook]               ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Data Architecture

### 5.1 Data Lifecycle

```
Phase 1: INGESTION
  Raw file/connection → Connector → Universal Loader → Input Sanitizer → DuckDB table

Phase 2: PROFILING
  DuckDB table → ydata-profiling → schema_info + data_profile in state

Phase 3: TRANSFORMATION
  DuckDB table → Feature tools → Engineered features → DuckDB feature table

Phase 4: MODELING
  Feature table → train/test split → sklearn/XGBoost/LightGBM → trained models → MLflow

Phase 5: OUTPUT
  State + models → Report generators → HTML/PDF/IPYNB files → outputs/ directory
```

### 5.2 DuckDB as Data Warehouse

```
DuckDB (in-process, embedded)
│
├── raw_data_{source_name}      ← Original data as-loaded
├── joined_data                 ← After multi-source join
├── profiled_data               ← After cleaning actions
├── feature_data                ← After feature engineering
├── train_data / test_data      ← After split
└── prediction_data             ← New data for predictions
```

**Why DuckDB:**
- Embedded (no server), zero-config
- Columnar storage → fast analytical queries
- Out-of-core processing → handles datasets larger than RAM
- SQL interface → clean data transformations
- Parquet/CSV/JSON native readers → efficient ingestion

### 5.3 MLflow Experiment Structure

```
mlruns/
└── {experiment_id}/            ← One experiment per session
    ├── {run_id_1}/             ← One run per model trained
    │   ├── params/             ← Hyperparameters
    │   ├── metrics/            ← Performance metrics
    │   ├── artifacts/          ← Model pickle, feature list, scaler
    │   └── tags/               ← Domain, problem type, user mode
    ├── {run_id_2}/
    └── ...
```

### 5.4 Session Storage

```
sessions/
├── checkpoints.db              ← LangGraph state checkpoints (SQLite)
├── chromadb/                   ← Vector embeddings for follow-up search
└── {session_id}.json           ← Exported session for sharing
```

---

## 6. Agent Orchestration Architecture

### 6.1 LangGraph StateGraph Definition

```python
# core/graph.py — simplified representation

workflow = StateGraph(AutoDSState)

# Register nodes
workflow.add_node("domain_detection",   domain_detector_agent)
workflow.add_node("data_profiling",     data_profiler_agent)
workflow.add_node("eda_questions",      eda_generate_questions)
workflow.add_node("eda_execute",        eda_execute_analyses)
workflow.add_node("fe_questions",       fe_generate_questions)
workflow.add_node("fe_execute",         fe_execute_engineering)
workflow.add_node("model_questions",    model_generate_questions)
workflow.add_node("model_execute",      model_train_evaluate)
workflow.add_node("explain",           explainability_agent)
workflow.add_node("report",            report_agent)

# Define edges
workflow.add_edge(START, "domain_detection")
workflow.add_edge("domain_detection", "data_profiling")
workflow.add_conditional_edges("data_profiling", route_after_profiling)
workflow.add_conditional_edges("eda_questions", route_after_eda_questions)
workflow.add_conditional_edges("eda_execute", route_after_eda)
# ... etc

# Compile with checkpointing + interrupts
app = workflow.compile(
    checkpointer=SqliteSaver.from_conn_string("sessions/checkpoints.db"),
    interrupt_before=["eda_execute", "fe_execute", "model_execute"]
)
```

### 6.2 Routing Logic Matrix

| After Node | Condition | Next Node |
|---|---|---|
| data_profiling | Auto mode | eda_execute |
| data_profiling | Guided/Expert mode | eda_questions |
| data_profiling | Critical errors | error_handler |
| eda_execute | Has target column | fe_questions (or fe_execute if Auto) |
| eda_execute | No target (EDA-only) | report |
| fe_execute | Always | model_questions (or model_execute if Auto) |
| model_execute | Always | explain |
| explain | Always | report |
| report | Always | END |

### 6.3 Interrupt & Resume Flow

```
Streamlit Dashboard                    LangGraph Engine
      │                                      │
      │  1. User uploads data                │
      │─────────────────────────────────────▶│
      │                                      │ 2. Run: domain → profile → eda_questions
      │                                      │
      │  3. Interrupt! Questions ready       │
      │◀─────────────────────────────────────│
      │                                      │ (state checkpointed)
      │  4. Render questions in UI           │
      │  5. User answers questions           │
      │                                      │
      │  6. Resume with answers              │
      │─────────────────────────────────────▶│
      │                                      │ 7. Run: eda_execute → fe_questions
      │                                      │
      │  8. Interrupt! More questions        │
      │◀─────────────────────────────────────│
      │                                      │
      │  ... (repeat for each step) ...      │
      │                                      │
      │  N. Pipeline complete                │
      │◀─────────────────────────────────────│
      │                                      │
      │  N+1. Display results + downloads    │
      │                                      │
```

---

## 7. Integration Architecture

### 7.1 Claude API Integration

```
┌──────────────────────────────────────────────────────┐
│                Agent Code                             │
│                                                      │
│  llm = get_llm()                                     │
│  response = invoke_llm_json(                         │
│      prompt=structured_prompt,                       │
│      system_prompt=agent_system_prompt,               │
│      max_tokens=4096                                 │
│  )                                                   │
└─────────────────────┬────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│            core/llm_config.py                         │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ ChatAnthropic(                                │    │
│  │     model="claude-sonnet-4-20250514",         │    │
│  │     temperature=0,                            │    │
│  │     max_tokens=4096                           │    │
│  │ )                                             │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  Features:                                           │
│  • Structured JSON output (always)                   │
│  • Token counting per call                           │
│  • Cost estimation                                   │
│  • Retry with backoff on API errors                  │
│  • Response caching for similar prompts              │
│  • Agent-specific system prompts from YAML           │
└──────────────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│            Anthropic Claude API                       │
│            (external service)                        │
│                                                      │
│  What is sent:                                       │
│  ✅ Column names, data types, summary statistics      │
│  ✅ Analysis results, metric values                   │
│  ✅ Domain context, question options                  │
│  ❌ Never: raw row-level data                         │
│  ❌ Never: PII, PHI, credentials                      │
└──────────────────────────────────────────────────────┘
```

### 7.2 MLflow Integration

```
Agent Code (modeling_agent.py)
    │
    │  mlflow.start_run()
    │  mlflow.log_params(hyperparams)
    │  mlflow.log_metrics(eval_metrics)
    │  mlflow.sklearn.log_model(model, "model")
    │  mlflow.log_artifact(feature_importance_plot)
    │  mlflow.end_run()
    │
    ▼
mlruns/ (local directory)
    │
    ├── Experiment per session
    ├── Run per model trained
    ├── Params: algorithm, hyperparameters
    ├── Metrics: AUC, F1, RMSE, domain-specific
    ├── Artifacts: model, scaler, feature list
    └── Tags: domain, mode, problem_type
```

---

## 8. UI/UX Design Architecture

### 8.1 Design System

**Color Palette:**

| Token | Value | Usage |
|---|---|---|
| `--color-primary` | `#4F46E5` (Indigo 600) | Primary actions, active states |
| `--color-success` | `#059669` (Emerald 600) | Completed steps, positive metrics |
| `--color-warning` | `#D97706` (Amber 600) | Warnings, attention needed |
| `--color-danger` | `#DC2626` (Red 600) | Errors, critical issues |
| `--color-info` | `#2563EB` (Blue 600) | Informational, recommendations |
| `--color-surface` | `#F8FAFC` (Slate 50) | Card backgrounds |
| `--color-text` | `#1E293B` (Slate 800) | Primary text |
| `--color-muted` | `#64748B` (Slate 500) | Secondary text, captions |

**Domain-Specific Accents:**

| Domain | Accent Color | Icon |
|---|---|---|
| Healthcare | `#0891B2` (Cyan 600) | 🏥 |
| Finance | `#059669` (Emerald 600) | 💰 |
| E-commerce | `#7C3AED` (Violet 600) | 🛒 |
| Marketing | `#EA580C` (Orange 600) | 📢 |
| HR | `#2563EB` (Blue 600) | 👥 |
| Manufacturing | `#CA8A04` (Yellow 600) | 🏭 |
| Generic | `#6366F1` (Indigo 500) | 📊 |

### 8.2 Layout Architecture

**Global Layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  Sidebar (280px, collapsible)   │  Main Content (fluid)          │
│                                  │                                │
│  ┌────────────────────────────┐ │  ┌──────────────────────────┐  │
│  │ 🔬 AutoDS                  │ │  │ Page Header               │  │
│  │ v0.1.0                     │ │  │ Domain Badge + Mode Label │  │
│  ├────────────────────────────┤ │  ├──────────────────────────┤  │
│  │ Analysis Mode              │ │  │                            │  │
│  │ ○ Auto                     │ │  │  Page Content              │  │
│  │ ● Guided                   │ │  │  (varies by page)          │  │
│  │ ○ Expert                   │ │  │                            │  │
│  ├────────────────────────────┤ │  │  Two-column layout:        │  │
│  │ Pipeline Progress          │ │  │  Left: Controls/Questions  │  │
│  │ ████████░░░░ 4/7           │ │  │  Right: Charts/Results     │  │
│  │                            │ │  │                            │  │
│  │ ✅ Domain Detection        │ │  │  OR                        │  │
│  │ ✅ Data Profiling          │ │  │                            │  │
│  │ ✅ EDA                     │ │  │  Full-width layout:        │  │
│  │ ⏸️ Feature Engineering     │ │  │  Tables, large charts      │  │
│  │ ⬜ Modeling                │ │  │                            │  │
│  │ ⬜ Explainability          │ │  │                            │  │
│  │ ⬜ Report                  │ │  │                            │  │
│  ├────────────────────────────┤ │  ├──────────────────────────┤  │
│  │ Sessions                   │ │  │ Page Footer               │  │
│  │ [New Session]              │ │  │ [Previous] [Next Step]    │  │
│  └────────────────────────────┘ │  └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.3 Page-Specific Layouts

**01_upload — Data Upload Page:**

```
┌─────────────────────────────────────────────────────┐
│  📁 Upload Your Data                                 │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 📄 File      │  │ 🔌 Database   │  │ 🌐 API    │ │
│  │  Upload      │  │  Connect     │  │  Import   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 📋 Clipboard │  │ ☁️ Cloud     │  │ 📊 Sample │ │
│  │  Paste       │  │  Storage     │  │  Dataset  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ Loaded Sources                                │   │
│  │ ┌──────────────────────────────────────────┐ │   │
│  │ │ sales_data.csv  │ 50,000 rows │ 25 cols  │ │   │
│  │ │ [Preview] [Schema] [Remove]              │ │   │
│  │ └──────────────────────────────────────────┘ │   │
│  │ ┌──────────────────────────────────────────┐ │   │
│  │ │ customer_db    │ 12,000 rows │ 15 cols   │ │   │
│  │ │ [Preview] [Schema] [Remove]              │ │   │
│  │ └──────────────────────────────────────────┘ │   │
│  │                                               │   │
│  │ [Suggest Joins] ← AI suggests join keys      │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  [Next: Configure →]                                │
└─────────────────────────────────────────────────────┘
```

**03_eda_interactive — EDA Page:**

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Exploratory Data Analysis                  🏥 Healthcare │
│                                                              │
│  ┌──────────────────────┐  ┌────────────────────────────────┐│
│  │ Questions (Guided)    │  │ Results                         ││
│  │                       │  │                                 ││
│  │ What's your primary   │  │ ┌─────────────────────────────┐││
│  │ analysis goal?        │  │ │ Distribution of Age          │││
│  │ ● Understand drivers  │  │ │ [Plotly Histogram]           │││
│  │ ○ Relationships       │  │ │                              │││
│  │ ○ Data quality        │  │ └─────────────────────────────┘││
│  │ ○ Segments            │  │                                 ││
│  │                       │  │ ┌─────────────────────────────┐││
│  │ 💡 Recommended:       │  │ │ Correlation Heatmap          │││
│  │ Since you have a      │  │ │ [Plotly Heatmap]             │││
│  │ clear target...       │  │ │                              │││
│  │                       │  │ └─────────────────────────────┘││
│  │ Which stats tests?    │  │                                 ││
│  │ ☑ Chi-square          │  │ ┌─────────────────────────────┐││
│  │ ☑ T-test              │  │ │ Key Insights                 │││
│  │ ☐ ANOVA               │  │ │ • Age is right-skewed        │││
│  │ ☑ KS test             │  │ │ • 23% missing in lab_result  │││
│  │                       │  │ │ • Strong correlation:         │││
│  │ [Run Analysis]        │  │ │   creatinine ↔ readmission   │││
│  │                       │  │ └─────────────────────────────┘││
│  └──────────────────────┘  └────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Statistical Test Results                                  ││
│  │ ┌─────────────┬──────────┬─────────┬──────────────────┐  ││
│  │ │ Test         │ Stat     │ p-value │ Interpretation    │  ││
│  │ ├─────────────┼──────────┼─────────┼──────────────────┤  ││
│  │ │ Chi-square   │ 15.23    │ 0.001   │ Significant       │  ││
│  │ │ T-test (age) │ 3.45     │ 0.012   │ Groups differ     │  ││
│  │ │ KS test      │ 0.89     │ < 0.001 │ Not normal        │  ││
│  │ └─────────────┴──────────┴─────────┴──────────────────┘  ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  [← Previous] [Next: Feature Engineering →]                  │
└──────────────────────────────────────────────────────────────┘
```

**04_feature_engineering — Per-Column Control:**

```
┌──────────────────────────────────────────────────────────────┐
│  ⚙️ Feature Engineering                        🏥 Healthcare │
│                                                              │
│  Domain Recommendations:                                     │
│  💡 Healthcare: Charlson Comorbidity Index, ICD grouping,    │
│     age bucketing by clinical thresholds recommended          │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Per-Column Decisions                                      ││
│  │                                                           ││
│  │ Column      │ Type    │ Missing │ Imputation │ Encoding  ││
│  │ ────────────┼─────────┼─────────┼────────────┼────────── ││
│  │ age         │ numeric │ 2%      │ [median ▼] │ [none ▼]  ││
│  │ gender      │ binary  │ 0%      │ [N/A]      │ [binary▼] ││
│  │ diagnosis   │ categ.  │ 5%      │ [mode ▼]   │ [target▼] ││
│  │ icd_code    │ categ.  │ 1%      │ [mode ▼]   │ [charls▼] ││
│  │ lab_result  │ numeric │ 23%     │ [KNN ▼]    │ [none ▼]  ││
│  │ admit_date  │ date    │ 0%      │ [N/A]      │ [parts▼]  ││
│  │                                                           ││
│  │ [Apply Domain Defaults] [Reset All] [Apply]              ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────┐  ┌────────────────────────────────┐│
│  │ Feature Importance    │  │ Created Features                ││
│  │ (preliminary)         │  │                                 ││
│  │ [Bar Chart]           │  │ • charlson_index (domain)       ││
│  │                       │  │ • age_bucket (clinical)         ││
│  │                       │  │ • days_since_admit              ││
│  │                       │  │ • lab_result_imputed            ││
│  └──────────────────────┘  └────────────────────────────────┘│
│                                                              │
│  [← Previous] [Next: Modeling →]                             │
└──────────────────────────────────────────────────────────────┘
```

### 8.4 Component Design Specifications

**Metric Card:**
```
┌───────────────────────┐
│  📊 AUC-ROC           │
│                       │
│  0.873                │
│  ▲ +0.05 vs baseline  │
│                       │
│  ━━━━━━━━━━░░░░░ 87%  │
└───────────────────────┘
```
- Title with icon (top)
- Large metric value (center, bold)
- Delta comparison (below value, color-coded)
- Optional progress bar (bottom)

**Chart Container:**
```
┌─────────────────────────────────────┐
│  Distribution of Age    [📷] [⛶]   │
│  ─────────────────────────────────  │
│                                     │
│  [Plotly Interactive Chart]         │
│                                     │
│  ─────────────────────────────────  │
│  📝 Age shows right skew with      │
│  outliers above 90. Median: 55.    │
└─────────────────────────────────────┘
```
- Title + export buttons (📷 PNG, ⛶ fullscreen)
- Interactive Plotly chart (middle)
- AI-generated caption (bottom, italic)

**Approval Widget:**
```
┌─────────────────────────────────────┐
│  ✅ Review & Approve                 │
│                                     │
│  The system recommends:             │
│  • 5 features created               │
│  • 2 dropped (low importance)       │
│  • Charlson index added (domain)    │
│                                     │
│  [✓ Approve & Continue]  [✎ Modify] │
└─────────────────────────────────────┘
```

### 8.5 Responsive Behavior

| Breakpoint | Layout Adaptation |
|---|---|
| Desktop (>1024px) | Sidebar visible, two-column main content |
| Tablet (768-1024px) | Sidebar collapsed by default, single column with tabs |
| Mobile (<768px) | Sidebar hidden, stacked layout, simplified charts |

Note: Streamlit handles most responsive behavior. Custom CSS for card grids and chart sizing.

### 8.6 Accessibility Requirements

| Feature | Implementation |
|---|---|
| Color contrast | WCAG AA (4.5:1 for text, 3:1 for large text) |
| Screen readers | Streamlit native ARIA support + custom labels |
| Keyboard navigation | Tab order through questions, Enter to submit |
| Reduced motion | Respect `prefers-reduced-motion` for chart animations |
| Alt text | All charts have text description fallback |
| Focus indicators | Visible focus ring on all interactive elements |

---

## 9. Security Architecture

### 9.1 Threat Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Trust Boundaries                           │
│                                                             │
│  ┌─────────────────────────┐    ┌─────────────────────────┐│
│  │ TRUSTED (Local)          │    │ UNTRUSTED (External)     ││
│  │                          │    │                          ││
│  │ • Application code       │    │ • User uploads           ││
│  │ • DuckDB                 │    │ • Database connections   ││
│  │ • MLflow                 │    │ • API responses          ││
│  │ • Report templates       │    │ • Claude API responses   ││
│  │                          │    │ • Web scraping results   ││
│  └─────────────────────────┘    └─────────────────────────┘│
│                                                             │
│  Boundary Controls:                                         │
│  • Input sanitizer at every connector                       │
│  • No eval/exec on user data                               │
│  • Schema validation on predictions                         │
│  • Max file size enforcement                                │
│  • Path traversal prevention                                │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Data Flow Security

| Stage | Security Control |
|---|---|
| Upload | Max file size, extension whitelist, encoding validation |
| Parsing | No code execution, sandboxed parsing, type validation |
| Storage | Local-only DuckDB, no cloud sync, session isolation |
| LLM calls | Only metadata sent (column names, stats), never raw data |
| Reports | Jinja2 autoescaping, no user-injectable templates |
| API | Input validation via Pydantic, rate limiting |

---

## 10. Deployment Architecture

### 10.1 Local Development

```
Developer Machine
├── Python 3.11+ venv
├── make setup (one-time)
├── make run → Streamlit :8501
├── make serve → FastAPI :8000
└── Environment: .env (ANTHROPIC_API_KEY)
```

### 10.2 Docker Compose

```
┌──────────────────────────────────────────┐
│  docker-compose.yml                       │
│                                          │
│  ┌─────────────────────┐                 │
│  │ dashboard            │                 │
│  │ Dockerfile.dashboard │                 │
│  │ Port: 8501           │                 │
│  │ Volumes:             │                 │
│  │   ./data:/app/data   │                 │
│  │   ./outputs:/app/out │                 │
│  │ Env: ANTHROPIC_KEY   │                 │
│  └─────────────────────┘                 │
│                                          │
│  (Single container — all-in-one)         │
│  (DuckDB, SQLite, MLflow embedded)       │
└──────────────────────────────────────────┘
```

### 10.3 Cloud Options

```
Option A: Streamlit Cloud
├── streamlit_app.py → dashboard/app.py
├── requirements.txt
├── .streamlit/secrets.toml (API key)
└── Free tier available

Option B: HuggingFace Spaces
├── Streamlit Space type
├── requirements.txt
├── .env via Space secrets
└── Free GPU available

Option C: Any Docker Host
├── docker-compose up
├── AWS ECS / GCP Cloud Run / Azure Container
└── Persistent volumes for data/outputs
```

---

## 11. Observability Architecture

### 11.1 Logging Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    Observability Layer                         │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Structured      │  │ Decision      │  │ Performance      │ │
│  │ Logger          │  │ Log           │  │ Log              │ │
│  │                 │  │               │  │                  │ │
│  │ JSON format     │  │ Every agent   │  │ Step timing      │ │
│  │ Per-module      │  │ decision with │  │ API call counts  │ │
│  │ levels          │  │ reasoning     │  │ Token usage      │ │
│  └────────┬───────┘  └──────┬───────┘  └────────┬─────────┘ │
│           │                  │                    │           │
│           └──────────────────┼────────────────────┘           │
│                              │                                │
│                    ┌─────────▼──────────┐                    │
│                    │   logs/ directory   │                    │
│                    │   (JSON files)      │                    │
│                    └────────────────────┘                    │
│                                                              │
│  ┌────────────────┐  ┌──────────────────────────────────────┐│
│  │ Cost Tracker    │  │ Audit Trail Export                    ││
│  │                 │  │                                      ││
│  │ Input tokens    │  │ Compliance-ready export for          ││
│  │ Output tokens   │  │ healthcare (HIPAA) and               ││
│  │ USD estimate    │  │ finance (model risk mgmt)            ││
│  │ Per-call + total│  │                                      ││
│  └────────────────┘  └──────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Dashboard Widgets                                         ││
│  │                                                           ││
│  │ workflow_progress: Step-by-step with timing + summaries   ││
│  │ metric_cards: Live KPIs during pipeline execution         ││
│  │ cost_display: Running API cost estimate in sidebar        ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 11.2 Key Metrics

| Metric | Source | Display |
|---|---|---|
| Pipeline step progress | `state.completed_steps` | Sidebar progress bar |
| Step duration | `state.pipeline_log` | Per-step timing in progress widget |
| API call count | `state.api_call_count` | Sidebar stat |
| Token usage | `state.api_token_count` | Sidebar stat |
| Estimated cost | cost_tracker calculation | Sidebar stat |
| Model performance | `state.model_results` | Metric cards on modeling page |
| Data quality score | `state.data_profile` | Metric card on profiling page |
| Error count | `state.errors` | Badge in progress widget |

---

## Appendix A: Technology Decision Records

### A1: Why LangGraph over LangChain Agents?

- **StateGraph** gives explicit control over routing logic vs. LLM-decided routing
- **Interrupts** enable clean human-in-the-loop without workarounds
- **Checkpointing** provides crash recovery out of the box
- **Conditional edges** match the domain × mode × data routing matrix exactly

### A2: Why DuckDB over pandas?

- Handles datasets larger than RAM (out-of-core processing)
- SQL interface cleaner for data transformations
- Columnar storage faster for analytical queries
- Native Parquet/CSV/JSON readers
- Embedded — no server to manage

### A3: Why Streamlit over React/Next.js?

- Python-native — same language as entire backend
- Interactive widgets match question-answer UI pattern perfectly
- Built-in session state management
- Rapid prototyping — ship faster
- Free cloud deployment (Streamlit Cloud)
- Trade-off: less UI customization than React, but sufficient for data science dashboard

### A4: Why Claude over GPT-4?

- Superior structured JSON output reliability
- Better at following complex system prompts
- Consistent reasoning for domain-specific decisions
- langchain-anthropic integration well-maintained
- Temperature 0 produces more deterministic results

### A5: Why MLflow over Weights & Biases?

- Open source, self-hosted, no account needed
- Embedded mode — no server required
- Mature model registry and artifact storage
- Standard in enterprise ML teams
- Trade-off: less polished UI than W&B, but fully local
