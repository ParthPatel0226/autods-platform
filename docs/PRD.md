# Product Requirements Document (PRD)
# AutoDS — Autonomous Data Science Platform

**Version:** 1.0
**Author:** Parth
**Date:** 2026-04-22
**Status:** Active Development (Alpha)

---

## 1. Executive Summary

AutoDS is an autonomous, multi-agent data science platform that accepts any tabular dataset from any source, auto-detects the industry domain, and produces complete data analyst + data scientist level outputs — from exploratory analysis to deployed ML models — with full user control over every analytical decision.

**Core Value Proposition:** Eliminate the gap between raw data and actionable insights for organizations without dedicated data science teams, while giving experienced practitioners a turbo-charged workflow that respects their expertise.

---

## 2. Problem Statement

### The Gap

- **Non-technical teams** have data but lack skills to extract insights. They depend on overloaded data science teams or expensive consultants.
- **Data scientists** spend 60-80% of their time on repetitive pipeline work (cleaning, profiling, feature engineering) rather than domain-specific analysis.
- **Existing AutoML tools** (H2O, DataRobot, auto-sklearn) focus narrowly on model training — they skip EDA, ignore domain context, produce no business-ready reports, and offer no explainability.
- **No platform** adapts its analysis vocabulary, metrics, compliance checks, and report style to the user's industry domain automatically.

### What's Missing

| Capability | Traditional AutoML | AutoDS |
|---|---|---|
| Data ingestion from 30+ sources | No | Yes |
| Auto domain detection | No | Yes (6 domains + generic) |
| Interactive EDA with domain questions | No | Yes |
| Per-column feature engineering control | No | Yes |
| Domain-specific metrics (KS, Charlson, OEE) | No | Yes |
| SHAP + fairness + model cards | Partial | Full |
| Professional reports (HTML/PDF/notebook) | No | Yes |
| Post-analysis conversational interface | No | Yes |
| Human-in-the-loop at every step | No | Yes (3 modes) |

---

## 3. User Personas

### Persona 1: Business Analyst — "Maya"

- **Role:** Marketing analyst at a mid-size e-commerce company
- **Skills:** Excel power user, basic SQL, no Python
- **Goal:** Understand customer churn drivers and predict at-risk customers
- **Pain:** Waits 2-3 weeks for data science team to run analysis
- **Mode:** Guided (wants recommendations, makes decisions)

### Persona 2: Data Scientist — "Raj"

- **Role:** Senior data scientist at a healthcare organization
- **Skills:** Python, R, scikit-learn, deep ML knowledge
- **Goal:** Accelerate pipeline work to focus on domain-specific modeling
- **Pain:** Spends 60% of time on boilerplate data prep and reporting
- **Mode:** Expert (full control, uses as acceleration tool)

### Persona 3: Executive — "Sarah"

- **Role:** VP of Operations at a manufacturing firm
- **Skills:** No technical background, reads reports
- **Goal:** Get a 1-page executive summary of predictive maintenance analysis
- **Pain:** Can't interpret data science outputs without translation
- **Mode:** Auto (upload data, get results + executive summary)

### Persona 4: Student / Researcher — "Alex"

- **Role:** Graduate student in quantitative finance
- **Skills:** Statistics knowledge, learning Python
- **Goal:** Rapid prototyping of credit scoring models with proper evaluation
- **Pain:** Building pipelines from scratch for each dataset takes days
- **Mode:** Guided → Expert (learns from recommendations, then takes control)

---

## 4. User Stories

### Data Ingestion

- **US-01:** As a user, I can upload CSV, Excel, Parquet, JSON, XML, PDF tables, and compressed archives so that I can analyze data in any format I have.
- **US-02:** As a user, I can connect to PostgreSQL, MySQL, BigQuery, Snowflake, and Redshift databases so that I can analyze production data directly.
- **US-03:** As a user, I can pull data from REST APIs, Kaggle, HuggingFace, Google Sheets, and public data APIs (World Bank, FRED, Yahoo Finance) so that I can use external data without manual download.
- **US-04:** As a user, I can paste tabular data from my clipboard so that I can quickly analyze ad-hoc data.
- **US-05:** As a user, I can load and join multiple data sources with AI-suggested join keys so that I can combine related datasets.

### Domain Detection

- **US-06:** As a user, the system automatically detects my industry domain (Healthcare, Finance, E-commerce, Marketing, HR, Manufacturing) from column names so that analysis is domain-appropriate without manual configuration.
- **US-07:** As a user, I can override the detected domain or select a different one so that I maintain control over domain-specific behavior.

### Analysis Modes

- **US-08:** As a non-technical user, I can select "Auto" mode so that the system makes all analytical decisions and I just get results.
- **US-09:** As an intermediate user, I can select "Guided" mode so that the system recommends approaches and I choose from options at each step.
- **US-10:** As an expert user, I can select "Expert" mode so that I have full control over every parameter, algorithm, and configuration.

