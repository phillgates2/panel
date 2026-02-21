"""
Multi-Environment Configuration Management
Secure configuration handling for different environments
"""

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from app.secret_key import ensure_secret_key
except Exception:  # pragma: no cover
    ensure_secret_key = None


class Environment(Enum):
    """Environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment"""

    name: str
    debug: bool = False
    testing: bool = False
    secret_key: str = ""
    database_url: str = ""
    redis_url: str = ""
    mail_server: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_use_tls: bool = True
    mail_use_ssl: bool = False
    oauth_providers: Dict[str, Dict[str, str]] = field(default_factory=dict)
    cdn_enabled: bool = False
    cdn_url: str = ""
    cdn_provider: str = "cloudflare"
    microservices_enabled: bool = False
    api_gateway_enabled: bool = False
    performance_monitoring_enabled: bool = True
    realtime_enabled: bool = True
    pwa_enabled: bool = True
    gdpr_enabled: bool = True
    load_test_users: int = 100
    load_test_spawn_rate: float = 10.0
    load_test_duration: str = "5m"
    # Security settings
    session_timeout: int = 3600  # 1 hour
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15 minutes
    # Feature flags
    features: Dict[str, bool] = field(
        default_factory=lambda: {
            "forum": True,
            "cms": True,
            "admin": True,
            "api": True,
            "oauth": True,
            "gdpr": True,
            "pwa": True,
            "realtime": True,
            "microservices": False,
            "cdn": False,
        }
    )


