"""Shared workflow state schema for the LangGraph state machine.

This TypedDict defines the complete state that flows through the LangGraph.
Every agent reads from and writes to this shared state.
"""

from typing import Any, TypedDict


class DataSourceInfo(TypedDict, total=False):
    """Metadata about a loaded data source."""
    source_type: str          # "file" | "database" | "api" | "clipboard" | "sample"
    source_name: str          # Filename, table name, or API name
    source_path: str          # File path, connection string, or URL
    format: str               # "csv" | "excel" | "parquet" | etc.
    row_count: int
    column_count: int
    size_mb: float
    duckdb_table_name: str    # Table name in DuckDB warehouse
    load_timestamp: str       # ISO format


class ColumnInfo(TypedDict, total=False):
    """Metadata about a single column."""
    name: str
    dtype: str                # pandas dtype
    inferred_type: str        # "numeric" | "categorical" | "datetime" | "text" | "boolean" | "id"
    unique_count: int
    missing_count: int
    missing_pct: float
    sample_values: list[str]
    cardinality: str          # "binary" | "low" | "medium" | "high" | "unique"


class QuestionResponse(TypedDict, total=False):
    """A question asked to the user and their response."""
    question_id: str
    step: str                 # "eda" | "feature_engineering" | "modeling"
    question_text: str
    question_type: str        # "single_select" | "multi_select" | "slider" | "per_column_table" | "text_input"
    options: list[dict]
    user_response: Any        # The user's selection
    timestamp: str


class ModelResult(TypedDict, total=False):
    """Results from training a single model."""
    model_name: str
    algorithm: str
    metrics: dict[str, float]
    training_time_seconds: float
    mlflow_run_id: str
    model_path: str
    hyperparameters: dict
    cv_scores: list[float]
    confusion_matrix: list[list[int]] | None
    feature_importance: dict[str, float] | None


class AutoDSState(TypedDict, total=False):
    """
    Complete workflow state for the AutoDS platform.
    
    This is the single source of truth that flows through the LangGraph.
    Every agent reads from and writes to this state.
    """

    # =========================================================================
    # Session & Configuration
    # =========================================================================
    session_id: str
    user_mode: str                      # "auto" | "guided" | "expert"
    random_seed: int                    # For reproducibility (default: 42)

    # =========================================================================
    # Data Sources
    # =========================================================================
    data_sources: list[DataSourceInfo]  # All loaded data sources
    joined_data_ref: str                # DuckDB table name for working dataset
    data_hash: str                      # SHA256 hash of input data
    row_count: int                      # Total rows in working dataset
    column_count: int                   # Total columns in working dataset

    # =========================================================================
    # Schema Information
    # =========================================================================
    schema_info: dict                   # Full schema: columns list with ColumnInfo
    columns: list[ColumnInfo]           # Detailed per-column metadata
    id_columns: list[str]              # Detected ID columns (excluded from modeling)
    datetime_columns: list[str]        # Detected datetime columns
    text_columns: list[str]            # Detected text columns
    numeric_columns: list[str]         # Detected numeric columns
    categorical_columns: list[str]     # Detected categorical columns

    # =========================================================================
    # Domain Detection
    # =========================================================================
    detected_domain: str                # "healthcare" | "finance" | "ecommerce" | etc.
    domain_config: dict                 # Full domain configuration object
    domain_confirmed: bool              # User confirmed/overrode detection
    domain_detection_confidence: float  # 0.0 to 1.0

    # =========================================================================
    # User Intent
    # =========================================================================
    user_goal: str                      # Natural language description
    target_column: str | None           # Target variable (None for unsupervised)
    problem_type: str                   # "classification" | "regression" | "clustering" | "time_series"
    time_column: str | None             # For time-series problems

    # =========================================================================
    # Data Profiling Results
    # =========================================================================
    data_profile: dict                  # Custom profiler output (get_data_profile)
    quality_issues: list[dict]          # Detected data quality issues
    cleaning_actions: list[dict]        # Applied cleaning actions with reasoning
    profile_timestamp: str

    # =========================================================================
    # EDA
    # =========================================================================
    eda_questions_asked: list[QuestionResponse]
    eda_analyses_selected: list[str]    # Names of analyses to run
    eda_results: dict                   # Analysis name → result mapping
    eda_charts: list[dict]              # Chart specifications (type, data, title)
    eda_summary: str                    # AI-generated summary of findings
    eda_insights: list[str]             # Key bullet-point insights

    # =========================================================================
    # Feature Engineering
    # =========================================================================
    fe_questions_asked: list[QuestionResponse]
    fe_choices: dict                    # Per-column decisions
    imputation_strategy: dict           # Column → strategy mapping
    encoding_strategy: dict             # Column → encoding mapping
    outlier_strategy: dict              # Column → outlier handling mapping
    scaling_strategy: str               # Global scaling choice
    feature_selection_method: str       # How final features were selected
    features_created: list[str]         # All features created
    features_selected: list[str]        # Final features after selection
    feature_importance_preliminary: dict # Early importance scores

    # =========================================================================
    # Modeling
    # =========================================================================
    model_questions_asked: list[QuestionResponse]
    model_choices: dict                 # User's modeling configuration
    algorithms_selected: list[str]      # Which algorithms to train
    validation_strategy: str            # "holdout" | "kfold" | "time_split" | "walk_forward"
    evaluation_metrics: list[str]       # Which metrics to compute
    cost_matrix: dict | None            # FN/FP cost weights
    threshold_strategy: str | None      # How to set decision threshold
    tuning_strategy: str                # "default" | "quick" | "thorough" | "expert"
    trained_models: dict[str, ModelResult]  # Model name → results
    best_model_name: str                # Name of selected best model
    best_model_path: str                # Path to saved model artifact
    best_model_metrics: dict            # Best model's evaluation metrics
    model_comparison: dict              # Statistical comparison between models

    # =========================================================================
    # Explainability
    # =========================================================================
    shap_values_path: str | None        # Path to saved SHAP values
    shap_summary: dict | None           # SHAP summary statistics
    fairness_report: dict | None        # Fairness audit results
    model_card: dict | None             # Generated model card
    counterfactual_examples: list[dict] | None

    # =========================================================================
    # Reports
    # =========================================================================
    report_paths: dict                  # Format → file path mapping
    report_generated: bool

    # =========================================================================
    # Deployment
    # =========================================================================
    api_endpoint_code: str | None       # Generated FastAPI code
    dockerfile_content: str | None      # Generated Dockerfile

    # =========================================================================
    # Pipeline Metadata & Logging
    # =========================================================================
    pipeline_log: list[dict]            # Timestamped log of all actions
    decision_log: list[dict]            # Log of all decisions with reasoning
    api_call_count: int                 # Claude API calls made this run
    api_token_count: int                # Total tokens used this run
    estimated_cost_usd: float           # Estimated API cost
    errors: list[dict]                  # Any errors encountered
    warnings: list[dict]                # Non-fatal warnings

    # =========================================================================
    # Workflow Control
    # =========================================================================
    current_step: str                   # Current pipeline step name
    completed_steps: list[str]          # Steps completed so far
    pending_approval: dict | None       # Question awaiting user approval
    workflow_status: str                # "running" | "paused" | "completed" | "error"
    start_timestamp: str
    end_timestamp: str | None
    total_duration_seconds: float | None


