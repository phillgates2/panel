"""
Performance Monitoring and APM Integration
Application Performance Monitoring with New Relic and custom metrics
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

import psutil
from flask import Flask, g, request


class PerformanceMonitor:
    """Application Performance Monitoring"""

    def __init__(self, app: Flask):
        self.app = app
        self.metrics = {
            "requests": [],
            "response_times": [],
            "errors": [],
            "memory_usage": [],
            "cpu_usage": [],
            "database_queries": [],
            "cache_hits": [],
            "cache_misses": [],
        }
        self.monitoring_thread = None
        self.monitoring_active = False

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        # Register Flask hooks
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)

        self.app.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        self.app.logger.info("Performance monitoring stopped")

    def _monitor_system_resources(self):
        """Monitor system resources in background"""
        while self.monitoring_active:
            try:
                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics["memory_usage"].append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "percentage": memory.percent,
                        "used_mb": memory.used / 1024 / 1024,
                        "available_mb": memory.available / 1024 / 1024,
                    }
                )

                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics["cpu_usage"].append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "percentage": cpu_percent,
                    }
                )

                # Keep only last 1000 entries to prevent memory issues
                for metric_list in self.metrics.values():
                    if len(metric_list) > 1000:
                        metric_list[:] = metric_list[-1000:]

            except Exception as e:
                self.app.logger.error(f"Resource monitoring error: {e}")

            time.sleep(10)  # Monitor every 10 seconds

    def _before_request(self):
        """Hook called before each request"""
        g.start_time = time.time()
        g.request_metrics = {
            "method": request.method,
            "endpoint": request.endpoint,
            "path": request.path,
            "user_agent": request.headers.get("User-Agent", ""),
            "ip": request.remote_addr,
        }

    def _after_request(self, response):
        """Hook called after each request"""
        if hasattr(g, "start_time"):
            response_time = (
                time.time() - g.start_time
            ) * 1000  # Convert to milliseconds

            content_length = 0
            try:
                if getattr(response, "direct_passthrough", False):
                    content_length = int(getattr(response, "content_length", 0) or 0)
                else:
                    data = response.get_data()
                    content_length = len(data) if data else 0
            except Exception:
                # Best-effort: never let monitoring break request handling.
                try:
                    content_length = int(getattr(response, "content_length", 0) or 0)
                except Exception:
                    content_length = 0

            request_metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": g.request_metrics["method"],
                "endpoint": g.request_metrics["endpoint"],
                "path": g.request_metrics["path"],
                "status_code": response.status_code,
                "response_time": response_time,
                "content_length": content_length,
                "user_agent": g.request_metrics["user_agent"],
                "ip": g.request_metrics["ip"],
            }

            self.metrics["requests"].append(request_metric)
            self.metrics["response_times"].append(response_time)

            # Log slow requests
            if response_time > 1000:  # More than 1 second
                self.app.logger.warning(
                    f"Slow request: {request.method} {request.path} - {response_time:.2f}ms"
                )

            # Log errors
            if response.status_code >= 400:
                error_metric = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status_code": response.status_code,
                    "method": g.request_metrics["method"],
                    "path": g.request_metrics["path"],
                    "error_message": getattr(response, "error_message", ""),
                    "ip": g.request_metrics["ip"],
                }
                self.metrics["errors"].append(error_metric)

        return response

    def _teardown_request(self, exception):
        """Hook called when request is torn down"""
        if exception:
            error_metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "exception": str(exception),
                "exception_type": type(exception).__name__,
                "path": getattr(g, "request_metrics", {}).get("path", "unknown"),
                "method": getattr(g, "request_metrics", {}).get("method", "unknown"),
            }
            self.metrics["errors"].append(error_metric)

    def record_database_query(self, query, execution_time):
        """Record database query metrics"""
        self.metrics["database_queries"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "query": (
                    query[:200] + "..." if len(query) > 200 else query
                ),  # Truncate long queries
                "execution_time": execution_time,
            }
        )

    def record_cache_operation(self, operation, hit=True):
        """Record cache operation metrics"""
        if hit:
            self.metrics["cache_hits"].append(
                {"timestamp": datetime.utcnow().isoformat(), "operation": operation}
            )
        else:
            self.metrics["cache_misses"].append(
                {"timestamp": datetime.utcnow().isoformat(), "operation": operation}
            )

    def get_metrics_summary(self):
        """Get summary of performance metrics"""
        summary = {
            "total_requests": len(self.metrics["requests"]),
            "total_errors": len(self.metrics["errors"]),
            "avg_response_time": 0,
            "95th_percentile_response_time": 0,
            "99th_percentile_response_time": 0,
            "error_rate": 0,
            "memory_usage_avg": 0,
            "cpu_usage_avg": 0,
            "cache_hit_rate": 0,
        }

        # Calculate response time statistics
        if self.metrics["response_times"]:
            response_times = sorted(self.metrics["response_times"])
            summary["avg_response_time"] = sum(response_times) / len(response_times)
            summary["95th_percentile_response_time"] = response_times[
                int(len(response_times) * 0.95)
            ]
            summary["99th_percentile_response_time"] = response_times[
                int(len(response_times) * 0.99)
            ]

        # Calculate error rate
        if summary["total_requests"] > 0:
            summary["error_rate"] = summary["total_errors"] / summary["total_requests"]

        # Calculate resource usage
        if self.metrics["memory_usage"]:
            memory_usage = [m["percentage"] for m in self.metrics["memory_usage"]]
            summary["memory_usage_avg"] = sum(memory_usage) / len(memory_usage)

        if self.metrics["cpu_usage"]:
            cpu_usage = [c["percentage"] for c in self.metrics["cpu_usage"]]
            summary["cpu_usage_avg"] = sum(cpu_usage) / len(cpu_usage)

        # Calculate cache hit rate
        total_cache_ops = len(self.metrics["cache_hits"]) + len(
            self.metrics["cache_misses"]
        )
        if total_cache_ops > 0:
            summary["cache_hit_rate"] = (
                len(self.metrics["cache_hits"]) / total_cache_ops
            )

        return summary

    def get_recent_metrics(self, minutes=5):
        """Get metrics from the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        recent_metrics = {
            "requests": [],
            "errors": [],
            "response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
        }

        for metric_list in ["requests", "errors"]:
            recent_metrics[metric_list] = [
                m
                for m in self.metrics[metric_list]
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]

        # Response times are stored separately
        recent_metrics["response_times"] = [
            rt
            for rt in self.metrics["response_times"]
            if rt > 0  # Only include actual response times
        ][
            :100
        ]  # Limit to last 100

        for metric_list in ["memory_usage", "cpu_usage"]:
            recent_metrics[metric_list] = [
                m
                for m in self.metrics[metric_list]
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]

        return recent_metrics


