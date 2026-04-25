"""Manufacturing / IoT domain configuration.

Covers: predictive maintenance, quality control, anomaly detection,
OEE optimization, sensor data analysis, process control.
"""
from domains.base_domain import BaseDomainConfig


class ManufacturingDomainConfig(BaseDomainConfig):
    @property
    def domain_name(self): return "manufacturing"
    @property
    def display_name(self): return "Manufacturing"
    @property
    def icon(self): return "🏭"
    @property
    def detection_keywords(self):
        return {
            "strong": ["machine_id","sensor","defect","yield","oee","downtime",
                       "production_line","batch_id","equipment"],
            "moderate": ["temperature","pressure","vibration","cycle_time","quality",
                        "maintenance","failure","rpm","flow_rate","humidity"],
            "weak": ["timestamp","reading","value","measurement","unit"],
        }
    @property
    def primary_metrics(self):
        return {"classification": ["precision","recall","f1","auc_roc"],
                "regression": ["rmse","mae","r2"],
                "anomaly_detection": ["precision","recall","f1"]}
    @property
    def terminology_map(self):
        return {"user":"equipment","prediction":"failure prediction","positive_class":"failure/defect","feature":"process parameter"}

    def get_eda_questions(self, schema_info):
        return [
            {
                "id": "manufacturing_eda_q1",
                "step": "eda",
                "question": "Run Overall Equipment Effectiveness (OEE) analysis?",
                "type": "single_select",
                "options": [
                    {"value": "full_oee", "label": "Full OEE Breakdown (Availability x Performance x Quality)", "recommended": True},
                    {"value": "availability_only", "label": "Availability Analysis Only"},
                    {"value": "quality_only", "label": "Quality Yield Analysis Only"},
                    {"value": "skip", "label": "Skip OEE analysis"},
                ],
                "recommendation_reason": "OEE provides a single metric that captures the three major sources of manufacturing loss.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_eda_q2",
                "step": "eda",
                "question": "Analyze failure/downtime patterns?",
                "type": "multi_select",
                "options": [
                    {"value": "mtbf_mttr", "label": "MTBF and MTTR Analysis", "recommended": True},
                    {"value": "failure_mode", "label": "Failure Mode Distribution"},
                    {"value": "time_pattern", "label": "Failure Time-of-Day/Week Patterns"},
                    {"value": "machine_comparison", "label": "Machine-to-Machine Comparison"},
                ],
                "recommendation_reason": "MTBF/MTTR quantifies reliability and maintainability, the two pillars of maintenance strategy.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_eda_q3",
                "step": "eda",
                "question": "Analyze quality and defect trends?",
                "type": "multi_select",
                "options": [
                    {"value": "spc_charts", "label": "SPC Control Charts", "recommended": True},
                    {"value": "defect_pareto", "label": "Defect Pareto Analysis"},
                    {"value": "batch_quality", "label": "Batch-to-Batch Quality Variation"},
                    {"value": "process_capability", "label": "Process Capability (Cp/Cpk)"},
                ],
                "recommendation_reason": "SPC control charts are the foundational quality tool for identifying process instability.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_eda_q4",
                "step": "eda",
                "question": "Analyze sensor reading distributions?",
                "type": "single_select",
                "options": [
                    {"value": "distributions", "label": "Sensor Value Distributions and Outliers", "recommended": True},
                    {"value": "correlations", "label": "Sensor Cross-Correlations"},
                    {"value": "both", "label": "Both Distributions and Correlations"},
                    {"value": "skip", "label": "Skip sensor analysis"},
                ],
                "recommendation_reason": "Understanding sensor distributions helps identify abnormal operating conditions before they cause failures.",
                "domain_specific": True,
            },
        ]

    def get_feature_engineering_questions(self, schema_info):
        return [
            {
                "id": "manufacturing_fe_q1",
                "step": "feature_engineering",
                "question": "Create sensor aggregation features?",
                "type": "multi_select",
                "options": [
                    {"value": "rolling_stats", "label": "Rolling Mean/Std/Min/Max (1h, 6h, 24h windows)", "recommended": True},
                    {"value": "rate_of_change", "label": "Rate of Change (first derivative)"},
                    {"value": "fft_features", "label": "Frequency Domain Features (FFT peaks)"},
                    {"value": "quantile_features", "label": "Quantile Features (10th, 25th, 75th, 90th)"},
                ],
                "recommendation_reason": "Rolling statistics capture gradual degradation patterns that precede equipment failures.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_fe_q2",
                "step": "feature_engineering",
                "question": "Create time-since-event features?",
                "type": "multi_select",
                "options": [
                    {"value": "time_since_maintenance", "label": "Time Since Last Maintenance", "recommended": True},
                    {"value": "time_since_failure", "label": "Time Since Last Failure"},
                    {"value": "cycles_since_maintenance", "label": "Cycles Since Last Maintenance"},
                    {"value": "cumulative_runtime", "label": "Cumulative Runtime Hours"},
                ],
                "recommendation_reason": "Time since last maintenance is a primary input to any predictive maintenance model.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_fe_q3",
                "step": "feature_engineering",
                "question": "Create SPC-based features?",
                "type": "single_select",
                "options": [
                    {"value": "control_limit_flags", "label": "Out-of-Control Limit Flags", "recommended": True},
                    {"value": "zone_violations", "label": "Western Electric Zone Rule Violations"},
                    {"value": "skip", "label": "Skip SPC features"},
                ],
                "recommendation_reason": "Control limit flags provide binary indicators of process instability that are directly actionable.",
                "domain_specific": True,
            },
        ]

    def get_model_questions(self, schema_info, problem_type):
        return [
            {
                "id": "manufacturing_model_q1",
                "step": "modeling",
                "question": "What is the predictive maintenance prediction horizon?",
                "type": "single_select",
                "options": [
                    {"value": "1h", "label": "1 Hour Ahead (real-time alerting)"},
                    {"value": "24h", "label": "24 Hours Ahead (shift planning)", "recommended": True},
                    {"value": "7d", "label": "7 Days Ahead (maintenance scheduling)"},
                    {"value": "30d", "label": "30 Days Ahead (parts procurement)"},
                ],
                "recommendation_reason": "24-hour horizon balances prediction accuracy with enough lead time for maintenance planning.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_model_q2",
                "step": "modeling",
                "question": "Anomaly detection approach?",
                "type": "single_select",
                "options": [
                    {"value": "isolation_forest", "label": "Isolation Forest (unsupervised)", "recommended": True},
                    {"value": "autoencoder", "label": "Autoencoder Reconstruction Error"},
                    {"value": "statistical", "label": "Statistical (Mahalanobis distance)"},
                    {"value": "supervised", "label": "Supervised Classification (if labeled failures available)"},
                ],
                "recommendation_reason": "Isolation Forest works well with mixed feature types and does not require labeled failure data.",
                "domain_specific": True,
            },
            {
                "id": "manufacturing_model_q3",
                "step": "modeling",
                "question": "How should false alarms be handled?",
                "type": "single_select",
                "options": [
                    {"value": "high_precision", "label": "Minimize False Alarms (high precision)"},
                    {"value": "high_recall", "label": "Catch All Failures (high recall)", "recommended": True},
                    {"value": "balanced", "label": "Balance Precision and Recall"},
                ],
                "recommendation_reason": "Missing a failure typically costs far more than investigating a false alarm in manufacturing.",
                "domain_specific": True,
            },
        ]
