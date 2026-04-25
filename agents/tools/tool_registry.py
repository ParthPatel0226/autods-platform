"""Master registry of ALL available tools.

Every statistical test, visualization, feature technique, and ML algorithm
is registered here with metadata. This ensures the system never "forgets"
a technique — agents search this registry, not their own memory.

The registry structure:
- Each tool has: name, function path, description, when_to_use,
  requirements, domains, parameters, output format
- Tools are organized by category: statistical_tests, visualizations,
  feature_engineering, models
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


TOOL_REGISTRY = {
    # =================================================================
    # STATISTICAL TESTS
    # =================================================================
    "statistical_tests": {
        "t_test_independent": {
            "name": "Independent Samples T-Test",
            "function": "agents.tools.stats_tools.t_test_independent",
            "description": "Compare means of a continuous variable between two groups",
            "when_to_use": "Binary grouping variable + continuous outcome, approximately normal distributions",
            "domains": ["all"],
        },
        "t_test_paired": {
            "name": "Paired Samples T-Test",
            "function": "agents.tools.stats_tools.t_test_paired",
            "description": "Compare means of paired/matched observations",
            "when_to_use": "Pre-post measurements on the same subjects",
            "domains": ["all"],
        },
        "mann_whitney_u": {
            "name": "Mann-Whitney U Test",
            "function": "agents.tools.stats_tools.mann_whitney_u",
            "description": "Non-parametric comparison of two groups",
            "when_to_use": "Binary grouping + continuous outcome + non-normal data",
            "domains": ["all"],
        },
        "chi_square": {
            "name": "Chi-Square Test of Independence",
            "function": "agents.tools.stats_tools.chi_square_test",
            "description": "Test association between two categorical variables",
            "when_to_use": "Two categorical variables, expected cell counts >= 5",
            "domains": ["all"],
        },
        "fisher_exact": {
            "name": "Fisher's Exact Test",
            "function": "agents.tools.stats_tools.fisher_exact_test",
            "description": "Exact test for 2x2 contingency tables",
            "when_to_use": "2x2 table with small expected counts (<5)",
            "domains": ["all"],
        },
        "anova_oneway": {
            "name": "One-Way ANOVA",
            "function": "agents.tools.stats_tools.anova_oneway",
            "description": "Compare means across 3+ groups",
            "when_to_use": "Categorical grouping (3+ levels) + continuous outcome",
            "domains": ["all"],
        },
        "kruskal_wallis": {
            "name": "Kruskal-Wallis H Test",
            "function": "agents.tools.stats_tools.kruskal_wallis",
            "description": "Non-parametric comparison across 3+ groups",
            "when_to_use": "Categorical grouping (3+ levels) + non-normal continuous outcome",
            "domains": ["all"],
        },
        "shapiro_wilk": {
            "name": "Shapiro-Wilk Normality Test",
            "function": "agents.tools.stats_tools.shapiro_wilk",
            "description": "Test if data follows a normal distribution",
            "when_to_use": "Check normality assumption before parametric tests",
            "domains": ["all"],
        },
        "levene_test": {
            "name": "Levene's Test for Equal Variances",
            "function": "agents.tools.stats_tools.levene_test",
            "description": "Test if groups have equal variances",
            "when_to_use": "Check variance assumption before ANOVA/t-test",
            "domains": ["all"],
        },
        "correlation_pearson": {
            "name": "Pearson Correlation",
            "function": "agents.tools.stats_tools.correlation_pearson",
            "description": "Linear correlation between two continuous variables",
            "when_to_use": "Two continuous variables, linear relationship expected",
            "domains": ["all"],
        },
        "correlation_spearman": {
            "name": "Spearman Rank Correlation",
            "function": "agents.tools.stats_tools.correlation_spearman",
            "description": "Monotonic correlation between two variables",
            "when_to_use": "Ordinal data or non-linear monotonic relationships",
            "domains": ["all"],
        },
        "ks_test": {
            "name": "Kolmogorov-Smirnov Test",
            "function": "agents.tools.stats_tools.ks_test",
            "description": "Compare two distributions or test against theoretical distribution",
            "when_to_use": "Score distribution comparison, model discrimination assessment",
            "domains": ["finance", "all"],
        },
        "vif_test": {
            "name": "Variance Inflation Factor",
            "function": "agents.tools.stats_tools.vif_analysis",
            "description": "Detect multicollinearity among features",
            "when_to_use": "Before regression modeling, check feature independence",
            "domains": ["all"],
        },
        "kaplan_meier": {
            "name": "Kaplan-Meier Survival Analysis",
            "function": "agents.tools.stats_tools.kaplan_meier",
            "description": "Survival probability over time with censored data",
            "when_to_use": "Time-to-event data (readmission, failure, churn duration)",
            "domains": ["healthcare", "manufacturing", "hr"],
        },
        "cox_proportional_hazards": {
            "name": "Cox Proportional Hazards",
            "function": "agents.tools.stats_tools.cox_ph",
            "description": "Regression model for survival/time-to-event data",
            "when_to_use": "Identify risk factors for time-to-event outcomes",
            "domains": ["healthcare", "manufacturing"],
        },
    },

    # =================================================================
    # VISUALIZATIONS
    # =================================================================
    "visualizations": {
        "histogram": {"name": "Histogram", "function": "agents.tools.viz_tools.histogram", "domains": ["all"]},
        "box_plot": {"name": "Box Plot", "function": "agents.tools.viz_tools.box_plot", "domains": ["all"]},
        "violin_plot": {"name": "Violin Plot", "function": "agents.tools.viz_tools.violin_plot", "domains": ["all"]},
        "scatter_plot": {"name": "Scatter Plot", "function": "agents.tools.viz_tools.scatter_plot", "domains": ["all"]},
        "correlation_heatmap": {"name": "Correlation Heatmap", "function": "agents.tools.viz_tools.correlation_heatmap", "domains": ["all"]},
        "pair_plot": {"name": "Pair Plot", "function": "agents.tools.viz_tools.pair_plot", "domains": ["all"]},
        "bar_chart": {"name": "Bar Chart", "function": "agents.tools.viz_tools.bar_chart", "domains": ["all"]},
        "line_chart": {"name": "Line Chart", "function": "agents.tools.viz_tools.line_chart", "domains": ["all"]},
        "time_series_plot": {"name": "Time Series Plot", "function": "agents.tools.viz_tools.time_series_plot", "domains": ["all"]},
        "pie_chart": {"name": "Pie Chart", "function": "agents.tools.viz_tools.pie_chart", "domains": ["all"]},
        "heatmap": {"name": "Heatmap", "function": "agents.tools.viz_tools.heatmap", "domains": ["all"]},
        "qq_plot": {"name": "Q-Q Plot", "function": "agents.tools.viz_tools.qq_plot", "domains": ["all"]},
        "residual_plot": {"name": "Residual Plot", "function": "agents.tools.viz_tools.residual_plot", "domains": ["all"]},
        "confusion_matrix": {"name": "Confusion Matrix", "function": "agents.tools.viz_tools.confusion_matrix_plot", "domains": ["all"]},
        "roc_curve": {"name": "ROC Curve", "function": "agents.tools.viz_tools.roc_curve_plot", "domains": ["all"]},
        "precision_recall_curve": {"name": "Precision-Recall Curve", "function": "agents.tools.viz_tools.pr_curve_plot", "domains": ["all"]},
        "calibration_curve": {"name": "Calibration Curve", "function": "agents.tools.viz_tools.calibration_curve_plot", "domains": ["healthcare", "finance"]},
        "shap_summary": {"name": "SHAP Summary Plot", "function": "agents.tools.viz_tools.shap_summary_plot", "domains": ["all"]},
        "shap_force": {"name": "SHAP Force Plot", "function": "agents.tools.viz_tools.shap_force_plot", "domains": ["all"]},
        "feature_importance": {"name": "Feature Importance Chart", "function": "agents.tools.viz_tools.feature_importance_plot", "domains": ["all"]},
        "funnel_chart": {"name": "Funnel Chart", "function": "agents.tools.viz_tools.funnel_chart", "domains": ["ecommerce", "marketing"]},
        "cohort_retention": {"name": "Cohort Retention Heatmap", "function": "agents.tools.viz_tools.cohort_retention_plot", "domains": ["ecommerce", "hr"]},
        "survival_curve": {"name": "Survival Curve", "function": "agents.tools.viz_tools.survival_curve_plot", "domains": ["healthcare", "manufacturing"]},
        "gain_lift_chart": {"name": "Gain/Lift Chart", "function": "agents.tools.viz_tools.gain_lift_plot", "domains": ["finance", "marketing"]},
        "pdp_plot": {"name": "Partial Dependence Plot", "function": "agents.tools.viz_tools.pdp_plot", "domains": ["all"]},
    },

    # =================================================================
    # FEATURE ENGINEERING TECHNIQUES
    # =================================================================
    "feature_engineering": {
        "charlson_index": {"name": "Charlson Comorbidity Index", "domains": ["healthcare"]},
        "elixhauser_index": {"name": "Elixhauser Comorbidity Index", "domains": ["healthcare"]},
        "rfm_segmentation": {"name": "RFM Segmentation", "domains": ["ecommerce", "marketing"]},
        "velocity_features": {"name": "Transaction Velocity Features", "domains": ["finance"]},
        "ratio_features": {"name": "Financial Ratio Features", "domains": ["finance"]},
        "lag_features": {"name": "Lag Features", "domains": ["all"]},
        "rolling_features": {"name": "Rolling Window Statistics", "domains": ["all"]},
        "datetime_features": {"name": "DateTime Extraction", "domains": ["all"]},
        "text_tfidf": {"name": "TF-IDF Text Features", "domains": ["all"]},
        "text_sentiment": {"name": "Sentiment Score", "domains": ["all"]},
        "polynomial_features": {"name": "Polynomial Features", "domains": ["all"]},
        "interaction_features": {"name": "Feature Interactions", "domains": ["all"]},
        "binning": {"name": "Numeric Binning", "domains": ["all"]},
        "log_transform": {"name": "Log Transformation", "domains": ["all"]},
        "boxcox_transform": {"name": "Box-Cox Transformation", "domains": ["all"]},
        "target_encoding": {"name": "Target Encoding", "domains": ["all"]},
        "frequency_encoding": {"name": "Frequency Encoding", "domains": ["all"]},
    },

    # =================================================================
    # ML MODELS
    # =================================================================
    "models": {
        # Classification
        "logistic_regression": {"name": "Logistic Regression", "type": "classification", "domains": ["all"]},
        "random_forest_clf": {"name": "Random Forest Classifier", "type": "classification", "domains": ["all"]},
        "xgboost_clf": {"name": "XGBoost Classifier", "type": "classification", "domains": ["all"]},
        "lightgbm_clf": {"name": "LightGBM Classifier", "type": "classification", "domains": ["all"]},
        "catboost_clf": {"name": "CatBoost Classifier", "type": "classification", "domains": ["all"]},
        "svm_clf": {"name": "SVM Classifier", "type": "classification", "domains": ["all"]},
        "knn_clf": {"name": "KNN Classifier", "type": "classification", "domains": ["all"]},
        "decision_tree_clf": {"name": "Decision Tree Classifier", "type": "classification", "domains": ["all"]},
        # Regression
        "linear_regression": {"name": "Linear Regression", "type": "regression", "domains": ["all"]},
        "ridge_regression": {"name": "Ridge Regression", "type": "regression", "domains": ["all"]},
        "lasso_regression": {"name": "Lasso Regression", "type": "regression", "domains": ["all"]},
        "random_forest_reg": {"name": "Random Forest Regressor", "type": "regression", "domains": ["all"]},
        "xgboost_reg": {"name": "XGBoost Regressor", "type": "regression", "domains": ["all"]},
        "lightgbm_reg": {"name": "LightGBM Regressor", "type": "regression", "domains": ["all"]},
        # Clustering
        "kmeans": {"name": "K-Means Clustering", "type": "clustering", "domains": ["all"]},
        "dbscan": {"name": "DBSCAN Clustering", "type": "clustering", "domains": ["all"]},
        "hierarchical": {"name": "Hierarchical Clustering", "type": "clustering", "domains": ["all"]},
        # AutoML
        "flaml_auto": {"name": "FLAML AutoML", "type": "auto", "domains": ["all"]},
    },
}


def get_tools_for_domain(domain: str, category: str = None) -> dict:
    """Get all tools applicable to a specific domain.
    
    Args:
        domain: Domain name (e.g., "healthcare").
        category: Optional category filter (e.g., "statistical_tests").
        
    Returns:
        Filtered tool registry dict.
    """
    result = {}
    categories = [category] if category else TOOL_REGISTRY.keys()
    
    for cat in categories:
        if cat not in TOOL_REGISTRY:
            continue
        result[cat] = {}
        for tool_id, tool_info in TOOL_REGISTRY[cat].items():
            domains = tool_info.get("domains", ["all"])
            if "all" in domains or domain in domains:
                result[cat][tool_id] = tool_info
    
    return result


def search_tools(query: str, domain: str = "all") -> list[dict]:
    """Search the tool registry by keyword.
    
    Args:
        query: Search query (matches against name, description, when_to_use).
        domain: Filter by domain.
        
    Returns:
        List of matching tool dicts with category and tool_id added.
    """
    query_lower = query.lower()
    matches = []
    
    for category, tools in TOOL_REGISTRY.items():
        for tool_id, tool_info in tools.items():
            # Check domain
            domains = tool_info.get("domains", ["all"])
            if domain != "all" and "all" not in domains and domain not in domains:
                continue
            
            # Check keyword match
            searchable = " ".join([
                tool_info.get("name", ""),
                tool_info.get("description", ""),
                tool_info.get("when_to_use", ""),
            ]).lower()
            
            if query_lower in searchable:
                matches.append({
                    "category": category,
                    "tool_id": tool_id,
                    **tool_info,
                })
    
    return matches


def get_tool_function(function_path: str):
    """Import and return a tool function by its dotted path.
    
    Args:
        function_path: Dotted path like "agents.tools.stats_tools.t_test_independent"
        
    Returns:
        The callable function.
    """
    import importlib
    
    module_path, func_name = function_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)
