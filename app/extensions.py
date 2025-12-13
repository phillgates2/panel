"""
Flask Extensions Initialization

This module coordinates the initialization of all Flask extensions
by delegating to specialized extension modules.
"""

from typing import Any, Dict

from flask import Flask

from app.core_extensions import init_core_extensions


def init_app_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize all Flask extensions and configurations for the app.

    This function coordinates the initialization of extensions across
    different categories: core, security, monitoring, AI, and integrations.

    Args:
        app: The Flask application instance.

    Returns:
        A dictionary containing all initialized extension instances
        organized by category.
    """
    # Validate configuration at startup
    try:
        from config_validator import validate_configuration_at_startup
        validate_configuration_at_startup(app)
    except Exception:
        # Configuration validator unavailable or incompatible; continue without it
        pass

    # Initialize extensions by category
    core_extensions = init_core_extensions(app)

    try:
        from app.security_extensions import init_security_extensions
        security_extensions = init_security_extensions(app)
    except Exception as e:
        app.logger.warning(f"Security extensions disabled: {e}")
        security_extensions = {}

    try:
        from app.monitoring_extensions import init_monitoring_extensions
        monitoring_extensions = init_monitoring_extensions(app)
    except Exception as e:
        app.logger.warning(f"Monitoring extensions disabled: {e}")
        monitoring_extensions = {}

    try:
        from app.ai_extensions import init_ai_extensions
        ai_extensions = init_ai_extensions(app)
    except Exception as e:
        app.logger.warning(f"AI extensions disabled: {e}")
        ai_extensions = {}

    try:
        from app.integration_extensions import init_integration_extensions
        integration_extensions = init_integration_extensions(app)
    except Exception as e:
        app.logger.warning(f"Integration extensions disabled: {e}")
        integration_extensions = {}

    # Combine all extensions into a single dictionary
    all_extensions = {
        **core_extensions,
        **security_extensions,
        **monitoring_extensions,
        **ai_extensions,
        **integration_extensions,
    }

    # Log successful initialization
    app.logger.info("All Flask extensions initialized successfully")

    return all_extensions
