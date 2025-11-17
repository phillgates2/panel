"""
Advanced Role-Based Access Control (RBAC) System

This module provides comprehensive role and permission management
for enterprise-grade access control.
"""

from datetime import datetime, timezone
from app import db
import json


class Permission(db.Model):
    """Individual permissions that can be granted to roles."""
    __tablename__ = 'permission'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True, index=True)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(32), nullable=False, index=True)  # admin, user, server, etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Role(db.Model):
    """User roles with associated permissions."""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    is_system_role = db.Column(db.Boolean, default=False)  # Cannot be deleted
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RolePermission(db.Model):
    """Many-to-many relationship between roles and permissions."""
    __tablename__ = 'role_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id', name='_role_permission_uc'),)
    
    role = db.relationship('Role', backref=db.backref('role_permissions', lazy='dynamic'))
    permission = db.relationship('Permission', backref=db.backref('role_permissions', lazy='dynamic'))


class UserRole(db.Model):
    """Many-to-many relationship between users and roles."""
    __tablename__ = 'user_role'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional role expiration
    
    __table_args__ = (db.UniqueConstraint('user_id', 'role_id', name='_user_role_uc'),)
    
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('user_roles', lazy='dynamic'))
    role = db.relationship('Role', backref=db.backref('user_roles', lazy='dynamic'))
    assigner = db.relationship('User', foreign_keys=[assigned_by])


class PermissionGroup(db.Model):
    """Groups of permissions for easier management."""
    __tablename__ = 'permission_group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    permissions = db.Column(db.Text, nullable=True)  # JSON list of permission names
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class RoleHierarchy(db.Model):
    """Role inheritance hierarchy."""
    __tablename__ = 'role_hierarchy'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    child_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('parent_role_id', 'child_role_id', name='_role_hierarchy_uc'),)
    
    parent_role = db.relationship('Role', foreign_keys=[parent_role_id])
    child_role = db.relationship('Role', foreign_keys=[child_role_id])


class UserPermissionOverride(db.Model):
    """Individual permission overrides for specific users."""
    __tablename__ = 'user_permission_override'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), nullable=False)
    granted = db.Column(db.Boolean, nullable=False)  # True=grant, False=deny
    reason = db.Column(db.String(255), nullable=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'permission_id', name='_user_permission_override_uc'),)
    
    user = db.relationship('User', foreign_keys=[user_id])
    permission = db.relationship('Permission')
    granter = db.relationship('User', foreign_keys=[granted_by])


# Permission checking helper functions
def has_permission(user, permission_name):
    """Check if user has a specific permission."""
    if not user:
        return False
    
    # Check user permission overrides first
    override = UserPermissionOverride.query.filter_by(
        user_id=user.id
    ).join(Permission).filter(Permission.name == permission_name).first()
    
    if override:
        # Check if override is still valid
        if override.expires_at is None or override.expires_at > datetime.now(timezone.utc):
            return override.granted
    
    # Check role-based permissions
    user_permissions = get_user_permissions(user)
    return permission_name in user_permissions


def get_user_permissions(user):
    """Get all permissions for a user (including inherited)."""
    if not user:
        return set()
    
    permissions = set()
    
    # Get direct role permissions
    for user_role in user.user_roles:
        # Check if role assignment is still valid
        if user_role.expires_at is None or user_role.expires_at > datetime.now(timezone.utc):
            role_permissions = get_role_permissions(user_role.role)
            permissions.update(role_permissions)
    
    return permissions


def get_role_permissions(role, visited_roles=None):
    """Get all permissions for a role (including inherited from parent roles)."""
    if visited_roles is None:
        visited_roles = set()
    
    if role.id in visited_roles:
        return set()  # Prevent circular inheritance
    
    visited_roles.add(role.id)
    permissions = set()
    
    # Direct permissions
    for role_perm in role.role_permissions:
        permissions.add(role_perm.permission.name)
    
    # Inherited permissions from parent roles
    parent_roles = RoleHierarchy.query.filter_by(child_role_id=role.id).all()
    for hierarchy in parent_roles:
        parent_permissions = get_role_permissions(hierarchy.parent_role, visited_roles.copy())
        permissions.update(parent_permissions)
    
    return permissions


def assign_role_to_user(user_id, role_id, assigned_by_id, expires_at=None):
    """Assign a role to a user."""
    existing = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
    
    if existing:
        # Update existing assignment
        existing.assigned_by = assigned_by_id
        existing.assigned_at = datetime.now(timezone.utc)
        existing.expires_at = expires_at
    else:
        # Create new assignment
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by_id,
            expires_at=expires_at
        )
        db.session.add(user_role)
    
    db.session.commit()


