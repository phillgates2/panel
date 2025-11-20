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
    webhook = os.environ.get("PANEL_DISCORD_WEBHOOK", "") or getattr(
        config, "DISCORD_WEBHOOK", ""
    )
    if not webhook:
        return
    try:
        import requests

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
        proc = subprocess.run(
            [script], capture_output=True, text=True, env=env, timeout=3600
        )
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
        proc = subprocess.run(
            [script], capture_output=True, text=True, env=env, timeout=300
        )
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
        from app import app, db, User
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
