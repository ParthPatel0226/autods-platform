"""Multi-source data manager.

Handles loading data from multiple sources, tracking metadata,
and joining them via DuckDB.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class MultiSourceManager:
    """Manage multiple loaded DataFrames and support join operations."""

    def __init__(self) -> None:
        self._sources: dict[str, dict[str, Any]] = {}

    def add_source(
        self,
        name: str,
        df: pd.DataFrame,
        *,
        origin: str = "unknown",
        metadata: dict | None = None,
    ) -> None:
        """Register a DataFrame as a named source.

        Args:
            name: Unique identifier for this source.
            df: The loaded DataFrame.
            origin: Where the data came from (e.g. "csv", "postgres").
            metadata: Optional extra metadata dict.
        """
        if name in self._sources:
            logger.warning("Overwriting existing source '%s'", name)

        self._sources[name] = {
            "df": df,
            "origin": origin,
            "n_rows": len(df),
            "n_cols": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "metadata": metadata or {},
        }
        logger.info(
            "Added source '%s' (%d rows, %d cols) from %s",
            name, len(df), len(df.columns), origin,
        )

    def remove_source(self, name: str) -> None:
        """Remove a registered source by name."""
        self._sources.pop(name, None)

    def list_sources(self) -> list[dict[str, Any]]:
        """Return summary info for every registered source."""
        return [
            {
                "name": name,
                "origin": info["origin"],
                "n_rows": info["n_rows"],
                "n_cols": info["n_cols"],
                "columns": info["columns"],
            }
            for name, info in self._sources.items()
        ]

    def get_dataframe(self, name: str) -> pd.DataFrame:
        """Retrieve a source DataFrame by name.

        Raises:
            KeyError: If source name is not registered.
        """
        if name not in self._sources:
            raise KeyError(f"Source '{name}' not found. Available: {list(self._sources)}")
        return self._sources[name]["df"]

    def get_schema(self, name: str) -> dict[str, str]:
        """Return {column: dtype_str} for a named source."""
        if name not in self._sources:
            raise KeyError(f"Source '{name}' not found.")
        return dict(self._sources[name]["dtypes"])

    def join(
        self,
        left_name: str,
        right_name: str,
        on: str | list[str],
        how: str = "inner",
        *,
        result_name: str | None = None,
    ) -> pd.DataFrame:
        """Join two sources and optionally register the result.

        Args:
            left_name: Name of left source.
            right_name: Name of right source.
            on: Column name(s) to join on.
            how: Join type — 'inner', 'left', 'right', or 'outer'.
            result_name: If provided, register the joined result as a new source.

        Returns:
            The joined DataFrame.
        """
        left = self.get_dataframe(left_name)
        right = self.get_dataframe(right_name)

        if how not in {"inner", "left", "right", "outer"}:
            raise ValueError(f"Invalid join type '{how}'. Use inner/left/right/outer.")

        joined = pd.merge(left, right, on=on, how=how, suffixes=("", f"_{right_name}"))

        logger.info(
            "Joined '%s' (%d) + '%s' (%d) on %s [%s] → %d rows",
            left_name, len(left), right_name, len(right), on, how, len(joined),
        )

        if result_name:
            self.add_source(result_name, joined, origin=f"join({left_name},{right_name})")

        return joined

    @property
    def source_count(self) -> int:
        return len(self._sources)
