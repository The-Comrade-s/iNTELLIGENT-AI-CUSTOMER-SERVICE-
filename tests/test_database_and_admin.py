"""
tests/test_database_and_admin.py

Covers database relationships/constraints and the admin_service
layer used by the ICS-003 admin console.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from authentication import register_user
from database import User, get_db
from services import admin_service


def test_duplicate_email_raises_integrity_error_at_db_level():
    register_user("unique_user1", "shared_email@example.com", "Str0ngPass!", "User One")
    with pytest.raises(IntegrityError):
        with get_db() as db:
            db.add(User(username="unique_user2", email="shared_email@example.com", password_hash="x"))


def test_user_profile_relationship_created_on_registration():
    result = register_user("profile_rel_user", "profile_rel@example.com", "Str0ngPass!", "Profile Rel User")
    with get_db() as db:
        user = db.query(User).filter(User.id == result.user_id).first()
        assert user.profile is not None
        assert user.profile.full_name == "Profile Rel User"


def test_admin_service_list_and_deactivate_user():
    result = register_user("admin_svc_user", "admin_svc@example.com", "Str0ngPass!", "Admin Svc User")
    users = admin_service.list_users(search="admin_svc_user")
    assert len(users) == 1
    assert users[0]["is_active"] is True

    admin_service.set_user_active(result.user_id, False, actor_id=result.user_id)
    users_after = admin_service.list_users(search="admin_svc_user")
    assert users_after[0]["is_active"] is False


def test_admin_service_role_change_is_audited():
    result = register_user("role_change_user", "role_change@example.com", "Str0ngPass!", "Role Change User")
    admin_service.set_user_role(result.user_id, "support_agent", actor_id=result.user_id)

    logs = admin_service.list_audit_logs(action_filter="role_change")
    assert any(f"#{result.user_id}" in (log["description"] or "") for log in logs)


def test_admin_service_faq_crud():
    admin_service.create_faq("Test question?", "Test answer.", "Testing", "test keyword", "published", actor_id=1)
    faqs = admin_service.list_faqs(status_filter="published")
    match = next((f for f in faqs if f["question"] == "Test question?"), None)
    assert match is not None

    admin_service.update_faq(match["id"], "Updated question?", "Updated answer.", "Testing", "updated", "draft", actor_id=1)
    updated = admin_service.list_faqs(status_filter="draft")
    assert any(f["question"] == "Updated question?" for f in updated)

    admin_service.delete_faq(match["id"], actor_id=1)
    remaining = admin_service.list_faqs()
    assert not any(f["id"] == match["id"] for f in remaining)
