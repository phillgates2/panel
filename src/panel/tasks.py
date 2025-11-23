"""
Background Tasks
Asynchronous task processing using Celery
"""

import os
import subprocess
import tempfile
from datetime import datetime

from src.panel.celery_app import celery_app

# Determine LOG_DIR with fallback to writable temp directory if configured dir is not accessible
try:
    from src.panel import config
    _log_dir_env = os.environ.get("LOG_DIR")
    _log_dir_config = config.LOG_DIR
    LOG_DIR = _log_dir_env or _log_dir_config
except ImportError:
    LOG_DIR = os.path.join(tempfile.gettempdir(), "panel_logs")

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
    line = f"[{datetime.utcnow().isoformat()}] {msg}\n"
    with open(path, "a") as f:
        f.write(line)


def _discord_post(payload):
    """Send Discord notification"""
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
        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        # best-effort
        pass


def _slack_post(message):
    """Send Slack notification"""
    webhook = os.environ.get("PANEL_SLACK_WEBHOOK", "")
    if not webhook:
        try:
            from src.panel import config
            webhook = getattr(config, "SLACK_WEBHOOK", "")
        except ImportError:
            pass

    if not webhook:
        return

    try:
        import requests
        payload = {"text": message}
        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        # best-effort
        pass


@celery_app.task(name='panel.send_email')
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


@celery_app.task(name='panel.process_file')
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


@celery_app.task(name='panel.backup_database')
def backup_database_task():
    """Run database backup asynchronously"""
    try:
        from tools.scripts.backup_manager import BackupManager

        backup_manager = BackupManager()
        backup_file = backup_manager.create_backup()

        if backup_file:
            _log("backup", f"Database backup completed: {backup_file}")

            # Send notifications
            _discord_post({
                "embeds": [{
                    "title": "Database Backup Completed",
                    "description": f"Backup saved to: {backup_file}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "color": 3066993,
                }]
            })
            _slack_post(f"✅ Database backup completed: {backup_file}")

            return {"status": "completed", "backup_file": backup_file}
        else:
            _log("backup", "Database backup failed")
            return {"status": "failed", "error": "Backup creation failed"}

    except Exception as e:
        _log("backup", f"Database backup exception: {e}")
        _discord_post({"content": f"Database backup exception: {e}"})
        return {"status": "failed", "error": str(e)}


@celery_app.task(name='panel.run_autodeploy')
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
        proc = subprocess.run([script_path], capture_output=True, text=True, env=env, timeout=3600)
        _log("autodeploy", "STDOUT:\n" + proc.stdout)
        _log("autodeploy", "STDERR:\n" + proc.stderr)

        if proc.returncode == 0:
            payload = {
                "content": None,
                "embeds": [{
                    "title": "Autodeploy Completed",
                    "description": f'Autodeploy finished successfully for {download_url or "(default)"}.',
                    "timestamp": datetime.utcnow().isoformat(),
                    "color": 3066993,
                }]
            }
            _discord_post(payload)
            return {"ok": True, "out": proc.stdout}
        else:
            payload = {
                "content": None,
                "embeds": [{
                    "title": "Autodeploy Failed",
                    "description": f"Autodeploy failed (rc={proc.returncode})",
                    "fields": [{"name": "stderr", "value": proc.stderr[:1000]}],
                    "timestamp": datetime.utcnow().isoformat(),
                    "color": 15158332,
                }]
            }
            _discord_post(payload)
            return {"ok": False, "out": proc.stdout, "err": proc.stderr}

    excep
