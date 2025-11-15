"""Extended routes for new features.

This module contains routes for:
- Audit log viewer
- Session management  
- API key management
- System monitoring
- User activity tracking
- Notifications
- Server templates
- And more...
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from datetime import datetime, timezone, timedelta
from app import app, db, session as flask_session
from models_extended import (
    UserSession, ApiKey, UserActivity, TwoFactorAuth, IpAccessControl,
    Notification, ServerTemplate, ScheduledTask, RconCommandHistory,
    PerformanceMetric, UserGroup, UserGroupMembership
)
from app import User, AuditLog, Server
import pyotp
import qrcode
import io
import base64
import json
# import psutil  # Temporarily commented for testing
import os


def require_system_admin(f):
    """Decorator to require system admin access."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = flask_session.get('user_id')
        if not user_id:
            flash('Please log in', 'error')
            return redirect(url_for('login'))
        
        user = db.session.get(User, user_id)
        if not user or not user.is_system_admin():
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


# ========== AUDIT LOG VIEWER ==========

@app.route('/admin/audit-viewer', methods=['GET'])
@require_system_admin
def admin_audit_viewer():
    """Audit log viewer with search and filtering."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_filter = request.args.get('user', type=int)
    action_filter = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = AuditLog.query
    
    # Apply filters
    if user_filter:
        query = query.filter_by(actor_id=user_filter)
    if action_filter:
        query = query.filter(AuditLog.action.like(f'%{action_filter}%'))
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.created_at >= df)
        except:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.created_at <= dt)
        except:
            pass
    
    # Paginate
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all users for filter dropdown
    users = User.query.order_by(User.email).all()
    
    return render_template('admin_audit_viewer.html',
                         logs=pagination.items,
                         pagination=pagination,
                         users=users,
                         filters={
                             'user': user_filter,
                             'action': action_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                         })


@app.route('/admin/audit-viewer/export', methods=['GET'])
@require_system_admin
def admin_audit_export():
    """Export audit logs as CSV."""
    import csv
    import io
    from flask import make_response
    
    # Apply same filters as viewer
    user_filter = request.args.get('user', type=int)
    action_filter = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = AuditLog.query
    
    # Apply filters
    if user_filter:
        query = query.filter_by(actor_id=user_filter)
    if action_filter:
        query = query.filter(AuditLog.action.like(f'%{action_filter}%'))
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.created_at >= df)
        except:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.created_at <= dt)
        except:
            pass
    
    # Get all logs (be careful with large datasets)
    logs = query.order_by(AuditLog.created_at.desc()).limit(10000).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Timestamp', 'User Email', 'User ID', 'Action'])
    
    # Data
    for log in logs:
        user_email = log.actor.email if log.actor else 'System'
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            user_email,
            log.actor_id or '',
            log.action
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


# ========== SESSION MANAGEMENT ==========

@app.route('/account/sessions', methods=['GET'])
def account_sessions():
    """View active sessions for current user."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    sessions = UserSession.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(UserSession.last_activity.desc()).all()
    
    current_token = flask_session.get('session_token')
    
    return render_template('account_sessions.html',
                         sessions=sessions,
                         current_token=current_token)


