"""
config.py

Centralised application configuration. Values are read from
environment variables where possible so the same codebase can move
from development (SQLite) to production (PostgreSQL) without code
changes -- only environment variables differ.
"""

import os
import tempfile
from dataclasses import dataclass

# Streamlit Community Cloud mounts the app's own source folder
# read-only, so a SQLite file (or log file) can never be created
# there for the first time -- it has to live somewhere writable.
# The OS temp directory is writable in every environment this app
# runs in (local dev included), so it's used as the default base
# instead of the current working directory.
_WRITABLE_DIR = os.path.join(tempfile.gettempdir(), "ics_platform")
os.makedirs(_WRITABLE_DIR, exist_ok=True)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable application settings, loaded once at import time."""

    app_name: str = "Intelligent Customer Service Chatbot Platform"
    environment: str = os.getenv("ICS_ENV", "development")
    debug: bool = _get_bool("ICS_DEBUG", True)

    # Database: defaults to a local SQLite file for development.
    # In production, set ICS_DATABASE_URL to a PostgreSQL DSN, e.g.
    # postgresql+psycopg2://user:password@host:5432/ics_db
    database_url: str = os.getenv(
        "ICS_DATABASE_URL",
        f"sqlite:///{os.path.join(_WRITABLE_DIR, 'ics_platform.db')}",
    )

    secret_key: str = os.getenv("ICS_SECRET_KEY", "dev-secret-key-change-in-production")

    session_timeout_minutes: int = int(os.getenv("ICS_SESSION_TIMEOUT_MIN", "60"))

    log_dir: str = os.getenv("ICS_LOG_DIR", _WRITABLE_DIR)
    log_level: str = os.getenv("ICS_LOG_LEVEL", "INFO")

    min_password_length: int = 8


settings = Settings()
