"""
Security Extensions

This module initializes security-related Flask extensions and configurations.
"""

import os
from typing import Any, Dict

from flask import Flask
from flask_babel import Babel
from flask_talisman import Talisman

from src.panel.gdpr_compliance import init_gdpr_compliance
from src.panel.rate_limiting import init_rate_limiting_admin, setup_rate_limiting


def init_security_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize security-related Flask extensions.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary of initialized security extension instances.
    """
    # Initialize GDPR compliance
    init_gdpr_compliance(app)

    # Initialize advanced rate limiting
    limiter = setup_rate_limiting(app)
    init_rate_limiting_admin(app)

    # Initialize security headers with Talisman
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'media-src': "'self'",
        'object-src': "'none'",
    }

    talisman = Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        force_https=os.environ.get('FLASK_ENV') == 'production',
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        strict_transport_security_include_subdomains=True,
        session_cookie_secure=os.environ.get('FLASK_ENV') == 'production',
        session_cookie_http_only=True,
        session_cookie_samesite='Lax',
    )

    # Initialize Babel for internationalization
    babel = Babel(app)

    # Configure enhanced security hardening
    security_hardening = {
        'content_security_policy': csp,
        'https_enforced': os.environ.get('FLASK_ENV') == 'production',
        'secure_cookies': os.environ.get('FLASK_ENV') == 'production',
        'rate_limiting_enabled': True,
        'gdpr_compliance_enabled': True,
    }

    return {
        "limiter": limiter,
        "talisman": talisman,
        "babel": babel,
        "security_hardening": security_hardening,
    }