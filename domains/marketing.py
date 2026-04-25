"""Marketing domain configuration.

Covers: campaign analysis, attribution, CTR/ROAS optimization,
audience segmentation, A/B testing, channel effectiveness.
"""
from domains.base_domain import BaseDomainConfig


class MarketingDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "marketing"
    @property
    def display_name(self): return "Marketing"
    @property
    def icon(self): return "📢"
    @property
    def detection_keywords(self):
        return {
            "strong": ["campaign_id","impressions","clicks","conversions","ad_spend",
                       "ctr","cpc","roas","campaign"],
            "moderate": ["channel","audience","creative","landing_page","bounce_rate",
                        "engagement","reach","frequency"],
            "weak": ["date","source","medium","utm"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["auc_roc","precision","recall","f1"],
                "regression": ["rmse","mae","r2"]}
    @property
    def terminology_map(self):
        return {"user":"prospect","prediction":"response prediction","feature":"campaign variable"}

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "marketing_eda_q1",
                "step": "eda",
                "question": "Which campaign performance metrics should we analyze?",
                "type": "multi_select",
                "options": [
                    {"value": "ctr", "label": "Click-Through Rate (CTR)", "recommended": True},
                    {"value": "conversion_rate", "label": "Conversion Rate", "recommended": True},
                    {"value": "cpc", "label": "Cost Per Click (CPC)"},
                    {"value": "roas", "label": "Return on Ad Spend (ROAS)"},
                    {"value": "cpa", "label": "Cost Per Acquisition (CPA)"},
                ],
                "recommendation_reason": "CTR and conversion rate are the two most fundamental campaign performance indicators.",
                "domain_specific": True,
            },
            {
                "id": "marketing_eda_q2",
                "step": "eda",
                "question": "Analyze performance by channel?",
                "type": "multi_select",
                "options": [
                    {"value": "channel_comparison", "label": "Channel Performance Comparison", "recommended": True},
                    {"value": "channel_trend", "label": "Channel Performance Over Time"},
                    {"value": "channel_audience", "label": "Audience Overlap Across Channels"},
                ],
                "recommendation_reason": "Channel comparison reveals budget allocation opportunities.",
                "domain_specific": True,
            },
            {
                "id": "marketing_eda_q3",
                "step": "eda",
                "question": "Analyze A/B test results?",
                "type": "single_select",
                "options": [
                    {"value": "lift_analysis", "label": "Campaign Lift Analysis (treatment vs control)", "recommended": True},
                    {"value": "multi_variant", "label": "Multi-Variant Test Comparison"},
                    {"value": "skip", "label": "No A/B tests to analyze"},
                ],
                "recommendation_reason": "Lift analysis quantifies the true incremental impact of campaign treatments.",
                "domain_specific": True,
            },
            {
                "id": "marketing_eda_q4",
                "step": "eda",
                "question": "Analyze audience segmentation?",
                "type": "single_select",
                "options": [
                    {"value": "demographic", "label": "Demographic Segment Performance"},
                    {"value": "behavioral", "label": "Behavioral Segment Performance", "recommended": True},
                    {"value": "both", "label": "Both Demographic and Behavioral"},
                    {"value": "skip", "label": "Skip audience analysis"},
                ],
                "recommendation_reason": "Behavioral segments are more actionable for targeting optimization than demographics alone.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "marketing_fe_q1",
                "step": "feature_engineering",
                "question": "Create engagement and interaction features?",
                "type": "multi_select",
                "options": [
                    {"value": "engagement_rate", "label": "Engagement Rate Features", "recommended": True},
                    {"value": "recency", "label": "Recency of Last Interaction"},
                    {"value": "frequency", "label": "Interaction Frequency (sessions, clicks)"},
                    {"value": "depth", "label": "Session Depth (pages per session)"},
                ],
                "recommendation_reason": "Engagement rate features capture prospect interest level across touchpoints.",
                "domain_specific": True,
            },
            {
                "id": "marketing_fe_q2",
                "step": "feature_engineering",
                "question": "Create attribution features?",
                "type": "single_select",
                "options": [
                    {"value": "last_touch", "label": "Last-Touch Channel Attribution", "recommended": True},
                    {"value": "first_touch", "label": "First-Touch Channel Attribution"},
                    {"value": "multi_touch", "label": "Multi-Touch (linear weighting)"},
                    {"value": "skip", "label": "Skip attribution features"},
                ],
                "recommendation_reason": "Last-touch attribution is the simplest and most widely used starting point.",
                "domain_specific": True,
            },
            {
                "id": "marketing_fe_q3",
                "step": "feature_engineering",
                "question": "Apply time-decay weighting to interactions?",
                "type": "single_select",
                "options": [
                    {"value": "exponential", "label": "Exponential Decay (recent interactions weighted higher)", "recommended": True},
                    {"value": "linear", "label": "Linear Decay"},
                    {"value": "skip", "label": "No time-decay weighting"},
                ],
                "recommendation_reason": "Exponential decay gives higher weight to recent interactions, reflecting realistic customer attention.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "marketing_model_q1",
                "step": "modeling",
                "question": "Should we build an uplift model (treatment effect)?",
                "type": "single_select",
                "options": [
                    {"value": "yes", "label": "Yes, build uplift model to find persuadable customers", "recommended": True},
                    {"value": "response_only", "label": "No, standard response model only"},
                ],
                "recommendation_reason": "Uplift models identify customers who are incrementally influenced by marketing, avoiding wasted spend on those who would convert anyway.",
                "domain_specific": True,
            },
            {
                "id": "marketing_model_q2",
                "step": "modeling",
                "question": "Which attribution model should be used for evaluation?",
                "type": "single_select",
                "options": [
                    {"value": "last_touch", "label": "Last-Touch Attribution", "recommended": True},
                    {"value": "data_driven", "label": "Data-Driven Attribution (Shapley-based)"},
                    {"value": "position_based", "label": "Position-Based (40/20/40)"},
                ],
                "recommendation_reason": "Last-touch is the industry default and the easiest to validate before moving to complex models.",
                "domain_specific": True,
            },
        ]
