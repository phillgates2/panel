"""OAuth2 Authentication Implementation

Provides OAuth2 authentication with support for Google, GitHub, and other providers.
Includes JWT token management and secure authentication flows.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from flask import Blueprint, request, session, redirect, url_for, flash, jsonify, g
from authlib.integrations.flask_client import OAuth
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from werkzeug.security import generate_password_hash

from simple_config import load_config


# OAuth setup
oauth = OAuth()

# JWT setup
jwt = JWTManager()

# OAuth providers configuration
OAUTH_PROVIDERS = {
    'google': {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
        'access_token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://openidconnect.googleapis.com/v1/userinfo',
        'scope': 'openid email profile',
        'server_metadata_url': 'https://accounts.google.com/.well-known/openid_configuration'
    },
    'github': {
        'client_id': os.environ.get('GITHUB_CLIENT_ID', ''),
        'client_secret': os.environ.get('GITHUB_CLIENT_SECRET', ''),
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'access_token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'scope': 'user:email',
    },
    'discord': {
        'client_id': os.environ.get('DISCORD_CLIENT_ID', ''),
        'client_secret': os.environ.get('DISCORD_CLIENT_SECRET', ''),
        'authorize_url': 'https://discord.com/api/oauth2/authorize',
        'access_token_url': 'https://discord.com/api/oauth2/token',
        'userinfo_url': 'https://discord.com/api/users/@me',
        'scope': 'identify email',
    }
}


class OAuthManager:
    """Manager for OAuth2 authentication."""

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize OAuth with Flask app."""
        config = load_config()

        # Configure OAuth providers
        for provider_name, provider_config in OAUTH_PROVIDERS.items():
            if provider_config['client_id'] and provider_config['client_secret']:
                oauth.register(
                    name=provider_name,
                    client_id=provider_config['client_id'],
                    client_secret=provider_config['client_secret'],
                    authorize_url=provider_config['authorize_url'],
                    access_token_url=provider_config['access_token_url'],
                    api_base_url=f"https://{provider_name}.com/" if provider_name != 'discord' else "https://discord.com/api/",
                    client_kwargs={
                        'scope': provider_config['scope'],
                    },
                )

        # Initialize JWT
        app.config['JWT_SECRET_KEY'] = config.get('JWT_SECRET_KEY', secrets.token_hex(32))
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

        jwt.init_app(app)

        # Register OAuth blueprint
        oauth_bp = self._create_oauth_blueprint()
        app.register_blueprint(oauth_bp)

    def _create_oauth_blueprint(self):
        """Create OAuth blueprint with routes."""
        oauth_bp = Blueprint('oauth', __name__, url_prefix='/auth')

        @oauth_bp.route('/login/<provider>')
        def oauth_login(provider):
            """Initiate OAuth login flow."""
            if provider not in OAUTH_PROVIDERS:
                flash('OAuth provider not supported', 'error')
                return redirect(url_for('login'))

            redirect_uri = url_for('oauth.oauth_callback', provider=provider, _external=True)
            return oauth.create_client(provider).authorize_redirect(redirect_uri)

        @oauth_bp.route('/callback/<provider>')
        def oauth_callback(provider):
            """Handle OAuth callback."""
            if provider not in OAUTH_PROVIDERS:
                flash('OAuth provider not supported', 'error')
                return redirect(url_for('login'))

            try:
                client = oauth.create_client(provider)
                token = client.authorize_access_token()

                # Get user info
                if provider == 'google':
                    user_info = client.get('https://openidconnect.googleapis.com/v1/userinfo').json()
                elif provider == 'github':
                    user_info = client.get('user').json()
                    # Get email separately for GitHub
                    emails = client.get('user/emails').json()
                    user_info['email'] = next((e['email'] for e in emails if e['primary']), user_info.get('email'))
                elif provider == 'discord':
                    user_info = client.get('users/@me').json()

                # Create or update user
                user = self._create_or_update_oauth_user(provider, user_info, token)

                # Create session
                session['user_id'] = user.id
                session['oauth_provider'] = provider

                # Log login
                from app import db, AuditLog
                db.session.add(AuditLog(
                    user_id=user.id,
                    action=f"oauth_login:{provider}",
                    details=f"Login via {provider}"
                ))
                db.session.commit()

                flash(f'Successfully logged in with {provider.title()}', 'success')
                return redirect(url_for('dashboard'))

            except Exception as e:
                print(f"OAuth error: {e}")
                flash('Authentication failed', 'error')
                return redirect(url_for('login'))

        @oauth_bp.route('/jwt/login', methods=['POST'])
        def jwt_login():
            """JWT token-based login."""
            if not request.is_json:
                return jsonify({"error": "JSON required"}), 400

            data = request.json
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return jsonify({"error": "Email and password required"}), 400

            from app import db
            from models import User

            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                return jsonify({"error": "Invalid credentials"}), 401

            if not user.is_active:
                return jsonify({"error": "Account is disabled"}), 401

            # Create tokens
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'is_admin': user.is_system_admin()
                }
            })

        @oauth_bp.route('/jwt/refresh', methods=['POST'])
        @jwt_required(refresh=True)
        def jwt_refresh():
            """Refresh JWT access token."""
            identity = get_jwt_identity()
            access_token = create_access_token(identity=identity)
            return jsonify({'access_token': access_token})

        @oauth_bp.route('/jwt/logout', methods=['POST'])
        @jwt_required()
        def jwt_logout():
            """JWT logout - client should discard tokens."""
            # In a production system, you might want to maintain a blacklist
            return jsonify({'message': 'Successfully logged out'})

        return oauth_bp

    def _create_or_update_oauth_user(self, provider: str, user_info: Dict[str, Any], token: Dict[str, Any]):
        """Create or update user from OAuth data."""
        from app import db
        from models import User

        # Extract user data based on provider
        if provider == 'google':
            oauth_id = user_info['sub']
            email = user_info['email']
            username = user_info.get('name', email.split('@')[0])
        elif provider == 'github':
            oauth_id = str(user_info['id'])
            email = user_info.get('email')
            username = user_info['login']
        elif provider == 'discord':
            oauth_id = user_info['id']
            email = user_info.get('email')
            username = user_info['username']

        if not email:
            raise ValueError(f"Email not provided by {provider}")

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if user:
            # Update existing user
            user.oauth_provider = provider
            user.oauth_id = oauth_id
            user.last_login = datetime.now(timezone.utc)
        else:
            # Create new user
            user = User(
                email=email,
                username=username,
                oauth_provider=provider,
                oauth_id=oauth_id,
                password_hash=generate_password_hash(secrets.token_hex(32)),  # Random password
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc)
            )
            db.session.add(user)

        db.session.commit()
        return user


