# Multi-Environment Configuration Management

This guide explains the multi-environment configuration management system for the Panel application, providing secure, environment-specific configuration handling.

## Overview

The Panel application includes comprehensive configuration management with:

- **Environment-Specific Configurations**: Separate settings for development, staging, production, and testing
- **Secure Secret Management**: Encrypted storage of sensitive data
- **Configuration Validation**: Automated validation and error checking
- **Environment Switching**: Easy switching between environments
- **Backup & Recovery**: Configuration backup and restore capabilities

## Configuration Architecture

### Environment Types

The system supports four environment types:

- **Development**: Local development with debug features enabled
- **Staging**: Pre-production environment for testing
- **Production**: Live production environment with security hardening
- **Testing**: Automated testing environment with minimal features

### Configuration Files

Each environment has its own configuration file:

```
config/
??? config.development.json
??? config.staging.json
??? config.production.json
??? config.testing.json
```

### Configuration Structure

```json
{
  "name": "environment_name",
  "debug": false,
  "testing": false,
  "database_url": "postgresql://...",
  "redis_url": "redis://...",
  "cdn_enabled": true,
  "features": {
    "forum": true,
    "cms": true,
    "admin": true
  }
}
```

## Getting Started

### Initial Setup

1. **Initialize configuration system**:
   ```bash
   make config-init
   ```

2. **Setup your environment**:
   ```bash
   make config-setup ENV=development
   ```

3. **Copy environment template**:
   ```bash
   cp .env.example .env
   # Edit .env with your specific values
   ```

4. **Validate configuration**:
   ```bash
   make config-validate
   ```

### Environment Variables

The system uses environment variables for sensitive data:

```bash
# Flask settings
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# External services
REDIS_URL=redis://localhost:6379
MAIL_SERVER=smtp.gmail.com
```

## Configuration Management

### Listing Environments

```bash
make config-list
```

Output:
```
? development
   Features: 8/10 enabled
   Database: Yes
   Redis: Yes
   CDN: No

? staging
   Features: 9/10 enabled
   Database: Yes
   Redis: Yes
   CDN: Yes
```

### Viewing Configuration

```bash
make config-show ENV=production
```

### Updating Configuration

```bash
# Update a configuration value
make config-update ENV=development KEY=debug VALUE=false

# Enable a feature
make config-update ENV=staging KEY=features.cdn VALUE=true
```

### Environment Setup

```bash
# Setup development environment
make config-setup ENV=development

# Setup production environment
make config-setup ENV=production
```

## Secret Management

### Encrypting Secrets

```bash
# Encrypt and store a database password
make config-encrypt KEY=db_password VALUE=mysecretpassword

# Encrypt API keys
make config-encrypt KEY=stripe_api_key VALUE=sk_live_...
```

### Accessing Secrets

The application automatically decrypts secrets when needed:

```python
from src.panel.config_manager import get_config_manager

manager = get_config_manager()
db_password = manager.secret_manager.get_secret('db_password')
```

### Manual Decryption

```bash
# Decrypt a stored secret
make config-decrypt KEY=db_password
```

## Security Features

### Encryption

- **AES-256 Encryption**: All secrets are encrypted using AES-256
- **PBKDF2 Key Derivation**: Secure key generation from passwords
- **Key Rotation**: Support for rotating encryption keys

### Access Control

- **Environment Isolation**: Configurations are environment-specific
- **Permission Levels**: Different access levels for different environments
- **Audit Logging**: All configuration changes are logged

### Validation

- **Schema Validation**: Configuration files are validated against schemas
- **Type Checking**: Values are type-checked and validated
- **Cross-Environment Checks**: Consistency validation across environments

## Environment-Specific Features

### Development Environment

```json
{
  "debug": true,
  "features": {
    "forum": true,
    "cms": true,
    "admin": true,
    "api": true
  }
}
```

### Production Environment

```json
{
  "debug": false,
  "cdn_enabled": true,
  "microservices_enabled": true,
  "password_min_length": 12,
  "max_login_attempts": 3
}
```

### Testing Environment

```json
{
  "testing": true,
  "features": {
    "oauth": false,
    "realtime": false
  }
}
```

## Backup & Recovery

### Creating Backups

```bash
# Create configuration backup
make config-backup
```

This creates a timestamped backup in `config/backup/`.

### Restoring from Backup

