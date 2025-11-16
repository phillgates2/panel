"""
Input Validation Schemas using Marshmallow
Provides type-safe request validation for API endpoints
"""

from marshmallow import Schema, fields, validates, ValidationError, validate
import re


class LoginSchema(Schema):
    """Validation schema for login requests"""
    email = fields.Email(required=True, error_messages={
        'required': 'Email is required',
        'invalid': 'Invalid email address'
    })
    password = fields.Str(required=True, validate=validate.Length(min=1), error_messages={
        'required': 'Password is required'
    })
    captcha = fields.Str(allow_none=True)


class RegisterSchema(Schema):
    """Validation schema for user registration"""
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    last_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    password_confirm = fields.Str(required=True)
    dob = fields.Date(required=True)
    captcha = fields.Str(allow_none=True)
    
    @validates('password')
    def validate_password(self, value):
        """Ensure password meets complexity requirements"""
        if len(value) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValidationError('Password must contain at least one number')


class ServerCreateSchema(Schema):
    """Validation schema for server creation"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    port = fields.Int(required=True, validate=validate.Range(min=1024, max=65535))
    max_players = fields.Int(validate=validate.Range(min=1, max=64), missing=32)
    map_name = fields.Str(validate=validate.Length(max=64), missing='oasis')
    sv_hostname = fields.Str(validate=validate.Length(max=128))
    rcon_password = fields.Str(validate=validate.Length(min=8, max=64))


class ServerUpdateSchema(Schema):
    """Validation schema for server updates"""
    name = fields.Str(validate=validate.Length(min=1, max=100))
    port = fields.Int(validate=validate.Range(min=1024, max=65535))
    max_players = fields.Int(validate=validate.Range(min=1, max=64))
    map_name = fields.Str(validate=validate.Length(max=64))
    sv_hostname = fields.Str(validate=validate.Length(max=128))
    rcon_password = fields.Str(validate=validate.Length(min=8, max=64))
    is_active = fields.Bool()


class RconCommandSchema(Schema):
    """Validation schema for RCON commands"""
    command = fields.Str(required=True, validate=validate.Length(min=1, max=512))
    server_id = fields.Int(required=True)


class DatabaseQuerySchema(Schema):
    """Validation schema for database queries"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=10000))
    database = fields.Str(validate=validate.OneOf(['sqlite', 'mysql']))


class UserUpdateSchema(Schema):
    """Validation schema for user profile updates"""
    first_name = fields.Str(validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(min=1, max=50))
    email = fields.Email()
    dob = fields.Date()
    current_password = fields.Str()
    new_password = fields.Str(validate=validate.Length(min=8, max=128))


class ApiKeyCreateSchema(Schema):
    """Validation schema for API key creation"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=128))
    scopes = fields.List(fields.Str(), missing=[])
    expires_days = fields.Int(validate=validate.Range(min=1, max=365), missing=30)


def validate_request(schema_class, data):
    """
    Helper function to validate request data against a schema
    
    Args:
        schema_class: The marshmallow schema class to use
        data: The data dictionary to validate
        
    Returns:
        Tuple of (validated_data, errors)
    """
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return validated_data, None
    except ValidationError as err:
        return None, err.messages


# Example usage:
# from input_validation import LoginSchema, validate_request
# validated_data, errors = validate_request(LoginSchema, request.form)
# if errors:
#     flash(f'Validation error: {errors}', 'error')
#     return redirect(url_for('login'))
