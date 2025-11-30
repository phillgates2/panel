from flask import Blueprint, Flask
from flask_caching import Cache
from flask_compress import Compress
from flask_socketio import SocketIO

from config import config
from src.panel.security_headers import configure_security_headers
from src.panel.structured_logging import setup_structured_logging

try:
    from src.panel.tools.mail import mail
except Exception:
    pass
from src.panel.database_admin import DatabaseAdmin

try:
    from config_validator import validate_configuration_at_startup
except Exception:
    validate_configuration_at_startup = None
import os

from app.context_processors import inject_user
from app.db import db
from src.panel.csrf import (ensure_csrf_after, ensure_csrf_for_templates,
                            ensure_theme_migration_once)

# Create main blueprint
main_bp = Blueprint("main", __name__)


def create_app(config_obj: Optional[object] = None) -> Flask:
    """Application factory.

    Creates and returns a Flask application configured like the module-level
    `app`. If `config_obj` is provided, it will be used instead of the
    default `config` module.

    Args:
        config_obj: Optional configuration object.

    Returns:
        Configured Flask application instance.
    """
    _app = Flask(__name__)

    # Validate configuration at startup
    try:
        if validate_configuration_at_startup:
            validate_configuration_at_startup(_app)
    except Exception as e:
        print(f"Configuration validation failed: {e}")

    # Load configuration
    if config_obj is None:
        _app.config.from_object(config)
    else:
        _app.config.from_object(config_obj)
    _app.secret_key = _app.config.get("SECRET_KEY", getattr(config, "SECRET_KEY", None))

    # --- Initialize extensions and configure app ---

    # Initialize SocketIO for real-time features
    _socketio = SocketIO(_app, cors_allowed_origins="*")

    # Initialize Cache for performance optimization
    _cache_config = {
        "CACHE_TYPE": "redis",
        "CACHE_REDIS_URL": os.environ.get(
            "PANEL_REDIS_URL", "redis://127.0.0.1:6379/0"
        ),
        "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default
    }
    _cache = Cache(_app, config=_cache_config)

    # Initialize Compression
    _compress = Compress(_app)

    # Configure logging for the new app
    setup_structured_logging(_app)

    # Configure security headers
    configure_security_headers(_app)

    # Initialize lightweight mail client if present
    try:
        mail.init_app(_app)
    except Exception:
        pass

    # Bind SQLAlchemy
    db.init_app(_app)

    # Mirror module-level startup behavior for factory-created apps
    # so tests and callers receive an app with the same routes and
    # integrations (DatabaseAdmin, blueprints, start_time).
    # Assign to module-level `app` so existing route code that
    # references `app` (legacy usage) will observe the factory app.
    global app
    app = _app

    # Track application startup time
    _app.start_time = time.time()

    # Initialize Database Admin integration for the new app
    try:
        # Create a DatabaseAdmin instance bound to this app
        DatabaseAdmin(_app, db)
    except Exception:
        # Best-effort during tests; ignore failures
        pass

    # --- End of initialization ---

    # Backwards-compat: create un-prefixed endpoint aliases on the
    # factory app so existing `url_for('login')` calls continue to work.
    try:
        # Build list of blueprint names to create unprefixed aliases for
        bp_names = [main_bp.name]
        try:
            if hasattr(_cms, "cms_bp"):
                bp_names.append(_cms.cms_bp.name)
        except NameError:
            pass
        try:
            if hasattr(_forum, "forum_bp"):
                bp_names.append(_forum.forum_bp.name)
        except NameError:
            pass
        try:
            if admin_bp is not None:
                bp_names.append(admin_bp.name)
        except NameError:
            pass

        for rule in list(_app.url_map.iter_rules()):
            ep = rule.endpoint
            for bpname in bp_names:
                if ep.startswith(f"{bpname}."):
                    short = ep.split(".", 1)[1]
                    if short not in _app.view_functions:
                        view = _app.view_functions.get(ep)
                        if view:
                            try:
                                methods = [
                                    m
                                    for m in rule.methods
                                    if m not in ("HEAD", "OPTIONS")
                                ]
                                _app.add_url_rule(
                                    rule.rule,
                                    endpoint=short,
                                    view_func=view,
                                    methods=methods,
                                )
                            except Exception:
                                pass
                    break
    except Exception:
        pass

    # Ensure key context processors and request handlers defined on the
    # module-level app are also registered on the factory-created app so
    # templates and request lifecycle behavior match.
    try:
        _app.context_processor(inject_user)
    except Exception:
        pass
    try:
        _app.after_request(ensure_csrf_after)
    except Exception:
        pass
    try:
        _app.context_processor(ensure_csrf_for_templates)
    except Exception:
        pass
    try:
        _app.before_request(ensure_theme_migration_once)
    except Exception:
        pass

    # Register blueprints on the factory-created app
    try:
        _app.register_blueprint(main_bp)
    except AssertionError:
        pass

    try:
        if hasattr(_cms, "cms_bp"):
            try:
                _app.register_blueprint(_cms.cms_bp)
            except AssertionError:
                pass
    except Exception:
        pass

    try:
        if hasattr(_forum, "forum_bp"):
            try:
                _app.register_blueprint(_forum.forum_bp)
            except AssertionError:
                pass
    except Exception:
        pass

    # Register additional blueprints that were added later
    try:
        _app.register_blueprint(monitoring_bp)
    except (AssertionError, NameError):
        pass

    try:
        _app.register_blueprint(routes_rbac.rbac_bp)
    except (AssertionError, NameError):
        pass

    # Create backwards-compat unprefixed endpoint aliases for factory-created apps
    try:
        bp_names = [main_bp.name]
        try:
            if hasattr(_cms, "cms_bp"):
                bp_names.append(_cms.cms_bp.name)
        except NameError:
            pass
        try:
            if hasattr(_forum, "forum_bp"):
                bp_names.append(_forum.forum_bp.name)
        except NameError:
            pass
        try:
            if admin_bp is not None:
                bp_names.append(admin_bp.name)
        except NameError:
            pass

        for rule in list(_app.url_map.iter_rules()):
            ep = rule.endpoint
            for bpname in bp_names:
                if ep.startswith(f"{bpname}."):
                    short = ep.split(".", 1)[1]
                    if short not in _app.view_functions:
                        view = _app.view_functions.get(ep)
                        if view:
                            try:
                                methods = [
                                    m
                                    for m in rule.methods
                                    if m not in ("HEAD", "OPTIONS")
                                ]
                                _app.add_url_rule(
                                    rule.rule,
                                    endpoint=short,
                                    view_func=view,
                                    methods=methods,
                                )
                            except Exception:
                                pass
                    break
    except Exception:
        pass

    return _app
