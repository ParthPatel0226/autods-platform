# BUILD_NEXT.md - Phase 1 Implementation Guide
## Actionable specs for next coding session

---

## Quick Start

```bash
# 1. Enter project
cd autods-platform

# 2. Install deps (if not done)
make install

# 3. Start with ANY of the 3 parallel tracks:
#    Track 1A: stats_tools.py + data_tools.py
#    Track 1B: viz_tools.py + feature_tools.py
#    Track 1C: ml_tools.py + file connectors
```

**Rule:** Every function returns a structured dict. Every function accepts `df: pd.DataFrame` as first arg. Every function has type hints + docstring. Every function is independently testable.

---

## Track 1A: Statistical & Data Tools

### File: `agents/tools/stats_tools.py`

All functions follow this pattern:
```python
def function_name(df: pd.DataFrame, ...) -> dict:
    """One-line description.

    Args:
        df: Input DataFrame
        ...specific params...

    Returns:
        dict with keys: statistic, p_value, effect_size, interpretation, ...
    """
```

**Functions to implement (16):**

| # | Function | Params | Returns | Library |
|---|----------|--------|---------|---------|
| 1 | `t_test_independent` | df, numeric_col, group_col, alpha=0.05 | statistic, p_value, effect_size (Cohen's d), ci_lower, ci_upper, interpretation | scipy.stats.ttest_ind |
| 2 | `t_test_paired` | df, col1, col2, alpha=0.05 | statistic, p_value, effect_size, interpretation | scipy.stats.ttest_rel |
| 3 | `mann_whitney_u` | df, numeric_col, group_col, alpha=0.05 | statistic, p_value, effect_size (rank-biserial), interpretation | scipy.stats.mannwhitneyu |
| 4 | `chi_square_test` | df, col1, col2, alpha=0.05 | statistic, p_value, dof, effect_size (Cramer's V), contingency_table, interpretation | scipy.stats.chi2_contingency |
| 5 | `fisher_exact_test` | df, col1, col2, alpha=0.05 | odds_ratio, p_value, contingency_table, interpretation | scipy.stats.fisher_exact |
| 6 | `anova_oneway` | df, numeric_col, group_col, alpha=0.05 | statistic, p_value, effect_size (eta-squared), group_means, interpretation | scipy.stats.f_oneway |
| 7 | `kruskal_wallis` | df, numeric_col, group_col, alpha=0.05 | statistic, p_value, effect_size (epsilon-squared), interpretation | scipy.stats.kruskal |
| 8 | `shapiro_wilk` | df, column, alpha=0.05 | statistic, p_value, is_normal, interpretation | scipy.stats.shapiro |
| 9 | `levene_test` | df, numeric_col, group_col, alpha=0.05 | statistic, p_value, equal_variances, interpretation | scipy.stats.levene |
| 10 | `correlation_pearson` | df, col1, col2 | r, p_value, r_squared, interpretation | scipy.stats.pearsonr |
| 11 | `correlation_spearman` | df, col1, col2 | rho, p_value, interpretation | scipy.stats.spearmanr |
| 12 | `ks_test` | df, column, reference_dist="norm" | statistic, p_value, interpretation | scipy.stats.kstest |
| 13 | `vif_analysis` | df, columns: list[str] | vif_scores: dict[str, float], high_vif_columns: list, interpretation | statsmodels.stats.outliers_influence.variance_inflation_factor |
| 14 | `kaplan_meier` | df, duration_col, event_col, group_col=None | survival_table, median_survival, plot_data, interpretation | lifelines.KaplanMeierFitter |
| 15 | `cox_ph` | df, duration_col, event_col, covariates: list[str] | coefficients, hazard_ratios, p_values, concordance, interpretation | lifelines.CoxPHFitter |
| 16 | `correlation_matrix` | df, columns: list[str]=None, method="pearson" | matrix: dict, top_correlations: list, interpretation | pandas .corr() |

**Interpretation helper (private):**
```python
def _interpret_p_value(p_value: float, alpha: float, test_name: str) -> str:
    """Generate plain-English interpretation of statistical test result."""
```

---

### File: `agents/tools/data_tools.py`

**Functions to implement (15):**

| # | Function | Purpose | Library |
|---|----------|---------|---------|
| 1 | `load_to_duckdb(df, table_name) -> str` | Load DataFrame into DuckDB, return table name | duckdb |
| 2 | `query_duckdb(query, table_name) -> pd.DataFrame` | Execute SQL query | duckdb |
| 3 | `get_column_stats(df) -> dict` | Per-column: dtype, unique, missing%, min/max/mean/std, top values | pandas |
| 4 | `detect_column_types(df) -> dict[str, str]` | Classify columns: numeric/categorical/datetime/text/binary/id | pandas + heuristics |
| 5 | `get_missing_summary(df) -> dict` | Missing values per column: count, percentage, pattern (MCAR/MAR/MNAR hint) | pandas |
| 6 | `handle_missing(df, strategy: dict) -> pd.DataFrame` | Apply per-column strategies: mean/median/mode/drop/forward_fill/knn | pandas, sklearn |
| 7 | `detect_outliers(df, columns, method="iqr") -> dict` | Detect outliers per column, return indices + stats | pandas |
| 8 | `handle_outliers(df, column, method, **kwargs) -> pd.DataFrame` | Cap/remove/winsorize outliers | pandas, scipy |
| 9 | `detect_duplicates(df) -> dict` | Find exact + near-duplicate rows | pandas |
| 10 | `remove_duplicates(df, subset=None, keep="first") -> pd.DataFrame` | Drop duplicate rows | pandas |
| 11 | `sample_data(df, n=1000, strategy="stratified", target_col=None) -> pd.DataFrame` | Smart sampling | pandas, sklearn |
| 12 | `get_data_profile(df) -> dict` | Comprehensive profile: shape, memory, dtypes, missing, cardinality, correlations | pandas |
| 13 | `split_train_test(df, target_col, test_size=0.2, stratify=True, seed=42) -> tuple` | Train/test split | sklearn |
| 14 | `merge_dataframes(df1, df2, on, how="inner") -> pd.DataFrame` | Merge with validation | pandas |
| 15 | `export_dataframe(df, path, format="csv") -> str` | Export to CSV/Parquet/Excel | pandas |

---

## Track 1B: Visualization & Feature Tools

### File: `agents/tools/viz_tools.py`

All viz functions follow this pattern:
```python
def chart_name(df: pd.DataFrame, ...) -> dict:
    """Create a [chart type].

    Returns:
        dict with keys:
            figure: plotly.graph_objects.Figure (JSON-serializable)
            title: str
            description: str
            insights: list[str]  (auto-generated observations)
    """
```

**Functions to implement (25):**

| # | Function | Key Params |
|---|----------|-----------|
| 1 | `histogram` | df, column, bins=30, color_by=None |
| 2 | `box_plot` | df, column, group_by=None |
| 3 | `violin_plot` | df, column, group_by=None |
| 4 | `scatter_plot` | df, x_col, y_col, color_by=None, size_by=None |
| 5 | `correlation_heatmap` | df, columns=None, method="pearson" |
| 6 | `pair_plot` | df, columns, color_by=None, max_cols=6 |
| 7 | `bar_chart` | df, x_col, y_col=None, orientation="v" |
| 8 | `line_chart` | df, x_col, y_col, group_by=None |
| 9 | `time_series_plot` | df, date_col, value_col, resample=None |
| 10 | `pie_chart` | df, labels_col, values_col=None |
| 11 | `heatmap` | df, x_col, y_col, value_col |
| 12 | `qq_plot` | df, column |
| 13 | `residual_plot` | y_true, y_pred |
| 14 | `confusion_matrix_plot` | y_true, y_pred, labels=None |
| 15 | `roc_curve_plot` | y_true, y_scores, model_names=None |
| 16 | `pr_curve_plot` | y_true, y_scores, model_names=None |
| 17 | `calibration_curve_plot` | y_true, y_probs, n_bins=10 |
| 18 | `shap_summary_plot` | shap_values, feature_names |
| 19 | `shap_force_plot` | shap_values, base_value, feature_names, instance_idx |
| 20 | `feature_importance_plot` | importances: dict, top_n=20 |
| 21 | `funnel_chart` | stages: list[dict] with name + value |
| 22 | `cohort_retention_plot` | df, cohort_col, period_col, value_col |
| 23 | `survival_curve_plot` | survival_data: dict from kaplan_meier |
| 24 | `gain_lift_plot` | y_true, y_scores |
| 25 | `pdp_plot` | model, X, feature, feature_name |

**Helper:**
```python
def _default_layout(title: str, x_label: str = "", y_label: str = "") -> dict:
    """Standard Plotly layout template for consistent styling."""
```

---

### File: `agents/tools/feature_tools.py`

All feature functions follow this pattern:
```python
def transform_name(df: pd.DataFrame, ...) -> pd.DataFrame:
    """Apply [transformation] to specified columns.

    Returns:
        New DataFrame with transformed/added columns.
        Never mutates the input df.
    """
```

**Functions to implement (30):**

**Encoding (7):**
| # | Function | Purpose |
|---|----------|---------|
| 1 | `one_hot_encode(df, columns, drop_first=True, max_categories=20)` | Binary dummies |
| 2 | `target_encode(df, columns, target_col, smoothing=10)` | Mean target per category |
| 3 | `ordinal_encode(df, columns, order_map=None)` | Ordered integer encoding |
| 4 | `binary_encode(df, columns)` | Binary digit encoding |
| 5 | `frequency_encode(df, columns)` | Replace with frequency |
| 6 | `woe_encode(df, columns, target_col)` | Weight of Evidence (finance) |
| 7 | `label_encode(df, columns)` | Simple integer labels |

**Scaling (4):**
| # | Function | Purpose |
|---|----------|---------|
| 8 | `standard_scale(df, columns)` | z-score normalization |
| 9 | `minmax_scale(df, columns, range=(0,1))` | Min-max scaling |
| 10 | `robust_scale(df, columns)` | Median/IQR scaling |
| 11 | `normalize(df, columns, norm="l2")` | L1/L2 normalization |

**Transforms (5):**
| # | Function | Purpose |
|---|----------|---------|
| 12 | `log_transform(df, columns, base="natural")` | Log transform (handle zeros) |
| 13 | `box_cox_transform(df, columns)` | Box-Cox power transform |
| 14 | `yeo_johnson_transform(df, columns)` | Yeo-Johnson (handles negatives) |
| 15 | `sqrt_transform(df, columns)` | Square root transform |
| 16 | `power_transform(df, columns, power=2)` | Arbitrary power transform |

**Feature Creation (8):**
| # | Function | Purpose |
|---|----------|---------|
| 17 | `polynomial_features(df, columns, degree=2, interaction_only=False)` | Polynomial expansion |
| 18 | `interaction_features(df, col_pairs: list[tuple])` | Pairwise interactions |
| 19 | `date_parts(df, date_col)` | Extract year/month/day/dow/hour/quarter/is_weekend |
| 20 | `lag_features(df, column, lags: list[int], sort_col=None)` | Time-series lags |
| 21 | `rolling_features(df, column, windows: list[int], aggs=["mean","std"])` | Rolling statistics |
| 22 | `binning(df, column, strategy="quantile", n_bins=5, labels=None)` | Numeric to categorical |
| 23 | `ratio_features(df, numerator_col, denominator_col, name=None)` | Column ratios |
| 24 | `text_length_features(df, text_col)` | char_count, word_count, avg_word_len |

**Imputation (4):**
| # | Function | Purpose |
|---|----------|---------|
| 25 | `impute_mean(df, columns)` | Mean imputation |
| 26 | `impute_median(df, columns)` | Median imputation |
| 27 | `impute_mode(df, columns)` | Mode imputation |
| 28 | `impute_knn(df, columns, n_neighbors=5)` | KNN imputation |

**Selection (2):**
| # | Function | Purpose |
|---|----------|---------|
| 29 | `select_features_importance(df, target_col, top_n=20)` | Tree-based importance selection |
| 30 | `drop_low_variance(df, threshold=0.01)` | Remove near-constant columns |

---

## Track 1C: ML Tools + File Connectors

### File: `agents/tools/ml_tools.py`

**Functions to implement (15):**

| # | Function | Purpose | Library |
|---|----------|---------|---------|
| 1 | `train_model(X_train, y_train, algorithm, params=None) -> dict` | Train single model, return model+metrics | sklearn/xgb/lgbm/catboost |
| 2 | `cross_validate_model(X, y, algorithm, cv=5, scoring=None) -> dict` | K-fold CV with metrics per fold | sklearn |
| 3 | `hyperparameter_tune(X, y, algorithm, param_grid, cv=5, method="random") -> dict` | Grid/random/bayesian search | sklearn, optuna |
| 4 | `evaluate_model(model, X_test, y_test, problem_type) -> dict` | Full metrics: accuracy/f1/auc/rmse/r2 + confusion matrix | sklearn |
| 5 | `compare_models(results: list[dict]) -> dict` | Rank models by metric, statistical comparison | pandas |
| 6 | `select_best_model(results: list[dict], metric="f1") -> dict` | Pick best by specified metric | - |
| 7 | `train_test_split_stratified(df, target_col, test_size=0.2, seed=42) -> tuple` | Stratified split | sklearn |
| 8 | `get_feature_importance(model, feature_names) -> dict` | Extract importance from any model type | sklearn/xgb/lgbm |
| 9 | `predict(model, X) -> np.ndarray` | Generate predictions | sklearn |
| 10 | `predict_proba(model, X) -> np.ndarray` | Generate probability predictions | sklearn |
| 11 | `save_model(model, path, metadata=None) -> str` | Save model artifact | joblib + mlflow |
| 12 | `load_model(path) -> Any` | Load model artifact | joblib |
| 13 | `get_supported_algorithms(problem_type) -> list[dict]` | List available algorithms for problem type | - |
| 14 | `automl_train(X, y, time_budget=60, metric="auto") -> dict` | FLAML AutoML training | flaml |
| 15 | `create_pipeline(steps: list[tuple]) -> sklearn.pipeline.Pipeline` | Build sklearn pipeline | sklearn |

**Algorithm registry (internal dict):**
```python
ALGORITHMS = {
    "classification": {
        "logistic_regression": {"class": LogisticRegression, "default_params": {...}},
        "random_forest": {"class": RandomForestClassifier, "default_params": {...}},
        "xgboost": {"class": XGBClassifier, "default_params": {...}},
        "lightgbm": {"class": LGBMClassifier, "default_params": {...}},
        "catboost": {"class": CatBoostClassifier, "default_params": {...}},
    },
    "regression": {
        "linear": {"class": LinearRegression, "default_params": {...}},
        "ridge": {"class": Ridge, "default_params": {...}},
        "random_forest": {"class": RandomForestRegressor, "default_params": {...}},
        "xgboost": {"class": XGBRegressor, "default_params": {...}},
        "lightgbm": {"class": LGBMRegressor, "default_params": {...}},
    },
    "clustering": {
        "kmeans": {"class": KMeans, "default_params": {...}},
        "dbscan": {"class": DBSCAN, "default_params": {...}},
    }
}
```

### File Connectors to Complete

| File | Status | What to add |
|------|--------|------------|
| `file_connectors/csv_connector.py` | DONE | Auto-delimiter detection (sniff first 5 lines) |
| `file_connectors/excel_connector.py` | PARTIAL | Sheet selection UI, multi-sheet merge |
| `file_connectors/json_connector.py` | DONE | - |
| `file_connectors/parquet_connector.py` | STUB | Parquet + Feather via pyarrow |
| `file_connectors/xml_connector.py` | STUB | lxml table extraction |
| `file_connectors/compressed_connector.py` | STUB | ZIP/GZ/TAR extract + scan |
| `file_connectors/statistical_connector.py` | STUB | SAS/STATA/SPSS via pyreadstat |
| `file_connectors/pdf_connector.py` | STUB | tabula-py table extraction |
| `file_connectors/sqlite_connector.py` | STUB | SQLite file + table listing |

---

## Phase 1 Completion Checklist

```
Track 1A (Stats + Data):
  [ ] stats_tools.py    — 16 functions implemented
  [ ] data_tools.py     — 15 functions implemented
  [ ] Unit tests for both in tests/unit/test_statistical_tools.py

Track 1B (Viz + Features):
  [ ] viz_tools.py      — 25 functions implemented
  [ ] feature_tools.py  — 30 functions implemented
  [ ] Unit tests in tests/unit/test_viz_tools.py, test_feature_tools.py

Track 1C (ML + Connectors):
  [ ] ml_tools.py       — 15 functions implemented
  [ ] tool_registry.py  — All entries have full metadata
  [ ] parquet_connector.py   — working
  [ ] excel_connector.py     — complete
  [ ] Remaining connectors   — at least stubs with base structure

INTEGRATION TEST:
  [ ] Can load CSV → get profile → run stats → generate charts → engineer features
  [ ] All tool_registry entries resolve to real functions
```

---

## Phase 2 Preview (After Phase 1)

Once tools exist, implement agents that USE them:
```
2A: agents/data_profiler.py → agents/eda_agent.py → agents/feature_engineer.py
2B: domains/*.py (full question sets + metrics for all 7 domains)
2C: logging_audit/* (structured logger, decision log, cost tracker)
```

See `docs/DEVELOPMENT_PHASES.md` for full Phase 2-7 details.

---

## Key Conventions

1. **Immutability**: `feature_tools` returns NEW DataFrame, never mutates input
2. **Dict returns**: All stats/viz/ml functions return structured dicts, not raw values
3. **Error handling**: Wrap in try/except, raise `ToolExecutionError` from `core.exceptions`
4. **Logging**: Use `logger.info/warning/error`, never `print()`
5. **Type hints**: Every function, every parameter
6. **No LLM calls**: Tool functions are pure Python computation. LLM calls live in agents only.
