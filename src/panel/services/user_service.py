"""
User Service Layer
Handles user-related business logic and database operations
"""

from datetime import datetime, timezone
from typing import Optional

from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from input_validation import RegisterSchema, validate_request
from logging_config import log_security_event


class UserService:
    """Service class for user management operations"""

    @staticmethod
    def create_user(first_name: str, last_name: str, email: str, password: str, dob) -> tuple:
        """
        Create a new user account

        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email address
            password: Plain text password
            dob: Date of birth

        Returns:
            Tuple of (user, error_message)
        """
        try:
            # Validate input data
            validated_data, validation_errors = validate_request(
                RegisterSchema,
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "password": password,
                    "password_confirm": password,
                    "dob": dob,
                }
            )

            if validation_errors:
                error_messages = []
                for field, messages in validation_errors.items():
                    if isinstance(messages, list):
                        error_messages.extend(messages)
                    else:
                        error_messages.append(str(messages))
                return None, "; ".join(error_messages)

            # Check if user already exists
            from app import User
            existing_user = User.query.filter_by(email=email.lower()).first()
            if existing_user:
                return None, "Email already registered"

            # Age validation
            today = datetime.now().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 16:
                return None, "You must be at least 16 years old to register"

            # Create user
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email.lower(),
                dob=dob
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            return user, None

        except IntegrityError:
            db.session.rollback()
            return None, "Email already registered"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {e}")
            return None, "An error occurred during registration"

    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple:
        """
        Authenticate a user

        Args:
            email: User's email
            password: Plain text password

        Returns:
            Tuple of (user, error_message)
        """
        try:
            from app import User
            user = User.query.filter_by(email=email.lower()).first()

            if not user:
                return None, "Invalid credentials"

            if not user.check_password(password):
                return None, "Invalid credentials"

            # Check if account is locked
            if user.is_account_locked():
                return None, "Account is temporarily locked due to too many failed login attempts"

            return user, None

        except Exception as e:
            current_app.logger.error(f"Error authenticating user: {e}")
            return None, "Authentication failed"

    @staticmethod
    def record_login_attempt(user, success: bool = False, ip_address: str = None):
        """
        Record a login attempt

        Args:
            user: User instance
            success: Whether login was successful
            ip_address: Client IP address
        """
        try:
            user.record_login_attempt(success=success)
            db.session.commit()

            # Log security event
            if success:
                log_security_event(
                    event_type="login_success",
                    description=f"User login successful: {user.email}",
                    user_id=user.id,
                    ip_address=ip_address,
                )
            else:
                log_security_event(
                    event_type="login_failed",
                    description=f"Failed login attempt for: {user.email}",
                    user_id=user.id,
                    ip_address=ip_address,
                )

        except Exception as e:
            current_app.logger.error(f"Error recording login attempt: {e}")
            db.session.rollback()

    @staticmethod
    def update_user_profile(user, **kwargs) -> tuple:
        """
        Update user profile information

        Args:
            user: User instance
            **kwargs: Profile fields to update

        Returns:
            Tuple of (success, error_message)
        """
        try:
            allowed_fields = ['first_name', 'last_name', 'bio']

            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(user, field, value.strip() if isinstance(value, str) else value)

            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user profile: {e}")
            return False, "Failed to update profile"

    @staticmethod
    def change_password(user, current_password: str, new_password: str) -> tuple:
        """
        Change user password

        Args:
            user: User instance
            current_password: Current password
            new_password: New password

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not user.check_password(current_password):
                return False, "Current password is incorrect"

            # Validate new password complexity
            import re
            if (len(new_password) < 8 or
                not re.search(r"[A-Z]", new_password) or
                not re.search(r"[a-z]", new_password) or
                not re.search(r"\d", new_password) or
                not re.search(r"[^A-Za-z0-9]", new_password)):
                return False, "New password does not meet complexity requirements"

            user.set_password(new_password)
            db.session.commit()

            return True, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error changing password: {e}")
            return False, "Failed to change password"