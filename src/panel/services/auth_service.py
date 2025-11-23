"""
Authentication Service Layer
Handles authentication-related business logic
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app, session

from app import db
from input_validation import LoginSchema, validate_request
from logging_config import log_security_event
from services.user_service import UserService


class AuthService:
    """Service class for authentication operations"""

    @staticmethod
    def login_user(email: str, password: str, captcha: str = None, ip_address: str = None) -> tuple:
        """
        Authenticate and login a user

        Args:
            email: User's email
            password: User's password
            captcha: CAPTCHA response
            ip_address: Client IP address

        Returns:
            Tuple of (success, user, error_message)
        """
        try:
            # Validate input data
            login_data = {"email": email, "password": password}
            if captcha:
                login_data["captcha"] = captcha

            validated_data, validation_errors = validate_request(LoginSchema, login_data)
            if validation_errors:
                error_messages = []
                for field, messages in validation_errors.items():
                    if isinstance(messages, list):
                        error_messages.extend(messages)
                    else:
                        error_messages.append(str(messages))
                return False, None, "; ".join(error_messages)

            # Verify CAPTCHA if not in testing mode
            if not current_app.config.get("TESTING", False):
                if session.get("captcha_text") != captcha:
                    return False, None, "Invalid captcha"

                # Check CAPTCHA expiry (3 minutes)
                ts = session.get("captcha_ts")
                if not ts or (datetime.now().timestamp() - int(ts) > 180):
                    return False, None, "Captcha expired"

            # Authenticate user
            user, auth_error = UserService.authenticate_user(email, password)
            if not user:
                # Record failed attempt
                if user:  # user might be None here, but let's check
                    from app import User
                    temp_user = User.query.filter_by(email=email.lower()).first()
                    if temp_user:
                        UserService.record_login_attempt(temp_user, success=False, ip_address=ip_address)
                return False, None, auth_error

            # Check if 2FA is required
            if user.totp_enabled:
                # Store temporary session data for 2FA
                session["pending_2fa_user_id"] = user.id
                session["pending_2fa_email"] = email
                return True, user, "2fa_required"

            # Complete login
            AuthService._complete_login(user, ip_address)

            # Clear CAPTCHA on success
            session.pop("captcha_text", None)
            session.pop("captcha_ts", None)

            return True, user, None

        except Exception as e:
            current_app.logger.error(f"Error during login: {e}")
            return False, None, "Login failed"

    @staticmethod
    def _complete_login(user, ip_address: str = None):
        """
        Complete the login process after authentication

        Args:
            user: Authenticated user
            ip_address: Client IP address
        """
        try:
            # Record successful login
            UserService.record_login_attempt(user, success=True, ip_address=ip_address)

            # Set session data
            session["user_id"] = user.id
            session_token = secrets.token_urlsafe(32)
            session["session_token"] = session_token

            # Create session tracking record
            from models_extended import UserActivity, UserSession

            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent="",  # Would be passed from request
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.session.add(user_session)

            db.session.add(
                UserActivity(
                    user_id=user.id,
                    activity_type="login",
                    ip_address=ip_address,
                    user_agent="",  # Would be passed from request
                    details='{"method": "password"}',
                )
            )

            db.session.commit()

        except Exception as e:
            current_app.logger.error(f"Error completing login: {e}")
            db.session.rollback()

    @staticmethod
    def logout_user(user_id: int, session_token: str = None, ip_address: str = None):
        """
        Logout a user and clean up sessions

        Args:
            user_id: User ID
            session_token: Session token to invalidate
            ip_address: Client IP address
        """
        try:
            # Deactivate session in database
            if session_token:
                from models_extended import UserSession
                user_session = UserSession.query.filter_by(
                    user_id=user_id,
                    session_token=session_token,
                    is_active=True
                ).first()

                if user_session:
                    user_session.is_active = False
                    db.session.commit()

            # Log logout activity
            from models_extended import UserActivity
            db.session.add(
                UserActivity(
                    user_id=user_id,
                    activity_type="logout",
                    ip_address=ip_address,
                    user_agent="",  # Would be passed from request
                )
            )
            db.session.commit()

            # Clear session
            session.clear()

        except Exception as e:
            current_app.logger.error(f"Error during logout: {e}")
            db.session.rollback()

    @staticmethod
    def validate_session(user_id: int, session_token: str) -> bool:
        """
        Validate if a session is still active

        Args:
            user_id: User ID
            session_token: Session token

        Returns:
            True if session is valid, False otherwise
        """
        try:
            from models_extended import UserSession
            user_session = UserSession.query.filter_by(
                user_id=user_id,
                session_token=session_token,
                is_active=True
            ).first()

            if not user_session:
                return False

            # Check if session has expired
            if user_session.expires_at and user_session.expires_at < datetime.now(timezone.utc):
                user_session.is_active = False
                db.session.commit()
                return False

            return True

        except Exception as e:
            current_app.logger.error(f"Error validating session: {e}")
            return False

    @staticmethod
    def get_current_user() -> Optional[object]:
        """
        Get the current authenticated user from session

        Returns:
            User instance or None
        """
        try:
            user_id = session.get("user_id")
            session_token = session.get("session_token")

            if not user_id or not session_token:
                return None

            if not AuthService.validate_session(user_id, session_token):
                return None

            from app import User
            user = db.session.get(User, user_id)
            return user

        except Exception as e:
            current_app.logger.error(f"Error getting current user: {e}")
            return None