"""
Enhanced structured logging configuration for Panel
Provides correlation IDs, performance monitoring, and comprehensive observability
"""

import json
import logging
import os
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, g, request


class StructuredJSONFormatter(logging.Formatter):
    """Enhanced JSON log formatter with structured data"""

    def format(self, record: logging.LogRecord) -> str:
        # Get correlation ID from record or flask g
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id is None and hasattr(g, "correlation_id"):
            correlation_id = g.correlation_id

        # Build structured log record
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        if correlation_id:
            log_record["correlation_id"] = correlation_id

        # Add request context if available
        if hasattr(g, "request_id"):
            log_record["request_id"] = g.request_id
        if hasattr(g, "user_id"):
            log_record["user_id"] = g.user_id

        # Add exception info
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields from record
        if hasattr(record, "__dict__"):
            extra = {k: v for k, v in record.__dict__.items()
                     if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                                  'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                                  'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                                  'thread', 'threadName', 'processName', 'process', 'message',
                                  'correlation_id']}
            if extra:
                log_record["extra"] = extra

        return json.dumps(log_record, default=str, ensure_ascii=False)


class PerformanceMiddleware:
    """Middleware for performance monitoring and request timing"""

    def __init__(self, app: Flask):
        self.app = app
        self.performance_threshold = float(os.environ.get("PERFORMANCE_THRESHOLD", "500"))
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Record request start time and generate request ID"""
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]

    def after_request(self, response):
        """Log request performance and add timing headers"""
        if hasattr(g, "start_time"):
            duration = time.time() - g.start_time
            duration_ms = round(duration * 1000, 2)

            # Add timing header
            response.headers['X-Response-Time'] = f"{duration_ms}ms"

            # Log slow requests
            if duration_ms > self.performance_threshold:
                self.app.logger.warning(
                    "Slow request detected",
                    extra={
                        "duration_ms": duration_ms,
                        "endpoint": getattr(request, "endpoint", "unknown"),
                        "method": request.method,
                        "status_code": response.status_code,
                        "path": request.path,
                        "user_agent": request.headers.get("User-Agent", ""),
                        "ip_address": request.remote_addr,
                        "request_id": getattr(g, "request_id", None)
                    }
                )

            # Log all requests in debug mode
            elif self.app.logger.isEnabledFor(logging.DEBUG):
                self.app.logger.debug(
                    "Request completed",
                    extra={
                        "duration_ms": duration_ms,
                        "endpoint": getattr(request, "endpoint", "unknown"),
                        "method": request.method,
                        "status_code": response.status_code,
                        "request_id": getattr(g, "request_id", None)
                    }
                )

        return response


class CorrelationIdMiddleware:
    """Middleware for correlation ID management"""

    def __init__(self, app: Flask):
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Generate or extract correlation ID"""
        # Check for correlation ID in headers
        correlation_id = (
            request.headers.get("X-Correlation-ID") or
            request.headers.get("x-correlation-id") or
            str(uuid.uuid4())
        )
        g.correlation_id = correlation_id

    def after_request(self, response):
        """Add correlation ID to response headers"""
        if hasattr(g, "correlation_id"):
            response.headers["X-Correlation-ID"] = g.correlation_id
        return response


def setup_structured_logging(app: Flask) -> logging.Logger:
    """Configure comprehensive structured logging for the Flask application"""

    # Get configuration from environment
    log_level_name = os.environ.get("LOG_LEVEL", app.config.get("LOG_LEVEL", "INFO"))
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    log_format = os.environ.get("LOG_FORMAT", "json").lower()

    # Create logs directory
    log_dir = Path(app.config.get("LOG_DIR", "instance/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure app logger
    app.logger.setLevel(log_level)
    app.logger.handlers.clear()

    # Choose formatter
    if log_format == "json":
        formatter = StructuredJSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # File handler - rotates daily
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "panel.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Error file handler
    error_handler = RotatingFileHandler(
        filename=log_dir / "panel_errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)

    # Security audit log handler
    if app.config.get("AUDIT_LOG_ENABLED", True):
        audit_dir = Path(app.config.get("AUDIT_LOG_DIR", "instance/audit_logs"))
        audit_dir.mkdir(parents=True, exist_ok=True)

        audit_handler = TimedRotatingFileHandler(
            filename=audit_dir / "security_audit.log",
            when="midnight",
            interval=1,
            backupCount=365,
            encoding="utf-8",
        )
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            "%(asctime)s [AUDIT] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        audit_handler.setFormatter(audit_formatter)

        # Create separate logger for audit events
        audit_logger = logging.getLogger("panel.audit")
        audit_logger.setLevel(logging.INFO)
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False

    # Performance logger
    performance_handler = RotatingFileHandler(
        filename=log_dir / "panel_performance.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding="utf-8",
    )
    performance_handler.setLevel(logging.INFO)
    performance_handler.setFormatter(formatter)

    performance_logger = logging.getLogger("panel.performance")
    performance_logger.setLevel(logging.INFO)
    performance_logger.addHandler(performance_handler)
    performance_logger.propagate = False

    # Set SQLAlchemy logging level
    if not app.config.get("SQLALCHEMY_ECHO", False):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Werkzeug logging
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.INFO if app.debug else logging.WARNING)

    # Add correlation ID to log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        try:
            record.correlation_id = getattr(g, "correlation_id", None)
        except (RuntimeError, ImportError):
            record.correlation_id = None
        return record

    logging.setLogRecordFactory(record_factory)

    # Initialize middleware
    CorrelationIdMiddleware(app)
    PerformanceMiddleware(app)

    app.logger.info(
        "Structured logging configured successfully",
        extra={
            "log_level": log_level_name,
            "log_format": log_format,
            "log_directory": str(log_dir),
            "correlation_ids_enabled": True,
            "performance_monitoring_enabled": True
        }
    )

    return app.logger


def get_audit_logger() -> logging.Logger:
    """Get the security audit logger"""
    return logging.getLogger("panel.audit")


def get_performance_logger() -> logging.Logger:
    """Get the performance logger"""
    return logging.getLogger("panel.performance")


def log_security_event(
    event_type: str,
    message: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
) -> None:
    """Log a security event to the audit log"""
    audit_logger = get_audit_logger()

    details = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        **kwargs,
    }

    log_message = f"{message} | {' | '.join(f'{k}={v}' for k, v in details.items() if v is not None)}"
    audit_logger.info(log_message)


def log_performance_metric(
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs
) -> None:
    """Log a performance metric"""
    performance_logger = get_performance_logger()

    extra = {
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        **kwargs
    }

    if success:
        performance_logger.info(f"Performance metric: {operation}", extra=extra)
    else:
        performance_logger.warning(f"Performance metric (failed): {operation}", extra=extra)


def get_request_logger() -> logging.Logger:
    """Get a logger configured for request-specific logging"""
    logger = logging.getLogger("panel.request")
    if not logger.handlers:
        # Configure request logger if not already configured
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredJSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger