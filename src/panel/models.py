"""Database models for the Panel application."""

import json
from datetime import datetime, timedelta, timezone
from typing import List

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# Try to import config for admin emails check
try:
    from flask import current_app

    def get_config():
        return current_app.config

except ImportError:
    # Fallback if Flask not available
    def get_config():
        return {}


# Role hierarchy definitions (5-tier system)
ROLE_HIERARCHY = {
    "user": 1,  # Basic user
    "premium": 2,  # Premium user with extra features
    "moderator": 3,  # Forum moderator
    "admin": 4,  # Server administrator
    "system_admin": 5,  # System administrator (full access)
}

ROLE_PERMISSIONS = {
    "user": [
        "view_forum",
        "create_posts",
        "view_blog",
        "view_profile",
        "edit_own_profile",
        "use_api_basic",
        "view_public_content",
    ],
    "premium": [
        "view_forum",
        "create_posts",
        "view_blog",
        "view_profile",
        "edit_own_profile",
        "use_api_basic",
        "view_public_content",
        "premium_features",
        "create_blog_posts",
        "upload_files",
        "advanced_search",
        "priority_support",
    ],
    "moderator": [
        "view_forum",
        "create_posts",
        "view_blog",
        "view_profile",
        "edit_own_profile",
        "use_api_basic",
        "view_public_content",
        "moderate_forum",
        "edit_posts",
        "delete_posts",
        "ban_users",
        "view_user_activity",
        "manage_categories",
        "moderate_chat",
    ],
    "admin": [
        "view_forum",
        "create_posts",
        "view_blog",
        "view_profile",
        "edit_own_profile",
        "use_api_basic",
        "view_public_content",
        "moderate_forum",
        "edit_posts",
        "delete_posts",
        "ban_users",
        "view_user_activity",
        "manage_categories",
        "moderate_chat",
        "manage_servers",
        "view_admin",
        "manage_users",
        "view_analytics",
        "manage_backups",
        "configure_system",
        "manage_api_keys",
    ],
    "system_admin": [
        "view_forum",
        "create_posts",
        "view_blog",
        "view_profile",
        "edit_own_profile",
        "use_api_basic",
        "view_public_content",
        "moderate_forum",
        "edit_posts",
        "delete_posts",
        "ban_users",
        "view_user_activity",
        "manage_categories",
        "moderate_chat",
        "manage_servers",
        "view_admin",
        "manage_users",
        "view_analytics",
        "manage_backups",
        "configure_system",
        "manage_api_keys",
        "system_config",
        "user_management",
        "audit_logs",
        "security_settings",
        "database_admin",
        "system_monitoring",
        "emergency_shutdown",
    ],
}


