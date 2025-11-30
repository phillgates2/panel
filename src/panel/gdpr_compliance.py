"""
GDPR Compliance and Data Protection
Provides data export, deletion, consent management, and audit trails
"""

import csv
import io
import json
import zipfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Flask, current_app, jsonify, request, send_file
from werkzeug.exceptions import BadRequest, NotFound

from src.panel import db
from src.panel.models import AuditLog, User
from src.panel.tasks import send_email_task


class GDPRCompliance:
    """GDPR compliance management"""

    def __init__(self, app: Flask):
        self.app = app
        self.retention_periods = {
            "audit_logs": timedelta(days=2555),  # 7 years
            "user_activity": timedelta(days=365),  # 1 year
            "temp_files": timedelta(days=30),  # 30 days
        }

    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all user data for GDPR Article 15"""
        user = User.query.get(user_id)
        if not user:
            raise NotFound("User not found")

        # Collect all user data
        export_data = {
            "user_profile": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "dob": user.dob.isoformat() if user.dob else None,
                "bio": user.bio,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": (
                    user.dob.isoformat() if hasattr(user, "created_at") else None
                ),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "oauth_accounts": [],
            "audit_logs": [],
            "forum_activity": [],
            "blog_posts": [],
            "api_tokens": [],
            "security_events": [],
        }

        # OAuth accounts (without sensitive tokens)
        if user.has_oauth_linked:
            export_data["oauth_accounts"].append(
                {
                    "provider": user.oauth_provider,
                    "linked_at": (
                        user.oauth_token_expires.isoformat()
                        if user.oauth_token_expires
                        else None
                    ),
                }
            )

        # Audit logs
        audit_logs = AuditLog.query.filter_by(actor_id=user_id).all()
        for log in audit_logs:
            export_data["audit_logs"].append(
                {
                    "action": log.action,
                    "timestamp": log.created_at.isoformat(),
                }
            )

        # Forum activity
        from src.panel.forum import Post, Thread

        threads = Thread.query.filter_by(author_id=user_id).all()
        posts = Post.query.filter_by(author_id=user_id).all()

        for thread in threads:
            export_data["forum_activity"].append(
                {
                    "type": "thread",
                    "title": thread.title,
                    "created_at": thread.created_at.isoformat(),
                    "is_pinned": thread.is_pinned,
                    "is_locked": thread.is_locked,
                }
            )

        for post in posts:
            export_data["forum_activity"].append(
                {
                    "type": "post",
                    "thread_id": post.thread_id,
                    "content": post.content,
                    "created_at": post.created_at.isoformat(),
                }
            )

        # Blog posts
        blog_posts = user.blog_posts
        for post in blog_posts:
            export_data["blog_posts"].append(
                {
                    "title": post.title,
                    "slug": post.slug,
                    "content": post.content,
                    "excerpt": post.excerpt,
                    "is_published": post.is_published,
                    "created_at": post.created_at.isoformat(),
                    "updated_at": post.updated_at.isoformat(),
                }
            )

        # API tokens (without actual tokens)
        from src.panel.models_extended import ApiKey

        api_keys = ApiKey.query.filter_by(user_id=user_id).all()
        for key in api_keys:
            export_data["api_tokens"].append(
                {
                    "name": key.name,
                    "created_at": key.created_at.isoformat(),
                    "last_used": key.last_used.isoformat() if key.last_used else None,
                    "is_active": key.is_active,
                }
            )

        # Security events
        from src.panel.models_extended import SecurityEvent, UserActivity

        activities = UserActivity.query.filter_by(user_id=user_id).all()
        security_events = SecurityEvent.query.filter_by(user_id=user_id).all()

        for activity in activities:
            export_data["security_events"].append(
                {
                    "type": "activity",
                    "activity_type": activity.activity_type,
                    "ip_address": activity.ip_address,
                    "timestamp": activity.created_at.isoformat(),
                }
            )

        for event in security_events:
            export_data["security_events"].append(
                {
                    "type": "security_event",
                    "event_type": event.event_type,
                    "ip_address": event.ip_address,
                    "description": event.description,
                    "severity": event.severity,
                    "timestamp": event.created_at.isoformat(),
                }
            )

        return export_data

    def delete_user_data(
        self, user_id: int, reason: str = "user_request"
    ) -> Dict[str, Any]:
        """Delete all user data for GDPR Article 17 (right to erasure)"""
        user = User.query.get(user_id)
        if not user:
            raise NotFound("User not found")

        deletion_summary = {
            "user_id": user_id,
            "email": user.email,
            "deletion_reason": reason,
            "deleted_at": datetime.utcnow().isoformat(),
            "data_removed": [],
        }

        try:
            # Delete forum content
            from src.panel.forum import Post, Thread

            threads_deleted = Thread.query.filter_by(author_id=user_id).delete()
            posts_deleted = Post.query.filter_by(author_id=user_id).delete()

            if threads_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{threads_deleted} forum threads"
                )
            if posts_deleted > 0:
                deletion_summary["data_removed"].append(f"{posts_deleted} forum posts")

            # Delete blog posts
            blog_posts_deleted = len(user.blog_posts)
            for post in user.blog_posts:
                db.session.delete(post)

            if blog_posts_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{blog_posts_deleted} blog posts"
                )

            # Delete API tokens
            from src.panel.models_extended import ApiKey

            api_keys_deleted = ApiKey.query.filter_by(user_id=user_id).delete()

            if api_keys_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{api_keys_deleted} API tokens"
                )

            # Delete audit logs
            audit_logs_deleted = AuditLog.query.filter_by(actor_id=user_id).delete()

            if audit_logs_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{audit_logs_deleted} audit log entries"
                )

            # Delete user activities and security events
            from src.panel.models_extended import SecurityEvent, UserActivity

            activities_deleted = UserActivity.query.filter_by(user_id=user_id).delete()
            security_deleted = SecurityEvent.query.filter_by(user_id=user_id).delete()

            if activities_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{activities_deleted} user activities"
                )
            if security_deleted > 0:
                deletion_summary["data_removed"].append(
                    f"{security_deleted} security events"
                )

            # Anonymize user (don't delete completely to maintain referential integrity)
            user.first_name = "[DELETED]"
            user.last_name = "[DELETED]"
            user.email = f"deleted_{user_id}@anonymous.local"
            user.bio = None
            user.avatar = None
            user.is_active = False
            user.reset_token = None

            # Remove OAuth links
            user.unlink_oauth_account()

            # Clear sensitive data
            user.totp_secret = None
            user.backup_codes = None

            db.session.commit()

            deletion_summary["data_removed"].append("user profile (anonymized)")
            deletion_summary["status"] = "completed"

        except Exception as e:
            db.session.rollback()
            deletion_summary["status"] = "failed"
            deletion_summary["error"] = str(e)

        return deletion_summary

    def apply_data_retention(self) -> Dict[str, int]:
        """Apply data retention policies"""
        now = datetime.utcnow()
        deleted_counts = {}

        # Delete old audit logs
        cutoff = now - self.retention_periods["audit_logs"]
        deleted_counts["audit_logs"] = AuditLog.query.filter(
            AuditLog.created_at < cutoff
        ).delete()

        # Delete old user activities
        cutoff = now - self.retention_periods["user_activity"]
        from src.panel.models_extended import UserActivity

        deleted_counts["user_activities"] = UserActivity.query.filter(
            UserActivity.created_at < cutoff
        ).delete()

        # Delete old security events
        from src.panel.models_extended import SecurityEvent

        deleted_counts["security_events"] = SecurityEvent.query.filter(
            SecurityEvent.created_at < cutoff
        ).delete()

        db.session.commit()

        return deleted_counts

    def get_consent_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's consent status for data processing"""
        user = User.query.get(user_id)
        if not user:
            raise NotFound("User not found")

        # For now, assume consent is given at registration
        # In production, you'd have a consent management system
        return {
            "user_id": user_id,
            "marketing_consent": True,  # Default for existing users
            "analytics_consent": True,
            "necessary_cookies": True,  # Always required
            "last_updated": user.last_login.isoformat() if user.last_login else None,
        }

    def update_consent(self, user_id: int, consent_data: Dict[str, bool]) -> bool:
        """Update user's consent preferences"""
        user = User.query.get(user_id)
        if not user:
            raise NotFound("User not found")

        # In a real implementation, you'd store consent preferences
        # For now, just validate and return success
        valid_keys = ["marketing_consent", "analytics_consent", "necessary_cookies"]
        for key in consent_data:
            if key not in valid_keys:
                raise BadRequest(f"Invalid consent key: {key}")

        # Log consent change
        from src.panel.structured_logging import log_security_event

        log_security_event(
            "consent_updated",
            f"User {user.email} updated consent preferences",
            user_id,
            request.remote_addr,
            consent_data=consent_data,
        )

        return True


