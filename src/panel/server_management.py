"""
Server Management with RCON Integration
Provides game server control and monitoring via RCON protocol
"""

import json
from typing import Dict, Any, Optional, List

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from src.panel import db
from src.panel.models import Server, User

server_bp = Blueprint("server", __name__, url_prefix="/servers")


@server_bp.context_processor
def inject_csrf_token():
    """Inject csrf_token function into server templates"""
    return {"csrf_token": lambda: session.get("csrf_token", "")}


def get_current_user():
    """Get the currently logged-in user"""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def can_manage_server(user: User, server: Server) -> bool:
    """Check if user can manage a specific server"""
    if user.is_system_admin():
        return True
    if server.owner_id == user.id:
        return True
    # Check server-specific roles
    from src.panel.models import ServerUser
    server_user = ServerUser.query.filter_by(
        server_id=server.id, user_id=user.id
    ).first()
    if server_user and server_user.role in ["server_admin", "server_mod"]:
        return True
    return False


@server_bp.route("/")
def index():
    """Server management dashboard"""
    user = get_current_user()
    if not user:
        flash("Login required", "error")
        return redirect(url_for("login"))

    # Get servers user can access
    if user.is_system_admin():
        servers = Server.query.all()
    else:
        # Servers where user is owner or has server role
        from src.panel.models import ServerUser
        owned_servers = Server.query.filter_by(owner_id=user.id).all()
        role_servers = Server.query.join(ServerUser).filter(
            ServerUser.user_id == user.id
        ).all()
        servers = list(set(owned_servers + role_servers))

    return render_template("servers/index.html", servers=servers, user=user)


@server_bp.route("/<int:server_id>")
def view(server_id):
    """View server details and controls"""
    user = get_current_user()
    if not user:
        flash("Login required", "error")
        return redirect(url_for("login"))

    server = db.session.get(Server, server_id)
    if not server or not can_manage_server(user, server):
        flash("Access denied", "error")
        return redirect(url_for("server.index"))

    return render_template("servers/view.html", server=server, user=user)


@server_bp.route("/<int:server_id>/rcon", methods=["GET", "POST"])
def rcon_console(server_id):
    """RCON console for server management"""
    user = get_current_user()
    if not user:
        flash("Login required", "error")
        return redirect(url_for("login"))

    server = db.session.get(Server, server_id)
    if not server or not can_manage_server(user, server):
        flash("Access denied", "error")
        return redirect(url_for("server.index"))

    if request.method == "POST":
        command = request.form.get("command", "").strip()
        if command:
            try:
                result = execute_rcon_command(server, command)
                # Log the command
                from src.panel.structured_logging import log_security_event
                log_security_event(
                    "rcon_command",
                    f"Executed RCON command on server {server.name}",
                    user.id,
                    request.remote_addr,
                    command=command[:100]  # Truncate for logging
                )
                flash(f"Command executed: {result}", "success")
            except Exception as e:
                flash(f"RCON error: {str(e)}", "error")
        return redirect(url_for("server.rcon_console", server_id=server_id))

    # Get command history for this server
    from src.panel.models_extended import RconCommandHistory
    history = RconCommandHistory.query.filter_by(server_id=server_id).order_by(
        RconCommandHistory.executed_at.desc()
    ).limit(20).all()

    return render_template("servers/rcon.html", server=server, history=history, user=user)


@server_bp.route("/<int:server_id>/rcon/execute", methods=["POST"])
def execute_rcon(server_id):
    """Execute RCON command via AJAX"""
    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}, 401

    server = db.session.get(Server, server_id)
    if not server or not can_manage_server(user, server):
        return {"error": "Access denied"}, 403

    command = request.json.get("command", "").strip()
    if not command:
        return {"error": "Command required"}, 400

    try:
        result = execute_rcon_command(server, command)

        # Store in history
        from src.panel.models_extended import RconCommandHistory
        history = RconCommandHistory(
            server_id=server_id,
            user_id=user.id,
            command=command,
            result=result[:1000]  # Truncate result
        )
        db.session.add(history)
        db.session.commit()

        # Log security event
        from src.panel.structured_logging import log_security_event
        log_security_event(
            "rcon_command",
            f"Executed RCON command on server {server.name}",
            user.id,
            request.remote_addr,
            command=command[:100]
        )

        return {"result": result}

    except Exception as e:
        return {"error": str(e)}, 500


