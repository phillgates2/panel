"""
Prometheus Metrics Collection
Implements basic application metrics for monitoring and observability
"""

import os
import time
from typing import Optional

import psutil
from flask import Flask, Response, g, session
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)


class MetricsCollector:
    """Collects and exposes Prometheus metrics for the application"""

    def __init__(self, app: Optional[Flask] = None):
        self.app = app

        # HTTP request metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )

        # Database metrics
        self.db_connections_active = Gauge(
            "db_connections_active", "Number of active database connections"
        )

        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["query_type"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            "cache_hits_total", "Total number of cache hits"
        )

        self.cache_misses_total = Counter(
            "cache_misses_total", "Total number of cache misses"
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            "system_cpu_usage_percent", "Current system CPU usage percentage"
        )

        self.system_memory_usage = Gauge(
            "system_memory_usage_bytes", "Current system memory usage in bytes"
        )

        self.system_disk_usage = Gauge(
            "system_disk_usage_bytes",
            "Current system disk usage in bytes",
            ["mount_point"],
        )

        # Application metrics
        self.active_users = Gauge("active_users", "Number of currently active users")

        self.registered_users_total = Gauge(
            "registered_users_total", "Total number of registered users"
        )

        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize metrics collection for Flask app"""
        self.app = app

        # Register request metrics middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)

        # Add metrics endpoint
        app.add_url_rule("/metrics", "metrics", self.metrics_endpoint)

        # Start background metrics collection
        self.start_background_collection()

    def before_request(self) -> None:
        """Record request start time"""
        g.request_start_time = time.time()

    def after_request(self, response):
        """Record request metrics"""
        if hasattr(g, "request_start_time"):
            duration = time.time() - g.request_start_time

            # Get endpoint info
            endpoint = getattr(g, "endpoint", "unknown")
            method = getattr(g, "method", "GET")

            # Record metrics
            self.http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=response.status_code
            ).inc()

            self.http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

        return response

    def metrics_endpoint(self) -> Response:
        """Expose Prometheus metrics endpoint (requires session auth)"""
        try:
            # Require a logged-in user for metrics per tests
            if not session.get("user_id"):
                return Response("Authentication required", status=401, mimetype="text/plain")
        except Exception:
            return Response("Authentication required", status=401, mimetype="text/plain")

        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    def start_background_collection(self) -> None:
        """Start background collection of system metrics"""
        import threading
        import time

        def collect_system_metrics():
            while True:
                try:
                    # CPU usage
                    self.system_cpu_usage.set(psutil.cpu_percent(interval=1))

                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.system_memory_usage.set(memory.used)

                    # Disk usage
                    for partition in psutil.disk_partitions():
                        if os.path.exists(partition.mountpoint):
                            try:
                                usage = psutil.disk_usage(partition.mountpoint)
                                self.system_disk_usage.labels(
                                    mount_point=partition.mountpoint
                                ).set(usage.used)
                            except Exception:
                                pass

                    # Application metrics
                    self.update_application_metrics()

                except Exception as e:
                    if self.app:
                        self.app.logger.warning(f"Error collecting system metrics: {e}")

                time.sleep(60)  # Collect every minute

        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()

    def update_application_metrics(self) -> None:
        """Update application-specific metrics"""
        if not self.app:
            return

        try:
            from src.panel import db
            from src.panel.models import User

            with self.app.app_context():
                # Database connection count (approximate)
                # This is a simple gauge, actual connection pooling metrics would be better
                self.db_connections_active.set(1)  # Placeholder

                # User counts
                total_users = User.query.count()
                self.registered_users_total.set(total_users)

                # Active users (rough estimate: users who logged in recently)
                from datetime import datetime, timedelta, timezone

                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                active_users = User.query.filter(
                    User.last_login >= recent_cutoff
                ).count()
                self.active_users.set(active_users)

        except Exception as e:
            if self.app:
                self.app.logger.warning(f"Error updating application metrics: {e}")

    def record_db_query(self, query_type: str, duration: float) -> None:
        """Record database query metrics"""
        self.db_query_duration_seconds.labels(query_type=query_type).observe(duration)

    def record_cache_hit(self) -> None:
        """Record cache hit"""
        self.cache_hits_total.inc()

    def record_cache_miss(self) -> None:
        """Record cache miss"""
        self.cache_misses_total.inc()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector


def init_metrics(app: Flask) -> None:
    """Initialize Prometheus metrics for the Flask application"""
    metrics_collector.init_app(app)
    app.logger.info("Prometheus metrics collection initialized")
