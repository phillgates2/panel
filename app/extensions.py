import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request, session
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS

from config import config
# from src.panel.socket_handlers import socketio
from config_validator import validate_configuration_at_startup
from src.panel.structured_logging import setup_structured_logging

try:
    from src.panel.tools.mail import mail
except Exception:
    pass
import logging

import sentry_sdk
from flask_babel import Babel
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_principal import Permission, Principal, RoleNeed
from flask_swagger_ui import get_swaggerui_blueprint
from graphene import ObjectType
from graphene import Schema as GraphQLSchema
from graphene import String
from marshmallow import Schema, fields
from prometheus_flask_exporter import PrometheusMetrics
from pythonjsonlogger import jsonlogger
from transformers import pipeline

from src.panel.ai_chat import init_ai_chat
from src.panel.ai_integration import init_ai_features
from src.panel.api_documentation import api_bp
from src.panel.backup_monitoring import init_backup_monitoring
from src.panel.backup_recovery import init_backup_system
from src.panel.cdn_integration import init_cdn_integration
from src.panel.celery_app import init_celery
from src.panel.config_manager import init_config_manager
from src.panel.custom_ai_training import init_model_trainer
from src.panel.db_optimization import init_db_optimization
from src.panel.enhanced_ai import init_advanced_ai_features
from src.panel.gdpr_compliance import init_gdpr_compliance
from src.panel.health import init_health_checks
from src.panel.metrics import init_metrics
from src.panel.microservices import init_microservices_architecture
from src.panel.oauth import init_oauth, init_oauth_routes
from src.panel.performance_monitoring import init_performance_monitoring
from src.panel.push_notifications import init_push_notifications
from src.panel.rate_limiting import (init_rate_limiting_admin,
                                     setup_rate_limiting)
from src.panel.server_management import init_server_management
from src.panel.video_processing import init_video_processor
from src.panel.voice_analysis import init_voice_analyzer


def init_app_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize all Flask extensions and configurations for the app.

    Args:
        app: The Flask application instance.

    Returns:
        A dictionary of initialized extension instances.
    """
    # Validate configuration at startup
    validate_configuration_at_startup(app)

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

    # Initialize SocketIO
    # socketio.init_app(app)

    # Initialize Cache for performance optimization
    cache_config = {
        "CACHE_TYPE": "redis",
        "CACHE_REDIS_URL": os.environ.get(
            "PANEL_REDIS_URL", "redis://127.0.0.1:6379/0"
        ),
        "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default
    }
    cache = Cache(app, config=cache_config)

    # Initialize Compression
    compress = Compress(app)

    # Configure logging
    logger = setup_structured_logging(app)

    # Set up JSON logging for better observability
    json_formatter = jsonlogger.JsonFormatter()
    for handler in logging.getLogger().handlers:
        handler.setFormatter(json_formatter)

    # Configure enhanced security hardening
    security_hardening = {}  # Placeholder for security hardening config

    # Initialize mail if available
    if mail:
        mail.init_app(app)

    # Initialize metrics tracking
    app._request_count = 0
    app._error_count = 0

    @app.before_request
    def track_request_metrics():
        """Track request metrics for monitoring."""
        if not request.path.startswith("/static/"):
            app._request_count += 1

    @app.after_request
    def track_error_metrics(response):
        """Track error metrics for monitoring."""
        if response.status_code >= 400:
            app._error_count += 1
        return response

    # Initialize metrics collection
    init_metrics(app)

    # Initialize database optimization and profiling
    init_db_optimization(app)

    # Initialize health check endpoints
    init_health_checks(app)

    # Initialize server management with RCON
    init_server_management(app)

    # Initialize Celery
    celery = init_celery(app)

    # Initialize advanced rate limiting
    limiter = setup_rate_limiting(app)
    init_rate_limiting_admin(app)

    # Initialize OAuth
    init_oauth(app)
    init_oauth_routes(app)

    # Initialize GDPR compliance
    init_gdpr_compliance(app)

    # Initialize CORS for GDPR endpoints
    cors = CORS(
        app,
        resources={
            r"/api/gdpr/*": {
                "origins": ["*"],  # Configure appropriately for production
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    # Initialize push notifications
    init_push_notifications(app)

    # Initialize microservices architecture preparation
    init_microservices_architecture(app)

    # Initialize CDN integration
    init_cdn_integration(app)

    # Initialize performance monitoring
    init_performance_monitoring(app)

    # Initialize API documentation
    app.register_blueprint(api_bp)

    # Add Swagger UI for API documentation
    swaggerui_blueprint = get_swaggerui_blueprint(
        "/api/docs",
        "/api/swagger.json",
        config={"app_name": "Panel API", "validatorUrl": None},
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix="/api/docs")

    # Initialize configuration management
    config_manager = init_config_manager(app)

    # Initialize backup and recovery system
    backup_manager = init_backup_system(app)

    # Initialize backup monitoring
    backup_monitor = init_backup_monitoring(app)

    # Initialize AI features
    init_ai_features()

    # Initialize advanced AI features
    init_advanced_ai_features()
    init_ai_chat()
    init_voice_analyzer()
    init_video_processor()
    init_model_trainer()

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
    PERMISSIONS = {
        "view_admin": view_admin,
        "manage_users": manage_users,
        "manage_servers": manage_servers,
        "moderate_forum": moderate_forum,
        "system_config": system_config,
    }

    # Initialize JWT
    jwt = JWTManager(app)

    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)

    # Initialize Babel for i18n
    babel = Babel(app)

    # Initialize Sentry for error tracking
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[
            # GpuOptions for better performance with Gunicorn
            sentry_sdk.integrations.gpu.GpuOptions(),
            sentry_sdk.integrations.flask.FlaskIntegration(),
        ],
        traces_sample_rate=1.0,  # Sample 100% of transactions for performance monitoring
    )

    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
    )

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
        "security_hardening": security_hardening,
        "mail": mail,
        "celery": celery,
        "limiter": limiter,
        "cors": cors,
        "config_manager": config_manager,
        "backup_manager": backup_manager,
        "backup_monitor": backup_monitor,
        "principal": principal,
        "jwt": jwt,
        "metrics": metrics,
        "babel": babel,
        "schema": schema,
        "permissions": PERMISSIONS,
    }
