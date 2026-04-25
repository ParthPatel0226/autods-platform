# 🔬 AutoDS — Autonomous Data Science Platform

> Upload any data. Get analyst + scientist level outputs. Full control over every decision.

AutoDS is a **multi-agent AI platform** that autonomously executes the complete data science workflow — from raw data ingestion to deployed ML models — using 8 specialized AI agents orchestrated through a LangGraph state machine.

**This is not another AutoML tool.** AutoDS detects your industry domain, adapts its analysis to domain-specific best practices, asks intelligent questions at every step, and produces professional reports that business stakeholders can act on.

![Architecture](docs/images/architecture_diagram.png)

---

## ✨ Key Features

### 🔌 Connect to Any Data Source
CSV, Excel, Parquet, JSON, PostgreSQL, MySQL, BigQuery, Snowflake, REST APIs, Kaggle, HuggingFace, Google Sheets, web scraping, AWS S3, clipboard paste, and more.

### 🏥💰🛒 Domain-Aware Intelligence
Auto-detects your industry (Healthcare, Finance, E-commerce, Marketing, HR, Manufacturing) and adapts everything — metrics, statistical tests, feature engineering, model evaluation, compliance checks, and report terminology.

### 🎛️ Three User Modes
- **🤖 Auto** — System makes all decisions. Upload data, get results.
- **🎛️ Guided** — System recommends options. You choose at each step.
- **🔧 Expert** — Full control over every parameter and algorithm.

### 🤖 8 Specialized AI Agents
| Agent | Role |
|-------|------|
| **Orchestrator** | Decomposes goals, routes work, manages state |
| **Data Profiler** | Schema detection, quality assessment, cleaning |
| **EDA Agent** | Domain-aware exploratory analysis with interactive questions |
| **Feature Engineer** | Domain-aware feature creation with per-column control |
| **Modeling Agent** | Model selection, training, evaluation, comparison |
| **Explainability Agent** | SHAP, fairness audit, counterfactuals, model cards |
| **Report Agent** | HTML, PDF, executive summary, Jupyter notebook |
| **Follow-Up Agent** | Post-pipeline "ask anything" conversational interface |

### 📊 20+ Statistical Tests, 25+ Chart Types, 20+ ML Algorithms
Every technique is registered in a searchable tool registry — the system never "forgets" a method.

### 📄 Professional Reports
Download as interactive HTML, print-ready PDF, 1-page executive summary, or runnable Jupyter notebook.

### 💬 Ask Anything After Analysis
Follow-up conversational interface: "Show me churn by region", "Run a chi-square test on gender vs outcome", "What if I change this patient's age to 65?"

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/your-username/autods-platform.git
cd autods-platform

# Install dependencies
make setup

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Launch the dashboard
make run
```

Open `http://localhost:8501` in your browser.

---

## 🏗️ Architecture

```
User Input → Domain Detection → Orchestrator (LangGraph)
  → Data Profiler → EDA Agent → Feature Engineer → Modeling Agent
  → Explainability Agent → Report Agent → Outputs
```

Each agent follows the principle: **LLM decides WHAT to do. Python tools DO it.** Claude handles decision-making and interpretation; registered Python functions handle all computation deterministically.

See [Architecture Documentation](docs/architecture.md) for details.

---

## 🛠️ Tech Stack

| Component | Tool |
|-----------|------|
| Agent Framework | LangGraph |
| LLM | Claude (Anthropic) |
| Data Warehouse | DuckDB |
| ML | scikit-learn, XGBoost, LightGBM, CatBoost, FLAML |
| Explainability | SHAP, Fairlearn |
| Statistics | scipy, statsmodels, lifelines |
| Visualization | Plotly |
| Dashboard | Streamlit |
| Experiment Tracking | MLflow |
| API Serving | FastAPI |
| Memory | SQLite + ChromaDB |

---

## 📊 Benchmark Results

| Dataset | Domain | Problem | Metric | AutoDS | Baseline |
|---------|--------|---------|--------|--------|----------|
| Titanic | Generic | Classification | AUC | — | — |
| Credit Default | Finance | Classification | KS | — | — |
| Hospital Readmission | Healthcare | Classification | Sensitivity | — | — |
| E-commerce Churn | E-commerce | Classification | F1 | — | — |
| Boston Housing | Generic | Regression | RMSE | — | — |

*Benchmarks will be populated after implementation is complete.*

---

## 📁 Project Structure

```
autods-platform/
├── CLAUDE.md              # Claude Code instructions (master reference)
├── agents/                # 8 AI agents + tool functions
├── core/                  # LangGraph workflow, state, LLM config
├── data_connectors/       # 30+ data source connectors
├── domains/               # 7 industry domain configurations
├── dashboard/             # Streamlit web application (9 pages)
├── validation/            # Data & model validation
├── explainability/        # SHAP, fairness, counterfactuals
├── evaluation/            # Agent evaluation & benchmarks
├── logging_audit/         # Structured logging & audit trail
├── session/               # Session persistence & comparison
├── reports/               # Report generation (HTML/PDF/notebook)
├── serving/               # FastAPI prediction endpoint + Docker
├── tests/                 # Unit, integration, agent, benchmark tests
├── scripts/               # Utility scripts
├── configs/               # YAML configurations
└── docs/                  # Documentation
```

---

## 🧪 Running Tests

```bash
make test              # Unit tests
make test-integration  # Integration tests
make test-all          # All tests with coverage
make benchmark         # Run benchmark suite
```

---

## 📝 License

MIT

---

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration framework
- [Anthropic Claude](https://anthropic.com) — LLM powering agent decisions
- [FLAML](https://github.com/microsoft/FLAML) — Microsoft's AutoML library
- [SHAP](https://github.com/shap/shap) — Model explainability
- [Fairlearn](https://github.com/fairlearn/fairlearn) — ML fairness toolkit
