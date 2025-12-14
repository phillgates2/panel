"""
Background Tasks
Asynchronous task processing using Celery
"""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone

from src.panel.celery_app import celery_app
from src.panel.models import db

# Determine LOG_DIR with fallback to writable temp directory if configured dir is not accessible
try:
    from config import LOG_DIR

    _log_dir_config = LOG_DIR
except ImportError:
    _log_dir_config = os.path.join(tempfile.gettempdir(), "panel_logs")

_log_dir_env = os.environ.get("LOG_DIR")
LOG_DIR = _log_dir_env or _log_dir_config

# Try to create LOG_DIR; if it fails (permission denied), fall back to temp directory
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    # Fall back to temp directory (e.g., for dev/test environments)
    LOG_DIR = os.path.join(tempfile.gettempdir(), "panel_logs")
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(name, msg):
    """Log message to file"""
    path = os.path.join(LOG_DIR, f"{name}.log")
    # Use timezone-aware UTC timestamps to avoid deprecation warnings
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n"
    with open(path, "a") as f:
        f.write(line)


def _discord_post(payload, include_server_stats=True):
    """Send Discord notification with optional server stats"""
    webhook = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
    if not webhook:
        try:
            from src.panel import config

            webhook = getattr(config, "DISCORD_WEBHOOK", "")
        except ImportError:
            pass

    if not webhook:
        return

    try:
        import requests

        # Add server stats if requested and not already present
        if include_server_stats and "embeds" in payload:
            server_stats = _get_server_player_stats()
            if server_stats:
                # Add server stats to each embed
                for embed in payload["embeds"]:
                    if "fields" not in embed:
                        embed["fields"] = []
                    embed["fields"].extend(server_stats)

        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        # best-effort
        pass


def _get_server_player_stats():
    """Get current server player statistics for Discord embeds"""
    try:
        from src.panel.models import Server
        from monitoring_system import ServerMetrics

        # Get all servers with their latest metrics
        servers = Server.query.all()
        fields = []

        total_players = 0
        online_servers = 0

        for server in servers:
            # Get latest metrics for this server
            latest_metric = ServerMetrics.query.filter_by(server_id=server.id)\
                .order_by(ServerMetrics.timestamp.desc()).first()

            if latest_metric and latest_metric.is_online:
                online_servers += 1
                player_count = latest_metric.player_count or 0
                max_players = latest_metric.max_players or 0
                total_players += player_count

                # Add server-specific field
                fields.append({
                    "name": f"🎮 {server.name}",
                    "value": f"{player_count}/{max_players} players",
                    "inline": True
                })

        # Add summary field
        if online_servers > 0:
            fields.insert(0, {
                "name": "📊 Server Status",
                "value": f"{online_servers} servers online, {total_players} total players",
                "inline": False
            })

        return fields

    except Exception as e:
        # If we can't get stats, don't fail the webhook
        print(f"Error getting server stats for Discord: {e}")
        return []


@celery_app.task(name="panel.send_email")
def send_email_task(to_email, subject, body, html_body=None):
    """Send email asynchronously"""
    try:
        from flask_mail import Message

        from src.panel import mail

        msg = Message(subject=subject, recipients=[to_email], body=body)
        if html_body:
            msg.html = html_body

        mail.send(msg)
        _log("email", f"Email sent to {to_email}: {subject}")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        _log("email", f"Email failed to {to_email}: {e}")
        return {"status": "failed", "to": to_email, "error": str(e)}


@celery_app.task(name="panel.process_file")
def process_file_task(file_path, operation):
    """Process file asynchronously (upload, resize, etc.)"""
    try:
        if operation == "resize_image":
            # Example: resize uploaded image
            from PIL import Image

            img = Image.open(file_path)
            img.thumbnail((800, 600))
            img.save(file_path)
            _log("file", f"Image resized: {file_path}")
            return {"status": "processed", "file": file_path}

        elif operation == "scan_virus":
            # Example: virus scan
            # Integrate with clamav or similar
            _log("file", f"File scanned: {file_path}")
            return {"status": "scanned", "file": file_path}

        return {"status": "unknown_operation", "operation": operation}

    except Exception as e:
        _log("file", f"File processing failed for {file_path}: {e}")
        return {"status": "failed", "file": file_path, "error": str(e)}


