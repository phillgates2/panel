import os
from urllib.parse import urlparse

import pytest


def _get_test_db_url() -> str:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        pytest.skip("Set DATABASE_URL to run installer bootstrap tests")

    if db_url.startswith("postgresql+psycopg2://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg2://") :]

    parsed = urlparse(db_url)
    if "test" not in (parsed.path or "").lower():
        pytest.skip("DATABASE_URL must point to a test database")

    if not db_url.startswith("postgresql://"):
        pytest.skip("DATABASE_URL must be a PostgreSQL URL")

    return db_url


def test_installer_ensure_default_admin_user_postgres(monkeypatch):
    db_url = _get_test_db_url()

    monkeypatch.setenv("PANEL_SECRET_KEY", "test-secret")

    from tools.installer.core import ensure_default_admin_user

    email = "admin-installer-test@example.com"

    res = ensure_default_admin_user(
        admin_email=email,
        admin_password="Str0ng!Password123",
        db_uri=db_url,
    )
    assert res.get("ok") is True
    assert isinstance(res.get("created"), bool)

    res2 = ensure_default_admin_user(
        admin_email=email,
        admin_password="Str0ng!Password123",
        db_uri=db_url,
    )
    assert res2.get("ok") is True
    assert res2.get("created") is False
    assert res2.get("reason") == "system_admin_exists"
