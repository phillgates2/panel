#!/usr/bin/env python3
"""
RBAC Migration Script

This script helps migrate existing users from the simple role system
to the advanced RBAC system.

Usage:
    python rbac_migrate.py

Requirements:
    - Flask application context
    - Existing users with simple roles
    - RBAC system initialized
"""

import os
import sys

# Add the panel directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def migrate_users_to_rbac():
    """Migrate existing users to RBAC roles based on their current simple roles."""

    # Import here to avoid import errors if Flask isn't available
    try:
        from app import User, app, db
        from rbac import Role, UserRole, has_permission, initialize_rbac_system

        print("✓ Imports successful")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure Flask and dependencies are installed")
        return False

    # Create application context
    with app.app_context():
        # Initialize RBAC system if not already done
        try:
            print("Initializing RBAC system...")
            initialize_rbac_system()
            print("✓ RBAC system initialized")
        except Exception as e:
            print(f"✗ Failed to initialize RBAC: {e}")
            return False

        # Get default roles
        super_admin_role = Role.query.filter_by(name="Super Administrator").first()
        admin_role = Role.query.filter_by(name="Administrator").first()
        server_manager_role = Role.query.filter_by(name="Server Manager").first()
        user_role = Role.query.filter_by(name="User").first()

        if not all([super_admin_role, admin_role, server_manager_role, user_role]):
            print("✗ Default roles not found. Make sure RBAC is properly initialized.")
            return False

        # Migrate users
        users = User.query.all()
        migrated_count = 0

        print(f"\nMigrating {len(users)} users to RBAC...")

        for user in users:
            assigned_roles = []

            # Check current simple roles and assign appropriate RBAC roles
            if user.role == "system_admin":
                # System admins get Super Administrator role
                if not UserRole.query.filter_by(
                    user_id=user.id, role_id=super_admin_role.id
                ).first():
                    user_role_assignment = UserRole(
                        user_id=user.id,
                        role_id=super_admin_role.id,
                        assigned_by=user.id,  # Self-assigned during migration
                    )
                    db.session.add(user_role_assignment)
                    assigned_roles.append("Super Administrator")
                    print(f"  → {user.email}: Assigned Super Administrator")

            elif user.role == "server_admin":
                # Server admins get Administrator role
                if not UserRole.query.filter_by(user_id=user.id, role_id=admin_role.id).first():
                    user_role_assignment = UserRole(
                        user_id=user.id, role_id=admin_role.id, assigned_by=user.id
                    )
                    db.session.add(user_role_assignment)
                    assigned_roles.append("Administrator")
                    print(f"  → {user.email}: Assigned Administrator")

            elif user.role == "server_mod":
                # Server mods get Server Manager role
                if not UserRole.query.filter_by(
                    user_id=user.id, role_id=server_manager_role.id
                ).first():
                    user_role_assignment = UserRole(
                        user_id=user.id, role_id=server_manager_role.id, assigned_by=user.id
                    )
                    db.session.add(user_role_assignment)
                    assigned_roles.append("Server Manager")
                    print(f"  → {user.email}: Assigned Server Manager")

            else:
                # Regular users get User role
                if not UserRole.query.filter_by(user_id=user.id, role_id=user_role.id).first():
                    user_role_assignment = UserRole(
                        user_id=user.id, role_id=user_role.id, assigned_by=user.id
                    )
                    db.session.add(user_role_assignment)
                    assigned_roles.append("User")
                    print(f"  → {user.email}: Assigned User")

            if assigned_roles:
                migrated_count += 1

        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✓ Migration completed successfully!")
            print(f"  → {migrated_count} users migrated")
            print(f"  → {len(users)} total users processed")

            # Show role distribution
            print("\nRole Distribution:")
            for role_name in ["Super Administrator", "Administrator", "Server Manager", "User"]:
                role = Role.query.filter_by(name=role_name).first()
                if role:
                    count = role.user_roles.count()
                    print(f"  → {role_name}: {count} users")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Migration failed: {e}")
            return False


def verify_migration():
    """Verify that the migration was successful."""
    print("\nVerifying migration...")

    try:
        from app import User, app, db
        from rbac import has_permission

        with app.app_context():
            # Test a few key permissions
            users = User.query.limit(5).all()

            for user in users:
                print(f"\nTesting user: {user.email}")
                print(f"  Simple role: {user.role}")

                # Test some key permissions
                permissions_to_test = [
                    "user.view_own",
                    "server.view_assigned",
                    "monitor.view_system",
                    "admin.user_management",
                ]

                for perm in permissions_to_test:
                    has_perm = has_permission(user, perm)
                    status = "✓" if has_perm else "✗"
                    print(f"  {status} {perm}")

        print("\n✓ Verification completed")

    except Exception as e:
        print(f"✗ Verification failed: {e}")


def main():
    """Main migration function."""
    print("Panel RBAC Migration Script")
    print("=" * 40)

    # Run migration
    success = migrate_users_to_rbac()

    if success:
        # Run verification
        verify_migration()

        print("\n" + "=" * 40)
        print("Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the RBAC system in the web interface")
        print("2. Update your code to use RBAC permission checks")
        print("3. Review and adjust user roles as needed")
        print("4. Consider removing old simple role checks over time")
    else:
        print("\nMigration failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
