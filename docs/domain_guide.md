# Domain Guide

## How Domain Detection Works

AutoDS auto-detects the industry domain by analyzing column names against keyword lists. Each domain defines three tiers of indicators with weighted scoring:

| Tier | Weight | Examples (Healthcare) |
|------|--------|----------------------|
| Strong | 3x | patient_id, diagnosis, icd, admission, hemoglobin |
| Moderate | 2x | age, gender, bmi, blood_pressure, medication |
| Weak | 1x | id, date, status, type, code |

Detection threshold: 3+ strong matches OR 5+ moderate matches trigger domain assignment. Confidence score (0-1) reflects match quality. Users can override detection.

## Supported Domains

### Healthcare

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | patient_id, diagnosis, icd, admission, discharge, hemoglobin, creatinine |
| **Primary Metrics** | Sensitivity, Specificity, AUC, NPV, PPV |
| **Special Features** | Charlson/Elixhauser comorbidity indices, ICD grouping |
| **Fairness** | Required: race, gender, age_group, insurance_type |
| **Compliance** | HIPAA awareness, PHI detection, clinical explainability |
| **Cost Matrix** | FN=10 (missing sick patient), FP=1 (unnecessary follow-up) |
| **Report Style** | Clinical terminology: patient, risk assessment, clinical variable |

### Finance

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | transaction_amount, credit_score, loan_amount, default, delinquency |
| **Primary Metrics** | KS statistic, Gini coefficient, PSI |
| **Special Features** | Vintage analysis, scorecard output, cost-sensitive learning |
| **Fairness** | Fair lending compliance, adverse action codes |
| **Compliance** | Model risk management, adverse action notices |
| **Report Style** | Financial terminology: applicant, risk score, credit variable |

### E-commerce

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | product_id, cart_value, order_id, customer_id, purchase_amount |
| **Primary Metrics** | Conversion rate, CLV, AOV, churn rate |
| **Special Features** | RFM segmentation, basket analysis, cohort retention, funnel analysis |
| **Report Style** | Business terminology: customer, segment, conversion driver |

### Marketing

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | campaign_id, impressions, clicks, ctr, roas |
| **Primary Metrics** | CTR, ROAS, CPA, conversion rate |
| **Special Features** | Attribution models, campaign lift, A/B testing, channel analysis |

### HR

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | employee_id, department, tenure, salary, performance_rating |
| **Primary Metrics** | Attrition rate, diversity metrics, compensation equity |
| **Special Features** | Sensitivity constraints, anonymization requirements |
| **Fairness** | Required: gender, race, age_group |

### Manufacturing

| Aspect | Details |
|--------|---------|
| **Icon** | -- |
| **Key Columns** | sensor_id, defect_rate, machine_id, cycle_time, temperature |
| **Primary Metrics** | OEE, MTBF, yield, defect rate |
| **Special Features** | Predictive maintenance, SPC charts, anomaly detection |

### Generic (Fallback)

Used when no specific domain is detected. Applies standard data science best practices without domain-specific customizations. All standard metrics available.

## How Domains Affect the Pipeline

| Pipeline Step | Domain Influence |
|---------------|-----------------|
| EDA | Domain-specific questions, relevant statistical tests |
| Feature Engineering | Domain features (Charlson, RFM, OEE), encoding strategy |
| Modeling | Metric selection, cost matrix, algorithm recommendations |
| Explainability | Required fairness audit, adverse action (finance), clinical interpretability |
| Reports | Domain terminology, compliance sections, formatting |

## Adding a New Domain

1. Create `domains/your_domain.py` extending `BaseDomainConfig`
2. Define detection keywords (strong, moderate, weak)
3. Specify primary metrics per problem type
4. Add EDA, feature, and model questions for guided mode
5. Configure fairness requirements (if applicable)
6. Set report terminology mapping
7. The domain auto-registers via `domain_registry.py`

See `domains/base_domain.py` for the full interface and `domains/healthcare.py` for a complete example.
