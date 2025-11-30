"""Background Job Processing with RQ

Provides asynchronous task processing using Redis Queue (RQ).
Handles long-running tasks like server backups, bulk operations, and notifications.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from redis import Redis
from rq import Queue, get_current_job

from simple_config import load_config

# Redis connection for RQ
redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
redis_conn = Redis.from_url(redis_url)

# Job queues
default_queue = Queue("default", connection=redis_conn)
backup_queue = Queue("backup", connection=redis_conn)
notification_queue = Queue("notification", connection=redis_conn)
maintenance_queue = Queue("maintenance", connection=redis_conn)


# ===== Job Functions =====


def process_server_backup(server_id: int, backup_type: str = "full") -> Dict[str, Any]:
    """Process server backup asynchronously."""
    job = get_current_job()
    job.meta["progress"] = 0
    job.save_meta()

    try:
        from models import Server

        from app import create_app, db

        app = create_app()
        with app.app_context():
            server = db.session.get(Server, server_id)
            if not server:
                raise ValueError(f"Server {server_id} not found")

            job.meta["progress"] = 10
            job.meta["message"] = f"Starting {backup_type} backup for {server.name}"
            job.save_meta()

            # Simulate backup process
            time.sleep(2)  # Simulate file operations

            job.meta["progress"] = 50
            job.meta["message"] = "Compressing server data"
            job.save_meta()

            time.sleep(3)  # Simulate compression

            job.meta["progress"] = 80
            job.meta["message"] = "Uploading to storage"
            job.save_meta()

            time.sleep(2)  # Simulate upload

            job.meta["progress"] = 100
            job.meta["message"] = "Backup completed successfully"
            job.save_meta()

            # Log the backup
            from app import AuditLog

            db.session.add(
                AuditLog(
                    user_id=server.user_id,
                    action=f"server_backup:{backup_type}",
                    details=f"Backup completed for server {server.name}",
                )
            )
            db.session.commit()

            return {
                "status": "completed",
                "server_id": server_id,
                "server_name": server.name,
                "backup_type": backup_type,
                "timestamp": datetime.utcnow().isoformat(),
                "size_mb": 150.5,  # Simulated size
            }

    except Exception as e:
        job.meta["progress"] = 0
        job.meta["error"] = str(e)
        job.save_meta()
        raise


def send_bulk_notifications(
    user_ids: list, subject: str, message: str, notification_type: str = "email"
) -> Dict[str, Any]:
    """Send bulk notifications asynchronously."""
    job = get_current_job()
    total_users = len(user_ids)
    successful = 0
    failed = 0

    job.meta["progress"] = 0
    job.meta["message"] = f"Starting bulk notification to {total_users} users"
    job.save_meta()

    try:
        from models import User

        from app import create_app, db

        app = create_app()
        with app.app_context():
            for i, user_id in enumerate(user_ids):
                try:
                    user = db.session.get(User, user_id)
                    if not user or not user.email:
                        failed += 1
                        continue

                    # Simulate sending notification
                    time.sleep(0.1)  # Simulate email/API call

                    # Log notification
                    from app import AuditLog

                    db.session.add(
                        AuditLog(
                            user_id=user_id,
                            action=f"notification_sent:{notification_type}",
                            details=f"Subject: {subject}",
                        )
                    )

                    successful += 1

                except Exception as e:
                    failed += 1
                    print(f"Failed to notify user {user_id}: {e}")

                # Update progress
                progress = int((i + 1) / total_users * 100)
                job.meta["progress"] = progress
                job.meta["message"] = f"Processed {i + 1}/{total_users} notifications"
                job.save_meta()

            db.session.commit()

            job.meta["progress"] = 100
            job.meta["message"] = (
                f"Bulk notification completed: {successful} sent, {failed} failed"
            )
            job.save_meta()

            return {
                "status": "completed",
                "total_users": total_users,
                "successful": successful,
                "failed": failed,
                "notification_type": notification_type,
                "subject": subject,
            }

    except Exception as e:
        job.meta["error"] = str(e)
        job.save_meta()
        raise


def cleanup_old_logs(days_to_keep: int = 90) -> Dict[str, Any]:
    """Clean up old audit logs asynchronously."""
    job = get_current_job()

    try:
        from datetime import datetime, timedelta

        from models import AuditLog

        from app import create_app, db

        app = create_app()
        with app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            job.meta["progress"] = 10
            job.meta["message"] = f"Deleting logs older than {days_to_keep} days"
            job.save_meta()

            # Count logs to be deleted
            count_to_delete = AuditLog.query.filter(
                AuditLog.created_at < cutoff_date
            ).count()

            # Delete old logs
            deleted_count = AuditLog.query.filter(
                AuditLog.created_at < cutoff_date
            ).delete()

            db.session.commit()

            job.meta["progress"] = 100
            job.meta["message"] = f"Cleanup completed: {deleted_count} logs deleted"
            job.save_meta()

            return {
                "status": "completed",
                "logs_deleted": deleted_count,
                "days_kept": days_to_keep,
                "cutoff_date": cutoff_date.isoformat(),
            }

    except Exception as e:
        job.meta["error"] = str(e)
        job.save_meta()
        raise


def update_server_metrics_bulk(server_ids: list) -> Dict[str, Any]:
    """Update metrics for multiple servers asynchronously."""
    job = get_current_job()
    total_servers = len(server_ids)
    successful = 0
    failed = 0

    job.meta["progress"] = 0
    job.meta["message"] = f"Starting metrics update for {total_servers} servers"
    job.save_meta()

    try:
        from app import create_app
        from monitoring_system import collect_server_metrics

        app = create_app()
        with app.app_context():
            for i, server_id in enumerate(server_ids):
                try:
                    collect_server_metrics(server_id)
                    successful += 1
                except Exception as e:
                    failed += 1
                    print(f"Failed to update metrics for server {server_id}: {e}")

                # Update progress
                progress = int((i + 1) / total_servers * 100)
                job.meta["progress"] = progress
                job.meta["message"] = (
                    f"Updated metrics for {i + 1}/{total_servers} servers"
                )
                job.save_meta()

            job.meta["progress"] = 100
            job.meta["message"] = (
                f"Metrics update completed: {successful} successful, {failed} failed"
            )
            job.save_meta()

            return {
                "status": "completed",
                "total_servers": total_servers,
                "successful": successful,
                "failed": failed,
            }

    except Exception as e:
        job.meta["error"] = str(e)
        job.save_meta()
        raise


# ===== Job Management =====


class JobManager:
    """Manager for background jobs."""

    def __init__(self):
        self.redis_conn = redis_conn

    def enqueue_backup(self, server_id: int, backup_type: str = "full") -> str:
        """Enqueue a server backup job."""
        job = backup_queue.enqueue(
            process_server_backup,
            server_id,
            backup_type,
            job_timeout=3600,  # 1 hour timeout
            result_ttl=86400,  # Keep results for 24 hours
        )
        return job.id

    def enqueue_bulk_notification(
        self, user_ids: list, subject: str, message: str
    ) -> str:
        """Enqueue a bulk notification job."""
        job = notification_queue.enqueue(
            send_bulk_notifications,
            user_ids,
            subject,
            message,
            job_timeout=1800,  # 30 minutes timeout
            result_ttl=3600,  # Keep results for 1 hour
        )
        return job.id

    def enqueue_log_cleanup(self, days_to_keep: int = 90) -> str:
        """Enqueue a log cleanup job."""
        job = maintenance_queue.enqueue(
            cleanup_old_logs,
            days_to_keep,
            job_timeout=1800,  # 30 minutes timeout
            result_ttl=3600,  # Keep results for 1 hour
        )
        return job.id

    def enqueue_metrics_update(self, server_ids: list) -> str:
        """Enqueue a bulk metrics update job."""
        job = default_queue.enqueue(
            update_server_metrics_bulk,
            server_ids,
            job_timeout=1800,  # 30 minutes timeout
            result_ttl=3600,  # Keep results for 1 hour
        )
        return job.id

    def get_job_status(
        self, job_id: str, queue_name: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        try:
            queue = self._get_queue(queue_name)
            job = queue.fetch_job(job_id)

            if not job:
                return None

            return {
                "id": job.id,
                "status": job.get_status(),
                "progress": job.meta.get("progress", 0),
                "message": job.meta.get("message", ""),
                "error": job.meta.get("error"),
                "result": job.result,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def cancel_job(self, job_id: str, queue_name: str = "default") -> bool:
        """Cancel a job."""
        try:
            queue = self._get_queue(queue_name)
            job = queue.fetch_job(job_id)
            if job:
                job.cancel()
                return True
            return False
        except Exception:
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues."""
        stats = {}
        for queue_name in ["default", "backup", "notification", "maintenance"]:
            queue = self._get_queue(queue_name)
            stats[queue_name] = {
                "queued": queue.count,
                "failed": queue.failed_job_registry.count,
                "finished": len(queue.finished_job_registry.get_job_ids()),
            }
        return stats

    def _get_queue(self, queue_name: str):
        """Get queue by name."""
        queues = {
            "default": default_queue,
            "backup": backup_queue,
            "notification": notification_queue,
            "maintenance": maintenance_queue,
        }
        return queues.get(queue_name, default_queue)


