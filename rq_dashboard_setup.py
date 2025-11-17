"""
RQ Dashboard Integration
Provides web interface for monitoring background jobs
"""

from flask import Blueprint
import rq_dashboard

# Create RQ Dashboard blueprint
rq_dashboard_bp = Blueprint('rq_dashboard', __name__)


def setup_rq_dashboard(app):
    """
    Setup RQ Dashboard for monitoring Redis Queue jobs
    
    Access at: http://localhost:8080/rq
    
    Configuration:
    - Set REDIS_URL in your config
    - Optionally set RQ_DASHBOARD_REDIS_URL to use different Redis instance
    """
    
    # Configure RQ Dashboard
    app.config.setdefault('RQ_DASHBOARD_REDIS_URL', app.config.get('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    
    # Register RQ Dashboard blueprint
    # This provides a web UI at /rq for monitoring jobs
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='/rq')
    
    app.logger.info("RQ Dashboard enabled at /rq")
    
    return app


# Middleware to protect RQ Dashboard with authentication
def require_admin_for_rq_dashboard(app):
    """Add authentication requirement for RQ Dashboard"""
    from functools import wraps
    from flask import session, redirect, url_for, request
    
    @app.before_request
    def check_rq_dashboard_auth():
        """Require admin access for RQ Dashboard"""
        if request.path.startswith('/rq'):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            # Import here to avoid circular dependency
            from app import db, User
            user = db.session.get(User, session['user_id'])
            if not user or not user.is_system_admin():
                return "Access Denied: Admin privileges required", 403
    
    return app
