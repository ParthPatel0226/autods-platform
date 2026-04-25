"""Memory and persistence layer for AutoDS.

Handles:
- SQLite: Session state persistence, decision logging, audit trail
- ChromaDB: Vector memory for semantic search over past analyses
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionStore:
    """SQLite-backed session persistence.
    
    Stores complete pipeline states so users can resume sessions,
    compare results, and export configurations for reproducibility.
    """

    def __init__(self, db_path: str = "sessions/autods.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    domain TEXT DEFAULT 'generic',
                    user_goal TEXT DEFAULT '',
                    data_source_name TEXT DEFAULT '',
                    state_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    step TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reasoning TEXT DEFAULT '',
                    user_choice BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    tool_name TEXT DEFAULT '',
                    parameters TEXT DEFAULT '{}',
                    result_summary TEXT DEFAULT '',
                    duration_seconds REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'success',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def save_session(self, session_id: str, state: dict):
        """Save or update a session."""
        now = datetime.now(timezone.utc).isoformat()
        state_json = json.dumps(state, default=str)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, created_at, updated_at, status, domain, user_goal, data_source_name, state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = ?,
                    status = ?,
                    domain = ?,
                    user_goal = ?,
                    state_json = ?
            """, (
                session_id, now, now,
                state.get("workflow_status", "running"),
                state.get("detected_domain", "generic"),
                state.get("user_goal", ""),
                state.get("data_sources", [{}])[0].get("source_name", "") if state.get("data_sources") else "",
                state_json,
                now,
                state.get("workflow_status", "running"),
                state.get("detected_domain", "generic"),
                state.get("user_goal", ""),
                state_json,
            ))
            conn.commit()

    def load_session(self, session_id: str) -> dict | None:
        """Load a session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT session_id, created_at, updated_at, status, domain, user_goal, data_source_name
                FROM sessions ORDER BY updated_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [
                {
                    "session_id": r[0], "created_at": r[1], "updated_at": r[2],
                    "status": r[3], "domain": r[4], "user_goal": r[5],
                    "data_source_name": r[6],
                }
                for r in rows
            ]

    def delete_session(self, session_id: str):
        """Delete a session and its logs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM decision_log WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM audit_trail WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    def log_decision(self, session_id: str, step: str, decision: str,
                     reasoning: str = "", user_choice: bool = False):
        """Log a pipeline decision."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO decision_log (session_id, timestamp, step, decision, reasoning, user_choice)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, now, step, decision, reasoning, user_choice))
            conn.commit()

    def log_audit(self, session_id: str, action: str, tool_name: str = "",
                  parameters: dict = None, result_summary: str = "",
                  duration_seconds: float = 0.0, status: str = "success"):
        """Log an audit trail entry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_trail (session_id, timestamp, action, tool_name, parameters, result_summary, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, now, action, tool_name,
                  json.dumps(parameters or {}), result_summary,
                  duration_seconds, status))
            conn.commit()

    def get_decision_log(self, session_id: str) -> list[dict]:
        """Get all decisions for a session."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT timestamp, step, decision, reasoning, user_choice
                FROM decision_log WHERE session_id = ? ORDER BY timestamp
            """, (session_id,)).fetchall()
            return [
                {"timestamp": r[0], "step": r[1], "decision": r[2],
                 "reasoning": r[3], "user_choice": bool(r[4])}
                for r in rows
            ]

    def get_audit_trail(self, session_id: str) -> list[dict]:
        """Get full audit trail for a session."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT timestamp, action, tool_name, parameters, result_summary, duration_seconds, status
                FROM audit_trail WHERE session_id = ? ORDER BY timestamp
            """, (session_id,)).fetchall()
            return [
                {"timestamp": r[0], "action": r[1], "tool_name": r[2],
                 "parameters": json.loads(r[3]), "result_summary": r[4],
                 "duration_seconds": r[5], "status": r[6]}
                for r in rows
            ]


class VectorMemory:
    """ChromaDB-backed vector memory for semantic search over past analyses.
    
    Stores embeddings of past EDA findings, model results, and insights
    so the Follow-Up Agent can reference previous work.
    """

    def __init__(self, persist_dir: str = "sessions/chromadb"):
        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Lazy-initialize ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self.persist_dir)
                self._collection = self._client.get_or_create_collection(
                    name="autods_memory",
                    metadata={"description": "AutoDS analysis memory"}
                )
            except ImportError:
                logger.warning("ChromaDB not installed. Vector memory disabled.")
                return None
            except Exception as e:
                logger.warning("Failed to initialize ChromaDB: %s", e)
                return None
        return self._collection

    def store(self, session_id: str, step: str, content: str, metadata: dict = None):
        """Store a memory entry with vector embedding."""
        collection = self._get_collection()
        if collection is None:
            return

        doc_id = f"{session_id}_{step}_{hash(content) % 10**8}"
        meta = {"session_id": session_id, "step": step}
        if metadata:
            meta.update({k: str(v) for k, v in metadata.items()})

        try:
            collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta],
            )
        except Exception as e:
            logger.warning("Failed to store memory: %s", e)

    def search(self, query: str, n_results: int = 5, session_id: str = None) -> list[dict]:
        """Search memory for relevant past analyses."""
        collection = self._get_collection()
        if collection is None:
            return []

        try:
            where_filter = {"session_id": session_id} if session_id else None
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
            return [
                {
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                }
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ]
        except Exception as e:
            logger.warning("Memory search failed: %s", e)
            return []

    def clear(self, session_id: str = None):
        """Clear memory entries."""
        collection = self._get_collection()
        if collection is None:
            return

        try:
            if session_id:
                # Delete entries for specific session
                results = collection.get(where={"session_id": session_id})
                if results["ids"]:
                    collection.delete(ids=results["ids"])
            else:
                # Delete all
                self._client.delete_collection("autods_memory")
                self._collection = None
        except Exception as e:
            logger.warning("Failed to clear memory: %s", e)