### Exploratory Data Analysis

- **US-11:** As a user, I get a complete data profile (schema, missing values, distributions, correlations, outliers) automatically.
- **US-12:** As a Guided/Expert user, I can answer domain-specific interactive questions (e.g., "Which clinical outcomes matter most?" for healthcare) that steer the analysis.
- **US-13:** As a user, I see 25+ chart types rendered interactively with Plotly, with export buttons.

### Feature Engineering

- **US-14:** As a user, I get domain-specific feature recommendations (RFM for e-commerce, Charlson index for healthcare, OEE for manufacturing).
- **US-15:** As a Guided/Expert user, I can make per-column decisions about encoding, imputation, scaling, and outlier handling via an interactive table.

### Modeling

- **US-16:** As a user, the system trains multiple models (logistic regression, random forest, XGBoost, LightGBM, CatBoost, FLAML auto) and compares them with domain-appropriate metrics.
- **US-17:** As a user, I see statistical model comparison (paired t-test, bootstrap CI) not just raw metric numbers.
- **US-18:** As a Guided/Expert user, I can choose which algorithms to try, validation strategy, and optimization metric.

### Explainability

- **US-19:** As a user, I get SHAP explanations (global feature importance + local prediction explanations) for the best model.
- **US-20:** As a user, I get fairness audits with disparate impact analysis when the domain requires it (healthcare, finance, HR).
- **US-21:** As a user, I get a standardized model card documenting the model's purpose, limitations, and performance.
- **US-22:** As a user, I can run "what-if" scenarios (change feature values, see prediction impact) interactively.

### Reports & Output

- **US-23:** As a user, I can download an interactive HTML report with embedded Plotly charts.
- **US-24:** As a user, I can download a print-ready PDF report.
- **US-25:** As a user, I can download a 1-page executive summary for stakeholders.
- **US-26:** As a user, I can download a runnable Jupyter notebook with all code and comments for reproducibility.
- **US-27:** As a user, I can download all outputs as a single ZIP package.

### Follow-Up & Predictions

- **US-28:** As a user, I can ask follow-up questions in natural language after the pipeline completes (e.g., "Show me churn by region", "Run a chi-square test on gender vs outcome").
- **US-29:** As a user, I can upload new data for batch predictions using the trained model.
- **US-30:** As a user, I can make single-row predictions with real-time explanations.

### Session Management

- **US-31:** As a user, I can save, resume, and compare analysis sessions so that I can iterate on my approach.

---

## 5. Functional Requirements

### FR-1: Data Ingestion

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | Support 9 file formats (CSV, Excel, Parquet, JSON, XML, PDF, SAS, STATA, SQLite) | P0 |
| FR-1.2 | Auto-detect delimiter, encoding, header row for CSV | P0 |
| FR-1.3 | Support 7 database connectors (Postgres, MySQL, SQL Server, DuckDB, BigQuery, Snowflake, Redshift) | P1 |
| FR-1.4 | Support 6 API connectors (REST, Kaggle, HuggingFace, Google Sheets, web scraping, public data) | P1 |
| FR-1.5 | Support 3 cloud storage connectors (S3, GCS, Azure Blob) | P2 |
| FR-1.6 | Multi-source loading with AI-suggested joins | P1 |
| FR-1.7 | Universal loader with smart format detection | P0 |

### FR-2: Domain Detection

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Detect 6 industry domains + generic fallback | P0 |
| FR-2.2 | Keyword-based detection with strong/moderate/weak indicators | P0 |
| FR-2.3 | User override capability | P0 |
| FR-2.4 | Domain config drives metrics, questions, features, reports, terminology | P0 |

### FR-3: Agent Pipeline

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | 8 specialized agents orchestrated via LangGraph StateGraph | P0 |
| FR-3.2 | Shared TypedDict state with full pipeline metadata | P0 |
| FR-3.3 | Conditional routing based on mode, domain, and data characteristics | P0 |
| FR-3.4 | Human-in-the-loop via LangGraph interrupt mechanism | P0 |
| FR-3.5 | Graceful error handling with per-agent fallback | P0 |
| FR-3.6 | Tool registry with 100+ registered techniques | P0 |

### FR-4: Analysis Capabilities

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | 20+ statistical tests (t-test, chi-square, ANOVA, KS, Mann-Whitney, etc.) | P0 |
| FR-4.2 | 25+ visualization types (scatter, box, heatmap, sunburst, etc.) | P0 |
| FR-4.3 | 50+ feature engineering techniques with domain tags | P0 |
| FR-4.4 | 20+ ML algorithms (sklearn, XGBoost, LightGBM, CatBoost, FLAML) | P0 |
| FR-4.5 | SHAP, PDP/ICE, counterfactual, what-if analysis | P0 |
| FR-4.6 | Fairness audit (disparate impact, equal opportunity, demographic parity) | P1 |