def revoke_role_from_user(user_id, role_id):
    """Revoke a role from a user."""
    user_role = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
    
    if user_role:
        db.session.delete(user_role)
        db.session.commit()
        return True
    
    return False


def create_default_permissions():
    """Create default system permissions."""
    default_permissions = [
        # System Administration
        ('admin.full_access', 'Full system administration access', 'admin'),
        ('admin.user_management', 'Manage users and roles', 'admin'),
        ('admin.system_config', 'Modify system configuration', 'admin'),
        ('admin.view_logs', 'View system logs and audit trails', 'admin'),
        ('admin.backup_restore', 'Perform backups and restores', 'admin'),
        
        # User Management
        ('user.create', 'Create new users', 'user'),
        ('user.edit', 'Edit user profiles', 'user'),
        ('user.delete', 'Delete users', 'user'),
        ('user.view_all', 'View all user profiles', 'user'),
        ('user.view_own', 'View own profile', 'user'),
        ('user.change_password', 'Change user passwords', 'user'),
        
        # Server Management
        ('server.create', 'Create new game servers', 'server'),
        ('server.edit', 'Edit server configurations', 'server'),
        ('server.delete', 'Delete game servers', 'server'),
        ('server.start_stop', 'Start/stop game servers', 'server'),
        ('server.view_all', 'View all servers', 'server'),
        ('server.view_assigned', 'View assigned servers', 'server'),
        ('server.rcon', 'Execute RCON commands', 'server'),
        
        # Monitoring
        ('monitor.view_system', 'View system monitoring dashboard', 'monitor'),
        ('monitor.view_metrics', 'View detailed system metrics', 'monitor'),
        ('monitor.view_logs', 'View application logs', 'monitor'),
        
        # Security
        ('security.view_audit', 'View audit logs', 'security'),
        ('security.manage_sessions', 'Manage user sessions', 'security'),
        ('security.manage_api_keys', 'Manage API keys', 'security'),
        ('security.two_factor', 'Manage two-factor authentication', 'security'),
        
        # Player Management
        ('player.view', 'View player information', 'player'),
        ('player.ban', 'Ban/unban players', 'player'),
        ('player.kick', 'Kick players from servers', 'player'),
        ('player.moderate', 'Moderate player chat and behavior', 'player'),
    ]
    
    for name, desc, category in default_permissions:
        existing = Permission.query.filter_by(name=name).first()
        if not existing:
            permission = Permission(name=name, description=desc, category=category)
            db.session.add(permission)
    
    db.session.commit()


def create_default_roles():
    """Create default system roles."""
    default_roles = [
        ('Super Administrator', 'Full system access', True, [
            'admin.full_access'
        ]),
        ('Administrator', 'System administration with limited access', True, [
            'admin.user_management', 'admin.view_logs', 'admin.backup_restore',
            'user.create', 'user.edit', 'user.delete', 'user.view_all', 'user.change_password',
            'server.create', 'server.edit', 'server.delete', 'server.start_stop', 'server.view_all', 'server.rcon',
            'monitor.view_system', 'monitor.view_metrics', 'monitor.view_logs',
            'security.view_audit', 'security.manage_sessions', 'security.manage_api_keys',
            'player.view', 'player.ban', 'player.kick', 'player.moderate'
        ]),
        ('Server Manager', 'Game server management', False, [
            'user.view_own',
            'server.create', 'server.edit', 'server.start_stop', 'server.view_assigned', 'server.rcon',
            'monitor.view_system', 'monitor.view_metrics',
            'player.view', 'player.kick', 'player.moderate'
        ]),
        ('Moderator', 'Player and chat moderation', False, [
            'user.view_own',
            'server.view_assigned',
            'monitor.view_system',
            'player.view', 'player.kick', 'player.moderate'
        ]),
        ('User', 'Basic user access', True, [
            'user.view_own',
            'server.view_assigned'
        ])
    ]
    
    for name, desc, is_system, permission_names in default_roles:
        existing = Role.query.filter_by(name=name).first()
        if not existing:
            role = Role(name=name, description=desc, is_system_role=is_system)
            db.session.add(role)
            db.session.flush()
            
            # Add permissions to role
            for perm_name in permission_names:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                    db.session.add(role_perm)
    
    db.session.commit()


def initialize_rbac_system():
    """Initialize the RBAC system with default permissions and roles."""
    create_default_permissions()
    create_default_roles()
    print("RBAC system initialized successfully")