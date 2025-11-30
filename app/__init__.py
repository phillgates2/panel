from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Import models for testing
from src.panel.models import User, SiteAsset, SiteSetting

def create_app(config_name='default'):
    """Application factory function"""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Load configuration
    if isinstance(config_name, str):
        app.config.from_object(config)
    else:
        # Assume it's a config object
        for key, value in vars(config_name).items():
            if not key.startswith('_'):
                app.config[key.upper()] = value

    # Initialize essential extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # Dummy user loader for testing
        return None

    # Register blueprints
    from src.panel.main_bp import main_bp
    from src.panel.api_bp import api_bp
    from src.panel.chat_bp import chat_bp
    from src.panel.payment_bp import payment_bp
    from src.panel.admin_bp import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(chat_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(admin_bp)

    # Register context processors
    from app.context_processors import inject_user
    app.context_processor(inject_user)

    return app

def verify_csrf():
    """Dummy CSRF verification for testing"""
    return True

# Create default app instance for testing
app = create_app()