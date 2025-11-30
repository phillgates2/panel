#!/usr/bin/env python3
"""
Database Seeding Script
Populates the database with sample data for testing and demonstrations
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add app path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from src.panel.models import User, Server
from src.panel.models_extended import UserGroup, UserGroupMembership


def create_sample_users():
    """Create sample users with different roles"""
    print("Creating sample users...")

    users_data = [
        {
            "first_name": "System",
            "last_name": "Administrator",
            "email": "admin@panel.local",
            "role": "system_admin",
            "bio": "System administrator with full access"
        },
        {
            "first_name": "Server",
            "last_name": "Admin",
            "email": "serveradmin@panel.local",
            "role": "admin",
            "bio": "Server administrator"
        },
        {
            "first_name": "Forum",
            "last_name": "Moderator",
            "email": "moderator@panel.local",
            "role": "moderator",
            "bio": "Forum moderator"
        },
        {
            "first_name": "Premium",
            "last_name": "User",
            "email": "premium@panel.local",
            "role": "premium",
            "bio": "Premium user with enhanced features"
        },
        {
            "first_name": "Regular",
            "last_name": "User",
            "email": "user@panel.local",
            "role": "user",
            "bio": "Regular user"
        },
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "role": "user",
            "bio": "Sample user for testing"
        },
        {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "role": "premium",
            "bio": "Another sample user"
        }
    ]

    users = []
    for user_data in users_data:
        user = User.query.filter_by(email=user_data["email"]).first()
        if not user:
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                email=user_data["email"],
                dob=datetime(1990, 1, 1, tzinfo=timezone.utc).date(),
                role=user_data["role"],
                bio=user_data["bio"]
            )
            user.set_password("password123")
            db.session.add(user)
            users.append(user)
        else:
            users.append(user)

    db.session.commit()
    print(f"Created {len(users)} users")
    return users


def create_sample_servers(users):
    """Create sample game servers"""
    print("Creating sample servers...")

    admin_user = next((u for u in users if u.role == "system_admin"), users[0])

    servers_data = [
        {
            "name": "Main Server",
            "description": "Primary game server for competitive play",
            "host": "127.0.0.1",
            "port": 27960,
            "game_type": "etlegacy",
            "owner_id": admin_user.id
        },
        {
            "name": "Casual Server",
            "description": "Casual gameplay server",
            "host": "127.0.0.1",
            "port": 27961,
            "game_type": "etlegacy",
            "owner_id": admin_user.id
        },
        {
            "name": "Test Server",
            "description": "Development and testing server",
            "host": "127.0.0.1",
            "port": 27962,
            "game_type": "quake3",
            "owner_id": admin_user.id
        }
    ]

    servers = []
    for server_data in servers_data:
        server = Server.query.filter_by(name=server_data["name"]).first()
        if not server:
            server = Server(**server_data)
            db.session.add(server)
            servers.append(server)
        else:
            servers.append(server)

    db.session.commit()
    print(f"Created {len(servers)} servers")
    return servers


def create_sample_user_groups(users):
    """Create sample user groups"""
    print("Creating sample user groups...")

    groups_data = [
        {
            "name": "Administrators",
            "description": "System administrators with full access",
            "permissions": ["system_config", "user_management", "server_management"]
        },
        {
            "name": "Moderators",
            "description": "Forum and community moderators",
            "permissions": ["moderate_forum", "edit_posts", "view_admin"]
        },
        {
            "name": "Premium Users",
            "description": "Users with premium features",
            "permissions": ["premium_features"]
        },
        {
            "name": "Beta Testers",
            "description": "Users testing new features",
            "permissions": ["beta_access"]
        }
    ]

    groups = []
    for group_data in groups_data:
        group = UserGroup.query.filter_by(name=group_data["name"]).first()
        if not group:
            group = UserGroup(
                name=group_data["name"],
                description=group_data["description"],
                permissions=str(group_data["permissions"])
            )
            db.session.add(group)
            groups.append(group)
        else:
            groups.append(group)

    # Assign users to groups
    admin_group = next((g for g in groups if g.name == "Administrators"), None)
    mod_group = next((g for g in groups if g.name == "Moderators"), None)
    premium_group = next((g for g in groups if g.name == "Premium Users"), None)

    memberships = []

    # Add system admin to admin group
    admin_user = next((u for u in users if u.role == "system_admin"), None)
    if admin_user and admin_group:
        membership = UserGroupMembership.query.filter_by(
            user_id=admin_user.id, group_id=admin_group.id
        ).first()
        if not membership:
            membership = UserGroupMembership(
                user_id=admin_user.id, group_id=admin_group.id
            )
            db.session.add(membership)
            memberships.append(membership)

    # Add moderator to mod group
    mod_user = next((u for u in users if u.role == "moderator"), None)
    if mod_user and mod_group:
        membership = UserGroupMembership.query.filter_by(
            user_id=mod_user.id, group_id=mod_group.id
        ).first()
        if not membership:
            membership = UserGroupMembership(
                user_id=mod_user.id, group_id=mod_group.id
            )
            db.session.add(membership)
            memberships.append(membership)

    # Add premium users to premium group
    premium_users = [u for u in users if u.role == "premium"]
    if premium_group:
        for user in premium_users:
            membership = UserGroupMembership.query.filter_by(
                user_id=user.id, group_id=premium_group.id
            ).first()
            if not membership:
                membership = UserGroupMembership(
                    user_id=user.id, group_id=premium_group.id
                )
                db.session.add(membership)
                memberships.append(membership)

    db.session.commit()
    print(f"Created {len(groups)} groups and {len(memberships)} memberships")
    return groups


def create_sample_forum_content(users):
    """Create sample forum threads and posts"""
    print("Creating sample forum content...")

    from src.panel.forum import Thread, Post

    # Create sample threads
    threads_data = [
        {
            "title": "Welcome to the Panel Forum!",
            "content": "Welcome to our community forum! Discuss strategies, share experiences.",
            "author": users[0],  # admin
            "is_pinned": True
        },
        {
            "title": "Server Rules and Guidelines",
            "content": "Please read and follow these rules to ensure a positive gaming experience.",
            "author": users[1],  # server admin
            "is_pinned": True
        },
        {
            "title": "Best strategies for competitive play",
            "content": "Share your tips and strategies for winning matches!",
            "author": users[5],  # regular user
            "is_pinned": False
        },
        {
            "title": "New update feedback",
            "content": "What do you think of the latest game update?",
            "author": users[6],  # another user
            "is_pinned": False
        }
    ]

    threads = []
    for thread_data in threads_data:
        thread = Thread(
            title=thread_data["title"],
            author_id=thread_data["author"].id,
            is_pinned=thread_data["is_pinned"]
        )
        db.session.add(thread)
        db.session.flush()  # Get thread ID

        # Create initial post
        post = Post(
            thread_id=thread.id,
            author_id=thread_data["author"].id,
            content=thread_data["content"]
        )
        db.session.add(post)

        # Add some replies to non-pinned threads
        if not thread_data["is_pinned"]:
            for i, reply_user in enumerate(users[1:4]):
                reply = Post(
                    thread_id=thread.id,
                    author_id=reply_user.id,
                    content=f"This is reply #{i+1} to the thread. Great discussion!"
                )
                db.session.add(reply)

        threads.append(thread)

    db.session.commit()
    print(f"Created {len(threads)} forum threads with posts")


def create_sample_blog_posts(users):
    """Create sample blog posts"""
    print("Creating sample blog posts...")

    from src.panel.cms import BlogPost

    posts_data = [
        {
            "title": "Welcome to Panel Blog",
            "slug": "welcome-to-panel-blog",
            "content": "Welcome to the official Panel blog! We'll share news, updates, highlights.",
            "excerpt": "Official welcome post for the Panel blog",
            "author": users[0],
            "is_published": True
        },
        {
            "title": "Server Maintenance Schedule",
            "slug": "server-maintenance-schedule",
            "content": "Scheduled maintenance windows and expected downtime information.",
            "excerpt": "Important maintenance schedule information",
            "author": users[1],
            "is_published": True
        },
        {
            "title": "New Features Coming Soon",
            "slug": "new-features-coming-soon",
            "content": "Preview of upcoming features and improvements.",
            "excerpt": "Sneak peek at future updates",
            "author": users[0],
            "is_published": False  # Draft
        },
        {
            "title": "Community Tournament Results",
            "slug": "community-tournament-results",
            "content": "Results and highlights from the recent community tournament.",
            "excerpt": "Tournament winners and memorable moments",
            "author": users[2],
            "is_published": True
        }
    ]

    posts = []
    for post_data in posts_data:
        post = BlogPost.query.filter_by(slug=post_data["slug"]).first()
        if not post:
            post = BlogPost(
                title=post_data["title"],
                slug=post_data["slug"],
                content=post_data["content"],
                excerpt=post_data["excerpt"],
                author_id=post_data["author"].id,
                is_published=post_data["is_published"]
            )
            db.session.add(post)
            posts.append(post)

    db.session.commit()
    print(f"Created {len(posts)} blog posts")


def main():
    """Main seeding function"""
    print("?? Starting database seeding...")

    # Create Flask app context
    app = create_app()
    with app.app_context():
        try:
            # Create sample data
            users = create_sample_users()
            servers = create_sample_servers(users)
            groups = create_sample_user_groups(users)
            create_sample_forum_content(users)
            create_sample_blog_posts(users)

            print("? Database seeding completed successfully!")
            print(f"   - {len(users)} users created")
            print(f"   - {len(servers)} servers created")
            print(f"   - {len(groups)} user groups created")
            print("   - Forum threads and posts created")
            print("   - Blog posts created")

            print("\n?? Sample login credentials:")
            for user in users[:5]:  # Show first 5 users
                print(f"   {user.email}: password123 (role: {user.role})")

        except Exception as e:
            print(f"? Error during seeding: {e}")
            db.session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    main()
