# System Design Document
# AutoDS — Autonomous Data Science Platform

**Version:** 1.0
**Date:** 2026-04-22
**Status:** Active Development

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Streamlit   │  │  FastAPI      │  │  Report Downloads         │  │
│  │  Dashboard   │  │  Prediction   │  │  (HTML/PDF/Notebook/ZIP)  │  │
│  │  (9 pages)   │  │  Endpoint     │  │                           │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              LangGraph StateGraph (core/graph.py)             │   │
│  │                                                               │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │   │
│  │  │ Domain   │───▶│ Data     │───▶│ EDA      │───▶│Feature │ │   │
│  │  │ Detector │    │ Profiler │    │ Agent    │    │Engineer│ │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └────────┘ │   │
│  │                                                       │      │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────┴───┐ │   │
│  │  │ Follow-  │◀───│ Report   │◀───│ Explain  │◀───│Modeling│ │   │
│  │  │ Up Agent │    │ Agent    │    │ Agent    │    │ Agent  │ │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │ AutoDSState       │  │ Tool Registry  │  │ Domain Configs      │  │
│  │ (shared state)    │  │ (100+ tools)   │  │ (7 domains)         │  │
│  └──────────────────┘  └───────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                    │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐    │
│  │  DuckDB   │  │  SQLite   │  │ ChromaDB  │  │  MLflow         │    │
│  │  (data    │  │  (state   │  │ (vector   │  │  (experiment    │    │
│  │  warehouse│  │  checkpts)│  │  memory)  │  │   tracking)     │    │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────────┘    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   DATA CONNECTORS (30+)                       │   │
│  │  Files │ Databases │ APIs │ Cloud Storage │ Direct Input      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Claude API    │  │ Data Sources  │  │ Cloud Storage            │  │
│  │ (Anthropic)   │  │ (DBs, APIs)   │  │ (S3, GCS, Azure)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **LLM decides, Python executes** — Claude chooses WHAT analyses to run. Registered Python functions DO the computation deterministically.
2. **Domain-aware everything** — Domain config drives metrics, questions, features, report language, compliance checks, and fairness requirements.
3. **Tool registry as memory** — Every statistical test, chart type, feature technique, and ML algorithm is registered with metadata. System never "forgets" a technique.
4. **Graceful degradation** — If Claude API fails, template-based fallbacks continue pipeline. If one analysis fails, others still run.
5. **Reproducibility** — Random seed, data hash, and full state export guarantee identical results on re-run.

---

## 2. Component Design

### 2.1 Agent Architecture

Each agent follows an identical contract:

```
Input:  AutoDSState (TypedDict)
Output: AutoDSState (updated)
```

**Agent responsibilities:**

| Agent | Reads From State | Writes To State |
|---|---|---|
| **Domain Detector** | `columns`, `sample_values` | `detected_domain`, `domain_config`, `domain_confidence` |
| **Data Profiler** | `joined_data_ref`, `domain_config` | `data_profile`, `schema_info`, `cleaning_actions` |
| **EDA Agent** | `data_profile`, `user_mode`, `domain_config` | `eda_results`, `eda_summary`, `eda_questions_asked` |
| **Feature Engineer** | `eda_results`, `schema_info`, `domain_config` | `fe_choices`, `feature_list`, `feature_importance` |
| **Modeling Agent** | `feature_list`, `target_column`, `domain_config` | `trained_models`, `model_results`, `best_model` |
| **Explainability Agent** | `best_model`, `model_results` | `shap_values`, `fairness_report`, `model_card` |
| **Report Agent** | All above | `report_paths` |
| **Follow-Up Agent** | All above + user query | Conversational response |

**Agent execution pattern:**

```
1. Read relevant state fields
2. IF Guided/Expert mode → generate domain-specific questions → interrupt for user
3. Select appropriate tools from Tool Registry
4. Execute tools (Python functions, not LLM)
5. Use LLM to interpret results + write summaries
6. Update state with results
7. Log decision to audit trail
8. Return updated state
```

### 2.2 State Machine (LangGraph)

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   domain     │
                    │   detection  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   data       │
                    │   profiling  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │ (Guided/Expert)         │ (Auto)
              ▼                         │
       ┌──────────────┐                │
       │ eda_questions │                │
       │ (interrupt)   │                │
       └──────┬───────┘                │
              │                         │
              ▼                         ▼
       ┌──────────────┐         ┌──────────────┐
       │ eda_execute   │◀────────│ eda_execute   │
       └──────┬───────┘         └──────────────┘
              │
              │ (if target exists)
              ├──────────────────────────┐
              │                          │ (no target → EDA only)
              ▼                          ▼
       ┌──────────────┐          ┌──────────────┐
       │ fe_questions  │          │   report      │
       │ (interrupt)   │          └──────┬───────┘
       └──────┬───────┘                 │
              ▼                          ▼
       ┌──────────────┐          ┌──────────────┐
       │ fe_execute    │          │    END        │
       └──────┬───────┘          └──────────────┘
              │
       ┌──────▼───────┐
       │model_questions│
       │ (interrupt)   │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │ model_execute │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │  explain      │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │   report      │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │    END        │
       └──────────────┘
```

**Interrupt mechanism:** LangGraph `interrupt_before` pauses the graph before `eda_execute`, `fe_execute`, and `model_execute`. The Streamlit dashboard renders questions, collects user responses, updates state, and resumes the graph.

**State checkpointing:** `SqliteSaver` checkpoints state after every node. If the process crashes, the graph resumes from the last completed node.

### 2.3 Tool Registry

Central catalog of all computational capabilities. Ensures the LLM can discover and route to any registered technique.

```
TOOL_REGISTRY
├── statistical_tests (20+)
│   ├── t_test_independent
│   ├── chi_square_independence
│   ├── anova_one_way
│   ├── mann_whitney_u
│   ├── ks_test
│   ├── shapiro_wilk
│   └── ... (correlation, regression diagnostics, survival)
├── visualizations (25+)
│   ├── histogram, box_plot, scatter, heatmap
│   ├── violin, strip, sunburst, treemap
│   ├── time_series_line, funnel, waterfall
│   └── ... (domain-specific: KM curve, SPC chart)
├── feature_engineering (50+)
│   ├── one_hot_encode, target_encode, ordinal_encode
│   ├── standard_scale, min_max_scale, log_transform
│   ├── polynomial_features, interaction_terms
│   ├── date_parts, lag_features, rolling_stats
│   └── ... (domain: charlson_index, rfm_features, oee_calc)
└── models (20+)
    ├── logistic_regression, random_forest, gradient_boosting
    ├── xgboost, lightgbm, catboost
    ├── svm, knn, naive_bayes
    ├── kmeans, dbscan (clustering)
    ├── flaml_auto (AutoML)
    └── ... (survival: cox_ph, kaplan_meier)
```

Each entry contains: `name`, `function` (importable path), `description`, `when_to_use`, `requirements`, `domains`, `parameters`, `output` schema.

### 2.4 Domain Detection Engine

**Detection algorithm:**

```
1. Normalize column names → lowercase, strip spaces/underscores
2. For each domain config:
   a. Count strong keyword matches (weighted 3x)
   b. Count moderate keyword matches (weighted 1x)
   c. Count weak keyword matches (weighted 0.3x)
   d. Calculate weighted score
3. Domain with highest score above threshold wins
4. If no domain exceeds threshold → "generic"
5. Return (domain_name, confidence_score, config_dict)
```

**Domain config structure:**

| Field | Purpose |
|---|---|
| `detection_keywords` | Strong/moderate/weak keyword lists for detection |
| `primary_metrics` | Domain-specific evaluation metrics by problem type |
| `eda_questions` | Domain-specific interactive questions for EDA step |
| `feature_questions` | Domain-specific questions for feature engineering |
| `model_questions` | Domain-specific questions for model selection |
| `default_cost_matrix` | Domain-appropriate false positive/negative costs |
| `fairness` | Whether fairness audit is required + protected attributes |
| `compliance_notes` | Regulatory considerations (HIPAA, fair lending, etc.) |
| `report_style` | Report template and terminology map |
| `special_encodings` | Domain-specific encoding functions (ICD codes, etc.) |

---

## 3. Data Flow

### 3.1 Data Ingestion Pipeline

```
User Input
    │
    ▼
┌───────────────────┐
│ Connector Factory  │ ← Detects source type, returns correct connector
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Universal Loader   │ ← Auto-detect format, encoding, delimiter, header
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Input Sanitizer    │ ← Handle encoding issues, mixed types, parse dates
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ DuckDB Warehouse   │ ← Load into DuckDB table for efficient querying
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Edge Case Detector │ ← Check for: single-class target, leakage,
│                    │   too few rows, constant columns, mixed types,
│                    │   extreme imbalance, perfect multicollinearity
└───────────────────┘
```

### 3.2 Multi-Source Join Flow

```
Source A (CSV)  ──┐
                  ├──▶ Schema Matcher ──▶ AI-suggested join keys
Source B (DB)   ──┘          │
                             ▼
                     User confirms/modifies
                             │
                             ▼
                     DuckDB JOIN execution
                             │
                             ▼
                     Row explosion check
                     (validate join didn't create
                      invalid Cartesian product)
```

### 3.3 Model Training Flow

```
Feature Matrix (X) + Target (y)
    │
    ├──▶ Train/Test Split (stratified, time-aware if temporal)
    │
    ├──▶ Cross-Validation (K-Fold or TimeSeriesSplit)
    │
    ├──▶ For each selected algorithm:
    │    ├── Train on fold
    │    ├── Predict on holdout
    │    ├── Calculate domain-specific metrics
    │    └── Log to MLflow (params, metrics, artifacts)
    │
    ├──▶ Statistical Model Comparison
    │    ├── Paired t-test on CV folds
    │    ├── Bootstrap confidence intervals
    │    └── McNemar's test (classification)
    │
    ├──▶ Select best model
    │
    └──▶ Retrain on full training set
         └── Save model artifact + metadata
```

---

## 4. Data Storage

### 4.1 Storage Architecture

| Store | Technology | Purpose | Persistence |
|---|---|---|---|
| Data Warehouse | DuckDB (embedded) | All tabular data operations, joins, queries | Session-scoped |
| State Checkpoint | SQLite | LangGraph state persistence, crash recovery | Session-scoped |
| Vector Memory | ChromaDB (embedded) | Semantic search for follow-up questions | Session-scoped |
| Experiment Tracking | MLflow (local) | Model params, metrics, artifacts | Persistent |
| Session Store | SQLite | Session metadata, comparison data | Persistent |
| Audit Trail | JSON files | Structured decision logs | Persistent |
| Reports | HTML/PDF/IPYNB files | Generated report outputs | Persistent |

### 4.2 AutoDSState Schema

The shared state TypedDict is the single source of truth. Key sections:

- **Session metadata:** `session_id`, `user_mode`, `random_seed`, `data_hash`
- **Data references:** `data_sources`, `joined_data_ref`, `data_profile`, `schema_info`
- **Domain context:** `detected_domain`, `domain_config`, `domain_confirmed`
- **User intent:** `user_goal`, `target_column`, `problem_type`
- **Step results:** `eda_results`, `fe_choices`, `model_results`, `shap_values`
- **Questions/responses:** `eda_questions_asked`, `fe_questions_asked`, `model_questions_asked`
- **Pipeline tracking:** `current_step`, `completed_steps`, `errors`, `pipeline_log`
- **Cost tracking:** `api_call_count`, `api_token_count`

---

## 5. Human-in-the-Loop Design

### 5.1 Question Types

| Type | Widget | Use Case |
|---|---|---|
| `single_select` | Radio buttons | Choose one analysis goal |
| `multi_select` | Checkboxes | Select multiple chart types |
| `slider` | Slider | Set correlation threshold |
| `per_column_table` | Table with dropdowns | Set imputation strategy per column |
| `text_input` | Text field | Custom analysis description |
| `number_input` | Number field | Set significance level |

### 5.2 Question Flow

```
Agent generates questions
    │
    ▼
LangGraph interrupt ──▶ State saved to checkpoint
    │
    ▼
Streamlit renders questions using question_renderer component
    │
    ▼
User answers in dashboard
    │
    ▼
Answers written to state (eda_questions_asked, etc.)
    │
    ▼
LangGraph resumes from checkpoint with updated state
    │
    ▼
Agent reads answers and proceeds
```

### 5.3 Mode Behavior

| Behavior | Auto | Guided | Expert |
|---|---|---|---|
| Questions shown | None | System-recommended with defaults | All available |
| Decisions | LLM decides everything | LLM recommends, user chooses | User specifies everything |
| Speed | Fastest | Medium | Slowest |
| Control | None | Moderate | Full |
| API calls | Fewer (no question generation) | More (question + answer processing) | Most (detailed parameter handling) |

---

## 6. Error Handling Strategy

### 6.1 Error Hierarchy

```
BaseAutoDS Exception
├── DataIngestionError
│   ├── UnsupportedFormatError
│   ├── ConnectionError
│   └── EncodingError
├── DataQualityError
│   ├── DataLeakageDetected
│   ├── InsufficientDataError
│   ├── SingleClassTargetError
│   └── ConstantColumnError
├── AgentError
│   ├── LLMAPIError
│   ├── ToolNotFoundError
│   └── ToolExecutionError
├── ModelingError
│   ├── TrainingFailedError
│   ├── ConvergenceError
│   └── InsufficientFeaturesError
└── ReportError
    ├── TemplateNotFoundError
    └── PDFGenerationError
```

### 6.2 Recovery Strategy

| Error Type | Strategy |
|---|---|
| LLM API failure | Template-based fallback (rule-based summaries, default parameters) |
| Single analysis fails | Skip that analysis, continue with others, log warning |
| Data leakage detected | Remove leaking feature, warn user, continue |
| Model training fails | Try simpler model (e.g., logistic regression), log failure |
| Report generation fails | Fall back to text-only output |
| Database connection fails | Retry 3x with backoff, then fail with clear message |

### 6.3 Audit Trail

Every agent decision is logged:

```json
{
  "timestamp": "2026-04-22T15:30:00Z",
  "session_id": "abc-123",
  "step": "eda",
  "agent": "eda_agent",
  "action": "selected_analysis",
  "tool": "chi_square_independence",
  "params": {"col_a": "gender", "col_b": "outcome"},
  "reasoning": "Binary categorical vs binary target — chi-square appropriate",
  "duration_seconds": 0.45,
  "status": "success",
  "llm_tokens_used": 1250
}
```

---

## 7. Security Design

### 7.1 Data Security

- **Local-first:** All data processing happens locally. No raw data sent to external services.
- **LLM prompts:** Only column names, data types, summary statistics, and analysis results sent to Claude. Never raw row-level data.
- **File upload scanning:** Input sanitizer checks for encoding attacks, path traversal, and oversized files.
- **No eval/exec:** Never execute user-provided code strings. Tool registry uses importable function paths only.

### 7.2 Domain-Specific Compliance

| Domain | Compliance Considerations |
|---|---|
| Healthcare | HIPAA column flagging, PHI detection warnings, clinical explainability |
| Finance | Fair lending compliance, adverse action code generation, model risk management |
| HR | Salary/demographic data sensitivity, anonymization recommendations |

### 7.3 API Key Management

- Anthropic API key via environment variable (`ANTHROPIC_API_KEY`)
- `.env.example` template provided, `.env` gitignored
- Startup validation checks for required API keys

---

## 8. Scalability Considerations

### 8.1 Data Scale

| Strategy | Implementation |
|---|---|
| Large files | DuckDB handles out-of-core processing for datasets exceeding RAM |
| Profiling | Sampling-based profiling for datasets > 100K rows |
| Feature engineering | DuckDB SQL-based transforms instead of pandas for large data |
| Model training | FLAML's time-budgeted training prevents runaway compute |

### 8.2 LLM Cost Optimization

| Strategy | Implementation |
|---|---|
| Batch decisions | One Claude call for all column strategies, not one per column |
| Response caching | Cache LLM responses for similar data patterns |
| Structured output | Always request JSON, never free-form text needing parsing |
| Temperature 0 | Deterministic responses for reproducibility |
| Token tracking | Log input/output tokens per call, display estimated cost |

---

## 9. Deployment Architecture

### 9.1 Local Development

```
make setup  →  pip install + DuckDB init + sample data download
make run    →  streamlit run dashboard/app.py --server.port 8501
make serve  →  uvicorn serving.api:app --port 8000
```

### 9.2 Docker Deployment

```yaml
# docker-compose.yml
services:
  dashboard:
    build:
      dockerfile: Dockerfile.dashboard
    ports:
      - "8501:8501"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
```

### 9.3 Cloud Deployment Options

| Platform | Configuration |
|---|---|
| Streamlit Cloud | `streamlit_app.py` pointing to `dashboard/app.py` |
| HuggingFace Spaces | Streamlit Space with `requirements.txt` |
| Docker (any cloud) | `docker-compose.yml` with volume mounts |

---

## 10. Monitoring & Observability

| Aspect | Tool | Output |
|---|---|---|
| Structured logging | Python `logging` → JSON | `logs/*.json` |
| Decision audit trail | Custom `decision_log.py` | Per-session audit file |
| Performance timing | Custom `performance_log.py` | Step-level timing data |
| API cost tracking | Custom `cost_tracker.py` | Token usage + estimated USD |
| Experiment tracking | MLflow | Model params, metrics, artifacts at `mlruns/` |
| Pipeline progress | Streamlit `workflow_progress` component | Real-time step indicator |
