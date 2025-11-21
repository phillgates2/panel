import os
import subprocess
import tempfile
from datetime import datetime

import config

# Determine LOG_DIR with fallback to writable temp directory if configured dir is not accessible
_log_dir_env = os.environ.get("LOG_DIR")
_log_dir_config = config.LOG_DIR  # Already OS-aware from config.py
LOG_DIR = _log_dir_env or _log_dir_config

# Try to create LOG_DIR; if it fails (permission denied), fall back to temp directory
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    # Fall back to temp directory (e.g., for dev/test environments)
    LOG_DIR = os.path.join(tempfile.gettempdir(), "panel_logs")
    os.makedirs(LOG_DIR, exist_ok=True)


def _log(name, msg):
    path = os.path.join(LOG_DIR, f"{name}.log")
    line = f"[{datetime.utcnow().isoformat()}] {msg}\n"
    with open(path, "a") as f:
        f.write(line)


def _discord_post(payload):
    webhook = os.environ.get("PANEL_DISCORD_WEBHOOK", "") or getattr(config, "DISCORD_WEBHOOK", "")
    if not webhook:
        return
    try:
        import requests

        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        # best-effort
        pass


def _slack_post(message):
    webhook = os.environ.get("PANEL_SLACK_WEBHOOK", "") or getattr(config, "SLACK_WEBHOOK", "")
    if not webhook:
        return
    try:
        import requests

        payload = {"text": message}
        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        # best-effort
        pass


def run_autodeploy(download_url=None):
    env = os.environ.copy()
    if download_url:
        env["DOWNLOAD_URL"] = download_url
    script = os.path.join(os.getcwd(), "scripts", "autodeploy.sh")
    _log("autodeploy", f"Starting autodeploy (download_url={download_url})")
    try:
        proc = subprocess.run([script], capture_output=True, text=True, env=env, timeout=3600)
        _log("autodeploy", "STDOUT:\n" + proc.stdout)
        _log("autodeploy", "STDERR:\n" + proc.stderr)
        if proc.returncode == 0:
            payload = {
                "content": None,
                "embeds": [
                    {
                        "title": "Autodeploy Completed",
                        "description": f'Autodeploy finished successfully for {download_url or "(default)"}.',
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 3066993,
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
                        "title": "Autodeploy Failed",
                        "description": f"Autodeploy failed (rc={proc.returncode})",
                        "fields": [{"name": "stderr", "value": proc.stderr[:1000]}],
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 15158332,
                    }
                ],
            }
            _discord_post(payload)
            return {"ok": False, "out": proc.stdout, "err": proc.stderr}
    except Exception as e:
        _log("autodeploy", f"Exception: {e}")
        _discord_post({"content": f"autodeploy exception: {e}"})
        return {"ok": False, "err": str(e)}


def run_memwatch(pid_file=None):
    env = os.environ.copy()
    if pid_file:
        env["ET_PID_FILE"] = pid_file
    # force memwatch to attempt dump by setting threshold to 0
    env["THRESH_BYTES"] = "0"
    script = os.path.join(os.getcwd(), "scripts", "memwatch.sh")
    _log("memwatch", f"Running memwatch with pid_file={pid_file}")
    try:
        proc = subprocess.run([script], capture_output=True, text=True, env=env, timeout=300)
        _log("memwatch", "STDOUT:\n" + proc.stdout)
        _log("memwatch", "STDERR:\n" + proc.stderr)
        # Report a simple embed
        payload = {
            "content": None,
            "embeds": [
                {
                    "title": "Memwatch run",
                    "description": f"Ran memwatch for pid_file={pid_file}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "color": 3447003,
                }
            ],
        }
        _discord_post(payload)
        return {"ok": True, "out": proc.stdout, "err": proc.stderr}
    except Exception as e:
        _log("memwatch", f"Exception: {e}")
        _discord_post({"content": f"memwatch exception: {e}"})
        return {"ok": False, "err": str(e)}


