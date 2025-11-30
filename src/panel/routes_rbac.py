"""
RBAC Management Routes

Provides web interface for managing roles, permissions, and user assignments.
"""

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   url_for)

from app import User, app, db
from models_extended import UserActivity
from rbac import (Permission, Role, RolePermission, UserRole,
                  assign_role_to_user, get_user_permissions, has_permission,
                  initialize_rbac_system, revoke_role_from_user)


def require_system_admin(f):
    """Decorator to require system admin access."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            flash("Please log in", "error")
            return redirect(url_for("login"))

        user = db.session.get(User, user_id)
        if not user or not user.is_system_admin():
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


# ========== RBAC MANAGEMENT ROUTES ==========

# ========== RBAC MANAGEMENT ROUTES ==========


@app.route("/admin/rbac/roles", methods=["GET"])
@require_system_admin
def admin_rbac_roles():
    """Manage roles and permissions."""
    roles = Role.query.order_by(Role.name).all()
    permissions = Permission.query.order_by(Permission.category, Permission.name).all()

    # Group permissions by category
    permission_groups = {}
    for perm in permissions:
        if perm.category not in permission_groups:
            permission_groups[perm.category] = []
        permission_groups[perm.category].append(perm)

    return render_template(
        "admin_rbac_roles.html",
        roles=roles,
        permissions=permissions,
        permission_groups=permission_groups,
    )


@app.route("/admin/rbac/roles/create", methods=["POST"])
@require_system_admin
def admin_rbac_create_role():
    """Create a new role."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    permission_ids = request.form.getlist("permissions")

    if not name:
        flash("Role name is required", "error")
        return redirect(url_for("admin_rbac_roles"))

    # Check if role already exists
    existing = Role.query.filter_by(name=name).first()
    if existing:
        flash("Role name already exists", "error")
        return redirect(url_for("admin_rbac_roles"))

    # Create role
    role = Role(name=name, description=description)
    db.session.add(role)
    db.session.flush()

    # Add permissions
    for perm_id in permission_ids:
        if perm_id.isdigit():
            role_perm = RolePermission(role_id=role.id, permission_id=int(perm_id))
            db.session.add(role_perm)

    db.session.commit()

    flash(f'Role "{name}" created successfully', "success")
    return redirect(url_for("admin_rbac_roles"))


@app.route("/admin/rbac/roles/<int:role_id>/edit", methods=["GET", "POST"])
@require_system_admin
def admin_rbac_edit_role(role_id):
    """Edit an existing role."""
    role = Role.query.get_or_404(role_id)

    if request.method == "POST":
        # Prevent editing system roles
        if role.is_system_role:
            flash("Cannot modify system roles", "error")
            return redirect(url_for("admin_rbac_roles"))

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        permission_ids = set(request.form.getlist("permissions"))

        if not name:
            flash("Role name is required", "error")
            return redirect(url_for("admin_rbac_edit_role", role_id=role_id))

        # Update role
        role.name = name
        role.description = description

        # Update permissions
        current_perms = {str(rp.permission_id) for rp in role.role_permissions}
        new_perms = {p for p in permission_ids if p.isdigit()}

        # Remove permissions
        to_remove = current_perms - new_perms
        for perm_id in to_remove:
            role_perm = RolePermission.query.filter_by(
                role_id=role.id, permission_id=int(perm_id)
            ).first()
            if role_perm:
                db.session.delete(role_perm)

        # Add new permissions
        to_add = new_perms - current_perms
        for perm_id in to_add:
            role_perm = RolePermission(role_id=role.id, permission_id=int(perm_id))
            db.session.add(role_perm)

        db.session.commit()

        flash(f'Role "{name}" updated successfully', "success")
        return redirect(url_for("admin_rbac_roles"))

    # GET request - show edit form
    permissions = Permission.query.order_by(Permission.category, Permission.name).all()
    role_permission_ids = {rp.permission_id for rp in role.role_permissions}

    # Group permissions by category
    permission_groups = {}
    for perm in permissions:
        if perm.category not in permission_groups:
            permission_groups[perm.category] = []
        permission_groups[perm.category].append(perm)

    return render_template(
        "admin_rbac_edit_role.html",
        role=role,
        permissions=permissions,
        permission_groups=permission_groups,
        role_permission_ids=role_permission_ids,
    )


