"""
Enhanced Input Validation Schemas
Strengthened Marshmallow schemas for all API inputs with comprehensive validation
"""

from marshmallow import Schema, ValidationError, fields, validates, validates_schema
import re
from typing import Dict, Any


class BaseSchema(Schema):
    """Base schema with common validation methods"""
    pass


class LoginSchema(Schema):
    """Enhanced login validation schema"""

    email = fields.Str(required=True)
    password = fields.Str(required=True)


class RegisterSchema(BaseSchema):
    """Enhanced registration validation schema"""

    first_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 50)
    last_name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 50)
    email = fields.Email(required=True, validate=lambda x: len(x) <= 254)
    password = fields.Str(required=True, validate=lambda x: 8 <= len(x) <= 128)
    confirm_password = fields.Str(required=True)
    dob = fields.Date(required=True)
    accept_terms = fields.Bool(required=True)

    @validates_schema
    def validate_passwords_match(self, data: Dict[str, Any], **kwargs) -> None:
        """Ensure passwords match"""
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match", field_name="confirm_password")

    @validates("first_name")
    def validate_name(self, value: str) -> None:
        """Validate name contains only letters and spaces"""
        if not re.match(r"^[a-zA-Z\s\-']+$", value):
            raise ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes")

    @validates("last_name")
    def validate_last_name(self, value: str) -> None:
        """Validate last name"""
        if not re.match(r"^[a-zA-Z\s\-']+$", value):
            raise ValidationError(
                "Last name can only contain letters, spaces, hyphens, and apostrophes"
            )

    @validates("password")
    def validate_password_complexity(self, value: str) -> None:
        """Comprehensive password complexity validation"""
        if len(value) < 12:
            raise ValidationError("Password must be at least 12 characters long")
        if not re.search(r"[A-Z]", value):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError("Password must contain at least one special character")
        # Check for common weak passwords
        weak_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if value.lower() in weak_passwords:
            raise ValidationError("Password is too common, please choose a stronger password")

    @validates("dob")
    def validate_age(self, value) -> None:
        """Validate user is at least 13 years old"""
        from datetime import date

        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 13:
            raise ValidationError("Must be at least 13 years old to register")


class PasswordResetSchema(BaseSchema):
    """Password reset request schema"""

    email = fields.Email(required=True, validate=lambda x: len(x) <= 254)


class PasswordResetConfirmSchema(BaseSchema):
    """Password reset confirmation schema"""

    token = fields.Str(required=True, validate=lambda x: len(x) == 64)
    password = fields.Str(required=True, validate=lambda x: 12 <= len(x) <= 128)
    confirm_password = fields.Str(required=True)

    @validates_schema
    def validate_passwords_match(self, data: Dict[str, Any], **kwargs) -> None:
        """Ensure passwords match"""
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match", field_name="confirm_password")

    @validates("password")
    def validate_password_complexity(self, value: str) -> None:
        """Password complexity validation"""
        if len(value) < 12:
            raise ValidationError("Password must be at least 12 characters long")
        if not re.search(r"[A-Z]", value):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError("Password must contain at least one special character")


class ServerCreateSchema(BaseSchema):
    """Server creation validation schema"""

    name = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 120)
    description = fields.Str(validate=lambda x: len(x) <= 512, allow_none=True)
    host = fields.Str(validate=lambda x: len(x) <= 128, allow_none=True)
    port = fields.Int(validate=lambda x: 1 <= x <= 65535, allow_none=True)
    rcon_password = fields.Str(validate=lambda x: len(x) <= 128, allow_none=True)
    game_type = fields.Str(validate=lambda x: x in ["etlegacy", "quake3"], missing="etlegacy")

    @validates("name")
    def validate_server_name(self, value: str) -> None:
        """Validate server name format"""
        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", value):
            raise ValidationError(
                "Server name can only contain letters, numbers, spaces, hyphens, underscores, and dots"
            )


class UserUpdateSchema(BaseSchema):
    """User profile update schema"""

    first_name = fields.Str(validate=lambda x: 1 <= len(x) <= 50)
    last_name = fields.Str(validate=lambda x: 1 <= len(x) <= 50)
    bio = fields.Str(validate=lambda x: len(x) <= 500, allow_none=True)
    current_password = fields.Str(validate=lambda x: len(x) >= 8)
    new_password = fields.Str(validate=lambda x: 12 <= len(x) <= 128, allow_none=True)
    confirm_new_password = fields.Str(allow_none=True)

    @validates_schema
    def validate_password_change(self, data: Dict[str, Any], **kwargs) -> None:
        """Validate password change logic"""
        if data.get("new_password") or data.get("confirm_new_password"):
            if not data.get("current_password"):
                raise ValidationError("Current password is required to change password")
            if data.get("new_password") != data.get("confirm_new_password"):
                raise ValidationError(
                    "New passwords do not match", field_name="confirm_new_password"
                )

    @validates("new_password")
    def validate_new_password_complexity(self, value: str) -> None:
        """Validate new password complexity"""
        if value:
            if len(value) < 12:
                raise ValidationError("Password must be at least 12 characters long")
            if not re.search(r"[A-Z]", value):
                raise ValidationError("Password must contain at least one uppercase letter")
            if not re.search(r"[a-z]", value):
                raise ValidationError("Password must contain at least one lowercase letter")
            if not re.search(r"\d", value):
                raise ValidationError("Password must contain at least one digit")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
                raise ValidationError("Password must contain at least one special character")


def validate_request(schema_class, data: Dict[str, Any]) -> tuple:
    """Validate request data against a schema"""
    schema = schema_class()
    try:
        return schema.load(data), None
    except ValidationError as err:
        return None, err.messages
