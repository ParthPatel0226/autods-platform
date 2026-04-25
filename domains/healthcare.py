"""Healthcare domain configuration.

Covers: hospital readmission, mortality, clinical risk, patient outcomes,
clinical trials, claims data. Includes ICD handling, survival analysis,
fairness auditing, HIPAA awareness, and clinical report terminology.
"""
from domains.base_domain import BaseDomainConfig


class HealthcareDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "healthcare"
    @property
    def display_name(self): return "Healthcare"
    @property
    def icon(self): return "🏥"
    @property
    def detection_keywords(self):
        return {
            "strong": ["patient_id","patient","diagnosis","icd","admission","discharge",
                       "readmission","readmitted","hemoglobin","creatinine","mortality",
                       "diagnosis_code","procedure_code","drg","ndc","los","length_of_stay",
                       "comorbidity","charlson"],
            "moderate": ["age","gender","sex","bmi","blood_pressure","heart_rate",
                        "medication","lab","vitals","insurance","payer","emergency",
                        "inpatient","outpatient","icu","surgery","clinical","hospital"],
            "weak": ["id","date","status","type","code","visit","encounter"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["sensitivity","specificity","auc_roc","ppv","npv","f1"],
                "regression": ["mae","rmse","r2"], "survival": ["concordance_index","brier_score"]}
    @property
    def default_cost_matrix(self): return {"false_negative": 10, "false_positive": 1}
    @property
    def fairness_config(self):
        return {"required": True, "protected_attributes": ["race","gender","age_group","insurance_type"], "metric": "equal_opportunity"}
    @property
    def compliance_notes(self):
        return ["Check for PHI (Protected Health Information)", "HIPAA considerations",
                "Model decisions must be explainable for clinical use", "Fairness analysis across demographics mandatory"]
    @property
    def terminology_map(self):
        return {"user":"patient","prediction":"risk assessment","positive_class":"event (readmission/mortality)","feature":"clinical variable"}
    @property
    def report_style(self): return "clinical"
    def get_special_encodings(self):
        return {"icd_codes":["charlson_index","elixhauser_index","ccs_category"],"cpt_codes":["procedure_grouper"]}

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "healthcare_eda_q1",
                "step": "eda",
                "question": "Which clinical outcomes should we analyze?",
                "type": "multi_select",
                "options": [
                    {"value": "readmission", "label": "30-day Readmission", "recommended": True},
                    {"value": "mortality", "label": "In-hospital Mortality"},
                    {"value": "los", "label": "Length of Stay"},
                    {"value": "complications", "label": "Post-operative Complications"},
                    {"value": "cost", "label": "Cost of Care"},
                ],
                "recommendation_reason": "Readmission analysis is the most common clinical quality metric and is directly tied to CMS penalties.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_eda_q2",
                "step": "eda",
                "question": "Which demographic breakdowns are relevant?",
                "type": "multi_select",
                "options": [
                    {"value": "age_group", "label": "Age Groups", "recommended": True},
                    {"value": "gender", "label": "Gender/Sex"},
                    {"value": "race_ethnicity", "label": "Race/Ethnicity", "recommended": True},
                    {"value": "insurance", "label": "Insurance/Payer Type"},
                    {"value": "geography", "label": "Geographic Region"},
                ],
                "recommendation_reason": "Age and race/ethnicity breakdowns are essential for fairness auditing and identifying health disparities.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_eda_q3",
                "step": "eda",
                "question": "Should we analyze comorbidity patterns?",
                "type": "single_select",
                "options": [
                    {"value": "charlson", "label": "Charlson Comorbidity Index", "recommended": True},
                    {"value": "elixhauser", "label": "Elixhauser Comorbidity Count"},
                    {"value": "both", "label": "Both Charlson and Elixhauser"},
                    {"value": "skip", "label": "Skip comorbidity analysis"},
                ],
                "recommendation_reason": "Charlson index is the standard comorbidity measure and is critical for risk adjustment.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_eda_q4",
                "step": "eda",
                "question": "Analyze temporal trends in outcomes?",
                "type": "single_select",
                "options": [
                    {"value": "monthly", "label": "Monthly Trend Analysis", "recommended": True},
                    {"value": "quarterly", "label": "Quarterly Trend Analysis"},
                    {"value": "yearly", "label": "Year-over-Year Comparison"},
                    {"value": "skip", "label": "Skip temporal analysis"},
                ],
                "recommendation_reason": "Monthly trends help identify seasonal patterns and quality improvement impacts.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_eda_q5",
                "step": "eda",
                "question": "Analyze insurance/payer impact on outcomes?",
                "type": "single_select",
                "options": [
                    {"value": "yes", "label": "Yes, compare outcomes by payer", "recommended": True},
                    {"value": "no", "label": "No, skip payer analysis"},
                ],
                "recommendation_reason": "Payer analysis reveals access-to-care disparities and informs value-based contracting.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "healthcare_fe_q1",
                "step": "feature_engineering",
                "question": "How should ICD diagnosis codes be encoded?",
                "type": "multi_select",
                "options": [
                    {"value": "charlson", "label": "Charlson Comorbidity Index", "recommended": True},
                    {"value": "elixhauser", "label": "Elixhauser Comorbidity Count"},
                    {"value": "ccs_category", "label": "CCS Category Grouping"},
                    {"value": "top_n_codes", "label": "Top-N Frequency Encoding"},
                ],
                "recommendation_reason": "Charlson index is clinically validated and compresses thousands of ICD codes into a single interpretable score.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_fe_q2",
                "step": "feature_engineering",
                "question": "Apply clinical threshold flags to lab values?",
                "type": "single_select",
                "options": [
                    {"value": "standard", "label": "Standard Clinical Ranges (e.g. hemoglobin < 12)", "recommended": True},
                    {"value": "custom", "label": "Custom Thresholds (I will specify)"},
                    {"value": "skip", "label": "Skip threshold flagging"},
                ],
                "recommendation_reason": "Standard clinical thresholds turn continuous labs into clinically meaningful binary indicators.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_fe_q3",
                "step": "feature_engineering",
                "question": "Create temporal admission features?",
                "type": "multi_select",
                "options": [
                    {"value": "prior_admissions", "label": "Prior Admissions Count", "recommended": True},
                    {"value": "days_since_last", "label": "Days Since Last Admission", "recommended": True},
                    {"value": "avg_los", "label": "Average Length of Stay"},
                    {"value": "weekend_admission", "label": "Weekend/Holiday Admission Flag"},
                ],
                "recommendation_reason": "Prior admission count and recency are strong predictors of readmission risk.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "healthcare_model_q1",
                "step": "modeling",
                "question": "How important is model interpretability for clinical use?",
                "type": "single_select",
                "options": [
                    {"value": "high", "label": "High -- must explain every prediction (logistic regression, decision tree)", "recommended": True},
                    {"value": "moderate", "label": "Moderate -- global explanations sufficient (gradient boosting + SHAP)"},
                    {"value": "low", "label": "Low -- accuracy is priority (any algorithm)"},
                ],
                "recommendation_reason": "Clinical decision support tools typically require high interpretability for regulatory and adoption reasons.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_model_q2",
                "step": "modeling",
                "question": "Enforce fairness constraints across demographic groups?",
                "type": "single_select",
                "options": [
                    {"value": "equal_opportunity", "label": "Equal Opportunity (equal TPR across groups)", "recommended": True},
                    {"value": "demographic_parity", "label": "Demographic Parity (equal positive rate)"},
                    {"value": "calibration", "label": "Calibration Equity (equal PPV across groups)"},
                    {"value": "none", "label": "No fairness constraints"},
                ],
                "recommendation_reason": "Equal opportunity ensures the model is equally sensitive across demographic groups, critical for equitable healthcare.",
                "domain_specific": True,
            },
            {
                "id": "healthcare_model_q3",
                "step": "modeling",
                "question": "How should the classification threshold be optimized?",
                "type": "single_select",
                "options": [
                    {"value": "sensitivity", "label": "Maximize Sensitivity (catch all events)", "recommended": True},
                    {"value": "youden", "label": "Youden's J (balance sensitivity and specificity)"},
                    {"value": "cost", "label": "Cost-based (10:1 FN:FP cost ratio)"},
                    {"value": "f1", "label": "Maximize F1 Score"},
                ],
                "recommendation_reason": "In clinical settings, missing a true event (false negative) is typically far more costly than a false alarm.",
                "domain_specific": True,
            },
        ]
