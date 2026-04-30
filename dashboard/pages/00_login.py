"""Login / Sign-up page.

Shown by require_auth() when no user is in session.
Uses the mock auth_service (swap for Supabase adapter later).
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _is_streamlit_running() -> bool:
    try:
        import streamlit as st
        st.session_state  # noqa: B018
        return True
    except Exception:
        return False


if _is_streamlit_running():
    import streamlit as st
    from dashboard.components.auth_service import is_authenticated, login, signup
    from dashboard.components.shared_css import inject_shared_css

    st.set_page_config(
        page_title="AutoDS — Sign In",
        page_icon="✦",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    inject_shared_css()

    # If already authenticated, go to the main app
    if is_authenticated():
        st.switch_page("app.py")

    st.markdown(
        """
        <div style="text-align:center;padding:2rem 0 1rem;">
            <div style="font-size:2.5rem;font-weight:800;
                        background:var(--gradient-primary);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                AutoDS
            </div>
            <div style="color:var(--text-muted);font-size:0.875rem;margin-top:0.25rem;">
                Autonomous Data Science Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Sign In", use_container_width=True, type="primary"
            )
        if submitted:
            ok, err = login(email, password)
            if ok:
                st.success("Welcome back!")
                st.switch_page("app.py")
            else:
                st.error(err)

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full Name", placeholder="Jane Smith")
            email_s = st.text_input("Email", placeholder="you@example.com", key="su_email")
            password_s = st.text_input("Password", type="password", key="su_pw")
            confirm_s = st.text_input("Confirm Password", type="password", key="su_cpw")
            submitted_s = st.form_submit_button(
                "Create Account", use_container_width=True, type="primary"
            )
        if submitted_s:
            ok, err = signup(name, email_s, password_s, confirm_s)
            if ok:
                st.success("Account created — you're now signed in.")
                st.switch_page("app.py")
            else:
                st.error(err)