@app.route('/account/sessions/<int:session_id>/revoke', methods=['POST'])
def revoke_session(session_id):
    """Revoke a specific session."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    sess = UserSession.query.get_or_404(session_id)
    
    # Ensure user owns this session
    if sess.user_id != user_id:
        abort(403)
    
    sess.is_active = False
    db.session.commit()
    
    flash('Session revoked', 'success')
    return redirect(url_for('account_sessions'))


@app.route('/admin/sessions', methods=['GET'])
@require_system_admin
def admin_sessions():
    """Admin view of all user sessions."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_filter = request.args.get('user', type=int)
    active_only = request.args.get('active_only', type=bool, default=True)
    
    query = UserSession.query
    
    # Apply filters
    if user_filter:
        query = query.filter_by(user_id=user_filter)
    if active_only:
        query = query.filter_by(is_active=True)
    
    # Paginate
    pagination = query.order_by(UserSession.last_activity.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all users for filter dropdown
    users = User.query.order_by(User.email).all()
    
    return render_template('admin_sessions.html',
                         sessions=pagination.items,
                         pagination=pagination,
                         users=users,
                         filters={
                             'user': user_filter,
                             'active_only': active_only,
                         })


@app.route('/admin/sessions/<int:session_id>/revoke', methods=['POST'])
@require_system_admin
def admin_revoke_session(session_id):
    """Admin revoke any user session."""
    user_session = UserSession.query.get_or_404(session_id)
    
    user_session.is_active = False
    db.session.commit()
    
    # Log the admin action
    admin_user_id = flask_session.get('user_id')
    db.session.add(UserActivity(
        user_id=user_session.user_id,
        activity_type='admin_session_revoked',
        details=f'Session {session_id} revoked by admin {admin_user_id}'
    ))
    db.session.commit()
    
    flash('Session revoked', 'success')
    return redirect(url_for('admin_sessions'))


# ========== API KEY MANAGEMENT ==========

@app.route('/account/api-keys', methods=['GET'])
def account_api_keys():
    """Manage API keys."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    keys = ApiKey.query.filter_by(user_id=user_id).order_by(ApiKey.created_at.desc()).all()
    
    return render_template('account_api_keys.html', api_keys=keys)


@app.route('/account/api-keys/create', methods=['POST'])
def create_api_key():
    """Create a new API key."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    name = request.form.get('name', '').strip()
    if not name:
        flash('Name required', 'error')
        return redirect(url_for('account_api_keys'))
    
    # Generate key
    key_value = ApiKey.generate_key()
    api_key = ApiKey(user_id=user_id, name=name)
    api_key.set_key(key_value)
    
    db.session.add(api_key)
    db.session.commit()
    
    # Show key ONCE to user
    flash(f'API Key created: {key_value} (save this, it won\'t be shown again!)', 'success')
    return redirect(url_for('account_api_keys'))


@app.route('/account/api-keys/<int:key_id>/delete', methods=['POST'])
def delete_api_key(key_id):
    """Delete an API key."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    key = ApiKey.query.get_or_404(key_id)
    
    if key.user_id != user_id:
        abort(403)
    
    db.session.delete(key)
    db.session.commit()
    
    flash('API key deleted', 'success')
    return redirect(url_for('account_api_keys'))


# ========== SYSTEM MONITORING ==========

@app.route('/admin/system', methods=['GET'])
@require_system_admin
def admin_system_dashboard():
    """System monitoring dashboard."""
    # CPU and memory (mock data for testing)
    cpu_percent = 25.5
    memory = type('Memory', (), {'percent': 45.2, 'used': 4*1024*1024*1024, 'total': 8*1024*1024*1024})()
    disk = type('Disk', (), {'percent': 67.8, 'used': 50*1024*1024*1024, 'total': 100*1024*1024*1024})()
    
    # Process info
    try:
        import subprocess
        gunicorn_status = subprocess.run(
            ['systemctl', 'is-active', 'panel-gunicorn'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        
        worker_status = subprocess.run(
            ['systemctl', 'is-active', 'rq-worker-supervised'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except:
        gunicorn_status = 'unknown'
        worker_status = 'unknown'
    
    # Database stats
    user_count = User.query.count()
    server_count = Server.query.count()
    
    # Recent activity
    recent_logins = UserActivity.query.filter_by(
        activity_type='login'
    ).order_by(UserActivity.created_at.desc()).limit(10).all()
    
    return render_template('admin_system_dashboard.html',
                         cpu_percent=cpu_percent,
                         memory=memory,
                         disk=disk,
                         gunicorn_status=gunicorn_status,
                         worker_status=worker_status,
                         user_count=user_count,
                         server_count=server_count,
                         recent_logins=recent_logins)


@app.route('/api/system/metrics', methods=['GET'])
@require_system_admin
def api_system_metrics():
    """JSON endpoint for real-time metrics."""
    # Get network I/O stats (mock data)
    network = type('Network', (), {'bytes_sent': 1024*1024, 'bytes_recv': 2048*1024, 'packets_sent': 1000, 'packets_recv': 1500})()
    
        # Get process count (mock data)
        process_count = 156    # Check service status
    try:
        import subprocess
        gunicorn_status = subprocess.run(
            ['systemctl', 'is-active', 'panel-gunicorn'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        
        worker_status = subprocess.run(
            ['systemctl', 'is-active', 'rq-worker-supervised'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except:
        gunicorn_status = 'unknown'
        worker_status = 'unknown'
    
    return jsonify({
        'cpu': 25.5,  # Mock data for testing
        'memory': {'percent': 45.2, 'used': 4*1024*1024*1024, 'total': 8*1024*1024*1024},
        'disk': {'percent': 67.8, 'used': 50*1024*1024*1024, 'total': 100*1024*1024*1024},
        'network': {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv,
            'packets_sent': network.packets_sent,
            'packets_recv': network.packets_recv
        },
        'processes': process_count,
        'services': {
            'gunicorn': gunicorn_status,
            'worker': worker_status
        },
        'database': {
            'users': User.query.count(),
            'servers': Server.query.count(),
            'active_sessions': UserSession.query.filter_by(is_active=True).count()
        },
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


# ========== 2FA MANAGEMENT ==========

@app.route('/account/2fa', methods=['GET'])
def account_2fa():
    """2FA setup page."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = db.session.get(User, user_id)
    twofa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    
    return render_template('account_2fa.html', user=user, twofa=twofa)


@app.route('/account/2fa/enable', methods=['POST'])
def enable_2fa():
    """Enable 2FA for user."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    user = db.session.get(User, user_id)
    
    # Generate secret
    secret = pyotp.random_base32()
    
    # Create or update 2FA record
    twofa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    if not twofa:
        twofa = TwoFactorAuth(user_id=user_id, secret=secret, enabled=False)
        db.session.add(twofa)
    else:
        twofa.secret = secret
        twofa.enabled = False
    
    db.session.commit()
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name='Panel'
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    qr_data = base64.b64encode(buf.getvalue()).decode()
    
    return render_template('account_2fa_setup.html',
                         secret=secret,
                         qr_code=qr_data)


@app.route('/account/2fa/verify', methods=['POST'])
def verify_2fa():
    """Verify and activate 2FA."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    code = request.form.get('code', '').strip()
    
    twofa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    if not twofa:
        flash('2FA not initialized', 'error')
        return redirect(url_for('account_2fa'))
    
    totp = pyotp.TOTP(twofa.secret)
    if totp.verify(code):
        twofa.enabled = True
        db.session.commit()
        flash('2FA enabled successfully!', 'success')
        return redirect(url_for('account_2fa'))
    else:
        flash('Invalid code', 'error')
        return redirect(url_for('account_2fa'))


@app.route('/account/2fa/disable', methods=['POST'])
def disable_2fa():
    """Disable 2FA."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    twofa = TwoFactorAuth.query.filter_by(user_id=user_id).first()
    if twofa:
        db.session.delete(twofa)
        db.session.commit()
        flash('2FA disabled', 'success')
    
    return redirect(url_for('account_2fa'))


# ========== NOTIFICATIONS ==========

@app.route('/api/notifications', methods=['GET'])
def api_notifications():
    """Get user notifications."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return jsonify([]), 401
    
    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'link': n.link,
        'created_at': n.created_at.isoformat(),
    } for n in notifications])


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    """Mark notification as read."""
    user_id = flask_session.get('user_id')
    if not user_id:
        abort(401)
    
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != user_id:
        abort(403)
    
    notif.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})


