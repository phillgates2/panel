def test_installer_creates_default_admin_user_sqlite_file(tmp_path, monkeypatch):
    # Force a deterministic, isolated DB (file-based so it persists across calls)
    db_path = tmp_path / "panel_test.db"
    db_uri = f"sqlite:///{db_path}"
    monkeypatch.setenv("PANEL_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PANEL_SQLITE_URI", db_uri)
def test_installer_creates_default_admin_user_sqlite(tmp_path, monkeypatch):
    # Use a file-backed sqlite DB so the second call sees persisted data.
    db_path = tmp_path / "panel_test.db"
    db_uri = f"sqlite:///{db_path}"
    monkeypatch.setenv("PANEL_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PANEL_SQLITE_URI", db_uri)

    from tools.installer.core import ensure_default_admin_user

    res = ensure_default_admin_user(
        admin_email="admin@example.com",
        admin_password="Str0ng!Password123",
        db_uri=db_uri,
    )
    assert res.get("ok") is True
    assert res.get("created") is True
    assert res.get("email") == "admin@example.com"

    res2 = ensure_default_admin_user(
        admin_email="admin@example.com",
        admin_password="Str0ng!Password123",
        db_uri=db_uri,
    )
    assert res2.get("ok") is True
    assert res2.get("created") is False
    assert res2.get("reason") == "system_admin_exists"