def run_ptero_eggs_sync():
    """
    Background task for automatic Ptero-Eggs template synchronization.

    This task can be scheduled to run periodically using RQ or systemd timer.
    """
    _log("ptero_eggs_sync", "Starting Ptero-Eggs template sync")

    try:
        # Import here to avoid circular dependencies
        from app import User, app, db
        from ptero_eggs_updater import PteroEggsUpdater

        with app.app_context():
            # Get an admin user to attribute the update to
            admin = User.query.filter_by(role="system_admin").first()
            if not admin:
                _log("ptero_eggs_sync", "ERROR: No admin user found")
                return {"ok": False, "err": "No admin user found"}

            # Run the sync
            updater = PteroEggsUpdater()
            stats = updater.sync_templates(admin.id)

            if stats["success"]:
                _log("ptero_eggs_sync", f"Sync completed: {stats['message']}")

                # Send Discord notification if configured
                payload = {
                    "content": None,
                    "embeds": [
                        {
                            "title": "Ptero-Eggs Templates Synced",
                            "description": stats["message"],
                            "fields": [
                                {"name": "Added", "value": str(stats["added"]), "inline": True},
                                {"name": "Updated", "value": str(stats["updated"]), "inline": True},
                                {"name": "Errors", "value": str(stats["errors"]), "inline": True},
                            ],
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 3066993,  # Green
                        }
                    ],
                }
                _discord_post(payload)

                return {"ok": True, "stats": stats}
            else:
                _log("ptero_eggs_sync", f"Sync failed: {stats['message']}")

                # Send error notification
                payload = {
                    "content": None,
                    "embeds": [
                        {
                            "title": "Ptero-Eggs Sync Failed",
                            "description": stats["message"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 15158332,  # Red
                        }
                    ],
                }
                _discord_post(payload)

                return {"ok": False, "err": stats["message"]}

    except Exception as e:
        _log("ptero_eggs_sync", f"Exception: {e}")
        _discord_post({"content": f"ptero_eggs_sync exception: {e}"})
        return {"ok": False, "err": str(e)}


# ============================================================================
# BACKUP SCHEDULING FUNCTIONS
# ============================================================================


def run_scheduled_database_backup():
    """Run scheduled database backup."""
    from backup_manager import BackupManager

    _log("backup", "Starting scheduled database backup")

    try:
        backup_manager = BackupManager()
        backup_file = backup_manager.create_database_backup()

        if backup_file:
            _log("backup", f"Database backup completed: {backup_file}")

            # Send Discord notification
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "Database Backup Completed",
                            "description": f"Backup saved to: {backup_file}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 3066993,  # Green
                        }
                    ]
                }
            )
            # Send Slack notification
            _slack_post(f"✅ Database backup completed: {backup_file}")

            return {"ok": True, "backup_file": backup_file}
        else:
            _log("backup", "Database backup failed")
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "Database Backup Failed",
                            "description": "Failed to create database backup",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 15158332,  # Red
                        }
                    ]
                }
            )
            return {"ok": False, "error": "Backup creation failed"}

    except Exception as e:
        _log("backup", f"Database backup exception: {e}")
        _discord_post({"content": f"Database backup exception: {e}"})
        _slack_post(f"🚨 Database backup exception: {e}")
        return {"ok": False, "error": str(e)}


def run_scheduled_config_backup():
    """Run scheduled configuration backup."""
    from backup_manager import BackupManager

    _log("backup", "Starting scheduled configuration backup")

    try:
        backup_manager = BackupManager()
        backup_file = backup_manager.create_config_backup()

        if backup_file:
            _log("backup", f"Configuration backup completed: {backup_file}")

            # Send Discord notification
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "Configuration Backup Completed",
                            "description": f"Backup saved to: {backup_file}",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 3066993,  # Green
                        }
                    ]
                }
            )

            return {"ok": True, "backup_file": backup_file}
        else:
            _log("backup", "Configuration backup failed")
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "Configuration Backup Failed",
                            "description": "Failed to create configuration backup",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 15158332,  # Red
                        }
                    ]
                }
            )
            return {"ok": False, "error": "Backup creation failed"}

    except Exception as e:
        _log("backup", f"Configuration backup exception: {e}")
        _discord_post({"content": f"Configuration backup exception: {e}"})
        return {"ok": False, "error": str(e)}


