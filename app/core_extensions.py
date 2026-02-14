"""
Core Flask Extensions

This module initializes core Flask extensions that are essential for the application.
"""

import os
from typing import Any, Dict

from flask import Flask
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_principal import Permission, Principal, RoleNeed
from flask_swagger_ui import get_swaggerui_blueprint
from graphene import ObjectType, Schema as GraphQLSchema, String

from config import config
from src.panel.api_documentation import api_bp
from src.panel.celery_app import init_celery
from src.panel.config_manager import init_config_manager
from src.panel.oauth import init_oauth, init_oauth_routes
from src.panel.structured_logging import setup_structured_logging


def init_core_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize core Flask extensions.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary of initialized core extension instances.
    """
    # Load configuration
    app.config.from_object(config)
    app.secret_key = config.SECRET_KEY

    # Database configuration with connection pooling
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "PANEL_SQLITE_URI", "sqlite:///panel_dev.db"
    )
    app.config["SQLALCHEMY_POOL_SIZE"] = int(os.environ.get("PANEL_DB_POOL_SIZE", "10"))
    app.config["SQLALCHEMY_MAX_OVERFLOW"] = int(
        os.environ.get("PANEL_DB_MAX_OVERFLOW", "20")
    )
    app.config["SQLALCHEMY_POOL_TIMEOUT"] = 30
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 3600
    app.config["SQLALCHEMY_POOL_PRE_PING"] = True

    # Initialize Cache for performance optimization
    # Use explicit backend class path to avoid deprecation warnings
    cache_config = {
        "CACHE_TYPE": "flask_caching.backends.SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default
    }
    cache = Cache(app, config=cache_config)

    # Initialize Compression
    compress = Compress(app)

    # Configure logging
    logger = setup_structured_logging(app)

    # Initialize Celery
    celery = init_celery(app)

    # Initialize advanced rate limiting
    # Prefer Redis when configured/available, but don't crash the whole app if
    # Redis isn't running yet.
    storage_uri = (
        os.environ.get("RATELIMIT_STORAGE_URI")
        or os.environ.get("PANEL_RATELIMIT_STORAGE_URI")
        or os.environ.get("PANEL_REDIS_URL")
        or "memory://"
    )
    if isinstance(storage_uri, str) and storage_uri.startswith(("redis://", "rediss://")):
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(storage_uri, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.ping()
        except Exception as e:
            app.logger.warning(f"Redis not available for rate limiting; falling back to memory storage: {e}")
            storage_uri = "memory://"

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
    )

    # Initialize OAuth
    init_oauth(app)
    try:
        init_oauth_routes(app)
    except Exception as e:
        app.logger.warning(f"OAuth routes disabled: {e}")

    # Initialize CORS
    cors = CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["*"],  # Configure appropriately for production
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    # Initialize API documentation
    try:
        app.register_blueprint(api_bp)
    except Exception as e:
        app.logger.warning(f"API documentation blueprint skipped: {e}")

    # Add Swagger UI for API documentation
    try:
        swaggerui_blueprint = get_swaggerui_blueprint(
            "/api/docs",
            "/api/swagger.json",
            config={"app_name": "Panel API", "validatorUrl": None},
        )
        app.register_blueprint(swaggerui_blueprint, url_prefix="/api/docs")
    except Exception as e:
        app.logger.warning(f"Swagger UI setup skipped: {e}")

    # Initialize configuration management
    config_manager = init_config_manager(app)

    # Initialize RBAC
    principal = Principal(app)

    # Define permissions
    view_admin = Permission(RoleNeed("admin"), RoleNeed("system_admin"))
    manage_users = Permission(RoleNeed("admin"), RoleNeed("system_admin"))
    manage_servers = Permission(RoleNeed("admin"), RoleNeed("system_admin"))
    moderate_forum = Permission(
        RoleNeed("moderator"), RoleNeed("admin"), RoleNeed("system_admin")
    )
    system_config = Permission(RoleNeed("system_admin"))

    # Store permissions for easy access
    permissions = {
        "view_admin": view_admin,
        "manage_users": manage_users,
        "manage_servers": manage_servers,
        "moderate_forum": moderate_forum,
        "system_config": system_config,
    }

    # Initialize JWT
    jwt = JWTManager(app)

    # Initialize GraphQL
    class Query(ObjectType):
        hello = String(description="A simple hello world")

        def resolve_hello(self, info):
            return "Hello, World!"

    schema = GraphQLSchema(query=Query)

    return {
        "cache": cache,
        "compress": compress,
        "logger": logger,
        "celery": celery,
        "limiter": limiter,
        "cors": cors,
        "config_manager": config_manager,
        "principal": principal,
        "jwt": jwt,
        "schema": schema,
        "permissions": permissions,
    }