# New Relic integration
class NewRelicMonitor:
    """New Relic APM integration"""

    def __init__(self, app: Flask):
        self.app = app
        self.api_key = app.config.get("NEW_RELIC_API_KEY")
        self.app_name = app.config.get("NEW_RELIC_APP_NAME", "Panel Application")

        if self.api_key:
            self._setup_new_relic()

    def _setup_new_relic(self):
        """Setup New Relic monitoring"""
        try:
            import newrelic.agent

            # Initialize New Relic
            newrelic.agent.initialize(
                config_file=None, environment="production", ignore_errors=False
            )

            # Set application name
            newrelic.agent.register_application(name=self.app_name, timeout=10.0)

            self.app.logger.info("New Relic monitoring initialized")

        except ImportError:
            self.app.logger.warning("New Relic package not installed")
        except Exception as e:
            self.app.logger.error(f"New Relic setup failed: {e}")

    def record_custom_metric(self, name, value, tags=None):
        """Record custom metric"""
        if not self.api_key:
            return

        try:
            import newrelic.agent

            newrelic.agent.record_custom_metric(name, value, tags or {})
        except:
            pass

    def record_custom_event(self, event_type, params):
        """Record custom event"""
        if not self.api_key:
            return

        try:
            import newrelic.agent

            newrelic.agent.record_custom_event(event_type, params)
        except:
            pass


