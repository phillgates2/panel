from flask import Blueprint, redirect, url_for, render_template
from flask_login import current_user

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/chat-moderation')
def chat_moderation():
    if not current_user or not current_user.has_permission('moderate_forum'):
        return redirect(url_for('index'))
    return render_template('admin_chat_moderation.html')