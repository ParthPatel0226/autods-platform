# Developer Guide

## Project Setup

```bash
git clone https://github.com/youruser/autods-platform.git
cd autods-platform
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
pip install -e .
make setup-db
make setup-data
```

## Project Structure

```
autods-platform/
  agents/           # AI agents (orchestrator, profiler, EDA, etc.)
    tools/          # Python tool functions agents call
  core/             # State, graph, LLM config, constants, exceptions
  data_connectors/  # 30+ data source connectors
  domains/          # Industry domain configurations (7 domains)
  dashboard/        # Streamlit web application (9 pages + components)
  evaluation/       # Model comparison, bootstrap CI, domain metrics
  explainability/   # SHAP, fairness, counterfactuals, model cards
  logging_audit/    # Structured logging, decision log, cost tracker
  reports/          # HTML/PDF/notebook generation + templates
  serving/          # FastAPI prediction API
  session/          # Session save/load/compare/export
  validation/       # Input, schema, edge case, drift validators
  tests/            # Unit, integration, agent, benchmark tests
  configs/          # YAML configuration files
  scripts/          # Utility scripts
  docs/             # Documentation
```

## Adding a New Connector

1. Create file in the appropriate `data_connectors/` subdirectory
2. Extend `BaseConnector` from `data_connectors/base.py`
3. Implement required methods:
   - `connector_type` (property) -- string identifier
   - `display_name` (property) -- human-readable name
   - `validate_config(config)` -- validate before loading
   - `load(config)` -- load data into DataFrame
   - `get_preview(config, n_rows)` -- quick preview
4. Register in `data_connectors/connector_factory.py` `_CONNECTOR_REGISTRY`

```python
from data_connectors.base import BaseConnector
from core.exceptions import DataLoadError

class MyConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "my_source"

    @property
    def display_name(self) -> str:
        return "My Data Source"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        if not config.get("url"):
            return False, "url is required"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            raise DataLoadError(error)
        # ... load logic ...
        return df

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        return self.load({**config, "limit": n_rows})
```

## Adding a New Tool

1. Implement the function in the appropriate `agents/tools/` module
2. Follow the signature pattern:

```python
def my_analysis(df: pd.DataFrame, column: str, **kwargs) -> dict:
    """One-line description.

    Args:
        df: Input DataFrame.
        column: Column to analyze.

    Returns:
        Dict with result keys matching tool_registry output spec.
    """
    # Computation here
    return {"statistic": value, "interpretation": "..."}
```

3. Register in `agents/tools/tool_registry.py`:

```python
"my_analysis": {
    "name": "My Analysis",
    "function": "agents.tools.stats_tools.my_analysis",
    "description": "What it does",
    "when_to_use": "When to use it",
    "requirements": {"min_columns": 1, "column_types": ["numeric"]},
    "domains": ["all"],
    "parameters": {"df": "DataFrame", "column": "Column name"},
    "output": {"statistic": "Test statistic", "interpretation": "Plain English"}
}
```

4. Add unit test in `tests/unit/`

## Adding a New Domain

1. Create `domains/your_domain.py`:

```python
from domains.base_domain import BaseDomainConfig

class YourDomainConfig(BaseDomainConfig):
    domain_name = "your_domain"
    display_name = "Your Domain"
    icon = "..."

    detection_keywords = {
        "strong": ["keyword1", "keyword2"],
        "moderate": ["keyword3", "keyword4"],
        "weak": ["keyword5"]
    }
    # ... implement all abstract methods
```

2. The domain auto-registers via `domain_registry.py` on import.

## Adding a New Agent

1. Create `agents/your_agent.py` following the pattern:

```python
def your_agent(state: AutoDSState) -> AutoDSState:
    """Agent docstring."""
    llm = get_llm()
    mode = state["user_mode"]
    # 1. Read context from state
    # 2. Generate/receive user questions (Guided/Expert)
    # 3. Execute tools
    # 4. LLM interprets results
    # 5. Update state
    return state
```

2. Register as a node in `core/graph.py`
3. Add edges and conditional routing

## Running Tests

```bash
make test              # Unit tests only
make test-integration  # Integration tests
make test-all          # Full suite with coverage report
make test-fast         # Quick unit tests, stop on first failure
make benchmark         # Run benchmarks on standard datasets
```

## Code Quality

```bash
make lint    # ruff + mypy
make format  # black + isort + ruff --fix
```

## Architecture Decisions

- **LLM decides, Python executes**: Claude never computes statistics directly. It routes to registered tool functions.
- **Tool Registry as memory**: Every technique registered with metadata prevents LLM "forgetting" methods.
- **Immutable state updates**: Agents return new state dicts, not mutate in-place.
- **Graceful degradation**: If one tool fails, log the error and continue with the next.
- **Temperature 0**: Deterministic LLM responses for reproducibility.

## Common Development Tasks

### Debugging a Pipeline Run

```python
from core.graph import build_graph
from core.state import AutoDSState

graph = build_graph()
state = AutoDSState(...)
# Step through nodes manually
result = graph.invoke(state)
# Check result["errors"] for failures
# Check result["pipeline_log"] for timing
```

### Testing with Sample Data

```python
from data_connectors.direct_input.sample_datasets import SampleDatasetConnector
connector = SampleDatasetConnector()
df = connector.load({"dataset": "iris"})
```

### Viewing MLflow Experiments

```bash
mlflow ui --backend-store-uri mlruns/
# Open http://localhost:5000
```
