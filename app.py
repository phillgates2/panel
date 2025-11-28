import time
import os
from flask import Flask, Blueprint, request, session, render_template, jsonify, redirect, url_for
from config import config
from src.panel import models
from src.panel.admin import DatabaseAdmin
from app.db import db
from app.extensions import init_app_extensions
from app.factory import create_app
from app.context_processors import inject_user
from app.error_handlers import page_not_found, internal_error

# Import permissions
from src.panel.models import ROLE_HIERARCHY, ROLE_PERMISSIONS
from flask_login import current_user
import newrelic.agent

# Initialize New Relic APM
newrelic.agent.initialize('newrelic.ini')

# Initialize SQLAlchemy
# Create main blueprint for routes
main_bp = Blueprint("main", __name__)

# Initialize the Flask app
app = Flask(__name__)

# Initialize all extensions and configurations
extensions = init_app_extensions(app)

# Bind SQLAlchemy to the app
db.init_app(app)

# Track application startup time
app.start_time = time.time()

# Initialize Database Admin integration
try:
    db_admin = DatabaseAdmin(app, db)
except Exception:
    # Best-effort during tests; ignore failures
    db_admin = None

# Optional CMS and Forum blueprints (kept optional so imports won't fail in test environments)
try:
    from src.panel.cms import cms_bp
except Exception:
    cms_bp = None
try:
    from src.panel.forum import forum_bp
except Exception:
    forum_bp = None

try:
    from src.panel.admin import admin_bp
except Exception:
    admin_bp = None

def _register_optional_blueprints(module_app):
    try:
        from src.panel import cms as _cms
        if hasattr(_cms, "cms_bp"):
            try:
                module_app.register_blueprint(_cms.cms_bp)
            except Exception:
                pass
    except Exception:
        pass
    try:
        from src.panel import forum as _forum
        if hasattr(_forum, "forum_bp"):
            try:
                module_app.register_blueprint(_forum.forum_bp)
            except Exception:
                pass
    except Exception:
        pass
    try:
        if admin_bp is not None:
            module_app.register_blueprint(admin_bp)
    except Exception:
        pass

# Register optional blueprints on the module-level app if available
_register_optional_blueprints(app)

# Register context processor and error handlers
app.context_processor(inject_user)
app.errorhandler(404)(page_not_found)
app.errorhandler(500)(internal_error)

@app.route('/status')
def status():
    return {
        'status': 'ok',
        'uptime': time.time() - app.start_time,
        'version': '1.0',
        'features': list(feature_flags.keys())
    }


@app.route('/health')
def health():
    # Check external services
    health_status = {'status': 'healthy', 'checks': {}}
    try:
        # Check Redis
        cache.get('health_check')
        health_status['checks']['redis'] = 'ok'
    except:
        health_status['checks']['redis'] = 'fail'
        health_status['status'] = 'unhealthy'
    try:
        # Check DB
        db.session.execute(db.text('SELECT 1'))
        health_status['checks']['database'] = 'ok'
    except:
        health_status['checks']['database'] = 'fail'
        health_status['status'] = 'unhealthy'
    # Add AI API check if applicable
    return health_status


@app.route('/api/v2/status')
def api_v2_status():
    return {'version': 'v2', 'status': 'ok'}


@app.route('/webhooks', methods=['POST'])
def webhooks():
    data = request.json
    # Process webhook, e.g., Discord/Slack
    return {'received': True}

# GraphQL
from graphene_flask import GraphQLView
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=extensions['schema'], graphiql=True))

