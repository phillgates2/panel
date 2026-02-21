# Configuration System - Panel Application

## Quick Reference

### **?? Security Issues Found**
- ?? **CRITICAL**: Hardcoded credentials in `config/config.production.json`
- ?? **CRITICAL**: Mixed configuration systems causing confusion
- ?? **HIGH**: Inconsistent environment variable naming

### **? Fixed/Created**
- ? Comprehensive configuration analysis (`docs/CONFIG_FOLDER_ANALYSIS.md`)
- ? Configuration documentation (this file)
- ? Security recommendations

---

## Configuration Overview

Panel uses environment variables for configuration. The system is currently in transition with some legacy files that should be removed.

### **Active Configuration Files**

| File | Purpose | Status |
|------|---------|--------|
| `.env` | Local environment variables | ? Active (gitignored) |
| `.env.example` | Environment variable template | ? Active |
| `config.py` | Configuration loader | ? Active |
| `src/panel/config.py` | Core Config class | ? Active |

### **Legacy/Deprecated Files**

| File | Purpose | Status |
|------|---------|--------|
| `config/*.json` | JSON configurations | ?? **Contains hardcoded credentials - needs review** |
| `config_dev.py` | Development config | ?? Duplicate - should merge |
| `simple_config.py` | Simple config interface | ?? Duplicate - should merge |

---

## Quick Start

### 1. Create Your Local Configuration

```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
nano .env  # or your preferred editor

# At minimum, set these:
PANEL_SECRET_KEY=$(openssl rand -base64 32)
PANEL_DATABASE_PASSWORD=your_secure_password
```

### 2. Verify Configuration

```python
python -c "from config import config; print('Config loaded successfully')"
```

### 3. Start Application

```bash
python app.py
```

---

## Environment Variables

All Panel configuration uses the `PANEL_` prefix for consistency.

### **Critical Settings** (Must Configure)

```bash
# Security
PANEL_SECRET_KEY=                 # Generate: openssl rand -base64 32

# Database (if using PostgreSQL)
PANEL_DATABASE_TYPE=postgresql
PANEL_DATABASE_PASSWORD=          # Strong password required

# Production
PANEL_ENV=production              # Set to production
PANEL_DEBUG=false                 # NEVER true in production
```

### **Common Settings**

```bash
# Application
PANEL_HOST=0.0.0.0               # Listen address
PANEL_PORT=5000                  # Listen port

# Database
# PostgreSQL-only (recommended)
DATABASE_URL=postgresql+psycopg2://paneluser:strong_password@127.0.0.1:5432/paneldb

# Or provide connection parts (the app will build DATABASE_URL)
PANEL_DB_HOST=127.0.0.1
PANEL_DB_PORT=5432
PANEL_DB_NAME=paneldb
PANEL_DB_USER=paneluser
PANEL_DB_PASS=strong_password

# Redis
PANEL_REDIS_URL=redis://localhost:6379/0

# Features
PANEL_FORUM_ENABLED=true
PANEL_CMS_ENABLED=true
PANEL_API_ENABLED=true
```

See `.env.example` for complete list with descriptions.

---

## Configuration by Environment

### **Development**

```bash
PANEL_ENV=development
PANEL_DEBUG=true
DATABASE_URL=postgresql+psycopg2://paneluser:panelpass@127.0.0.1:5432/panel_dev
PANEL_LOG_LEVEL=DEBUG
```

### **Staging**

```bash
PANEL_ENV=staging
PANEL_DEBUG=false
DATABASE_URL=postgresql+psycopg2://paneluser:staging_password@db.example.com:5432/panel_staging
PANEL_LOG_LEVEL=INFO
```

### **Production**

```bash
PANEL_ENV=production
PANEL_DEBUG=false
DATABASE_URL=postgresql+psycopg2://paneluser:strong_production_password@db.example.com:5432/paneldb
PANEL_SESSION_COOKIE_SECURE=true
PANEL_LOG_LEVEL=WARNING
```

---

## Security Best Practices

### 1. Never Commit Secrets

```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Check for leaked secrets before committing
git diff --cached
```

### 2. Generate Strong Keys

```bash
# SECRET_KEY (required)
openssl rand -base64 32

# Database passwords
openssl rand -base64 24

# API keys
openssl rand -hex 32
```

### 3. Use Environment-Specific Files

```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production

# Load with:
export $(cat .env.production | xargs)
```

### 4. Rotate Credentials Regularly

```bash
# Update SECRET_KEY
PANEL_SECRET_KEY=$(openssl rand -base64 32)

# Update database password
PANEL_DATABASE_PASSWORD=$(openssl rand -base64 24)

# Restart application
sudo systemctl restart panel
```

---

## Common Configuration Patterns

### **PostgreSQL**

