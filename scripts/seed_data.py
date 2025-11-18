#!/usr/bin/env python3
"""Seed data generator for development and testing.

Creates sample users, servers, templates, and other data.

Usage:
    python scripts/seed_data.py --all          # Create all sample data
    python scripts/seed_data.py --users        # Create sample users only
    python scripts/seed_data.py --servers      # Create sample servers only
    python scripts/seed_data.py --clear        # Clear all data (dangerous!)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import random
from datetime import datetime, timedelta, timezone

from app import AuditLog, Server, User, app, db
from models_extended import (Notification, ServerTemplate, UserActivity,
                             UserGroup)


def create_admin_user():
    """Create system admin user."""
    admin = User.query.filter_by(email="admin@panel.local").first()
    if not admin:
        admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@panel.local",
            dob=datetime(1990, 1, 1).date(),
            role="system_admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("✓ Created admin user (admin@panel.local / admin123)")
    else:
        print("✓ Admin user already exists")

    return admin


def create_sample_users(count=10):
    """Create sample regular users."""
    created = 0

    for i in range(count):
        email = f"user{i+1}@panel.local"
        if not User.query.filter_by(email=email).first():
            user = User(
                first_name="User",
                last_name=f"{i+1}",
                email=email,
                dob=datetime(1990 + i, 1, 1).date(),
                role="user",
            )
            user.set_password("password123")
            db.session.add(user)
            created += 1

    if created:
        print(f"✓ Created {created} sample users")
    else:
        print("✓ Sample users already exist")


def create_server_templates():
    """Create sample server templates."""
    templates = [
        {
            "name": "Competitive 6v6",
            "description": "Standard competitive 6v6 configuration",
            "category": "competitive",
            "variables_json": '{"maxclients": "12", "sv_maxRate": "25000", "g_antilag": "1"}',
            "raw_config": 'set sv_hostname "Competitive Server"\nset g_gametype 6\nset sv_maxclients 12',
        },
        {
            "name": "Casual Public",
            "description": "Casual 32-player public server",
            "category": "casual",
            "variables_json": '{"maxclients": "32", "sv_maxRate": "25000", "g_antilag": "1"}',
            "raw_config": 'set sv_hostname "Public Server"\nset g_gametype 2\nset sv_maxclients 32',
        },
        {
            "name": "LAN Tournament",
            "description": "LAN-optimized tournament config",
            "category": "tournament",
            "variables_json": '{"maxclients": "12", "sv_lanOnly": "1"}',
            "raw_config": 'set sv_hostname "LAN Tournament"\nset g_gametype 6\nset sv_lanOnly 1',
        },
    ]

    created = 0
    for tmpl in templates:
        if not ServerTemplate.query.filter_by(name=tmpl["name"]).first():
            template = ServerTemplate(**tmpl)
            db.session.add(template)
            created += 1

    if created:
        print(f"✓ Created {created} server templates")
    else:
        print("✓ Server templates already exist")


def create_sample_servers(count=5):
    """Create sample servers."""
    created = 0

    templates = ServerTemplate.query.all()

    for i in range(count):
        name = f"Sample Server {i+1}"
        if not Server.query.filter_by(name=name).first():
            tmpl = random.choice(templates) if templates else None
            server = Server(
                name=name,
                description="Sample server for testing purposes",
                variables_json=tmpl.variables_json if tmpl else "{}",
                raw_config=tmpl.raw_config if tmpl else "",
            )
            db.session.add(server)
            created += 1

    if created:
        print(f"✓ Created {created} sample servers")
    else:
        print("✓ Sample servers already exist")


def create_user_groups():
    """Create sample user groups."""
    groups = [
        {
            "name": "Moderators",
            "description": "Server moderators",
            "permissions": '["kick", "ban", "mute"]',
        },
        {
            "name": "Admins",
            "description": "Server administrators",
            "permissions": '["all"]',
        },
        {
            "name": "VIP",
            "description": "VIP players",
            "permissions": '["reserved_slot"]',
        },
    ]

    created = 0
    for grp in groups:
        if not UserGroup.query.filter_by(name=grp["name"]).first():
            group = UserGroup(**grp)
            db.session.add(group)
            created += 1

    if created:
        print(f"✓ Created {created} user groups")
    else:
        print("✓ User groups already exist")


def create_sample_activity():
    """Create sample user activity logs."""
    users = User.query.limit(5).all()

    if not users:
        return

    activities = ["login", "logout", "server_create", "server_edit", "rcon_command"]

    created = 0
    for user in users:
        for _ in range(random.randint(5, 20)):
            activity = UserActivity(
                user_id=user.id,
                activity_type=random.choice(activities),
                ip_address=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                created_at=datetime.now(timezone.utc)
                - timedelta(days=random.randint(0, 30)),
            )
            db.session.add(activity)
            created += 1

    print(f"✓ Created {created} activity logs")


def create_notifications():
    """Create sample notifications."""
    users = User.query.limit(5).all()

    if not users:
        return

    messages = [
        ("Welcome!", "Welcome to the Panel. Get started by creating a server.", "info"),
        (
            "Server Ready",
            "Your server is now online and ready to accept players.",
            "success",
        ),
        ("Maintenance", "Scheduled maintenance will occur tonight at 2 AM.", "warning"),
        ("Update Available", "A new version of Panel is available.", "info"),
    ]

    created = 0
    for user in users:
        for title, message, ntype in random.sample(messages, k=2):
            notif = Notification(
                user_id=user.id,
                title=title,
                message=message,
                notification_type=ntype,
                is_read=random.choice([True, False]),
            )
            db.session.add(notif)
            created += 1

    print(f"✓ Created {created} notifications")


def clear_all_data():
    """Clear all data from database (dangerous!)."""
    if input("⚠️  This will DELETE ALL DATA. Type 'YES' to confirm: ") != "YES":
        print("Aborted.")
        return

    # Clear in reverse dependency order
    for model in [
        UserActivity,
        Notification,
        ServerTemplate,
        Server,
        AuditLog,
        UserGroup,
        User,
    ]:
        count = model.query.delete()
        if count:
            print(f"✓ Deleted {count} {model.__name__} records")

    db.session.commit()
    print("✓ All data cleared")


def main():
    args = sys.argv[1:]

    with app.app_context():
        if "--clear" in args:
            clear_all_data()
            return

        if "--users" in args or "--all" in args:
            create_admin_user()
            create_sample_users()

        if "--groups" in args or "--all" in args:
            create_user_groups()

        if "--templates" in args or "--all" in args:
            create_server_templates()

        if "--servers" in args or "--all" in args:
            create_sample_servers()

        if "--activity" in args or "--all" in args:
            create_sample_activity()

        if "--notifications" in args or "--all" in args:
            create_notifications()

        # Commit all changes
        try:
            db.session.commit()
            print("\n✅ Seed data created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(1)

    sys.exit(main())
