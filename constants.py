"""
constants.py

Centralised constants for the Intelligent Customer Service Chatbot
Platform (ICS). Keeping these in one module means every later phase
(ICS-002 .. ICS-005) can import from here instead of hard-coding
values, which keeps the whole codebase consistent.
"""

from enum import Enum


# ----------------------------------------------------------------------
# Brand / design tokens
# ----------------------------------------------------------------------
class Colors:
    """Central colour palette used by styles.py and all pages."""

    PRIMARY = "#2563EB"
    SECONDARY = "#3B82F6"
    ACCENT = "#60A5FA"
    BACKGROUND = "#F8FAFC"
    DARK_BACKGROUND = "#0F172A"
    TEXT = "#111827"
    TEXT_MUTED = "#6B7280"
    CARD_LIGHT = "rgba(255, 255, 255, 0.75)"
    CARD_DARK = "rgba(15, 23, 42, 0.65)"
    SUCCESS = "#22C55E"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    INFO = "#0EA5E9"


APP_NAME = "Intelligent Customer Service Chatbot Platform"
APP_SHORT_NAME = "ICS Platform"
APP_TAGLINE = "Deliver fast, intelligent and personalized customer support using Artificial Intelligence."


# ----------------------------------------------------------------------
# Roles & permissions (RBAC groundwork used by authentication.py)
# ----------------------------------------------------------------------
class UserRole(str, Enum):
    """Roles supported by the platform. ICS-003 will extend the
    permission matrix; the values themselves must not change so that
    existing stored rows stay valid."""

    ADMIN = "admin"
    SUPPORT_AGENT = "support_agent"
    CUSTOMER = "customer"


ROLE_LABELS = {
    UserRole.ADMIN: "Administrator",
    UserRole.SUPPORT_AGENT: "Support Agent",
    UserRole.CUSTOMER: "Customer",
}

DEFAULT_ROLE = UserRole.CUSTOMER


# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------
class NavItem:
    """Simple container describing one sidebar navigation entry."""

    def __init__(self, key: str, label: str, icon: str, roles: tuple):
        self.key = key
        self.label = label
        self.icon = icon
        self.roles = roles  # roles allowed to see this item


NAV_ITEMS = [
    NavItem("dashboard", "Dashboard", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT, UserRole.CUSTOMER)),
    NavItem("chat", "Chat", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT, UserRole.CUSTOMER)),
    NavItem("knowledge_base", "Knowledge Base", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT, UserRole.CUSTOMER)),
    NavItem("analytics", "Analytics", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    NavItem("reports", "Reports", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    NavItem("admin_console", "Admin Console", "", (UserRole.ADMIN,)),
    NavItem("settings", "Settings", "", (UserRole.ADMIN,)),
    NavItem("profile", "Profile", "", (UserRole.ADMIN, UserRole.SUPPORT_AGENT, UserRole.CUSTOMER)),
]


# ----------------------------------------------------------------------
# Session state keys (avoid magic strings scattered across pages)
# ----------------------------------------------------------------------
class SessionKeys:
    AUTH_USER_ID = "auth_user_id"
    AUTH_USERNAME = "auth_username"
    AUTH_ROLE = "auth_role"
    AUTH_FULL_NAME = "auth_full_name"
    IS_AUTHENTICATED = "is_authenticated"
    CURRENT_PAGE = "current_page"
    THEME = "theme"
    AUTH_VIEW = "auth_view"  # login / register / forgot_password
