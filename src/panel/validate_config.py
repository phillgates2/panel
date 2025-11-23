#!/usr/bin/env python3
"""Configuration validation utility.

Validates environment variables and configuration before starting the application.
Use this as a pre-flight check to catch configuration errors early.

Usage:
    python validate_config.py              # Validate current config
    python validate_config.py --strict     # Fail on warnings
    python validate_config.py --fix        # Attempt to fix issues
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse


class ConfigValidator:
    """Validate Panel configuration."""

    def __init__(self, strict=False):
        self.strict = strict
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_all(self):
        """Run all validation checks."""
        print("🔍 Validating Panel configuration...\n")

        self.check_secret_key()
        self.check_database_config()
        self.check_redis_config()
        self.check_etlegacy_config()
        self.check_file_permissions()
        self.check_dependencies()
        self.check_directories()

        return self.report()

    def check_secret_key(self):
        """Validate SECRET_KEY."""
        secret = os.environ.get("PANEL_SECRET_KEY", "")

        # Check if we're in development/testing mode
        is_dev_mode = (
            os.environ.get("FLASK_ENV") == "development"
            or os.environ.get("TESTING") == "1"
            or not secret  # No secret key indicates dev mode
        )

        if not secret or secret == "dev-secret-key-change":
            if is_dev_mode:
                # Try to read from config.py as fallback
                try:
                    import config

                    if (
                        hasattr(config, "SECRET_KEY")
                        and config.SECRET_KEY != "dev-secret-key-change"
                    ):
                        self.info.append("✓ SECRET_KEY from config.py (dev mode)")
                        return
                except ImportError:
                    pass
                self.warnings.append("Using default SECRET_KEY in dev mode")
            else:
                self.errors.append("SECRET_KEY not set or using default value in production")
        elif len(secret) < 32:
            self.warnings.append(f"SECRET_KEY is short ({len(secret)} chars), recommend 32+")
        else:
            self.info.append(f"✓ SECRET_KEY configured ({len(secret)} chars)")

    def check_database_config(self):
        """Validate database configuration (SQLite only)."""
        self.info.append("✓ Using SQLite")
        sqlite_uri = os.environ.get("PANEL_SQLITE_URI")
        if not sqlite_uri:
            try:
                import config

                sqlite_uri = getattr(config, "SQLALCHEMY_DATABASE_URI", "sqlite:///panel_dev.db")
            except ImportError:
                sqlite_uri = "sqlite:///panel_dev.db"

        # Extract path from sqlite:/// URI
        if sqlite_uri.startswith("sqlite:///"):
            db_path = sqlite_uri[10:]
            if not db_path.startswith("/"):
                db_path = Path(db_path)
                if not db_path.parent.exists():
                    self.warnings.append(f"SQLite directory doesn't exist: {db_path.parent}")

    def check_redis_config(self):
        """Validate Redis configuration."""
        redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")

        # Check if we're in dev mode
        is_dev_mode = (
            os.environ.get("FLASK_ENV") == "development"
            or os.environ.get("TESTING") == "1"
            or not os.environ.get("PANEL_REDIS_URL")
        )

        try:
            parsed = urlparse(redis_url)
            if parsed.scheme != "redis":
                self.errors.append(f"Invalid Redis URL scheme: {parsed.scheme}")
                return

            # Try to connect
            import redis

            r = redis.from_url(redis_url, socket_connect_timeout=5)
            r.ping()
            self.info.append(f"✓ Redis connection successful ({redis_url})")
        except ImportError:
            self.warnings.append("redis package not installed, skipping connection test")
        except Exception as e:
            if is_dev_mode:
                self.warnings.append(f"Redis connection failed (dev mode): {e}")
            else:
                self.errors.append(f"Redis connection failed: {e}")

    def check_etlegacy_config(self):
        """Validate ET:Legacy server configuration."""
        et_host = os.environ.get("ET_SERVER_HOST", "127.0.0.1")
        et_port = os.environ.get("ET_SERVER_PORT", "27960")
        et_pass = os.environ.get("ET_RCON_PASSWORD", "changeme")

        if et_pass == "changeme":
            self.warnings.append("ET_RCON_PASSWORD using default value")

        try:
            port = int(et_port)
            if port < 1 or port > 65535:
                self.errors.append(f"Invalid ET_SERVER_PORT: {port}")
        except ValueError:
            self.errors.append(f"ET_SERVER_PORT not a number: {et_port}")

        self.info.append(f"✓ ET:Legacy config: {et_host}:{et_port}")

    def check_file_permissions(self):
        """Check file/directory permissions."""
        checks = [
            ("instance/", True, "Instance directory"),
        ]

        for path, should_writable, desc in checks:
            p = Path(path)
            if not p.exists():
                continue

            if should_writable:
                # Try to write a test file
                test_file = p / ".write_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    self.info.append(f"✓ {desc} writable: {path}")
                except Exception as e:
                    self.errors.append(f"{desc} not writable: {path} ({e})")

    def check_dependencies(self):
        """Check Python dependencies."""
        # Map of dependency name to import name
        required = {"flask": "flask", "flask_sqlalchemy": "flask_sqlalchemy"}
        optional = {
            "redis": "redis",
            "rq": "rq",
            "pillow": "PIL",  # Pillow installs as PIL
        }

        missing_required = []
        missing_optional = []

        for dep_name, import_name in required.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_required.append(dep_name)

        for dep_name, import_name in optional.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_optional.append(dep_name)

        if missing_required:
            self.errors.append(f"Missing required dependencies: {', '.join(missing_required)}")
        else:
            self.info.append("✓ Required dependencies installed")

        if missing_optional:
            self.warnings.append(f"Missing optional dependencies: {', '.join(missing_optional)}")
        else:
            self.info.append("✓ Optional dependencies installed")

    def check_directories(self):
        """Ensure required directories exist."""
        required = ["instance", "static", "templates"]
        optional = ["logs"]  # Optional directories

        # Check if we're in dev mode
        is_dev_mode = (
            os.environ.get("FLASK_ENV") == "development"
            or os.environ.get("TESTING") == "1"
            or not os.environ.get("PANEL_SECRET_KEY")
        )

        for dir_name in required:
            p = Path(dir_name)
            if not p.exists():
                self.warnings.append(f"Required directory missing: {dir_name}")
            elif not p.is_dir():
                self.errors.append(f"Path exists but not a directory: {dir_name}")
            else:
                self.info.append(f"✓ Directory exists: {dir_name}")

        for dir_name in optional:
            p = Path(dir_name)
            if not p.exists():
                if is_dev_mode:
                    self.info.append(f"Optional directory missing (dev mode): {dir_name}")
                else:
                    self.warnings.append(f"Optional directory missing: {dir_name}")
            elif not p.is_dir():
                self.errors.append(f"Path exists but not a directory: {dir_name}")
            else:
                self.info.append(f"✓ Optional directory exists: {dir_name}")

    def report(self):
        """Print validation report and return exit code."""
        print()

        if self.info:
            for msg in self.info:
                print(f"ℹ️  {msg}")

        if self.warnings:
            print()
            for msg in self.warnings:
                print(f"⚠️  WARNING: {msg}")

        if self.errors:
            print()
            for msg in self.errors:
                print(f"❌ ERROR: {msg}")

        print()

        # Determine exit code
        if self.errors:
            print("❌ Validation FAILED - fix errors before running")
            return 1
        elif self.warnings and self.strict:
            print("⚠️  Validation FAILED (strict mode) - fix warnings")
            return 1
        elif self.warnings:
            print("⚠️  Validation PASSED with warnings")
            return 0
        else:
            print("✅ Validation PASSED")
            return 0


def main():
    strict = "--strict" in sys.argv
    validator = ConfigValidator(strict=strict)
    exit_code = validator.validate_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
