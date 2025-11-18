from functools import wraps
from flask import redirect, url_for, session, current_app, request, flash
from app import db


def current_user():
    """Return the current User instance based on session['user_id'] or None."""
    user_id = session.get('user_id')
    if user_id:
        try:
            return db.session.get(db.Model._decl_class_registry.get('User'), user_id)
        except Exception:
            # Fallback: query by id via User class import
            try:
                from app import User
                return db.session.get(User, user_id)
            except Exception:
                return None
    return None


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Prefer the User model role check
        try:
            from app import User
            uid = session.get('user_id')
            if uid:
                u = db.session.get(User, uid)
                if u and (getattr(u, 'role', None) in ('system_admin', 'server_admin') or u.is_system_admin()):
                    return f(*args, **kwargs)
        except Exception:
            pass

        # Fallback: legacy session flag
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)

        flash('Admin access required', 'error')
        return redirect(url_for('cms.admin_login', next=request.path))

    return wrapped
