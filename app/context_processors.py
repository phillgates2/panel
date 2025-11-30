import os
from typing import Any, Dict

from flask import current_app, session

from app.db import db
from src.panel import models

# CDN Integration
CDN_ENABLED = os.environ.get("PANEL_CDN_ENABLED", "false").lower() == "true"
CDN_PROVIDER = os.environ.get(
    "PANEL_CDN_PROVIDER", "cloudflare"
)  # cloudflare or cloudfront
CDN_BASE_URL = os.environ.get("PANEL_CDN_BASE_URL", "https://cdn.panel.com")


def get_cdn_url(path):
    """Get CDN URL for static assets"""
    if CDN_ENABLED:
        return f"{CDN_BASE_URL}{path}"
    return path


def inject_user() -> Dict[str, Any]:
    """Inject `logged_in` and `current_user` into templates.
    Uses `session['user_id']` when present. Returns a simple boolean
    and the `User` instance (or None).

    Returns:
        Dictionary of template variables.
    """
    user = None
    user_id = session.get("user_id")
    if user_id:
        try:
            user = db.session.get(models.User, user_id)
        except Exception:
            user = None
    # theme enabled flag stored in DB (fallback to instance file for older installations
    theme_enabled = False
    try:
        s = db.session.query(models.SiteSetting).filter_by(key="theme_enabled").first()
        if s and s.value is not None:
            theme_enabled = s.value.strip() == "1"
        else:
            # fallback to instance file for older installations
            theme_flag = os.path.join(
                current_app.root_path, "instance", "theme_enabled"
            )
            if os.path.exists(theme_flag):
                with open(theme_flag, "r", encoding="utf-8") as f:
                    v = f.read().strip()
                    theme_enabled = v == "1"
    except Exception:
        theme_enabled = False

    # user theme preference (stored in SiteSetting as user_theme:<id>)
    user_theme_pref = None
    try:
        if user:
            k = f"user_theme:{user.id}"
            s_user_theme = db.session.query(models.SiteSetting).filter_by(key=k).first()
            if s_user_theme and (s_user_theme.value in ("dark", "light")):
                user_theme_pref = s_user_theme.value
    except Exception:
        user_theme_pref = None

    # site-wide flag to allow client theme toggle (default on)
    theme_toggle_enabled = True
    try:
        s_toggle = (
            db.session.query(models.SiteSetting)
            .filter_by(key="theme_toggle_enabled")
            .first()
        )
        if s_toggle and s_toggle.value is not None:
            theme_toggle_enabled = s_toggle.value.strip() == "1"
    except Exception:
        theme_toggle_enabled = True
    # optional forced theme when toggle disabled: 'dark'|'light'
    theme_forced = None
    try:
        s_forced = (
            db.session.query(models.SiteSetting).filter_by(key="theme_forced").first()
        )
        if s_forced and s_forced.value in ("dark", "light"):
            theme_forced = s_forced.value
    except Exception:
        theme_forced = None

    return dict(
        logged_in=bool(user),
        current_user=user,
        theme_enabled=theme_enabled,
        theme_toggle_enabled=theme_toggle_enabled,
        theme_forced=theme_forced,
        config=current_app.config,
        user_theme_pref=user_theme_pref,
        get_cdn_url=get_cdn_url,
    )
