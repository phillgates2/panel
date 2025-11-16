"""
API Rate Limiting Configuration
Implements rate limiting for API endpoints to prevent abuse
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import logging

logger = logging.getLogger(__name__)


def get_user_id_or_ip():
    """Get user ID if logged in, otherwise use IP address for rate limiting"""
    from flask import session
    return session.get('user_id', get_remote_address())


def setup_rate_limiting(app):
    """
    Configure rate limiting for the Flask application
    
    Default limits:
    - 100 requests per hour for general endpoints
    - 20 requests per minute for login
    - 30 requests per minute for API endpoints
    """
    
    limiter = Limiter(
        app=app,
        key_func=get_user_id_or_ip,
        default_limits=["200 per hour"],  # Global default
        storage_uri=app.config.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        storage_options={"socket_connect_timeout": 30},
        strategy="fixed-window",  # or "moving-window" for more accuracy
        headers_enabled=True,  # Add X-RateLimit headers to responses
    )
    
    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        logger.warning(f"Rate limit exceeded for {get_remote_address()}: {e.description}")
        return {
            "error": "Rate limit exceeded",
            "message": str(e.description)
        }, 429
    
    logger.info("Rate limiting enabled")
    
    return limiter


# Example usage in routes:
# from rate_limiting import limiter
#
# @app.route('/api/endpoint')
# @limiter.limit("30 per minute")
# def api_endpoint():
#     return jsonify({"status": "ok"})
#
# @app.route('/login', methods=['POST'])
# @limiter.limit("20 per minute")
# def login():
#     ...