@app.route("/admin/rbac/roles/<int:role_id>/delete", methods=["POST"])
@require_system_admin
def admin_rbac_delete_role(role_id):
    """Delete a role."""
    role = Role.query.get_or_404(role_id)

    if role.is_system_role:
        flash("Cannot delete system roles", "error")
        return redirect(url_for("admin_rbac_roles"))

    # Check if role is assigned to any users
    user_count = UserRole.query.filter_by(role_id=role_id).count()
    if user_count > 0:
        flash(f"Cannot delete role: assigned to {user_count} users", "error")
        return redirect(url_for("admin_rbac_roles"))

    # Delete role and its permissions
    RolePermission.query.filter_by(role_id=role_id).delete()
    db.session.delete(role)
    db.session.commit()

    flash(f'Role "{role.name}" deleted successfully', "success")
    return redirect(url_for("admin_rbac_roles"))


@app.route("/admin/rbac/users", methods=["GET"])
@require_system_admin
def admin_rbac_users():
    """Manage user role assignments."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()

    query = User.query

    if search:
        query = query.filter(User.email.like(f"%{search}%"))

    pagination = query.order_by(User.email).paginate(
        page=page, per_page=25, error_out=False
    )

    roles = Role.query.order_by(Role.name).all()

    return render_template(
        "admin_rbac_users.html",
        users=pagination.items,
        pagination=pagination,
        roles=roles,
        search=search,
    )


@app.route("/admin/rbac/users/<int:user_id>/assign-role", methods=["POST"])
@require_system_admin
def admin_rbac_assign_role(user_id):
    """Assign a role to a user."""
    user = User.query.get_or_404(user_id)
    role_id = request.form.get("role_id")
    expires_at = request.form.get("expires_at")

    if not role_id or not role_id.isdigit():
        flash("Invalid role selected", "error")
        return redirect(url_for("admin_rbac_users"))

    role = Role.query.get_or_404(int(role_id))

    # Parse expiration date
    expires_datetime = None
    if expires_at:
        try:
            from datetime import datetime

            expires_datetime = datetime.fromisoformat(expires_at)
        except ValueError:
            flash("Invalid expiration date format", "error")
            return redirect(url_for("admin_rbac_users"))

    # Assign role
    admin_user_id = request.session.get("user_id")
    assign_role_to_user(user_id, int(role_id), admin_user_id, expires_datetime)

    # Log the activity
    db.session.add(
        UserActivity(
            user_id=user_id,
            activity_type="role_assigned",
            details=f'Role "{role.name}" assigned by admin {admin_user_id}',
        )
    )
    db.session.commit()

    flash(f'Role "{role.name}" assigned to {user.email}', "success")
    return redirect(url_for("admin_rbac_users"))


@app.route("/admin/rbac/users/<int:user_id>/revoke-role", methods=["POST"])
@require_system_admin
def admin_rbac_revoke_role(user_id):
    """Revoke a role from a user."""
    user = User.query.get_or_404(user_id)
    role_id = request.form.get("role_id")

    if not role_id or not role_id.isdigit():
        flash("Invalid role selected", "error")
        return redirect(url_for("admin_rbac_users"))

    role = Role.query.get_or_404(int(role_id))

    success = revoke_role_from_user(user_id, int(role_id))

    if success:
        # Log the activity
        admin_user_id = request.session.get("user_id")
        db.session.add(
            UserActivity(
                user_id=user_id,
                activity_type="role_revoked",
                details=f'Role "{role.name}" revoked by admin {admin_user_id}',
            )
        )
        db.session.commit()

        flash(f'Role "{role.name}" revoked from {user.email}', "success")
    else:
        flash("Role assignment not found", "error")

    return redirect(url_for("admin_rbac_users"))


@app.route("/admin/rbac/initialize", methods=["POST"])
@require_system_admin
def admin_rbac_initialize():
    """Initialize RBAC system with default permissions and roles."""
    try:
        initialize_rbac_system()
        flash("RBAC system initialized successfully", "success")
    except Exception as e:
        flash(f"Failed to initialize RBAC system: {str(e)}", "error")

    return redirect(url_for("admin_rbac_roles"))


@app.route("/api/rbac/user/<int:user_id>/permissions", methods=["GET"])
@require_system_admin
def api_rbac_user_permissions(user_id):
    """Get user permissions via API."""
    user = User.query.get_or_404(user_id)
    permissions = list(get_user_permissions(user))

    return jsonify(
        {"user_id": user_id, "email": user.email, "permissions": permissions}
    )


@app.route("/api/rbac/check-permission", methods=["POST"])
def api_rbac_check_permission():
    """Check if current user has a specific permission."""
    user_id = request.session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    permission_name = request.json.get("permission")
    if not permission_name:
        return jsonify({"error": "Permission name required"}), 400

    has_perm = has_permission(user, permission_name)

    return jsonify(
        {"user_id": user_id, "permission": permission_name, "granted": has_perm}
    )
