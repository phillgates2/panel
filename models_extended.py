"""Extended database models for new features.

This module contains additional models for:
- Session management
- API keys
- User activity tracking
- 2FA
- IP whitelist/blacklist
- Notifications
- Server templates
- Performance metrics
"""

from datetime import datetime, timezone
from app import db
from werkzeug.security import generate_password_hash
import secrets


class UserSession(db.Model):
    """Track active user sessions for management and security."""
    __tablename__ = 'user_session'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    user = db.relationship('User', backref=db.backref('sessions', lazy='dynamic'))


class ApiKey(db.Model):
    """API keys for programmatic access."""
    __tablename__ = 'api_key'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)  # Human-readable name
    key_hash = db.Column(db.String(256), nullable=False, unique=True)
    key_prefix = db.Column(db.String(16), nullable=False)  # For display (e.g., "pk_abc...")
    scopes = db.Column(db.Text, nullable=True)  # JSON array of allowed scopes
    last_used = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    user = db.relationship('User', backref=db.backref('api_keys', lazy='dynamic'))
    
    @staticmethod
    def generate_key():
        """Generate a new API key."""
        key = f"pk_{secrets.token_urlsafe(32)}"
        return key
    
    def set_key(self, key):
        """Hash and store the API key."""
        self.key_hash = generate_password_hash(key)
        self.key_prefix = key[:10]


class UserActivity(db.Model):
    """Track user login activity and security events."""
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    activity_type = db.Column(db.String(64), nullable=False, index=True)  # login, logout, failed_login, etc.
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON with additional context
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))


class TwoFactorAuth(db.Model):
    """TOTP-based two-factor authentication."""
    __tablename__ = 'two_factor_auth'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    secret = db.Column(db.String(32), nullable=False)  # Base32-encoded TOTP secret
    backup_codes = db.Column(db.Text, nullable=True)  # JSON array of hashed backup codes
    enabled = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('two_factor', uselist=False))


class IpAccessControl(db.Model):
    """IP whitelist/blacklist for access control."""
    __tablename__ = 'ip_access_control'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # IP or CIDR
    list_type = db.Column(db.String(16), nullable=False, index=True)  # 'whitelist' or 'blacklist'
    description = db.Column(db.String(256), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)


class Notification(db.Model):
    """In-app notifications for users."""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(32), nullable=False)  # info, success, warning, error
    link = db.Column(db.String(512), nullable=True)  # Optional action link
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))


class ServerTemplate(db.Model):
    """Pre-configured server templates."""
    __tablename__ = 'server_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(64), nullable=True)  # competitive, casual, custom, etc.
    variables_json = db.Column(db.Text, nullable=False)  # Default variables
    raw_config = db.Column(db.Text, nullable=False)  # Default config
    is_public = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    use_count = db.Column(db.Integer, default=0)  # Track popularity


class ScheduledTask(db.Model):
    """Scheduled tasks for servers (restarts, updates, etc)."""
    __tablename__ = 'scheduled_task'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    task_type = db.Column(db.String(64), nullable=False)  # restart, update, backup, etc.
    schedule = db.Column(db.String(128), nullable=False)  # Cron-style schedule
    parameters = db.Column(db.Text, nullable=True)  # JSON parameters
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class RconCommandHistory(db.Model):
    """RCON command history and favorites."""
    __tablename__ = 'rcon_command_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    command = db.Column(db.Text, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    executed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    user = db.relationship('User', backref=db.backref('rcon_history', lazy='dynamic'))


class PerformanceMetric(db.Model):
    """Store performance metrics for monitoring."""
    __tablename__ = 'performance_metric'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(128), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    tags = db.Column(db.Text, nullable=True)  # JSON key-value pairs
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class UserGroup(db.Model):
    """User groups for permission management."""
    __tablename__ = 'user_group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    permissions = db.Column(db.Text, nullable=True)  # JSON array of permissions
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class UserGroupMembership(db.Model):
    """Many-to-many relationship between users and groups."""
    __tablename__ = 'user_group_membership'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='_user_group_uc'),)