def execute_rcon_command(server: Server, command: str) -> str:
    """Execute RCON command on server"""
    try:
        from src.panel.rcon_client import ETLegacyRcon

        # Get server connection details
        host = server.host or "127.0.0.1"
        port = server.port or 27960
        password = server.rcon_password

        if not password:
            raise Exception("RCON password not configured for this server")

        # Create RCON client
        rcon = ETLegacyRcon(host, port, password)

        # Execute command
        result = rcon.send_command(command)

        # Log command execution
        from src.panel.structured_logging import get_performance_logger
        perf_logger = get_performance_logger()
        perf_logger.info(
            "RCON command executed",
            extra={
                "server_id": server.id,
                "server_name": server.name,
                "command": command[:100],
                "result_length": len(result)
            }
        )

        return result

    except Exception as e:
        # Log error
        from src.panel.structured_logging import get_performance_logger
        perf_logger = get_performance_logger()
        perf_logger.error(
            "RCON command failed",
            extra={
                "server_id": server.id,
                "server_name": server.name,
                "command": command[:100],
                "error": str(e)
            }
        )
        raise


@server_bp.route("/<int:server_id>/status")
def server_status(server_id):
    """Get server status via RCON"""
    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}, 401

    server = db.session.get(Server, server_id)
    if not server or not can_manage_server(user, server):
        return {"error": "Access denied"}, 403

    try:
        # Get basic server info
        status = execute_rcon_command(server, "status")

        # Parse status (basic parsing for ET:Legacy)
        lines = status.split('\n')
        players = []
        map_name = "unknown"
        player_count = 0

        for line in lines:
            if line.startswith('map:'):
                map_name = line.split(':')[1].strip()
            elif line.startswith('players:'):
                player_count = int(line.split(':')[1].strip())
            elif len(line.split()) >= 5 and not line.startswith(('map:', 'players:', '----')):
                # Player line: score ping name
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        score = int(parts[0])
                        ping = int(parts[1])
                        name = ' '.join(parts[2:])
                        players.append({
                            "name": name,
                            "score": score,
                            "ping": ping
                        })
                    except ValueError:
                        continue

        return {
            "server_name": server.name,
            "map": map_name,
            "player_count": player_count,
            "max_players": 32,  # Default for ET
            "players": players[:10],  # Limit for API response
            "status": "online"
        }

    except Exception as e:
        return {
            "server_name": server.name,
            "status": "offline",
            "error": str(e)
        }


@server_bp.route("/<int:server_id>/players")
def server_players(server_id):
    """Get detailed player information"""
    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}, 401

    server = db.session.get(Server, server_id)
    if not server or not can_manage_server(user, server):
        return {"error": "Access denied"}, 403

    try:
        # Get player dump
        dump = execute_rcon_command(server, "dumpuser")

        # Parse player dump (simplified)
        lines = dump.split('\n')
        players = []

        for line in lines:
            if 'name:' in line and 'guid:' in line:
                # Parse player info
                parts = line.split()
                player_info = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        player_info[key] = value

                if 'name' in player_info:
                    players.append(player_info)

        return {
            "server_name": server.name,
            "players": players
        }

    except Exception as e:
        return {
            "server_name": server.name,
            "error": str(e),
            "players": []
        }


# Register the blueprint
def init_server_management(app):
    """Initialize server management blueprint"""
    app.register_blueprint(server_bp)
    app.logger.info("Server management with RCON integration initialized")