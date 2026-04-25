"""Generic domain configuration -- fallback when no specific domain is detected."""

from domains.base_domain import BaseDomainConfig


class GenericDomainConfig(BaseDomainConfig):
    """Generic domain config with standard data science practices."""

    @property
    def domain_name(self) -> str:
        return "generic"

    @property
    def display_name(self) -> str:
        return "General Data Science"

    @property
    def icon(self) -> str:
        return "📊"

    @property
    def detection_keywords(self) -> dict[str, list[str]]:
        return {"strong": [], "moderate": [], "weak": []}

    @property
    def primary_metrics(self) -> dict[str, list[str]]:
        return {
            "classification": ["accuracy", "precision", "recall", "f1", "auc_roc"],
            "regression": ["rmse", "mae", "r2", "mape"],
            "clustering": ["silhouette_score", "calinski_harabasz"],
            "time_series": ["rmse", "mae", "mape"],
        }

    @property
    def terminology_map(self) -> dict[str, str]:
        return {
            "user": "record",
            "prediction": "prediction",
            "positive_class": "positive class",
            "feature": "feature",
        }

    def get_eda_questions(self, schema_info: dict) -> list[dict]:
        return [
            {
                "id": "generic_eda_q1",
                "step": "eda",
                "question": "What is your primary analysis goal?",
                "type": "single_select",
                "options": [
                    {"value": "understand_target", "label": "Understand what drives the target variable", "recommended": True},
                    {"value": "relationships", "label": "Explore relationships between features"},
                    {"value": "quality", "label": "Deep data quality investigation"},
                    {"value": "segments", "label": "Find natural segments or clusters"},
                    {"value": "comprehensive", "label": "Comprehensive analysis (all of the above)"},
                ],
                "recommendation_reason": "Understanding target drivers is the most actionable analysis for predictive modeling.",
                "domain_specific": False,
            },
            {
                "id": "generic_eda_q2",
                "step": "eda",
                "question": "Which distribution checks should we run?",
                "type": "multi_select",
                "options": [
                    {"value": "histograms", "label": "Histograms for All Numeric Columns", "recommended": True},
                    {"value": "normality", "label": "Normality Tests (Shapiro-Wilk)"},
                    {"value": "outliers", "label": "Outlier Detection (IQR / Z-score)", "recommended": True},
                    {"value": "cardinality", "label": "Cardinality Analysis for Categoricals"},
                ],
                "recommendation_reason": "Histograms and outlier detection provide the fastest overview of data quality issues.",
                "domain_specific": False,
            },
            {
                "id": "generic_eda_q3",
                "step": "eda",
                "question": "Which correlation/association analyses should we run?",
                "type": "multi_select",
                "options": [
                    {"value": "pearson", "label": "Pearson Correlation Matrix", "recommended": True},
                    {"value": "spearman", "label": "Spearman Rank Correlation"},
                    {"value": "cramers_v", "label": "Cramer's V for Categorical Associations"},
                    {"value": "mutual_info", "label": "Mutual Information Scores"},
                ],
                "recommendation_reason": "Pearson correlation is the standard starting point for identifying linear relationships.",
                "domain_specific": False,
            },
            {
                "id": "generic_eda_q4",
                "step": "eda",
                "question": "Analyze missing data patterns?",
                "type": "single_select",
                "options": [
                    {"value": "summary", "label": "Missing Value Summary Table", "recommended": True},
                    {"value": "patterns", "label": "Missing Data Pattern Analysis (MCAR/MAR/MNAR)"},
                    {"value": "skip", "label": "Skip missing data analysis"},
                ],
                "recommendation_reason": "A missing value summary is essential before any imputation or modeling decisions.",
                "domain_specific": False,
            },
        ]

    def get_feature_engineering_questions(self, schema_info: dict) -> list[dict]:
        return [
            {
                "id": "generic_fe_q1",
                "step": "feature_engineering",
                "question": "How should categorical variables be encoded?",
                "type": "single_select",
                "options": [
                    {"value": "auto", "label": "Auto-select based on cardinality", "recommended": True},
                    {"value": "one_hot", "label": "One-Hot Encoding (all categoricals)"},
                    {"value": "target", "label": "Target Encoding"},
                    {"value": "ordinal", "label": "Ordinal Encoding"},
                ],
                "recommendation_reason": "Auto-selection uses one-hot for low cardinality and target encoding for high cardinality, balancing interpretability and efficiency.",
                "domain_specific": False,
            },
            {
                "id": "generic_fe_q2",
                "step": "feature_engineering",
                "question": "How should numeric features be scaled?",
                "type": "single_select",
                "options": [
                    {"value": "standard", "label": "StandardScaler (zero mean, unit variance)", "recommended": True},
                    {"value": "minmax", "label": "MinMaxScaler (0-1 range)"},
                    {"value": "robust", "label": "RobustScaler (median/IQR, outlier-resistant)"},
                    {"value": "none", "label": "No scaling (tree-based models only)"},
                ],
                "recommendation_reason": "StandardScaler is the safest default for most algorithms.",
                "domain_specific": False,
            },
            {
                "id": "generic_fe_q3",
                "step": "feature_engineering",
                "question": "Feature selection approach?",
                "type": "single_select",
                "options": [
                    {"value": "auto", "label": "Automatic (remove low-variance + high-correlation)", "recommended": True},
                    {"value": "importance", "label": "Feature Importance Based (tree model)"},
                    {"value": "mutual_info", "label": "Mutual Information Selection"},
                    {"value": "none", "label": "Keep all features"},
                ],
                "recommendation_reason": "Automatic removal of low-variance and highly correlated features reduces noise without losing signal.",
                "domain_specific": False,
            },
        ]

    def get_model_questions(self, schema_info: dict, problem_type: str) -> list[dict]:
        return [
            {
                "id": "generic_model_q1",
                "step": "modeling",
                "question": "Which algorithms should we try?",
                "type": "multi_select",
                "options": [
                    {"value": "logistic_regression", "label": "Logistic Regression (interpretable baseline)"},
                    {"value": "random_forest", "label": "Random Forest", "recommended": True},
                    {"value": "gradient_boosting", "label": "Gradient Boosting (XGBoost/LightGBM)", "recommended": True},
                    {"value": "svm", "label": "Support Vector Machine"},
                    {"value": "automl", "label": "AutoML (FLAML -- try all algorithms)"},
                ],
                "recommendation_reason": "Random Forest and Gradient Boosting consistently perform well across diverse datasets.",
                "domain_specific": False,
            },
            {
                "id": "generic_model_q2",
                "step": "modeling",
                "question": "Validation strategy?",
                "type": "single_select",
                "options": [
                    {"value": "cv5", "label": "5-Fold Cross-Validation", "recommended": True},
                    {"value": "cv10", "label": "10-Fold Cross-Validation"},
                    {"value": "stratified", "label": "Stratified K-Fold (for imbalanced classes)"},
                    {"value": "holdout", "label": "Single Train/Test Split (80/20)"},
                    {"value": "time_series", "label": "Time-Series Split (if temporal data)"},
                ],
                "recommendation_reason": "5-fold CV provides a robust estimate of generalization performance with reasonable computation time.",
                "domain_specific": False,
            },
            {
                "id": "generic_model_q3",
                "step": "modeling",
                "question": "Which evaluation metric should be primary?",
                "type": "single_select",
                "options": [
                    {"value": "auto", "label": "Auto-select based on problem type", "recommended": True},
                    {"value": "accuracy", "label": "Accuracy"},
                    {"value": "f1", "label": "F1 Score"},
                    {"value": "auc_roc", "label": "AUC-ROC"},
                    {"value": "rmse", "label": "RMSE (regression)"},
                    {"value": "custom", "label": "Custom metric (I will specify)"},
                ],
                "recommendation_reason": "Auto-selection picks AUC-ROC for balanced classification, F1 for imbalanced, and RMSE for regression.",
                "domain_specific": False,
            },
        ]
