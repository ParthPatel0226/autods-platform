"""Global constants for the AutoDS platform."""

# =============================================================================
# Platform Info
# =============================================================================
PLATFORM_NAME = "AutoDS"
PLATFORM_VERSION = "1.0.0"
PLATFORM_DESCRIPTION = "Autonomous Data Science Platform"

# =============================================================================
# User Modes
# =============================================================================
MODE_AUTO = "auto"
MODE_GUIDED = "guided"
MODE_EXPERT = "expert"
VALID_MODES = [MODE_AUTO, MODE_GUIDED, MODE_EXPERT]

# =============================================================================
# Problem Types
# =============================================================================
PROBLEM_CLASSIFICATION = "classification"
PROBLEM_REGRESSION = "regression"
PROBLEM_CLUSTERING = "clustering"
PROBLEM_TIME_SERIES = "time_series"
PROBLEM_UNSUPERVISED = "unsupervised"
VALID_PROBLEM_TYPES = [
    PROBLEM_CLASSIFICATION,
    PROBLEM_REGRESSION,
    PROBLEM_CLUSTERING,
    PROBLEM_TIME_SERIES,
]

# =============================================================================
# Supported Domains
# =============================================================================
DOMAIN_HEALTHCARE = "healthcare"
DOMAIN_FINANCE = "finance"
DOMAIN_ECOMMERCE = "ecommerce"
DOMAIN_MARKETING = "marketing"
DOMAIN_HR = "hr"
DOMAIN_MANUFACTURING = "manufacturing"
DOMAIN_GENERIC = "generic"
VALID_DOMAINS = [
    DOMAIN_HEALTHCARE,
    DOMAIN_FINANCE,
    DOMAIN_ECOMMERCE,
    DOMAIN_MARKETING,
    DOMAIN_HR,
    DOMAIN_MANUFACTURING,
    DOMAIN_GENERIC,
]

# =============================================================================
# Column Type Detection
# =============================================================================
COLUMN_TYPE_NUMERIC = "numeric"
COLUMN_TYPE_CATEGORICAL = "categorical"
COLUMN_TYPE_DATETIME = "datetime"
COLUMN_TYPE_TEXT = "text"
COLUMN_TYPE_BOOLEAN = "boolean"
COLUMN_TYPE_ID = "id"
COLUMN_TYPE_UNKNOWN = "unknown"

# =============================================================================
# Supported File Formats
# =============================================================================
SUPPORTED_FILE_EXTENSIONS = {
    "csv": "CSV (Comma-Separated Values)",
    "tsv": "TSV (Tab-Separated Values)",
    "xlsx": "Excel Workbook",
    "xls": "Excel Legacy",
    "parquet": "Apache Parquet",
    "feather": "Apache Feather / Arrow",
    "json": "JSON",
    "jsonl": "JSON Lines",
    "xml": "XML",
    "sqlite": "SQLite Database",
    "db": "SQLite Database",
    "sas7bdat": "SAS Dataset",
    "dta": "STATA Dataset",
    "sav": "SPSS Dataset",
    "h5": "HDF5 Dataset",
    "hdf5": "HDF5 Dataset",
    "orc": "Apache ORC",
    "pkl": "Python Pickle (use with caution)",
    "zip": "ZIP Archive",
    "gz": "GZip Compressed",
    "pdf": "PDF (table extraction)",
}

# =============================================================================
# Supported Database Engines
# =============================================================================
SUPPORTED_DATABASES = {
    "postgresql": "PostgreSQL",
    "mysql": "MySQL / MariaDB",
    "sqlite": "SQLite",
    "duckdb": "DuckDB",
    "sqlserver": "Microsoft SQL Server",
    "bigquery": "Google BigQuery",
    "snowflake": "Snowflake",
    "redshift": "Amazon Redshift",
}

# =============================================================================
# ML Algorithm Registry (names for UI display)
# =============================================================================
CLASSIFICATION_ALGORITHMS = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "svm": "Support Vector Machine",
    "knn": "K-Nearest Neighbors",
    "naive_bayes": "Naive Bayes",
    "mlp": "Neural Network (MLP)",
    "flaml_auto": "AutoML (FLAML)",
}

REGRESSION_ALGORITHMS = {
    "linear_regression": "Linear Regression",
    "ridge": "Ridge Regression",
    "lasso": "Lasso Regression",
    "elasticnet": "ElasticNet",
    "decision_tree_reg": "Decision Tree Regressor",
    "random_forest_reg": "Random Forest Regressor",
    "xgboost_reg": "XGBoost Regressor",
    "lightgbm_reg": "LightGBM Regressor",
    "catboost_reg": "CatBoost Regressor",
    "flaml_auto": "AutoML (FLAML)",
}

