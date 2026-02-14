"""
Panel Application Entry Point

This module serves as the main entry point for the Panel Flask application.
It initializes the app, registers blueprints, and starts the server.
"""

import os
import time
from typing import Optional

from flask import (Blueprint, Flask, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user

# Import application components
from app.context_processors import inject_user
from app.db import db
from app.error_handlers import internal_error, page_not_found
from app.extensions import init_app_extensions

# Import configuration
from config import config

# Import models and routes
from src.panel.models import User
try:
    from src.panel.admin import DatabaseAdmin
except Exception:
    DatabaseAdmin = None

# Import blueprints
try:
    from src.panel.admin_bp import admin_bp
except Exception:
    admin_bp = None
try:
    from src.panel.api_bp import api_bp
except Exception:
    api_bp = None
try:
    from src.panel.chat_bp import chat_bp
except Exception:
    chat_bp = None
from src.panel.main_bp import main_bp
try:
    from src.panel.payment_bp import payment_bp
except Exception:
    payment_bp = None

# Initialize New Relic APM (optional)
try:
    import newrelic.agent as _nr_agent

    _nr_config = os.environ.get("NEW_RELIC_CONFIG_FILE")
    if not _nr_config:
        for _candidate in ("config/newrelic.ini", "newrelic.ini"):
            if os.path.exists(_candidate):
                _nr_config = _candidate
                break
    if _nr_config:
        _nr_agent.initialize(_nr_config)
except Exception:
    # If New Relic isn't installed or configured, continue without it
    pass

# Initialize the Flask app
app = Flask(__name__)

# Load configuration early so extensions (sessions, CSRF, etc.) have access to
# SECRET_KEY and other required settings.
try:
    app.config.from_object(config)
except Exception:
    # Best-effort: keep app booting in minimal/test environments.
    pass

# Explicitly set Flask's secret key attribute (used by sessions).
try:
    app.secret_key = app.config.get("SECRET_KEY")
except Exception:
    pass

# Initialize all extensions and configurations
extensions = init_app_extensions(app)

# Bind SQLAlchemy to the app
db.init_app(app)

# Initialize Flask-Migrate so `flask db ...` commands are registered
try:
    from flask_migrate import Migrate

    _migrate = Migrate(app, db)
except Exception:
    _migrate = None

# Track application startup time
app.start_time = time.time()

# Initialize Database Admin integration
try:
    if DatabaseAdmin is not None:
        db_admin = DatabaseAdmin(app, db)
    else:
        db_admin = None
except Exception:
    # Best-effort during tests; ignore failures
    db_admin = None

# Optional CMS and Forum blueprints (kept optional so imports won't fail in test environments)
try:
    from src.panel.cms import cms_bp
except Exception:
    cms_bp = None
try:
    from src.panel.forum import forum_bp
except Exception:
    forum_bp = None

def _register_optional_blueprints(module_app: Flask) -> None:
    try:
        from src.panel import cms as _cms

        if hasattr(_cms, "cms_bp"):
            try:
                module_app.register_blueprint(_cms.cms_bp)
            except Exception:
                pass
    except Exception:
        pass
    try:
        from src.panel import forum as _forum

        if hasattr(_forum, "forum_bp"):
            try:
                module_app.register_blueprint(_forum.forum_bp)
            except Exception:
                pass
    except Exception:
        pass


# Register optional blueprints on the module-level app if available
_register_optional_blueprints(app)

# Register context processor and error handlers
app.context_processor(inject_user)
app.errorhandler(404)(page_not_found)
app.errorhandler(500)(internal_error)

app.register_blueprint(main_bp)
if api_bp is not None:
    app.register_blueprint(api_bp, url_prefix="/api")
if chat_bp is not None:
    app.register_blueprint(chat_bp)
if payment_bp is not None:
    app.register_blueprint(payment_bp)
if admin_bp is not None:
    app.register_blueprint(admin_bp)

SERVICE_NAME = os.environ.get("SERVICE_NAME", "main")

if SERVICE_NAME == "auth":
    # Auth service routes
    @app.route("/auth/login")
    def auth_login() -> str:
        return "Auth service login"

elif SERVICE_NAME == "chat":
    # Chat service routes
    pass  # Chat routes are already in chat_bp
elif SERVICE_NAME == "payment":
    # Payment service routes
    pass  # Payment routes are already in payment_bp
else:
    # Main app routes
    pass

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
