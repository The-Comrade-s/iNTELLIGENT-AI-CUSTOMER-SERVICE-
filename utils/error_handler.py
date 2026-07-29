"""
utils/error_handler.py

Centralised exception handling: logs the full technical detail while
showing the user a short, friendly message. Used to wrap page
rendering in app.py so one broken page can't crash the whole session.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager

import streamlit as st

logger = logging.getLogger("ics.errors")


@contextmanager
def safe_page(page_name: str):
    """Wrap a page's render() call: unexpected exceptions are logged
    with full detail and the user sees a friendly, non-technical
    message instead of a stack trace."""

    try:
        yield
    except Exception:
        logger.exception("Unhandled error while rendering page '%s'", page_name)
        st.error(
            "Something went wrong loading this page. The issue has been logged — "
            "please try again, or contact an administrator if it persists."
        )