CLUSTERING_ALGORITHMS = {
    "kmeans": "K-Means",
    "dbscan": "DBSCAN",
    "hierarchical": "Agglomerative Clustering",
    "gaussian_mixture": "Gaussian Mixture Model",
}

# =============================================================================
# Evaluation Metrics
# =============================================================================
CLASSIFICATION_METRICS = [
    "accuracy", "precision", "recall", "f1", "auc_roc", "auc_pr",
    "sensitivity", "specificity", "npv", "ppv",
    "ks_statistic", "gini_coefficient",  # Finance-specific
    "log_loss", "brier_score", "matthews_corrcoef",
]

REGRESSION_METRICS = [
    "rmse", "mae", "mape", "r2", "adjusted_r2",
    "median_absolute_error", "max_error",
]

CLUSTERING_METRICS = [
    "silhouette_score", "calinski_harabasz", "davies_bouldin",
    "inertia",
]

# =============================================================================
# Missing Value Strategies
# =============================================================================
IMPUTATION_STRATEGIES = {
    "mean": "Mean Imputation",
    "median": "Median Imputation",
    "mode": "Mode Imputation",
    "knn": "KNN Imputation",
    "forward_fill": "Forward Fill (time-series)",
    "backward_fill": "Backward Fill (time-series)",
    "interpolate": "Linear Interpolation",
    "flag_missing": "Create Missing Indicator Flag",
    "drop_rows": "Drop Rows with Missing Values",
    "drop_column": "Drop Entire Column",
    "constant": "Fill with Constant Value",
}

# =============================================================================
# Encoding Strategies
# =============================================================================
ENCODING_STRATEGIES = {
    "onehot": "One-Hot Encoding",
    "label": "Label Encoding",
    "target": "Target Encoding",
    "frequency": "Frequency Encoding",
    "binary": "Binary Encoding",
    "hash": "Hash Encoding",
    "ordinal": "Ordinal Encoding",
}

# =============================================================================
# Scaling Strategies
# =============================================================================
SCALING_STRATEGIES = {
    "standard": "StandardScaler (zero mean, unit variance)",
    "minmax": "MinMaxScaler (0-1 range)",
    "robust": "RobustScaler (median/IQR — handles outliers)",
    "none": "No Scaling",
}

# =============================================================================
# Default Settings
# =============================================================================
DEFAULT_RANDOM_SEED = 42
DEFAULT_TEST_SIZE = 0.2
DEFAULT_CV_FOLDS = 5
DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.80
DEFAULT_MAX_FEATURES = 100
DEFAULT_FLAML_TIME_BUDGET = 120  # seconds
DEFAULT_OPTUNA_TRIALS = 100
MISSING_THRESHOLD_DROP_COLUMN = 0.5  # Drop column if >50% missing
OUTLIER_IQR_MULTIPLIER = 1.5
HIGH_CARDINALITY_THRESHOLD = 50  # Target-encode if >50 unique values
CORRELATION_THRESHOLD = 0.95  # Remove one of correlated pair above this
VIF_THRESHOLD = 10.0  # Flag multicollinearity above this VIF

# =============================================================================
# API Cost Estimates (per 1K tokens, by provider)
# =============================================================================
PROVIDER_TOKEN_COSTS: dict[str, dict[str, float]] = {
    "gemini":    {"input": 0.00013, "output": 0.00038},   # Gemma 4 31B via Gemini API
    "ollama":    {"input": 0.0,     "output": 0.0},       # Free (local)
    "anthropic": {"input": 0.003,   "output": 0.015},     # Claude Sonnet
    "openai":    {"input": 0.005,   "output": 0.015},     # GPT-4o
}


def get_token_costs(provider: str | None = None) -> tuple[float, float]:
    """Return (input_cost_per_1k, output_cost_per_1k) for the given provider.

    If *provider* is None, reads AUTODS_LLM_PROVIDER from the environment,
    defaulting to ``"gemini"``.
    """
    import os

    if provider is None:
        provider = os.getenv("AUTODS_LLM_PROVIDER", "gemini").lower()
    costs = PROVIDER_TOKEN_COSTS.get(provider, {"input": 0.0, "output": 0.0})
    return costs["input"], costs["output"]


# Legacy aliases -- kept for backward compatibility but now provider-aware
COST_PER_1K_INPUT_TOKENS = PROVIDER_TOKEN_COSTS["anthropic"]["input"]
COST_PER_1K_OUTPUT_TOKENS = PROVIDER_TOKEN_COSTS["anthropic"]["output"]

# =============================================================================
# Report Settings
# =============================================================================
REPORT_FORMATS = ["html", "pdf", "executive_summary", "notebook", "zip"]
MAX_CHARTS_PER_REPORT = 30
MAX_SHAP_SAMPLES = 500  # Limit SHAP computation for speed
