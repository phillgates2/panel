"""
Enhanced Monitoring Dashboard Implementation
Integrates Grafana, Prometheus, alerting, and comprehensive system monitoring
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import Blueprint, Response, jsonify, render_template, request

from simple_config import load_config

monitoring_dashboard_bp = Blueprint("monitoring_dashboard", __name__)


class MonitoringDashboard:
    """Enhanced monitoring dashboard with Grafana integration and alerting"""

    def __init__(self):
        self.config = load_config()
        self.alerts: List[Dict] = []
        self.metrics_cache = {}
        self.cache_timeout = 30  # seconds

    def get_system_metrics(self) -> Dict:
        """Get comprehensive system metrics"""
        current_time = time.time()

        # Check cache
        if "system" in self.metrics_cache:
            cache_time, cached_data = self.metrics_cache["system"]
            if current_time - cache_time < self.cache_timeout:
                return cached_data

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime": self._get_uptime(),
            "cpu": self._get_cpu_metrics(),
            "memory": self._get_memory_metrics(),
            "disk": self._get_disk_metrics(),
            "network": self._get_network_metrics(),
            "database": self._get_database_metrics(),
            "redis": self._get_redis_metrics(),
            "application": self._get_application_metrics(),
        }

        # Cache the results
        self.metrics_cache["system"] = (current_time, metrics)
        return metrics

    def _get_uptime(self) -> float:
        """Get system uptime"""
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.read().split()[0])
                return uptime_seconds
        except Exception:
            return 0.0

    def _get_cpu_metrics(self) -> Dict:
        """Get CPU usage metrics"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            return {
                "usage_percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else 0,
            }
        except Exception:
            return {"usage_percent": 0, "count": 0, "frequency_mhz": 0}

    def _get_memory_metrics(self) -> Dict:
        """Get memory usage metrics"""
        try:
            import psutil

            memory = psutil.virtual_memory()

            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.available / (1024**3), 2),
                "usage_percent": memory.percent,
            }
        except Exception:
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "usage_percent": 0}

    def _get_disk_metrics(self) -> Dict:
        """Get disk usage metrics"""
        try:
            import psutil

            disk = psutil.disk_usage("/")

            return {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": disk.percent,
            }
        except Exception:
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "usage_percent": 0}

    def _get_network_metrics(self) -> Dict:
        """Get network I/O metrics"""
        try:
            import psutil

            net_io = psutil.net_io_counters()

            return {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }
        except Exception:
            return {
                "bytes_sent_mb": 0,
                "bytes_recv_mb": 0,
                "packets_sent": 0,
                "packets_recv": 0,
            }

    def _get_database_metrics(self) -> Dict:
        """Get database connection metrics"""
        try:
            from app import db

            engine = db.engine

            # Get connection pool stats
            pool = engine.pool
            return {
                "pool_size": getattr(pool, "size", 0),
                "checked_out": getattr(pool, "checkedout", 0),
                "overflow": getattr(pool, "overflow", 0),
                "invalid": getattr(pool, "invalid", 0),
            }
        except Exception:
            return {"pool_size": 0, "checked_out": 0, "overflow": 0, "invalid": 0}

    def _get_redis_metrics(self) -> Dict:
        """Get Redis metrics"""
        try:
            import redis

            redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
            r = redis.from_url(redis_url)

            info = r.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / (1024**2), 2),
                "total_keys": r.dbsize(),
                "uptime_days": round(info.get("uptime_in_days", 0), 1),
            }
        except Exception:
            return {
                "connected_clients": 0,
                "used_memory_mb": 0,
                "total_keys": 0,
                "uptime_days": 0,
            }

    def _get_application_metrics(self) -> Dict:
        """Get application-specific metrics"""
        try:
            from app import Server, User, app

            return {
                "uptime_seconds": int(time.time() - app.start_time),
                "total_users": User.query.count(),
                "active_users": User.query.filter_by(is_active=True).count(),
                "total_servers": Server.query.count(),
                "request_count": getattr(app, "_request_count", 0),
                "error_count": getattr(app, "_error_count", 0),
            }
        except Exception:
            return {
                "uptime_seconds": 0,
                "total_users": 0,
                "active_users": 0,
                "total_servers": 0,
                "request_count": 0,
                "error_count": 0,
            }

    def get_prometheus_metrics(self) -> str:
        """Generate comprehensive Prometheus metrics"""
        metrics = self.get_system_metrics()

        prometheus_output = f"""# HELP panel_system_uptime_seconds System uptime in seconds
# TYPE panel_system_uptime_seconds gauge
panel_system_uptime_seconds {metrics['uptime']}

# HELP panel_cpu_usage_percent CPU usage percentage
# TYPE panel_cpu_usage_percent gauge
panel_cpu_usage_percent {metrics['cpu']['usage_percent']}

# HELP panel_memory_total_gb Total memory in GB
# TYPE panel_memory_total_gb gauge
panel_memory_total_gb {metrics['memory']['total_gb']}

# HELP panel_memory_used_gb Used memory in GB
# TYPE panel_memory_used_gb gauge
panel_memory_used_gb {metrics['memory']['used_gb']}

# HELP panel_memory_usage_percent Memory usage percentage
# TYPE panel_memory_usage_percent gauge
panel_memory_usage_percent {metrics['memory']['usage_percent']}

# HELP panel_disk_total_gb Total disk space in GB
# TYPE panel_disk_total_gb gauge
panel_disk_total_gb {metrics['disk']['total_gb']}

# HELP panel_disk_used_gb Used disk space in GB
# TYPE panel_disk_used_gb gauge
panel_disk_used_gb {metrics['disk']['used_gb']}

# HELP panel_disk_usage_percent Disk usage percentage
# TYPE panel_disk_usage_percent gauge
panel_disk_usage_percent {metrics['disk']['usage_percent']}

# HELP panel_network_bytes_sent_mb Network bytes sent in MB
# TYPE panel_network_bytes_sent_mb counter
panel_network_bytes_sent_mb {metrics['network']['bytes_sent_mb']}

# HELP panel_network_bytes_recv_mb Network bytes received in MB
# TYPE panel_network_bytes_recv_mb counter
panel_network_bytes_recv_mb {metrics['network']['bytes_recv_mb']}

# HELP panel_db_pool_size Database connection pool size
# TYPE panel_db_pool_size gauge
panel_db_pool_size {metrics['database']['pool_size']}

# HELP panel_db_connections_checked_out Checked out database connections
# TYPE panel_db_connections_checked_out gauge
panel_db_connections_checked_out {metrics['database']['checked_out']}

# HELP panel_redis_connected_clients Redis connected clients
# TYPE panel_redis_connected_clients gauge
panel_redis_connected_clients {metrics['redis']['connected_clients']}

# HELP panel_redis_used_memory_mb Redis used memory in MB
# TYPE panel_redis_used_memory_mb gauge
panel_redis_used_memory_mb {metrics['redis']['used_memory_mb']}

# HELP panel_app_uptime_seconds Application uptime in seconds
# TYPE panel_app_uptime_seconds gauge
panel_app_uptime_seconds {metrics['application']['uptime_seconds']}

# HELP panel_app_total_users Total number of users
# TYPE panel_app_total_users gauge
panel_app_total_users {metrics['application']['total_users']}

# HELP panel_app_active_users Number of active users
# TYPE panel_app_active_users gauge
panel_app_active_users {metrics['application']['active_users']}

# HELP panel_app_total_servers Total number of servers
# TYPE panel_app_total_servers gauge
panel_app_total_servers {metrics['application']['total_servers']}

# HELP panel_app_request_count Total request count
# TYPE panel_app_request_count counter
panel_app_request_count {metrics['application']['request_count']}

# HELP panel_app_error_count Total error count
# TYPE panel_app_error_count counter
panel_app_error_count {metrics['application']['error_count']}
"""

        return prometheus_output

    def check_alerts(self) -> List[Dict]:
        """Check for alert conditions and return active alerts"""
        alerts = []
        metrics = self.get_system_metrics()

        # CPU usage alert
        if metrics["cpu"]["usage_percent"] > 90:
            alerts.append(
                {
                    "type": "cpu_high",
                    "severity": "critical",
                    "message": f'CPU usage is {metrics["cpu"]["usage_percent"]:.1f}%',
                    "value": metrics["cpu"]["usage_percent"],
                    "threshold": 90,
                }
            )

        # Memory usage alert
        if metrics["memory"]["usage_percent"] > 90:
            alerts.append(
                {
                    "type": "memory_high",
                    "severity": "critical",
                    "message": f'Memory usage is {metrics["memory"]["usage_percent"]:.1f}%',
                    "value": metrics["memory"]["usage_percent"],
                    "threshold": 90,
                }
            )

        # Disk usage alert
        if metrics["disk"]["usage_percent"] > 95:
            alerts.append(
                {
                    "type": "disk_high",
                    "severity": "warning",
                    "message": f'Disk usage is {metrics["disk"]["usage_percent"]:.1f}%',
                    "value": metrics["disk"]["usage_percent"],
                    "threshold": 95,
                }
            )

        # Database connection pool alert
        if metrics["database"]["checked_out"] > metrics["database"]["pool_size"] * 0.8:
            alerts.append(
                {
                    "type": "db_connections_high",
                    "severity": "warning",
                    "message": f'Database connections: {metrics["database"]["checked_out"]}/{metrics["database"]["pool_size"]}',
                    "value": metrics["database"]["checked_out"],
                    "threshold": metrics["database"]["pool_size"] * 0.8,
                }
            )

        return alerts

    def get_grafana_dashboard_json(self) -> Dict:
        """Generate Grafana dashboard JSON configuration"""
        return {
            "dashboard": {
                "title": "Panel System Monitoring",
                "tags": ["panel", "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "title": "System CPU Usage",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "panel_cpu_usage_percent",
                                "legendFormat": "CPU Usage %",
                            }
                        ],
                    },
                    {
                        "title": "System Memory Usage",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "panel_memory_usage_percent",
                                "legendFormat": "Memory Usage %",
                            }
                        ],
                    },
                    {
                        "title": "Application Metrics",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "panel_app_total_users",
                                "legendFormat": "Total Users",
                            },
                            {
                                "expr": "panel_app_active_users",
                                "legendFormat": "Active Users",
                            },
                        ],
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            }
        }


