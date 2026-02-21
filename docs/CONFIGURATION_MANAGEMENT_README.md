# Configuration Management Implementation

This document describes the configuration management system implemented for the Panel application using Python's built-in validation capabilities.

## Overview

The configuration management system provides:

1. **Schema Validation** - Built-in Python validation for configuration values
2. **Type Safety** - Type checking with automatic validation
3. **Environment Variables** - Support for configuration via environment variables
4. **Configuration Files** - JSON-based configuration file support
5. **Startup Validation** - Configuration validation at application startup
6. **CLI Tools** - Command-line tools for configuration management

## Configuration Classes

### DatabaseConfig

```python
class DatabaseConfig:
    use_sqlite: bool = True
    sqlite_uri: str = "sqlite:///panel_dev.db"
    postgres_user: str = "paneluser"
    postgres_password: str = "panelpass"
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    pool_pre_ping: bool = True
    pool_recycle: int = 300
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False
```

### LoggingConfig

```python
class LoggingConfig:
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    directory: Path = Path("instance/logs")
    format: str = "json"  # json or text
    audit_enabled: bool = True
    audit_directory: Path = Path("instance/audit_logs")
    performance_threshold: float = 500.0
```

### SecurityConfig

```python
class SecurityConfig:
    secret_key: str  # Required, minimum 16 characters
    admin_emails: List[str] = []  # Email validation
```

## Environment Variables

Configuration can be set via environment variables:

```bash
# Database
# Preferred
DATABASE_URL=postgresql+psycopg2://paneluser:panelpass@127.0.0.1:5432/paneldb

# Or split connection parts (the app will build a PostgreSQL URL)
PANEL_DB_USER=paneluser
PANEL_DB_PASS=panelpass
PANEL_DB_HOST=127.0.0.1
PANEL_DB_PORT=5432
PANEL_DB_NAME=paneldb

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/var/log/panel

# Security (required)
PANEL_SECRET_KEY=your-secret-key-here
PANEL_ADMIN_EMAILS=admin@example.com,admin2@example.com

# ET:Legacy
ET_SERVER_HOST=127.0.0.1
ET_SERVER_PORT=27960
ET_RCON_PASSWORD=secure-password

# Redis
PANEL_REDIS_URL=redis://127.0.0.1:6379/0

# Notifications
PANEL_DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

## Validation Rules

### Type Validation

- **Strings**: Length validation for secret keys
- **Integers**: Range validation for ports (1-65535)
- **Booleans**: Automatic string-to-bool conversion
- **Emails**: RFC-compliant email validation using regex
- **URLs**: Format validation for Redis URLs and webhooks

### Required Fields

- `secret_key`: Must be at least 16 characters
- Valid log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Valid log formats: json, text
- Valid port ranges: 1-65535

### Cross-Field Validation

- Email format validation for admin emails
- Redis URL format validation
- Discord webhook URL validation

## CLI Commands

### Validate Configuration

```bash
# Validate current configuration
flask config-validate

# Output:
✅ Configuration is valid
Database: sqlite:///panel_dev.db
Log Level: INFO
```

### Show Configuration

```bash
# Show current configuration (with sensitive data masked)
flask config-show

# Output:
Current Configuration:
==================================================

Database:
  SQLALCHEMY_DATABASE_URI: sqlite:///panel_dev.db
  SQLALCHEMY_ECHO: False

Logging:
  LOG_LEVEL: INFO
  LOG_FORMAT: json
  LOG_DIR: instance/logs

Security:
  SECRET_KEY: ***masked***

ET:Legacy:
  ET_SERVER_HOST: 127.0.0.1
  ET_SERVER_PORT: 27960

System:
  OS_SYSTEM: Linux
  OS_DISTRO: Alpine Linux
```

### Check Configuration

```bash
# Check for common configuration issues
flask config-check

# Output:
✅ No configuration issues found
```

### Generate Template

```bash
# Generate configuration template
flask config-template

# Output:
Configuration template generated: config_template.json
```

## Programmatic Usage

### Load Validated Configuration

```python
from simple_config import load_config

# Load and validate configuration
config = load_config()

# Access validated values
db_uri = config.database.sqlalchemy_database_uri
log_level = config.logging.level
secret_key = config.security.secret_key
```

### Flask Integration

```python
from config_validator import get_validated_config

# Get validated config instance
config = get_validated_config()

# Access configuration values
db_uri = config.database.sqlalchemy_database_uri
is_feature_enabled = config.feature_flags.get('new_feature', False)
```

## Startup Validation

Configuration is automatically validated at application startup:

```python
# In app.py
from config_validator import validate_configuration_at_startup

app = Flask(__name__)
validate_configuration_at_startup(app)  # Validates before first request
```

### Strict Mode

By default, configuration validation failures cause the application to exit:

```bash
PANEL_CONFIG_STRICT=true  # Default: exit on validation failure
PANEL_CONFIG_STRICT=false # Continue with invalid config (development only)
```

## Error Handling

### Validation Errors

```python
from simple_config import ValidationError

try:
    config = load_config()
except ValidationError as e:
    for error in e.errors:
        print(f"Configuration error: {error['msg']}")
```

### Common Errors

- **Missing secret key**: `SECRET_KEY must be at least 16 characters long`
- **Invalid log level**: `LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL`
- **Invalid email**: `Invalid email format: bad-email`
- **Invalid port**: `ET_SERVER_PORT must be between 1 and 65535`

## Configuration Files

### JSON Configuration File

```json
{
  "database": {
    "use_sqlite": true,
    "sqlite_uri": "sqlite:///panel_dev.db"
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "security": {
    "secret_key": "your-very-secure-secret-key-here",
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
```

### File Validation

```python
from simple_config import validate_config_file

# Validate a configuration file
is_valid = validate_config_file('config.json')
```

## Security Considerations

1. **Secret Management**: Never commit secrets to version control
2. **Environment Separation**: Use different configurations for dev/staging/prod
3. **Access Control**: Restrict access to configuration files
4. **Validation**: All configuration values are validated at startup

## Performance Impact

- **Validation Overhead**: Minimal - validation occurs once at startup
- **Memory Usage**: Lightweight configuration objects
- **Startup Time**: Negligible impact on application startup

## Dependencies

No external dependencies required - uses only Python standard library.

## Next Steps

After implementing configuration management, continue with:

1. **Security Hardening** - Enhanced CSP and security headers
2. **Monitoring Dashboard** - Grafana integration