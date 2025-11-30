"""
Health Check Endpoints
Provides comprehensive health monitoring for the application
"""

import os
import time
import psutil
from flask import Flask, jsonify, current_app
from typing import Dict, Any
from datetime import datetime, timezone


class HealthChecker:
    """Comprehensive health checker for the application"""

    def __init__(self, app: Flask):
        self.app = app
        self.start_time = time.time()

    def get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "version": "1.0.0",  # Would be dynamic in real implementation
        }

    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status including all components"""
        health_data = self.get_basic_health()

        # Database health
        health_data["database"] = self.check_database()

        # Redis/Cache health
        health_data["cache"] = self.check_cache()

        # File system health
        health_data["filesystem"] = self.check_filesystem()

        # System resources
        health_data["system"] = self.check_system_resources()

        # Application metrics
        health_data["application"] = self.check_application_metrics()

        # Overall status
        components = [
            health_data["database"],
            health_data["cache"],
            health_data["filesystem"],
            health_data["system"],
        ]
        if all(comp.get("status") == "healthy" for comp in components):
            health_data["status"] = "healthy"
        else:
            health_data["status"] = "degraded"

        return health_data

    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            from src.panel import db

            with self.app.app_context():
                # Test basic connectivity
                start_time = time.time()
                db.session.execute(text("SELECT 1"))
                db_time = time.time() - start_time

                # Get connection info
                connection_info = {
                    "status": "healthy",
                    "response_time_ms": round(db_time * 1000, 2),
                    "type": "postgresql" if "postgresql" in str(db.engine.url) else "sqlite",
                }

                # Additional checks for PostgreSQL
                if connection_info["type"] == "postgresql":
                    try:
                        result = db.session.execute(text("SELECT version()")).scalar()
                        connection_info["version"] = result.split()[1] if result else "unknown"
                    except Exception:
                        connection_info["version"] = "unknown"

                return connection_info

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_cache(self) -> Dict[str, Any]:
        """Check Redis/cache connectivity"""
        try:
            from flask_caching import Cache

            cache = self.app.extensions.get("cache")

            if cache:
                # Test cache operations
                test_key = "health_check_test"
                test_value = "ok"

                start_time = time.time()
                cache.set(test_key, test_value, timeout=10)
                retrieved = cache.get(test_key)
                cache_time = time.time() - start_time

                cache.delete(test_key)

                if retrieved == test_value:
                    return {
                        "status": "healthy",
                        "response_time_ms": round(cache_time * 1000, 2),
                        "type": "redis",
                    }
                else:
                    return {"status": "unhealthy", "error": "Cache read/write test failed"}
            else:
                return {"status": "unknown", "error": "Cache not configured"}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_filesystem(self) -> Dict[str, Any]:
        """Check filesystem health"""
        try:
            # Check critical directories
            critical_paths = [
                self.app.root_path,
                os.path.join(self.app.root_path, "instance"),
                os.path.join(self.app.root_path, "logs"),
            ]

            filesystem_status = {"status": "healthy", "paths": {}}

            for path in critical_paths:
                if os.path.exists(path):
                    try:
                        # Check write permissions
                        test_file = os.path.join(path, ".health_test")
                        with open(test_file, "w") as f:
                            f.write("test")
                        os.remove(test_file)

                        # Get disk usage
                        stat = os.statvfs(path) if hasattr(os, "statvfs") else None
                        if stat:
                            free_space = stat.f_bavail * stat.f_frsize
                            total_space = stat.f_blocks * stat.f_frsize
                            usage_percent = ((total_space - free_space) / total_space) * 100

                            filesystem_status["paths"][path] = {
                                "writable": True,
                                "free_space_gb": round(free_space / (1024**3), 2),
                                "usage_percent": round(usage_percent, 1),
                            }
                        else:
                            filesystem_status["paths"][path] = {
                                "writable": True,
                                "free_space_gb": "unknown",
                            }
                    except Exception as e:
                        filesystem_status["paths"][path] = {"writable": False, "error": str(e)}
                        filesystem_status["status"] = "degraded"
                else:
                    filesystem_status["paths"][path] = {"exists": False, "writable": False}
                    filesystem_status["status"] = "degraded"

            return filesystem_status

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = round(memory.used / (1024**3), 2)
            memory_total_gb = round(memory.total / (1024**3), 2)

            # Disk usage for application directory
            disk = psutil.disk_usage(self.app.root_path)
            disk_percent = disk.percent
            disk_free_gb = round(disk.free / (1024**3), 2)

            system_status = {
                "status": "healthy",
                "cpu": {"usage_percent": cpu_percent},
                "memory": {
                    "usage_percent": memory_percent,
                    "used_gb": memory_used_gb,
                    "total_gb": memory_total_gb,
                },
                "disk": {"usage_percent": disk_percent, "free_gb": disk_free_gb},
            }

            # Set status based on thresholds
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
                system_status["status"] = "warning"
            elif cpu_percent > 95 or memory_percent > 95 or disk_percent > 98:
                system_status["status"] = "critical"

            return system_status

        except Exception as e:
            return {"status": "unknown", "error": str(e)}

    def check_application_metrics(self) -> Dict[str, Any]:
        """Check application-specific metrics"""
        try:
            from src.panel import db
            from src.panel.models import User, Server

            with self.app.app_context():
                # User counts
                total_users = User.query.count()
                active_users = User.query.filter(
                    User.last_login
                    >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                ).count()

                # Server counts
                total_servers = Server.query.count()

                # Recent activity (last 24 hours)
                recent_logins = User.query.filter(
                    User.last_login
                    >= datetime.now(timezone.utc).replace(
                        hour=datetime.now(timezone.utc).hour - 24, minute=0, second=0, microsecond=0
                    )
                ).count()

                return {
                    "status": "healthy",
                    "metrics": {
                        "total_users": total_users,
                        "active_users_today": active_users,
                        "total_servers": total_servers,
                        "recent_logins_24h": recent_logins,
                    },
                }

        except Exception as e:
            return {"status": "unknown", "error": str(e)}


# Global health checker instance
health_checker = HealthChecker


def init_health_checks(app: Flask) -> None:
    """Initialize health check endpoints"""

    checker = HealthChecker(app)

    @app.route("/health")
    def health():
        """Basic health check endpoint"""
        return jsonify(checker.get_basic_health())

    @app.route("/health/detailed")
    def health_detailed():
        """Detailed health check endpoint"""
        return jsonify(checker.get_detailed_health())

    app.logger.info("Health check endpoints initialized")
