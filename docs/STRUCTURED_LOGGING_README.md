# Structured Logging Implementation

This document describes the structured logging implementation for the Panel application to improve observability and debugging capabilities.

## Overview

Structured logging provides:

1. **Correlation IDs** - Track requests across service boundaries
2. **Structured JSON logs** - Machine-readable log format
3. **Log levels and filtering** - Configurable verbosity
4. **Performance monitoring** - Request timing and metrics
5. **Error tracking** - Enhanced error context and stack traces

## Implementation Components

### 1. Enhanced Logging Configuration (`logging_config.py`)

The logging configuration has been enhanced with:

- JSON formatting for structured logs
- Correlation ID injection
- Request/response logging middleware
- Performance timing
- Error context capture

### 2. Correlation ID Middleware

A Flask middleware that:

- Generates unique correlation IDs for each request
- Injects correlation IDs into request context
- Adds correlation IDs to all log entries
- Propagates IDs to downstream services

### 3. Structured Log Formatter

Custom JSON formatter that:

- Includes timestamp, level, message, and context
- Adds correlation ID, request ID, and user info
- Captures exception details and stack traces
- Supports custom fields and metadata

### 4. Performance Logging

Request timing middleware that:

- Measures request duration
- Logs slow requests (>500ms)
- Tracks endpoint performance metrics
- Identifies performance bottlenecks

## Configuration

### Logging Levels

```python
LOGGING_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
```

### Structured Log Format

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "panel.app",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "req-12345",
  "user_id": "user-67890",
  "message": "User login successful",
  "module": "auth",
  "function": "login",
  "line": 156,
  "extra": {
    "endpoint": "/api/login",
    "method": "POST",
    "status_code": 200,
    "duration_ms": 245
  }
}
```

## Usage Examples

### Basic Logging

```python
from flask import current_app

# Info logging with context
current_app.logger.info("User authenticated", extra={
    'user_id': user.id,
    'endpoint': request.endpoint
})

# Error logging with exception
try:
    # Some operation
    pass
except Exception as e:
    current_app.logger.error("Operation failed", exc_info=True, extra={
        'error_code': 'OPERATION_FAILED',
        'user_id': user.id
    })
```

### Performance Logging

```python
import time

start_time = time.time()
# Some operation
duration = time.time() - start_time

current_app.logger.info("Operation completed", extra={
    'duration_ms': round(duration * 1000, 2),
    'operation': 'database_query'
})
```

### Request Context Logging

```python
from flask import g

# Access correlation ID
correlation_id = g.correlation_id

# Log with request context
current_app.logger.info("Processing request", extra={
    'correlation_id': correlation_id,
    'user_agent': request.headers.get('User-Agent'),
    'ip_address': request.remote_addr
})
```

## Middleware Implementation

### Correlation ID Middleware

```python
import uuid
from flask import g, request

class CorrelationIdMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        # Generate correlation ID if not provided
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        g.correlation_id = correlation_id

    def after_request(self, response):
        # Add correlation ID to response headers
        response.headers['X-Correlation-ID'] = g.correlation_id
        return response
```

### Performance Middleware

```python
import time
from flask import g, request, current_app

class PerformanceMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        g.start_time = time.time()

    def after_request(self, response):
        duration = time.time() - g.start_time
        duration_ms = round(duration * 1000, 2)

        # Log slow requests
        if duration_ms > 500:
            current_app.logger.warning("Slow request detected", extra={
                'duration_ms': duration_ms,
                'endpoint': request.endpoint,
                'method': request.method,
                'status_code': response.status_code
            })

        # Add timing header
        response.headers['X-Response-Time'] = f"{duration_ms}ms"
        return response
```

## Log Analysis

### Using jq for Log Analysis

```bash
# Filter errors
cat app.log | jq 'select(.level == "ERROR")'

# Find slow requests
cat app.log | jq 'select(.extra.duration_ms > 500)'

# Group by endpoint
cat app.log | jq -r '.extra.endpoint' | sort | uniq -c | sort -nr

# Search by correlation ID
cat app.log | jq "select(.correlation_id == \"550e8400-e29b-41d4-a716-446655440000\")"
```

### Log Aggregation with Loki

```yaml
# Promtail configuration for log shipping
scrape_configs:
  - job_name: panel
    static_configs:
      - targets:
          - localhost
        labels:
          job: panel
          __path__: /var/log/panel/*.log
```

## Integration with Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

# Request metrics
REQUEST_COUNT = Counter('panel_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('panel_request_duration_seconds', 'Request duration', ['method', 'endpoint'])

# Log metrics
LOG_COUNT = Counter('panel_logs_total', 'Total log entries', ['level', 'module'])
ERROR_COUNT = Counter('panel_errors_total', 'Total errors', ['error_type'])
```

### Grafana Dashboards

Create dashboards for:

- Request volume and latency
- Error rates by endpoint
- User activity patterns
- Performance bottlenecks
- Log volume trends

## Configuration Options

### Environment Variables

```bash
# Logging level
LOG_LEVEL=INFO

# Log format (json/text)
LOG_FORMAT=json

# Enable correlation IDs
ENABLE_CORRELATION_ID=true

# Performance logging threshold (ms)
PERFORMANCE_THRESHOLD=500

# Log file path
LOG_FILE=/var/log/panel/app.log

# Enable Loki shipping
ENABLE_LOKI=true
LOKI_URL=http://loki:3100
```

### Configuration File

```python
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'class': 'panel.logging.StructuredFormatter',
        },
        'text': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/panel/app.log',
            'formatter': 'json',
            'level': 'INFO'
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO'
    }
}
```

## Benefits

1. **Improved Debugging** - Correlation IDs track requests across services
2. **Better Monitoring** - Structured logs enable advanced analytics
3. **Performance Insights** - Request timing identifies bottlenecks
4. **Error Tracking** - Enhanced context for troubleshooting
5. **Compliance** - Audit trails and security event logging

## Next Steps

After implementing structured logging, continue with:

1. **Configuration Management** - Add schema validation for configuration
2. **Security Hardening** - Enhance CSP and security headers
3. **Monitoring Dashboard** - Implement Grafana integration