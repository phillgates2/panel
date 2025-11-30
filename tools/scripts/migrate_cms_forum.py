#!/usr/bin/env python3
"""
Migration script to add BlogPost model and update Forum models
This script adds:
1. cms_blog_post table with author_id, is_published, etc.
2. Updates forum_thread: adds author_id, is_pinned, is_locked
3. Updates forum_post: changes author (string) to author_id (FK)
"""

import os
import sys

from sqlalchemy import text

# Import app to get db context
try:
    from app import app, db
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def run_migration():
    """Run the database migration"""
    with app.app_context():
        print("Starting migration...")

        # Check if tables exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        # 1. Create cms_blog_post table if it doesn't exist
        if "cms_blog_post" not in existing_tables:
            print("Creating cms_blog_post table...")
            db.create_all()
            print("✓ cms_blog_post table created")
        else:
            print("ℹ cms_blog_post table already exists")

        # 2. Check and update forum_thread table
        print("\nChecking forum_thread table...")
        thread_columns = [col["name"] for col in inspector.get_columns("forum_thread")]

        if "author_id" not in thread_columns:
            print("Adding author_id column to forum_thread...")
            with db.engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE forum_thread ADD COLUMN author_id INTEGER")
                )
                conn.execute(
                    text(
                        "ALTER TABLE forum_thread ADD FOREIGN KEY (author_id) REFERENCES user(id)"
                    )
                )
                conn.commit()
            print("✓ author_id added to forum_thread")
        else:
            print("ℹ author_id already exists in forum_thread")

        if "is_pinned" not in thread_columns:
            print("Adding is_pinned column to forum_thread...")
            with db.engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE forum_thread ADD COLUMN is_pinned BOOLEAN DEFAULT 0"
                    )
                )
                conn.commit()
            print("✓ is_pinned added to forum_thread")
        else:
            print("ℹ is_pinned already exists in forum_thread")

        if "is_locked" not in thread_columns:
            print("Adding is_locked column to forum_thread...")
            with db.engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE forum_thread ADD COLUMN is_locked BOOLEAN DEFAULT 0"
                    )
                )
                conn.commit()
            print("✓ is_locked added to forum_thread")
        else:
            print("ℹ is_locked already exists in forum_thread")

        # 3. Check and update forum_post table
        print("\nChecking forum_post table...")
        post_columns = [col["name"] for col in inspector.get_columns("forum_post")]

        if "author_id" not in post_columns and "author" in post_columns:
            print("Migrating forum_post from author (string) to author_id (FK)...")

            # This is complex - we need to:
            # 1. Add author_id column
            # 2. Try to match existing author strings to users
            # 3. Remove old author column

            with db.engine.connect() as conn:
                # Add new column
                conn.execute(
                    text("ALTER TABLE forum_post ADD COLUMN author_id INTEGER")
                )

                # Set author_id to NULL for now (posts with string authors can't be matched)
                print(
                    "⚠ Warning: Existing posts with string authors will have author_id set to NULL"
                )
                print("  You may want to manually update these or delete old posts")

                # Add foreign key constraint
                conn.execute(
                    text(
                        "ALTER TABLE forum_post ADD FOREIGN KEY (author_id) REFERENCES user(id)"
                    )
                )

                # Optionally: Remove old author column (commented out for safety)
                # conn.execute(text('ALTER TABLE forum_post DROP COLUMN author'))

                conn.commit()

            print("✓ author_id added to forum_post")
            print(
                "ℹ Old 'author' column preserved for reference (can be manually removed)"
            )
        elif "author_id" in post_columns:
            print("ℹ author_id already exists in forum_post")
        else:
            print("ℹ forum_post table structure OK")

        print("\n" + "=" * 50)
        print("Migration completed successfully!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Restart your Flask application")
        print("2. Check that forum and CMS features work correctly")
        print("3. Consider creating some test blog posts")
        print("4. If forum has old posts, manually update or remove them")


if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Script")
    print("Adding BlogPost and updating Forum models")
    print("=" * 50)
    print()

    # Check for non-interactive mode
    non_interactive = (
        "--non-interactive" in sys.argv
        or "-y" in sys.argv
        or "--yes" in sys.argv
        or os.environ.get("PANEL_NON_INTERACTIVE", "").lower() in ("true", "1", "yes")
        or not sys.stdin.isatty()  # Not running in a terminal
    )

    if not non_interactive:
        try:
            response = input("This will modify your database. Continue? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("Migration cancelled.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nMigration cancelled.")
            sys.exit(0)
    else:
        print("Running in non-interactive mode, proceeding with migration...")

    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