### FR-5: Output & Reporting

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Interactive HTML report with embedded charts | P0 |
| FR-5.2 | Print-ready PDF report via WeasyPrint | P0 |
| FR-5.3 | 1-page executive summary | P1 |
| FR-5.4 | Runnable Jupyter notebook export | P1 |
| FR-5.5 | Domain-specific report templates and terminology | P0 |
| FR-5.6 | ZIP package with all outputs | P1 |

---

## 6. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | Pipeline completes on 100K-row dataset | < 10 minutes |
| Performance | Dashboard page load time | < 3 seconds |
| Scalability | Maximum dataset size (via DuckDB) | 10M+ rows |
| Reliability | Pipeline crash recovery via checkpointing | Session resumable |
| Security | No data leaves local environment (except LLM API calls) | Enforced |
| Security | HIPAA-aware column flagging for healthcare domain | Implemented |
| Cost | Claude API cost tracking per pipeline run | Visible in dashboard |
| Reproducibility | Deterministic results with same seed + data | Guaranteed |
| Observability | Structured JSON logging for all agent decisions | Full audit trail |
| Observability | MLflow experiment tracking for all model runs | Integrated |
| Portability | Deploy on Streamlit Cloud, HuggingFace Spaces, Docker | Supported |
| Testing | Code coverage on tool functions | >= 80% |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Domain accuracy | >= 90% correct domain detection | Benchmark on 20+ datasets |
| Model quality | Within 5% of hand-tuned models | Compare AutoDS vs manual on 8+ datasets |
| Pipeline completion rate | >= 95% (no crashes on valid data) | Integration test suite |
| User satisfaction | System Usability Scale >= 70 | User testing |
| Time savings | 10x faster than manual pipeline | Timed comparison |
| Report usefulness | Stakeholders can act on results without data scientist | User feedback |

---

## 8. Out of Scope (v1.0)

- Deep learning / neural network training
- Real-time streaming data analysis
- Natural language / unstructured text as primary input
- Image or video data analysis
- Multi-tenant SaaS deployment with user accounts
- Custom domain creation via UI (requires code)
- GPU-accelerated training
- Automated feature store integration
- AutoML neural architecture search

---

## 9. Technical Constraints

- **LLM Dependency:** Claude API required for agent decision-making. Graceful degradation with template fallbacks if API unavailable.
- **Python 3.11+:** Required for TypedDict and modern type hint features.
- **Local-first:** Data stays local. Only LLM prompts (no raw data) sent to Claude API.
- **DuckDB for compute:** All tabular operations run through DuckDB for performance on large datasets.

---

## 10. Implementation Phases

### Phase 1: Foundation (MVP)
Core pipeline: CSV upload → domain detection → profiling → EDA → basic modeling → results display. Single user mode (Auto). Generic domain only.

### Phase 2: Core Agents
All 8 agents functional. Three user modes. Interactive questions. Tool registry complete. 6 domain configs.

### Phase 3: Domain Intelligence
Full domain-specific behavior. Healthcare fairness, finance KS/Gini, e-commerce RFM. Domain-specific report templates.

### Phase 4: Explainability & Reports
SHAP, fairness audit, model cards, counterfactuals. HTML/PDF/notebook report generation.

### Phase 5: Advanced Features
Follow-up chat, deployment agent, full validation suite, session management, additional connectors.

### Phase 6: Polish
Complete test suite (80%+ coverage), benchmarks on 8+ datasets, documentation, deployment guides, demo GIF.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Claude API latency / cost | Pipeline slow or expensive | Batch LLM calls, cache responses, token tracking, graceful degradation |
| Domain detection inaccuracy | Wrong metrics/features applied | User override, confidence scoring, fallback to generic |
| Edge case data (single class, leakage) | Pipeline crashes or bad results | Edge case detector with 10+ checks before modeling |
| Large dataset memory limits | OOM on big data | DuckDB handles compute, streaming for profiling |
| Security (user uploads malicious files) | Code injection, data exfiltration | Input sanitizer, pickle scan, no eval/exec on user data |

---

## 12. Dependencies

| Component | Dependency | Risk Level |
|---|---|---|
| LLM | Anthropic Claude API | Medium (API availability) |
| Agent Framework | LangGraph | Low (stable, actively maintained) |
| Data Engine | DuckDB | Low (embedded, no server needed) |
| Dashboard | Streamlit | Low (stable, widely used) |
| ML | scikit-learn + XGBoost + LightGBM | Low (industry standard) |
| Explainability | SHAP + Fairlearn | Low (established libraries) |
| Reports | Jinja2 + WeasyPrint | Low (mature tools) |
| Experiment Tracking | MLflow | Low (standard tool) |
