# Tool Registry Reference

The tool registry (`agents/tools/tool_registry.py`) catalogs every computation function available to AutoDS agents. Agents search the registry to find appropriate tools for each analysis task.

## Statistical Tests (16 tests)

| Test | Function | When to Use | Domains |
|------|----------|-------------|---------|
| Independent T-Test | `stats_tools.t_test_independent` | Compare means between 2 groups | All |
| Paired T-Test | `stats_tools.t_test_paired` | Pre-post measurements | All |
| Mann-Whitney U | `stats_tools.mann_whitney_u` | Non-parametric 2-group comparison | All |
| Chi-Square | `stats_tools.chi_square_test` | Association between categoricals | All |
| Fisher's Exact | `stats_tools.fisher_exact_test` | Small 2x2 contingency tables | All |
| One-Way ANOVA | `stats_tools.one_way_anova` | Compare means across 3+ groups | All |
| Kruskal-Wallis | `stats_tools.kruskal_wallis` | Non-parametric 3+ group comparison | All |
| Shapiro-Wilk | `stats_tools.shapiro_wilk` | Normality test | All |
| Levene's Test | `stats_tools.levene_test` | Test equal variances | All |
| Pearson Correlation | `stats_tools.correlation_pearson` | Linear correlation coefficient | All |
| Spearman Correlation | `stats_tools.correlation_spearman` | Monotonic correlation | All |
| KS Test | `stats_tools.ks_test_2sample` | Distribution comparison | Finance |
| VIF | `stats_tools.variance_inflation_factor` | Multicollinearity detection | All |
| Kaplan-Meier | `stats_tools.kaplan_meier` | Survival curve estimation | Healthcare, Mfg |
| Cox PH | `stats_tools.cox_proportional_hazard` | Survival regression | Healthcare |
| Log-Rank | `stats_tools.log_rank_test` | Compare survival curves | Healthcare |

## Visualizations (25+ chart types)

| Chart | Function | Best For |
|-------|----------|----------|
| Histogram | `viz_tools.histogram` | Distribution of single numeric |
| Box Plot | `viz_tools.box_plot` | Distribution + outliers |
| Violin Plot | `viz_tools.violin_plot` | Distribution shape comparison |
| Scatter Plot | `viz_tools.scatter_plot` | 2-variable relationship |
| Heatmap | `viz_tools.correlation_heatmap` | Correlation matrix |
| Bar Chart | `viz_tools.bar_chart` | Category comparison |
| Line Chart | `viz_tools.line_chart` | Trends over time |
| Pie Chart | `viz_tools.pie_chart` | Proportion breakdown |
| Sunburst | `viz_tools.sunburst_chart` | Hierarchical proportions |
| Treemap | `viz_tools.treemap_chart` | Nested category proportions |
| Pair Plot | `viz_tools.pair_plot` | Multi-variable relationships |
| Strip Plot | `viz_tools.strip_plot` | Individual point distributions |
| Waterfall | `viz_tools.waterfall_chart` | Sequential value contributions |
| Funnel | `viz_tools.funnel_chart` | Conversion funnel |
| Time Series | `viz_tools.time_series_plot` | Temporal patterns |
| Distribution Comparison | `viz_tools.distribution_comparison` | Side-by-side distributions |
| QQ Plot | `viz_tools.qq_plot` | Normality assessment |
| Residual Plot | `viz_tools.residual_plot` | Model diagnostic |
| ROC Curve | `viz_tools.roc_curve_plot` | Classification performance |
| Precision-Recall | `viz_tools.precision_recall_plot` | Imbalanced classification |
| Confusion Matrix | `viz_tools.confusion_matrix_plot` | Classification errors |
| Feature Importance | `viz_tools.feature_importance_plot` | Model feature ranking |
| Learning Curve | `viz_tools.learning_curve_plot` | Bias-variance diagnosis |
| Gain/Lift | `viz_tools.gain_lift_plot` | Model discrimination |
| Calibration | `viz_tools.calibration_plot` | Probability reliability |

## Feature Engineering (30+ techniques)

| Technique | Function | Category |
|-----------|----------|----------|
| One-Hot Encoding | `feature_tools.one_hot_encode` | Categorical |
| Target Encoding | `feature_tools.target_encode` | Categorical |
| Ordinal Encoding | `feature_tools.ordinal_encode` | Categorical |
| Binary Encoding | `feature_tools.binary_encode` | Categorical |
| Frequency Encoding | `feature_tools.frequency_encode` | Categorical |
| WoE Encoding | `feature_tools.woe_encode` | Categorical (Finance) |
| Standard Scaling | `feature_tools.standard_scale` | Numeric |
| MinMax Scaling | `feature_tools.minmax_scale` | Numeric |
| Log Transform | `feature_tools.log_transform` | Numeric (skewed) |
| Box-Cox | `feature_tools.box_cox_transform` | Numeric (skewed) |
| Polynomial Features | `feature_tools.polynomial_features` | Numeric |
| Interaction Features | `feature_tools.interaction_features` | Numeric |
| Date Parts | `feature_tools.date_parts` | Datetime |
| Lag Features | `feature_tools.lag_features` | Time Series |
| Rolling Features | `feature_tools.rolling_features` | Time Series |
| Binning | `feature_tools.bin_numeric` | Numeric |

## Domain-Specific Tools (22 functions)

| Tool | Function | Domain |
|------|----------|--------|
| Charlson Index | `domain_tools.charlson_comorbidity_index` | Healthcare |
| Elixhauser Index | `domain_tools.elixhauser_comorbidity` | Healthcare |
| RFM Features | `domain_tools.rfm_features` | E-commerce |
| CLV Calculation | `domain_tools.clv_calculation` | E-commerce |
| KS Statistic | `domain_tools.ks_statistic` | Finance |
| Gini Coefficient | `domain_tools.gini_coefficient` | Finance |
| OEE Calculation | `domain_tools.oee_calculation` | Manufacturing |
| MTBF Calculation | `domain_tools.mtbf_calculation` | Manufacturing |
| Campaign Lift | `domain_tools.campaign_lift` | Marketing |
| Attribution Model | `domain_tools.attribution_model` | Marketing |

## ML Algorithms (20+)

### Classification
Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost, SVM, K-Nearest Neighbors, Gradient Boosting, Extra Trees, Neural Network (MLP), Naive Bayes, Decision Tree

### Regression
Linear Regression, Ridge, Lasso, ElasticNet, Random Forest Regressor, XGBoost Regressor, LightGBM Regressor, SVR, Gradient Boosting Regressor

### Clustering
K-Means, DBSCAN, Hierarchical (Agglomerative), Gaussian Mixture

## Registry Structure

Each entry follows this schema:

```python
{
    "name": "Human-readable name",
    "function": "module.path.function_name",
    "description": "What it does",
    "when_to_use": "Conditions for selection",
    "requirements": {
        "min_columns": 2,
        "column_types": ["numeric", "binary"]
    },
    "domains": ["all"],  # or specific domains
    "parameters": {"param": "description"},
    "output": {"key": "description"}
}
```

Agents query the registry via `search_tools(query)` and `get_tools_for_domain(domain)`.
