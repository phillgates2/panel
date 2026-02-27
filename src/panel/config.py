import os
from urllib.parse import quote_plus

from .os_paths import os_paths


class Config:
    """Base configuration class."""

    SECRET_KEY = os.environ.get("PANEL_SECRET_KEY", "dev-secret-key-change")

    # Database configuration: PostgreSQL only.
    # Only PostgreSQL is supported to avoid split-brain installs where migrations
    # are applied to one DB but the running service points at another.
    DB_USER = os.environ.get("PANEL_DB_USER", "paneluser")
    # Support common alias PANEL_DB_PASSWORD used by docker-compose templates.
    DB_PASS = (
        os.environ.get("PANEL_DB_PASS")
        or os.environ.get("PANEL_DB_PASSWORD")
        or "panelpass"
    )
    DB_HOST = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
    DB_PORT = os.environ.get("PANEL_DB_PORT", "5432")
    DB_NAME = os.environ.get("PANEL_DB_NAME", "paneldb")
    # Ensure the app can find tables created in the expected schema.
    # In PostgreSQL, an altered role/database `search_path` can cause runtime
    # errors like "relation 'user' does not exist" even when migrations ran.
    DB_SEARCH_PATH = os.environ.get("PANEL_DB_SEARCH_PATH", "public")

    # Support common alias PANEL_DATABASE_URL used in some deployment configs.
    _override_db = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("PANEL_DATABASE_URL")
    )
    if isinstance(_override_db, str) and _override_db.strip():
        if _override_db.strip().lower().startswith("sqlite"):
            raise ValueError(
                "SQLite is no longer supported. Configure PostgreSQL via DATABASE_URL/SQLALCHEMY_DATABASE_URI or PANEL_DB_*."
            )
        SQLALCHEMY_DATABASE_URI = _override_db.strip()
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database connection pooling and performance optimization
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connections before use
        "pool_recycle": 300,  # Recycle connections after 5 minutes
        "pool_size": 10,  # Base pool size
        "max_overflow": 20,  # Maximum overflow connections
        "pool_timeout": 30,  # Connection timeout
        # Force the schema search path for every new DB connection.
        # Psycopg2 supports the `options` argument for runtime parameters.
        "connect_args": (
            {"options": f"-c search_path={DB_SEARCH_PATH}"}
            if isinstance(DB_SEARCH_PATH, str) and DB_SEARCH_PATH.strip()
            else {}
        ),
    }

    # Query optimization settings
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "False") == "True"

    # OS-aware paths with environment variable overrides
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = os.environ.get("LOG_DIR", os_paths.log_dir)
    AUDIT_LOG_ENABLED = os.environ.get("AUDIT_LOG_ENABLED", "True") == "True"
    AUDIT_LOG_DIR = os.environ.get("AUDIT_LOG_DIR", os.path.join(LOG_DIR, "audit"))

    # Session and security defaults
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "auto")
    # Interpret 'auto' as True in production.
    if SESSION_COOKIE_SECURE in ("", None):
        SESSION_COOKIE_SECURE = False
    elif isinstance(SESSION_COOKIE_SECURE, str) and SESSION_COOKIE_SECURE.lower() == "auto":
        env_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
        SESSION_COOKIE_SECURE = env_name in ("production", "prod")
    else:
        SESSION_COOKIE_SECURE = str(SESSION_COOKIE_SECURE).lower() in ("1", "true", "yes")

    SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY", "true").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 2592000))  # 30 days

    # ET:Legacy server settings (used by RCON and autodeployer)
    # Treat defaults as placeholders; only consider the server “configured”
    # when the operator explicitly sets env vars.
    ET_SERVER_CONFIGURED = ("ET_SERVER_HOST" in os.environ) or ("ET_SERVER_PORT" in os.environ)
    ET_SERVER_HOST = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
    ET_SERVER_PORT = int(os.environ.get("ET_SERVER_PORT", 27960))
    ET_RCON_PASSWORD = os.environ.get("ET_RCON_PASSWORD", "changeme")

    # OS-aware paths with environment variable overrides
    ET_PID_FILE = os.environ.get(
        "ET_PID_FILE", os.path.join(os_paths.run_dir, "etlegacy.pid")
    )
    DOWNLOAD_DIR = os.environ.get("PANEL_DOWNLOAD_DIR", os_paths.etlegacy_dir)
    BACKUP_DIR = os.environ.get("PANEL_BACKUP_DIR", os_paths.backup_dir)

    # Admin list (comma separated emails) allowed to perform manual deploys/core-dumps
    ADMIN_EMAILS = [
        e.strip().lower()
        for e in os.environ.get("PANEL_ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]

    # Discord webhook for notifications (optional)
    DISCORD_WEBHOOK = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
    REDIS_URL = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")

    # System information (useful for debugging)
    OS_SYSTEM = os_paths.system
    OS_DISTRO = os_paths.distro


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Relax session security for tests
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
