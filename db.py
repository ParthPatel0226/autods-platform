"""Supabase client wrapper for AutoDS Platform.

Provides singleton client, user session helpers, and project CRUD.
"""

from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import Client, create_client


def get_client() -> Client:
    """Return a Supabase client (singleton per Streamlit session)."""
    if "supabase_client" not in st.session_state:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["anon_key"]
        st.session_state.supabase_client = create_client(url, key)
    return st.session_state.supabase_client


def get_current_user() -> Any | None:
    """Return the logged-in user object, or None if not authenticated."""
    session = st.session_state.get("supabase_session")
    if session is None:
        return None
    return session.user


def get_user_profile(user_id: str) -> dict | None:
    """Fetch a user's profile from the profiles table."""
    client = get_client()
    resp = client.table("profiles").select("*").eq("id", user_id).single().execute()
    return resp.data


def create_project(user_id: str, name: str, domain: str | None = None) -> dict:
    """Insert a new project for the given user."""
    client = get_client()
    resp = (
        client.table("projects")
        .insert({"user_id": user_id, "name": name, "domain": domain})
        .execute()
    )
    return resp.data[0]


def get_user_projects(user_id: str) -> list[dict]:
    """List all projects for the given user, newest first."""
    client = get_client()
    resp = (
        client.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data