# CSP
@app.after_request
def add_csp(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.example.com; style-src 'self' 'unsafe-inline'"
    return response


# HTTP Caching
@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year for static
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'private, max-age=300'  # 5 min for API
    return response


@app.route('/api/swagger.json')
def swagger_json():
    return {
        "swagger": "2.0",
        "info": {
            "title": "Panel API",
            "version": "1.0",
            "description": "API for Panel application"
        },
        "host": "localhost:5000",
        "basePath": "/api",
        "schemes": ["http"],
        "paths": {
            "/status": {
                "get": {
                    "summary": "Get application status",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "uptime": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }


# Feature flags
feature_flags = {
    'dark_mode': True,
    'new_ui': False,
    'gdpr_auto_export': True
}


@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/notifications')
def notifications():
    return render_template('notifications.html')


@app.route('/api/user/theme', methods=['POST'])
def update_theme():
    data = request.json
    theme = data.get('theme')
    # Save to user settings
    return {'success': True}


@app.route('/api/notifications')
def get_notifications():
    # Get user notifications
    notifications = []  # Query from DB
    return {'notifications': notifications}


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    # Mark as read
    return {'success': True}


@app.context_processor
def inject_breadcrumbs():
    # Simple breadcrumb logic - customize based on routes
    path = request.path
    breadcrumbs = []
    if path.startswith('/forum'):
        breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Forum', 'url': '/forum'}]
    elif path.startswith('/profile'):
        breadcrumbs = [{'name': 'Home', 'url': '/'}, {'name': 'Profile', 'url': '/profile'}]
    return {'breadcrumbs': breadcrumbs}


@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Implement search logic
    results = []
    if query:
        # Search in models
        results = []  # Placeholder
    return render_template('search.html', query=query, results=results)


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/permissions')
def permissions():
    return render_template('permissions.html')


@app.route('/api/permissions')
def get_permissions():
    return {
        'roles': ROLE_HIERARCHY,
        'permissions': ROLE_PERMISSIONS,
        'user_permissions': current_user.get_available_permissions() if current_user.is_authenticated else []
    }


@app.route('/api/user/<int:user_id>/role', methods=['POST'])
def update_user_role(user_id):
    if not current_user.is_authenticated or not current_user.can_grant_role(request.json.get('role')):
        return {'error': 'Unauthorized'}, 403

    user = models.User.query.get(user_id)
    if not user:
        return {'error': 'User not found'}, 404

    new_role = request.json.get('role')
    if new_role not in ROLE_HIERARCHY:
        return {'error': 'Invalid role'}, 400

    user.role = new_role
    db.session.commit()

    return {'success': True, 'role': new_role}


@app.route('/chat')
def chat():
    return render_template('chat.html')


@app.route('/donate')
def donate():
    return render_template('donate.html')


@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    import stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')

    data = request.json
    amount = data.get('amount', 500)  # cents
    email = data.get('email')

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={'enabled': True},
            receipt_email=email if email else None,
        )
        return {'clientSecret': intent.client_secret}
    except Exception as e:
        return {'error': str(e)}, 400


@app.route('/api/chat/rooms')
def get_chat_rooms():
    return {
        'rooms': ['general', 'support', 'random'],
        'current_room': 'general'
    }


@app.route('/api/chat/messages/<room>', methods=['GET', 'POST'])
def chat_messages(room):
    from src.panel.models import ChatMessage

    if request.method == 'POST':
        data = request.json
        message = data['message']
        moderated = moderate_message(message)
        user_id = getattr(current_user, 'id', None) if current_user.is_authenticated else None
        msg = ChatMessage(
            room=room,
            user_id=user_id,
            username=data['username'],
            message=message,
            moderated=moderated
        )
        db.session.add(msg)
        db.session.commit()
        return {'status': 'sent', 'moderated': moderated}

    # GET
    messages = ChatMessage.query.filter_by(room=room, moderated=True).order_by(ChatMessage.timestamp).limit(50).all()
    return {
        'messages': [{
            'id': m.id,
            'username': m.username,
            'message': m.message,
            'timestamp': m.timestamp.isoformat()
        } for m in messages]
    }


@app.route('/api/chat/moderate/<int:message_id>', methods=['POST'])
def moderate_message(message_id):
    if not current_user or not current_user.has_permission('moderate_forum'):
        return {'error': 'Unauthorized'}, 403

    from src.panel.models import ChatMessage
    msg = ChatMessage.query.get(message_id)
    if not msg:
        return {'error': 'Message not found'}, 404

    action = request.json.get('action')
    if action == 'approve':
        msg.moderated = True
    elif action == 'reject':
        msg.moderated = False
    elif action == 'flag':
        msg.flagged = True

    db.session.commit()
    return {'status': 'updated'}


@app.route('/admin/chat-moderation')
def chat_moderation():
    if not current_user or not current_user.has_permission('moderate_forum'):
        return redirect(url_for('index'))
    return render_template('admin_chat_moderation.html')


@app.route('/api/admin/chat-messages')
def admin_chat_messages():
    if not current_user or not current_user.has_permission('moderate_forum'):
        return {'error': 'Unauthorized'}, 403

    from src.panel.models import ChatMessage
    tab = request.args.get('tab', 'pending')

    if tab == 'pending':
        messages = ChatMessage.query.filter_by(moderated=False).order_by(ChatMessage.timestamp.desc()).limit(50).all()
    elif tab == 'flagged':
        messages = ChatMessage.query.filter_by(flagged=True).order_by(ChatMessage.timestamp.desc()).limit(50).all()
    else:
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(50).all()

    return {
        'messages': [{
            'id': m.id,
            'username': m.username,
            'message': m.message,
            'room': m.room,
            'timestamp': m.timestamp.isoformat(),
            'moderated': m.moderated,
            'flagged': m.flagged
        } for m in messages]
    }


def send_donation_email(payment_intent):
    """Send donation confirmation email"""
    try:
        from flask_mail import Message
        from src.panel import mail

        donor_email = payment_intent.get('receipt_email')
        if not donor_email:
            return

        amount = payment_intent['amount'] / 100  # Convert cents to dollars

        msg = Message(
            subject="Thank you for your donation!",
            recipients=[donor_email],
            body=f"Thank you for your generous donation of ${amount:.2f} to Panel. Your support helps us maintain and improve the platform."
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send donation email: {e}")


@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    import stripe
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('stripe-signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Save donation
        save_donation(payment_intent)
        # Send confirmation email
        send_donation_email(payment_intent)
        print(f"Payment succeeded: {payment_intent['id']}")
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Save failed donation
        save_donation(payment_intent, status='failed')
        print(f"Payment failed: {payment_intent['id']}")

def save_donation(payment_intent, status='completed'):
    """Save donation to database"""
    from src.panel.models import Donation
    donation = Donation(
        stripe_payment_id=payment_intent['id'],
        amount=payment_intent['amount'],
        currency=payment_intent.get('currency', 'usd'),
        donor_email=payment_intent.get('receipt_email'),
        status=status
    )
    db.session.add(donation)
    db.session.commit()


@app.route('/admin/donation-analytics')
def donation_analytics():
    if not current_user or not current_user.is_system_admin():
        return redirect(url_for('index'))
    return render_template('admin_donation_analytics.html')


@app.route('/api/donation-analytics')
def donation_analytics_data():
    if not current_user or not current_user.is_system_admin():
        return {'error': 'Unauthorized'}, 403

    from src.panel.models import Donation
    from sqlalchemy import func

    # Total donations
    total = db.session.query(func.sum(Donation.amount)).scalar() or 0
    total /= 100  # Convert to dollars

    # Monthly breakdown
    monthly = db.session.query(
        func.date_trunc('month', Donation.timestamp).label('month'),
        func.sum(Donation.amount).label('amount')
    ).filter(Donation.status == 'completed').group_by('month').order_by('month').all()

    monthly_data = [{'month': str(m.month)[:7], 'amount': m.amount / 100} for m in monthly]

    return {
        'total': total,
        'monthly': monthly_data,
        'count': len(monthly_data)
    }

SERVICE_NAME = os.environ.get('SERVICE_NAME', 'main')

if SERVICE_NAME == 'auth':
    # Auth service routes
    @app.route('/auth/login')
    def auth_login():
        return "Auth service login"
elif SERVICE_NAME == 'chat':
    # Chat service routes
    pass  # Chat routes are already defined above
elif SERVICE_NAME == 'payment':
    # Payment service routes
    pass  # Payment routes are already defined above
else:
    # Main app routes
    pass
