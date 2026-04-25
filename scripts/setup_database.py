"""Initialize DuckDB and SQLite databases.

Usage:
    python scripts/setup_database.py
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Create directories
    for d in ["data", "sessions", "logs", "outputs", "mlruns"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Initialize session store
    from core.memory import SessionStore
    store = SessionStore()
    logger.info("Session database initialized at sessions/autods.db")

    logger.info("Database setup complete.")


if __name__ == "__main__":
    main()
