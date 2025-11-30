"""Request Tracing and Correlation IDs

Provides request ID tracing for better debugging and log correlation.
Automatically generates unique IDs for each request and includes them in logs.
"""

import uuid
from flask import g, request
from functools import wraps


class RequestTracer:
    """Request tracing and correlation ID management."""

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize request tracing with Flask app."""

        @app.before_request
        def add_request_id():
            """Add unique request ID to each request."""
            # Generate unique request ID
            request_id = str(uuid.uuid4())

            # Store in Flask g object for access throughout request
            g.request_id = request_id

            # Add to request headers for downstream services
            g.request_start_time = time.time()

        @app.after_request
        def add_request_id_header(response):
            """Add request ID to response headers."""
            if hasattr(g, "request_id"):
                response.headers["X-Request-ID"] = g.request_id

                # Add request duration
                if hasattr(g, "request_start_time"):
                    duration = time.time() - g.request_start_time
                    response.headers["X-Request-Duration"] = f"{duration:.3f}s"

            return response

        # Add request ID to application logger
        import logging
        import time

        class RequestIdFilter(logging.Filter):
            """Logging filter to add request ID to log records."""

            def filter(self, record):
                if hasattr(g, "request_id"):
                    record.request_id = g.request_id
                else:
                    record.request_id = "no-request-id"
                return True

        # Add filter to all handlers
        for handler in app.logger.handlers:
            handler.addFilter(RequestIdFilter())

        # Update log format to include request ID
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [RequestID: %(request_id)s] - %(message)s"
        )
        for handler in app.logger.handlers:
            handler.setFormatter(formatter)


# Global request tracer instance
request_tracer = RequestTracer()


def get_current_request_id():
    """Get the current request ID."""
    return getattr(g, "request_id", "no-request-id")


def log_with_request_id(logger, level, message, *args, **kwargs):
    """Log a message with request ID context."""
    request_id = get_current_request_id()
    enhanced_message = f"[RequestID: {request_id}] {message}"
    logger.log(level, enhanced_message, *args, **kwargs)


def traced_route(f):
    """Decorator to add tracing to route handlers."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time

        start_time = time.time()

        # Log request start
        from flask import current_app

        current_app.logger.info(f"Started {request.method} {request.path}")

        try:
            result = f(*args, **kwargs)

            # Log request completion
            duration = time.time() - start_time
            current_app.logger.info(f"Completed {request.method} {request.path} in {duration:.3f}s")

            return result

        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            current_app.logger.error(
                f"Failed {request.method} {request.path} in {duration:.3f}s: {str(e)}"
            )
            raise

    return decorated_function


def init_request_tracing(app):
    """Initialize request tracing for the application."""
    request_tracer.init_app(app)
