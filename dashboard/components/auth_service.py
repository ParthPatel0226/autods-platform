"""Mock authentication service backed by st.session_state.

Provides the same interface expected by pages (is_authenticated, current_user,
login, signup, logout, require_auth).  Swap this module for a real Supabase
adapter later without touching callers.
"""

from __future__ import annotations

from typing import TypedDict

SESSION_KEY = "auth_user"


class User(TypedDict):
    id: str
    email: str
    name: str


def is_authenticated() -> bool:
    """Return True when a user is currently logged in."""
    import streamlit as st

    return st.session_state.get(SESSION_KEY) is not None


def current_user() -> User | None:
    """Return the logged-in user dict or None."""
    import streamlit as st

    return st.session_state.get(SESSION_KEY)


def login(email: str, password: str) -> tuple[bool, str]:
    """Attempt login. Returns (success, error_message).

    Mock: any non-empty email + password succeeds.
    """
    import streamlit as st

    email = (email or "").strip()
    password = (password or "").strip()
    if not email or not password:
        return False, "Email and password are required."
    user: User = {"id": email, "email": email, "name": email.split("@")[0]}
    st.session_state[SESSION_KEY] = user
    return True, ""


def signup(
    name: str,
    email: str,
    password: str,
    confirm: str,
) -> tuple[bool, str]:
    """Attempt sign-up. Returns (success, error_message).

    Mock: creates an account immediately; no persistence outside session.
    """
    import streamlit as st

    name = (name or "").strip()
    email = (email or "").strip()
    password = (password or "").strip()
    confirm = (confirm or "").strip()
    if not all([name, email, password, confirm]):
        return False, "All fields are required."
    if password != confirm:
        return False, "Passwords do not match."
    user: User = {"id": email, "email": email, "name": name}
    st.session_state[SESSION_KEY] = user
    return True, ""


def logout() -> None:
    """Log out the current user and clear active project."""
    import streamlit as st
    from dashboard.components import project_service  # lazy — avoids circular dep

    project_service.clear_active()
    st.session_state.pop(SESSION_KEY, None)


def require_auth() -> None:
    """Redirect to login page if the user is not authenticated.

    Call near the top of any page that requires authentication.
    """
    import streamlit as st

    if not is_authenticated():
        st.switch_page("pages/00_login.py")
        st.stop()
