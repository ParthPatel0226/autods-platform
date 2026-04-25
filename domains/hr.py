"""HR / People Analytics domain configuration.

Covers: attrition prediction, compensation equity, performance analysis,
hiring funnel, diversity metrics, employee satisfaction.
"""
from domains.base_domain import BaseDomainConfig


class HRDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "hr"
    @property
    def display_name(self): return "Human Resources"
    @property
    def icon(self): return "👥"
    @property
    def detection_keywords(self):
        return {
            "strong": ["employee_id","department","hire_date","termination","attrition",
                       "salary","performance_rating","job_title","employee"],
            "moderate": ["tenure","manager","promotion","satisfaction","engagement_score",
                        "overtime","training","compensation","benefit"],
            "weak": ["name","age","gender","date","level"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["auc_roc","f1","precision","recall"],
                "regression": ["rmse","mae","r2"]}
    @property
    def fairness_config(self):
        return {"required": True, "protected_attributes": ["gender","race","age_group"], "metric": "demographic_parity"}
    @property
    def compliance_notes(self):
        return ["Sensitivity constraints: anonymize if group < 5 employees",
                "Do not expose individual compensation data",
                "Aggregate demographics to prevent identification"]
    @property
    def terminology_map(self):
        return {"user":"employee","prediction":"risk assessment","positive_class":"attrition","feature":"workforce variable"}

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "hr_eda_q1",
                "step": "eda",
                "question": "Which attrition drivers should we analyze?",
                "type": "multi_select",
                "options": [
                    {"value": "tenure", "label": "Tenure vs Attrition", "recommended": True},
                    {"value": "department", "label": "Department-Level Attrition Rates", "recommended": True},
                    {"value": "satisfaction", "label": "Satisfaction/Engagement Scores"},
                    {"value": "compensation", "label": "Compensation Relative to Market"},
                    {"value": "manager", "label": "Manager Effect on Attrition"},
                ],
                "recommendation_reason": "Tenure and department are the most commonly available and actionable attrition predictors.",
                "domain_specific": True,
            },
            {
                "id": "hr_eda_q2",
                "step": "eda",
                "question": "Run diversity and representation analysis?",
                "type": "multi_select",
                "options": [
                    {"value": "gender", "label": "Gender Representation", "recommended": True},
                    {"value": "race_ethnicity", "label": "Race/Ethnicity Representation"},
                    {"value": "age_distribution", "label": "Age Distribution"},
                    {"value": "leadership_diversity", "label": "Leadership Pipeline Diversity"},
                ],
                "recommendation_reason": "Gender representation is the most commonly reported diversity metric and is a good starting point.",
                "domain_specific": True,
            },
            {
                "id": "hr_eda_q3",
                "step": "eda",
                "question": "Analyze compensation equity?",
                "type": "single_select",
                "options": [
                    {"value": "raw_gap", "label": "Raw Pay Gap by Group", "recommended": True},
                    {"value": "adjusted_gap", "label": "Role-Adjusted Pay Gap"},
                    {"value": "both", "label": "Both Raw and Adjusted Analysis"},
                    {"value": "skip", "label": "Skip compensation analysis"},
                ],
                "recommendation_reason": "Raw pay gap provides the headline number; adjusted gap reveals whether the gap is explained by role differences.",
                "domain_specific": True,
            },
            {
                "id": "hr_eda_q4",
                "step": "eda",
                "question": "Analyze performance rating patterns?",
                "type": "single_select",
                "options": [
                    {"value": "distribution", "label": "Rating Distribution by Department/Level", "recommended": True},
                    {"value": "equity", "label": "Rating Equity Across Demographics"},
                    {"value": "trend", "label": "Rating Trends Over Time"},
                    {"value": "skip", "label": "Skip performance analysis"},
                ],
                "recommendation_reason": "Rating distribution by department reveals calibration inconsistencies.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "hr_fe_q1",
                "step": "feature_engineering",
                "question": "Create tenure-based features?",
                "type": "multi_select",
                "options": [
                    {"value": "tenure_years", "label": "Tenure in Years", "recommended": True},
                    {"value": "tenure_bucket", "label": "Tenure Buckets (0-1yr, 1-3yr, 3-5yr, 5+yr)"},
                    {"value": "is_new_hire", "label": "New Hire Flag (<6 months)"},
                    {"value": "time_since_promotion", "label": "Time Since Last Promotion"},
                ],
                "recommendation_reason": "Tenure in years is the most predictive single feature for attrition in most HR datasets.",
                "domain_specific": True,
            },
            {
                "id": "hr_fe_q2",
                "step": "feature_engineering",
                "question": "Create performance trajectory features?",
                "type": "multi_select",
                "options": [
                    {"value": "rating_trend", "label": "Rating Trend (improving/declining/stable)"},
                    {"value": "promotion_rate", "label": "Promotion Rate (promotions per year of tenure)"},
                    {"value": "rating_vs_dept", "label": "Rating vs Department Average"},
                ],
                "recommendation_reason": "Performance trajectory captures career momentum, which is a leading indicator of attrition.",
                "domain_specific": True,
            },
            {
                "id": "hr_fe_q3",
                "step": "feature_engineering",
                "question": "How should department be encoded?",
                "type": "single_select",
                "options": [
                    {"value": "target_encoding", "label": "Target Encoding (department attrition rate)", "recommended": True},
                    {"value": "one_hot", "label": "One-Hot Encoding"},
                    {"value": "ordinal", "label": "Ordinal by Department Size"},
                ],
                "recommendation_reason": "Target encoding captures the department-level attrition signal without creating many sparse columns.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "hr_model_q1",
                "step": "modeling",
                "question": "Which fairness constraints should the model enforce?",
                "type": "multi_select",
                "options": [
                    {"value": "gender", "label": "Gender Parity", "recommended": True},
                    {"value": "race", "label": "Racial Equity", "recommended": True},
                    {"value": "age", "label": "Age Non-Discrimination"},
                    {"value": "none", "label": "No fairness constraints"},
                ],
                "recommendation_reason": "Gender and racial equity constraints are legally mandated in many jurisdictions for employment decisions.",
                "domain_specific": True,
            },
            {
                "id": "hr_model_q2",
                "step": "modeling",
                "question": "How important is model interpretability?",
                "type": "single_select",
                "options": [
                    {"value": "high", "label": "High -- HR must explain predictions to managers", "recommended": True},
                    {"value": "moderate", "label": "Moderate -- global feature importance is sufficient"},
                    {"value": "low", "label": "Low -- accuracy is the priority"},
                ],
                "recommendation_reason": "HR stakeholders and managers typically require clear explanations to act on model predictions.",
                "domain_specific": True,
            },
            {
                "id": "hr_model_q3",
                "step": "modeling",
                "question": "Should individual-level results be anonymized?",
                "type": "single_select",
                "options": [
                    {"value": "aggregate_only", "label": "Show aggregate results only (team/department level)", "recommended": True},
                    {"value": "individual_restricted", "label": "Individual results restricted to HR leadership"},
                    {"value": "full_access", "label": "Full individual-level access"},
                ],
                "recommendation_reason": "Aggregate-only output prevents identification of individuals and is the safest default for privacy.",
                "domain_specific": True,
            },
        ]
