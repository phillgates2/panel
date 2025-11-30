from flask import Blueprint, jsonify, request
from flask_login import current_user

from src.panel.models import ROLE_HIERARCHY, ROLE_PERMISSIONS

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/swagger.json")
def swagger_json():
    return {
        "swagger": "2.0",
        "info": {
            "title": "Panel API",
            "version": "1.0",
            "description": "API for Panel application",
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
                                    "uptime": {"type": "number"},
                                },
                            },
                        }
                    },
                }
            }
        },
    }


@api_bp.route("/permissions")
def get_permissions():
    return {
        "roles": ROLE_HIERARCHY,
        "permissions": ROLE_PERMISSIONS,
        "user_permissions": (
            current_user.get_available_permissions()
            if current_user.is_authenticated
            else []
        ),
    }


@api_bp.route("/user/<int:user_id>/role", methods=["POST"])
def update_user_role(user_id):
    if not current_user.is_authenticated or not current_user.can_grant_role(
        request.json.get("role")
    ):
        return {"error": "Unauthorized"}, 403

    from src.panel.models import User

    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}, 404

    new_role = request.json.get("role")
    if new_role not in ROLE_HIERARCHY:
        return {"error": "Invalid role"}, 400

    user.role = new_role
    from src.panel.models import db

    db.session.commit()

    return {"success": True, "role": new_role}
