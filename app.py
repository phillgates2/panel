import os
import time
from typing import Optional

import newrelic.agent
from flask import (Blueprint, Flask, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user

from app.context_processors import inject_user
from app.db import db
from app.error_handlers import internal_error, page_not_found
from app.extensions import init_app_extensions
from app.factory import create_app
from config import config
from src.panel import models
from src.panel.admin import DatabaseAdmin
# Import permissions
from src.panel.models import ROLE_HIERARCHY, ROLE_PERMISSIONS

# Initialize New Relic APM
newrelic.agent.initialize("newrelic.ini")

# Initialize the Flask app
app = Flask(__name__)

# Initialize all extensions and configurations
extensions = init_app_extensions(app)

# Bind SQLAlchemy to the app
db.init_app(app)

# Track application startup time
app.start_time = time.time()

# Initialize Database Admin integration
try:
    db_admin = DatabaseAdmin(app, db)
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

try:
    from src.panel.admin import admin_bp
except Exception:
    admin_bp = None


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
    try:
        if admin_bp is not None:
            module_app.register_blueprint(admin_bp)
    except Exception:
        pass


# Register optional blueprints on the module-level app if available
_register_optional_blueprints(app)

# Register context processor and error handlers
app.context_processor(inject_user)
app.errorhandler(404)(page_not_found)
app.errorhandler(500)(internal_error)

from src.panel.admin_bp import admin_bp
from src.panel.api_bp import api_bp
from src.panel.chat_bp import chat_bp
# Import and register blueprints
from src.panel.main_bp import main_bp
from src.panel.payment_bp import payment_bp

app.register_blueprint(main_bp)
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(chat_bp)
app.register_blueprint(payment_bp)
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