```bash
DATABASE_URL=postgresql+psycopg2://paneluser:secure_password@db.example.com:5432/paneldb

# Or split configuration:
PANEL_DB_HOST=db.example.com
PANEL_DB_PORT=5432
PANEL_DB_NAME=paneldb
PANEL_DB_USER=paneluser
PANEL_DB_PASS=secure_password
```

### **Redis for Caching**

```bash
PANEL_REDIS_URL=redis://localhost:6379/0
PANEL_CACHE_TYPE=redis
PANEL_CACHE_DEFAULT_TIMEOUT=300
```

### **OAuth Login**

```bash
PANEL_OAUTH_ENABLED=true

# Google
PANEL_GOOGLE_CLIENT_ID=your_client_id
PANEL_GOOGLE_CLIENT_SECRET=your_client_secret

# GitHub
PANEL_GITHUB_CLIENT_ID=your_client_id
PANEL_GITHUB_CLIENT_SECRET=your_client_secret
```

---

## Troubleshooting

### Configuration Not Loading

```bash
# Check if .env exists
ls -la .env

# Verify syntax
cat .env | grep -v '^#' | grep -v '^$'

# Test import
python -c "from config import config; print(config.SECRET_KEY[:10])"
```

### Database Connection Failed

```bash
# PostgreSQL: Check connection
psql -h localhost -U paneluser -d panel

# Check config
python -c "from config import config; print(config.SQLALCHEMY_DATABASE_URI)"
```

### Redis Connection Failed

```bash
# Check Redis is running
redis-cli ping

# Test connection
python -c "from config import config; print(config.REDIS_URL)"
```

### SECRET_KEY Warning

```bash
# Generate new key
openssl rand -base64 32

# Set in .env
echo "PANEL_SECRET_KEY=<generated_key>" >> .env
```

---

## Migration from JSON Configs

If you're using the old JSON configuration files:

### 1. Extract Current Settings

```bash
# Check what's in production.json
cat config/config.production.json
```

### 2. Convert to Environment Variables

```bash
# JSON:
{
  "database_url": "postgresql://user:pass@host:5432/db"
}

# .env:
PANEL_DATABASE_TYPE=postgresql
PANEL_DATABASE_USER=user
PANEL_DATABASE_PASSWORD=pass
PANEL_DATABASE_HOST=host
PANEL_DATABASE_PORT=5432
PANEL_DATABASE_NAME=db
```

### 3. Update Application Code

```python
# OLD (don't use):
from config.production import settings

# NEW (correct):
from config import config
```

### 4. Remove JSON Files

```bash
# After migration, remove JSON configs
rm config/config.*.json
```

---

## Configuration Validation

Panel validates critical configuration at startup.

### Validation Checks

- ? SECRET_KEY exists and is strong
- ? Database credentials are set (PostgreSQL)
- ? Required directories exist
- ? Critical services are reachable

### Manual Validation

```python
from config import config

# This runs validation automatically
# Raises ConfigValidationError if invalid
```

---

## Advanced Configuration

### Custom Configuration Class

```python
# config/custom.py
from src.panel.config import BaseConfig

class CustomConfig(BaseConfig):
    """Custom configuration."""
    
    # Override settings
    CUSTOM_FEATURE_ENABLED = True
    
    def validate(self):
        """Add custom validation."""
        super().validate()
        # Your validation here
```

### Load Custom Config

```python
# config.py
from config.custom import CustomConfig

config = CustomConfig()
```

---

## Related Documentation

- **Analysis**: `docs/CONFIG_FOLDER_ANALYSIS.md` - Complete analysis
- **Security**: `.github/SECRETS.md` - Secret management
- **Environment Template**: `.env.example` - All variables documented
- **Cloud Deployment**: `cloud-init/README.md` - Deployment configs

---

## Quick Commands

```bash
# Generate SECRET_KEY
openssl rand -base64 32

# Test configuration
python -c "from config import config; print('? Config OK')"

# Check database connection
python -c "from app import db; print('? DB OK')"

# Check Redis connection
redis-cli ping

# View current configuration (safe)
python -c "from config import config; print(f'ENV: {config.ENV}, DEBUG: {config.DEBUG}')"
```

---

## Support

### Issues

1. Check this README
2. Review `docs/CONFIG_FOLDER_ANALYSIS.md`
3. Verify `.env` file exists and is correct
4. Check application logs
5. Create issue with details

### Common Errors

| Error | Solution |
|-------|----------|
| `SECRET_KEY is required` | Set PANEL_SECRET_KEY in .env |
| `Database connection failed` | Check PostgreSQL credentials |
| `Redis connection failed` | Check PANEL_REDIS_URL |
| `Config validation failed` | Review validation error message |

---

**Status**: ? Configuration system documented  
**Last Updated**: December 2024  
**Version**: 1.0

For complete analysis, see: `docs/CONFIG_FOLDER_ANALYSIS.md`
