from functools import wraps
from flask import session, redirect, url_for, abort

from src.panel.models import db


def requires_permission(permission_name):
    """Decorator to require a specific permission for a view.

    Usage:
        @requires_permission('admin.user_management')
        def view():
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return redirect(url_for('login'))

            try:
                from src.panel.models import User
                from rbac import has_permission

                user = db.session.get(User, user_id)
                if not user:
                    return redirect(url_for('login'))

                if not has_permission(user, permission_name):
                    abort(403)

            except Exception:
                # If RBAC system absent or fails, deny access by default
                abort(403)

            return f(*args, **kwargs)

        return wrapped

    return decorator
