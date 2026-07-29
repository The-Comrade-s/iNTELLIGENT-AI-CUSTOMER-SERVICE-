"""
authentication.py

Handles user registration, login, logout, password hashing, session
issuance, and role-based access control (RBAC) helpers.

Password hashing uses PBKDF2-HMAC-SHA256 with a per-user random salt
(stdlib only -- no extra native dependency required). This is a
well-vetted, NIST-recommended construction for password storage.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import logging
import os
import re
import secrets
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.exc import IntegrityError

from config import settings
from constants import DEFAULT_ROLE, UserRole
from database import Profile, User, UserSession, get_db, log_activity

logger = logging.getLogger("ics.auth")

_PBKDF2_ITERATIONS = 260_000
_SALT_BYTES = 16


# ----------------------------------------------------------------------
# Password hashing
# ----------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Return a salted PBKDF2 hash string encoded as
    ``pbkdf2_sha256$iterations$salt_hex$hash_hex``."""

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Constant-time verification of a password against a stored hash."""

    try:
        algorithm, iterations_s, salt_hex, hash_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(candidate, expected)
    except (ValueError, AttributeError):
        return False


def password_strength_errors(password: str) -> list[str]:
    """Return a list of human-readable validation errors; empty list
    means the password satisfies the minimum policy."""

    errors = []
    if len(password) < settings.min_password_length:
        errors.append(f"Password must be at least {settings.min_password_length} characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    return errors


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


# ----------------------------------------------------------------------
# Result types
# ----------------------------------------------------------------------
@dataclass
class AuthResult:
    success: bool
    message: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    full_name: Optional[str] = None


# ----------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------
def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str = DEFAULT_ROLE.value,
) -> AuthResult:
    """Create a new user + profile row. Validates input, enforces
    unique username/email, and hashes the password before storage."""

    username = username.strip()
    email = email.strip().lower()

    if not username or len(username) < 3:
        return AuthResult(False, "Username must be at least 3 characters long.")
    if not is_valid_email(email):
        return AuthResult(False, "Please enter a valid email address.")
    strength_errors = password_strength_errors(password)
    if strength_errors:
        return AuthResult(False, " ".join(strength_errors))
    if role not in {r.value for r in UserRole}:
        role = DEFAULT_ROLE.value

    with get_db() as db:
        existing = (
            db.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )
        if existing:
            return AuthResult(False, "A user with that username or email already exists.")

        try:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
            )
            db.add(user)
            db.flush()  # populate user.id before creating the profile

            profile = Profile(user_id=user.id, full_name=full_name.strip() or username)
            db.add(profile)

            log_activity(db, user.id, "register", f"New account created ({role}).")

            return AuthResult(
                success=True,
                message="Account created successfully. You can now log in.",
                user_id=user.id,
                username=user.username,
                role=user.role,
                full_name=profile.full_name,
            )
        except IntegrityError:
            db.rollback()
            return AuthResult(False, "A user with that username or email already exists.")


# ----------------------------------------------------------------------
# Login / logout / sessions
# ----------------------------------------------------------------------
def login_user(identifier: str, password: str, remember_me: bool = False) -> AuthResult:
    """Authenticate by username or email + password. Updates
    last_login_at and, on success, issues a tracked session token.
    Applies brute-force protection: after 5 consecutive failed
    attempts, the account is locked for 15 minutes."""

    identifier = identifier.strip()
    _MAX_FAILED_ATTEMPTS = 5
    _LOCKOUT_MINUTES = 15

    with get_db() as db:
        user = (
            db.query(User)
            .filter((User.username == identifier) | (User.email == identifier.lower()))
            .first()
        )

        if user and user.locked_until and user.locked_until > dt.datetime.utcnow():
            remaining = int((user.locked_until - dt.datetime.utcnow()).total_seconds() / 60) + 1
            return AuthResult(False, f"Too many failed attempts. Try again in {remaining} minute(s).")

        if not user or not verify_password(password, user.password_hash):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
                    user.locked_until = dt.datetime.utcnow() + dt.timedelta(minutes=_LOCKOUT_MINUTES)
                    log_activity(db, user.id, "account_locked", "Account locked after repeated failed logins.")
            log_activity(db, user.id if user else None, "login_failed", f"Failed login for '{identifier}'.")
            return AuthResult(False, "Incorrect username/email or password.")

        if not user.is_active:
            return AuthResult(False, "This account has been deactivated. Contact an administrator.")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = dt.datetime.utcnow()

        token_lifetime_days = 30 if remember_me else 0
        expires_at = dt.datetime.utcnow() + dt.timedelta(
            days=token_lifetime_days, minutes=0 if remember_me else settings.session_timeout_minutes
        )
        session_row = UserSession(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            expires_at=expires_at,
            remember_me=remember_me,
        )
        db.add(session_row)

        log_activity(db, user.id, "login_success", "User logged in.")

        full_name = user.profile.full_name if user.profile else user.username
        return AuthResult(
            success=True,
            message=f"Welcome back, {full_name}!",
            user_id=user.id,
            username=user.username,
            role=user.role,
            full_name=full_name,
        )


def logout_user(user_id: Optional[int]) -> None:
    """Revoke session tracking rows and log the logout event. The
    caller is still responsible for clearing Streamlit session_state."""

    if user_id is None:
        return
    with get_db() as db:
        db.query(UserSession).filter(
            UserSession.user_id == user_id, UserSession.is_revoked.is_(False)
        ).update({"is_revoked": True})
        log_activity(db, user_id, "logout", "User logged out.")


def request_password_reset(email: str) -> AuthResult:
    """Demo-friendly 'forgot password' flow. In production this would
    email a signed reset link; here it confirms whether an account
    exists without leaking which part (username/email) was wrong."""

    email = email.strip().lower()
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Intentionally vague to avoid user enumeration.
            return AuthResult(True, "If that email is registered, reset instructions have been sent.")
        log_activity(db, user.id, "password_reset_requested", "Password reset requested.")
        return AuthResult(True, "If that email is registered, reset instructions have been sent.")


def reset_password(email: str, new_password: str) -> AuthResult:
    """Complete a password reset (demo flow: no email token verification
    yet -- ICS-005 hardens this with signed, expiring tokens)."""

    strength_errors = password_strength_errors(new_password)
    if strength_errors:
        return AuthResult(False, " ".join(strength_errors))

    email = email.strip().lower()
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return AuthResult(False, "No account found with that email address.")
        user.password_hash = hash_password(new_password)
        log_activity(db, user.id, "password_reset", "Password reset completed.")
        return AuthResult(True, "Password updated successfully. You can now log in.")


def change_password(user_id: int, current_password: str, new_password: str) -> AuthResult:
    """Change password for an already-authenticated user."""

    strength_errors = password_strength_errors(new_password)
    if strength_errors:
        return AuthResult(False, " ".join(strength_errors))

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not verify_password(current_password, user.password_hash):
            return AuthResult(False, "Current password is incorrect.")
        user.password_hash = hash_password(new_password)
        log_activity(db, user.id, "password_change", "Password changed by user.")
        return AuthResult(True, "Password changed successfully.")


# ----------------------------------------------------------------------
# RBAC helpers
# ----------------------------------------------------------------------
def has_permission(role: Optional[str], allowed_roles: tuple) -> bool:
    """Check whether a role string is within an allowed-roles tuple of
    UserRole members. Used by app.py / pages to gate navigation."""

    if role is None:
        return False
    try:
        role_enum = UserRole(role)
    except ValueError:
        return False
    return role_enum in allowed_roles