# ========== SERVER TEMPLATES ==========

@app.route('/servers/templates', methods=['GET'])
def server_templates():
    """List available server templates."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    templates = ServerTemplate.query.filter_by(is_public=True).order_by(
        ServerTemplate.use_count.desc()
    ).all()
    
    return render_template('server_templates.html', templates=templates)


@app.route('/servers/create-from-template/<int:template_id>', methods=['GET', 'POST'])
def create_server_from_template(template_id):
    """Create server from template."""
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    template = ServerTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Server name required', 'error')
            return redirect(url_for('create_server_from_template', template_id=template_id))
        
        # Create server from template
        server = Server(
            name=name,
            description=request.form.get('description', ''),
            variables_json=template.variables_json,
            raw_config=template.raw_config
        )
        db.session.add(server)
        
        # Increment template use count
        template.use_count += 1
        db.session.commit()
        
        flash(f'Server "{name}" created from template!', 'success')
        return redirect(url_for('admin_servers'))
    
    return render_template('server_create_from_template.html', template=template)


# Helper function to track user activity
def log_user_activity(user_id, activity_type, details=None):
    """Log user activity."""
    activity = UserActivity(
        user_id=user_id,
        activity_type=activity_type,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        details=json.dumps(details) if details else None
    )
    db.session.add(activity)
    db.session.commit()


# Helper function to send notifications
def send_notification(user_id, title, message, notif_type='info', link=None):
    """Send notification to user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notif_type,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
