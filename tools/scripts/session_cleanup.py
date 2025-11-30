#!/usr/bin/env python3
"""
Session cleanup script to remove expired sessions.

This script should be run periodically to clean up expired sessions.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path so we can import the models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models_extended import UserActivity, UserSession


def cleanup_expired_sessions():
    """Remove expired sessions from the database."""
    with app.app_context():
        now = datetime.now(timezone.utc)

        # Find expired sessions
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at < now, UserSession.is_active
        ).all()

        if expired_sessions:
            print(f"Found {len(expired_sessions)} expired sessions to clean up")

            for session in expired_sessions:
                session.is_active = False

                # Log the session expiry
                db.session.add(
                    UserActivity(
                        user_id=session.user_id,
                        activity_type="session_expired",
                        details=f"Session {session.id} expired automatically",
                    )
                )

            db.session.commit()
            print(f"Cleaned up {len(expired_sessions)} expired sessions")
        else:
            print("No expired sessions found")


def cleanup_old_sessions(days_old=30):
    """Remove old inactive sessions beyond specified days."""
    with app.app_context():
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        old_sessions = UserSession.query.filter(
            UserSession.created_at < cutoff_date, UserSession.is_active.is_(False)
        ).all()

        if old_sessions:
            print(f"Found {len(old_sessions)} old sessions to remove")

            for session in old_sessions:
                db.session.delete(session)

            db.session.commit()
            print(f"Removed {len(old_sessions)} old sessions")
        else:
            print("No old sessions found")


def cleanup_old_activity(days_old=90):
    """Remove old user activity records."""
    with app.app_context():
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        old_activities = UserActivity.query.filter(
            UserActivity.created_at < cutoff_date
        ).all()

        if old_activities:
            print(f"Found {len(old_activities)} old activity records to remove")

            for activity in old_activities:
                db.session.delete(activity)

            db.session.commit()
            print(f"Removed {len(old_activities)} old activity records")
        else:
            print("No old activity records found")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean up expired sessions and old data"
    )
    parser.add_argument(
        "--sessions", action="store_true", help="Clean up expired sessions"
    )
    parser.add_argument(
        "--old-sessions",
        type=int,
        default=30,
        help="Remove inactive sessions older than N days (default: 30)",
    )
    parser.add_argument(
        "--old-activity",
        type=int,
        default=90,
        help="Remove activity records older than N days (default: 90)",
    )
    parser.add_argument("--all", action="store_true", help="Run all cleanup tasks")

    args = parser.parse_args()

    if args.all or args.sessions:
        cleanup_expired_sessions()

    if args.all or args.old_sessions:
        cleanup_old_sessions(args.old_sessions)

    if args.all or args.old_activity:
        cleanup_old_activity(args.old_activity)

    if not any([args.sessions, args.old_sessions, args.old_activity, args.all]):
        # Default: just clean up expired sessions
        cleanup_expired_sessions()
