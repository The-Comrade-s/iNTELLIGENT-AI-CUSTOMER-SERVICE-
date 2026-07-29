"""
database.py

SQLAlchemy models and session/engine management for the ICS
platform. Uses SQLite for development (see config.py) and is
PostgreSQL-ready for production simply by changing ICS_DATABASE_URL.

Tables (ICS-001):
    - users            core account + credentials
    - profiles         extended profile info (1:1 with users)
    - sessions         active login sessions (for "remember me" /
                        session tracking, separate from Streamlit's
                        own session_state)
    - activity_logs    audit trail of user actions

Later phases (ICS-002 onward) will ADD new tables in their own
migration functions rather than editing these classes, to preserve
backward compatibility.
"""

from __future__ import annotations

import datetime as dt
import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import settings

logger = logging.getLogger("ics.database")


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in the project."""

    pass


class User(Base):
    """Core account record: credentials, role, and account status."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="customer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)

    profile = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "ActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    """Extended profile information, one row per user."""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    full_name = Column(String(128), nullable=False, default="")
    phone = Column(String(32), nullable=True)
    company = Column(String(128), nullable=True)
    job_title = Column(String(128), nullable=True)
    avatar_path = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)

    user = relationship("User", back_populates="profile")


class UserSession(Base):
    """Tracks issued sessions for audit / 'remember me' support."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    remember_me = Column(Boolean, nullable=False, default=False)
    is_revoked = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="sessions")


class ActivityLog(Base):
    """Audit log entry describing a single user action."""

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="activity_logs")


# ----------------------------------------------------------------------
# ICS-002: chatbot engine tables
# ----------------------------------------------------------------------
class Conversation(Base):
    """A single chat session between a customer and the AI (and,
    potentially, a human agent after escalation)."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False, default="New Conversation")
    is_pinned = Column(Boolean, nullable=False, default=False)
    is_favourite = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    user = relationship("User")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    escalation = relationship(
        "Escalation", back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )


class Message(Base):
    """A single message (customer or AI) inside a conversation."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(String(16), nullable=False)  # 'customer' | 'ai' | 'agent'
    content = Column(Text, nullable=False)
    intent = Column(String(64), nullable=True)
    confidence = Column(Integer, nullable=True)  # stored as percentage 0-100
    sentiment = Column(String(16), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class FAQ(Base):
    """A knowledge-base FAQ entry, searchable by the chatbot engine
    and manageable from the ICS-003 admin CMS."""

    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, default="General")
    keywords = Column(String(255), nullable=True)
    status = Column(String(16), nullable=False, default="published")  # draft|published|archived
    views = Column(Integer, nullable=False, default=0)
    helpful_votes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)


class Escalation(Base):
    """Tracks a conversation escalated from AI to a human agent."""

    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, unique=True)
    reason = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="open")  # open|assigned|resolved
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="escalation")
    assigned_agent = relationship("User")


# ----------------------------------------------------------------------
# ICS-003: admin portal tables
# ----------------------------------------------------------------------
class Notification(Base):
    """A system or user-facing notification shown in the notification
    centre (e.g. new escalation, knowledge base update)."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = broadcast to admins
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(32), nullable=False, default="system")  # system|escalation|knowledge_base|announcement
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)


class Feedback(Base):
    """Customer rating/comment about a conversation or a specific
    AI response."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    conversation = relationship("Conversation")


class AppSetting(Base):
    """Simple admin-editable key/value settings store (branding, AI
    configuration, chat behaviour). Kept generic so new settings can
    be added without a schema migration."""

    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)


# ----------------------------------------------------------------------
# ICS-004: document intelligence, profiling, prompts
# ----------------------------------------------------------------------
class UploadedDocument(Base):
    """A file a customer uploaded during a conversation, plus the
    AI-generated summary produced for it."""

    __tablename__ = "uploaded_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)
    summary = Column(Text, nullable=True)
    extracted_text_preview = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    user = relationship("User")


class CustomerProfile(Base):
    """Aggregated, denormalised profile signals about a customer,
    refreshed as new conversations happen. Kept separate from
    ``profiles`` (account info) since this is behavioural/derived
    data rather than user-entered data."""

    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    preferred_language = Column(String(8), nullable=False, default="en")
    total_conversations = Column(Integer, nullable=False, default=0)
    total_escalations = Column(Integer, nullable=False, default=0)
    most_frequent_intent = Column(String(64), nullable=True)
    average_sentiment_score = Column(Integer, nullable=False, default=0)  # stored as -100..100
    last_interaction_at = Column(DateTime, nullable=True)

    user = relationship("User")


class PromptTemplate(Base):
    """Admin-editable prompt templates used by different stages of
    the pipeline (system, escalation, knowledge, translation,
    summarisation)."""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False)
    label = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)


# ----------------------------------------------------------------------
# Engine / session management
# ----------------------------------------------------------------------
_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they do not already exist. Safe to call
    on every app startup -- it never drops or alters existing data."""

    Base.metadata.create_all(bind=_engine)
    logger.info("Database initialised at %s", settings.database_url)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context-managed DB session: ``with get_db() as db: ...``"""

    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_activity(
    db: Session,
    user_id: Optional[int],
    action: str,
    description: str = "",
    ip_address: Optional[str] = None,
) -> None:
    """Write a single audit-log row. Never raises to the caller --
    logging failures must not break the user-facing feature."""

    try:
        entry = ActivityLog(
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to write activity log: %s", exc)