# Global OAuth manager instance
oauth_manager = OAuthManager()


# ===== JWT Middleware =====

@jwt.user_identity_loader
def user_identity_lookup(user_id):
    """JWT user identity loader."""
    return user_id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """JWT user lookup callback."""
    identity = jwt_data["sub"]
    from app import db
    from models import User

    user = db.session.get(User, identity)
    if user and user.is_active:
        g.user = user
        return user
    return None


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Handle expired tokens."""
    return jsonify({"error": "Token has expired"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Handle invalid tokens."""
    return jsonify({"error": "Invalid token"}), 401


@jwt.unauthorized_loader
def unauthorized_callback(error):
    """Handle missing tokens."""
    return jsonify({"error": "Missing or invalid token"}), 401


# ===== API Key Authentication =====

class APIKeyAuth:
    """API key authentication for programmatic access."""

    @staticmethod
    def authenticate():
        """Authenticate using API key."""
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')

        if not api_key:
            return None

        # Remove "Bearer " prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]

        from app import db
        from models_extended import ApiKey

        # Find API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_record = ApiKey.query.filter_by(key_hash=key_hash).first()

        if not api_key_record:
            return None

        # Check if expired
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
            return None

        # Get user
        user = db.session.get(db.User, api_key_record.user_id)
        if not user or not user.is_active:
            return None

        # Check permissions (if implemented)
        # This would check against api_key_record.scopes

        g.user = user
        g.api_key = api_key_record
        return user


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = APIKeyAuth.authenticate()
        if not user:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function


def init_oauth_auth(app):
    """Initialize OAuth2 authentication."""
    oauth.init_app(app)
    oauth_manager.init_app(app)