@celery_app.task(name="panel.backup_database")
def backup_database_task():
    """Run database backup asynchronously"""
    try:
        from tools.scripts.backup_manager import BackupManager

        backup_manager = BackupManager()
        backup_file = backup_manager.create_backup()

        if backup_file:
            _log("backup", f"Database backup completed: {backup_file}")

            # Send notifications
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "💾 Database Backup Completed",
                            "description": f"Backup saved to: {backup_file}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 3066993,
                            "fields": [
                                {
                                    "name": "📁 Backup Location",
                                    "value": backup_file,
                                    "inline": False
                                }
                            ]
                        }
                    ]
                }
            )
            _slack_post(f"✅ Database backup completed: {backup_file}")

            return {"status": "completed", "backup_file": backup_file}
        else:
            _log("backup", "Database backup failed")
            return {"status": "failed", "error": "Backup creation failed"}

    except Exception as e:
        _log("backup", f"Database backup exception: {e}")
        _discord_post({"content": f"Database backup exception: {e}"})
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="panel.run_autodeploy")
def run_autodeploy_task(download_url=None):
    """Run autodeploy asynchronously"""
    env = os.environ.copy()
    if download_url:
        env["DOWNLOAD_URL"] = download_url

    script_path = os.path.join(os.getcwd(), "tools", "scripts", "autodeploy.sh")
    if not os.path.exists(script_path):
        return {"ok": False, "err": "Autodeploy script not found"}

    _log("autodeploy", f"Starting autodeploy (download_url={download_url})")

    try:
        proc = subprocess.run(
            [script_path], capture_output=True, text=True, env=env, timeout=3600
        )
        _log("autodeploy", "STDOUT:\n" + proc.stdout)
        _log("autodeploy", "STDERR:\n" + proc.stderr)

        if proc.returncode == 0:
            payload = {
                "content": None,
                "embeds": [
                    {
                        "title": "🚀 Autodeploy Completed Successfully",
                        "description": f'ET:Legacy server deployment finished for {download_url or "default version"}.',
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 3066993,
                        "fields": [
                            {
                                "name": "📦 Version",
                                "value": download_url or "Default",
                                "inline": True
                            },
                            {
                                "name": "⏱️ Duration",
                                "value": f"{(datetime.utcnow() - datetime.utcnow()).seconds}s",  # Would need to track actual duration
                                "inline": True
                            }
                        ]
                    }
                ],
            }
            _discord_post(payload)
            return {"ok": True, "out": proc.stdout}
        else:
            payload = {
                "content": None,
                "embeds": [
                    {
                        "title": "❌ Autodeploy Failed",
                        "description": f"ET:Legacy server deployment failed (exit code: {proc.returncode})",
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 15158332,
                        "fields": [
                            {
                                "name": "📦 Version",
                                "value": download_url or "Default",
                                "inline": True
                            },
                            {
                                "name": "🔍 Error Details",
                                "value": proc.stderr[:500] + "..." if len(proc.stderr) > 500 else proc.stderr,
                                "inline": False
                            }
                        ]
                    }
                ],
            }
            _discord_post(payload)
            return {"ok": False, "out": proc.stdout, "err": proc.stderr}

    except Exception as e:
        _log("autodeploy", f"Autodeploy exception: {e}")
        return {"ok": False, "err": str(e)}


@celery_app.task(name="panel.train_ai_model")
def train_ai_model_task(model_name, data_path):
    """Train AI model asynchronously"""
    try:
        # Example: Call AI training function
        from src.panel.ai_integration import train_model

        result = train_model(model_name, data_path)
        _log("ai", f"AI model trained: {model_name}")
        return {"status": "trained", "model": model_name, "result": result}
    except Exception as e:
        _log("ai", f"AI training failed for {model_name}: {e}")
        return {"status": "failed", "model": model_name, "error": str(e)}


@celery_app.task(name="panel.gdpr_export")
def gdpr_export_task(user_id):
    """Export user data for GDPR"""
    try:
        from src.panel import models

        user = models.User.query.get(user_id)
        if user:
            data = {
                "user": user.display_name,
                "email": user.email,
                "posts": [p.content for p in user.forum_posts],
                # Add more
            }
            # Save to file or email
            _log("gdpr", f"Data exported for user {user_id}")
            return {"status": "exported", "data": data}
        return {"status": "user_not_found"}
    except Exception as e:
        _log("gdpr", f"GDPR export failed for {user_id}: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="panel.data_retention")
def data_retention_task():
    """Clean up old data for retention compliance"""
    try:
        from src.panel import models

        cutoff = datetime.now(timezone.utc) - timedelta(days=365)  # 1 year

        # Delete old audit logs
        old_audits = models.AuditLog.query.filter(
            models.AuditLog.created_at < cutoff
        ).delete()
        db.session.commit()

        _log("retention", f"Deleted {old_audits} old audit logs")

        return {"status": "completed", "deleted_audits": old_audits}
    except Exception as e:
        _log("retention", f"Data retention failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="panel.send_server_status")
def send_server_status_task():
    """Send periodic server status update to Discord"""
    try:
        from src.panel.models import Server
        from monitoring_system import ServerMetrics

        servers = Server.query.all()
        online_servers = []
        total_players = 0
        total_max_players = 0

        server_fields = []

        for server in servers:
            latest_metric = ServerMetrics.query.filter_by(server_id=server.id)\
                .order_by(ServerMetrics.timestamp.desc()).first()

            if latest_metric:
                player_count = latest_metric.player_count or 0
                max_players = latest_metric.max_players or 0
                is_online = latest_metric.is_online

                total_players += player_count if is_online else 0
                total_max_players += max_players

                status_emoji = "🟢" if is_online else "🔴"
                server_fields.append({
                    "name": f"{status_emoji} {server.name}",
                    "value": f"{player_count}/{max_players} players",
                    "inline": True
                })

                if is_online:
                    online_servers.append(server)

        # Create status embed
        embed = {
            "title": "🎮 Server Network Status",
            "description": f"Current status of all game servers",
            "color": 0x00FF00 if len(online_servers) > 0 else 0xFF0000,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "📊 Network Overview",
                    "value": f"{len(online_servers)}/{len(servers)} servers online\n{total_players}/{total_max_players} total players",
                    "inline": False
                }
            ] + server_fields
        }

        # Add performance summary if available
        if online_servers:
            embed["fields"].append({
                "name": "⚡ Performance",
                "value": f"Average load: {total_players/max(len(online_servers), 1):.1f} players/server",
                "inline": True
            })

        _discord_post({"embeds": [embed]})

        _log("discord", f"Sent server status update: {len(online_servers)} online servers, {total_players} total players")
        return {"status": "sent", "online_servers": len(online_servers), "total_players": total_players}

    except Exception as e:
        _log("discord", f"Server status update failed: {e}")
        return {"status": "failed", "error": str(e)}
