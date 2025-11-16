import os
from os_paths import os_paths

# Basic config - change values in env or edit directly for local testing
SECRET_KEY = os.environ.get("PANEL_SECRET_KEY", "dev-secret-key-change")

# SQLite database configuration
SQLALCHEMY_DATABASE_URI = os.environ.get('PANEL_SQLITE_URI', 'sqlite:///panel_dev.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# OS-aware paths with environment variable overrides
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_DIR = os.environ.get('LOG_DIR', os_paths.log_dir)
AUDIT_LOG_ENABLED = os.environ.get('AUDIT_LOG_ENABLED', 'True') == 'True'
AUDIT_LOG_DIR = os.environ.get('AUDIT_LOG_DIR', os.path.join(LOG_DIR, 'audit'))

# ET:Legacy server settings (used by RCON and autodeployer)
ET_SERVER_HOST = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
ET_SERVER_PORT = int(os.environ.get("ET_SERVER_PORT", 27960))
ET_RCON_PASSWORD = os.environ.get("ET_RCON_PASSWORD", "changeme")

# OS-aware paths with environment variable overrides
ET_PID_FILE = os.environ.get("ET_PID_FILE", os.path.join(os_paths.run_dir, "etlegacy.pid"))
DOWNLOAD_DIR = os.environ.get("PANEL_DOWNLOAD_DIR", os_paths.etlegacy_dir)
BACKUP_DIR = os.environ.get("PANEL_BACKUP_DIR", os_paths.backup_dir)

# Admin list (comma separated emails) allowed to perform manual deploys/core-dumps
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("PANEL_ADMIN_EMAILS", "").split(",") if e.strip()]

# Discord webhook for notifications (optional)
DISCORD_WEBHOOK = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
REDIS_URL = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")

# System information (useful for debugging)
OS_SYSTEM = os_paths.system
OS_DISTRO = os_paths.distro
