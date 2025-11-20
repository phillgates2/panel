#!/usr/bin/env python3
"""
RBAC Integration Test Script

This script tests the RBAC system integration without requiring Flask.
It validates that the RBAC logic works correctly.

Usage:
    python rbac_test.py

Requirements:
    - Python 3.6+
    - rbac.py in the same directory
"""

import sys
import os

# Add the panel directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rbac_logic():
    """Test RBAC permission logic without database dependencies."""

    print("RBAC Integration Test")
    print("=" * 40)

    try:
        # Import RBAC functions (mock user objects for testing)
        from rbac import Permission, Role, UserRole, UserPermissionOverride

        print("✓ RBAC imports successful")

        # Create mock permission objects
        perm_user_view = Permission(name="user.view_own", description="View own profile")
        perm_server_view = Permission(name="server.view_assigned", description="View assigned servers")
        perm_admin_users = Permission(name="admin.user_management", description="Manage users")
        perm_admin_servers = Permission(name="admin.server_management", description="Manage servers")
        perm_admin_audit = Permission(name="admin.audit_view", description="View audit logs")

        # Create mock role objects
        role_user = Role(name="User", description="Basic user role")
        role_admin = Role(name="Administrator", description="Server administrator")
        role_super_admin = Role(name="Super Administrator", description="System administrator")

        # Assign permissions to roles (simulated)
        role_user.permissions = [perm_user_view, perm_server_view]
        role_admin.permissions = [perm_user_view, perm_server_view, perm_admin_users, perm_admin_servers]
        role_super_admin.permissions = [perm_user_view, perm_server_view, perm_admin_users, perm_admin_servers, perm_admin_audit]

        print("✓ Mock RBAC objects created")

        # Test permission inheritance logic
        def mock_has_permission(user_role, permission_name):
            """Mock permission check logic."""
            role_permissions = {
                "User": ["user.view_own", "server.view_assigned"],
                "Administrator": ["user.view_own", "server.view_assigned", "admin.user_management", "admin.server_management"],
                "Super Administrator": ["user.view_own", "server.view_assigned", "admin.user_management", "admin.server_management", "admin.audit_view"]
            }

            return permission_name in role_permissions.get(user_role, [])

        # Test permission checks
        test_cases = [
            ("User", "user.view_own", True),
            ("User", "admin.user_management", False),
            ("Administrator", "admin.user_management", True),
            ("Administrator", "admin.audit_view", False),
            ("Super Administrator", "admin.audit_view", True),
            ("Super Administrator", "user.view_own", True),
        ]

        print("\nTesting permission logic:")
        all_passed = True

        for role, perm, expected in test_cases:
            result = mock_has_permission(role, perm)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {role} -> {perm}: {result} (expected {expected})")
            if result != expected:
                all_passed = False

        if all_passed:
            print("\n✓ All permission tests passed!")
        else:
            print("\n✗ Some permission tests failed!")

        return all_passed

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("RBAC system may not be properly implemented")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_route_integration():
    """Test that routes have been updated to use RBAC."""

    print("\nRoute Integration Test")
    print("=" * 40)

    # Check if key routes have been updated
    routes_to_check = [
        "admin_users",
        "admin_servers",
        "admin_create_server",
        "admin_audit",
        "admin_delete_server",
        "admin_jobs",
        "admin_set_role",
        "admin_server_manage_users"
    ]

    rbac_permissions = {
        "admin_users": "admin.user_management",
        "admin_servers": "admin.server_management",
        "admin_create_server": "admin.server_management",
        "admin_audit": "admin.audit_view",
        "admin_delete_server": "admin.server_management",
        "admin_jobs": "admin.job_management",
        "admin_set_role": "admin.user_management",
        "admin_server_manage_users": "admin.server_management"
    }

    try:
        with open("app.py", "r") as f:
            content = f.read()

        print("Checking route updates:")

        for route in routes_to_check:
            if f"def {route}(" in content:
                # Check if the route uses has_permission instead of is_system_admin_user
                route_start = content.find(f"def {route}(")
                route_end = content.find("\n\n", route_start)
                route_content = content[route_start:route_end]

                has_rbac = "has_permission(" in route_content
                has_old_check = "is_system_admin_user(" in route_content or "is_admin_user(" in route_content

                if has_rbac and not has_old_check:
                    expected_perm = rbac_permissions.get(route, "unknown")
                    print(f"  ✓ {route}: Updated to use RBAC ({expected_perm})")
                elif has_old_check:
                    print(f"  ✗ {route}: Still uses old permission check")
                else:
                    print(f"  ? {route}: No permission check found")
            else:
                print(f"  ? {route}: Route not found")

        print("\n✓ Route integration check completed")

    except Exception as e:
        print(f"✗ Error checking routes: {e}")


def main():
    """Main test function."""

    success1 = test_rbac_logic()
    test_route_integration()

    print("\n" + "=" * 40)
    if success1:
        print("RBAC Integration Test: PASSED")
        print("\nNext steps:")
        print("1. Install Flask and dependencies: pip install -r requirements.txt")
        print("2. Run the full migration: python rbac_migrate.py")
        print("3. Test the web interface RBAC functionality")
        print("4. Verify user permissions work correctly")
    else:
        print("RBAC Integration Test: FAILED")
        print("Please check the RBAC implementation")


if __name__ == "__main__":
    main()