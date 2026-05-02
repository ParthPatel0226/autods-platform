"""Supabase client singleton.

Returns a connected ``supabase.Client`` when SUPABASE_URL / SUPABASE_KEY are
set, or ``None`` to let callers fall back to local storage.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_initialised = False


def get_supabase():
    """Return a cached Supabase client, or None if credentials are absent."""
    global _client, _initialised

    if _initialised:
        return _client

    _initialised = True

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if not url:
        logger.warning(
            "SUPABASE_URL is not set — storage will fall back to local /tmp."
        )
        return None

    if not key:
        logger.warning(
            "SUPABASE_KEY is not set — storage will fall back to local /tmp."
        )
        return None

    try:
        from supabase import create_client  # type: ignore

        _client = create_client(url, key)
        logger.info("Supabase client initialised (url=%s…)", url[:30])
    except ImportError:
        logger.warning(
            "supabase package not installed — storage will fall back to local /tmp."
        )
    except Exception as exc:
        logger.warning("Supabase init failed: %s — falling back to local /tmp.", exc)

    return _client
