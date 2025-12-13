"""Input validation schemas for Panel."""

from marshmallow import Schema, ValidationError, fields


class LoginSchema(Schema):
    """Login validation schema."""

    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)


class RegisterSchema(Schema):
    """Registration validation schema."""

    first_name = fields.Str(required=True, validate=lambda x: len(x) >= 2)
    last_name = fields.Str(required=True, validate=lambda x: len(x) >= 2)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 8)
    password_confirm = fields.Str(required=True)
    dob = fields.Date(required=True)


def validate_request(schema_class, data):
    """Validate request data against schema.

    Returns a tuple of (validated_data, errors). On success, errors is None.
    On validation failure, validated_data is None and errors is a dict.
    """
    schema = schema_class()
    try:
        result = schema.load(data)
        return result, None
    except ValidationError as err:
        return None, err.messages
