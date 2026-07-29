"""
app_pages/auth_pages.py

Login, registration, and forgot-password forms. On success these
populate st.session_state via constants.SessionKeys and rerun so
app.py routes the user into the authenticated shell.
"""

import streamlit as st

from authentication import login_user, register_user, request_password_reset
from constants import APP_NAME, DEFAULT_ROLE, SessionKeys


def _switch_view(view: str) -> None:
    st.session_state[SessionKeys.AUTH_VIEW] = view
    st.rerun()


def _set_authenticated(result) -> None:
    st.session_state[SessionKeys.IS_AUTHENTICATED] = True
    st.session_state[SessionKeys.AUTH_USER_ID] = result.user_id
    st.session_state[SessionKeys.AUTH_USERNAME] = result.username
    st.session_state[SessionKeys.AUTH_ROLE] = result.role
    st.session_state[SessionKeys.AUTH_FULL_NAME] = result.full_name
    st.session_state[SessionKeys.CURRENT_PAGE] = "dashboard"


def render_login() -> None:
    st.markdown(f'<div class="ics-hero-title" style="font-size:1.8rem;">Welcome back</div>', unsafe_allow_html=True)
    st.caption(f"Sign in to {APP_NAME}")

    with st.form("login_form"):
        identifier = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        remember_me = st.checkbox("Remember me")
        submitted = st.form_submit_button("Log In", use_container_width=True)

    if submitted:
        if not identifier or not password:
            st.error("Please enter both your username/email and password.")
        else:
            result = login_user(identifier, password, remember_me=remember_me)
            if result.success:
                st.success(result.message)
                _set_authenticated(result)
                st.rerun()
            else:
                st.error(result.message)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create an account", use_container_width=True):
            _switch_view("register")
    with c2:
        if st.button("Forgot password?", use_container_width=True):
            _switch_view("forgot_password")


def render_register() -> None:
    st.markdown('<div class="ics-hero-title" style="font-size:1.8rem;">Create your account</div>', unsafe_allow_html=True)
    st.caption("Join in seconds — no credit card required.")

    with st.form("register_form"):
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        if password != confirm_password:
            st.error("Passwords do not match.")
        else:
            result = register_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role=DEFAULT_ROLE.value,
            )
            if result.success:
                st.success(result.message)
                _switch_view("login")
            else:
                st.error(result.message)

    if st.button("Already have an account? Log in", use_container_width=True):
        _switch_view("login")


def render_forgot_password() -> None:
    st.markdown('<div class="ics-hero-title" style="font-size:1.8rem;">Reset your password</div>', unsafe_allow_html=True)
    st.caption("Enter your account email and we'll send reset instructions.")

    with st.form("forgot_password_form"):
        email = st.text_input("Email")
        submitted = st.form_submit_button("Send Reset Instructions", use_container_width=True)

    if submitted:
        if not email:
            st.error("Please enter your email address.")
        else:
            result = request_password_reset(email)
            st.info(result.message)

    if st.button("Back to login", use_container_width=True):
        _switch_view("login")


def render() -> None:
    """Dispatch to the correct auth view based on session state."""

    view = st.session_state.get(SessionKeys.AUTH_VIEW, "login")
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        st.markdown("<br>", unsafe_allow_html=True)
        if view == "register":
            render_register()
        elif view == "forgot_password":
            render_forgot_password()
        else:
            render_login()