class User(db.Model):
    """User model representing application users with authentication and authorization."""

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(32), default="user")

    # Two-Factor Authentication
    totp_secret = db.Column(db.String(32), nullable=True)  # TOTP secret for 2FA
    totp_enabled = db.Column(db.Boolean, default=False)  # Whether 2FA is enabled
    backup_codes = db.Column(db.Text, nullable=True)  # JSON array of backup codes

    # API Access
    api_token = db.Column(
        db.String(128), nullable=True, unique=True
    )  # API access token
    api_token_created = db.Column(db.DateTime, nullable=True)  # When token was created
    api_token_last_used = db.Column(db.DateTime, nullable=True)  # Last API usage

    # Session management
    last_login = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Profile
    bio = db.Column(db.Text, nullable=True)  # User biography
    avatar = db.Column(db.String(255), nullable=True)  # Avatar image filename

    # OAuth 2.0 Social Login
    oauth_provider = db.Column(
        db.String(32), nullable=True
    )  # 'google', 'github', 'discord'
    oauth_id = db.Column(
        db.String(128), nullable=True, unique=True
    )  # Provider's user ID
    oauth_token = db.Column(db.Text, nullable=True)  # Access token (encrypted)
    oauth_refresh_token = db.Column(db.Text, nullable=True)  # Refresh token (encrypted)
    oauth_token_expires = db.Column(db.DateTime, nullable=True)  # Token expiration

    __table_args__ = (
        db.Index("idx_user_email", "email"),
        db.Index("idx_user_role", "role"),
        db.Index("idx_user_oauth", "oauth_provider", "oauth_id"),
    )

    def set_password(self, password: str) -> None:
        """Set user password with complexity validation."""
        self._validate_password_complexity(password)
        self.password_hash = generate_password_hash(password)

    @staticmethod
    def _validate_password_complexity(password: str) -> None:
        """Validate password complexity requirements"""
        import re

        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValueError("Password must contain at least one special character")
        # Check for common weak passwords
        weak_passwords = [
            "password",
            "123456",
            "qwerty",
            "admin",
            "letmein",
            "password123",
        ]
        if password.lower() in weak_passwords:
            raise ValueError(
                "Password is too common, please choose a stronger password"
            )

    def check_password(self, password: str) -> bool:
        """Check the user's password."""
        return check_password_hash(self.password_hash, password)

    def is_account_locked(self) -> bool:
        """Check if account is temporarily locked due to failed login attempts."""
        if self.locked_until and datetime.now(timezone.utc) < self.locked_until:
            return True
        return False

    def record_login_attempt(self, success: bool = False) -> None:
        """Record a login attempt and handle account locking."""
        if success:
            self.login_attempts = 0
            self.locked_until = None
            self.last_login = datetime.now(timezone.utc)
        else:
            self.login_attempts += 1
            if self.login_attempts >= 5:  # Lock after 5 failed attempts
                self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def verify_totp(self, code: str) -> bool:
        """Verify TOTP code for 2FA."""
        if not self.totp_enabled or not self.totp_secret:
            return True  # 2FA not enabled

        try:
            import pyotp

            totp = pyotp.TOTP(self.totp_secret)
            return totp.verify(code)
        except Exception:
            return False

    def generate_backup_codes(self) -> List[str]:
        """Generate new backup codes for account recovery."""
        import secrets

        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        self.backup_codes = json.dumps(codes)
        return codes

    def use_backup_code(self, code: str) -> bool:
        """Use a backup code and remove it from the list."""
        if not self.backup_codes:
            return False

        try:
            codes = json.loads(self.backup_codes)
            if code in codes:
                codes.remove(code)
                self.backup_codes = json.dumps(codes) if codes else None
                return True
        except Exception:
            pass
        return False

    @property
    def display_name(self) -> str:
        """Return full name or email as display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def is_system_admin(self) -> bool:
        return (self.role == "system_admin") or (
            self.email.lower() in get_config().get("ADMIN_EMAILS", [])
        )

    def is_server_admin(self) -> bool:
        return self.role == "admin" or self.role == "system_admin"

    def is_server_mod(self) -> bool:
        return (
            self.role == "moderator"
            or self.role == "admin"
            or self.role == "system_admin"
        )

    def get_role_level(self) -> int:
        """Get the numeric level of the user's role"""
        return ROLE_HIERARCHY.get(self.role, 1)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        user_permissions = ROLE_PERMISSIONS.get(self.role, [])
        return permission in user_permissions

    def can_access_role(self, required_role: str) -> bool:
        """Check if user can access features requiring a certain role level"""
        required_level = ROLE_HIERARCHY.get(required_role, 1)
        return self.get_role_level() >= required_level

    def can_perform_action(self, action: str, resource: str = None) -> bool:
        """Check if user can perform a specific action, optionally on a resource"""
        base_permission = self.has_permission(action)
        if not base_permission:
            return False

        # Additional checks based on resource
        if resource:
            if action == "edit_posts" and resource == "own":
                return True  # Users can edit their own posts
            elif action == "manage_servers" and resource:
                # Check if user owns or is assigned to the server
                return self.is_server_admin() or self.is_server_mod()
            elif action == "view_user_activity" and resource:
                # Admins can view anyone's activity, mods can view non-admin activity
                if self.is_system_admin():
                    return True
                elif (
                    self.is_server_admin()
                    and not User.query.get(int(resource)).is_system_admin()
                ):
                    return True
                return False

        return True

    def get_available_permissions(self) -> List[str]:
        """Get all permissions available to the user's role"""
        return ROLE_PERMISSIONS.get(self.role, [])

    def can_grant_role(self, target_role: str) -> bool:
        """Check if user can grant a specific role to others"""
        user_level = self.get_role_level()
        target_level = ROLE_HIERARCHY.get(target_role, 1)
        return user_level > target_level and self.has_permission("user_management")

    def can_revoke_role(self, target_user_role: str) -> bool:
        """Check if user can revoke a specific role from others"""
        return self.can_grant_role(target_user_role)  # Same logic as granting

    def get_max_grantable_role(self) -> str:
        """Get the highest role this user can grant"""
        user_level = self.get_role_level()
        if user_level <= 1:
            return None
        # Can grant roles one level below
        for role, level in ROLE_HIERARCHY.items():
            if level == user_level - 1:
                return role
        return None

    def generate_api_token(self) -> str:
        """Generate a new API token for the user."""
        import secrets

        self.api_token = secrets.token_urlsafe(64)
        self.api_token_created = datetime.now(timezone.utc)
        return self.api_token

    def revoke_api_token(self) -> None:
        """Revoke the current API token."""
        self.api_token = None
        self.api_token_created = None
        self.api_token_last_used = None

    def validate_api_token(self, token: str) -> bool:
        """Validate an API token and update last used time."""
        if self.api_token and self.api_token == token:
            self.api_token_last_used = datetime.now(timezone.utc)
            return True
        return False

    def generate_password_reset_token(self) -> str:
        """Generate a secure password reset token"""
        import secrets

        self.reset_token = secrets.token_urlsafe(64)
        return self.reset_token

    def validate_password_reset_token(self, token: str) -> bool:
        """Validate password reset token and clear it"""
        if self.reset_token and self.reset_token == token:
            self.reset_token = None
            return True
        return False

    def link_oauth_account(
        self,
        provider: str,
        provider_id: str,
        access_token: str = None,
        refresh_token: str = None,
        expires_at: datetime = None,
    ) -> None:
        """Link OAuth account to user"""
        self.oauth_provider = provider
        self.oauth_id = provider_id
        if access_token:
            # In production, encrypt these tokens
            self.oauth_token = access_token
        if refresh_token:
            self.oauth_refresh_token = refresh_token
        if expires_at:
            self.oauth_token_expires = expires_at

    def unlink_oauth_account(self) -> None:
        """Unlink OAuth account"""
        self.oauth_provider = None
        self.oauth_id = None
        self.oauth_token = None
        self.oauth_refresh_token = None
        self.oauth_token_expires = None

    @classmethod
    def find_by_oauth(cls, provider: str, provider_id: str):
        """Find user by OAuth provider and ID"""
        return cls.query.filter_by(
            oauth_provider=provider, oauth_id=provider_id
        ).first()

    @property
    def has_oauth_linked(self) -> bool:
        """Check if user has OAuth account linked"""
        return self.oauth_provider is not None


