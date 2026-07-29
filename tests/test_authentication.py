"""
tests/test_authentication.py

Covers password hashing, registration validation, login success/
failure, and the ICS-005 account-lockout hardening.
"""

from authentication import (
    hash_password,
    login_user,
    password_strength_errors,
    register_user,
    verify_password,
)


def test_hash_password_roundtrip():
    hashed = hash_password("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert verify_password("Sup3rSecret!", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_password_strength_rules():
    assert password_strength_errors("short") != []
    assert password_strength_errors("alllowercase1") != []
    assert password_strength_errors("Str0ngPassword") == []


def test_register_and_login_success():
    result = register_user("alice_test", "alice_test@example.com", "Str0ngPass!", "Alice Test")
    assert result.success, result.message

    login_result = login_user("alice_test", "Str0ngPass!")
    assert login_result.success
    assert login_result.username == "alice_test"


def test_register_duplicate_username_rejected():
    register_user("bob_test", "bob_test@example.com", "Str0ngPass!", "Bob Test")
    duplicate = register_user("bob_test", "someoneelse@example.com", "Str0ngPass!", "Someone Else")
    assert not duplicate.success


def test_login_wrong_password_fails():
    register_user("carol_test", "carol_test@example.com", "Str0ngPass!", "Carol Test")
    result = login_user("carol_test", "WrongPassword1")
    assert not result.success


def test_account_lockout_after_repeated_failures():
    register_user("dave_test", "dave_test@example.com", "Str0ngPass!", "Dave Test")
    for _ in range(5):
        login_user("dave_test", "WrongPassword1")

    locked_attempt = login_user("dave_test", "Str0ngPass!")
    assert not locked_attempt.success
    assert "Too many failed attempts" in locked_attempt.message