# Global monitoring dashboard instance
monitoring_dashboard = MonitoringDashboard()


@monitoring_dashboard_bp.route("/admin/monitoring/enhanced")
def enhanced_monitoring_dashboard():
    """Enhanced monitoring dashboard with Grafana-style interface"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return redirect("/login")

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    # Get current metrics
    metrics = monitoring_dashboard.get_system_metrics()
    alerts = monitoring_dashboard.check_alerts()

    return render_template(
        "enhanced_monitoring_dashboard.html",
        metrics=metrics,
        alerts=alerts,
        title="Enhanced Monitoring Dashboard",
    )


@monitoring_dashboard_bp.route("/api/monitoring/metrics")
def api_monitoring_metrics():
    """API endpoint for monitoring metrics"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    metrics = monitoring_dashboard.get_system_metrics()
    return jsonify(metrics)


@monitoring_dashboard_bp.route("/api/monitoring/alerts")
def api_monitoring_alerts():
    """API endpoint for monitoring alerts"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    alerts = monitoring_dashboard.check_alerts()
    return jsonify({"alerts": alerts})


@monitoring_dashboard_bp.route("/metrics/enhanced")
def enhanced_prometheus_metrics():
    """Enhanced Prometheus metrics endpoint"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return Response("Authentication required", status=401, mimetype="text/plain")

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return Response("Admin access required", status=403, mimetype="text/plain")

    metrics = monitoring_dashboard.get_prometheus_metrics()
    return Response(metrics, mimetype="text/plain; charset=utf-8")


