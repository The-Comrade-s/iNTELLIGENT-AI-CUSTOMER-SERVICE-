"""
services/admin_service.py

Query/command layer for the ICS-003 admin portal: user management,
knowledge-base CMS, notifications, and audit log access. Kept
separate from the page modules so pages stay thin (UI only) and this
logic is reusable/testable on its own.
"""

from __future__ import annotations

import datetime as dt

from authentication import hash_password
from database import ActivityLog, Escalation, FAQ, Notification, User, get_db, log_activity


# ----------------------------------------------------------------------
# User management
# ----------------------------------------------------------------------
def list_users(search: str = "", role_filter: str = "", status_filter: str = "") -> list[dict]:
    with get_db() as db:
        query = db.query(User)
        if search:
            like = f"%{search.strip()}%"
            query = query.filter((User.username.ilike(like)) | (User.email.ilike(like)))
        if role_filter:
            query = query.filter(User.role == role_filter)
        if status_filter == "active":
            query = query.filter(User.is_active.is_(True))
        elif status_filter == "inactive":
            query = query.filter(User.is_active.is_(False))

        users = query.order_by(User.created_at.desc()).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
                "full_name": u.profile.full_name if u.profile else "",
            }
            for u in users
        ]


def set_user_role(user_id: int, new_role: str, actor_id: int) -> None:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            old_role = user.role
            user.role = new_role
            log_activity(db, actor_id, "role_change", f"Changed user #{user_id} role from {old_role} to {new_role}.")


def set_user_active(user_id: int, is_active: bool, actor_id: int) -> None:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = is_active
            action = "user_activated" if is_active else "user_deactivated"
            log_activity(db, actor_id, action, f"User #{user_id} set to {'active' if is_active else 'inactive'}.")


def admin_reset_password(user_id: int, new_password: str, actor_id: int) -> None:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.password_hash = hash_password(new_password)
            log_activity(db, actor_id, "admin_password_reset", f"Admin reset password for user #{user_id}.")


def delete_user(user_id: int, actor_id: int) -> None:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            log_activity(db, actor_id, "user_deleted", f"User #{user_id} deleted.")


# ----------------------------------------------------------------------
# Knowledge base CMS
# ----------------------------------------------------------------------
def list_faqs(status_filter: str = "") -> list[dict]:
    with get_db() as db:
        query = db.query(FAQ)
        if status_filter:
            query = query.filter(FAQ.status == status_filter)
        faqs = query.order_by(FAQ.category, FAQ.question).all()
        return [
            {
                "id": f.id, "question": f.question, "answer": f.answer,
                "category": f.category, "keywords": f.keywords, "status": f.status,
                "views": f.views, "helpful_votes": f.helpful_votes,
            }
            for f in faqs
        ]


def create_faq(question: str, answer: str, category: str, keywords: str, status: str, actor_id: int) -> None:
    with get_db() as db:
        db.add(FAQ(question=question.strip(), answer=answer.strip(), category=category.strip() or "General",
                    keywords=keywords.strip(), status=status))
        log_activity(db, actor_id, "faq_created", f"Created FAQ '{question[:60]}'.")


def update_faq(faq_id: int, question: str, answer: str, category: str, keywords: str, status: str, actor_id: int) -> None:
    with get_db() as db:
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq:
            faq.question = question.strip()
            faq.answer = answer.strip()
            faq.category = category.strip() or "General"
            faq.keywords = keywords.strip()
            faq.status = status
            faq.updated_at = dt.datetime.utcnow()
            log_activity(db, actor_id, "faq_updated", f"Updated FAQ #{faq_id}.")


def delete_faq(faq_id: int, actor_id: int) -> None:
    with get_db() as db:
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq:
            db.delete(faq)
            log_activity(db, actor_id, "faq_deleted", f"Deleted FAQ #{faq_id}.")


# ----------------------------------------------------------------------
# Escalations (surfaced in the admin console)
# ----------------------------------------------------------------------
def list_escalations(status_filter: str = "") -> list[dict]:
    with get_db() as db:
        query = db.query(Escalation)
        if status_filter:
            query = query.filter(Escalation.status == status_filter)
        escalations = query.order_by(Escalation.created_at.desc()).all()
        return [
            {
                "id": e.id, "conversation_id": e.conversation_id, "reason": e.reason,
                "status": e.status, "assigned_agent_id": e.assigned_agent_id,
                "notes": e.notes, "created_at": e.created_at, "resolved_at": e.resolved_at,
            }
            for e in escalations
        ]


def assign_escalation(escalation_id: int, agent_id: int, actor_id: int) -> None:
    with get_db() as db:
        escalation = db.query(Escalation).filter(Escalation.id == escalation_id).first()
        if escalation:
            escalation.assigned_agent_id = agent_id
            escalation.status = "assigned"
            log_activity(db, actor_id, "escalation_assigned", f"Escalation #{escalation_id} assigned to agent #{agent_id}.")


def resolve_escalation(escalation_id: int, notes: str, actor_id: int) -> None:
    with get_db() as db:
        escalation = db.query(Escalation).filter(Escalation.id == escalation_id).first()
        if escalation:
            escalation.status = "resolved"
            escalation.notes = notes
            escalation.resolved_at = dt.datetime.utcnow()
            log_activity(db, actor_id, "escalation_resolved", f"Escalation #{escalation_id} resolved.")


# ----------------------------------------------------------------------
# Audit logs
# ----------------------------------------------------------------------
def list_audit_logs(action_filter: str = "", limit: int = 200) -> list[dict]:
    with get_db() as db:
        query = db.query(ActivityLog)
        if action_filter:
            query = query.filter(ActivityLog.action == action_filter)
        logs = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": log.id, "user_id": log.user_id, "action": log.action,
                "description": log.description, "created_at": log.created_at,
            }
            for log in logs
        ]


def distinct_audit_actions() -> list[str]:
    with get_db() as db:
        rows = db.query(ActivityLog.action).distinct().all()
        return sorted({r[0] for r in rows})


# ----------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------
def create_notification(title: str, message: str, category: str = "system", user_id: int | None = None) -> None:
    with get_db() as db:
        db.add(Notification(title=title, message=message, category=category, user_id=user_id))


def list_notifications(user_id: int | None, unread_only: bool = False, limit: int = 20) -> list[dict]:
    with get_db() as db:
        query = db.query(Notification).filter(
            (Notification.user_id == user_id) | (Notification.user_id.is_(None))
        )
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return [
            {
                "id": n.id, "title": n.title, "message": n.message,
                "category": n.category, "is_read": n.is_read, "created_at": n.created_at,
            }
            for n in notifications
        ]


def mark_notification_read(notification_id: int) -> None:
    with get_db() as db:
        n = db.query(Notification).filter(Notification.id == notification_id).first()
        if n:
            n.is_read = True


def unread_notification_count(user_id: int | None) -> int:
    with get_db() as db:
        return (
            db.query(Notification)
            .filter((Notification.user_id == user_id) | (Notification.user_id.is_(None)))
            .filter(Notification.is_read.is_(False))
            .count()
        )
