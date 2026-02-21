"""
Configuration Validator

Validates application configuration at startup and provides configuration management utilities.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask

from simple_config import PanelConfig, ValidationError, load_config

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration validator for Flask applications"""

    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.validated_config: Optional[PanelConfig] = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize configuration validation for Flask app"""
        self.app = app

        # Validate configuration before first request
        app.before_first_request(self._validate_and_apply_config)

        # Add CLI commands
        self._add_cli_commands(app)

    def _validate_and_apply_config(self) -> None:
        """Validate configuration and apply to Flask app"""
        try:
            # Load and validate configuration
            config = load_config()
            self.validated_config = config

            # Apply configuration to Flask app
            flask_config = config.to_flask_config()
            self.app.config.update(flask_config)

            logger.info(
                "Configuration validated and applied successfully",
                extra={
                    "database_uri": config.database.sqlalchemy_database_uri,
                    "log_level": config.logging.level,
                    "log_format": config.logging.format,
                },
            )

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            # In production, you might want to exit the application
            if os.environ.get("PANEL_CONFIG_STRICT", "true").lower() == "true":
                logger.error("Exiting due to configuration validation failure")
                sys.exit(1)
            else:
                logger.warning(
                    "Continuing with invalid configuration (strict mode disabled)"
                )

    def _add_cli_commands(self, app: Flask) -> None:
        """Add configuration CLI commands"""

        @app.cli.command("config-validate")
        def validate_command():
            """Validate current configuration"""
            try:
                config = load_config()
                print("✅ Configuration is valid")
                print(f"Database: {config.database.sqlalchemy_database_uri}")
                print(f"Log Level: {config.logging.level}")
                print(f"Log Format: {config.logging.format}")
                return True
            except Exception as e:
                print(f"❌ Configuration validation failed: {e}")
                return False

        @app.cli.command("config-show")
        def show_command():
            """Show current configuration"""
            try:
                config = load_config()
                flask_config = config.to_flask_config()

                print("Current Configuration:")
                print("=" * 50)

                # Group configurations by category
                categories = {
                    "Database": ["SQLALCHEMY_DATABASE_URI", "SQLALCHEMY_ECHO"],
                    "Logging": ["LOG_LEVEL", "LOG_FORMAT", "LOG_DIR"],
                    "Security": ["SECRET_KEY"],
                    "ET:Legacy": ["ET_SERVER_HOST", "ET_SERVER_PORT"],
                    "System": ["OS_SYSTEM", "OS_DISTRO"],
                }

                for category, keys in categories.items():
                    print(f"\n{category}:")
                    for key in keys:
                        if key in flask_config:
                            value = flask_config[key]
                            # Mask sensitive values
                            if "password" in key.lower() or "secret" in key.lower():
                                value = "***masked***"
                            print(f"  {key}: {value}")

                return True
            except Exception as e:
                print(f"❌ Failed to load configuration: {e}")
                return False

        @app.cli.command("config-template")
        def template_command():
            """Generate configuration template"""
            from config_schema import generate_config_template

            output_file = "config_template.json"
            generate_config_template(output_file)
            print(f"Configuration template generated: {output_file}")

        @app.cli.command("config-check")
        def check_command():
            """Check configuration for common issues"""
            issues = []

            try:
                config = load_config()

                # Check database configuration
                if config.database.postgres_password == "panelpass":
                    issues.append(
                        "Using default PostgreSQL password - change in production"
                    )

                # Check secret key
                if config.security.secret_key in [
                    "dev-secret-key-change",
                    "dev-local-change-me",
                ]:
                    issues.append("Using default secret key - change in production")

                # Check log directory
                if not config.logging.directory.exists():
                    try:
                        config.logging.directory.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        issues.append(
                            f"Cannot create log directory: {config.logging.directory}"
                        )

                # Check audit directory
                if (
                    config.logging.audit_enabled
                    and not config.logging.audit_directory.exists()
                ):
                    try:
                        config.logging.audit_directory.mkdir(
                            parents=True, exist_ok=True
                        )
                    except Exception:
                        issues.append(
                            f"Cannot create audit log directory: {config.logging.audit_directory}"
                        )

                # Check backup directory
                if not config.system.backup_dir.exists():
                    try:
                        config.system.backup_dir.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        issues.append(
                            f"Cannot create backup directory: {config.system.backup_dir}"
                        )

                if issues:
                    print("⚠️  Configuration Issues Found:")
                    for issue in issues:
                        print(f"  - {issue}")
                    return False
                else:
                    print("✅ No configuration issues found")
                    return True

            except Exception as e:
                print(f"❌ Configuration check failed: {e}")
                return False


def validate_configuration_at_startup(app: Flask) -> None:
    """Validate configuration at application startup"""
    validator = ConfigValidator(app)


def get_validated_config() -> PanelConfig:
    """Get the validated configuration instance"""
    from flask import current_app

    if not hasattr(current_app, "config_validator"):
        current_app.config_validator = ConfigValidator(current_app)

    validator = current_app.config_validator
    if validator.validated_config is None:
        validator._validate_and_apply_config()

    return validator.validated_config


def reload_configuration() -> bool:
    """Reload configuration from environment"""
    try:
        from flask import current_app

        if hasattr(current_app, "config_validator"):
            validator = current_app.config_validator
            validator._validate_and_apply_config()
            return True
        else:
            # Create new validator if not exists
            ConfigValidator(current_app)
            return True

    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        return False


# Utility functions for configuration access
def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value with validation"""
    config = get_validated_config()

    # Map common keys to config attributes
    key_mapping = {
        "database_uri": lambda: config.database.sqlalchemy_database_uri,
        "log_level": lambda: config.logging.level,
        "log_format": lambda: config.logging.format,
        "secret_key": lambda: config.security.secret_key,
        "redis_url": lambda: config.redis_url,
    }

    if key in key_mapping:
        return key_mapping[key]()
    else:
        # Try to get from Flask config
        from flask import current_app

        return current_app.config.get(key, default)


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled"""
    config = get_validated_config()
    return config.feature_flags.get(feature_name, False)
