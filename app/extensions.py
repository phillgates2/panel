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

    # Flask-Login: required for routes that use @login_required.
    # In deployments that import `app:app` from app.py (module-level app),
    # the app factory in app/__init__.py is bypassed, so we must initialize
    # LoginManager here.
    try:
        from flask_login import LoginManager

        from app.db import db

        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = "main.login"
        login_manager.login_message = "Please log in to access this page."

        @login_manager.user_loader
        def load_user(user_id: str):
            try:
                from src.panel.models import User
                return db.session.get(User, int(user_id))
            except Exception:
                return None

        @login_manager.request_loader
        def load_user_from_request(_request):
            # Support the app's session-based auth (session['user_id']) so
            # routes protected with @login_required work consistently.
            try:
                from flask import session

                user_id = session.get("user_id")
                if not user_id:
                    return None
                from src.panel.models import User

                return db.session.get(User, int(user_id))
            except Exception:
                return None

        all_extensions["login_manager"] = login_manager
    except Exception as e:
        app.logger.warning(f"Login manager disabled: {e}")

    # Log successful initialization
    app.logger.info("All Flask extensions initialized successfully")

    return all_extensions
