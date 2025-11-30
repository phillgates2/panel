#!/usr/bin/env python3
"""
Database Migration Helper
Creates and manages database migrations using Flask-Migrate
"""

import os
import sys
from pathlib import Path

# Add app path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_migration(message: str):
    """Create a new database migration"""
    from app import create_app

    app = create_app()

    with app.app_context():
        # This will create a new migration file
        os.system(
            f"cd {Path(__file__).parent.parent} && flask db migrate -m '{message}'"
        )
        print(f"Migration created: {message}")


def upgrade_database():
    """Upgrade database to latest migration"""
    from app import create_app

    app = create_app()
    with app.app_context():
        os.system(f"cd {Path(__file__).parent.parent} && flask db upgrade")
        print("Database upgraded to latest migration")


def downgrade_database(revision: str = "-1"):
    """Downgrade database to specific revision"""
    from app import create_app

    app = create_app()
    with app.app_context():
        os.system(f"cd {Path(__file__).parent.parent} && flask db downgrade {revision}")
        print(f"Database downgraded to revision: {revision}")


def show_migration_history():
    """Show migration history"""
    from app import create_app

    app = create_app()
    with app.app_context():
        os.system(f"cd {Path(__file__).parent.parent} && flask db history")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database Migration Helper")
    parser.add_argument(
        "action",
        choices=["create", "upgrade", "downgrade", "history"],
        help="Migration action",
    )
    parser.add_argument("--message", "-m", help="Migration message (for create)")
    parser.add_argument("--revision", "-r", help="Revision to downgrade to")

    args = parser.parse_args()

    if args.action == "create":
        if not args.message:
            print("Error: --message required for create action")
            sys.exit(1)
        create_migration(args.message)
    elif args.action == "upgrade":
        upgrade_database()
    elif args.action == "downgrade":
        downgrade_database(args.revision or "-1")
    elif args.action == "history":
        show_migration_history()
