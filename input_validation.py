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
    """Validate request data against schema."""
    schema = schema_class()
    try:
        return schema.load(data)
    except ValidationError as err:
        raise err
