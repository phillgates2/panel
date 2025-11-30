"""API Versioning Implementation

Provides backward-compatible API versions for the panel application.
Supports v1 (legacy) and v2 (enhanced) APIs.
"""

from flask import Blueprint, jsonify, request
from models import Server, User
from sqlalchemy import desc

from app import db

# API v1 - Legacy compatibility
api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# API v2 - Enhanced features
api_v2 = Blueprint("api_v2", __name__, url_prefix="/api/v2")


# ===== API v1 (Legacy) =====


@api_v1.route("/servers")
def get_servers_v1():
    """Legacy server listing API."""
    from flask import session

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Legacy format - simple list
    servers = []
    for server in user.servers:
        servers.append(
            {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "host": server.host,
                "port": server.port,
                "created_at": (
                    server.created_at.isoformat() if server.created_at else None
                ),
            }
        )

    return jsonify({"servers": servers})


@api_v1.route("/servers/<int:server_id>")
def get_server_v1(server_id):
    """Legacy single server API."""
    from flask import session

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    server = db.session.get(Server, server_id)

    if not server or server.user_id != user.id:
        return jsonify({"error": "Server not found"}), 404

    return jsonify(
        {
            "id": server.id,
            "name": server.name,
            "status": server.status,
            "host": server.host,
            "port": server.port,
            "created_at": server.created_at.isoformat() if server.created_at else None,
        }
    )


@api_v1.route("/health")
def health_v1():
    """Legacy health check."""
    return jsonify({"status": "healthy", "version": "v1"})


# ===== API v2 (Enhanced) =====


