# New Features Documentation

This document describes the 8 new features added to Panel for improved security, monitoring, and developer experience.

## Table of Contents

1. [Logging Infrastructure](#1-logging-infrastructure)
2. [Database Migrations](#2-database-migrations)
3. [Environment Configuration](#3-environment-configuration)
4. [API Rate Limiting](#4-api-rate-limiting)
5. [Health Check Endpoint](#5-health-check-endpoint)
6. [Security Headers](#6-security-headers)
7. [Input Validation](#7-input-validation)
8. [RQ Dashboard](#8-rq-dashboard)

---

## 1. Logging Infrastructure

### Overview
Replaced `print()` statements with Python's logging module for professional, structured logging.

### Features
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Multiple Handlers**:
  - Console output with timestamps
  - Daily rotating file logs (30 days retention)
  - Separate error log (errors only, 5 file rotation)
  - Security audit log (1 year retention)
- **Configurable**: Set `LOG_LEVEL` environment variable

### Usage

```python
from logging_config import log_security_event

# Log security events
log_security_event(
    event_type='login_success',
    message='User logged in',
    user_id=123,
    ip_address='192.168.1.1'
)
```

### Configuration

```bash
export LOG_LEVEL=INFO
export LOG_DIR=instance/logs
export AUDIT_LOG_ENABLED=True
```

### Log Files
- `instance/logs/panel.log` - General application log
- `instance/logs/panel_errors.log` - Error logs only
- `instance/audit_logs/security_audit.log` - Security events

---

## 2. Database Migrations

### Overview
Flask-Migrate integration for safe database schema changes and version control.

### Setup

```bash
# Initialize migrations (one-time)
make db-init

# Create a migration
make db-migrate message="Add user preferences table"

# Apply migrations
make db-upgrade

# Rollback migration
make db-downgrade
```

### Features
- Automatic schema change detection
- Safe rollback capability
- Migration history tracking
- Production-safe upgrades

### Usage

```python
# migrations_init.py is already configured
# Just use the make commands above
```

---

## 3. Environment Configuration

### Overview
Complete `.env.example` file documenting all environment variables.

### Setup

```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env
```

### Key Variables

```bash
# Database
PANEL_USE_SQLITE=1
DB_HOST=localhost
DB_NAME=panel_db

# Redis
PANEL_REDIS_URL=redis://127.0.0.1:6379/0

# Security
SECRET_KEY=change-this-in-production
MAX_QUERIES_PER_MINUTE=30

# Logging
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=True
```

See `.env.example` for complete list of 50+ configuration options.

---

## 4. API Rate Limiting

### Overview
Flask-Limiter integration to prevent API abuse and DDoS attacks.

### Features
- Per-user or per-IP rate limiting
- Redis-backed for distributed systems
- Custom limits per endpoint
- Automatic retry headers

### Setup

```python
# In app.py (uncomment to enable)
from rate_limiting import setup_rate_limiting
limiter = setup_rate_limiting(app)

# Apply to specific routes
@app.route('/api/endpoint')
@limiter.limit("30 per minute")
def api_endpoint():
    return jsonify({"status": "ok"})
```

### Default Limits
- General endpoints: 200/hour
- Login: 20/minute
- API endpoints: 30/minute (customizable)

---

## 5. Health Check Endpoint

### Overview
Production-ready health check endpoint for monitoring and load balancers.

### Endpoint

```
GET /health
```

### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T12:00:00Z",
  "uptime_seconds": 86400,
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

### Status Codes
- `200` - All systems healthy
- `503` - Degraded (database or Redis unavailable)

### Usage with Load Balancers

```nginx
# Nginx health check
location /health {
    access_log off;
    proxy_pass http://panel_backend;
}
```

---

## 6. Security Headers

### Overview
Comprehensive security headers implementation for protection against XSS, clickjacking, and other attacks.

### Headers Implemented

- **Content-Security-Policy**: Prevents XSS attacks
- **Strict-Transport-Security**: Forces HTTPS (production only)
- **X-Content-Type-Options**: Prevents MIME sniffing
- **X-Frame-Options**: Prevents clickjacking
- **X-XSS-Protection**: Browser XSS protection
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Disables unnecessary browser features

### Configuration

Headers are automatically applied to all responses. Adjust CSP policy in `security_headers.py`:

```python
csp_policy = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",
    "style-src": "'self' 'unsafe-inline'",
    # ... customize as needed
}
```

### Security Score
Implementing these headers improves security scores on:
- Mozilla Observatory
- Security Headers
- SSL Labs

---

## 7. Input Validation

### Overview
Marshmallow schemas for type-safe request validation with detailed error messages.

### Features
- Email validation
- Password complexity requirements
- Field length restrictions
- Custom validation rules

### Usage

```python
from input_validation import LoginSchema, validate_request

# Validate login request
validated_data, errors = validate_request(LoginSchema, request.form)
if errors:
    flash(f'Validation error: {errors}', 'error')
    return redirect(url_for('login'))

# Use validated data
email = validated_data['email']
password = validated_data['password']
```

### Available Schemas

- `LoginSchema` - Login validation
- `RegisterSchema` - User registration with password complexity
- `ServerCreateSchema` - Server creation with port validation
- `DatabaseQuerySchema` - SQL query validation
- `ApiKeyCreateSchema` - API key generation

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

---

## 8. RQ Dashboard

### Overview
Web interface for monitoring background jobs in Redis Queue.

### Setup

```python
# In app.py (uncomment to enable)
from rq_dashboard_setup import setup_rq_dashboard, require_admin_for_rq_dashboard
setup_rq_dashboard(app)
require_admin_for_rq_dashboard(app)
```

### Access

```
http://localhost:8080/rq
```

### Features
- View queued jobs
- Monitor job status (queued, started, finished, failed)
- View job results and exceptions
- Retry failed jobs
- Delete jobs
- Real-time updates

### Authentication
Requires system admin login. Access is protected automatically.

---

## Installation

All new features are included in the requirements.

```bash
# Install all dependencies
make install

# Or for development
make install-dev
```

### New Dependencies Added
- `Flask-Limiter==3.5.0` - Rate limiting
- `Flask-Talisman==1.1.0` - Security headers
- `marshmallow==3.20.1` - Input validation
- `rq-dashboard==0.6.1` - Job monitoring

---

## Testing

```bash
# Run all tests
make test

# Test specific features
pytest tests/test_database_integration.py -v

# Check code quality
make lint
```

---

## Configuration Summary

### Enable All Features

Add to your app startup:

```python
# Logging (enabled by default)
from logging_config import setup_logging
logger = setup_logging(app)

# Security headers (enabled by default)
from security_headers import configure_security_headers
configure_security_headers(app)

# Rate limiting (uncomment to enable)
from rate_limiting import setup_rate_limiting
limiter = setup_rate_limiting(app)

# RQ Dashboard (uncomment to enable)
from rq_dashboard_setup import setup_rq_dashboard
setup_rq_dashboard(app)
```

---

## Rollout Strategy

### Phase 1: Monitoring (Safe)
1. ✅ Logging infrastructure
2. ✅ Health check endpoint
3. ✅ Environment configuration

### Phase 2: Security (Low Risk)
4. ✅ Security headers
5. ✅ Input validation

### Phase 3: Infrastructure (Test First)
6. ⚠️ Database migrations (test in dev)
7. ⚠️ Rate limiting (monitor false positives)
8. ⚠️ RQ Dashboard (admin only)

---

## Monitoring

### Check Logs

```bash
# View application logs
tail -f instance/logs/panel.log

# View errors only
tail -f instance/logs/panel_errors.log

# View security audit
tail -f instance/audit_logs/security_audit.log
```

### Check Health

```bash
curl http://localhost:8080/health
```

### Monitor Jobs

Visit `http://localhost:8080/rq` (requires admin login)

---

## Troubleshooting

### Issue: Logging not working
**Solution**: Check `LOG_LEVEL` and `LOG_DIR` in environment or config

### Issue: Rate limiting too aggressive
**Solution**: Adjust limits in `rate_limiting.py` or disable temporarily

### Issue: Migration failed
**Solution**: `make db-downgrade` then fix and retry

### Issue: Health check returns 503
**Solution**: Check database and Redis connections

---

## Next Steps

1. Review `.env.example` and create your `.env` file
2. Enable logging (already enabled)
3. Test health check endpoint
4. Optionally enable rate limiting
5. Configure security headers for your CSP needs
6. Set up database migrations for future schema changes

---

## Documentation Links

- [Database Management](DATABASE_MANAGEMENT.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Main README](../README.md)
