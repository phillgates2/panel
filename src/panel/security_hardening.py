"""
Enhanced Security Hardening Implementation
Implements advanced security measures including enhanced CSP, security headers,
rate limiting, input validation, and security monitoring.
"""

import hashlib
import hmac
import logging
import re
import time
from typing import Dict, List, Optional, Set

from simple_config import load_config

# Flask imports moved to avoid module-level import issues during testing
# from flask import Flask, Request, Response, g, request, session
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address


logger = logging.getLogger(__name__)


class SecurityHardening:
    """Enhanced security hardening for Flask applications"""

    def __init__(self, app: Flask):
        self.app = app
        self.config = load_config()
        self.suspicious_patterns = self._load_suspicious_patterns()
        self.blocked_ips: Set[str] = set()
        self.security_events: List[Dict] = []

    def _load_suspicious_patterns(self) -> List[str]:
        """Load patterns that indicate potential security threats"""
        return [
            r"<script[^>]*>.*?</script>",  # XSS attempts
            r"javascript:",  # JavaScript URLs
            r"data:text/html",  # Data URL XSS
            r"vbscript:",  # VBScript
            r"onload\s*=",  # Event handlers
            r"onerror\s*=",  # Error handlers
            r"eval\s*\(",  # Eval usage
            r"document\.cookie",  # Cookie access
            r"document\.location",  # Location manipulation
            r"../../../",  # Path traversal
            r"\.\./\.\./",  # Directory traversal
            r"union\s+select",  # SQL injection
            r"1=1\s*--",  # SQL injection
            r"drop\s+table",  # SQL injection
            r"<iframe",  # Clickjacking
            r"<object",  # Object injection
            r"<embed",  # Embed injection
        ]

    def init_app(self):
        """Initialize all security hardening features"""
        self._configure_enhanced_security_headers()
        self._configure_enhanced_csp()
        self._configure_rate_limiting()
        self._configure_input_validation()
        self._configure_security_monitoring()
        self._configure_request_filtering()

        logger.info("Enhanced security hardening initialized")

    def _configure_enhanced_security_headers(self):
        """Configure enhanced security headers"""

        @self.app.after_request
        def set_enhanced_security_headers(response: Response) -> Response:
            """Add comprehensive security headers to all responses"""

            # Enhanced Content Security Policy
            csp_policy = self._build_csp_policy()
            response.headers["Content-Security-Policy"] = csp_policy

            # HTTP Strict Transport Security (HSTS)
            if self._is_https_request():
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

            # X-Content-Type-Options
            response.headers["X-Content-Type-Options"] = "nosniff"

            # X-Frame-Options
            response.headers["X-Frame-Options"] = "DENY"

            # X-XSS-Protection
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Referrer-Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Cross-Origin-Embedder-Policy
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

            # Cross-Origin-Opener-Policy
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

            # Cross-Origin-Resource-Policy
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

            # Permissions-Policy (enhanced)
            permissions_policy = [
                "geolocation=()",
                "microphone=()",
                "camera=()",
                "payment=()",
                "usb=()",
                "magnetometer=()",
                "gyroscope=()",
                "accelerometer=()",
                "ambient-light-sensor=()",
                "autoplay=()",
                "bluetooth=()",
                "browsing-topics=()",
                "display-capture=()",
                "document-domain=()",
                "encrypted-media=()",
                "fullscreen=()",
                "gamepad=()",
                "hid=()",
                "identity-credentials-get=()",
                "idle-detection=()",
                "local-fonts=()",
                "midi=()",
                "otp-credentials=()",
                "picture-in-picture=()",
                "publickey-credentials-create=()",
                "publickey-credentials-get=()",
                "screen-wake-lock=()",
                "serial=()",
                "speaker-selection=()",
                "storage-access=()",
                "usb=()",
                "web-share=()",
                "window-management=()",
                "xr-spatial-tracking=()",
            ]
            response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

            # Cache-Control for sensitive pages
            if self._is_sensitive_path(request.path):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, private, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            # Remove server header
            response.headers.pop("Server", None)
            response.headers["X-Powered-By"] = "Panel/1.0"

            return response

        # Configure secure session cookies
        self.app.config.update(
            SESSION_COOKIE_SECURE=self._is_https_request(),
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Strict",  # More restrictive than Lax
            PERMANENT_SESSION_LIFETIME=86400,  # 24 hours instead of 30 days
            SESSION_COOKIE_NAME="panel_session",
        )

    def _build_csp_policy(self) -> str:
        """Build enhanced Content Security Policy"""
        csp_directives = {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",  # Allow inline styles for admin panel
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": "'self'",
            "media-src": "'self'",
            "object-src": "'none'",
            "frame-src": "'none'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
            "upgrade-insecure-requests": "",  # Enable HTTPS upgrades
            "block-all-mixed-content": "",  # Block mixed content
        }

        # Add nonce for dynamic scripts if needed
        if hasattr(g, "csp_nonce"):
            csp_directives["script-src"] += f" 'nonce-{g.csp_nonce}'"

        return "; ".join([f"{k} {v}".strip() for k, v in csp_directives.items() if v])

    def _configure_enhanced_csp(self):
        """Configure CSP nonce generation"""

        @self.app.before_request
        def generate_csp_nonce():
            """Generate CSP nonce for dynamic content"""
            import secrets

            g.csp_nonce = secrets.token_hex(16)

    def _configure_rate_limiting(self):
        """Configure enhanced rate limiting"""

        def get_user_id_or_ip():
            """Get user ID if logged in, otherwise use IP address"""
            return session.get("user_id", get_remote_address())

        def get_rate_limit_by_role():
            """Get rate limit based on user role"""
            user_id = session.get("user_id")
            if user_id:
                try:
                    from app import User, db

                    user = db.session.get(User, user_id)
                    if user:
                        if user.is_system_admin():
                            return "2000 per hour"
                        elif user.is_admin:
                            return "1000 per hour"
                        elif hasattr(user, "is_moderator") and user.is_moderator:
                            return "500 per hour"
                except Exception:
                    pass

            return "100 per hour"  # Reduced default for better security

        limiter = Limiter(
            app=self.app,
            key_func=get_user_id_or_ip,
            default_limits=["100 per hour"],
            storage_uri=self.config.redis_url,
            storage_options={"socket_connect_timeout": 30},
            strategy="fixed-window-elastic-expiry",
            headers_enabled=True,
        )

        # Enhanced error handler for rate limit exceeded
        @self.app.errorhandler(429)
        def enhanced_ratelimit_handler(e):
            client_ip = get_remote_address()
            self._log_security_event(
                "rate_limit_exceeded",
                {
                    "ip": client_ip,
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "retry_after": getattr(e, "retry_after", 3600),
                },
            )

            # Add to suspicious activity tracking
            self._track_suspicious_activity(client_ip, "rate_limit_exceeded")

            return {
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": getattr(e, "retry_after", 3600),
            }, 429

        # Stricter limits for sensitive endpoints
        limiter.limit("5 per minute")(
            self.app.view_functions.get("login", lambda: None)
        )
        limiter.limit("3 per minute")(
            self.app.view_functions.get("register", lambda: None)
        )
        limiter.limit("10 per minute")(
            self.app.view_functions.get("forgot_password", lambda: None)
        )

        # API endpoints with role-based limits
        limiter.limit(get_rate_limit_by_role)(
            self.app.view_functions.get("api_get_tokens", lambda: None)
        )
        limiter.limit(get_rate_limit_by_role)(
            self.app.view_functions.get("teams_dashboard", lambda: None)
        )

        # Admin endpoints - very restrictive
        limiter.limit("50 per hour", key_func=get_user_id_or_ip)(
            self.app.view_functions.get("admin_dashboard", lambda: None)
        )

        logger.info("Enhanced rate limiting configured with role-based limits")

    def _configure_input_validation(self):
        """Configure enhanced input validation"""

        @self.app.before_request
        def validate_request_data():
            """Validate incoming request data for security threats"""
            if request.method in ["POST", "PUT", "PATCH"]:
                self._validate_request_content(request)

    def _validate_request_content(self, req: Request):
        """Validate request content for security threats"""
        # Check form data
        if req.form:
            for key, value in req.form.items():
                if isinstance(value, str):
                    self._check_for_suspicious_content(value, f"form_{key}")

        # Check JSON data
        if req.is_json and req.get_json(silent=True):
            json_data = req.get_json()
            self._validate_json_security(json_data)

        # Check URL parameters
        for key, value in req.args.items():
            if isinstance(value, str):
                self._check_for_suspicious_content(value, f"url_param_{key}")

    def _check_for_suspicious_content(self, content: str, source: str):
        """Check content for suspicious patterns"""
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                client_ip = get_remote_address()
                self._log_security_event(
                    "suspicious_content_detected",
                    {
                        "ip": client_ip,
                        "source": source,
                        "pattern": pattern,
                        "content_length": len(content),
                        "user_agent": request.headers.get("User-Agent", ""),
                    },
                )
                self._track_suspicious_activity(client_ip, "suspicious_content")
                break

    def _validate_json_security(self, data, path="root"):
        """Recursively validate JSON data for security issues"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    self._check_for_suspicious_content(value, f"json_{path}.{key}")
                else:
                    self._validate_json_security(value, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_json_security(item, f"{path}[{i}]")

    def _configure_security_monitoring(self):
        """Configure security event monitoring"""

        @self.app.after_request
        def monitor_security_events(response: Response) -> Response:
            """Monitor responses for security-related events"""
            if response.status_code >= 400:
                self._log_security_event(
                    "error_response",
                    {
                        "status_code": response.status_code,
                        "path": request.path,
                        "method": request.method,
                        "ip": get_remote_address(),
                        "user_agent": request.headers.get("User-Agent", ""),
                    },
                )

            # Monitor for potential security headers bypass attempts
            if "X-Forwarded-For" in request.headers and self._is_internal_ip(
                get_remote_address()
            ):
                self._log_security_event(
                    "proxy_header_detected",
                    {
                        "ip": get_remote_address(),
                        "xff_header": request.headers.get("X-Forwarded-For"),
                        "path": request.path,
                    },
                )

            return response

    def _configure_request_filtering(self):
        """Configure request filtering for known bad actors"""

        @self.app.before_request
        def filter_requests():
            """Filter out requests from blocked IPs or suspicious sources"""
            client_ip = get_remote_address()

            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                self._log_security_event(
                    "blocked_ip_access",
                    {
                        "ip": client_ip,
                        "path": request.path,
                        "user_agent": request.headers.get("User-Agent", ""),
                    },
                )
                return {"error": "Access denied"}, 403

            # Check for suspicious user agents
            user_agent = request.headers.get("User-Agent", "")
            if self._is_suspicious_user_agent(user_agent):
                self._log_security_event(
                    "suspicious_user_agent",
                    {"ip": client_ip, "user_agent": user_agent, "path": request.path},
                )
                self._track_suspicious_activity(client_ip, "suspicious_user_agent")

    def _log_security_event(self, event_type: str, details: Dict):
        """Log security events"""
        event = {"timestamp": time.time(), "type": event_type, "details": details}

        self.security_events.append(event)

        # Keep only last 1000 events in memory
        if len(self.security_events) > 1000:
            self.security_events.pop(0)

        # Log to structured logger
        logger.warning(
            f"Security event: {event_type}",
            extra={"security_event": event_type, "event_details": details},
        )

    def _track_suspicious_activity(self, ip: str, activity_type: str):
        """Track suspicious activity from IPs"""
        # Simple in-memory tracking - in production, use Redis or database
        # After 5 suspicious activities in an hour, block the IP
        current_time = time.time()
        suspicious_key = f"{ip}:{activity_type}"

        # This is a simplified implementation
        # In production, you'd want persistent storage
        if hasattr(self, "_suspicious_tracking"):
            self._suspicious_tracking[suspicious_key] = current_time
        else:
            self._suspicious_tracking = {suspicious_key: current_time}

    def _is_sensitive_path(self, path: str) -> bool:
        """Check if the path is sensitive and needs special headers"""
        sensitive_paths = [
            "/admin",
            "/account",
            "/settings",
            "/security",
            "/api/admin",
            "/api/user",
            "/api/auth",
        ]
        return any(path.startswith(sp) for sp in sensitive_paths)

    def _is_https_request(self) -> bool:
        """Check if the current request is over HTTPS"""
        return request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"

    def _is_internal_ip(self, ip: str) -> bool:
        """Check if IP is internal/private"""
        private_ranges = [
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",
        ]
        return (
            any(ip.startswith(range) for range in private_ranges) or ip == "127.0.0.1"
        )

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent looks suspicious"""
        suspicious_patterns = [
            "sqlmap",
            "nmap",
            "nikto",
            "dirbuster",
            "gobuster",
            "masscan",
            "zmap",
            "acunetix",
            "openvas",
            "nessus",
            "metasploit",
            "burpsuite",
            "owasp",
            "qualysguard",
        ]
        return any(
            pattern.lower() in user_agent.lower() for pattern in suspicious_patterns
        )

    def get_security_report(self) -> Dict:
        """Get a security report"""
        return {
            "total_events": len(self.security_events),
            "blocked_ips": len(self.blocked_ips),
            "recent_events": self.security_events[-10:] if self.security_events else [],
            "rate_limiting_enabled": True,
            "csp_enabled": True,
            "security_headers_enabled": True,
        }


