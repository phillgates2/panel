"""
Simple Configuration Validation

Basic configuration validation using Python's built-in capabilities.
Provides validation without external dependencies.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus

from os_paths import os_paths


class ValidationError(Exception):
    """Configuration validation error"""

    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        super().__init__(f"Configuration validation failed with {len(errors)} errors")


class DatabaseConfig:
    """Database configuration"""

    def __init__(self):
        self.use_sqlite = os.environ.get("PANEL_USE_SQLITE", "1") == "1"
        self.sqlite_uri = os.environ.get("PANEL_SQLITE_URI", "sqlite:///panel_dev.db")
        self.postgres_user = os.environ.get("PANEL_DB_USER", "paneluser")
        self.postgres_password = os.environ.get("PANEL_DB_PASS", "panelpass")
        self.postgres_host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
        self.postgres_port = int(os.environ.get("PANEL_DB_PORT", "5432"))
        self.pool_pre_ping = True
        self.pool_recycle = 300
        self.pool_size = 10
        self.max_overflow = 20
        self.pool_timeout = 30
        self.echo = os.environ.get("SQLALCHEMY_ECHO", "False") == "True"

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Generate SQLAlchemy database URI"""
        if self.use_sqlite:
            return self.sqlite_uri
        else:
            return (
                f"postgresql+psycopg2://{quote_plus(self.postgres_user)}:"
                f"{quote_plus(self.postgres_password)}@{self.postgres_host}:"
                f"{self.postgres_port}/{self.postgres_database}"
            )

    @property
    def sqlalchemy_engine_options(self) -> dict:
        """Generate SQLAlchemy engine options"""
        return {
            'pool_pre_ping': self.pool_pre_ping,
            'pool_recycle': self.pool_recycle,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
        }


class LoggingConfig:
    """Logging configuration"""

    VALID_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    def __init__(self):
        self.level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.directory = Path(os.environ.get("LOG_DIR", os_paths.log_dir))
        self.format = os.environ.get("LOG_FORMAT", "text").lower()
        self.audit_enabled = os.environ.get("AUDIT_LOG_ENABLED", "True") == "True"
        self.audit_directory = Path(os.environ.get("AUDIT_LOG_DIR", os.path.join(str(self.directory), "audit")))
        self.performance_threshold = 500.0


class SecurityConfig:
    """Security configuration"""

    def __init__(self):
        self.secret_key = os.environ.get("PANEL_SECRET_KEY", "dev-secret-key-change")
        admin_emails_str = os.environ.get("PANEL_ADMIN_EMAILS", "")
        self.admin_emails = [e.strip().lower() for e in admin_emails_str.split(",") if e.strip()]


class ETLegacyConfig:
    """ET:Legacy server configuration"""

    def __init__(self):
        self.server_host = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
        self.server_port = int(os.environ.get("ET_SERVER_PORT", 27960))
        self.rcon_password = os.environ.get("ET_RCON_PASSWORD", "changeme")
        self.pid_file = Path(os.environ.get("ET_PID_FILE", os.path.join(os_paths.run_dir, "etlegacy.pid")))
        self.download_dir = Path(os.environ.get("PANEL_DOWNLOAD_DIR", os_paths.etlegacy_dir))


class SystemConfig:
    """System information configuration"""

    def __init__(self):
        self.os_system = os_paths.system
        self.os_distro = os_paths.distro
        self.backup_dir = Path(os.environ.get("PANEL_BACKUP_DIR", os_paths.backup_dir))


