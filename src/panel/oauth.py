"""
OAuth 2.0 Social Login Integration
Supports Google, GitHub, and Discord authentication
"""

import os
from flask import Flask, url_for, session, redirect, flash, current_app
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client import OAuthError
from werkzeug.security import generate_password_hash

from src.panel import db
from src.panel.models import User

oauth = OAuth()


def init_oauth(app: Flask) -> None:
    """Initialize OAuth clients"""
    oauth.init_app(app)

    # Google OAuth
    if app.config.get('GOOGLE_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )

    # GitHub OAuth
    if app.config.get('GITHUB_CLIENT_ID'):
        oauth.register(
            name='github',
            client_id=app.config['GITHUB_CLIENT_ID'],
            client_secret=app.config['GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    # Discord OAuth
    if app.config.get('DISCORD_CLIENT_ID'):
        oauth.register(
            name='discord',
            client_id=app.config['DISCORD_CLIENT_ID'],
            client_secret=app.config['DISCORD_CLIENT_SECRET'],
            access_token_url='https://discord.com/api/oauth2/token',
            authorize_url='https://discord.com/api/oauth2/authorize',
            api_base_url='https://discord.com/api/',
            client_kwargs={'scope': 'identify email'},
        )

    app.logger.info("OAuth integration initialized")


def get_oauth_client(provider: str):
    """Get OAuth client for provider"""
    try:
        return oauth.create_client(provider)
    except Exception:
        return None


class OAuthHandler:
    """Handles OAuth authentication flow"""

    @staticmethod
    def get_login_url(provider: str) -> str:
        """Get OAuth login URL for provider"""
        client = get_oauth_client(provider)
        if not client:
            raise ValueError(f"OAuth provider '{provider}' not configured")

        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        return client.authorize_redirect(redirect_uri).location

    @staticmethod
    def handle_callback(provider: str, request):
        """Handle OAuth callback and authenticate user"""
        client = get_oauth_client(provider)
        if not client:
            raise ValueError(f"OAuth provider '{provider}' not configured")

        try:
            token = client.authorize_access_token()
            user_info = OAuthHandler._get_user_info(provider, client, token)

            # Find or create user
            user = User.find_by_oauth(provider, user_info['id'])

            if user:
                # Existing user - update tokens and login
                user.link_oauth_account(
                    provider=provider,
                    provider_id=user_info['id'],
                    access_token=token.get('access_token'),
                    refresh_token=token.get('refresh_token'),
                    expires_at=OAuthHandler._parse_expires_at(token)
                )
                db.session.commit()
                session['user_id'] = user.id
                flash(f"Welcome back, {user.display_name}!", "success")
            else:
                # New user - create account
                user = OAuthHandler._create_oauth_user(provider, user_info, token)
                session['user_id'] = user.id
                flash(f"Welcome, {user.display_name}! Your account has been created.", "success")

            return user

        except OAuthError as e:
            current_app.logger.error(f"OAuth error for {provider}: {e}")
            raise ValueError(f"OAuth authentication failed: {str(e)}")

    @staticmethod
    def _get_user_info(provider: str, client, token):
        """Get user info from OAuth provider"""
        if provider == 'google':
            resp = client.get('https://openidconnect.googleapis.com/v1/userinfo')
            return resp.json()

        elif provider == 'github':
            resp = client.get('user')
            user_data = resp.json()

            # Get email if not provided
            if not user_data.get('email'):
                email_resp = client.get('user/emails')
                emails = email_resp.json()
                primary_email = next((e for e in emails if e.get('primary')), None)
                if primary_email:
                    user_data['email'] = primary_email['email']

            return {
                'id': str(user_data['id']),
                'email': user_data.get('email'),
                'name': user_data.get('name') or user_data.get('login'),
                'avatar': user_data.get('avatar_url')
            }

        elif provider == 'discord':
            resp = client.get('users/@me')
            user_data = resp.json()
            return {
                'id': user_data['id'],
                'email': user_data.get('email'),
                'name': user_data.get('username'),
                'avatar': f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data.get('avatar')}.png" if user_data.get('avatar') else None
            }

        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

    @staticmethod
    def _create_oauth_user(provider: str, user_info: dict, token: dict) -> User:
        """Create new user from OAuth data"""
        # Generate a unique username if name conflicts
        base_name = user_info.get('name', f"{provider}_user")
        username = base_name
        counter = 1

        while User.query.filter_by(email=user_info['email']).first():
            username = f"{base_name}_{counter}"
            counter += 1

        # Create user
        user = User(
            first_name=username.split()[0] if ' ' in username else username,
            last_name=' '.join(username.split()[1:]) if ' ' in username else '',
            email=user_info['email'],
            dob=datetime(2000, 1, 1).date(),  # Default DOB
            role='user'
        )

        # Set a random password (user can change later)
        user.set_password(os.urandom(32).hex())

        # Link OAuth account
        user.link_oauth_account(
            provider=provider,
            provider_id=user_info['id'],
            access_token=token.get('access_token'),
            refresh_token=token.get('refresh_token'),
            expires_at=OAuthHandler._parse_expires_at(token)
        )

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def _parse_expires_at(token: dict):
        """Parse token expiration time"""
        expires_in = token.get('expires_in')
        if expires_in:
            from datetime import datetime, timedelta
            return datetime.utcnow() + timedelta(seconds=expires_in)
        return None


# OAuth routes
def init_oauth_routes(app: Flask) -> None:
    """Initialize OAuth routes"""

    @app.route('/oauth/login/<provider>')
    def oauth_login(provider):
        """Initiate OAuth login"""
        try:
            redirect_url = OAuthHandler.get_login_url(provider)
            return redirect(redirect_url)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for('login'))

    @app.route('/oauth/callback/<provider>')
    def oauth_callback(provider):
        """Handle OAuth callback"""
        try:
            user = OAuthHandler.handle_callback(provider, request)
            next_url = session.pop('next', url_for('index'))
            return redirect(next_url)
        except Exception as e:
            current_app.logger.error(f"OAuth callback error: {e}")
            flash("Authentication failed. Please try again.", "error")
            return redirect(url_for('login'))

    @app.route('/oauth/unlink/<provider>', methods=['POST'])
    @login_required
    def oauth_unlink(provider):
        """Unlink OAuth account"""
        user = get_current_user()
        if user and user.oauth_provider == provider:
            user.unlink_oauth_account()
            db.session.commit()
            flash(f"{provider.title()} account unlinked successfully.", "success")
        else:
            flash("OAuth account not found.", "error")

        return redirect(url_for('profile'))