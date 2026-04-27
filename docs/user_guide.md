# User Guide

## Quick Start

```bash
git clone https://github.com/youruser/autods-platform.git
cd autods-platform
make setup          # Install deps + download sample datasets
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
make run            # Launch Streamlit dashboard at localhost:8501
```

## User Modes

AutoDS offers three modes that control how much input you provide at each step:

| Mode | Interaction | Best For |
|------|------------|----------|
| **Auto** | System makes all decisions | Quick exploration, demos |
| **Guided** | System recommends, you choose | Production analysis work |
| **Expert** | Full parameter control | Data scientists, audits |

You select the mode on the Configuration page. You can switch modes mid-pipeline.

## Theme System

AutoDS features a **professional dual-theme design system** implemented via CSS custom properties.

### Light Mode (Default)
Clean, high-contrast light theme with white backgrounds, slate neutrals, and a blue accent (#2563eb primary).

### Dark Mode
Deep navy theme optimized for reduced eye strain during long analysis sessions. All UI elements automatically adapt — shadows, borders, text colors, and chart colors.

**Toggle dark mode** anytime via the button in the top-right of the sidebar. Your preference persists throughout your session.

The design system includes 80+ CSS tokens controlling:
- Backgrounds (`--bg-primary`, `--bg-card`, `--bg-elevated`, `--bg-inset`)
- Text colors (`--text-primary`, `--text-secondary`, `--text-muted`)
- Accent colors (primary blue `#2563eb`, secondary cyan `#0891b2`, purple, success, warning, danger)
- Spacing, radii, shadows, transitions, and typography (`Plus Jakarta Sans` display, `Inter` body, `JetBrains Mono` code)

## Workflow Steps

## Landing Page

When you first open AutoDS, you'll see a professional landing page featuring:

- **Hero Banner**: Dark gradient background with animated title and floating stat pills showing platform capabilities
- **Feature Showcase**: Three bento-grid cards highlighting Domain Intelligence, Collaborative Agents, and Pipeline Control
- **File Upload**: Central drag-and-drop zone with format chips showing supported types
- **Sample Datasets**: Quick-start options for Titanic, Heart Disease, Credit Risk, Online Retail, Attrition, and Predictive Maintenance
- **Platform Stats**: Bottom grid showing key metrics (7 Domains, 25+ Charts, 16 Tests, 8 Agents, 30+ Sources)

### 1. Upload Data

Navigate to the Upload page. Supported sources:

- **File Upload**: CSV, Excel, Parquet, JSON, XML, PDF tables, SAS/STATA/SPSS, SQLite, compressed archives
- **Database**: PostgreSQL, MySQL, SQL Server, DuckDB, BigQuery, Snowflake, Redshift
- **API**: REST endpoints, Kaggle datasets, HuggingFace datasets, Google Sheets, web scraping
- **Cloud**: AWS S3, Google Cloud Storage, Azure Blob Storage
- **Direct**: Paste from clipboard, manual entry, built-in sample datasets

Multi-source: upload multiple files and join them. AutoDS suggests join keys.

### 2. Configure

- **Domain Detection**: AutoDS analyzes column names and auto-detects your industry (Healthcare, Finance, E-commerce, Marketing, HR, Manufacturing). Override if needed.
- **Target Column**: Select the variable to predict (or leave empty for unsupervised).
- **Problem Type**: Classification, regression, clustering, or time series.
- **Goal**: Select your analysis objective from a problem-type-aware dropdown, or type a custom goal in the text field below (e.g., "Find top 5 churn predictors with AUC > 0.85").

### 3. Exploratory Data Analysis (EDA)

In Guided/Expert mode, AutoDS asks domain-specific questions:
- What's your primary analysis goal?
- Which visualisations would you like?
- Which statistical tests should be run?

Each question includes preset options plus a manual text field for custom specifications. Click **Run Selected Analyses** to execute — results appear immediately with charts, statistical test tables, and key insights.

### 4. Feature Engineering

AutoDS generates a per-column decision table:
- **Missing values**: mean, median, mode, drop, domain-specific
- **Encoding**: one-hot, target, ordinal, frequency, WoE
- **Scaling**: standard, minmax, log, box-cox
- **Outlier handling**: clip, remove, keep
- **Domain features**: Charlson index (healthcare), RFM scores (e-commerce), etc.

In Guided mode, AutoDS recommends a strategy per column with reasons.

### 5. Modeling

AutoDS recommends algorithms based on your data characteristics and domain:
- Classification: Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost, SVM, Neural Network
- Regression: Linear, Ridge, Lasso, ElasticNet, tree ensembles
- Clustering: K-Means, DBSCAN, Hierarchical

Training includes cross-validation, statistical model comparison (paired t-test, McNemar's, Wilcoxon), and bootstrap confidence intervals. All experiments logged to MLflow.

### 6. Explainability

- **SHAP**: Global feature importance + local explanations per prediction
- **Partial Dependence**: How each feature affects predictions
- **Counterfactuals**: What would change the prediction
- **Fairness Audit**: Disparate impact, demographic parity across protected attributes
- **Model Card**: Standardized documentation (Google format)
- **What-If**: Interactively modify features and see impact
- **Calibration**: Reliability diagrams for probabilistic predictions

### 7. Predictions

- **Batch**: Upload new data for bulk predictions
- **Single Row**: Fill in a form to predict one sample
- Real-time explanation display with SHAP values

### 8. Chat / Follow-Up

Post-pipeline conversational interface:
- "Show me churn by region"
- "Run a chi-square test on gender vs outcome"
- "What if I change this patient's age to 65?"
- "Generate a scatter plot of income vs spending"

The follow-up agent searches the tool registry and executes on-demand analyses.

### 9. Download

Download all outputs:
- Interactive HTML report with embedded Plotly charts
- Print-ready PDF report
- 1-page executive summary for stakeholders
- Runnable Jupyter notebook with all code
- Trained model artifact (.joblib)
- Complete audit trail (JSON)
- ZIP package of everything

## Session Management

- **Save**: Sessions auto-save to SQLite. Resume any previous session.
- **Compare**: Side-by-side comparison of two sessions on the same data.
- **Export**: Download session as portable JSON for sharing or reproduction.

## Keyboard Shortcuts (Dashboard)

| Shortcut | Action |
|----------|--------|
| `R` | Rerun current page |
| `C` | Clear cache |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `AUTODS_MODEL_PATH` | No | Override model artifact path |
| `AUTODS_DUCKDB_PATH` | No | DuckDB warehouse location |
| `AUTODS_SQLITE_PATH` | No | Session database location |
| `MLFLOW_TRACKING_URI` | No | MLflow server URI |

## FAQ

**Q: How much does it cost to run?**
A: AutoDS tracks Claude API costs per pipeline run. Typical analysis: $0.10-$0.50 depending on data size and mode. Auto mode uses fewer API calls than Guided/Expert.

**Q: Can I use my own models?**
A: The serving API loads any scikit-learn-compatible model saved as .joblib. Train externally, save the artifact, and serve via the API.

**Q: Is my data sent to the cloud?**
A: Only LLM prompts (column names, statistics, summaries) are sent to the Claude API. Raw data stays local and is processed by Python tool functions.
