# Spec 02 — Auth Placeholder (`auth_service.py` + login page)

## Goal

Gate the app behind a login screen. No real backend yet — any non-empty input passes. All callers go through `auth_service` so swapping in real auth later is a one-file change.

## File: `dashboard/components/auth_service.py`

```python
"""
auth_service.py — Auth abstraction with session_state-backed mock implementation.

To wire real auth (Supabase / FastAPI / etc.) later, swap the body of these
functions to call the real backend. Callers do not change.
"""
from __future__ import annotations
from typing import Optional, TypedDict
from datetime import datetime
import streamlit as st


class User(TypedDict):
    id: str
    name: str
    email: str
    created_at: str


SESSION_KEY = "auth_user"


def is_authenticated() -> bool:
    return SESSION_KEY in st.session_state and st.session_state[SESSION_KEY] is not None


def current_user() -> Optional[User]:
    return st.session_state.get(SESSION_KEY)


def login(email: str, password: str) -> tuple[bool, Optional[str]]:
    """Mock login. Any non-empty email + password succeeds.
    Returns (success, error_message)."""
    email = (email or "").strip()
    password = password or ""
    if not email or "@" not in email:
        return False, "Please enter a valid email."
    if len(password) < 1:
        return False, "Please enter your password."
    user: User = {
        "id": email,  # mock — use email as id
        "name": email.split("@")[0].title(),
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
    }
    st.session_state[SESSION_KEY] = user
    return True, None


def signup(name: str, email: str, password: str, confirm: str) -> tuple[bool, Optional[str]]:
    """Mock signup. Validates basic shape, then logs user in."""
    name = (name or "").strip()
    email = (email or "").strip()
    if not name:
        return False, "Please enter your name."
    if not email or "@" not in email:
        return False, "Please enter a valid email."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirm:
        return False, "Passwords don't match."
    user: User = {
        "id": email,
        "name": name,
        "email": email,
        "created_at": datetime.utcnow().isoformat(),
    }
    st.session_state[SESSION_KEY] = user
    return True, None


def logout() -> None:
    if SESSION_KEY in st.session_state:
        del st.session_state[SESSION_KEY]
    # Also clear active project on logout
    from dashboard.components import project_service
    project_service.clear_active()


def require_auth() -> bool:
    """Use at the top of any page that requires login. Returns True if authed.
    If not, renders a redirect to login and returns False. Caller should st.stop()."""
    if not is_authenticated():
        st.switch_page("pages/00_login.py")
        return False
    return True
```

## File: `dashboard/pages/00_login.py`

Numbered `00` so it sorts before all pipeline pages in Streamlit's auto-discovered nav. The custom sidebar will hide it from regular navigation.

```python
"""Login + signup screens. Mock auth — any non-empty input proceeds."""
import streamlit as st

from dashboard.components import auth_service
from dashboard.components.shared_css import inject_shared_css

st.set_page_config(page_title="AutoDS — Sign In", page_icon="🔐", layout="centered",
                   initial_sidebar_state="collapsed")

inject_shared_css()

# Hide default sidebar entirely on login page
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stMain"] > div { padding-top: 4rem; }
.login-card {
  max-width: 420px; margin: 0 auto;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 20px; padding: 36px 32px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 50px -25px rgba(0,0,0,0.7), 0 0 0 1px rgba(139,92,246,0.08);
}
.login-brand {
  text-align: center; margin-bottom: 28px;
}
.login-brand-mark {
  width: 48px; height: 48px; margin: 0 auto 12px;
  background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%);
  border-radius: 12px;
  display: grid; place-items: center;
  font-family: 'Instrument Serif', serif; font-size: 28px; font-style: italic; color: white;
  box-shadow: 0 0 24px rgba(139,92,246,0.5);
}
.login-title {
  font-family: 'Instrument Serif', serif; font-size: 32px;
  background: linear-gradient(135deg, #C5C7FF 0%, #A855F7 50%, #EC4899 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 6px;
}
.login-subtitle { color: var(--text-muted); font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# If already authed, send home
if auth_service.is_authenticated():
    st.switch_page("app.py")
    st.stop()

# Tab selector
tab = st.radio("Auth mode", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed")

st.markdown('<div class="login-card">', unsafe_allow_html=True)
st.markdown('<div class="login-brand">'
            '<div class="login-brand-mark">A</div>'
            '<div class="login-title">Welcome to AutoDS</div>'
            f'<div class="login-subtitle">{"Sign in to continue" if tab == "Sign in" else "Create your account"}</div>'
            '</div>', unsafe_allow_html=True)

if tab == "Sign in":
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        if submitted:
            ok, err = auth_service.login(email, password)
            if ok:
                st.switch_page("app.py")
            else:
                st.error(err)
    st.caption("New here? Switch to **Create account** above.")
else:
    with st.form("signup_form", clear_on_submit=False):
        name = st.text_input("Name", placeholder="Your name")
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password", placeholder="At least 6 characters")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted:
            ok, err = auth_service.signup(name, email, password, confirm)
            if ok:
                st.switch_page("app.py")
            else:
                st.error(err)
    st.caption("Already have an account? Switch to **Sign in** above.")

st.markdown('</div>', unsafe_allow_html=True)

# Footnote
st.markdown(
    '<div style="text-align:center;margin-top:20px;color:var(--text-faint);font-size:12px;">'
    'Auth is in placeholder mode — any valid-looking input proceeds.'
    '</div>',
    unsafe_allow_html=True,
)
```

## Auth gate in `app.py`

Add at the top of `dashboard/app.py` (after imports, before main UI render):

```python
from dashboard.components import auth_service

if not auth_service.is_authenticated():
    st.switch_page("pages/00_login.py")
    st.stop()
```

## Notes for implementer

- `st.switch_page` requires Streamlit 1.30+. If the project pins an older version, use `st.experimental_rerun()` plus a session-state flag instead. Check `requirements.txt`.
- The login page's `st.set_page_config(layout="centered")` — pipeline pages should keep `wide`. Each page sets its own.
- Mock auth purposely accepts almost anything. Do not add password complexity rules beyond the existing 6-char minimum — easy demo flow.
