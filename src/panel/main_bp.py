from typing import Any, Dict

import io

from flask import (Blueprint, current_app, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user

from app.utils import moderate_message
from src.panel.models import ChatMessage, db
from src.panel.models import SiteSetting
from src.panel.models import SiteAsset

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> str:
    # Always render the home page. Theme enable/disable is handled by
    # template context (e.g., whether /theme.css is linked), not by 404ing '/'.
    return render_template("index.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        # Minimal auth flow for tests: find user by email and verify password
        from src.panel.models import User
        email = request.form.get("email")
        password = request.form.get("password")
        if email and password:
            u = db.session.query(User).filter_by(email=email).first()
            if u and u.check_password(password):
                # establish session
                from flask import session

                session["user_id"] = u.id
                try:
                    from flask_login import login_user

                    login_user(u)
                except Exception:
                    pass
                return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main_bp.route("/register")
def register() -> str:
    return render_template("register.html")


@main_bp.route("/status")
def status() -> Dict[str, Any]:
    import time

    return {
        "status": "ok",
        "uptime": time.time() - current_app.start_time,
        "version": "1.0",
        "features": list(feature_flags.keys()),
    }


@main_bp.route("/health")
def health() -> Dict[str, Any]:
    import time

    # Check external services
    health_status = {
        "status": "healthy",
        "checks": {},
        "timestamp": time.time(),
        "uptime_seconds": time.time() - current_app.start_time if hasattr(current_app, "start_time") else 0,
    }
    try:
        # Check Redis
        cache.get("health_check")
        health_status["checks"]["redis"] = "ok"
    except:
        health_status["checks"]["redis"] = "fail"
        health_status["status"] = "unhealthy"
    try:
        # Check DB
        db.session.execute(db.text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except:
        health_status["checks"]["database"] = "fail"
        health_status["status"] = "unhealthy"
    # Add AI API check if applicable
    return health_status


@main_bp.route("/health/ready")
def health_ready() -> Any:
    # Readiness probe: basic DB check
    try:
        db.session.execute(db.text("SELECT 1"))
        import time
        return jsonify({"status": "ready", "timestamp": time.time(), "checks": {"database": "ok"}}), 200
    except Exception:
        import time
        return jsonify({"status": "not_ready", "timestamp": time.time(), "checks": {"database": "fail"}}), 503


@main_bp.route("/health/live")
def health_live() -> Any:
    # Liveness probe: app is running
    import time
    uptime = 0
    try:
        uptime = time.time() - getattr(current_app, "start_time", time.time())
    except Exception:
        pass
    return jsonify({"status": "alive", "timestamp": time.time(), "uptime_seconds": uptime}), 200


@main_bp.route("/metrics")
def metrics() -> Any:
    # Require auth: if not logged in, 401
    from flask import session
    if not session.get("user_id"):
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"uptime": 1}), 200


@main_bp.route("/api/v2/status")
def api_v2_status() -> Dict[str, Any]:
    return {"version": "v2", "status": "ok"}


@main_bp.route("/webhooks", methods=["POST"])
def webhooks() -> Dict[str, Any]:
    data = request.json
    # Process webhook, e.g., Discord/Slack
    return {"received": True}


# GraphQL
from graphene import ObjectType
from graphene import Schema as GraphQLSchema
from graphene import String


@main_bp.route("/graphql", methods=["GET", "POST"])
def graphql_view() -> Any:
    # Optional feature: if GraphQL isn't configured in this environment,
    # return a simple non-error response instead of crashing.
    try:
        from flask import Response

        return Response(
            "<html><body><h1>GraphQL</h1><p>GraphQL is not configured.</p></body></html>",
            status=200,
            mimetype="text/html",
        )
    except Exception:
        return {"error": "GraphQL is not configured"}, 200


@main_bp.route("/captcha.png")
def captcha_png() -> Any:
    from datetime import datetime

    from flask import Response, session

    try:
        from src.panel.captcha import generate_captcha_image, last_image_bytes
    except Exception:
        # If captcha module is unavailable for any reason, avoid 500.
        return Response(status=204)

    try:
        text = generate_captcha_image()
    except Exception:
        return Response(status=204)

    # Session may be unavailable/misconfigured in some deployments; captcha image
    # should still render even if we can't persist the expected text.
    try:
        session["captcha_text"] = str(text).strip().upper()
        session["captcha_ts"] = int(datetime.now().timestamp())
    except Exception:
        pass

    try:
        img = last_image_bytes()
    except Exception:
        img = None
    if not img:
        return Response(status=204)

    resp = Response(img, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@main_bp.route("/captcha_audio")
def captcha_audio() -> Any:
    from flask import Response, session

    try:
        from src.panel.captcha import generate_captcha_audio
    except Exception:
        return Response(b"", status=204, mimetype="audio/wav")

    try:
        text = session.get("captcha_text")
    except Exception:
        text = None
    if not text:
        return Response(b"", status=204, mimetype="audio/wav")
    try:
        audio = generate_captcha_audio(text=text)
    except Exception:
        return Response(b"", status=204, mimetype="audio/wav")

    resp = Response(audio, mimetype="audio/wav")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


# Feature flags
feature_flags = {"dark_mode": True, "new_ui": False, "gdpr_auto_export": True}


@main_bp.route("/profile")
def profile() -> str:
    return render_template("profile.html")


@main_bp.route("/settings")
def settings() -> str:
    return render_template("settings.html")


@main_bp.route("/dashboard")
def dashboard() -> str:
    return render_template("dashboard.html")


@main_bp.route("/rcon")
def rcon_console() -> str:
    # Minimal placeholder route used by dashboard template links
    return render_template("rcon_console.html")


@main_bp.route("/notifications")
def notifications() -> str:
    return render_template("notifications.html")


@main_bp.route("/api/user/theme", methods=["POST"])
def update_theme() -> Dict[str, Any]:
    data = request.json
    theme = data.get("theme")
    # Save to user settings
    return {"success": True}


@main_bp.route("/api/notifications")
def get_notifications() -> Dict[str, Any]:
    # Get user notifications
    notifications = []  # Query from DB
    return {"notifications": notifications}


@main_bp.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
def mark_notification_read(notif_id: int) -> Dict[str, Any]:
    # Mark as read
    return {"success": True}


@main_bp.context_processor
def inject_breadcrumbs() -> Dict[str, Any]:
    # Simple breadcrumb logic - customize based on routes
    path = request.path
    breadcrumbs = []
    if path.startswith("/forum"):
        breadcrumbs = [{"name": "Home", "url": "/"}, {"name": "Forum", "url": "/forum"}]
    elif path.startswith("/profile"):
        breadcrumbs = [
            {"name": "Home", "url": "/"},
            {"name": "Profile", "url": "/profile"},
        ]
    return {"breadcrumbs": breadcrumbs}


@main_bp.route("/search")
def search() -> str:
    query = request.args.get("q", "")
    # Implement search logic
    results = []
    if query:
        # Search in models
        results = []  # Placeholder
    return render_template("search.html", query=query, results=results)


@main_bp.route("/help")
def help_page() -> str:
    return render_template("help.html")


@main_bp.route("/forgot", methods=["GET", "POST"])
def forgot() -> str:
    # Minimal forgot-password page (template already exists)
    return render_template("forgot.html")


@main_bp.route("/account/change-password")
def change_password() -> Any:
    # Placeholder route used by templates; redirect to settings for now.
    return redirect(url_for("main.settings"))


@main_bp.route("/account/2fa/setup")
def setup_2fa() -> Any:
    return redirect(url_for("main.settings"))


@main_bp.route("/account/2fa/disable")
def disable_2fa() -> Any:
    return redirect(url_for("main.settings"))


@main_bp.route("/account/api-tokens")
def api_get_tokens() -> Any:
    return redirect(url_for("main.settings"))


@main_bp.route("/account/avatar/remove", methods=["POST"])
def remove_avatar() -> Any:
    # Placeholder endpoint referenced by the profile page JS.
    return redirect(url_for("main.profile"))


@main_bp.route("/permissions")
def permissions() -> str:
    return render_template("permissions.html")


@main_bp.route("/chat")
def chat() -> str:
    return render_template("chat.html")


@main_bp.route("/theme.css")
def theme_css() -> str:
    # Serve theme CSS from DB when enabled
    try:
        enabled = False
        s_flag = db.session.query(SiteSetting).filter_by(key="theme_enabled").first()
        if s_flag and (s_flag.value or "").strip() == "1":
            enabled = True
        if not enabled:
            return "", 404
        s_css = db.session.query(SiteSetting).filter_by(key="custom_theme_css").first()
        css = s_css.value if s_css and s_css.value else ""
        from flask import Response
        return Response(css, mimetype="text/css")
    except Exception:
        return "", 404


@main_bp.route("/theme_asset/id/<int:asset_id>")
def theme_asset_by_id(asset_id: int):
    try:
        sa = db.session.get(SiteAsset, asset_id)
        if not sa:
            return "", 404
        from flask import Response
        return Response(sa.data, mimetype=sa.mimetype or "application/octet-stream")
    except Exception:
        return "", 404


@main_bp.route("/theme_asset/<path:filename>")
def theme_asset_by_name(filename: str):
    try:
        sa = db.session.query(SiteAsset).filter_by(filename=filename).first()
        if not sa:
            return "", 404
        from flask import Response
        return Response(sa.data, mimetype=sa.mimetype or "application/octet-stream")
    except Exception:
        return "", 404


@main_bp.route("/theme_asset/thumb/<int:asset_id>")
def theme_asset_thumb(asset_id: int):
    try:
        sa = db.session.get(SiteAsset, asset_id)
        if not sa:
            return "", 404
        from flask import Response
        return Response(sa.data, mimetype=sa.mimetype or "image/png")
    except Exception:
        return "", 404
