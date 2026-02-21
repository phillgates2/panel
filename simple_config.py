"""Simple configuration management for Panel (PostgreSQL-only)."""

import os
from urllib.parse import quote_plus


class ValidationError(Exception):
    """Configuration validation error."""

    pass


class PanelConfig:
    """Panel configuration class."""

    def __init__(self):
        override_db = os.environ.get("DATABASE_URL") or os.environ.get(
            "SQLALCHEMY_DATABASE_URI"
        )
        if override_db and override_db.strip().lower().startswith("sqlite"):
            raise ValidationError(
                "SQLite is not supported. Configure PostgreSQL via DATABASE_URL/SQLALCHEMY_DATABASE_URI or PANEL_DB_* env vars."
            )

        if override_db:
            self.SQLALCHEMY_DATABASE_URI = override_db
        else:
            user = os.environ.get("PANEL_DB_USER", "paneluser")
            password = os.environ.get("PANEL_DB_PASS", "panelpass")
            host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
            port = int(os.environ.get("PANEL_DB_PORT", "5432"))
            database = os.environ.get("PANEL_DB_NAME", "paneldb")
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
            )
        self.TESTING = False
        self.SECRET_KEY = "default-secret-key"


def load_config():
    """Load configuration."""
    return PanelConfig()


def validate_configuration_at_startup(app):
    """Validate configuration at startup."""
    pass