def create_initial_state(session_id: str, user_mode: str = "guided") -> AutoDSState:
    """Create a fresh initial state for a new pipeline run."""
    from datetime import datetime, timezone

    return AutoDSState(
        session_id=session_id,
        user_mode=user_mode,
        random_seed=42,
        data_sources=[],
        joined_data_ref="",
        data_hash="",
        row_count=0,
        column_count=0,
        schema_info={},
        columns=[],
        id_columns=[],
        datetime_columns=[],
        text_columns=[],
        numeric_columns=[],
        categorical_columns=[],
        detected_domain="generic",
        domain_config={},
        domain_confirmed=False,
        domain_detection_confidence=0.0,
        user_goal="",
        target_column=None,
        problem_type="",
        time_column=None,
        data_profile={},
        quality_issues=[],
        cleaning_actions=[],
        profile_timestamp="",
        eda_questions_asked=[],
        eda_analyses_selected=[],
        eda_results={},
        eda_charts=[],
        eda_summary="",
        eda_insights=[],
        fe_questions_asked=[],
        fe_choices={},
        imputation_strategy={},
        encoding_strategy={},
        outlier_strategy={},
        scaling_strategy="robust",
        feature_selection_method="",
        features_created=[],
        features_selected=[],
        feature_importance_preliminary={},
        model_questions_asked=[],
        model_choices={},
        algorithms_selected=[],
        validation_strategy="kfold",
        evaluation_metrics=[],
        cost_matrix=None,
        threshold_strategy=None,
        tuning_strategy="quick",
        trained_models={},
        best_model_name="",
        best_model_path="",
        best_model_metrics={},
        model_comparison={},
        shap_values_path=None,
        shap_summary=None,
        fairness_report=None,
        model_card=None,
        counterfactual_examples=None,
        report_paths={},
        report_generated=False,
        api_endpoint_code=None,
        dockerfile_content=None,
        pipeline_log=[],
        decision_log=[],
        api_call_count=0,
        api_token_count=0,
        estimated_cost_usd=0.0,
        errors=[],
        warnings=[],
        current_step="initialization",
        completed_steps=[],
        pending_approval=None,
        workflow_status="running",
        start_timestamp=datetime.now(timezone.utc).isoformat(),
        end_timestamp=None,
        total_duration_seconds=None,
    )
