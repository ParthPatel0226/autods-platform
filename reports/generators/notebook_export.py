"""Jupyter Notebook Export Generator.

Produces a runnable .ipynb notebook that reproduces the entire analysis
pipeline: data loading, profiling, EDA, feature engineering, model
training, evaluation, and SHAP explainability.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _safe_get(state: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        val = state.get(key)
        if val is not None:
            return val
    return default


def _nb():  # noqa: ANN202
    """Lazy-import nbformat to avoid hard dependency at module level."""
    try:
        import nbformat
        return nbformat
    except ImportError as exc:
        raise ImportError(
            "nbformat is required for notebook generation. "
            "Install with: pip install nbformat"
        ) from exc


def _md(source: str):  # noqa: ANN202
    """Create a markdown cell."""
    return _nb().v4.new_markdown_cell(source)


def _code(source: str):  # noqa: ANN202
    """Create a code cell."""
    return _nb().v4.new_code_cell(source)


def _create_import_cell():  # noqa: ANN202
    """Create the initial imports cell.

    Returns:
        A notebook code cell with standard data science imports.
    """
    return _code(
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "import warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "\n"
        "# Plotting defaults\n"
        "plt.rcParams['figure.figsize'] = (10, 6)\n"
        "plt.rcParams['figure.dpi'] = 100\n"
        "sns.set_style('whitegrid')\n"
        "%matplotlib inline"
    )


def _create_eda_cells(state: dict) -> list:
    """Create EDA section cells with actual analysis code.

    Args:
        state: Pipeline state dict.

    Returns:
        List of notebook cells for the EDA section.
    """
    target = state.get("target_column", "target")
    problem_type = state.get("problem_type", "classification")

    cells = [
        _md("## 3. Exploratory Data Analysis"),
        _code(
            "# Dataset shape and info\n"
            "print(f'Dataset shape: {df.shape}')\n"
            "print(f'\\nColumn types:\\n{df.dtypes.value_counts()}')\n"
            "print(f'\\nMissing values:\\n{df.isnull().sum()[df.isnull().sum() > 0]}')"
        ),
        _code(
            "# Descriptive statistics\n"
            "df.describe(include='all').T"
        ),
    ]

    # Target distribution
    if problem_type == "classification":
        cells.append(
            _code(
                f"# Target distribution\n"
                f"if '{target}' in df.columns:\n"
                f"    fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n"
                f"    df['{target}'].value_counts().plot(kind='bar', ax=axes[0], "
                f"color='steelblue')\n"
                f"    axes[0].set_title('Target Class Distribution')\n"
                f"    axes[0].set_ylabel('Count')\n"
                f"    df['{target}'].value_counts(normalize=True).plot(kind='pie', "
                f"ax=axes[1], autopct='%1.1f%%')\n"
                f"    axes[1].set_title('Target Class Proportions')\n"
                f"    plt.tight_layout()\n"
                f"    plt.show()"
            )
        )
    else:
        cells.append(
            _code(
                f"# Target distribution\n"
                f"if '{target}' in df.columns:\n"
                f"    fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n"
                f"    df['{target}'].hist(bins=30, ax=axes[0], color='steelblue', "
                f"edgecolor='white')\n"
                f"    axes[0].set_title('Target Distribution')\n"
                f"    axes[0].set_xlabel('{target}')\n"
                f"    import scipy.stats as stats\n"
                f"    stats.probplot(df['{target}'].dropna(), plot=axes[1])\n"
                f"    axes[1].set_title('Q-Q Plot')\n"
                f"    plt.tight_layout()\n"
                f"    plt.show()"
            )
        )

    # Correlation heatmap
    cells.append(
        _code(
            "# Correlation heatmap (numeric columns)\n"
            "numeric_cols = df.select_dtypes(include=[np.number]).columns\n"
            "if len(numeric_cols) > 1:\n"
            "    corr = df[numeric_cols].corr()\n"
            "    mask = np.triu(np.ones_like(corr, dtype=bool))\n"
            "    plt.figure(figsize=(12, 10))\n"
            "    sns.heatmap(corr, mask=mask, annot=len(numeric_cols) <= 15,\n"
            "                fmt='.2f', cmap='RdBu_r', center=0,\n"
            "                square=True, linewidths=0.5)\n"
            "    plt.title('Feature Correlation Matrix')\n"
            "    plt.tight_layout()\n"
            "    plt.show()"
        )
    )

    # EDA summary from the agent
    eda_summary = state.get("eda_summary")
    if eda_summary:
        cells.append(
            _md(
                "### EDA Summary (from AutoDS)\n\n"
                f"{str(eda_summary)[:2000]}"
            )
        )

    return cells


def _create_model_cells(state: dict) -> list:
    """Create model training and evaluation cells.

    Args:
        state: Pipeline state dict.

    Returns:
        List of notebook cells for the modeling section.
    """
    target = state.get("target_column", "target")
    features = _safe_get(state, "feature_list", "features_selected", default=[])
    problem_type = state.get("problem_type", "classification")
    random_seed = state.get("random_seed", 42)
    model_results = state.get("model_results") or {}
    best_model = _safe_get(
        state, "best_model", "best_model_name", default="N/A"
    )

    cells = [
        _md("## 5. Model Training & Evaluation"),
        _code(
            f"RANDOM_SEED = {random_seed}\n"
            f"TARGET = '{target}'\n"
            f"FEATURES = {json.dumps(features[:50])}\n"
            "\n"
            "# Use available features\n"
            "available = [c for c in FEATURES if c in df.columns]\n"
            "X = df[available].copy()\n"
            "y = df[TARGET].copy() if TARGET in df.columns else None\n"
            "print(f'Features: {len(available)}, Samples: {len(X)}')"
        ),
        _code(
            "from sklearn.model_selection import train_test_split\n"
            "\n"
            "if y is not None:\n"
            f"    X_train, X_test, y_train, y_test = train_test_split(\n"
            f"        X, y, test_size=0.2, random_state=RANDOM_SEED,\n"
            f"        stratify=y if '{problem_type}' == 'classification' "
            f"and y.nunique() <= 20 else None\n"
            f"    )\n"
            "    print(f'Train: {len(X_train)}, Test: {len(X_test)}')"
        ),
    ]

    if problem_type == "classification":
        cells.append(
            _code(
                "from sklearn.ensemble import RandomForestClassifier, "
                "GradientBoostingClassifier\n"
                "from sklearn.linear_model import LogisticRegression\n"
                "from sklearn.metrics import (\n"
                "    classification_report, roc_auc_score, confusion_matrix,\n"
                "    ConfusionMatrixDisplay\n"
                ")\n"
                "\n"
                "models = {\n"
                "    'LogisticRegression': LogisticRegression(\n"
                "        max_iter=1000, random_state=RANDOM_SEED),\n"
                "    'RandomForest': RandomForestClassifier(\n"
                "        n_estimators=100, random_state=RANDOM_SEED),\n"
                "    'GradientBoosting': GradientBoostingClassifier(\n"
                "        n_estimators=100, random_state=RANDOM_SEED),\n"
                "}\n"
                "\n"
                "results = {}\n"
                "for name, model in models.items():\n"
                "    model.fit(X_train, y_train)\n"
                "    preds = model.predict(X_test)\n"
                "    acc = (preds == y_test).mean()\n"
                "    results[name] = {'accuracy': acc}\n"
                "    try:\n"
                "        proba = model.predict_proba(X_test)[:, 1]\n"
                "        results[name]['auc'] = roc_auc_score(y_test, proba)\n"
                "    except Exception:\n"
                "        pass\n"
                "    print(f'{name}: {results[name]}')"
            )
        )
    else:
        cells.append(
            _code(
                "from sklearn.ensemble import RandomForestRegressor, "
                "GradientBoostingRegressor\n"
                "from sklearn.linear_model import Ridge\n"
                "from sklearn.metrics import mean_absolute_error, "
                "mean_squared_error, r2_score\n"
                "\n"
                "models = {\n"
                "    'Ridge': Ridge(random_state=RANDOM_SEED),\n"
                "    'RandomForest': RandomForestRegressor(\n"
                "        n_estimators=100, random_state=RANDOM_SEED),\n"
                "    'GradientBoosting': GradientBoostingRegressor(\n"
                "        n_estimators=100, random_state=RANDOM_SEED),\n"
                "}\n"
                "\n"
                "results = {}\n"
                "for name, model in models.items():\n"
                "    model.fit(X_train, y_train)\n"
                "    preds = model.predict(X_test)\n"
                "    results[name] = {\n"
                "        'mae': mean_absolute_error(y_test, preds),\n"
                "        'rmse': mean_squared_error(y_test, preds, "
                "squared=False),\n"
                "        'r2': r2_score(y_test, preds),\n"
                "    }\n"
                "    print(f'{name}: {results[name]}')"
            )
        )

    # AutoDS results comparison
    cells.append(
        _md(
            "### AutoDS Model Results\n\n"
            f"Best model selected by AutoDS: **{best_model}**"
        )
    )
    cells.append(
        _code(
            f"autods_results = {json.dumps(model_results, default=str)}\n"
            "\n"
            "if autods_results:\n"
            "    results_df = pd.DataFrame(autods_results).T\n"
            "    print('AutoDS Model Comparison:')\n"
            "    display(results_df)"
        )
    )

    return cells


def _create_shap_cells(state: dict) -> list:
    """Create SHAP explainability cells if SHAP data is available.

    Args:
        state: Pipeline state dict.

    Returns:
        List of notebook cells for the SHAP section (may be empty).
    """
    shap_data = _safe_get(state, "shap_values", "shap_summary", default=None)
    if not shap_data:
        return [
            _md("## 7. Explainability\n\n*SHAP analysis was not performed. "
                 "Run the explainability agent for feature importance.*")
        ]

    return [
        _md("## 7. Explainability (SHAP)"),
        _code(
            "try:\n"
            "    import shap\n"
            "    # Use the best model from the comparison\n"
            "    best_name = max(results, key=lambda k: "
            "list(results[k].values())[0])\n"
            "    best_model_obj = models[best_name]\n"
            "    explainer = shap.Explainer(best_model_obj, X_train)\n"
            "    shap_values = explainer(X_test[:100])\n"
            "    shap.summary_plot(shap_values, X_test[:100])\n"
            "except ImportError:\n"
            "    print('Install shap: pip install shap')\n"
            "except Exception as e:\n"
            "    print(f'SHAP failed: {e}')"
        ),
    ]


def generate_notebook(state: dict, output_dir: str) -> str:
    """Generate a runnable Jupyter notebook reproducing the analysis.

    The notebook includes all pipeline steps with actual feature lists,
    model results, and metrics from the state. It is designed to be
    self-contained and reproducible.

    Args:
        state: AutoDS pipeline state dict.
        output_dir: Directory to write the .ipynb file into.

    Returns:
        Absolute path to the generated notebook file.
    """
    nbformat = _nb()

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    domain = state.get("detected_domain", "generic")
    target = state.get("target_column", "target")
    problem_type = state.get("problem_type", "classification")
    session_id = state.get("session_id", "N/A")
    random_seed = state.get("random_seed", 42)

    cells = [
        # Title
        _md(
            f"# AutoDS Analysis Notebook\n\n"
            f"**Session**: `{session_id}`  \n"
            f"**Domain**: {domain.title()} | "
            f"**Problem**: {problem_type.title()} | "
            f"**Target**: `{target}`  \n"
            f"**Random Seed**: {random_seed}\n\n"
            f"---\n\n"
            f"This notebook reproduces the analysis performed by the AutoDS "
            f"platform. All code is runnable — update the data path in "
            f"Section 1 to point at your dataset."
        ),
        # Imports
        _md("## 1. Setup"),
        _create_import_cell(),
        _code(f"RANDOM_SEED = {random_seed}\nnp.random.seed(RANDOM_SEED)"),
        # Data loading
        _md("## 2. Data Loading"),
        _code(
            "# Update this path to your dataset location\n"
            "DATA_PATH = 'data/dataset.csv'\n"
            "\n"
            "df = pd.read_csv(DATA_PATH)\n"
            "print(f'Loaded dataset: {df.shape[0]:,} rows x {df.shape[1]} columns')\n"
            "df.head()"
        ),
    ]

    # EDA
    cells.extend(_create_eda_cells(state))

    # Feature engineering
    features = _safe_get(state, "feature_list", "features_selected", default=[])
    cells.append(_md("## 4. Feature Engineering"))
    cells.append(
        _code(
            f"FEATURES = {json.dumps(features[:50])}\n"
            "\n"
            "# Show available features\n"
            "available = [c for c in FEATURES if c in df.columns]\n"
            "missing = [c for c in FEATURES if c not in df.columns]\n"
            "print(f'Available: {len(available)} / {len(FEATURES)}')\n"
            "if missing:\n"
            "    print(f'Missing features (need engineering): {missing[:10]}')"
        )
    )

    # Modeling
    cells.extend(_create_model_cells(state))

    # Evaluation visualization
    cells.append(_md("## 6. Evaluation Visualization"))
    if problem_type == "classification":
        cells.append(
            _code(
                "# Confusion matrix for best model\n"
                "best_name = max(results, key=lambda k: "
                "list(results[k].values())[0])\n"
                "best_model_obj = models[best_name]\n"
                "preds = best_model_obj.predict(X_test)\n"
                "\n"
                "fig, ax = plt.subplots(figsize=(8, 6))\n"
                "ConfusionMatrixDisplay.from_predictions(\n"
                "    y_test, preds, ax=ax, cmap='Blues')\n"
                "ax.set_title(f'Confusion Matrix - {best_name}')\n"
                "plt.tight_layout()\n"
                "plt.show()\n"
                "\n"
                "print(f'\\nClassification Report ({best_name}):')\n"
                "print(classification_report(y_test, preds))"
            )
        )
    else:
        cells.append(
            _code(
                "# Residual plot for best model\n"
                "best_name = max(results, key=lambda k: results[k].get('r2', 0))\n"
                "best_model_obj = models[best_name]\n"
                "preds = best_model_obj.predict(X_test)\n"
                "residuals = y_test - preds\n"
                "\n"
                "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n"
                "axes[0].scatter(preds, residuals, alpha=0.5, s=10)\n"
                "axes[0].axhline(y=0, color='r', linestyle='--')\n"
                "axes[0].set_xlabel('Predicted')\n"
                "axes[0].set_ylabel('Residual')\n"
                "axes[0].set_title(f'Residuals - {best_name}')\n"
                "\n"
                "axes[1].scatter(y_test, preds, alpha=0.5, s=10)\n"
                "mn, mx = min(y_test.min(), preds.min()), "
                "max(y_test.max(), preds.max())\n"
                "axes[1].plot([mn, mx], [mn, mx], 'r--')\n"
                "axes[1].set_xlabel('Actual')\n"
                "axes[1].set_ylabel('Predicted')\n"
                "axes[1].set_title('Actual vs Predicted')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            )
        )

    # SHAP
    cells.extend(_create_shap_cells(state))

    # Reproducibility footer
    cells.append(
        _md(
            "---\n\n"
            f"**Reproducibility**: Random seed = `{random_seed}` | "
            f"Data hash = `{state.get('data_hash', 'N/A')}`\n\n"
            f"Generated by [AutoDS](https://github.com/autods) on "
            f"{state.get('timestamp', 'N/A')}"
        )
    )

    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }

    out_path = out_dir / "analysis_notebook.ipynb"
    with open(out_path, "w", encoding="utf-8") as fh:
        nbformat.write(nb, fh)

    logger.info("Jupyter notebook generated at %s", out_path)
    return str(out_path)
