"""
Prometheus Monitoring Configuration

This module configures Prometheus metrics collection and Grafana dashboard integration.
"""

import os
from typing import Dict, Any

from flask import Flask, Response, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


def init_prometheus_metrics(app: Flask) -> Dict[str, Any]:
    """Initialize Prometheus metrics for the Flask application.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary containing metric collectors.
    """
    # Request metrics
    request_count = Counter(
        'flask_requests_total',
        'Total number of requests',
        ['method', 'endpoint', 'status']
    )

    request_duration = Histogram(
        'flask_request_duration_seconds',
        'Request duration in seconds',
        ['method', 'endpoint']
    )

    # User metrics
    active_users = Gauge(
        'panel_active_users',
        'Number of currently active users'
    )

    registered_users = Gauge(
        'panel_registered_users_total',
        'Total number of registered users'
    )

    # Server metrics
    active_servers = Gauge(
        'panel_active_servers',
        'Number of currently active game servers'
    )

    server_players = Gauge(
        'panel_server_players',
        'Number of players across all servers',
        ['server_id']
    )

    # Database metrics
    db_connections = Gauge(
        'panel_db_connections_active',
        'Number of active database connections'
    )

    db_query_duration = Histogram(
        'panel_db_query_duration_seconds',
        'Database query duration',
        ['query_type']
    )

    # Cache metrics
    cache_hits = Counter(
        'panel_cache_hits_total',
        'Total number of cache hits'
    )

    cache_misses = Counter(
        'panel_cache_misses_total',
        'Total number of cache misses'
    )

    # Error metrics
    error_count = Counter(
        'panel_errors_total',
        'Total number of errors',
        ['error_type', 'endpoint']
    )

    # Business metrics
    donations_total = Counter(
        'panel_donations_total',
        'Total number of donations'
    )

    forum_posts = Counter(
        'panel_forum_posts_total',
        'Total number of forum posts'
    )

    # Store metrics in app for access by other modules
    app.metrics = {
        'request_count': request_count,
        'request_duration': request_duration,
        'active_users': active_users,
        'registered_users': registered_users,
        'active_servers': active_servers,
        'server_players': server_players,
        'db_connections': db_connections,
        'db_query_duration': db_query_duration,
        'cache_hits': cache_hits,
        'cache_misses': cache_misses,
        'error_count': error_count,
        'donations_total': donations_total,
        'forum_posts': forum_posts,
    }

    # Add Prometheus metrics endpoint.
    # Keep /metrics reserved for the auth-protected endpoint in src.panel.metrics.
    @app.route('/metrics/prometheus')
    def metrics_prometheus():
        """Expose Prometheus metrics (unauthenticated)."""
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    # Middleware to collect request metrics
    @app.before_request
    def before_request():
        """Collect request start time."""
        import time
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        """Collect request metrics."""
        import time

        # Calculate request duration
        duration = time.time() - getattr(request, 'start_time', time.time())
        request_duration.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)

        # Count requests
        request_count.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()

        # Count errors
        if response.status_code >= 400:
            error_count.labels(
                error_type=str(response.status_code),
                endpoint=request.endpoint or 'unknown'
            ).inc()

        return response

    # Update metrics periodically
    def update_metrics():
        """Update gauge metrics periodically."""
        try:
            # Update user count
            from src.panel.models import User
            registered_users.set(User.query.count())

            # Update server count
            from src.panel.models import Server
            active_servers.set(Server.query.count())

            # Update database connections (if available)
            # This would depend on your database connection pool

        except Exception:
            # Don't let metrics updates break the app
            pass

    # Update metrics on startup
    update_metrics()

    return app.metrics


def create_grafana_dashboard() -> Dict[str, Any]:
    """Create a Grafana dashboard configuration for Panel metrics.

    Returns:
        Grafana dashboard JSON configuration.
    """
    dashboard = {
        "dashboard": {
            "title": "Panel Application Dashboard",
            "tags": ["panel", "flask", "monitoring"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Request Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(flask_requests_total[5m])",
                            "legendFormat": "{{method}} {{endpoint}}"
                        }
                    ]
                },
                {
                    "title": "Response Time",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(flask_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "95th percentile"
                        }
                    ]
                },
                {
                    "title": "Active Users",
                    "type": "singlestat",
                    "targets": [
                        {
                            "expr": "panel_active_users",
                            "legendFormat": "Active Users"
                        }
                    ]
                },
                {
                    "title": "Error Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(panel_errors_total[5m])",
                            "legendFormat": "{{error_type}}"
                        }
                    ]
                }
            ],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "refresh": "30s"
        }
    }

    return dashboard


def init_grafana_integration(app: Flask) -> None:
    """Initialize Grafana integration.

    Args:
        app: The Flask application instance.
    """
    grafana_url = os.environ.get('GRAFANA_URL')
    if grafana_url:
        app.config['GRAFANA_URL'] = grafana_url

        @app.route('/monitoring/grafana')
        def grafana_redirect():
            """Redirect to Grafana dashboard."""
            return redirect(f"{grafana_url}/d/panel-dashboard")


def create_prometheus_config() -> str:
    """Create a Prometheus configuration for scraping Panel metrics.

    Returns:
        Prometheus configuration YAML content.
    """
    config = f"""
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'panel'
    static_configs:
      - targets: ['localhost:{os.environ.get("PANEL_PORT", "5000")}']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'panel-database'
    static_configs:
      - targets: ['localhost:5432']
    scrape_interval: 30s
"""

    return config