class ConfigManager:
    """Manages configuration across different environments"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.environments: Dict[str, EnvironmentConfig] = {}
        self.current_env: Optional[Environment] = None
        self.secret_manager = SecretManager()
        self.logger = logging.getLogger(__name__)

        # Load all environment configurations
        self._load_environments()

    def _load_environments(self):
        """Load configuration for all environments"""
        for env in Environment:
            config_file = self.config_dir / f"config.{env.value}.json"
            if config_file.exists():
                try:
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        config = EnvironmentConfig(**data)
                        self.environments[env.value] = config
                except Exception as e:
                    self.logger.error(f"Failed to load config for {env.value}: {e}")
            else:
                # Create default configuration
                self.environments[env.value] = self._create_default_config(env.value)

    def _create_default_config(self, env_name: str) -> EnvironmentConfig:
        """Create default configuration for an environment"""
        config = EnvironmentConfig(name=env_name)

        # Environment-specific defaults
        if env_name == "development":
            config.debug = True
            config.database_url = "sqlite:///panel_dev.db"
            config.redis_url = "redis://localhost:6379/0"
            config.mail_server = "localhost"
            config.secret_key = self._generate_secret_key()

        elif env_name == "testing":
            config.debug = False
            config.testing = True
            config.database_url = "sqlite:///test.db"
            config.redis_url = "redis://localhost:6379/1"
            config.secret_key = "test-secret-key-for-testing-only"

        elif env_name == "staging":
            config.debug = False
            config.database_url = "postgresql://panel:password@staging-db:5432/panel"
            config.redis_url = "redis://staging-redis:6379/0"
            config.cdn_enabled = True
            config.cdn_url = "https://cdn-staging.panel.com"
            config.secret_key = self.secret_manager.get_secret("staging/secret_key")

        elif env_name == "production":
            config.debug = False
            config.database_url = "postgresql://panel:password@prod-db:5432/panel"
            config.redis_url = "redis://prod-redis:6379/0"
            config.cdn_enabled = True
            config.cdn_url = "https://cdn.panel.com"
            config.microservices_enabled = True
            config.api_gateway_enabled = True
            config.secret_key = self.secret_manager.get_secret("production/secret_key")

        return config

    def _generate_secret_key(self) -> str:
        """Generate a secure random secret key"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")

    def set_environment(self, env: Environment):
        """Set the current environment"""
        if env.value not in self.environments:
            raise ValueError(f"Environment {env.value} not configured")

        self.current_env = env
        os.environ["FLASK_ENV"] = env.value
        self.logger.info(f"Environment set to: {env.value}")

    def get_current_config(self) -> EnvironmentConfig:
        """Get configuration for current environment"""
        if not self.current_env:
            # Auto-detect from environment variable
            env_name = os.getenv("FLASK_ENV", "development")
            try:
                self.current_env = Environment(env_name)
            except ValueError:
                self.current_env = Environment.DEVELOPMENT

        return self.environments[self.current_env.value]

    def update_config(self, env: str, updates: Dict[str, Any]):
        """Update configuration for an environment"""
        if env not in self.environments:
            raise ValueError(f"Environment {env} not found")

        config = self.environments[env]
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                self.logger.warning(f"Unknown config key: {key}")

        # Save to file
        self._save_config(env)

    def _save_config(self, env: str):
        """Save configuration to file"""
        config = self.environments[env]
        config_file = self.config_dir / f"config.{env}.json"

        # Convert to dict, excluding sensitive data
        config_dict = {
            k: v
            for k, v in config.__dict__.items()
            if not k.startswith("_") and k not in ["secret_key", "mail_password"]
        }

        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2, default=str)

    def validate_config(self, env: str) -> List[str]:
        """Validate configuration for an environment"""
        config = self.environments[env]
        errors = []

        # Required fields
        required_fields = ["secret_key", "database_url"]
        for field in required_fields:
            value = getattr(config, field, None)
            if not value:
                errors.append(f"Missing required field: {field}")

        # URL validations
        if config.database_url and not config.database_url.startswith(
            ("sqlite://", "postgresql://", "mysql://")
        ):
            errors.append("Invalid database URL format")

        if config.redis_url and not config.redis_url.startswith("redis://"):
            errors.append("Invalid Redis URL format")

        # Security validations
        if config.secret_key and len(config.secret_key) < 32:
            errors.append("Secret key should be at least 32 characters")

        if config.password_min_length < 8:
            errors.append("Password minimum length should be at least 8")

        return errors

    def get_flask_config(self, env: str) -> Dict[str, Any]:
        """Get Flask-compatible configuration"""
        config = self.environments[env]

        flask_config = {
            "DEBUG": config.debug,
            "TESTING": config.testing,
            "SQLALCHEMY_DATABASE_URI": config.database_url,
            "REDIS_URL": config.redis_url,
            "MAIL_SERVER": config.mail_server,
            "MAIL_PORT": config.mail_port,
            "MAIL_USERNAME": config.mail_username,
            "MAIL_PASSWORD": config.mail_password,
            "MAIL_USE_TLS": config.mail_use_tls,
            "MAIL_USE_SSL": config.mail_use_ssl,
            "SESSION_TIMEOUT": config.session_timeout,
            "PASSWORD_MIN_LENGTH": config.password_min_length,
            "MAX_LOGIN_ATTEMPTS": config.max_login_attempts,
            "LOCKOUT_DURATION": config.lockout_duration,
        }

        # Only set SECRET_KEY when explicitly configured.
        # (Otherwise leave any existing SECRET_KEY intact so session/OAuth works.)
        if config.secret_key:
            flask_config["SECRET_KEY"] = config.secret_key

        # Add OAuth providers
        for provider, settings in config.oauth_providers.items():
            flask_config[f"{provider.upper()}_CLIENT_ID"] = settings.get(
                "client_id", ""
            )
            flask_config[f"{provider.upper()}_CLIENT_SECRET"] = settings.get(
                "client_secret", ""
            )

        # Add feature flags
        for feature, enabled in config.features.items():
            flask_config[f"{feature.upper()}_ENABLED"] = enabled

        # Add CDN settings
        flask_config["CDN_ENABLED"] = config.cdn_enabled
        flask_config["CDN_URL"] = config.cdn_url
        flask_config["CDN_PROVIDER"] = config.cdn_provider

        # Add microservices settings
        flask_config["MICROSERVICES_ENABLED"] = config.microservices_enabled
        flask_config["API_GATEWAY_ENABLED"] = config.api_gateway_enabled

        # Add monitoring settings
        flask_config["PERFORMANCE_MONITORING_ENABLED"] = (
            config.performance_monitoring_enabled
        )

        # Add load testing settings
        flask_config["LOAD_TEST_USERS"] = config.load_test_users
        flask_config["LOAD_TEST_SPAWN_RATE"] = config.load_test_spawn_rate
        flask_config["LOAD_TEST_DURATION"] = config.load_test_duration

        return flask_config

    def create_env_file(self, env: str, output_file: str = None):
        """Create .env file for an environment"""
        config = self.environments[env]
        env_file = output_file or f".env.{env}"

        env_vars = []

        # Basic Flask settings
        env_vars.extend(
            [
                f"FLASK_ENV={env}",
                f"DEBUG={'true' if config.debug else 'false'}",
                f"TESTING={'true' if config.testing else 'false'}",
                f"SECRET_KEY={config.secret_key}",
            ]
        )

        # Database and cache
        if config.database_url:
            env_vars.append(f"DATABASE_URL={config.database_url}")
        if config.redis_url:
            env_vars.append(f"REDIS_URL={config.redis_url}")

        # Email settings
        if config.mail_server:
            env_vars.extend(
                [
                    f"MAIL_SERVER={config.mail_server}",
                    f"MAIL_PORT={config.mail_port}",
                    f"MAIL_USERNAME={config.mail_username}",
                    f"MAIL_USE_TLS={'true' if config.mail_use_tls else 'false'}",
                    f"MAIL_USE_SSL={'true' if config.mail_use_ssl else 'false'}",
                ]
            )

        # CDN settings
        if config.cdn_enabled:
            env_vars.extend(
                [
                    f"CDN_ENABLED=true",
                    f"CDN_URL={config.cdn_url}",
                    f"CDN_PROVIDER={config.cdn_provider}",
                ]
            )

        # Microservices
        if config.microservices_enabled:
            env_vars.append("MICROSERVICES_ENABLED=true")
        if config.api_gateway_enabled:
            env_vars.append("API_GATEWAY_ENABLED=true")

        # Security settings
        env_vars.extend(
            [
                f"SESSION_TIMEOUT={config.session_timeout}",
                f"PASSWORD_MIN_LENGTH={config.password_min_length}",
                f"MAX_LOGIN_ATTEMPTS={config.max_login_attempts}",
                f"LOCKOUT_DURATION={config.lockout_duration}",
            ]
        )

        # Feature flags
        for feature, enabled in config.features.items():
            env_vars.append(
                f"{feature.upper()}_ENABLED={'true' if enabled else 'false'}"
            )

        # Write to file
        with open(env_file, "w") as f:
            f.write("\n".join(env_vars))

        self.logger.info(f"Environment file created: {env_file}")

    def list_environments(self) -> List[str]:
        """List all configured environments"""
        return list(self.environments.keys())

    def get_environment_info(self, env: str) -> Dict[str, Any]:
        """Get detailed information about an environment"""
        config = self.environments[env]
        errors = self.validate_config(env)

        return {
            "name": config.name,
            "debug": config.debug,
            "testing": config.testing,
            "features_enabled": sum(config.features.values()),
            "total_features": len(config.features),
            "has_database": bool(config.database_url),
            "has_redis": bool(config.redis_url),
            "has_mail": bool(config.mail_server),
            "has_cdn": config.cdn_enabled,
            "has_oauth": bool(config.oauth_providers),
            "validation_errors": errors,
            "is_valid": len(errors) == 0,
        }