```bash
# Restore from backup
make config-restore FILE=config/backup/20231201_143000.tar.gz
```

### Backup Contents

- Configuration files for all environments
- Encrypted secrets file
- Encryption keys (securely stored)
- Backup metadata

## Validation & Testing

### Configuration Validation

```bash
# Validate all environments
make config-validate

# Validate specific environment
python scripts/validate-config.py production

# Generate validation report
python scripts/validate-config.py --output validation-report.md
```

### Validation Checks

- **Required Fields**: Ensures all required configuration is present
- **Data Types**: Validates data types and formats
- **URL Formats**: Checks database and Redis URLs
- **Security Settings**: Validates security-related configurations
- **Cross-Environment**: Checks consistency across environments

### Automated Testing

```python
# Test configuration loading
def test_config_loading():
    manager = ConfigManager()
    config = manager.get_current_config()
    assert config.database_url is not None

# Test environment switching
def test_environment_switching():
    manager = ConfigManager()
    manager.set_environment(Environment.PRODUCTION)
    config = manager.get_current_config()
    assert not config.debug
```

## Integration with Development

### Flask Integration

The configuration system integrates seamlessly with Flask:

```python
from src.panel.config_manager import init_config_manager

app = Flask(__name__)
config_manager = init_config_manager(app)

# Configuration is now loaded into app.config
database_url = app.config['SQLALCHEMY_DATABASE_URI']
```

### Environment Detection

The system automatically detects the environment:

```bash
# Set environment via environment variable
export FLASK_ENV=production

# Or via command line
FLASK_ENV=staging python app.py
```

### Feature Flags

Use feature flags to enable/disable functionality:

```python
from flask import current_app

if current_app.config.get('FORUM_ENABLED', True):
    # Enable forum functionality
    pass
```

## Advanced Configuration

### Custom Configuration Classes

```python
@dataclass
class CustomConfig:
    custom_setting: str = "default"

    def to_dict(self):
        return asdict(self)
```

### Configuration Hooks

```python
def post_config_load(config):
    """Hook called after configuration is loaded"""
    # Custom validation or setup
    if config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

# Register hook
config_manager.add_hook('post_load', post_config_load)
```

### Dynamic Configuration

```python
# Load configuration from external sources
def load_from_vault():
    # Load secrets from HashiCorp Vault
    pass

def load_from_aws_secrets():
    # Load secrets from AWS Secrets Manager
    pass
```

## Troubleshooting

### Common Issues

#### Configuration Not Loading

```bash
# Check configuration files exist
ls -la config/

# Validate JSON syntax
python -m json.tool config/config.development.json

# Check file permissions
ls -l config/
```

#### Secrets Not Decrypting

```bash
# Check encryption key exists
ls -la .config_key

# Verify key permissions
ls -l .config_key

# Regenerate key (WARNING: This will invalidate all encrypted secrets)
rm .config_key
make config-init
```

#### Environment Variables Missing

```bash
# Check current environment variables
env | grep -E "(FLASK|DATABASE|REDIS)"

# Load .env file
source .env

# Check .env file syntax
cat .env | grep -v '^#' | grep -v '^$'
```

### Debug Commands

```bash
# Show current configuration
python -c "
from src.panel.config_manager import get_config_manager
manager = get_config_manager()
config = manager.get_current_config()
print(f'Environment: {config.name}')
print(f'Debug: {config.debug}')
print(f'Database: {config.database_url is not None}')
"

# Test configuration validation
python scripts/validate-config.py development --json

# Check environment detection
python -c "
import os
from src.panel.config_manager import Environment
env_name = os.getenv('FLASK_ENV', 'development')
print(f'Detected environment: {env_name}')
try:
    env = Environment(env_name)
    print(f'Valid environment: {env.value}')
except ValueError as e:
    print(f'Invalid environment: {e}')
"
```

## Best Practices

### Security

1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive data
3. **Rotate encryption keys** regularly
4. **Audit configuration changes** in production

### Organization

1. **Environment-specific configs** for different deployment stages
2. **Feature flags** for gradual rollouts
3. **Validation rules** for configuration integrity
4. **Documentation** for all configuration options

### Maintenance

1. **Regular backups** of configuration
2. **Automated validation** in CI/CD
3. **Change tracking** for configuration updates
4. **Rollback procedures** for configuration issues

This comprehensive configuration management system ensures secure, maintainable, and scalable configuration handling across all deployment environments.