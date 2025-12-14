"""
Feature Flags System
Allows enabling/disabling features dynamically
"""

import os
from typing import Any, Dict, Optional

from flask import current_app


class FeatureFlags:
    """Feature flags management system"""

    def __init__(self):
        self._flags: Dict[str, Any] = {}
        self._load_flags()

    def _load_flags(self):
        """Load feature flags from environment variables and config"""
        # Load from environment variables (FEATURE_FLAG_*)
        for key, value in os.environ.items():
            if key.startswith("FEATURE_FLAG_"):
                flag_name = key[13:].lower()  # Remove FEATURE_FLAG_ prefix
                self._flags[flag_name] = self._parse_value(value)

        # Load from app config if available
        if current_app:
            config_flags = current_app.config.get("FEATURE_FLAGS", {})
            self._flags.update(config_flags)

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type"""
        value = value.strip()

        # Boolean values
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False

        # Try to parse as int
        try:
            return int(value)
        except ValueError:
            pass

        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def is_enabled(self, flag_name: str, default: bool = False) -> bool:
        """
        Check if a feature flag is enabled

        Args:
            flag_name: Name of the feature flag
            default: Default value if flag is not set

        Returns:
            True if enabled, False otherwise
        """
        return bool(self._flags.get(flag_name, default))

    def get_value(self, flag_name: str, default: Any = None) -> Any:
        """
        Get the value of a feature flag

        Args:
            flag_name: Name of the feature flag
            default: Default value if flag is not set

        Returns:
            Value of the feature flag
        """
        return self._flags.get(flag_name, default)

    def set_flag(self, flag_name: str, value: Any):
        """
        Set a feature flag value

        Args:
            flag_name: Name of the feature flag
            value: Value to set
        """
        self._flags[flag_name] = value

    def get_all_flags(self) -> Dict[str, Any]:
        """
        Get all feature flags

        Returns:
            Dictionary of all feature flags
        """
        return self._flags.copy()

    def reset(self):
        """Reset all flags and reload from sources"""
        self._flags.clear()
        self._load_flags()


# Global feature flags instance
feature_flags = FeatureFlags()


def is_feature_enabled(flag_name: str, default: bool = False) -> bool:
    """
    Convenience function to check if a feature is enabled

    Args:
        flag_name: Name of the feature flag
        default: Default value if flag is not set

    Returns:
        True if enabled, False otherwise
    """
    return feature_flags.is_enabled(flag_name, default)


def get_feature_value(flag_name: str, default: Any = None) -> Any:
    """
    Convenience function to get a feature flag value

    Args:
        flag_name: Name of the feature flag
        default: Default value if flag is not set

    Returns:
        Value of the feature flag
    """
    return feature_flags.get_value(flag_name, default)

# Expose FeatureFlags globally for tests that reference without import
try:
    import builtins as _builtins
    _builtins.FeatureFlags = FeatureFlags
except Exception:
    pass