# Association table: server-specific roles for users (server_admin/server_mod)
class ServerUser(db.Model):
    """Association table for server-specific roles for users."""

    __tablename__ = "server_user"
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # 'server_admin' or 'server_mod'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("server_id", "user_id", name="_server_user_uc"),
    )


class Server(db.Model):
    """Server model representing game servers."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(512), nullable=True)
    host = db.Column(db.String(128), nullable=True)  # server host/IP
    port = db.Column(db.Integer, nullable=True)  # server port
    rcon_password = db.Column(db.String(128), nullable=True)  # RCON password
    variables_json = db.Column(db.Text, nullable=True)  # structured variables (JSON)
    raw_config = db.Column(db.Text, nullable=True)  # raw server config
    game_type = db.Column(
        db.String(32), default="etlegacy", nullable=False
    )  # game type for configs
    owner_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )  # server owner
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    users = db.relationship(
        "ServerUser", backref="server", cascade="all, delete-orphan"
    )
    owner = db.relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        db.Index("idx_server_name", "name"),
        db.Index("idx_server_owner", "owner_id"),
    )


class AuditLog(db.Model):
    """Audit log for tracking user actions and system events."""

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(1024), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_audit_actor", "actor_id"),
        db.Index("idx_audit_created", "created_at"),
    )


class SiteSetting(db.Model):
    """Simple key/value storage for site-wide settings.

    Keys used:
        - 'custom_theme_css' : text containing CSS
        - 'theme_enabled' : '1' or '0'
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    __table_args__ = (db.Index("idx_site_setting_key", "key"),)


