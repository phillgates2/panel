"""
Integration Extensions

This module initializes external integration Flask extensions.
"""

from typing import Any, Dict

from flask import Flask

from src.panel.cdn_integration import init_cdn_integration
from src.panel.db_optimization import init_db_optimization
from src.panel.microservices import init_microservices_architecture
from src.panel.push_notifications import init_push_notifications
from src.panel.server_management import init_server_management


def init_integration_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize external integration Flask extensions.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary of initialized integration extension instances.
    """
    # Initialize database optimization and profiling
    init_db_optimization(app)

    # Initialize server management with RCON
    init_server_management(app)

    # Initialize push notifications
    init_push_notifications(app)

    # Initialize microservices architecture preparation
    init_microservices_architecture(app)

    # Initialize CDN integration
    init_cdn_integration(app)

    # Configure integration settings
    integration_config = {
        'database_optimization_enabled': True,
        'server_management_enabled': True,
        'push_notifications_enabled': True,
        'microservices_enabled': True,
        'cdn_integration_enabled': True,
    }

    return {
        "integration_config": integration_config,
    }