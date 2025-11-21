#!/usr/bin/env python3
"""Database migration script - creates all missing tables.

This script ensures all database tables are created, including
tables from models_extended.py which may not exist in older installations.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from config_manager import ConfigDeployment, ConfigTemplate

# Import all models to ensure they're registered
from models_extended import (
    ApiKey,
    IpAccessControl,
    Notification,
    PerformanceMetric,
    ServerTemplate,
    TwoFactorAuth,
    UserActivity,
    UserSession,
)


def migrate_database():
    """Create all database tables."""
    with app.app_context():
        print("Starting database migration...")

        # Get existing tables
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        print(f"Existing tables: {len(existing_tables)}")

        # Create all tables (only creates missing ones)
        db.create_all()

        # Get updated table list
        inspector = inspect(db.engine)
        new_tables = set(inspector.get_table_names())

        # Show what was created
        created = new_tables - existing_tables
        if created:
            print(f"\n✓ Created {len(created)} new table(s):")
            for table in sorted(created):
                print(f"  - {table}")
        else:
            print("\n✓ All tables already exist")

        print(f"\n✓ Total tables in database: {len(new_tables)}")
        print("\nDatabase migration completed successfully!")


if __name__ == "__main__":
    migrate_database()