class DataExportService:
    """Service for exporting user data in various formats"""

    @staticmethod
    def export_as_json(data: Dict[str, Any]) -> str:
        """Export data as JSON string"""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def export_as_csv(data: Dict[str, Any]) -> str:
        """Export data as CSV (flattened structure)"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Category", "Field", "Value"])

        # Flatten nested data
        for category, items in data.items():
            if isinstance(items, list):
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        for field, value in item.items():
                            writer.writerow([f"{category}[{i}]", field, str(value)])
                    else:
                        writer.writerow([f"{category}[{i}]", "", str(item)])
            elif isinstance(items, dict):
                for field, value in items.items():
                    writer.writerow([category, field, str(value)])
            else:
                writer.writerow([category, "", str(items)])

        return output.getvalue()

    @staticmethod
    def create_zip_export(data: Dict[str, Any], user_email: str) -> io.BytesIO:
        """Create a ZIP file containing all export formats"""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # JSON export
            json_data = DataExportService.export_as_json(data)
            zip_file.writestr("data.json", json_data)

            # CSV export
            csv_data = DataExportService.export_as_csv(data)
            zip_file.writestr("data.csv", csv_data)

            # Add README
            readme = f"""Data Export for {user_email}

This archive contains your personal data exported under GDPR Article 15.

Files included:
- data.json: Complete data in JSON format
- data.csv: Data in CSV format for spreadsheet applications

Export generated on: {datetime.utcnow().isoformat()}

If you have any questions about this data, please contact our privacy officer.
"""
            zip_file.writestr("README.txt", readme)

        zip_buffer.seek(0)
        return zip_buffer


# Global instance
gdpr_compliance = None
data_export_service = DataExportService()


def init_gdpr_compliance(app: Flask) -> None:
    """Initialize GDPR compliance features"""
    global gdpr_compliance
    gdpr_compliance = GDPRCompliance(app)

    # Schedule data retention cleanup (would be done via cron in production)
    @app.cli.command("cleanup-retention")
    def cleanup_retention():
        """Clean up old data according to retention policies"""
        if gdpr_compliance:
            results = gdpr_compliance.apply_data_retention()
            print(f"Data retention cleanup completed: {results}")

    app.logger.info("GDPR compliance features initialized")


def get_gdpr_compliance() -> GDPRCompliance:
    """Get the global GDPR compliance instance"""
    return gdpr_compliance
