"""
Monitoring Extensions

This module initializes monitoring and metrics-related Flask extensions.
"""

import os
from typing import Any, Dict

from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

import sentry_sdk
from pythonjsonlogger import jsonlogger
import logging

from src.panel.backup_monitoring import init_backup_monitoring
from src.panel.backup_recovery import init_backup_system
from src.panel.health import init_health_checks
from src.panel.metrics import init_metrics
from src.panel.performance_monitoring import init_performance_monitoring
from app.prometheus_monitoring import (
    init_prometheus_metrics,
    init_grafana_integration,
)


def init_monitoring_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize monitoring and metrics-related Flask extensions.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary of initialized monitoring extension instances.
    """
    # Set up JSON logging for better observability
    json_formatter = jsonlogger.JsonFormatter()
    for handler in logging.getLogger().handlers:
        handler.setFormatter(json_formatter)

    # Initialize metrics collection
    init_metrics(app)

    # Initialize health check endpoints
    init_health_checks(app)

    # Initialize performance monitoring
    init_performance_monitoring(app)

    # Initialize Prometheus metrics
    metrics = init_prometheus_metrics(app)

    # Initialize Grafana integration
    init_grafana_integration(app)

    # Initialize backup and recovery system
    backup_manager = init_backup_system(app)

    # Initialize backup monitoring
    backup_monitor = init_backup_monitoring(app)

    # Initialize Sentry for error tracking
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[
            sentry_sdk.integrations.flask.FlaskIntegration(),
        ],
        traces_sample_rate=1.0,  # Sample 100% of transactions for performance monitoring
        environment=os.environ.get('FLASK_ENV', 'development'),
    )

    # Initialize metrics tracking
    app._request_count = 0
    app._error_count = 0

    @app.before_request
    def track_request_metrics():
        """Track request metrics for monitoring."""
        from flask import request
        if not request.path.startswith("/static/"):
            app._request_count += 1

    @app.after_request
    def track_error_metrics(response):
        """Track error metrics for monitoring."""
        if response.status_code >= 400:
            app._error_count += 1
        return response

    # Schedule periodic server status updates
    def schedule_server_status_updates():
        """Schedule periodic Discord server status updates."""
        from src.panel.tasks import send_server_status_task
        import time

        def status_update_loop():
            while True:
                try:
                    # Send status update every 5 minutes
                    send_server_status_task.delay()
                    time.sleep(300)  # 5 minutes
                except Exception as e:
                    print(f"Server status update scheduling error: {e}")
                    time.sleep(60)  # Retry in 1 minute on error

        # Start the status update loop in a background thread
        import threading
        status_thread = threading.Thread(target=status_update_loop, daemon=True)
        status_thread.start()

    # Start periodic status updates
    schedule_server_status_updates()

    # Configure monitoring settings
    monitoring_config = {
        'prometheus_enabled': True,
        'sentry_enabled': bool(os.environ.get("SENTRY_DSN")),
        'health_checks_enabled': True,
        'performance_monitoring_enabled': True,
        'backup_monitoring_enabled': True,
        'json_logging_enabled': True,
    }

    return {
        "metrics": metrics,
        "backup_manager": backup_manager,
        "backup_monitor": backup_monitor,
        "monitoring_config": monitoring_config,
    }