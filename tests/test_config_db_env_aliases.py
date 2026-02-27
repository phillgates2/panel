import importlib


def test_config_accepts_panel_db_password_alias(monkeypatch):
    # Ensure we don't accidentally pick up a real DATABASE_URL from the environment.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("PANEL_DATABASE_URL", raising=False)

    monkeypatch.delenv("PANEL_DB_PASS", raising=False)
    monkeypatch.setenv("PANEL_DB_USER", "paneluser")
    monkeypatch.setenv("PANEL_DB_PASSWORD", "supersecret")
    monkeypatch.setenv("PANEL_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("PANEL_DB_PORT", "5432")
    monkeypatch.setenv("PANEL_DB_NAME", "paneldb")

    import src.panel.config as config_module

    importlib.reload(config_module)
    cfg = config_module.Config

    assert "supersecret" in cfg.SQLALCHEMY_DATABASE_URI


def test_config_accepts_panel_database_url_alias(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)

    monkeypatch.setenv(
        "PANEL_DATABASE_URL",
        "postgresql+psycopg2://paneluser:pw@127.0.0.1:5432/paneldb",
    )

    import src.panel.config as config_module

    importlib.reload(config_module)
    cfg = config_module.Config

    assert cfg.SQLALCHEMY_DATABASE_URI.startswith("postgresql")
    assert ":pw@" in cfg.SQLALCHEMY_DATABASE_URI
