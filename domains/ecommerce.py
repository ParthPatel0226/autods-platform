"""E-commerce domain configuration.

Covers: churn prediction, CLV, recommendation, demand forecasting,
basket analysis, funnel optimization, cohort retention.
"""
from domains.base_domain import BaseDomainConfig


class EcommerceDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "ecommerce"
    @property
    def display_name(self): return "E-commerce"
    @property
    def icon(self): return "🛒"
    @property
    def detection_keywords(self):
        return {
            "strong": ["product_id","cart_value","order_id","purchase","add_to_cart",
                       "checkout","sku","customer_id","session_id","shopping"],
            "moderate": ["price","quantity","category","brand","discount","shipping",
                        "return","review","rating","wishlist","browse"],
            "weak": ["id","date","name","value","item"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["f1","precision","recall","auc_roc"],
                "regression": ["rmse","mae","mape"]}
    @property
    def terminology_map(self):
        return {"user":"customer","prediction":"prediction","positive_class":"churn/conversion","feature":"behavioral variable"}

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "ecommerce_eda_q1",
                "step": "eda",
                "question": "Which customer segmentation analysis should we run?",
                "type": "multi_select",
                "options": [
                    {"value": "rfm", "label": "RFM Segmentation (Recency, Frequency, Monetary)", "recommended": True},
                    {"value": "behavioral", "label": "Behavioral Segments (browsing patterns)"},
                    {"value": "demographic", "label": "Demographic Segments"},
                    {"value": "value_tiers", "label": "Customer Value Tiers (CLV-based)"},
                ],
                "recommendation_reason": "RFM segmentation is the standard first step for understanding customer value distribution.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_eda_q2",
                "step": "eda",
                "question": "Analyze cohort retention over time?",
                "type": "single_select",
                "options": [
                    {"value": "monthly", "label": "Monthly Cohort Retention", "recommended": True},
                    {"value": "weekly", "label": "Weekly Cohort Retention"},
                    {"value": "skip", "label": "Skip cohort analysis"},
                ],
                "recommendation_reason": "Monthly cohort retention reveals customer lifecycle patterns and identifies retention drop-off points.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_eda_q3",
                "step": "eda",
                "question": "Run conversion funnel analysis?",
                "type": "single_select",
                "options": [
                    {"value": "full_funnel", "label": "Full Funnel (visit -> cart -> checkout -> purchase)", "recommended": True},
                    {"value": "checkout_only", "label": "Checkout Funnel Only"},
                    {"value": "skip", "label": "Skip funnel analysis"},
                ],
                "recommendation_reason": "Full funnel analysis identifies the largest drop-off points where optimization has the highest ROI.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_eda_q4",
                "step": "eda",
                "question": "Analyze seasonal and temporal patterns?",
                "type": "multi_select",
                "options": [
                    {"value": "day_of_week", "label": "Day-of-Week Patterns", "recommended": True},
                    {"value": "monthly", "label": "Monthly Seasonality"},
                    {"value": "holiday", "label": "Holiday Impact Analysis"},
                    {"value": "hour_of_day", "label": "Hour-of-Day Patterns"},
                ],
                "recommendation_reason": "Day-of-week patterns are the most actionable temporal insight for marketing scheduling.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "ecommerce_fe_q1",
                "step": "feature_engineering",
                "question": "Create Customer Lifetime Value features?",
                "type": "multi_select",
                "options": [
                    {"value": "total_spend", "label": "Total Spend", "recommended": True},
                    {"value": "avg_order_value", "label": "Average Order Value", "recommended": True},
                    {"value": "purchase_frequency", "label": "Purchase Frequency"},
                    {"value": "clv_estimate", "label": "CLV Estimate (projected)"},
                ],
                "recommendation_reason": "Total spend and AOV are foundational features for any customer-level prediction model.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_fe_q2",
                "step": "feature_engineering",
                "question": "Create recency and engagement features?",
                "type": "multi_select",
                "options": [
                    {"value": "days_since_last", "label": "Days Since Last Purchase", "recommended": True},
                    {"value": "days_since_first", "label": "Days Since First Purchase"},
                    {"value": "purchase_gap", "label": "Average Purchase Gap (days)"},
                    {"value": "return_rate", "label": "Return Rate"},
                ],
                "recommendation_reason": "Days since last purchase is the single strongest predictor of churn in most e-commerce datasets.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_fe_q3",
                "step": "feature_engineering",
                "question": "Create basket/product features?",
                "type": "multi_select",
                "options": [
                    {"value": "basket_size", "label": "Average Basket Size (items per order)"},
                    {"value": "category_diversity", "label": "Category Diversity (unique categories purchased)"},
                    {"value": "discount_sensitivity", "label": "Discount Sensitivity (% orders with discount)"},
                ],
                "recommendation_reason": "Basket features capture purchasing behavior patterns.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "ecommerce_model_q1",
                "step": "modeling",
                "question": "Which business metrics should drive model selection?",
                "type": "multi_select",
                "options": [
                    {"value": "conversion_rate", "label": "Predicted Conversion Rate Accuracy"},
                    {"value": "roas", "label": "ROAS (Return on Ad Spend) Optimization"},
                    {"value": "ltv_accuracy", "label": "Customer LTV Prediction Accuracy", "recommended": True},
                    {"value": "churn_reduction", "label": "Churn Reduction Impact"},
                ],
                "recommendation_reason": "LTV accuracy directly impacts marketing spend allocation and customer retention strategy.",
                "domain_specific": True,
            },
            {
                "id": "ecommerce_model_q2",
                "step": "modeling",
                "question": "Customer segmentation approach?",
                "type": "single_select",
                "options": [
                    {"value": "rfm_based", "label": "RFM-Based Segments", "recommended": True},
                    {"value": "clustering", "label": "Unsupervised Clustering (K-Means/DBSCAN)"},
                    {"value": "rule_based", "label": "Rule-Based Tiers (business-defined)"},
                    {"value": "skip", "label": "No segmentation needed"},
                ],
                "recommendation_reason": "RFM-based segments are interpretable and directly actionable for marketing campaigns.",
                "domain_specific": True,
            },
        ]
