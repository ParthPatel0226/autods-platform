# AutoDS Platform — API Signatures Reference

> Auto-generated from source. All 55 modules across the platform.
> State keys reference `AutoDSState` in `core/state.py`.

---

## Table of Contents

1. [core/](#core)
2. [agents/](#agents)
3. [configs/](#configs)
4. [domains/](#domains)
5. [session/](#session)
6. [serving/](#serving)
7. [data_connectors/](#data_connectors)
8. [validation/](#validation)
9. [evaluation/](#evaluation)
10. [explainability/](#explainability)
11. [reports/generators/](#reportsgenerators)
12. [logging_audit/](#logging_audit)

---

## core/

### `core/state.py`

#### `AutoDSState` (TypedDict)
Full shared state passed through every LangGraph node (~80+ fields across 14 categories):

| Category | Key fields |
|----------|-----------|
| Identity | `session_id`, `user_mode`, `random_seed` |
| Data | `data_sources`, `joined_data_ref`, `row_count`, `col_count`, `data_hash` |
| Schema | `schema_info`, `column_info`, `target_column`, `problem_type` |
| Profiling | `data_profile`, `quality_issues` |
| EDA | `eda_questions`, `eda_answers`, `eda_summary`, `eda_insights`, `eda_charts` |
| Features | `fe_questions`, `fe_answers`, `feature_list`, `features_selected`, `encoders`, `scalers` |
| Modeling | `model_choices`, `trained_models`, `model_results`, `best_model`, `best_model_name`, `best_model_path` |
| Explainability | `shap_values`, `fairness_report`, `model_card`, `explainability_results` |
| Orchestration | `current_step`, `completed_steps`, `pipeline_steps`, `errors`, `warnings` |
| Reports | `report_paths`, `notebook_path`, `zip_path` |
| Logging | `cost_log`, `performance_log`, `decision_log` |
| Config | `domain_config`, `detected_domain`, `agent_prompts` |
| Session | `estimated_cost`, `pipeline_duration` |
| Follow-up | `followup_history`, `last_question`, `last_answer` |

---

#### Supporting TypedDicts

```python
class DataSourceInfo(TypedDict):
    name: str
    path: str
    connector_type: str
    row_count: int
    col_count: int
    columns: list[str]
    loaded_at: str

class ColumnInfo(TypedDict):
    name: str
    dtype: str
    n_unique: int
    missing_ratio: float
    sample_values: list[Any]

class QuestionResponse(TypedDict):
    question: str
    answer: str
    agent: str
    timestamp: str

class ModelResult(TypedDict):
    metrics: dict[str, float]
    feature_importance: dict[str, float]
    model_path: str
    training_time: float
```

---

#### `create_initial_state`

```python
def create_initial_state(
    session_id: str,
    user_mode: str = "auto",
) -> AutoDSState
```

Creates a blank `AutoDSState` with sensible defaults.
**State written:** all fields initialised to `None` / `[]` / `{}`.

---

### `core/graph.py`

#### `build_workflow`

```python
def build_workflow(
    checkpoint_path: str | None = None,
    user_mode: str = "auto",
) -> CompiledGraph
```

Builds the full LangGraph `StateGraph` with all agent nodes and edges.
`user_mode="guided"` or `"expert"` adds `interrupt_before` checkpoints.
**State read:** `user_mode`. **State written:** none (returns graph object).

---

#### `build_auto_workflow`

```python
def build_auto_workflow(
    checkpoint_path: str | None = None,
) -> CompiledGraph
```

Convenience wrapper; calls `build_workflow(user_mode="auto")`.

---

### `core/exceptions.py`

Exception hierarchy rooted at `AutoDSError(Exception)`:

```
AutoDSError
├── DataError
│   ├── DataLoadError
│   ├── DataValidationError
│   └── UnsupportedFileTypeError
├── AgentError
│   ├── OrchestratorError
│   ├── ProfilingError
│   ├── EDAError
│   ├── FeatureEngineeringError
│   ├── ModelingError
│   └── ExplainabilityError
├── ModelError
│   ├── ModelTrainingError
│   ├── ModelLoadError
│   └── ModelPredictionError
├── ConfigError
│   ├── MissingConfigError
│   └── InvalidConfigError
├── SessionError
│   ├── SessionNotFoundError
│   └── SessionCorruptedError
├── ReportError
│   └── ReportGenerationError
├── LLMError
│   ├── LLMConnectionError
│   └── LLMResponseParseError
└── EdgeCaseError(DataError)
      attrs: edge_case_type: str, suggestion: str
```

---

### `core/llm_config.py`

#### `get_llm`

```python
def get_llm(
    provider: str | None = None,
    temperature: float = 0.1,
) -> BaseChatModel
```

Returns a LangChain chat model instance for the active provider (OpenAI / Anthropic / Azure / local).

---

#### `invoke_llm`

```python
def invoke_llm(
    prompt: str,
    system_prompt: str | None = None,
    state: AutoDSState | None = None,
    use_cache: bool = True,
    json_output: bool = False,
) -> str
```

Calls the LLM, logs cost to `state["cost_log"]` if state provided.
**State read:** `session_id`, `detected_domain`. **State written:** `cost_log` (appended).

---

#### `invoke_llm_json`

```python
def invoke_llm_json(
    prompt: str,
    system_prompt: str | None = None,
    state: AutoDSState | None = None,
) -> dict
```

Wraps `invoke_llm(json_output=True)` and parses the response.

---

#### `get_agent_system_prompt`

```python
def get_agent_system_prompt(
    agent_name: str,
    domain_config: dict | None = None,
) -> str
```

Loads the agent's system prompt from YAML config; optionally injects domain terminology.

---

#### `set_runtime_provider`

```python
def set_runtime_provider(provider: str) -> None
```

Hot-swaps the active LLM provider at runtime.

---

### `core/memory.py`

#### `class SessionStore`

SQLite-backed K/V store (`~/.autods/memory.db`).

```python
class SessionStore:
    def __init__(self, db_path: str | None = None) -> None
    def set(self, session_id: str, key: str, value: Any) -> None
    def get(self, session_id: str, key: str, default: Any = None) -> Any
    def delete(self, session_id: str, key: str | None = None) -> None
    def list_keys(self, session_id: str) -> list[str]
```

---

#### `class VectorMemory`

ChromaDB collection `autods_memory` for semantic recall.

```python
class VectorMemory:
    def __init__(self, persist_dir: str | None = None) -> None
    def add(self, text: str, metadata: dict | None = None) -> str
    def search(self, query: str, n_results: int = 5) -> list[dict]
    def clear(self) -> None
```

---

## agents/

### `agents/orchestrator.py`

#### `orchestrator_agent`

```python
def orchestrator_agent(state: AutoDSState) -> AutoDSState
```

Entry node. Detects domain, sets pipeline steps, resolves target column, seeds RNG.
**State read:** `data_sources`, `schema_info`, `user_mode`.
**State written:** `detected_domain`, `domain_config`, `pipeline_steps`, `target_column`, `problem_type`, `random_seed`, `current_step`.

---

#### `_resolve_target_column`

```python
def _resolve_target_column(state: AutoDSState) -> str | None
```

Heuristically picks the target column from schema info and domain config.

---

#### `_set_pipeline_steps`

```python
def _set_pipeline_steps(state: AutoDSState) -> list[str]
```

Returns the ordered list of pipeline steps based on `user_mode` and available data.

---

#### `_set_evaluation_metrics`

```python
def _set_evaluation_metrics(
    problem_type: str,
    domain: str,
) -> list[str]
```

Returns the primary evaluation metric names for the given problem type and domain.

---

### `agents/data_profiler.py`

#### `run_data_profiling`

```python
def run_data_profiling(state: AutoDSState) -> AutoDSState
```

Computes per-column statistics, dtype summary, missing-value counts, and a sample.
**State read:** `joined_data_ref`, `data_sources`.
**State written:** `data_profile`, `schema_info`, `column_info`, `completed_steps`, `current_step`.

---

### `agents/eda_agent.py`

#### `generate_eda_questions`

```python
def generate_eda_questions(state: AutoDSState) -> AutoDSState
```

LLM generates domain-appropriate EDA questions.
**State read:** `schema_info`, `domain_config`, `target_column`.
**State written:** `eda_questions`, `current_step`.

---

#### `execute_eda`

```python
def execute_eda(state: AutoDSState) -> AutoDSState
```

Executes each EDA question: runs DuckDB queries / pandas ops, generates Plotly charts.
**State read:** `joined_data_ref`, `eda_questions`, `target_column`, `domain_config`.
**State written:** `eda_answers`, `eda_summary`, `eda_insights`, `eda_charts`, `completed_steps`.

---

### `agents/feature_engineer.py`

#### `generate_fe_questions`

```python
def generate_fe_questions(state: AutoDSState) -> AutoDSState
```

LLM generates feature engineering questions.
**State read:** `schema_info`, `eda_summary`, `domain_config`.
**State written:** `fe_questions`.

---

#### `execute_feature_engineering`

```python
def execute_feature_engineering(state: AutoDSState) -> AutoDSState
```

Applies encoding, scaling, imputation, and feature creation based on LLM decisions.
**State read:** `joined_data_ref`, `fe_questions`, `schema_info`, `target_column`, `domain_config`.
**State written:** `feature_list`, `features_selected`, `encoders`, `scalers`, `completed_steps`.

---

### `agents/modeling_agent.py`

Algorithm selection constants (domain-aware):

```python
CLASSIFICATION_ALGORITHMS = ["random_forest", "gradient_boosting", "logistic_regression", "xgboost", "lightgbm"]
REGRESSION_ALGORITHMS     = ["random_forest_regressor", "gradient_boosting_regressor", "linear_regression", "xgboost_regressor", "lightgbm_regressor"]
```

#### `generate_model_questions`

```python
def generate_model_questions(state: AutoDSState) -> AutoDSState
```

LLM selects appropriate algorithms and hyperparameter search ranges.
**State read:** `problem_type`, `feature_list`, `domain_config`, `row_count`.
**State written:** `model_choices`.

---

#### `execute_modeling`

```python
def execute_modeling(state: AutoDSState) -> AutoDSState
```

Trains selected models, runs cross-validation, picks the best by primary metric.
**State read:** `joined_data_ref`, `feature_list`, `target_column`, `problem_type`, `model_choices`, `random_seed`.
**State written:** `trained_models`, `model_results`, `best_model`, `best_model_name`, `best_model_path`, `completed_steps`.

---

### `agents/explainability_agent.py`

#### `run_explainability`

```python
def run_explainability(state: AutoDSState) -> AutoDSState
```

Runs SHAP, fairness audit, and generates model card; delegates to `explainability/` modules.
**State read:** `best_model_path`, `joined_data_ref`, `feature_list`, `target_column`, `problem_type`, `domain_config`, `detected_domain`.
**State written:** `shap_values`, `fairness_report`, `model_card`, `explainability_results`, `completed_steps`.

---

### `agents/followup_agent.py`

#### `handle_followup`

```python
def handle_followup(
    state: AutoDSState,
    user_question: str,
) -> dict
```

Routes a user's natural-language question to the correct handler and returns `{"answer": str, "intent": str}`.
**State read:** `session_id`, plus intent-specific keys.
**State written:** `followup_history` (appended).

---

#### Intent handlers (internal)

```python
def _detect_intent(question: str) -> str
# Returns one of: "data_query" | "feature_importance" | "what_if" |
#                 "model_performance" | "fairness" | "add_data" |
#                 "retrain" | "general"

def _handle_data_query(state, question) -> str
def _handle_feature_importance(state, question) -> str
def _handle_what_if(state, question) -> str
def _handle_model_performance(state, question) -> str
def _handle_fairness(state, question) -> str
def _handle_add_data(state, question) -> str
def _handle_retrain(state, question) -> str
def _handle_general(state, question) -> str
```

---

### `agents/report_agent.py`

#### `generate_reports`

```python
def generate_reports(state: AutoDSState) -> AutoDSState
```

Orchestrates all report generators; populates `state["report_paths"]`.
**State read:** full state.
**State written:** `report_paths`, `notebook_path`, `zip_path`, `completed_steps`.

---

#### Internal builders

```python
def _build_html_report(state, output_dir) -> str
def _build_executive_summary(state, output_dir) -> str
def _build_notebook(state, output_dir) -> str
def _build_zip(file_paths, output_dir, session_id) -> str
```

---

### `agents/tools/tool_registry.py`

#### `TOOL_REGISTRY`

Dict of 74 tools across 4 categories:

| Category | Count | Examples |
|----------|-------|---------|
| `data_analysis` | ~20 | `describe_dataframe`, `correlation_matrix`, `value_counts` |
| `visualization` | ~15 | `histogram`, `scatter_plot`, `confusion_matrix_plot` |
| `ml_utilities` | ~20 | `train_test_split_tool`, `cross_validate`, `hyperparameter_search` |
| `domain_specific` | ~19 | `ks_statistic`, `clinical_metrics`, `rfm_scores` |

---

#### `get_tools_for_domain`

```python
def get_tools_for_domain(domain: str) -> dict[str, Callable]
```

Returns the base tool set plus domain-specific tools for the given domain.

---

#### `search_tools`

```python
def search_tools(query: str) -> list[str]
```

Fuzzy-searches tool names and descriptions; returns matching tool names.

---

#### `get_tool_function`

```python
def get_tool_function(tool_name: str) -> Callable | None
```

Looks up a callable by name from `TOOL_REGISTRY`.

---

## configs/

### `configs/loader.py`

#### `_load_yaml`

```python
def _load_yaml(filename: str) -> dict
```

Loads a YAML file from `configs/` relative to the package root. Internal helper.

---

#### `load_agent_prompts`

```python
@lru_cache(maxsize=1)
def load_agent_prompts() -> dict[str, Any]
```

Returns the full agent prompts YAML (`configs/agent_prompts.yaml`).

---

#### `load_domain_configs`

```python
@lru_cache(maxsize=1)
def load_domain_configs() -> dict[str, Any]
```

Returns all domain configs YAML (`configs/domain_configs.yaml`).

---

#### `get_agent_prompt`

```python
def get_agent_prompt(agent_name: str) -> str
```

Returns the system prompt string for `agent_name`; raises `MissingConfigError` if absent.

---

## domains/

### `domains/domain_registry.py`

#### `detect_domain`

```python
def detect_domain(
    column_names: list[str],
    sample_values: dict[str, list] | None = None,
) -> tuple[str, float, dict]
```

Keyword-scoring heuristic across 7 domains.
Returns `(domain_name, confidence_score, per_domain_scores)`.
Domain names: `"healthcare"`, `"finance"`, `"ecommerce"`, `"marketing"`, `"hr"`, `"manufacturing"`, `"generic"`.

---

#### `get_domain_config`

```python
def get_domain_config(domain_name: str) -> dict[str, Any]
```

Returns the config dict for the domain (terminology map, preferred algorithms, evaluation metrics, etc.).
Falls back to `"generic"` config if domain not found.

---

#### `list_available_domains`

```python
def list_available_domains() -> list[str]
```

Returns the list of registered domain names.

---

## session/

### `session/session_manager.py`

SQLite storage at `~/.autods/sessions/{session_id}.json`.

#### `save_session`

```python
def save_session(state: AutoDSState) -> None
```

Serialises state to JSON; overwrites existing file.

---

#### `load_session`

```python
def load_session(session_id: str) -> AutoDSState
```

Deserialises and returns state; raises `SessionNotFoundError` if missing.

---

#### `list_sessions`

```python
def list_sessions() -> list[dict[str, Any]]
```

Returns summary dicts `{"session_id", "created_at", "domain", "row_count"}` for all saved sessions.

---

#### `delete_session`

```python
def delete_session(session_id: str) -> None
```

Removes the session file; raises `SessionNotFoundError` if not found.

---

#### `session_exists`

```python
def session_exists(session_id: str) -> bool
```

Returns `True` if the session file exists.

---

### `session/session_compare.py`

#### `compare_sessions`

```python
def compare_sessions(
    session_a: AutoDSState,
    session_b: AutoDSState,
    label_a: str = "Session A",
    label_b: str = "Session B",
) -> dict[str, Any]
```

Side-by-side metric comparison for A/B testing runs.
Returns `{"label_a", "label_b", "metrics_a", "metrics_b", "delta", "winner"}`.

---

### `session/session_export.py`

#### `export_session`

```python
def export_session(
    state: AutoDSState,
    output_path: str,
    include_data_sample: bool = True,
    sample_rows: int = 100,
) -> str
```

Writes a portable ZIP bundle (`config.json` + optional data sample).
Returns the absolute path to the ZIP file.

---

#### `import_session_config`

```python
def import_session_config(export_path: str) -> dict[str, Any]
```

Reads `config.json` from an export ZIP; returns the config dict.

---

## serving/

### `serving/api.py`

FastAPI application mounted at `/serving`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/serving/health` | Returns `{"status": "ok", "model_loaded": bool}` |
| `GET` | `/serving/info` | Returns model metadata and feature list |
| `POST` | `/serving/predict` | Single-row prediction with optional SHAP explanation |
| `POST` | `/serving/predict/batch` | Batch prediction from JSON array |
| `POST` | `/serving/reload` | Hot-reloads the model from disk |

**Predict request schema:**
```json
{
  "features": {"col1": value, "col2": value, ...},
  "explain": false
}
```

**Predict response schema:**
```json
{
  "prediction": <value>,
  "probability": <float | null>,
  "explanation": {"feature": importance, ...} | null
}
```

---

### `serving/model_loader.py`

#### `load_model`

```python
def load_model(model_path: str) -> Any
```

Loads a joblib-serialised sklearn-compatible model.

---

#### `load_model_metadata`

```python
def load_model_metadata(model_path: str) -> dict[str, Any]
```

Reads accompanying `_metadata.json` file (feature names, problem type, training date).

---

#### `load_model_cached`

```python
@lru_cache(maxsize=4)
def load_model_cached(model_path: str) -> tuple[Any, dict]
```

Cached version returning `(model, metadata)`.

---

#### `get_feature_names`

```python
def get_feature_names(model_path: str) -> list[str]
```

Extracts feature names from model metadata or `model.feature_names_in_`.

---

#### `get_model_info`

```python
def get_model_info(model_path: str) -> dict[str, Any]
```

Returns a summary dict: name, type, feature count, training date, file size.

---

#### `try_load_mlflow`

```python
def try_load_mlflow(
    run_id: str,
    artifact_path: str = "model",
) -> Any | None
```

Attempts to load model from MLflow registry; returns `None` if MLflow unavailable.

---

#### `clear_cache`

```python
def clear_cache() -> None
```

Clears the `load_model_cached` LRU cache.

---

## data_connectors/

### `data_connectors/universal_loader.py`

#### `detect_encoding`

```python
def detect_encoding(file_path: str) -> str
```

Tries `charset_normalizer`, then `chardet`, falls back to `"utf-8"`.

---

#### `detect_delimiter`

```python
def detect_delimiter(
    file_path: str,
    encoding: str = "utf-8",
) -> str
```

Sniffs CSV delimiter from the first 4096 bytes; returns `","`, `"\t"`, `";"`, or `"|"`.

---

#### `compute_file_hash`

```python
def compute_file_hash(file_path: str) -> str
```

Returns SHA-256 hex digest of the file (for change detection).

---

#### `smart_load`

```python
def smart_load(
    file_path: str,
    config: dict | None = None,
    max_rows: int | None = None,
) -> pd.DataFrame
```

Detects file type by extension and delegates to the appropriate connector.
Supports: CSV, TSV, XLSX/XLS, Parquet, JSON/JSONL, Feather, ORC, HDF5, Pickle.

---

#### `load_to_duckdb`

```python
def load_to_duckdb(
    df: pd.DataFrame,
    table_name: str = "main_data",
    duckdb_path: str | None = None,
) -> duckdb.DuckDBPyConnection
```

Registers DataFrame as a DuckDB table; returns the connection.
Pass `duckdb_path=None` for in-memory DB.

---

### `data_connectors/connector_factory.py`

#### `class ConnectorFactory`

Registry of 40+ connector types.

```python
class ConnectorFactory:
    _CONNECTOR_REGISTRY: dict[str, type]   # 40+ entries

    @staticmethod
    def get_connector(connector_type: str) -> BaseConnector

    @staticmethod
    def get_connector_for_file(file_path: str) -> BaseConnector
    # Matches extension → connector

    @staticmethod
    def list_available_connectors() -> list[str]
```

Connector categories: local files (CSV/Excel/Parquet/JSON/HDF5/Feather/ORC), databases (SQLite/PostgreSQL/MySQL/MSSQL/BigQuery/Snowflake/Redshift), cloud (S3/GCS/Azure Blob/ADLS), APIs (REST/GraphQL/Salesforce/HubSpot/Stripe), streaming (Kafka/Kinesis/Pubsub).

---

### `data_connectors/multi_source_manager.py`

#### `class MultiSourceManager`

Manages multiple loaded DataFrames.

```python
class MultiSourceManager:
    def __init__(self) -> None
    def add_source(self, name: str, df: pd.DataFrame, metadata: dict | None = None) -> None
    def remove_source(self, name: str) -> None
    def list_sources(self) -> list[str]
    def get_dataframe(self, name: str) -> pd.DataFrame
    def get_schema(self, name: str) -> dict[str, str]
    def join(
        self,
        left: str,
        right: str,
        on: str | list[str],
        how: str = "inner",
    ) -> pd.DataFrame
```

---

### `data_connectors/schema_matcher.py`

#### `suggest_join_keys`

```python
def suggest_join_keys(
    left: pd.DataFrame,
    right: pd.DataFrame,
    name_threshold: float = 0.8,
    overlap_threshold: float = 0.5,
) -> list[dict[str, Any]]
```

Returns candidate join keys sorted by confidence score. Each entry: `{"left_col", "right_col", "name_similarity", "value_overlap", "score"}`.

---

#### `compare_schemas`

```python
def compare_schemas(
    left: pd.DataFrame,
    right: pd.DataFrame,
) -> dict[str, Any]
```

Returns `{"common_columns", "left_only", "right_only", "type_mismatches"}`.

---

## validation/

### `validation/input_sanitizer.py`

#### `sanitize_dataframe`

```python
def sanitize_dataframe(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]
```

Seven-step cleaning pipeline (see below). Returns `(cleaned_df, issues)`.

Steps:
1. Clean column names (lowercase, underscores, strip special chars)
2. Deduplicate column names (appends `_1`, `_2`, …)
3. Strip whitespace from string columns
4. Convert empty strings to `NaN`
5. Attempt numeric conversion for object columns (≥80% parse rate)
6. Fix mixed-type columns (cast to dominant type)
7. Parse date-like string columns (≥50% parse rate)

---

#### `detect_encoding`

```python
def detect_encoding(file_path: str) -> str
```

Same as `universal_loader.detect_encoding`; tries charset_normalizer → chardet → "utf-8".

---

#### `clean_column_names`

```python
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame
```

Lowercases, strips, replaces spaces/hyphens with underscores, removes non-alphanumeric.

---

#### `parse_dates`

```python
def parse_dates(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame
```

Attempts `pd.to_datetime` on specified columns (or all object columns); leaves failures unchanged.

---

#### `fix_mixed_types`

```python
def fix_mixed_types(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]
```

Casts each mixed-type object column to its dominant Python type. Returns `(fixed_df, fixed_col_names)`.

---

### `validation/edge_case_detector.py`

#### `detect_all_edge_cases`

```python
def detect_all_edge_cases(
    df: pd.DataFrame,
    target_column: str | None = None,
) -> list[dict[str, Any]]
```

Runs all checks; returns issues sorted by severity (critical → warning → info).

Issue schema: `{"type", "severity", "message", "suggestion", "affected_columns"}`.

---

#### Individual check functions

```python
def check_single_class_target(df, target) -> list[dict]
# severity: critical — target has ≤1 unique non-null value

def check_extreme_imbalance(df, target, threshold=0.01) -> list[dict]
# severity: warning — minority class < threshold fraction of rows

def check_target_leakage(df, target) -> list[dict]
# severity: critical — |correlation| > 0.95 with target

def check_constant_columns(df) -> list[dict]
# severity: warning — column has ≤1 unique non-null value

def check_high_cardinality(df, threshold=0.95) -> list[dict]
# severity: warning — categorical unique ratio > threshold

def check_too_few_rows(df, min_rows=30) -> list[dict]
# severity: critical (<10) or warning (<30)

def check_too_many_missing(df, threshold=0.5) -> list[dict]
# severity: warning — missing ratio > threshold per column

def check_perfect_correlation(df, threshold=0.99) -> list[dict]
# severity: warning — numeric pair |corr| ≥ threshold

def check_id_like_columns(df) -> list[dict]
# severity: info — name matches ID pattern, all unique, or sequential ints
```

---

### `validation/schema_validator.py`

#### `extract_training_schema`

```python
def extract_training_schema(df: pd.DataFrame) -> dict[str, Any]
```

Captures column names, dtypes, nullable flags, and value ranges for later validation.

---

#### `validate_prediction_schema`

```python
def validate_prediction_schema(
    prediction_df: pd.DataFrame,
    training_schema: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]
```

Returns `(is_valid, issues)` where issues describe missing columns or type mismatches.

---

#### `adapt_prediction_data`

```python
def adapt_prediction_data(
    prediction_df: pd.DataFrame,
    training_schema: dict[str, Any],
) -> pd.DataFrame
```

Adds missing columns (filled with `NaN`) and coerces dtypes to match training schema.

---

#### `_dtypes_compatible`

```python
def _dtypes_compatible(expected: str, actual: str) -> bool
```

Returns True if `actual` dtype is compatible with `expected` (e.g., int64 ↔ float64).

---

### `validation/data_drift_checker.py`

#### `check_data_drift`

```python
def check_data_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str] | None = None,
    threshold_ks: float = 0.05,
    threshold_psi: float = 0.2,
) -> dict[str, Any]
```

Per-feature KS test (numeric) and PSI (categorical).
Returns `{"feature_results": {col: {"ks_stat", "ks_p_value", "psi", "drifted"}}, "drifted_features", "overall_drift"}`.

---

#### `generate_drift_report`

```python
def generate_drift_report(drift_result: dict[str, Any]) -> str
```

Returns a human-readable Markdown summary of drift results.

---

### `validation/model_validator.py`

#### `validate_model_for_deployment`

```python
def validate_model_for_deployment(
    model_path: str,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    problem_type: str,
    domain: str,
    min_performance: dict[str, float] | None = None,
) -> dict[str, Any]
```

Checks model loads, scores meet thresholds, and prediction latency is acceptable.
Returns `{"passed": bool, "metrics": dict, "checks": list[dict], "recommendation": str}`.

---

#### `check_model_stability`

```python
def check_model_stability(
    model_path: str,
    X_test: pd.DataFrame,
    n_runs: int = 10,
) -> dict[str, Any]
```

Runs prediction `n_runs` times; returns `{"mean_latency_ms", "std_latency_ms", "stable": bool}`.

---

## evaluation/

### `evaluation/agent_evaluator.py`

#### `@dataclass EvaluationCase`

```python
@dataclass
class EvaluationCase:
    name: str
    input_state: dict[str, Any]
    expected_outputs: dict[str, Any]
    domain: str = "generic"
    description: str = ""
```

---

#### `evaluate_orchestrator`

```python
def evaluate_orchestrator(
    cases: list[EvaluationCase],
    workflow: CompiledGraph,
) -> dict[str, Any]
```

Runs each case through the orchestrator node; compares outputs against expected.

---

#### `evaluate_profiler`

```python
def evaluate_profiler(
    cases: list[EvaluationCase],
) -> dict[str, Any]
```

Runs `run_data_profiling` against test cases.

---

#### `evaluate_model_selection`

```python
def evaluate_model_selection(
    cases: list[EvaluationCase],
) -> dict[str, Any]
```

Validates that the modeling agent selects sensible algorithms for the given domain/problem type.

---

#### `run_evaluation_suite`

```python
def run_evaluation_suite(
    cases: list[EvaluationCase] | None = None,
    workflow: CompiledGraph | None = None,
) -> dict[str, Any]
```

Runs all three evaluators; aggregates results.

---

#### `get_builtin_cases`

```python
def get_builtin_cases() -> list[EvaluationCase]
```

Returns pre-built test cases spanning all 7 domains.

---

#### `generate_report`

```python
def generate_report(results: dict[str, Any]) -> str
```

Formats evaluation results as a Markdown table.

---

### `evaluation/model_comparator.py`

#### `paired_ttest`

```python
def paired_ttest(
    scores_a: list[float],
    scores_b: list[float],
    alpha: float = 0.05,
) -> dict[str, Any]
```

Returns `{"statistic", "p_value", "significant", "winner"}`.

---

#### `mcnemar_test`

```python
def mcnemar_test(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    alpha: float = 0.05,
) -> dict[str, Any]
```

McNemar's test for classification disagreements.

---

#### `wilcoxon_test`

```python
def wilcoxon_test(
    scores_a: list[float],
    scores_b: list[float],
    alpha: float = 0.05,
) -> dict[str, Any]
```

Non-parametric signed-rank test. Returns `{"statistic", "p_value", "significant", "winner"}`.

---

#### `compare_models`

```python
def compare_models(
    model_results: dict[str, dict[str, float]],
    metric: str,
    method: str = "paired_ttest",
) -> dict[str, Any]
```

Compares all model pairs; returns pairwise results and overall ranking.

---

### `evaluation/bootstrap_ci.py`

#### `bootstrap_ci`

```python
def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Callable,
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
    method: str = "percentile",   # "percentile" | "bca"
) -> dict[str, Any]
```

Returns `{"estimate", "ci_lower", "ci_upper", "ci_level", "n_bootstrap", "method"}`.

---

#### `bootstrap_compare`

```python
def bootstrap_compare(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    metric_fn: Callable,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> dict[str, Any]
```

Bootstrap test of difference; returns `{"delta_estimate", "ci_lower", "ci_upper", "p_value", "significant"}`.

---

#### `bootstrap_multi_metric`

```python
def bootstrap_multi_metric(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fns: dict[str, Callable],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> dict[str, dict[str, Any]]
```

Runs `bootstrap_ci` for each metric function; returns per-metric result dicts.

---

### `evaluation/domain_metrics.py`

#### Finance

```python
def ks_statistic(y_true, y_prob) -> float
# Kolmogorov-Smirnov separation between score distributions

def gini_coefficient(y_true, y_prob) -> float
# Gini = 2 * AUROC - 1

def psi(expected, actual, bins=10) -> float
# Population Stability Index
```

#### Healthcare

```python
def clinical_metrics(y_true, y_pred, y_prob=None) -> dict[str, float]
# sensitivity, specificity, ppv, npv, f1, auroc

def concordance_index(event_times, event_observed, risk_scores) -> float
# Harrell's C-index for survival models
```

#### E-commerce

```python
def rfm_scores(df, customer_id_col, date_col, amount_col) -> pd.DataFrame
# Recency, Frequency, Monetary scoring

def clv_simple(df, customer_id_col, amount_col, periods=12) -> pd.DataFrame
# Simple CLV projection
```

#### Manufacturing

```python
def oee_score(availability, performance, quality) -> float
# Overall Equipment Effectiveness = A × P × Q

def process_capability(measurements, usl, lsl) -> dict[str, float]
# Cp, Cpk, Pp, Ppk
```

#### Marketing

```python
def campaign_lift(control_cr, treatment_cr) -> float
# Percentage lift over control conversion rate
```

#### Dispatcher

```python
def get_domain_metrics(domain: str, y_true, y_pred, y_prob=None, **kwargs) -> dict[str, float]
# Routes to the right domain metrics based on domain name
```

---

### `evaluation/benchmarks/benchmark_runner.py`

#### `class BenchmarkRunner`

```python
class BenchmarkRunner:
    def __init__(
        self,
        datasets_dir: str | None = None,
    ) -> None
    # datasets_dir defaults to package "benchmarks/datasets/"

    def run_single(
        self,
        dataset_name: str,
        dataset_path: str,
        domain: str,
        target_column: str,
        problem_type: str,     # "classification" | "regression"
    ) -> dict[str, Any]
    # Loads dataset, trains standard sklearn models, returns metrics dict

    def run_all(
        self,
        datasets: list[dict] | None = None,
    ) -> list[dict[str, Any]]
    # Runs run_single for each dataset in datasets_dir or provided list

    def save_results(
        self,
        results: list[dict[str, Any]],
        output_path: str | None = None,
    ) -> None
    # Writes results to JSON; defaults to "benchmark_results.json"
```

Internal helpers:
```python
def _benchmark_classification(X_train, X_test, y_train, y_test) -> list[dict]
def _benchmark_regression(X_train, X_test, y_train, y_test) -> list[dict]
```

---

### `evaluation/_comparator_utils.py` (internal)

Not part of the public API; used by `model_comparator.py`.

```python
def validate_paired_scores(scores_a, scores_b, label_a, label_b) -> tuple[ndarray, ndarray]
def validate_score_matrix(score_matrix, model_names) -> ndarray
def significance_label(p_value: float, alpha: float) -> str
# Returns "***" / "**" / "*" / "ns"

def rank_matrix_best_first(matrix: ndarray) -> ndarray
def nemenyi_q_alpha(alpha: float, n_models: int) -> float
# Critical value table from Demsar (2006)

def friedman_test(
    score_matrix: np.ndarray,   # shape (n_datasets, n_models)
    model_names: list[str],
    alpha: float = 0.05,
) -> dict[str, Any]
# Returns {"statistic", "p_value", "significant", "avg_ranks", "model_names"}

def nemenyi_posthoc(
    score_matrix: np.ndarray,
    model_names: list[str],
    alpha: float = 0.05,
) -> dict[str, Any]
# Returns {"pairwise_significant", "critical_difference", "avg_ranks"}
```

---

## explainability/

### `explainability/shap_explainer.py`

#### `compute_shap_values`

```python
def compute_shap_values(
    model: Any,
    X: pd.DataFrame,
    problem_type: str,           # "classification" | "regression"
    max_rows: int = 500,
) -> dict[str, Any]
```

Uses `TreeExplainer` for tree models, `KernelExplainer` otherwise.
Returns `{"global_importance": {feature: float}, "top_features": list[dict], "shap_values": ndarray, "feature_names": list[str], "n_rows_explained": int}`.

---

#### `shap_summary_plot`

```python
def shap_summary_plot(
    shap_values: np.ndarray,
    feature_names: list[str],
    max_features: int = 20,
    title: str = "SHAP Feature Importance",
) -> go.Figure
```

Returns Plotly beeswarm-style figure.

---

#### `shap_waterfall_plot`

```python
def shap_waterfall_plot(
    shap_values: np.ndarray,
    feature_names: list[str],
    instance_idx: int = 0,
    max_features: int = 10,
    title: str = "SHAP Waterfall",
) -> go.Figure
```

Single-instance waterfall chart.

---

#### `shap_bar_plot`

```python
def shap_bar_plot(
    global_importance: dict[str, float],
    max_features: int = 20,
    title: str = "Mean |SHAP| Feature Importance",
) -> go.Figure
```

Horizontal bar chart of mean absolute SHAP values.

---

### `explainability/pdp_ice.py`

#### `partial_dependence_plot`

```python
def partial_dependence_plot(
    model: Any,
    X: pd.DataFrame,
    feature: str,
    grid_resolution: int = 50,
    title: str | None = None,
) -> go.Figure
```

Marginal effect of `feature` on prediction (averaged over all rows).

---

#### `ice_plot`

```python
def ice_plot(
    model: Any,
    X: pd.DataFrame,
    feature: str,
    num_ice_lines: int = 50,
    grid_resolution: int = 50,
    title: str | None = None,
) -> go.Figure
```

Individual Conditional Expectation lines (one per sampled row) + mean PDP overlay.

---

#### `pdp_interact_plot`

```python
def pdp_interact_plot(
    model: Any,
    X: pd.DataFrame,
    feature1: str,
    feature2: str,
    grid_resolution: int = 25,
    title: str | None = None,
) -> go.Figure
```

2D contour heatmap for the interaction between two features.

---

### `explainability/counterfactual.py`

#### `generate_counterfactuals`

```python
def generate_counterfactuals(
    model: Any,
    instance: pd.Series | dict,
    X_train: pd.DataFrame,
    n_counterfactuals: int = 3,
    features_to_vary: list[str] | None = None,
) -> list[dict[str, Any]]
```

Nearest-neighbour strategy. Each result: `{"original_values", "counterfactual_values", "changed_features", "original_pred", "new_pred", "distance"}`.

---

#### `format_counterfactual_explanation`

```python
def format_counterfactual_explanation(cf: dict[str, Any]) -> str
```

Returns a human-readable string describing what changes flip the prediction.

---

### `explainability/fairness_audit.py`

#### `run_fairness_audit`

```python
def run_fairness_audit(
    model: Any,
    X: pd.DataFrame,
    y_true: pd.Series,
    sensitive_features: dict[str, pd.Series],
) -> dict[str, Any]
```

Computes demographic parity difference and equalized odds (fairlearn preferred, manual fallback).
Returns `{"per_attribute": {attr: {"demographic_parity_difference", "equalized_odds_difference", "disparate_impact_ratio"}}, "n_samples", "n_attributes_audited", "recommendations": list[str]}`.

---

#### `disparate_impact_ratio`

```python
def disparate_impact_ratio(
    y_pred: np.ndarray,
    sensitive_col: pd.Series,
) -> float
```

Ratio of positive prediction rates: min_group / max_group.

---

#### `generate_fairness_report`

```python
def generate_fairness_report(audit_results: dict[str, Any]) -> str
```

Returns Markdown summary with pass/fail for each sensitive attribute.

---

### `explainability/plain_english.py`

#### `explain_prediction`

```python
def explain_prediction(
    model: Any,
    instance: pd.Series | dict,
    feature_names: list[str],
    shap_values: np.ndarray | None = None,
    top_n: int = 5,
) -> str
```

Returns plain-language explanation of a single prediction.
Uses SHAP values if available; falls back to `feature_importances_`.

---

#### `explain_model_overall`

```python
def explain_model_overall(
    global_importance: dict[str, float],
    metrics: dict[str, float],
    problem_type: str,
) -> str
```

Returns a paragraph summarising model performance and top drivers.

---

### `explainability/what_if.py`

#### `what_if_prediction`

```python
def what_if_prediction(
    model: Any,
    baseline: pd.Series | dict,
    changes: dict[str, Any],
    feature_names: list[str],
) -> dict[str, Any]
```

Returns `{"baseline_pred", "modified_pred", "delta", "changed_features"}`.

---

#### `what_if_sweep`

```python
def what_if_sweep(
    model: Any,
    baseline: pd.Series | dict,
    feature: str,
    values: list[Any],
    feature_names: list[str],
) -> list[dict[str, Any]]
```

Sweeps `feature` across `values`; returns list of `what_if_prediction` results.

---

### `explainability/adverse_action.py`

#### `generate_adverse_action_codes`

```python
def generate_adverse_action_codes(
    model: Any,
    instance: pd.Series | dict,
    shap_values: np.ndarray,
    feature_names: list[str],
    top_n: int = 4,
) -> list[dict[str, Any]]
```

ECOA / Reg B compliant adverse action codes.
Each entry: `{"reason_code": "AA01"..."AA0N", "feature", "feature_value", "impact", "direction": "increased"|"decreased", "rank"}`.

---

#### `format_adverse_action_notice`

```python
def format_adverse_action_notice(codes: list[dict[str, Any]]) -> str
```

Returns formatted adverse action notice text for regulatory disclosure.

---

### `explainability/calibration.py`

#### `calibration_curve_data`

```python
def calibration_curve_data(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]
```

Returns `{"bin_edges", "mean_predicted", "fraction_positive", "bin_counts"}`.

---

#### `calibration_plot`

```python
def calibration_plot(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    model_name: str = "Model",
    n_bins: int = 10,
) -> go.Figure
```

Reliability diagram (predicted probability vs actual fraction positive) with bin-count histogram overlay.

---

#### `expected_calibration_error`

```python
def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float
```

Weighted mean absolute deviation across bins.

---

#### `brier_score`

```python
def brier_score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> float
```

Mean squared error of probability forecasts (lower = better calibrated).

---

### `explainability/model_card_generator.py`

#### `generate_model_card`

```python
def generate_model_card(
    model_name: str,
    problem_type: str,
    domain: str,
    metrics: dict[str, Any],
    features: list[str],
    training_rows: int,
    shap_results: dict[str, Any] | None = None,
    fairness_results: dict[str, Any] | None = None,
    domain_config: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Google Model Card format.
Returns dict with keys: `model_details`, `intended_use`, `training_data`, `metrics`, `feature_importance`, `limitations`, `ethical_considerations`, `fairness`, `generated_at`.

---

#### `model_card_to_markdown`

```python
def model_card_to_markdown(card: dict[str, Any]) -> str
```

Renders the model card as Markdown with tables for metrics and feature importance.

---

#### `model_card_to_html`

```python
def model_card_to_html(card: dict[str, Any]) -> str
```

Renders the model card as a standalone HTML document (converts Markdown internally).

---

## reports/generators/

### `reports/generators/html_report.py`

#### `generate_html_report`

```python
def generate_html_report(
    state: dict,
    output_dir: str,
) -> str
```

Jinja2-based HTML report; selects domain-specific template (healthcare/finance/ecommerce fall back to base).
Embeds Plotly charts inline.
**State read:** `detected_domain`, `model_results`, `best_model`, `best_model_name`, `eda_charts`, `shap_values`, `fairness_report`, `data_profile`, `session_id`, `pipeline_duration`, `estimated_cost`, `row_count`, `column_info`, `target_column`, `problem_type`, `feature_list`.
Returns absolute path to `{output_dir}/report.html`.

---

### `reports/generators/pdf_report.py`

#### `generate_pdf_report`

```python
def generate_pdf_report(
    state: dict,
    output_dir: str,
) -> str
```

Delegates to `generate_html_report`, strips Plotly JS, injects print CSS, converts via weasyprint.
Returns absolute path to `{output_dir}/report.pdf`, or `""` if weasyprint not installed.

---

### `reports/generators/executive_summary.py`

#### `generate_executive_summary`

```python
def generate_executive_summary(
    state: dict,
    output_dir: str,
) -> str
```

1-page HTML executive summary via Jinja2 `executive_template.html`.
Uses domain terminology map for audience-appropriate language.
**State read:** `detected_domain`, `domain_config`, `best_model`, `best_model_name`, `model_results`, `eda_insights`, `quality_issues`, `feature_list`, `features_selected`, `fairness_report`, `session_id`, `row_count`, `random_seed`.
Returns absolute path to `{output_dir}/executive_summary.html`.

---

### `reports/generators/notebook_export.py`

#### `generate_notebook`

```python
def generate_notebook(
    state: dict,
    output_dir: str,
) -> str
```

Produces a runnable Jupyter notebook (`.ipynb`) via `nbformat`.
Cell sections: imports → data loading → EDA → feature engineering → model training → evaluation → SHAP visualisation.
**State read:** `target_column`, `problem_type`, `feature_list`, `model_results`, `best_model`, `best_model_name`, `shap_values`, `random_seed`, `data_hash`, `session_id`, `detected_domain`.
Returns absolute path to `{output_dir}/analysis.ipynb`.

---

### `reports/generators/zip_packager.py`

#### `create_zip_package`

```python
def create_zip_package(
    file_paths: list[str],
    output_dir: str,
    session_id: str,
) -> str
```

Bundles existing report files into `autods_{session_id}.zip`.
Automatically appends a generated `README.txt` listing contents.
Returns absolute path to the ZIP, or `""` if no valid files exist.

---

## logging_audit/

### `logging_audit/structured_logger.py`

#### `class StructuredLogger`

JSONL event log at `{log_dir}/{session_id}.jsonl` (one JSON object per line).

```python
class StructuredLogger:
    def __init__(
        self,
        session_id: str,
        log_dir: str = "logs",
    ) -> None

    def log_event(
        self,
        event: str,
        data: dict | None = None,
        level: str = "info",
    ) -> None
    # Appends {"timestamp", "session_id", "event", "data", "level"}

    def log_step_start(self, step_name: str) -> None
    def log_step_end(
        self,
        step_name: str,
        duration_seconds: float,
        status: str,          # "success" | "failed" | "skipped"
    ) -> None

    def log_tool_call(
        self,
        tool_name: str,
        params: dict,
        result_summary: str,
        duration: float,
    ) -> None

    def log_error(
        self,
        step: str,
        error: Exception,
        context: dict | None = None,
    ) -> None

    def get_log_path(self) -> str
    def get_all_events(self) -> list[dict]
```

---

### `logging_audit/decision_log.py`

#### `class DecisionLog`

In-memory log of agent decisions for auditability.

```python
class DecisionLog:
    def __init__(self) -> None

    def log_decision(
        self,
        agent: str,
        decision_type: str,
        chosen: str,
        alternatives: list[str] | None = None,
        reasoning: str = "",
        confidence: float | None = None,
    ) -> None
    # Entry schema: {"timestamp", "agent", "step", "decision_type", "chosen",
    #                "alternatives", "reasoning", "confidence"}

    def get_decisions_for_step(self, step: str) -> list[dict]
    def get_all_decisions(self) -> list[dict]
    def to_state_format(self) -> list[dict]
    # Formats for insertion into AutoDSState["decision_log"]

    def export_to_json(self, path: str) -> None
```

---

### `logging_audit/cost_tracker.py`

#### `class CostTracker`

Tracks LLM API call costs by provider and agent.

```python
class CostTracker:
    def __init__(self, provider: str = "openai") -> None

    def log_call(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None

    def get_total_cost(self) -> float
    def get_total_tokens(self) -> dict[str, int]
    # Returns {"input_tokens": int, "output_tokens": int}

    def get_cost_by_agent(self) -> dict[str, float]
    def get_summary(self) -> dict[str, Any]
    # Returns {"total_cost", "total_tokens", "by_agent", "by_model", "n_calls"}
```

---

### `logging_audit/performance_log.py`

#### `class PerformanceLog`

Step-level timing with context manager support.

```python
class PerformanceLog:
    def __init__(self) -> None

    def timer(self, step_name: str) -> ContextManager
    # with perf_log.timer("modeling"): ...

    def start_step(self, step_name: str) -> None
    def end_step(self, step_name: str) -> float
    # Returns elapsed seconds for that step

    def get_total_duration(self) -> float
    def get_slowest_steps(self, n: int = 5) -> list[tuple[str, float]]
    # Returns [(step_name, seconds), ...] sorted by duration desc

    def get_summary(self) -> dict[str, Any]
    # Returns {"total_duration", "steps": {name: seconds}, "slowest"}
```

---

### `logging_audit/audit_trail_export.py`

**Status: Not implemented (stub only).**
File contains only a `logging.getLogger` call; no public functions defined.

---

*End of AutoDS Platform API Signatures Reference.*
