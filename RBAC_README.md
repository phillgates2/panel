# Advanced Role-Based Access Control (RBAC) System

The Panel now includes a comprehensive RBAC system that provides enterprise-grade access control with granular permissions, role inheritance, and flexible user management.

## Overview

The RBAC system consists of:
- **Permissions**: Individual access rights (e.g., "server.create", "admin.user_management")
- **Roles**: Collections of permissions assigned to users
- **Users**: Individuals with assigned roles and optional permission overrides
- **Permission Groups**: Predefined sets of related permissions

## Default Permissions

### System Administration
- `admin.full_access` - Complete system control
- `admin.user_management` - Manage users and roles
- `admin.system_config` - Modify system settings
- `admin.view_logs` - Access system logs
- `admin.backup_restore` - Perform backups and restores

### User Management
- `user.create` - Create new users
- `user.edit` - Edit user profiles
- `user.delete` - Delete users
- `user.view_all` - View all user profiles
- `user.view_own` - View own profile
- `user.change_password` - Change passwords

### Server Management
- `server.create` - Create game servers
- `server.edit` - Edit server configurations
- `server.delete` - Delete servers
- `server.start_stop` - Start/stop servers
- `server.view_all` - View all servers
- `server.view_assigned` - View assigned servers
- `server.rcon` - Execute RCON commands

### Monitoring
- `monitor.view_system` - System monitoring dashboard
- `monitor.view_metrics` - Detailed metrics
- `monitor.view_logs` - Application logs

### Security
- `security.view_audit` - Audit logs
- `security.manage_sessions` - User sessions
- `security.manage_api_keys` - API key management
- `security.two_factor` - 2FA management

### Player Management
- `player.view` - Player information
- `player.ban` - Ban/unban players
- `player.kick` - Kick players
- `player.moderate` - Moderate chat/behavior

## Default Roles

### Super Administrator
**Full system access** - All permissions
- Complete control over the entire system
- Cannot be deleted or modified

### Administrator
**System administration** - Most admin permissions
- User and role management
- Server management
- System monitoring
- Security management

### Server Manager
**Game server management**
- Create and manage game servers
- RCON access to assigned servers
- Player management
- Basic monitoring

### User
**Basic user access**
- View own profile
- Access assigned servers
- Basic system features

## Getting Started

### 1. Initialize RBAC System

As a system administrator:

1. Go to **RBAC** in the navigation menu
2. Click **"Initialize RBAC"** button
3. This creates all default permissions and roles

### 2. Assign Roles to Users

1. Go to **RBAC → User Management**
2. Select a user
3. Assign appropriate roles
4. Set expiration dates if needed

### 3. Create Custom Roles

1. Go to **RBAC → Role Management**
2. Click **"Create Role"**
3. Select permissions for the role
4. Assign users to the new role

## Permission Checking in Code

The RBAC system provides several ways to check permissions:

### Basic Permission Check
```python
from rbac import has_permission

if has_permission(user, "server.create"):
    # User can create servers
    pass
```

### Get All User Permissions
```python
from rbac import get_user_permissions

user_perms = get_user_permissions(user)
if "admin.full_access" in user_perms:
    # User has full access
    pass
```

### Role-Based Checks
```python
# Check if user has a specific role
user_roles = [ur.role.name for ur in user.user_roles]
if "Administrator" in user_roles:
    # User is an administrator
    pass
```

## Advanced Features

### Permission Overrides
Individual users can have permission overrides that grant or deny specific permissions regardless of their roles.

### Role Expiration
Roles can be assigned with expiration dates for temporary access.

### Role Inheritance
Roles can inherit permissions from parent roles (planned feature).

### Permission Groups
Permissions can be organized into groups for easier management.

## API Integration

The RBAC system integrates with the REST API:

```bash
# Check user permissions via API
GET /api/v1/users/{id}/permissions

# Assign roles via API
POST /api/v1/users/{id}/roles
```

## Migration from Simple Roles

The system maintains backward compatibility with the old simple role system (`system_admin`, `server_admin`, etc.) while providing the advanced RBAC features.

### Migration Steps

1. **Initialize RBAC** - Creates default roles and permissions
2. **Map Existing Users** - Automatically assigns appropriate roles based on current simple roles
3. **Update Code** - Gradually replace simple role checks with RBAC permission checks
4. **Test Access** - Verify that all users have appropriate access levels

## Best Practices

### Role Design
- **Principle of Least Privilege**: Give users only the permissions they need
- **Role Separation**: Separate administrative roles from operational roles
- **Regular Audits**: Periodically review user roles and permissions

### Permission Management
- **Descriptive Names**: Use clear, descriptive permission names
- **Logical Grouping**: Group related permissions by category
- **Documentation**: Document what each permission allows

### Security Considerations
- **Regular Reviews**: Review user access regularly
- **Expiration Dates**: Use role expiration for temporary access
- **Audit Logging**: All role and permission changes are logged

## Troubleshooting

### Common Issues

**"Permission denied" errors**
- Check if user has the required permission
- Verify role assignments are active (not expired)
- Check for permission overrides

**RBAC not working**
- Ensure RBAC system is initialized
- Check database tables exist
- Verify user-role assignments

**Performance issues**
- RBAC checks are cached where possible
- Consider permission grouping for complex permission sets

## API Reference

### Permissions
```python
# Check permission
has_permission(user, "permission.name")

# Get all user permissions
get_user_permissions(user)

# Get role permissions
get_role_permissions(role)
```

### Roles
```python
# Assign role to user
assign_role_to_user(user, role, assigned_by=current_user)

# Remove role from user
revoke_role_from_user(user, role)

# Create new role
role = Role(name="Custom Role", description="Custom permissions")
```

### Management
```python
# Initialize system
initialize_rbac_system()

# Create custom permissions
permission = Permission(name="custom.action", description="Custom action", category="custom")
```

## Support

For RBAC system support:
- Check the RBAC management interface (`/admin/rbac/roles`)
- Review the audit logs for permission changes
- Test with different user accounts to verify access levels

The RBAC system provides enterprise-grade access control while maintaining ease of use for administrators.