# Global job manager instance
job_manager = JobManager()


# ===== Flask Routes =====


def init_background_jobs(app):
    """Initialize background job routes."""
    from flask import Blueprint, jsonify, request

    from app import db

    jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

    @jobs_bp.route("/backup/server/<int:server_id>", methods=["POST"])
    def enqueue_server_backup(server_id):
        """Enqueue a server backup job."""
        from flask import session
        from models import Server

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        server = db.session.get(Server, server_id)

        if not server or server.user_id != user.id:
            return jsonify({"error": "Server not found"}), 404

        backup_type = (
            request.json.get("backup_type", "full") if request.is_json else "full"
        )

        job_id = job_manager.enqueue_backup(server_id, backup_type)

        return jsonify(
            {
                "job_id": job_id,
                "message": f"Backup job enqueued for server {server.name}",
                "backup_type": backup_type,
            }
        )

    @jobs_bp.route("/notification/bulk", methods=["POST"])
    def enqueue_bulk_notification():
        """Enqueue a bulk notification job."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        if not request.is_json:
            return jsonify({"error": "JSON required"}), 400

        data = request.json
        user_ids = data.get("user_ids", [])
        subject = data.get("subject", "")
        message = data.get("message", "")

        if not user_ids or not subject or not message:
            return jsonify({"error": "user_ids, subject, and message required"}), 400

        job_id = job_manager.enqueue_bulk_notification(user_ids, subject, message)

        return jsonify(
            {
                "job_id": job_id,
                "message": f"Bulk notification enqueued for {len(user_ids)} users",
            }
        )

    @jobs_bp.route("/maintenance/cleanup-logs", methods=["POST"])
    def enqueue_log_cleanup():
        """Enqueue a log cleanup job."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        days_to_keep = request.json.get("days_to_keep", 90) if request.is_json else 90

        job_id = job_manager.enqueue_log_cleanup(days_to_keep)

        return jsonify(
            {
                "job_id": job_id,
                "message": f"Log cleanup enqueued (keeping {days_to_keep} days)",
            }
        )

    @jobs_bp.route("/metrics/update-bulk", methods=["POST"])
    def enqueue_metrics_update():
        """Enqueue a bulk metrics update job."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        if not request.is_json:
            return jsonify({"error": "JSON required"}), 400

        server_ids = request.json.get("server_ids", [])

        if not server_ids:
            return jsonify({"error": "server_ids required"}), 400

        job_id = job_manager.enqueue_metrics_update(server_ids)

        return jsonify(
            {
                "job_id": job_id,
                "message": f"Metrics update enqueued for {len(server_ids)} servers",
            }
        )

    @jobs_bp.route("/<job_id>")
    def get_job_status(job_id):
        """Get status of a job."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        queue_name = request.args.get("queue", "default")
        status = job_manager.get_job_status(job_id, queue_name)

        if status is None:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(status)

    @jobs_bp.route("/<job_id>/cancel", methods=["POST"])
    def cancel_job(job_id):
        """Cancel a job."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        queue_name = request.args.get("queue", "default")
        success = job_manager.cancel_job(job_id, queue_name)

        if success:
            return jsonify({"message": f"Job {job_id} cancelled"})
        else:
            return jsonify({"error": "Failed to cancel job"}), 500

    @jobs_bp.route("/stats")
    def get_queue_stats():
        """Get queue statistics."""
        from flask import session

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(db.session.get(db.User, uid))
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        stats = job_manager.get_queue_stats()
        return jsonify(stats)

    app.register_blueprint(jobs_bp)


# ===== RQ Worker Script =====

WORKER_SCRIPT = '''
#!/usr/bin/env python3
"""
RQ Worker Script for Panel Background Jobs

Run with: python rq_worker.py
"""

import os
import sys
from rq import Worker, Queue, Connection
from redis import Redis

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import job functions
from background_jobs import (
    default_queue, backup_queue, notification_queue, maintenance_queue
)

# Redis connection
redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
redis_conn = Redis.from_url(redis_url)

# Listen to all queues
listen = ['high', 'default', 'backup', 'notification', 'maintenance']

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen), connection=redis_conn)
        worker.work()
'''
