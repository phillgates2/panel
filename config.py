import os
from urllib.parse import quote_plus

# Allow a quick dev sqlite mode for local testing/CI when PANEL_USE_SQLITE=1
USE_SQLITE = os.environ.get('PANEL_USE_SQLITE', '') == '1'

# Basic config - change values in env or edit directly for local testing
MYSQL_USER = os.environ.get("PANEL_DB_USER", "paneluser")
MYSQL_PASS = os.environ.get("PANEL_DB_PASS", "panelpass")
MYSQL_HOST = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
MYSQL_DB = os.environ.get("PANEL_DB_NAME", "paneldb")

SECRET_KEY = os.environ.get("PANEL_SECRET_KEY", "dev-secret-key-change")

if USE_SQLITE:
    SQLALCHEMY_DATABASE_URI = os.environ.get('PANEL_SQLITE_URI', 'sqlite:///panel_dev.db')
else:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASS)}@{MYSQL_HOST}/{MYSQL_DB}"
    )
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ET:Legacy server settings (used by RCON and autodeployer)
ET_SERVER_HOST = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
ET_SERVER_PORT = int(os.environ.get("ET_SERVER_PORT", 27960))
ET_RCON_PASSWORD = os.environ.get("ET_RCON_PASSWORD", "changeme")

# Paths used by utilities
ET_PID_FILE = os.environ.get("ET_PID_FILE", "/var/run/etlegacy.pid")
DOWNLOAD_DIR = os.environ.get("PANEL_DOWNLOAD_DIR", "/opt/etlegacy")
LOG_DIR = os.environ.get("PANEL_LOG_DIR", "/var/log/panel")

# Admin list (comma separated emails) allowed to perform manual deploys/core-dumps
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("PANEL_ADMIN_EMAILS", "").split(",") if e.strip()]

# Discord webhook for notifications (optional)
DISCORD_WEBHOOK = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
REDIS_URL = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
