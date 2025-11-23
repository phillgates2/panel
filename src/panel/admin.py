# src/admin.py - Admin management routes

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import text

from models import User
from models_extended import IPBlacklist, IPWhitelist, SecurityEvent, UserGroup, UserGroupMembership
from structured_logging import log_security_event

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================================
# TEAM MANAGEMENT ROUTES
# ============================================================================


@admin_bp.route("/teams", methods=["GET"])
def teams_dashboard():
    """Team management dashboard."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("dashboard"))

    teams = UserGroup.query.all()
    team_data = []

    for team in teams:
        members = UserGroupMembership.query.filter_by(group_id=team.id).all()
        member_users = []
        for membership in members:
            member_user = db.session.get(User, membership.user_id)
            if member_user:
                member_users.append(member_user)

        team_data.append({"team": team, "members": member_users, "member_count": len(member_users)})

    return render_template("teams.html", user=user, teams=team_data)


@admin_bp.route("/teams/create", methods=["POST"])
def create_team():
    """Create a new team."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("admin.teams_dashboard"))

    team_name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not team_name:
        flash("Team name is required", "error")
        return redirect(url_for("admin.teams_dashboard"))

    try:
        new_team = UserGroup(
            name=team_name,
            description=description,
            permissions=json.dumps([]),  # Empty permissions array
        )
        db.session.add(new_team)
        db.session.commit()
        flash(f"Team '{team_name}' created successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating team: {str(e)}", "error")

    return redirect(url_for("admin.teams_dashboard"))


@admin_bp.route("/teams/<int:team_id>/add_member", methods=["POST"])
def add_team_member(team_id):
    """Add a member to a team."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("admin.teams_dashboard"))

    member_email = request.form.get("email", "").strip()

    if not member_email:
        flash("Member email is required", "error")
        return redirect(url_for("admin.teams_dashboard"))

    # Find user by email
    member_user = User.query.filter_by(email=member_email).first()
    if not member_user:
        flash("User not found", "error")
        return redirect(url_for("admin.teams_dashboard"))

    # Check if team exists
    team = db.session.get(UserGroup, team_id)
    if not team:
        flash("Team not found", "error")
        return redirect(url_for("admin.teams_dashboard"))

    # Check if already a member
    existing = UserGroupMembership.query.filter_by(user_id=member_user.id, group_id=team_id).first()
    if existing:
        flash("User is already a member of this team", "warning")
        return redirect(url_for("admin.teams_dashboard"))

    try:
        membership = UserGroupMembership(user_id=member_user.id, group_id=team_id)
        db.session.add(membership)
        db.session.commit()
        flash(
            f"Added {member_user.first_name} {member_user.last_name} to team '{team.name}'",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding member: {str(e)}", "error")

    return redirect(url_for("admin.teams_dashboard"))


# ============================================================================
# SECURITY MANAGEMENT ROUTES
# ============================================================================


@admin_bp.route("/security", methods=["GET"])
def security_dashboard():
    """Security management dashboard."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("dashboard"))

    # Get security data
    whitelist = IPWhitelist.query.filter_by(is_active=True).all()
    blacklist = IPBlacklist.query.filter_by(is_active=True).all()
    recent_events = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).limit(20).all()

    return render_template(
        "security.html",
        user=user,
        whitelist=whitelist,
        blacklist=blacklist,
        recent_events=recent_events,
    )


@admin_bp.route("/security/whitelist/add", methods=["POST"])
def add_to_whitelist():
    """Add IP to whitelist."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("admin.security_dashboard"))

    ip_address = request.form.get("ip_address", "").strip()
    description = request.form.get("description", "").strip()

    if not ip_address:
        flash("IP address is required", "error")
        return redirect(url_for("admin.security_dashboard"))

    # Validate IP address format
    import ipaddress

    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        flash("Invalid IP address format", "error")
        return redirect(url_for("admin.security_dashboard"))

    try:
        whitelist_entry = IPWhitelist(
            ip_address=ip_address, description=description, created_by=user.id
        )
        db.session.add(whitelist_entry)
        db.session.commit()

        # Log security event
        log_security_event(
            "ip_whitelisted", ip_address, user.id, f"IP {ip_address} added to whitelist"
        )

        flash(f"IP {ip_address} added to whitelist", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding IP to whitelist: {str(e)}", "error")

    return redirect(url_for("admin.security_dashboard"))


@admin_bp.route("/security/blacklist/add", methods=["POST"])
def add_to_blacklist():
    """Add IP to blacklist."""
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))

    user = db.session.get(User, uid)
    if not user or not user.is_system_admin():
        flash("Admin access required", "error")
        return redirect(url_for("admin.security_dashboard"))

    ip_address = request.form.get("ip_address", "").strip()
    reason = request.form.get("reason", "").strip()

    if not ip_address:
        flash("IP address is required", "error")
        return redirect(url_for("admin.security_dashboard"))

    # Validate IP address format
    import ipaddress

    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        flash("Invalid IP address format", "error")
        return redirect(url_for("admin.security_dashboard"))

    try:
        blacklist_entry = IPBlacklist(ip_address=ip_address, reason=reason, created_by=user.id)
        db.session.add(blacklist_entry)
        db.session.commit()

        # Log security event
        log_security_event(
            "ip_blacklisted", ip_address, user.id, f"IP {ip_address} blacklisted: {reason}"
        )

        flash(f"IP {ip_address} added to blacklist", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding IP to blacklist: {str(e)}", "error")

    return redirect(url_for("admin.security_dashboard"))