class PanelConfig:
    """Main Panel configuration"""

    def __init__(self):
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.etlegacy = ETLegacyConfig()
        self.system = SystemConfig()
        self.redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
        self.discord_webhook = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
        self.feature_flags = {}

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate secret key
        if len(self.security.secret_key) < 16:
            errors.append("SECRET_KEY must be at least 16 characters long")

        # Validate log level
        if self.logging.level not in self.logging.VALID_LEVELS:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(self.logging.VALID_LEVELS)}")

        # Validate log format
        if self.logging.format not in ['json', 'text']:
            errors.append("LOG_FORMAT must be 'json' or 'text'")

        # Validate port ranges
        if not (1 <= self.etlegacy.server_port <= 65535):
            errors.append("ET_SERVER_PORT must be between 1 and 65535")

        # Validate email formats
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for email in self.security.admin_emails:
            if not email_pattern.match(email):
                errors.append(f"Invalid email format: {email}")

        # Validate Redis URL
        if not self.redis_url.startswith(('redis://', 'rediss://', 'unix://')):
            errors.append("REDIS_URL must start with redis://, rediss://, or unix://")

        # Validate Discord webhook
        if self.discord_webhook and not self.discord_webhook.startswith(('http://', 'https://')):
            errors.append("DISCORD_WEBHOOK must be a valid HTTP/HTTPS URL")

        return errors

    def to_flask_config(self) -> dict:
        """Convert to Flask-compatible configuration dictionary"""
        return {
            # Database
            'SQLALCHEMY_DATABASE_URI': self.database.sqlalchemy_database_uri,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': self.database.sqlalchemy_engine_options,
            'SQLALCHEMY_ECHO': self.database.echo,

            # Logging
            'LOG_LEVEL': self.logging.level,
            'LOG_DIR': str(self.logging.directory),
            'LOG_FORMAT': self.logging.format,
            'AUDIT_LOG_ENABLED': self.logging.audit_enabled,
            'AUDIT_LOG_DIR': str(self.logging.audit_directory),
            'PERFORMANCE_THRESHOLD': self.logging.performance_threshold,

            # ET:Legacy
            'ET_SERVER_HOST': self.etlegacy.server_host,
            'ET_SERVER_PORT': self.etlegacy.server_port,
            'ET_RCON_PASSWORD': self.etlegacy.rcon_password,
            'ET_PID_FILE': str(self.etlegacy.pid_file),

            # Notifications
            'DISCORD_WEBHOOK': self.discord_webhook,

            # Security
            'SECRET_KEY': self.security.secret_key,
            'ADMIN_EMAILS': self.security.admin_emails,

            # System
            'BACKUP_DIR': str(self.system.backup_dir),
            'DOWNLOAD_DIR': str(self.etlegacy.download_dir),
            'OS_SYSTEM': self.system.os_system,
            'OS_DISTRO': self.system.os_distro,

            # Redis
            'REDIS_URL': self.redis_url,

            # Feature flags
            'FEATURE_FLAGS': self.feature_flags,
        }


def load_config() -> PanelConfig:
    """Load and validate configuration"""
    config = PanelConfig()
    errors = config.validate()

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ValidationError([{"loc": ["config"], "msg": error_msg}])

    return config


def validate_config_file(config_file: Union[str, Path]) -> bool:
    """Validate a configuration file"""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return False

    try:
        import json
        with open(config_path, 'r') as f:
            config_data = json.load(f)

        # Basic structure validation
        required_sections = ['database', 'logging', 'security']
        for section in required_sections:
            if section not in config_data:
                print(f"❌ Missing required section: {section}")
                return False

        if 'secret_key' not in config_data.get('security', {}):
            print("❌ Missing required field: security.secret_key")
            return False

        print(f"✅ Configuration file '{config_file}' structure is valid")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Configuration file '{config_file}' has invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration file '{config_file}' validation failed: {e}")
        return False


def generate_config_template(output_file: Union[str, Path]) -> None:
    """Generate a configuration template file"""
    config_path = Path(output_file)

    template_config = {
        "database": {
            "use_sqlite": True,
            "sqlite_uri": "sqlite:///panel_dev.db"
        },
        "logging": {
            "level": "INFO",
            "format": "json"
        },
        "security": {
            "secret_key": "your-very-secure-secret-key-here-minimum-16-chars",
            "admin_emails": ["admin@example.com"]
        },
        "etlegacy": {
            "server_host": "127.0.0.1",
            "server_port": 27960,
            "rcon_password": "secure-rcon-password"
        },
        "redis_url": "redis://127.0.0.1:6379/0",
        "discord_webhook": "https://discord.com/api/webhooks/your-webhook-url"
    }

    import json
    with open(config_path, 'w') as f:
        json.dump(template_config, f, indent=2)

    print(f"Configuration template generated: {config_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "validate" and len(sys.argv) > 2:
            config_file = sys.argv[2]
            success = validate_config_file(config_file)
            sys.exit(0 if success else 1)

        elif command == "template" and len(sys.argv) > 2:
            output_file = sys.argv[2]
            generate_config_template(output_file)

        else:
            print("Usage:")
            print("  python config_schema.py validate <config_file>")
            print("  python config_schema.py template <output_file>")
    else:
        # Load and validate current configuration
        try:
            config = load_config()
            print("✅ Current configuration is valid")
            print(f"Database URI: {config.database.sqlalchemy_database_uri}")
            print(f"Log level: {config.logging.level}")
        except ValidationError as e:
            print("❌ Configuration validation errors:")
            for error in e.errors:
                print(f"  {error['msg']}")
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)