class SecretManager:
    """Manages sensitive configuration data"""

    def __init__(self, key_file: str = ".config_key"):
        self.key_file = Path(key_file)
        self._key = None

    def _get_key(self) -> bytes:
        """Get or create encryption key"""
        if self._key:
            return self._key

        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self._key = f.read()
        else:
            # Generate new key
            self._key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self._key)

        return self._key

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret value"""
        f = Fernet(self._get_key())
        encrypted = f.encrypt(secret.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value"""
        f = Fernet(self._get_key())
        encrypted = base64.urlsafe_b64decode(encrypted_secret)
        return f.decrypt(encrypted).decode()

    def get_secret(self, key: str, default: str = "") -> str:
        """Get a secret from environment or encrypted storage"""
        # First check environment variables
        env_key = key.upper().replace("/", "_").replace("-", "_")
        env_value = os.getenv(env_key)
        if env_value:
            return env_value

        # Check for encrypted secrets file
        secrets_file = Path(".secrets")
        if secrets_file.exists():
            try:
                with open(secrets_file, "r") as f:
                    secrets = json.load(f)
                    encrypted_value = secrets.get(key)
                    if encrypted_value:
                        return self.decrypt_secret(encrypted_value)
            except Exception:
                pass

        return default

    def set_secret(self, key: str, value: str):
        """Store an encrypted secret"""
        secrets_file = Path(".secrets")
        secrets = {}

        if secrets_file.exists():
            try:
                with open(secrets_file, "r") as f:
                    secrets = json.load(f)
            except Exception:
                pass

        secrets[key] = self.encrypt_secret(value)

        with open(secrets_file, "w") as f:
            json.dump(secrets, f, indent=2)


# Global configuration manager
config_manager = ConfigManager()


