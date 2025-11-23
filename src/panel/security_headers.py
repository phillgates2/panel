"""
Security Headers Configuration
Implements CSP, HSTS, and other security best practices
"""

from flask import request


def configure_security_headers(app):
    """Configure security headers for the Flask application"""

    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""

        # Content Security Policy
        # Adjust these directives based on your application's needs
        csp_policy = {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust as needed
            "style-src": "'self' 'unsafe-inline'",  # For inline styles
            "img-src": "'self' data: https:",  # Allow images from self, data URIs, and HTTPS
            "font-src": "'self' data:",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",  # Prevent clickjacking
            "base-uri": "'self'",
            "form-action": "'self'",
        }

        csp_header = "; ".join([f"{key} {value}" for key, value in csp_policy.items()])
        response.headers["Content-Security-Policy"] = csp_header

        # HTTP Strict Transport Security (HSTS)
        # Only enable in production with HTTPS
        if not app.debug and app.config.get("PREFERRED_URL_SCHEME") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # X-Content-Type-Options
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # Cache-Control for sensitive pages
        if request.path.startswith("/admin") or request.path.startswith("/account"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    # Configure secure session cookies
    app.config.update(
        SESSION_COOKIE_SECURE=not app.debug,  # Only send cookies over HTTPS in production
        SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access to session cookie
        SESSION_COOKIE_SAMESITE="Lax",  # CSRF protection
        PERMANENT_SESSION_LIFETIME=2592000,  # 30 days
    )

    return app


# Additional security middleware
def configure_cors(app, allowed_origins=None):
    """Configure CORS if needed for API endpoints"""
    if allowed_origins is None:
        allowed_origins = []

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response

    return app
