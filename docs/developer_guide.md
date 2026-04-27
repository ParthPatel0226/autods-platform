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
    components/
      shared_css.py # Design system + theme tokens (80+ CSS variables)
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

## Design System & Styling

All dashboard pages use a shared CSS design system defined in `dashboard/components/shared_css.py`. This ensures consistency and makes theme switching seamless.

### Key Design System Features

**80+ CSS Custom Properties** organized by category:
- **Backgrounds**: `--bg-primary`, `--bg-card`, `--bg-elevated`, `--bg-inset`, `--bg-overlay`
- **Text Colors**: `--text-primary`, `--text-secondary`, `--text-muted`, `--text-inverse`
- **Accent Colors**: `--accent-primary` (#2563eb), `--accent-secondary` (#0891b2), plus success/warning/danger/info/purple variants
- **Shadows**: `--shadow-xs` through `--shadow-lg`, `--shadow-glow`, `--shadow-focus`
- **Spacing**: `--space-1` through `--space-12` (0.25rem to 3rem)
- **Radii**: `--radius-xs` through `--radius-full`
- **Typography**: `--font-display` (Plus Jakarta Sans), `--font-body` (Inter), `--font-mono` (JetBrains Mono)
- **Transitions**: `--duration-fast/normal/slow`, `--ease-in-out`, `--ease-out`

**Dual-Theme Support**:
- Light mode (default) with white backgrounds and high contrast
- Dark mode with deep navy backgrounds optimized for eye comfort
- Theme values baked into `:root` CSS via `inject_shared_css()` — no JavaScript needed

**Shared Component Classes**:
- `.glass-card` — Card with border, shadow, hover effects
- `.pill-tabs` / `.pill-tab` — Tab-like control with pill styling
- `.glass-table` — Styled table with hover rows
- `.badge-*` / `.status-dot-*` — Utility classes for badges and status indicators

**When Adding Dashboard Pages or Components**:

1. Call `inject_shared_css()` at the top of every page
2. Use CSS variables instead of hardcoded colors: `var(--bg-card)`, `var(--accent-primary)`, etc.
3. Reference shared component classes for consistency
4. For charts, use `get_plotly_layout(is_dark)` helper and `PLOTLY_CHART_COLORS` list
5. Example:

```python
from dashboard.components.shared_css import inject_shared_css, get_plotly_layout, PLOTLY_CHART_COLORS
import streamlit as st

# Page setup
is_dark = inject_shared_css()

# Use in Plotly charts
fig.update_layout(**get_plotly_layout(is_dark))

# Use in markdown/HTML
st.markdown(
    '<div class="glass-card"><h3>Analysis Results</h3></div>',
    unsafe_allow_html=True
)

# Don't hardcode colors — use variables
st.markdown(
    '<div style="color: var(--accent-primary); background: var(--bg-card);">Content</div>',
    unsafe_allow_html=True
)
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

## Adding a Dashboard Page

All Streamlit pages live in `dashboard/pages/` and follow this pattern:

```python
import streamlit as st
from dashboard.components.shared_css import inject_shared_css

def _page() -> None:
    """Page entry point — only runs inside Streamlit runtime."""
    inject_shared_css()
    # ... page content ...

def _is_streamlit_running() -> bool:
    """Return True only when executing inside a Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False

if _is_streamlit_running():
    _page()
```

Key rules:
- **Never call `_page()` unconditionally** at module level. Always gate behind `_is_streamlit_running()` to prevent bare-import crashes in tests.
- **Use `st.session_state.get("key")` not `st.session_state["key"]`** for data that may not exist yet.
- **Import `inject_shared_css`** from `dashboard/components/shared_css.py` for consistent theming.
- **Guard against missing data** with `st.info("descriptive message about what this page does")` + `st.stop()` at the top of `_page()`.
- **Never hardcode colors** — use `var(--bg-primary)`, `var(--text-primary)`, etc. from shared_css.py.
- **Do not redefine `:root` CSS variables** in page CSS — shared_css.py owns all design tokens.
- **Theme support**: `inject_shared_css()` bakes the active theme palette directly into `:root`. Both light and dark palettes are defined as Python dicts (`_LIGHT`, `_DARK`) and `_build_css()` generates the CSS. Page-specific CSS should use only `var(--xxx)` references.
- **No rgba(255,255,255,...) backgrounds** — use `var(--bg-elevated)` instead (invisible on white in light mode).
- **No heavy dark shadows** — use `var(--shadow-glow)` or `var(--shadow-card)` instead of hardcoded rgba.

### Design System Reference

The design system lives in `dashboard/components/shared_css.py`. Key token categories:

| Category | Examples | Usage |
|----------|---------|-------|
| **Backgrounds** | `--bg-primary`, `--bg-card`, `--bg-elevated`, `--bg-inset` | Page/card/section backgrounds |
| **Borders** | `--border-subtle`, `--border-default`, `--border-active` | Container borders |
| **Text** | `--text-primary`, `--text-secondary`, `--text-muted` | Typography colors |
| **Accents** | `--accent-primary` (#2563eb), `--accent-secondary`, `--accent-success`, `--accent-warning`, `--accent-danger`, `--accent-purple` | Interactive elements |
| **Subtle accents** | `--accent-primary-subtle`, `--accent-primary-light` | Hover backgrounds, badges |
| **Fonts** | `--font-display` (Plus Jakarta Sans), `--font-body` (Inter), `--font-mono` (JetBrains Mono) | Typography families |
| **Sizes** | `--text-xs` through `--text-4xl` | Font sizes |
| **Spacing** | `--space-1` through `--space-12` | Margins/padding |
| **Radii** | `--radius-xs` through `--radius-full` | Border radius |
| **Shadows** | `--shadow-xs`, `--shadow-card`, `--shadow-md`, `--shadow-lg`, `--shadow-glow`, `--shadow-focus` | Elevation |
| **Transitions** | `--transition-colors`, `--transition-shadow`, `--transition-all` | Motion |
| **Charts** | `--chart-1` through `--chart-8` | Plotly/data viz colors |

For Plotly charts, use the helper:
```python
from dashboard.components.shared_css import get_plotly_layout, PLOTLY_CHART_COLORS

fig.update_layout(**get_plotly_layout(is_dark))
```

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