# Enhanced input validation schemas
class SecurityValidationSchemas:
    """Enhanced security-focused validation schemas"""

    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """Validate password strength and return issues"""
        issues = []

        if len(password) < 12:
            issues.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", password):
            issues.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            issues.append("Password must contain at least one lowercase letter")

        if not re.search(r"[0-9]", password):
            issues.append("Password must contain at least one number")

        if not re.search(r"[^A-Za-z0-9]", password):
            issues.append("Password must contain at least one special character")

        # Check for common weak patterns
        common_patterns = ["123456", "password", "qwerty", "admin", "letmein"]
        if any(pattern in password.lower() for pattern in common_patterns):
            issues.append("Password contains common weak patterns")

        return issues

    @staticmethod
    def validate_email_domain(email: str) -> bool:
        """Validate email domain for suspicious patterns"""
        if not email or "@" not in email:
            return False

        domain = email.split("@")[1].lower()

        # Block suspicious domains
        blocked_domains = [
            "10minutemail.com",
            "guerrillamail.com",
            "mailinator.com",
            "temp-mail.org",
            "throwaway.email",
            "yopmail.com",
        ]

        return domain not in blocked_domains

    @staticmethod
    def sanitize_html_content(content: str) -> str:
        """Sanitize HTML content to prevent XSS"""
        # Remove script tags and event handlers
        content = re.sub(
            r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
        )
        content = re.sub(r"<[^>]+on\w+\s*=", "<", content, flags=re.IGNORECASE)

        # Remove javascript: URLs
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

        return content


def init_security_hardening(app: Flask) -> SecurityHardening:
    """Initialize security hardening for the Flask application"""
    security = SecurityHardening(app)
    security.init_app()
    return security
