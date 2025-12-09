"""
App Package

This package contains the core application components.
Use create_app() factory function to create Flask app instances.
"""

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# Import core models so tests and legacy code can use `from app import User, SiteAsset, SiteSetting`
from src.panel.models import SiteAsset, SiteSetting, User, Server, ServerUser
from src.panel.routes_rbac import user_can_edit_server, user_server_role
from src.panel.csrf import verify_csrf

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name="default"):
    """Application factory function.
    
    Creates and configures a Flask application instance.
    
    Args:
        config_name: Configuration name or object
        
    Returns:
        Configured Flask application
    """
    import os
    from pathlib import Path
    
    # Determine template and static directories
    root_dir = Path(__file__).parent.parent
    template_dir = root_dir / "templates"
    static_dir = root_dir / "static"
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    
    # Load configuration
    from config import config
    if isinstance(config_name, str):
        app.config.from_object(config)
    else:
        # Assume it's a config object
        for key, value in vars(config_name).items():
            if not key.startswith("_"):
                app.config[key.upper()] = value
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = "main.login"
    login_manager.login_message = "Please log in to access this page."
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID."""
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_blueprints(app):
    """Register application blueprints."""
    try:
        from src.panel.main_bp import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.api_bp import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
    except ImportError:
        pass
    
    try:
        from src.panel.admin_bp import admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.payment_bp import payment_bp
        app.register_blueprint(payment_bp)
    except ImportError:
        pass


def register_context_processors(app):
    """Register template context processors."""
    try:
        from app.context_processors import inject_user
        app.context_processor(inject_user)
    except ImportError:
        pass


def register_error_handlers(app):
    """Register error handlers."""
    try:
        from app.error_handlers import page_not_found, internal_error
        app.errorhandler(404)(page_not_found)
        app.errorhandler(500)(internal_error)
    except ImportError:
        pass


# Legacy global app object for tests and older code paths
# This allows imports like `from app import app` to continue working.
app = create_app()


# Expose key components at package level
__all__ = [
    "create_app",
    "db",
    "login_manager",
    "User",
    "SiteAsset",
    "SiteSetting",
    "Server",
    "ServerUser",
    "user_can_edit_server",
    "user_server_role",
    "verify_csrf",
    "app",
]
