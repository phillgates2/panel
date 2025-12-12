"""Extended models for Panel.

Compatibility shim that re-exports extended models from src.panel.models_extended
so existing imports like `from models_extended import UserGroup` continue to work.
"""

from src.panel.models_extended import (  # noqa: F401
    ApiKey,
    IpAccessControl,
    PerformanceMetric,
    RconCommandHistory,
    ScheduledTask,
    ServerTemplate,
    TwoFactorAuth,
    UserActivity,
    UserGroup,
    UserGroupMembership,
    UserSession,
)

__all__ = [
    "UserSession",
    "ApiKey",
    "UserActivity",
    "TwoFactorAuth",
    "IpAccessControl",
    "ServerTemplate",
    "ScheduledTask",
    "RconCommandHistory",
    "PerformanceMetric",
    "UserGroup",
    "UserGroupMembership",
]