@api_v2.route("/servers")
def get_servers_v2():
    """Enhanced server listing with pagination and filtering."""
    from flask import session

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Enhanced features
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status_filter = request.args.get("status")
    search = request.args.get("search")

    query = Server.query.filter_by(user_id=user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(Server.name.ilike(f"%{search}%"))

    servers_query = query.order_by(desc(Server.created_at))
    servers_paginated = servers_query.paginate(page=page, per_page=per_page)

    servers = []
    for server in servers_paginated.items:
        # Enhanced server data with metrics
        server_data = {
            "id": server.id,
            "name": server.name,
            "status": server.status,
            "host": server.host,
            "port": server.port,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "updated_at": server.updated_at.isoformat() if server.updated_at else None,
            "connection_info": {
                "rcon_password_set": bool(server.rcon_password),
                "last_connection": None,  # Would be populated from metrics
            },
        }

        # Add latest metrics if available
        try:
            from monitoring_system import ServerMetrics

            latest_metric = (
                ServerMetrics.query.filter_by(server_id=server.id)
                .order_by(desc(ServerMetrics.timestamp))
                .first()
            )
            if latest_metric:
                server_data["metrics"] = {
                    "cpu_usage": latest_metric.cpu_usage,
                    "memory_usage": latest_metric.memory_usage,
                    "player_count": latest_metric.player_count,
                    "timestamp": latest_metric.timestamp.isoformat(),
                }
        except:
            pass

        servers.append(server_data)

    return jsonify(
        {
            "servers": servers,
            "pagination": {
                "page": servers_paginated.page,
                "per_page": servers_paginated.per_page,
                "total": servers_paginated.total,
                "pages": servers_paginated.pages,
                "has_next": servers_paginated.has_next,
                "has_prev": servers_paginated.has_prev,
            },
            "filters": {"status": status_filter, "search": search},
        }
    )


@api_v2.route("/servers/<int:server_id>")
def get_server_v2(server_id):
    """Enhanced single server API with detailed metrics."""
    from flask import session

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    server = db.session.get(Server, server_id)

    if not server or server.user_id != user.id:
        return jsonify({"error": "Server not found"}), 404

    server_data = {
        "id": server.id,
        "name": server.name,
        "status": server.status,
        "host": server.host,
        "port": server.port,
        "created_at": server.created_at.isoformat() if server.created_at else None,
        "updated_at": server.updated_at.isoformat() if server.updated_at else None,
        "connection_info": {
            "rcon_available": bool(server.rcon_password),
            "connection_status": "unknown",  # Would be checked via health check
        },
        "permissions": {
            "can_edit": user_can_edit_server(user, server),
            "can_delete": user_can_edit_server(user, server),
            "can_restart": user.is_system_admin() or user_can_edit_server(user, server),
        },
    }

    # Add comprehensive metrics
    try:
        from monitoring_system import ServerMetrics

        metrics = (
            ServerMetrics.query.filter_by(server_id=server.id)
            .order_by(desc(ServerMetrics.timestamp))
            .limit(10)
            .all()
        )

        if metrics:
            server_data["metrics"] = {
                "current": {
                    "cpu_usage": metrics[0].cpu_usage,
                    "memory_usage": metrics[0].memory_usage,
                    "disk_usage": metrics[0].disk_usage,
                    "network_rx": metrics[0].network_rx,
                    "network_tx": metrics[0].network_tx,
                    "player_count": metrics[0].player_count,
                    "timestamp": metrics[0].timestamp.isoformat(),
                },
                "history": [
                    {
                        "cpu_usage": m.cpu_usage,
                        "memory_usage": m.memory_usage,
                        "player_count": m.player_count,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in metrics[1:]
                ],
            }
    except:
        pass

    return jsonify(server_data)


@api_v2.route("/servers/<int:server_id>/metrics")
def get_server_metrics_v2(server_id):
    """Dedicated metrics endpoint for detailed monitoring."""
    from datetime import datetime, timedelta

    from flask import session

    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    server = db.session.get(Server, server_id)

    if not server or server.user_id != user.id:
        return jsonify({"error": "Server not found"}), 404

    # Time range parameters
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)  # 1 hour to 1 week

    since = datetime.utcnow() - timedelta(hours=hours)

    try:
        from monitoring_system import ServerMetrics

        metrics = (
            ServerMetrics.query.filter(
                ServerMetrics.server_id == server_id, ServerMetrics.timestamp >= since
            )
            .order_by(ServerMetrics.timestamp)
            .all()
        )

        return jsonify(
            {
                "server_id": server_id,
                "server_name": server.name,
                "time_range_hours": hours,
                "metrics": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "cpu_usage": m.cpu_usage,
                        "memory_usage": m.memory_usage,
                        "disk_usage": m.disk_usage,
                        "network_rx": m.network_rx,
                        "network_tx": m.network_tx,
                        "player_count": m.player_count,
                        "uptime": m.uptime,
                    }
                    for m in metrics
                ],
            }
        )
    except Exception as e:
        return jsonify({"error": f"Metrics unavailable: {str(e)}"}), 500


@api_v2.route("/health")
def health_v2():
    """Enhanced health check with system status."""
    try:
        # Check database
        db.session.execute(db.text("SELECT 1")).first()

        # Check Redis if available
        try:
            import redis

            redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
            r = redis.from_url(redis_url)
            r.ping()
            redis_status = "healthy"
        except:
            redis_status = "unavailable"

        return jsonify(
            {
                "status": "healthy",
                "version": "v2",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": "healthy",
                    "redis": redis_status,
                    "api": "healthy",
                },
                "uptime": getattr(app, "start_time", None),
            }
        )
    except Exception as e:
        return jsonify({"status": "unhealthy", "version": "v2", "error": str(e)}), 503


def user_can_edit_server(user, server):
    """Check if user can edit a server."""
    return server.user_id == user.id or user.is_system_admin()


def init_api_versioning(app):
    """Initialize API versioning."""
    app.register_blueprint(api_v1)
    app.register_blueprint(api_v2)

    # Add version headers to all API responses
    @app.after_request
    def add_version_header(response):
        if request.path.startswith("/api/"):
            if request.path.startswith("/api/v1/"):
                response.headers["API-Version"] = "v1"
            elif request.path.startswith("/api/v2/"):
                response.headers["API-Version"] = "v2"
        return response
