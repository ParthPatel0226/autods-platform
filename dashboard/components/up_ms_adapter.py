"""Adapter bridging the spec-assumed multi-source interface to the actual backend.

Spec assumed:
  - add_source(file_path, name) -> df_ref: str
  - get_source_info(df_ref) -> {"n_rows", "n_cols", "columns"}
  - get_columns(df_ref) -> list[str]
  - execute_joins(primary_ref, joins: list[dict]) -> pd.DataFrame
  - last_result_id: str

Actual backend:
  - MultiSourceManager.add_source(name, df, *, origin) -> None
  - MultiSourceManager.get_schema(name) -> dict[str, str]  (col -> dtype)
  - MultiSourceManager.join(left, right, on, how) -> pd.DataFrame
  - schema_matcher.suggest_join_keys(left_df, right_df) -> list[dict]
"""
from __future__ import annotations

import pandas as pd

from data_connectors.multi_source_manager import MultiSourceManager
from data_connectors import schema_matcher
from data_connectors.universal_loader import smart_load


class MSAdapter:
    """Wraps MultiSourceManager to match the spec-assumed interface."""

    def __init__(self) -> None:
        self._mgr = MultiSourceManager()
        self._dfs: dict[str, pd.DataFrame] = {}
        self.last_result_id: str | None = None

    # ------------------------------------------------------------------
    # Spec-assumed interface
    # ------------------------------------------------------------------

    def add_source(self, file_path: str, name: str | None = None) -> str:
        """Load file_path, register in manager, return ref name."""
        df, _ = smart_load(file_path)
        ref = name or file_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        # De-duplicate ref name
        if ref in self._dfs:
            ref = f"{ref}_{len(self._dfs)}"
        self._mgr.add_source(ref, df, origin="upload")
        self._dfs[ref] = df
        return ref

    def add_dataframe(self, df: pd.DataFrame, name: str) -> str:
        """Register a pre-loaded DataFrame. Returns the ref name."""
        ref = name
        if ref in self._dfs:
            ref = f"{ref}_{len(self._dfs)}"
        self._mgr.add_source(ref, df, origin="upload")
        self._dfs[ref] = df
        return ref

    def get_source_info(self, df_ref: str) -> dict:
        df = self._dfs[df_ref]
        return {"n_rows": len(df), "n_cols": len(df.columns), "columns": list(df.columns)}

    def get_columns(self, df_ref: str) -> list[str]:
        return list(self._dfs[df_ref].columns)

    def execute_joins(self, primary_ref: str, joins: list[dict]) -> pd.DataFrame:
        """Execute a chain of joins. Each join dict: {left_ref, right_ref, left_key, right_key, join_type}."""
        result = self._dfs[primary_ref].copy()
        for j in joins:
            right_df = self._dfs.get(j["right_ref"])
            if right_df is None:
                continue
            left_key = j["left_key"]
            right_key = j["right_key"]
            how = j.get("join_type", "left")
            if left_key == right_key:
                result = result.merge(right_df, on=left_key, how=how, suffixes=("", "_dup"))
            else:
                result = result.merge(right_df, left_on=left_key, right_on=right_key,
                                      how=how, suffixes=("", "_dup"))
        result_ref = f"_joined_{primary_ref}"
        self._mgr.add_source(result_ref, result, origin="join")
        self._dfs[result_ref] = result
        self.last_result_id = result_ref
        return result


def detect_join_keys(adapter: MSAdapter, left_ref: str, right_ref: str) -> dict:
    """Detect best join keys between two registered sources.

    Returns dict: {left_key, right_key, match_type, confidence}
    """
    left_df = adapter._dfs.get(left_ref)
    right_df = adapter._dfs.get(right_ref)

    if left_df is None or right_df is None:
        return {"left_key": "", "right_key": "", "match_type": "fuzzy", "confidence": 0.0}

    suggestions = schema_matcher.suggest_join_keys(left_df, right_df)
    if not suggestions:
        # Fallback: first column of each
        return {
            "left_key": left_df.columns[0] if len(left_df.columns) else "",
            "right_key": right_df.columns[0] if len(right_df.columns) else "",
            "match_type": "fuzzy",
            "confidence": 0.0,
        }

    best = suggestions[0]
    name_sim = best.get("name_similarity", 0.0)
    overlap = best.get("value_overlap", 0.0)
    score = best.get("score", (name_sim + overlap) / 2)
    match_type = "exact" if name_sim >= 0.99 and overlap >= 0.95 else "fuzzy"
    return {
        "left_key": best["left_col"],
        "right_key": best["right_col"],
        "match_type": match_type,
        "confidence": round(score, 2),
    }