@monitoring_dashboard_bp.route("/api/monitoring/grafana/dashboard")
def grafana_dashboard_config():
    """Generate Grafana dashboard configuration"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    dashboard_config = monitoring_dashboard.get_grafana_dashboard_json()
    return jsonify(dashboard_config)


@monitoring_dashboard_bp.route("/admin/logs/aggregated")
def aggregated_logs_dashboard():
    """Aggregated logs dashboard for centralized logging"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return redirect("/login")

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    # Get log statistics
    try:
        from collections import defaultdict

        from app import AuditLog

        # Get logs from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        recent_logs = AuditLog.query.filter(AuditLog.created_at >= yesterday).all()

        # Aggregate by action type
        log_stats = defaultdict(int)
        for log in recent_logs:
            log_stats[log.action] += 1

        # Get error logs from structured logging
        error_logs = []
        # This would integrate with your logging system

        return render_template(
            "aggregated_logs_dashboard.html",
            log_stats=dict(log_stats),
            recent_logs=recent_logs[:50],  # Last 50 logs
            error_logs=error_logs,
            title="Aggregated Logs Dashboard",
        )

    except Exception as e:
        return render_template(
            "aggregated_logs_dashboard.html",
            error=str(e),
            title="Aggregated Logs Dashboard",
        )


@monitoring_dashboard_bp.route("/api/monitoring/logs/stats")
def api_logs_stats():
    """API endpoint for log statistics"""
    from flask import session

    from app import User, db

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        return jsonify({"error": "Admin access required"}), 403

    try:
        from collections import defaultdict

        from app import AuditLog

        # Get logs from different time periods
        now = datetime.now()
        periods = {
            "1h": now - timedelta(hours=1),
            "24h": now - timedelta(hours=24),
            "7d": now - timedelta(days=7),
        }

        stats = {}
        for period_name, period_start in periods.items():
            logs = AuditLog.query.filter(AuditLog.created_at >= period_start).all()

            period_stats = defaultdict(int)
            for log in logs:
                period_stats[log.action] += 1

            stats[period_name] = {
                "total_logs": len(logs),
                "action_breakdown": dict(period_stats),
            }

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def init_monitoring_dashboard(app):
    """Initialize the monitoring dashboard"""
    app.register_blueprint(monitoring_dashboard_bp)
    return monitoring_dashboard
