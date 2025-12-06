import logging
from typing import Tuple

from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)


def wants_json_response():
    """Check if client wants JSON response."""
    return (
        request.accept_mimetypes.best == "application/json"
        or request.path.startswith("/api/")
    )


def bad_request(e) -> Tuple:
    """Handle 400 Bad Request errors."""
    logger.warning(f"400 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Bad Request",
            "message": str(e),
            "status": 400
        }), 400
    
    return render_template("400.html", error=e), 400


def unauthorized(e) -> Tuple:
    """Handle 401 Unauthorized errors."""
    logger.warning(f"401 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required",
            "status": 401
        }), 401
    
    return render_template("401.html", error=e), 401


def forbidden(e) -> Tuple:
    """Handle 403 Forbidden errors."""
    logger.warning(f"403 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Forbidden",
            "message": "You don't have permission to access this resource",
            "status": 403
        }), 403
    
    return render_template("403.html", error=e), 403


def page_not_found(e) -> Tuple:
    """Handle 404 Not Found errors."""
    logger.warning(f"404 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found",
            "status": 404
        }), 404
    
    return render_template("404.html", error=e), 404


def method_not_allowed(e) -> Tuple:
    """Handle 405 Method Not Allowed errors."""
    logger.warning(f"405 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Method Not Allowed",
            "message": str(e),
            "status": 405
        }), 405
    
    return render_template("405.html", error=e), 405


def too_many_requests(e) -> Tuple:
    """Handle 429 Too Many Requests errors."""
    logger.warning(f"429 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again later.",
            "status": 429
        }), 429
    
    return render_template("429.html", error=e), 429


def internal_error(e) -> Tuple:
    """Handle 500 Internal Server Error."""
    logger.error(f"500 error: {e}", exc_info=True)
    
    if wants_json_response():
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status": 500
        }), 500
    
    return render_template("500.html", error=e), 500


def service_unavailable(e) -> Tuple:
    """Handle 503 Service Unavailable errors."""
    logger.error(f"503 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Service Unavailable",
            "message": "The service is temporarily unavailable",
            "status": 503
        }), 503
    
    return render_template("503.html", error=e), 503


# Export all error handlers
__all__ = [
    "bad_request",
    "unauthorized",
    "forbidden",
    "page_not_found",
    "method_not_allowed",
    "too_many_requests",
    "internal_error",
    "service_unavailable",
]
