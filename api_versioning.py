"""API Versioning Implementation

Provides backward-compatible API versions for the panel application.
Supports v1 (legacy) and v2 (enhanced) APIs.
"""

import os
import re
import secrets
import smtplib
import time
from datetime import date, datetime
from email.message import EmailMessage
from urllib.parse import quote

import json

from flask import Blueprint, current_app, jsonify, request
from models import Notification, NotificationSubscription, Server, User
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, text

from app import db

# API v1 - Legacy compatibility
api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# API v2 - Enhanced features
api_v2 = Blueprint("api_v2", __name__, url_prefix="/api/v2")


def _get_authenticated_user_id():
    """Return a user id from either session auth or JWT bearer auth."""
    from flask import session

    uid = session.get("user_id")
    if uid is not None:
        try:
            return int(uid)
        except (TypeError, ValueError):
            return None

    # Support mobile/API clients using JWT from /auth/jwt/login
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

        verify_jwt_in_request(optional=True)
        jwt_uid = get_jwt_identity()
        if jwt_uid is not None:
            try:
                return int(jwt_uid)
            except (TypeError, ValueError):
                return None
    except Exception:
        return None

    return None


# ===== API v1 (Legacy) =====


@api_v1.route("/servers")
def get_servers_v1():
    """Legacy server listing API."""
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    servers_query = Server.query
    if not user.is_system_admin():
        servers_query = servers_query.filter(Server.owner_id == user.id)

    servers = []
    for server in servers_query.order_by(desc(Server.created_at)).all():
        servers.append(
            {
                "id": server.id,
                "name": server.name,
                "status": getattr(server, "status", None) or "unknown",
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
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    server = db.session.get(Server, server_id)

    if not server or (not user.is_system_admin() and server.owner_id != user.id):
        return jsonify({"error": "Server not found"}), 404

    return jsonify(
        {
            "id": server.id,
            "name": server.name,
            "status": getattr(server, "status", None) or "unknown",
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
    uid = _get_authenticated_user_id()
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

    query = Server.query
    if not user.is_system_admin():
        query = query.filter(Server.owner_id == user.id)

    if status_filter:
        # The core Server model doesn't currently persist status; keep filter for forward-compat.
        query = query.filter(text("1=1"))

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
            "status": getattr(server, "status", None) or "unknown",
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
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    server = db.session.get(Server, server_id)

    if not server or (not user.is_system_admin() and server.owner_id != user.id):
        return jsonify({"error": "Server not found"}), 404

    server_data = {
        "id": server.id,
        "name": server.name,
        "status": getattr(server, "status", None) or "unknown",
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
    from datetime import timedelta

    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    server = db.session.get(Server, server_id)

    if not server or (not user.is_system_admin() and server.owner_id != user.id):
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
        db.session.execute(text("SELECT 1")).first()

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
                "uptime": getattr(current_app, "start_time", None),
            }
        )
    except Exception as e:
        return jsonify({"status": "unhealthy", "version": "v2", "error": str(e)}), 503


def user_can_edit_server(user, server):
    """Check if user can edit a server."""
    return user.is_system_admin() or (getattr(server, "owner_id", None) == user.id)


# ===== API v2 (Mobile compatibility endpoints) =====


@api_v2.route("/servers", methods=["POST"])
def create_server_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not name:
        return jsonify({"error": "Missing required field: name"}), 400

    server = Server(
        name=name,
        description=payload.get("description"),
        host=payload.get("host"),
        port=payload.get("port"),
        rcon_password=payload.get("rcon_password") or payload.get("rconPassword"),
        game_type=payload.get("game_type") or payload.get("gameType") or "etlegacy",
        owner_id=user.id,
    )
    db.session.add(server)
    db.session.commit()

    return (
        jsonify(
            {
                "id": server.id,
                "name": server.name,
                "status": getattr(server, "status", None) or "unknown",
                "host": server.host,
                "port": server.port,
                "created_at": server.created_at.isoformat() if server.created_at else None,
            }
        ),
        201,
    )


@api_v2.route("/servers/<int:server_id>", methods=["PUT"])
def update_server_v2(server_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    server = db.session.get(Server, server_id)
    if not server or not user_can_edit_server(user, server):
        return jsonify({"error": "Server not found"}), 404

    payload = request.get_json(silent=True) or {}
    for key, attr in (
        ("name", "name"),
        ("description", "description"),
        ("host", "host"),
        ("port", "port"),
        ("rcon_password", "rcon_password"),
        ("rconPassword", "rcon_password"),
        ("game_type", "game_type"),
        ("gameType", "game_type"),
    ):
        if key in payload:
            setattr(server, attr, payload.get(key))

    db.session.commit()
    return jsonify({"success": True})


@api_v2.route("/servers/<int:server_id>", methods=["DELETE"])
def delete_server_v2(server_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    server = db.session.get(Server, server_id)
    if not server or not user_can_edit_server(user, server):
        return jsonify({"error": "Server not found"}), 404

    db.session.delete(server)
    db.session.commit()
    return jsonify({"success": True})


def _server_action_response(server, action: str):
    return jsonify(
        {
            "server_id": server.id,
            "action": action,
            "status": "accepted",
            "server_status": getattr(server, "status", None) or "unknown",
        }
    ), 202


@api_v2.route("/servers/<int:server_id>/start", methods=["POST"])
def start_server_v2(server_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    server = db.session.get(Server, server_id)
    if not server or not user_can_edit_server(user, server):
        return jsonify({"error": "Server not found"}), 404
    return _server_action_response(server, "start")


@api_v2.route("/servers/<int:server_id>/stop", methods=["POST"])
def stop_server_v2(server_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    server = db.session.get(Server, server_id)
    if not server or not user_can_edit_server(user, server):
        return jsonify({"error": "Server not found"}), 404
    return _server_action_response(server, "stop")


@api_v2.route("/servers/<int:server_id>/restart", methods=["POST"])
def restart_server_v2(server_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    server = db.session.get(Server, server_id)
    if not server or not user_can_edit_server(user, server):
        return jsonify({"error": "Server not found"}), 404
    return _server_action_response(server, "restart")


@api_v2.route("/notifications", methods=["GET"])
def get_notifications_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    notifications = (
        Notification.query.filter_by(user_id=uid, read=False)
        .order_by(desc(Notification.created_at))
        .limit(50)
        .all()
    )
    return jsonify(
        [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "read": n.read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    )


@api_v2.route("/notifications/<int:notif_id>/read", methods=["POST"])
def mark_notification_read_v2(notif_id):
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    notif = db.session.get(Notification, notif_id)
    if not notif or notif.user_id != uid:
        return jsonify({"error": "Notification not found"}), 404

    notif.read = True
    db.session.commit()
    return jsonify({"success": True})


@api_v2.route("/notifications/register", methods=["POST"])
def register_notification_device_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    payload = request.get_json(silent=True) or {}
    device_token = payload.get("deviceToken")
    platform = payload.get("platform")
    if not device_token or not platform:
        return jsonify({"error": "Missing deviceToken or platform"}), 400

    endpoint = f"mobile:{platform}:{device_token}"
    existing = NotificationSubscription.query.filter_by(
        user_id=uid, endpoint=endpoint
    ).first()
    subscription_data = json.dumps(
        {"deviceToken": device_token, "platform": platform}, sort_keys=True
    )

    if existing:
        existing.subscription_data = subscription_data
    else:
        db.session.add(
            NotificationSubscription(
                user_id=uid,
                endpoint=endpoint,
                subscription_data=subscription_data,
            )
        )
    db.session.commit()
    return jsonify({"success": True})


@api_v2.route("/user/profile", methods=["GET"])
def get_user_profile_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "bio": getattr(user, "bio", None),
            "avatar": getattr(user, "avatar", None),
            "role": getattr(user, "role", None),
        }
    )


@api_v2.route("/user/profile", methods=["PUT"])
def update_user_profile_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json(silent=True) or {}
    for key in ("first_name", "last_name", "bio", "avatar"):
        if key in payload and hasattr(user, key):
            setattr(user, key, payload.get(key))

    db.session.commit()
    return jsonify({"success": True})


@api_v2.route("/user/password", methods=["POST"])
def change_password_v2():
    uid = _get_authenticated_user_id()
    if not uid:
        return jsonify({"error": "Authentication required"}), 401

    user = db.session.get(User, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json(silent=True) or {}
    old_password = payload.get("oldPassword")
    new_password = payload.get("newPassword")
    if not old_password or not new_password:
        return jsonify({"error": "Missing oldPassword or newPassword"}), 400

    if not user.check_password(old_password):
        return jsonify({"error": "Invalid old password"}), 400

    try:
        user.set_password(new_password)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    db.session.commit()
    return jsonify({"success": True})


def _not_implemented(feature: str):
    return jsonify({"error": "Not implemented", "feature": feature}), 501


def _get_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_smtp_settings():
    cfg = current_app.config if current_app else {}
    host = cfg.get("MAIL_SERVER") or os.environ.get("SMTP_HOST")
    port = int(cfg.get("MAIL_PORT") or os.environ.get("SMTP_PORT") or 587)
    username = cfg.get("MAIL_USERNAME") or os.environ.get("SMTP_USERNAME")
    password = cfg.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD")
    use_tls = _get_bool(cfg.get("MAIL_USE_TLS", os.environ.get("SMTP_TLS")), True)
    use_ssl = _get_bool(cfg.get("MAIL_USE_SSL", os.environ.get("SMTP_SSL")), False)
    sender = (
        cfg.get("MAIL_DEFAULT_SENDER")
        or os.environ.get("SMTP_FROM")
        or username
        or "no-reply@panel.local"
    )

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "sender": sender,
    }


def _get_public_base_url() -> str:
    """Return externally-reachable base URL for links in emails.

    Prefer configuration/env because request.host_url may be internal
    behind proxies or different from the public hostname.
    """
    cfg = current_app.config if current_app else {}
    base = (
        cfg.get("PUBLIC_BASE_URL")
        or cfg.get("APP_PUBLIC_URL")
        or os.environ.get("PANEL_PUBLIC_BASE_URL")
        or os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("APP_PUBLIC_URL")
    )
    if base:
        return str(base).rstrip("/")

    return request.host_url.rstrip("/")


def _send_email_smtp(to_email: str, subject: str, body_text: str):
    settings = _get_smtp_settings()
    if not settings.get("host"):
        raise RuntimeError("SMTP not configured (MAIL_SERVER/SMTP_HOST missing)")

    msg = EmailMessage()
    msg["From"] = settings["sender"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_text)

    if settings["use_ssl"]:
        server = smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=15)
    else:
        server = smtplib.SMTP(settings["host"], settings["port"], timeout=15)

    try:
        server.ehlo()
        if settings["use_tls"] and not settings["use_ssl"]:
            server.starttls()
            server.ehlo()
        if settings.get("username") and settings.get("password"):
            server.login(settings["username"], settings["password"])
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def _new_email_verification_token() -> str:
    issued = int(time.time())
    code = secrets.token_hex(16)
    return f"verify:{issued}:{code}"


def _is_email_verification_token_valid(token: str, max_age_seconds: int = 7 * 24 * 3600) -> bool:
    try:
        prefix, issued_s, _code = token.split(":", 2)
        if prefix != "verify":
            return False
        issued = int(issued_s)
        return (int(time.time()) - issued) <= max_age_seconds
    except Exception:
        return False


def _verification_email_content(email: str, token: str) -> str:
    base = _get_public_base_url()
    link = f"{base}/api/v2/auth/verify-email?token={quote(token)}"
    # Use the code portion as a manual fallback.
    code = token.split(":", 2)[-1] if token else ""
    return (
        "Verify your Panel account\n\n"
        "To activate your account, use one of the options below:\n\n"
        f"1) Click this link: {link}\n\n"
        f"2) Or enter this verification code: {code}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )


@api_v2.route("/analytics/dashboard")
def analytics_dashboard_v2():
    return _not_implemented("analytics_dashboard")


@api_v2.route("/analytics/players")
def analytics_players_v2():
    return _not_implemented("analytics_players")


@api_v2.route("/auth/register", methods=["POST"])
def auth_register_v2():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    first_name = (data.get("first_name") or data.get("firstName") or "").strip()
    last_name = (data.get("last_name") or data.get("lastName") or "").strip()
    dob = (data.get("dob") or data.get("date_of_birth") or data.get("dateOfBirth"))

    missing = []
    if not email:
        missing.append("email")
    if not password:
        missing.append("password")
    if not first_name:
        missing.append("first_name")
    if not last_name:
        missing.append("last_name")
    if not dob:
        missing.append("dob")

    if missing:
        return (
            jsonify(
                {
                    "error": "Missing required fields",
                    "missing": missing,
                    "expected": {
                        "dob": "YYYY-MM-DD",
                    },
                }
            ),
            400,
        )

    # Basic email format check (lightweight, no external dependency)
    if len(email) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Invalid email address"}), 400

    # Age gate: require user to be 16+ based on provided DOB (DD-MM-YYYY)
    try:
        if isinstance(dob, str):
            dob_date = datetime.strptime(dob, "%d-%m-%Y").date()
        elif hasattr(dob, "year") and hasattr(dob, "month") and hasattr(dob, "day"):
            dob_date = date(dob.year, dob.month, dob.day)
        else:
            raise ValueError("Invalid dob")

        today = date.today()
        age = today.year - dob_date.year - (
            (today.month, today.day) < (dob_date.month, dob_date.day)
        )
        if age < 16:
            return (
                jsonify({"error": "You must be at least 16 years old to register"}),
                403,
            )
    except ValueError:
        return jsonify({"error": "Invalid dob format. Expected DD-MM-YYYY"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        dob=dob_date,
        is_active=False,
        role=data.get("role") or "user",
    )

    verification_token = _new_email_verification_token()
    user.reset_token = verification_token

    try:
        user.set_password(password)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email already registered"}), 409

    try:
        subject = "Verify your Panel account"
        body = _verification_email_content(user.email, verification_token)
        _send_email_smtp(user.email, subject, body)
    except Exception as e:
        # Keep the user record so they can request a resend.
        return (
            jsonify(
                {
                    "error": "Failed to send verification email",
                    "details": str(e),
                }
            ),
            502,
        )

    return (
        jsonify(
            {
                "message": "Verification email sent. Please verify to activate your account.",
                "email": user.email,
            }
        ),
        202,
    )


@api_v2.route("/auth/verify-email", methods=["GET", "POST"])
def verify_email_v2():
    token = request.args.get("token")
    if not token and request.is_json:
        token = (request.get_json(silent=True) or {}).get("token")

    if not token:
        return jsonify({"error": "Missing token"}), 400

    if not _is_email_verification_token_valid(token):
        return jsonify({"error": "Invalid or expired token"}), 400

    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return jsonify({"error": "Invalid token"}), 400

    user.is_active = True
    user.reset_token = None
    db.session.commit()

    return jsonify({"success": True, "email": user.email})


@api_v2.route("/auth/resend-verification", methods=["POST"])
def resend_verification_v2():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Missing email"}), 400

    user = User.query.filter_by(email=email).first()
    # Avoid leaking whether an email exists.
    if not user:
        return jsonify({"message": "If that account exists, a verification email was sent."}), 202

    if user.is_active:
        return jsonify({"message": "Account already verified."}), 200

    token = user.reset_token
    if not token or not _is_email_verification_token_valid(token):
        token = _new_email_verification_token()
        user.reset_token = token
        db.session.commit()

    try:
        subject = "Verify your Panel account"
        body = _verification_email_content(user.email, token)
        _send_email_smtp(user.email, subject, body)
    except Exception as e:
        return jsonify({"error": "Failed to send verification email", "details": str(e)}), 502

    return jsonify({"message": "If that account exists, a verification email was sent."}), 202


@api_v2.route("/plugins/search")
def plugins_search_v2():
    return _not_implemented("plugins_search")


@api_v2.route("/plugins/<plugin_id>")
def plugin_details_v2(plugin_id):
    return _not_implemented("plugin_details")


@api_v2.route("/plugins/<plugin_id>/install", methods=["POST"])
def plugin_install_v2(plugin_id):
    return _not_implemented("plugin_install")


@api_v2.route("/plugins/<plugin_id>/uninstall", methods=["POST"])
def plugin_uninstall_v2(plugin_id):
    return _not_implemented("plugin_uninstall")


@api_v2.route("/blockchain/wallet/balance")
def wallet_balance_v2():
    return _not_implemented("wallet_balance")


@api_v2.route("/blockchain/nfts")
def nfts_v2():
    return _not_implemented("nfts")


@api_v2.route("/blockchain/nfts/mint", methods=["POST"])
def mint_nft_v2():
    return _not_implemented("mint_nft")


@api_v2.route("/support/tickets", methods=["GET", "POST"])
def support_tickets_v2():
    return _not_implemented("support_tickets")


@api_v2.route("/support/kb/search")
def support_kb_search_v2():
    return _not_implemented("support_kb_search")


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
