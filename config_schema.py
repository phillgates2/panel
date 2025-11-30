"""
Configuration Schema Validation

Uses Pydantic for comprehensive configuration validation, type checking, and documentation.
"""

import os
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import quote_plus

from os_paths import os_paths
from pydantic import (BaseModel, Field, ValidationError, field_validator,
                      model_validator)
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database configuration schema"""

    use_sqlite: bool = Field(
        default=True, description="Use SQLite instead of PostgreSQL"
    )
    sqlite_uri: str = Field(
        default="sqlite:///panel_dev.db", description="SQLite database URI"
    )
    postgres_user: str = Field(default="paneluser", description="PostgreSQL username")
    postgres_password: str = Field(
        default="panelpass", description="PostgreSQL password"
    )
    postgres_host: str = Field(default="127.0.0.1", description="PostgreSQL host")
    postgres_port: int = Field(
        default=5432, ge=1, le=65535, description="PostgreSQL port"
    )
    postgres_database: str = Field(
        default="paneldb", description="PostgreSQL database name"
    )

    # Connection pooling settings
    pool_pre_ping: bool = Field(
        default=True, description="Verify connections before use"
    )
    pool_recycle: int = Field(
        default=300, ge=0, description="Recycle connections after N seconds"
    )
    pool_size: int = Field(default=10, ge=1, description="Base connection pool size")
    max_overflow: int = Field(
        default=20, ge=0, description="Maximum overflow connections"
    )
    pool_timeout: int = Field(
        default=30, ge=1, description="Connection timeout in seconds"
    )

    # Query settings
    echo: bool = Field(default=False, description="Log all SQL queries")

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
            "pool_pre_ping": self.pool_pre_ping,
            "pool_recycle": self.pool_recycle,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
        }


class LoggingConfig(BaseModel):
    """Logging configuration schema"""

    level: str = Field(default="INFO", description="Logging level")
    directory: Path = Field(
        default_factory=lambda: Path("instance/logs"), description="Log directory"
    )
    format: str = Field(default="json", description="Log format (json/text)")
    audit_enabled: bool = Field(
        default=True, description="Enable security audit logging"
    )
    audit_directory: Path = Field(
        default_factory=lambda: Path("instance/audit_logs"),
        description="Audit log directory",
    )
    performance_threshold: float = Field(
        default=500.0, ge=0, description="Slow request threshold (ms)"
    )

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format"""
        if v.lower() not in ["json", "text"]:
            raise ValueError("Log format must be 'json' or 'text'")
        return v.lower()


class ETLegacyConfig(BaseModel):
    """ET:Legacy server configuration schema"""

    server_host: str = Field(default="127.0.0.1", description="ET:Legacy server host")
    server_port: int = Field(
        default=27960, ge=1, le=65535, description="ET:Legacy server port"
    )
    rcon_password: str = Field(
        default="changeme", min_length=1, description="RCON password"
    )
    pid_file: Path = Field(
        default_factory=lambda: Path(os_paths.run_dir) / "etlegacy.pid",
        description="ET:Legacy PID file path",
    )
    download_dir: Path = Field(
        default_factory=lambda: Path(os_paths.etlegacy_dir),
        description="Download directory",
    )


class NotificationConfig(BaseModel):
    """Notification configuration schema"""

    discord_webhook: Optional[str] = Field(
        default=None, description="Discord webhook URL"
    )

    @field_validator("discord_webhook")
    @classmethod
    def validate_discord_webhook(cls, v: Optional[str]) -> Optional[str]:
        """Validate Discord webhook URL format"""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Discord webhook must be a valid HTTP/HTTPS URL")
        return v


class SecurityConfig(BaseModel):
    """Security configuration schema"""

    secret_key: str = Field(..., min_length=16, description="Flask secret key")
    admin_emails: List[str] = Field(
        default_factory=list, description="Admin email addresses"
    )

    @field_validator("admin_emails")
    @classmethod
    def validate_admin_emails(cls, v: List[str]) -> List[str]:
        """Validate admin email format"""
        import re

        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email format: {email}")
        return [email.lower() for email in v]


class SystemConfig(BaseModel):
    """System information configuration"""

    os_system: str = Field(
        default_factory=lambda: os_paths.system, description="Operating system"
    )
    os_distro: str = Field(
        default_factory=lambda: os_paths.distro, description="OS distribution"
    )
    backup_dir: Path = Field(
        default_factory=lambda: Path(os_paths.backup_dir),
        description="Backup directory",
    )