def init_config_manager(app):
    """Initialize configuration manager for Flask app"""
    global config_manager

    def _redact_db_url(url: str) -> str:
        try:
            from urllib.parse import urlsplit, urlunsplit

            parts = urlsplit(url)
            if not parts.scheme or not parts.netloc:
                return url

            if parts.username is None and parts.password is None:
                return url

            host = parts.hostname or ""
            if parts.port is not None:
                host = f"{host}:{parts.port}"

            userinfo = ""
            if parts.username:
                if parts.password is not None:
                    userinfo = f"{parts.username}:***@"
                else:
                    userinfo = f"{parts.username}@"

            redacted_netloc = f"{userinfo}{host}"
            return urlunsplit((parts.scheme, redacted_netloc, parts.path, parts.query, parts.fragment))
        except Exception:
            return url

    # Detect environment
    env_name = os.getenv("FLASK_ENV", "development")
    try:
        env = Environment(env_name)
    except ValueError:
        env = Environment.DEVELOPMENT

    config_manager.set_environment(env)

    # Load configuration into Flask app
    flask_config = config_manager.get_flask_config(env.value)
    app.config.update(flask_config)

    # Allow environment variables to override the DB config.
    # This is important for packaged installs where systemd provides an
    # EnvironmentFile (/etc/panel/panel.env) and the installer writes PANEL_DB_*.
    try:
        from urllib.parse import quote_plus

        override_db = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")

        panel_use_sqlite = os.environ.get("PANEL_USE_SQLITE")
        if not override_db and panel_use_sqlite is not None:
            if str(panel_use_sqlite).strip() in ("1", "true", "yes"):
                override_db = os.environ.get("PANEL_SQLITE_URI") or "sqlite:///panel_dev.db"
            elif str(panel_use_sqlite).strip() in ("0", "false", "no"):
                db_user = os.environ.get("PANEL_DB_USER", "paneluser")
                db_pass = os.environ.get("PANEL_DB_PASS", "")
                db_host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
                db_port = os.environ.get("PANEL_DB_PORT", "5432")
                db_name = os.environ.get("PANEL_DB_NAME", "paneldb")
                override_db = f"postgresql+psycopg2://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}"

        # If PANEL_DB_* is set but PANEL_USE_SQLITE isn't, assume Postgres.
        if not override_db and any(os.environ.get(k) for k in ("PANEL_DB_HOST", "PANEL_DB_USER", "PANEL_DB_NAME")):
            db_user = os.environ.get("PANEL_DB_USER", "paneluser")
            db_pass = os.environ.get("PANEL_DB_PASS", "")
            db_host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
            db_port = os.environ.get("PANEL_DB_PORT", "5432")
            db_name = os.environ.get("PANEL_DB_NAME", "paneldb")
            override_db = f"postgresql+psycopg2://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}"

        if override_db:
            app.config["SQLALCHEMY_DATABASE_URI"] = override_db
    except Exception:
        pass

    # IMPORTANT:
    # Our environment JSON configs intentionally do not persist `secret_key`.
    # When such a config is loaded, `config.secret_key` becomes an empty string,
    # and app.config.update() would wipe a previously-valid SECRET_KEY.
    # Guarantee a usable secret key after applying config-manager settings.
    try:
        if ensure_secret_key is not None:
            ensure_secret_key(app, candidates=[app.config.get("SECRET_KEY")])
    except Exception:
        pass

    # Emit a high-signal startup log showing the effective DB target.
    # This helps diagnose cases where Alembic migrations were applied to one
    # database but the running systemd service points to another.
    try:
        effective_db = app.config.get("SQLALCHEMY_DATABASE_URI")
        if isinstance(effective_db, str) and effective_db:
            app.logger.info(f"Effective SQLALCHEMY_DATABASE_URI: {_redact_db_url(effective_db)}")
    except Exception:
        pass

    app.logger.info(f"Configuration loaded for environment: {env.value}")

    return config_manager


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager"""
    return config_manager


# Utility functions
def create_environment_configs():
    """Create configuration files for all environments"""
    manager = ConfigManager()

    for env_name in manager.list_environments():
        config_file = Path("config") / f"config.{env_name}.json"
        if not config_file.exists():
            manager._save_config(env_name)
            print(f"Created config file: {config_file}")

    print("Environment configurations created")


def validate_all_configs():
    """Validate all environment configurations"""
    manager = ConfigManager()
    all_valid = True

    for env_name in manager.list_environments():
        errors = manager.validate_config(env_name)
        if errors:
            print(f"? {env_name} configuration has errors:")
            for error in errors:
                print(f"  - {error}")
            all_valid = False
        else:
            print(f"? {env_name} configuration is valid")

    return all_valid


def setup_environment(env_name: str):
    """Setup environment for development/testing"""
    manager = ConfigManager()

    if env_name not in manager.list_environments():
        print(f"Environment {env_name} not found")
        return False

    # Set environment
    try:
        env = Environment(env_name)
        manager.set_environment(env)
    except ValueError:
        print(f"Invalid environment: {env_name}")
        return False

    # Create .env file
    manager.create_env_file(env_name)

    # Validate configuration
    errors = manager.validate_config(env_name)
    if errors:
        print(f"Configuration validation failed for {env_name}:")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"Environment {env_name} setup complete")
    return True
