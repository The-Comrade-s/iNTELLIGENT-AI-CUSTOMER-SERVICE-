"""
tests/conftest.py

Points the app at a throwaway SQLite file for the test session so
tests never touch a developer's real ics_platform.db, and initialises
the schema once before tests run.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["ICS_DATABASE_URL"] = "sqlite:///./test_ics_platform.db"

import pytest  # noqa: E402

from database import Base, init_db  # noqa: E402
from database import _engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    init_db()
    yield
    Base.metadata.drop_all(bind=_engine)
    db_path = "./test_ics_platform.db"
    if os.path.exists(db_path):
        os.remove(db_path)