# DataDog integration
class DataDogMonitor:
    """DataDog APM integration"""

    def __init__(self, app: Flask):
        self.app = app
        self.api_key = app.config.get("DATADOG_API_KEY")
        self.app_key = app.config.get("DATADOG_APP_KEY")

        if self.api_key and self.app_key:
            self._setup_datadog()

    def _setup_datadog(self):
        """Setup DataDog monitoring"""
        try:
            from datadog import initialize, statsd

            initialize(
                api_key=self.api_key,
                app_key=self.app_key,
                statsd_host="localhost",
                statsd_port=8125,
            )

            self.app.logger.info("DataDog monitoring initialized")

        except ImportError:
            self.app.logger.warning("DataDog package not installed")
        except Exception as e:
            self.app.logger.error(f"DataDog setup failed: {e}")

    def increment_metric(self, metric_name, value=1, tags=None):
        """Increment metric"""
        if not self.api_key:
            return

        try:
            from datadog import statsd

            statsd.increment(metric_name, value, tags=tags or [])
        except:
            pass

    def gauge_metric(self, metric_name, value, tags=None):
        """Record gauge metric"""
        if not self.api_key:
            return

        try:
            from datadog import statsd

            statsd.gauge(metric_name, value, tags=tags or [])
        except:
            pass


# Performance monitoring decorators
def monitor_performance(name=None):
    """Decorator to monitor function performance"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000

                # Record metric
                metric_name = name or f"{func.__module__}.{func.__name__}"
                performance_monitor.record_custom_metric(
                    f"Custom/Function/{metric_name}", execution_time
                )

                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                # Record error metric
                performance_monitor.record_custom_metric(
                    f"Custom/Error/{func.__module__}.{func.__name__}", execution_time
                )
                raise

        return wrapper

    return decorator


def monitor_database_query():
    """Decorator to monitor database queries"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000

                # Record database query metric
                performance_monitor.record_database_query(
                    str(args) if args else "query", execution_time
                )

                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                performance_monitor.record_database_query(
                    f"ERROR: {str(e)}", execution_time
                )
                raise

        return wrapper

    return decorator


# Global instances
performance_monitor = None
new_relic_monitor = None
datadog_monitor = None


def init_performance_monitoring(app: Flask):
    """Initialize performance monitoring"""
    global performance_monitor, new_relic_monitor, datadog_monitor

    # Initialize custom performance monitor
    performance_monitor = PerformanceMonitor(app)
    performance_monitor.start_monitoring()

    # Initialize APM integrations
    new_relic_monitor = NewRelicMonitor(app)
    datadog_monitor = DataDogMonitor(app)

    # Add performance monitoring routes
    _add_monitoring_routes(app)

    app.logger.info("Performance monitoring initialized")


def _add_monitoring_routes(app: Flask):
    """Add monitoring routes"""

    @app.route("/api/monitoring/metrics")
    def get_metrics():
        """Get current performance metrics"""
        if not performance_monitor:
            return {"error": "Monitoring not initialized"}, 503

        return {
            "summary": performance_monitor.get_metrics_summary(),
            "recent": performance_monitor.get_recent_metrics(minutes=5),
        }

    @app.route("/api/monitoring/health")
    def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }

    @app.route("/api/monitoring/system")
    def system_info():
        """Get system information"""
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "network_connections": len(psutil.net_connections()),
                "load_average": (
                    psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
                ),
            }
        except Exception as e:
            return {"error": str(e)}, 500


# Export for external use
__all__ = [
    "PerformanceMonitor",
    "NewRelicMonitor",
    "DataDogMonitor",
    "monitor_performance",
    "monitor_database_query",
    "init_performance_monitoring",
]