class PanelConfig(BaseSettings):
    """Main Panel configuration with validation"""

    # Database configuration
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # ET:Legacy configuration
    etlegacy: ETLegacyConfig = Field(default_factory=ETLegacyConfig)

    # Notification configuration
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    # Security configuration
    security: SecurityConfig

    # System configuration
    system: SystemConfig = Field(default_factory=SystemConfig)

    # Redis configuration
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0", description="Redis connection URL"
    )

    # Feature flags
    feature_flags: dict = Field(default_factory=dict, description="Feature flags")

    model_config = SettingsConfigDict(
        env_prefix="PANEL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="after")
    def validate_database_config(self) -> "PanelConfig":
        """Cross-field validation for database configuration"""
        if not self.database.use_sqlite:
            # Validate PostgreSQL required fields
            required_fields = [
                "postgres_user",
                "postgres_password",
                "postgres_host",
                "postgres_database",
            ]
            for field in required_fields:
                value = getattr(self.database, field)
                if not value or str(value).strip() == "":
                    raise ValueError(
                        f"PostgreSQL {field} is required when not using SQLite"
                    )
        return self

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format"""
        if not v.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError(
                "Redis URL must start with redis://, rediss://, or unix://"
            )
        return v

    def to_flask_config(self) -> dict:
        """Convert to Flask-compatible configuration dictionary"""
        return {
            # Database
            "SQLALCHEMY_DATABASE_URI": self.database.sqlalchemy_database_uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": self.database.sqlalchemy_engine_options,
            "SQLALCHEMY_ECHO": self.database.echo,
            # Logging
            "LOG_LEVEL": self.logging.level,
            "LOG_DIR": str(self.logging.directory),
            "LOG_FORMAT": self.logging.format,
            "AUDIT_LOG_ENABLED": self.logging.audit_enabled,
            "AUDIT_LOG_DIR": str(self.logging.audit_directory),
            "PERFORMANCE_THRESHOLD": self.logging.performance_threshold,
            # ET:Legacy
            "ET_SERVER_HOST": self.etlegacy.server_host,
            "ET_SERVER_PORT": self.etlegacy.server_port,
            "ET_RCON_PASSWORD": self.etlegacy.rcon_password,
            "ET_PID_FILE": str(self.etlegacy.pid_file),
            # Notifications
            "DISCORD_WEBHOOK": self.notifications.discord_webhook or "",
            # Security
            "SECRET_KEY": self.security.secret_key,
            "ADMIN_EMAILS": self.security.admin_emails,
            # System
            "BACKUP_DIR": str(self.system.backup_dir),
            "DOWNLOAD_DIR": str(self.etlegacy.download_dir),
            "OS_SYSTEM": self.system.os_system,
            "OS_DISTRO": self.system.os_distro,
            # Redis
            "REDIS_URL": self.redis_url,
            # Feature flags
            "FEATURE_FLAGS": self.feature_flags,
        }


def load_config() -> PanelConfig:
    """Load and validate configuration from environment variables"""
    try:
        config = PanelConfig()
        return config
    except ValidationError as e:
        print("Configuration validation errors:")
        for error in e.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  {field_path}: {error['msg']}")
        raise


def validate_config_file(config_file: Union[str, Path]) -> bool:
    """Validate a configuration file"""
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        # Load configuration from file
        import json

        with open(config_path, "r") as f:
            config_data = json.load(f)

        # Validate against schema
        config = PanelConfig(**config_data)
        print(f"✅ Configuration file '{config_file}' is valid")
        return True

    except ValidationError as e:
        print(f"❌ Configuration file '{config_file}' has validation errors:")
        for error in e.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  {field_path}: {error['msg']}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Configuration file '{config_file}' has invalid JSON: {e}")
        return False


def generate_config_template(output_file: Union[str, Path]) -> None:
    """Generate a configuration template file"""
    config_path = Path(output_file)

    # Create default configuration
    default_config = PanelConfig(
        security=SecurityConfig(secret_key="your-secret-key-here")
    )

    # Convert to dictionary for JSON serialization
    config_dict = default_config.model_dump()

    # Write to file
    with open(config_path, "w") as f:
        import json

        json.dump(config_dict, f, indent=2, default=str)

    print(f"Configuration template generated: {config_path}")


def print_config_schema() -> None:
    """Print the configuration schema for documentation"""
    config = PanelConfig(security=SecurityConfig(secret_key="example-key"))
    schema = config.model_json_schema()

    print("Panel Configuration Schema:")
    print("=" * 50)
    print(json.dumps(schema, indent=2))


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

        elif command == "schema":
            print_config_schema()

        else:
            print("Usage:")
            print("  python config_schema.py validate <config_file>")
            print("  python config_schema.py template <output_file>")
            print("  python config_schema.py schema")
    else:
        # Load and validate current configuration
        try:
            config = load_config()
            print("✅ Current configuration is valid")
            print(f"Database URI: {config.database.sqlalchemy_database_uri}")
            print(f"Log level: {config.logging.level}")
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
