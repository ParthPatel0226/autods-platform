"""Authentication module for AutoDS Platform.

Provides login/signup forms, logout, and auth gate using Supabase Auth.
"""

from __future__ import annotations

import streamlit as st

from db import get_client


def login_form() -> bool:
    """Render login form. Returns True if login succeeded this run."""
    with st.form("login_form", clear_on_submit=True):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted and email and password:
        try:
            client = get_client()
            resp = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state.supabase_session = resp.session
            return True
        except Exception as exc:
            st.error(f"Login failed: {exc}")
    return False


def signup_form() -> bool:
    """Render signup form. Returns True if signup succeeded this run."""
    with st.form("signup_form", clear_on_submit=True):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Sign Up", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Email and password are required.")
            return False
        if password != confirm:
            st.error("Passwords do not match.")
            return False
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return False
        try:
            client = get_client()
            resp = client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}},
                }
            )
            if resp.session:
                st.session_state.supabase_session = resp.session
                # Insert profile row (trigger was removed)
                user = resp.session.user
                client.table("profiles").upsert(
                    {
                        "id": user.id,
                        "email": user.email,
                        "full_name": full_name or None,
                    }
                ).execute()
                return True
            else:
                st.success("Check your email for a confirmation link.")
                return False
        except Exception as exc:
            st.error(f"Signup failed: {exc}")
    return False


def logout() -> None:
    """Sign out and clear session state."""
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:
        pass
    for key in ["supabase_session", "supabase_client"]:
        st.session_state.pop(key, None)


def require_auth():
    """Auth gate. Returns user if logged in, shows login/signup page if not.

    Usage at top of app:
        user = require_auth()  # blocks here if not logged in
    """
    # Already authenticated
    session = st.session_state.get("supabase_session")
    if session is not None:
        return session.user

    # Show auth page
    st.markdown(
        "<h1 style='text-align:center;'>AutoDS Platform</h1>"
        "<p style='text-align:center;opacity:0.7;'>Sign in to continue</p>",
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])

    with login_tab:
        if login_form():
            st.rerun()

    with signup_tab:
        if signup_form():
            st.rerun()

    st.stop()
