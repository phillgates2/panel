"""
CSRF Protection Module

Provides CSRF token generation, validation, and middleware for Flask applications.
"""

import hashlib
import hmac
import secrets
from flask import request, session, abort


def generate_csrf_token():
    """Generate a new CSRF token for the current session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def verify_csrf():
    """Verify CSRF token from request."""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token:
        abort(400, "CSRF token missing")

    expected_token = session.get("csrf_token")
    if not expected_token:
        abort(400, "CSRF token not found in session")

    # Use constant-time comparison
    if not hmac.compare_digest(token, expected_token):
        abort(400, "CSRF token invalid")


def ensure_csrf_after(response):
    """Ensure CSRF token is set after request processing."""
    # Generate token if not present
    generate_csrf_token()
    return response


def ensure_csrf_for_templates():
    """Context processor to inject CSRF token into templates."""
    return {"csrf_token": generate_csrf_token()}


def ensure_theme_migration_once():
    """Ensure theme migration runs once per session."""
    # This is a placeholder - theme migration logic would go here
    pass
