"""Finance domain configuration.

Covers: credit risk, fraud detection, trading, insurance claims, revenue.
Includes KS/Gini metrics, adverse action codes, scorecard output,
fair lending compliance, and financial report terminology.
"""
from domains.base_domain import BaseDomainConfig


class FinanceDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "finance"
    @property
    def display_name(self): return "Finance"
    @property
    def icon(self): return "💰"
    @property
    def detection_keywords(self):
        return {
            "strong": ["transaction_amount","credit_score","account_balance","default",
                       "delinquency","fraud","loan","credit_limit","interest_rate","payment",
                       "fico","bureau","underwriting"],
            "moderate": ["amount","balance","account","merchant","currency","risk","score",
                        "income","debt","apr","fee","credit","debit"],
            "weak": ["id","date","status","type"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["ks_statistic","gini_coefficient","auc_roc","precision","recall"],
                "regression": ["rmse","mae","r2"]}
    @property
    def default_cost_matrix(self): return {"false_negative": 100, "false_positive": 1}
    @property
    def compliance_notes(self):
        return ["Fair lending regulations (ECOA, FCRA)", "Adverse action reason codes may be required",
                "Check for disparate impact on protected classes"]
    @property
    def terminology_map(self):
        return {"user":"applicant","prediction":"risk score","positive_class":"default/fraud","feature":"risk factor"}
    @property
    def report_style(self): return "financial"

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "finance_eda_q1",
                "step": "eda",
                "question": "What default/delinquency patterns should we explore?",
                "type": "multi_select",
                "options": [
                    {"value": "default_rate", "label": "Overall Default Rate by Segment", "recommended": True},
                    {"value": "delinquency_roll", "label": "Delinquency Roll Rate Analysis"},
                    {"value": "time_to_default", "label": "Time-to-Default Distribution"},
                    {"value": "loss_severity", "label": "Loss Given Default Distribution"},
                ],
                "recommendation_reason": "Default rate by segment is the foundational analysis for credit risk modeling.",
                "domain_specific": True,
            },
            {
                "id": "finance_eda_q2",
                "step": "eda",
                "question": "Analyze score and feature distributions?",
                "type": "multi_select",
                "options": [
                    {"value": "score_dist", "label": "Credit Score Distribution", "recommended": True},
                    {"value": "income_dist", "label": "Income Distribution"},
                    {"value": "dti_dist", "label": "Debt-to-Income Ratio Distribution"},
                    {"value": "utilization", "label": "Credit Utilization Distribution"},
                ],
                "recommendation_reason": "Score distributions reveal population shifts and inform binning strategies.",
                "domain_specific": True,
            },
            {
                "id": "finance_eda_q3",
                "step": "eda",
                "question": "Run vintage/cohort analysis?",
                "type": "single_select",
                "options": [
                    {"value": "monthly", "label": "Monthly Origination Vintages", "recommended": True},
                    {"value": "quarterly", "label": "Quarterly Origination Vintages"},
                    {"value": "skip", "label": "Skip vintage analysis"},
                ],
                "recommendation_reason": "Vintage analysis reveals whether recent originations perform differently from historical ones.",
                "domain_specific": True,
            },
            {
                "id": "finance_eda_q4",
                "step": "eda",
                "question": "Check Population Stability Index (PSI) across time periods?",
                "type": "single_select",
                "options": [
                    {"value": "yes", "label": "Yes, check PSI for key features", "recommended": True},
                    {"value": "no", "label": "No, skip PSI check"},
                ],
                "recommendation_reason": "PSI detects distributional drift that can degrade model performance over time.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "finance_fe_q1",
                "step": "feature_engineering",
                "question": "Create velocity/behavioral features?",
                "type": "multi_select",
                "options": [
                    {"value": "txn_velocity", "label": "Transaction Velocity (count/amount in windows)", "recommended": True},
                    {"value": "balance_change", "label": "Balance Change Ratios"},
                    {"value": "payment_patterns", "label": "Payment Pattern Features (on-time %, avg days late)"},
                    {"value": "utilization_trend", "label": "Utilization Trend (3m, 6m, 12m)"},
                ],
                "recommendation_reason": "Velocity features capture behavioral changes that are strong predictors of default.",
                "domain_specific": True,
            },
            {
                "id": "finance_fe_q2",
                "step": "feature_engineering",
                "question": "Create financial ratio features?",
                "type": "multi_select",
                "options": [
                    {"value": "dti", "label": "Debt-to-Income Ratio", "recommended": True},
                    {"value": "ltv", "label": "Loan-to-Value Ratio"},
                    {"value": "payment_income", "label": "Payment-to-Income Ratio"},
                    {"value": "utilization", "label": "Credit Utilization Ratio", "recommended": True},
                ],
                "recommendation_reason": "DTI and utilization are regulatory-standard risk factors used in virtually all credit models.",
                "domain_specific": True,
            },
            {
                "id": "finance_fe_q3",
                "step": "feature_engineering",
                "question": "Apply Weight of Evidence (WoE) binning?",
                "type": "single_select",
                "options": [
                    {"value": "auto", "label": "Auto-bin continuous features with WoE", "recommended": True},
                    {"value": "manual", "label": "Manual bin specification"},
                    {"value": "skip", "label": "Skip WoE binning"},
                ],
                "recommendation_reason": "WoE binning creates monotonic, interpretable features required for regulatory scorecards.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "finance_model_q1",
                "step": "modeling",
                "question": "What KS/Gini targets should the model achieve?",
                "type": "single_select",
                "options": [
                    {"value": "high", "label": "KS > 40, Gini > 60 (strong discrimination)", "recommended": True},
                    {"value": "moderate", "label": "KS > 30, Gini > 45 (acceptable)"},
                    {"value": "any", "label": "No specific KS/Gini target"},
                ],
                "recommendation_reason": "Industry standard for production credit models is KS > 40 and Gini > 60.",
                "domain_specific": True,
            },
            {
                "id": "finance_model_q2",
                "step": "modeling",
                "question": "Output format for the final model?",
                "type": "single_select",
                "options": [
                    {"value": "scorecard", "label": "Points-based Scorecard (logistic regression)", "recommended": True},
                    {"value": "probability", "label": "Probability Score (any algorithm)"},
                    {"value": "both", "label": "Both scorecard and ML probability"},
                ],
                "recommendation_reason": "Points-based scorecards are the regulatory standard and are required for adverse action code generation.",
                "domain_specific": True,
            },
            {
                "id": "finance_model_q3",
                "step": "modeling",
                "question": "Regulatory and compliance requirements?",
                "type": "multi_select",
                "options": [
                    {"value": "adverse_action", "label": "Adverse Action Reason Codes", "recommended": True},
                    {"value": "fair_lending", "label": "Fair Lending / Disparate Impact Testing", "recommended": True},
                    {"value": "model_documentation", "label": "Full Model Documentation (SR 11-7)"},
                    {"value": "none", "label": "No specific regulatory requirements"},
                ],
                "recommendation_reason": "Adverse action codes and fair lending testing are legally required for most consumer credit decisions.",
                "domain_specific": True,
            },
        ]
