# Authentication Pattern Update for routes_config.py

## Current State
The routes in `routes_config.py` currently use `flask_login` decorators and methods:
- `@login_required`
- `current_user.is_system_admin`
- `current_user.id`

## Required Change
The main `app.py` uses session-based authentication instead. All routes need to be updated to use the helper function pattern.

## Pattern to Apply

Replace:
```python
@config_bp.route("/admin/some-route")
@login_required
def some_route():
    if not current_user.is_system_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))

    # route logic using current_user.id
```

With:
```python
@config_bp.route("/admin/some-route")
def some_route():
    redirect_response, user = require_admin()
    if redirect_response:
        return redirect_response

    # route logic using user.id
```

For API routes:
```python
@config_bp.route("/api/some-route")
def some_api_route():
    redirect_response, user = require_admin()
    if redirect_response:
        return jsonify({"success": False, "message": "Access denied"}), 403

    # API logic using user.id
```

## Helper Function
The `require_admin()` helper is already defined at the top of routes_config.py:

```python
def require_admin():
    """Check if current user is admin, redirect if not."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login")), None

    user = db.session.get(User, user_id)
    if not is_system_admin_user(user):
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard")), None

    return None, user
```

## Routes to Update
All routes in routes_config.py from line 40 onwards need this pattern applied.

## Testing
After updating, run:
```bash
python -m pytest tests/test_ptero_eggs_features.py -v
```

All tests should pass once the authentication pattern is consistently applied.