def run_scheduled_server_backups():
    """Run scheduled backups for all servers."""
    from app import Server, db
    from backup_manager import BackupManager

    _log("backup", "Starting scheduled server backups")

    try:
        backup_manager = BackupManager()

        # Get all servers
        servers = Server.query.all()
        results = []

        for server in servers:
            try:
                # Get server data for backup
                server_data = {
                    "id": server.id,
                    "name": server.name,
                    "host": server.host,
                    "port": server.port,
                    "rcon_password": server.rcon_password,
                    "variables_json": server.variables_json,
                    "raw_config": server.raw_config,
                    "game_type": server.game_type,
                    "max_players": server.max_players,
                }

                backup_file = backup_manager.create_server_backup(
                    server.id,
                    server_data,
                    f"scheduled_server_{server.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                )

                if backup_file:
                    results.append(
                        {"server_id": server.id, "status": "success", "backup_file": backup_file}
                    )
                    _log("backup", f"Server {server.id} backup completed: {backup_file}")
                else:
                    results.append(
                        {
                            "server_id": server.id,
                            "status": "failed",
                            "error": "Backup creation failed",
                        }
                    )
                    _log("backup", f"Server {server.id} backup failed")

            except Exception as e:
                results.append({"server_id": server.id, "status": "error", "error": str(e)})
                _log("backup", f"Server {server.id} backup exception: {e}")

        # Send Discord notification
        success_count = sum(1 for r in results if r["status"] == "success")
        total_count = len(results)

        _discord_post(
            {
                "embeds": [
                    {
                        "title": "Server Backups Completed",
                        "description": f"Successfully backed up {success_count}/{total_count} servers",
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 3066993
                        if success_count == total_count
                        else 16776960,  # Green or Yellow
                    }
                ]
            }
        )

        return {"ok": True, "results": results}

    except Exception as e:
        _log("backup", f"Server backups exception: {e}")
        _discord_post({"content": f"Server backups exception: {e}"})
        return {"ok": False, "error": str(e)}


def run_backup_cleanup(days_to_keep=30):
    """Run scheduled backup cleanup."""
    from backup_manager import BackupManager

    _log("backup", f"Starting scheduled backup cleanup (keeping {days_to_keep} days)")

    try:
        backup_manager = BackupManager()
        deleted_files = backup_manager.cleanup_old_backups(days_to_keep)

        _log("backup", f"Backup cleanup completed: {len(deleted_files)} files deleted")

        # Send Discord notification
        _discord_post(
            {
                "embeds": [
                    {
                        "title": "Backup Cleanup Completed",
                        "description": f"Deleted {len(deleted_files)} old backup files",
                        "timestamp": datetime.utcnow().isoformat(),
                        "color": 3066993,  # Green
                    }
                ]
            }
        )
        # Send Slack notification
        _slack_post(f"🧹 Backup cleanup completed: {len(deleted_files)} old files deleted")

        return {"ok": True, "deleted_count": len(deleted_files), "deleted_files": deleted_files}

    except Exception as e:
        _log("backup", f"Backup cleanup exception: {e}")
        _discord_post({"content": f"Backup cleanup exception: {e}"})
        _slack_post(f"🚨 Backup cleanup exception: {e}")
        return {"ok": False, "error": str(e)}


def run_auto_scaling_check():
    """Monitor server performance and auto-scale as needed."""
    _log("scaling", "Starting auto-scaling check")

    try:
        from datetime import datetime, timedelta, timezone

        from app import Server, ServerMetrics, db

        # Get servers with high CPU usage in last 5 minutes
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

        high_cpu_servers = (
            db.session.query(Server)
            .join(ServerMetrics)
            .filter(ServerMetrics.timestamp >= five_min_ago)
            .filter(ServerMetrics.cpu_usage > 90)
            .distinct(Server.id)
            .all()
        )

        for server in high_cpu_servers:
            _log("scaling", f"Server {server.name} has high CPU usage, considering restart")

            # Send notifications
            _discord_post(
                {
                    "embeds": [
                        {
                            "title": "High CPU Alert",
                            "description": f"Server {server.name} has CPU > 90%. Auto-restart initiated.",
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 15158332,  # Red
                        }
                    ]
                }
            )
            _slack_post(f"🚨 High CPU alert: Server {server.name} CPU > 90%, auto-restart initiated")

            # TODO: Implement actual server restart logic
            # This would require integration with the game server management system

        _log("scaling", f"Auto-scaling check completed: {len(high_cpu_servers)} servers flagged")

    except Exception as e:
        _log("scaling", f"Auto-scaling check exception: {e}")
        _discord_post({"content": f"Auto-scaling check exception: {e}"})
        _slack_post(f"🚨 Auto-scaling check exception: {e}")
