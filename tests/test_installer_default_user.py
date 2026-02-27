import os
from urllib.parse import urlparse

import pytest


def test_installer_default_user_venv_fallback_parses_sentinel(monkeypatch):
    """Ensure venv-fallback parsing ignores noisy stdout.

    We don't execute a real subprocess here; we just validate that the
    sentinel format is JSON-decodable even if other JSON lines are present.
    """
    sentinel = "__PANEL_BOOTSTRAP_RESULT__"
    noisy_stdout = "\n".join(
        [
            '{"timestamp":"x","level":"INFO","message":"log"}',
            f"{sentinel}" + '{"ok": true, "created": true}',
        ]
    )
    # Mimic the parsing logic in tools.installer.core.ensure_default_admin_user.
    lines = noisy_stdout.splitlines()
    line = next((ln for ln in reversed(lines) if ln.startswith(sentinel)), None)
    assert line is not None
    import json

    parsed = json.loads(line[len(sentinel) :])
    assert parsed["ok"] is True
    assert parsed["created"] is True


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
