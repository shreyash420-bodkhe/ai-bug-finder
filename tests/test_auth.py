import sqlite3

from auth_manager import AuthStore


def test_registered_user_can_log_in_with_email(tmp_path):
    store = AuthStore(tmp_path / "users.db")
    assert store.register_user("Person@Example.com", "secure-password") == "registered"

    is_valid, role = store.validate_login("person@example.com", "secure-password")
    assert is_valid is True
    assert role == "user"


def test_admin_login_uses_configured_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFINDER_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BUGFINDER_ADMIN_PASSWORD", "a-secure-admin-password")
    store = AuthStore(tmp_path / "users.db")

    is_valid, role = store.validate_login("admin@example.com", "a-secure-admin-password")
    assert is_valid is True
    assert role == "admin"


def test_admin_login_is_disabled_without_configured_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("BUGFINDER_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BUGFINDER_ADMIN_PASSWORD", raising=False)
    store = AuthStore(tmp_path / "users.db")

    assert store.validate_login("admin@123", "admin123321") == (False, None)
    assert store.validate_login("admin@example.com", "any-password") == (False, None)


def test_invalid_login_is_rejected(tmp_path):
    store = AuthStore(tmp_path / "users.db")
    store.register_user("person@example.com", "secure-password")

    is_valid, role = store.validate_login("person@example.com", "wrong-password")
    assert is_valid is False
    assert role is None


def test_registration_rejects_invalid_or_duplicate_accounts(tmp_path):
    store = AuthStore(tmp_path / "users.db")

    assert store.register_user("not-an-email", "secure-password") == "invalid_email"
    assert store.register_user("person@example.com", "short") == "weak_password"
    assert store.register_user("person@example.com", "secure-password") == "registered"
    assert store.register_user("PERSON@example.com", "another-password") == "already_registered"


def test_admin_user_listing_never_returns_password_data(tmp_path):
    database_path = tmp_path / "users.db"
    store = AuthStore(database_path)
    store.register_user("person@example.com", "secure-password")

    assert set(store.list_users()[0]) == {"email", "created_at"}
    with sqlite3.connect(database_path) as connection:
        saved_hash, = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("person@example.com",)
        ).fetchone()
    assert saved_hash != "secure-password"


def test_admin_password_reset_stores_hash_and_invalidates_old_password(tmp_path):
    database_path = tmp_path / "users.db"
    store = AuthStore(database_path)
    assert store.register_user("person@example.com", "old-password") == "registered"

    assert store.reset_user_password("person@example.com", "new-password") == "updated"
    assert store.validate_login("person@example.com", "old-password") == (False, None)
    assert store.validate_login("person@example.com", "new-password") == (True, "user")

    with sqlite3.connect(database_path) as connection:
        saved_hash, = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("person@example.com",)
        ).fetchone()
    assert saved_hash != "new-password"


def test_admin_password_reset_validates_password_and_user(tmp_path):
    store = AuthStore(tmp_path / "users.db")
    store.register_user("person@example.com", "old-password")

    assert store.reset_user_password("person@example.com", "short") == "weak_password"
    assert store.reset_user_password("unknown@example.com", "new-password") == "not_found"
    assert store.reset_user_password(store.admin_email, "new-password") == "reserved_email"
    assert store.validate_login("person@example.com", "old-password") == (True, "user")
