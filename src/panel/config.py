import os
from urllib.parse import quote_plus

from .os_paths import os_paths

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get("PANEL_SECRET_KEY", "dev-secret-key-change")

    # Database configuration: PostgreSQL for production, SQLite for dev
    USE_SQLITE = os.environ.get("PANEL_USE_SQLITE", "1") == "1"

    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = os.environ.get("PANEL_SQLITE_URI", "sqlite:///panel_dev.db")
    else:
        # PostgreSQL configuration
        DB_USER = os.environ.get("PANEL_DB_USER", "paneluser")
        DB_PASS = os.environ.get("PANEL_DB_PASS", "panelpass")
        DB_HOST = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
        DB_PORT = os.environ.get("PANEL_DB_PORT", "5432")
        DB_NAME = os.environ.get("PANEL_DB_NAME", "paneldb")
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database connection pooling and performance optimization
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections after 5 minutes
        'pool_size': 10,        # Base pool size
        'max_overflow': 20,     # Maximum overflow connections
        'pool_timeout': 30,     # Connection timeout
    }

    # Query optimization settings
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "False") == "True"

    # OS-aware paths with environment variable overrides
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = os.environ.get("LOG_DIR", os_paths.log_dir)
    AUDIT_LOG_ENABLED = os.environ.get("AUDIT_LOG_ENABLED", "True") == "True"
    AUDIT_LOG_DIR = os.environ.get("AUDIT_LOG_DIR", os.path.join(LOG_DIR, "audit"))

    # ET:Legacy server settings (used by RCON and autodeployer)
    ET_SERVER_HOST = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
    ET_SERVER_PORT = int(os.environ.get("ET_SERVER_PORT", 27960))
    ET_RCON_PASSWORD = os.environ.get("ET_RCON_PASSWORD", "changeme")

    # OS-aware paths with environment variable overrides
    ET_PID_FILE = os.environ.get("ET_PID_FILE", os.path.join(os_paths.run_dir, "etlegacy.pid"))
    DOWNLOAD_DIR = os.environ.get("PANEL_DOWNLOAD_DIR", os_paths.etlegacy_dir)
    BACKUP_DIR = os.environ.get("PANEL_BACKUP_DIR", os_paths.backup_dir)

    # Admin list (comma separated emails) allowed to perform manual deploys/core-dumps
    ADMIN_EMAILS = [
        e.strip().lower() for e in os.environ.get("PANEL_ADMIN_EMAILS", "").split(",") if e.strip()
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
    USE_SQLITE = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    USE_SQLITE = False
    LOG_LEVEL = "INFO"


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    USE_SQLITE = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
