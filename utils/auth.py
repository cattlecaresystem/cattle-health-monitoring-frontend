"""
Authentication utilities for Streamlit session state management.
Supports 3-tier role hierarchy: Super Admin → Admin → User.
Includes token validation, expiry detection, and session persistence.
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")

# Debounce: validate token at most once every 30 seconds
_VALIDATION_INTERVAL = 30


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "authenticated": False,
        "token": None,
        "user": None,
        "role": None,
        "effective_role": None,  # super_admin | admin | user
        "lang": _DEFAULT_LANG,
        "theme": "light",
        "current_page": "dashboard",
        "selected_cattle_cid": None,
        "session_expired": False,
        "_last_validated": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _detect_effective_role(user: dict) -> str:
    """
    Determine the effective role from user data.
    Super Admin = explicit super_admin role OR admin with empty farm_ids.
    Admin = admin with specific farm_ids (scoped).
    User = regular user role.
    """
    role = user.get("role", "user")
    if role == "super_admin":
        return "super_admin"
    if role == "admin":
        farm_ids = user.get("farm_ids", [])
        if not farm_ids:
            return "super_admin"
        return "admin"
    return "user"


def login_user(token: str, user: dict):
    """Store authentication data in session state."""
    st.session_state.authenticated = True
    st.session_state.token = token
    st.session_state.user = user
    st.session_state.role = user.get("role", "user")
    st.session_state.effective_role = _detect_effective_role(user)
    st.session_state.session_expired = False


def logout_user():
    """Clear authentication data from session state."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.effective_role = None
    st.session_state.current_page = "login"
    st.session_state.session_expired = False
    st.session_state.selected_cattle_cid = None
    st.session_state._last_validated = 0.0


def handle_session_expired():
    """Mark session as expired and force re-login."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.effective_role = None
    st.session_state.current_page = "login"
    st.session_state.session_expired = True
    st.session_state._last_validated = 0.0


def validate_session() -> bool:
    """
    Validate the current session by calling /auth/me.
    Debounced: only calls the API once per _VALIDATION_INTERVAL seconds.
    Returns True if the token is still valid, False if expired/invalid.
    """
    if not st.session_state.get("authenticated") or not st.session_state.get("token"):
        return False

    # Debounce — skip validation if recently checked
    now = time.time()
    last = st.session_state.get("_last_validated", 0.0)
    if now - last < _VALIDATION_INTERVAL:
        return True

    from services.api_client import api_get_me
    result = api_get_me(st.session_state.token)
    if result is None:
        # Only expire if _handle() hasn't already done it
        if st.session_state.get("authenticated"):
            handle_session_expired()
        return False

    # Token is valid — refresh user data and update timestamp
    st.session_state._last_validated = now
    st.session_state.user = result
    st.session_state.role = result.get("role", "user")
    st.session_state.effective_role = _detect_effective_role(result)
    return True


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def is_super_admin() -> bool:
    return st.session_state.get("effective_role") == "super_admin"


def is_admin() -> bool:
    return st.session_state.get("effective_role") in ("admin", "super_admin")


def is_user() -> bool:
    return st.session_state.get("effective_role") == "user"


def get_effective_role() -> str:
    return st.session_state.get("effective_role", "user")


def get_token() -> str:
    return st.session_state.get("token", "")


def get_user() -> dict:
    return st.session_state.get("user") or {}


def get_lang() -> str:
    return st.session_state.get("lang", "en")


def get_theme() -> str:
    return st.session_state.get("theme", "light")


def navigate_to(page: str, **kwargs):
    """Navigate to a different page, with optional extra state."""
    st.session_state.current_page = page
    for key, value in kwargs.items():
        st.session_state[key] = value
