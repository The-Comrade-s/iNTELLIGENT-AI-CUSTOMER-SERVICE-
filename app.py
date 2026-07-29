"""
app.py

Entry point for the Intelligent Customer Service Chatbot Platform.
Run with:

    streamlit run app.py

This module owns page routing (landing -> auth -> authenticated
shell) and the sidebar navigation. Individual pages live under
app_pages/ and each expose a render() function so this file stays thin
as later ICS phases add more pages.
"""

import logging
import os

import streamlit as st

from authentication import has_permission, logout_user
from config import settings
from constants import APP_SHORT_NAME, NAV_ITEMS, SessionKeys, UserRole
from chatbot.faq_engine import seed_default_faqs_if_empty
from database import init_db
from services.prompt_service import seed_default_prompts_if_empty
from app_pages import (
    admin_console,
    analytics,
    auth_pages,
    chat,
    dashboard,
    knowledge_base,
    landing,
    profile,
    reports,
    settings as settings_page,
)
from styles import apply_global_styles
from utils.error_handler import safe_page


def _configure_logging() -> None:
    os.makedirs(settings.log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(settings.log_dir, "app.log")),
            logging.StreamHandler(),
        ],
    )


def _init_session_state() -> None:
    defaults = {
        SessionKeys.IS_AUTHENTICATED: False,
        SessionKeys.AUTH_USER_ID: None,
        SessionKeys.AUTH_USERNAME: None,
        SessionKeys.AUTH_ROLE: None,
        SessionKeys.AUTH_FULL_NAME: None,
        SessionKeys.CURRENT_PAGE: "landing",
        SessionKeys.THEME: "light",
        SessionKeys.AUTH_VIEW: "login",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_sidebar() -> None:
    role = st.session_state.get(SessionKeys.AUTH_ROLE)
    full_name = st.session_state.get(SessionKeys.AUTH_FULL_NAME) or "User"

    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center;padding:0.5rem 0 1rem 0;">
                <div style="font-size:1.9rem;">🤖</div>
                <div style="font-weight:800;font-size:1.05rem;">{APP_SHORT_NAME}</div>
                <div style="color:#6B7280;font-size:0.8rem;">{full_name}</div>
            </div>
            <hr style="border-color:rgba(148,163,184,0.2);">
            """,
            unsafe_allow_html=True,
        )

        for item in NAV_ITEMS:
            if not has_permission(role, item.roles):
                continue
            is_active = st.session_state[SessionKeys.CURRENT_PAGE] == item.key
            label = f"**{item.label}**" if is_active else f"{item.label}"
            if st.button(label, key=f"nav_{item.key}", use_container_width=True):
                st.session_state[SessionKeys.CURRENT_PAGE] = item.key
                st.rerun()

        st.markdown("<hr style='border-color:rgba(148,163,184,0.2);'>", unsafe_allow_html=True)
        theme_label = "Dark Mode" if st.session_state[SessionKeys.THEME] == "light" else "Light Mode"
        if st.button(theme_label, use_container_width=True):
            st.session_state[SessionKeys.THEME] = "dark" if st.session_state[SessionKeys.THEME] == "light" else "light"
            st.rerun()

        if st.button("Logout", use_container_width=True):
            logout_user(st.session_state.get(SessionKeys.AUTH_USER_ID))
            for key in (
                SessionKeys.IS_AUTHENTICATED,
                SessionKeys.AUTH_USER_ID,
                SessionKeys.AUTH_USERNAME,
                SessionKeys.AUTH_ROLE,
                SessionKeys.AUTH_FULL_NAME,
            ):
                st.session_state[key] = None if key != SessionKeys.IS_AUTHENTICATED else False
            st.session_state[SessionKeys.CURRENT_PAGE] = "landing"
            st.session_state[SessionKeys.AUTH_VIEW] = "login"
            st.rerun()


def _route_authenticated_page() -> None:
    page = st.session_state[SessionKeys.CURRENT_PAGE]
    role = st.session_state.get(SessionKeys.AUTH_ROLE)

    matching_item = next((item for item in NAV_ITEMS if item.key == page), None)
    if matching_item and not has_permission(role, matching_item.roles):
        st.warning("You do not have permission to view that page.")
        st.session_state[SessionKeys.CURRENT_PAGE] = "dashboard"
        page = "dashboard"

    if page == "dashboard":
        with safe_page("dashboard"):
            dashboard.render(st.session_state.get(SessionKeys.AUTH_FULL_NAME) or "there")
    elif page == "profile":
        with safe_page("profile"):
            profile.render(st.session_state[SessionKeys.AUTH_USER_ID])
    elif page == "chat":
        with safe_page("chat"):
            chat.render(st.session_state[SessionKeys.AUTH_USER_ID])
    elif page == "knowledge_base":
        with safe_page("knowledge_base"):
            knowledge_base.render()
    elif page == "analytics":
        with safe_page("analytics"):
            analytics.render()
    elif page == "reports":
        with safe_page("reports"):
            reports.render()
    elif page == "admin_console":
        with safe_page("admin_console"):
            admin_console.render(st.session_state[SessionKeys.AUTH_USER_ID])
    elif page == "settings":
        with safe_page("settings"):
            settings_page.render()
    else:
        with safe_page("dashboard"):
            dashboard.render(st.session_state.get(SessionKeys.AUTH_FULL_NAME) or "there")


def main() -> None:
    st.set_page_config(
        page_title=APP_SHORT_NAME,
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded" if st.session_state.get(SessionKeys.IS_AUTHENTICATED) else "collapsed",
    )

    _configure_logging()
    init_db()
    seed_default_faqs_if_empty()
    seed_default_prompts_if_empty()
    _init_session_state()

    apply_global_styles(dark_mode=st.session_state[SessionKeys.THEME] == "dark")

    if st.session_state[SessionKeys.IS_AUTHENTICATED]:
        _render_sidebar()
        _route_authenticated_page()
    else:
        # Unauthenticated visitors see the landing page until they choose
        # to log in / sign up, at which point the auth forms take over.
        if st.session_state.get("_show_auth", False):
            auth_pages.render()
            _, mid, _ = st.columns([1, 1, 1])
            with mid:
                if st.button("Back to home", use_container_width=True):
                    st.session_state["_show_auth"] = False
                    st.rerun()
        else:
            landing.render()
            st.markdown("<br>", unsafe_allow_html=True)
            _, mid, _ = st.columns([1, 1, 1])
            with mid:
                if st.button("Log In / Sign Up", use_container_width=True):
                    st.session_state["_show_auth"] = True
                    st.rerun()


if __name__ == "__main__":
    main()