class SiteAsset(db.Model):
    """Store uploaded theme assets (logos) in DB when configured.

    Fields:
        - filename: sanitized filename used in URL
        - data: binary blob
        - mimetype: original/derived mimetype
        - created_at
    """

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), unique=True, nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    mimetype = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class IPWhitelist(db.Model):
    """IP addresses allowed to access the system."""

    __tablename__ = "ip_whitelist"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(
        db.String(45), nullable=False, unique=True
    )  # IPv4/IPv6 support
    description = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    creator = db.relationship("User")


class IPBlacklist(db.Model):
    """IP addresses blocked from accessing the system."""

    __tablename__ = "ip_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(
        db.String(45), nullable=False, unique=True
    )  # IPv4/IPv6 support
    reason = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    creator = db.relationship("User")


class SecurityEvent(db.Model):
    """Log security-related events."""

    __tablename__ = "security_event"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(
        db.String(64), nullable=False
    )  # login_attempt, ip_blocked, etc.
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(16), default="info")  # info, warning, critical
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User")


class NotificationSubscription(db.Model):
    """Push notification subscriptions"""

    __tablename__ = "notification_subscription"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    subscription_data = db.Column(db.Text, nullable=False)  # JSON data
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User", backref=db.backref("notification_subscriptions", lazy=True)
    )

    def __repr__(self):
        return f"<NotificationSubscription user={self.user_id} endpoint={self.endpoint[:50]}>"


class Notification(db.Model):
    """User notifications"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default="info")  # info, success, warning, error
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="notifications")

    __table_args__ = (
        db.Index("idx_notification_user", "user_id"),
        db.Index("idx_notification_read", "read"),
    )


class Achievement(db.Model):
    """User achievements for engagement"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="achievements")


class ChatMessage(db.Model):
    """Chat messages for persistence"""

    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    username = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    moderated = db.Column(db.Boolean, default=True)  # True if approved
    flagged = db.Column(db.Boolean, default=False)

    user = db.relationship("User")

    __table_args__ = (
        db.Index("idx_chat_room_timestamp", "room", "timestamp"),
        db.Index("idx_chat_moderated", "moderated"),
    )


class Donation(db.Model):
    """Donation records for analytics"""

    id = db.Column(db.Integer, primary_key=True)
    stripe_payment_id = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # In cents
    currency = db.Column(db.String(3), default="usd")
    donor_email = db.Column(db.String(120), nullable=True)
    status = db.Column(
        db.String(20), default="completed"
    )  # completed, failed, refunded
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_donation_timestamp", "timestamp"),
        db.Index("idx_donation_email", "donor_email"),
    )


class Badge(db.Model):
    """User badges for gamification"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True)


class UserBadge(db.Model):
    """User earned badges"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("badge.id"), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User")
    badge = db.relationship("Badge")
