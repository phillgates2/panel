from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.utils import moderate_message
from src.panel.models import ChatMessage, db

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat/rooms")
def get_chat_rooms():
    return {"rooms": ["general", "support", "random"], "current_room": "general"}


@chat_bp.route("/api/chat/messages/<room>", methods=["GET", "POST"])
def chat_messages(room):
    if request.method == "POST":
        data = request.json
        message = data["message"]
        moderated = moderate_message(message)
        user_id = (
            getattr(current_user, "id", None) if current_user.is_authenticated else None
        )
        msg = ChatMessage(
            room=room,
            user_id=user_id,
            username=data["username"],
            message=message,
            moderated=moderated,
        )
        db.session.add(msg)
        db.session.commit()
        return {"status": "sent", "moderated": moderated}

    # GET
    messages = (
        ChatMessage.query.filter_by(room=room, moderated=True)
        .order_by(ChatMessage.timestamp)
        .limit(50)
        .all()
    )
    return {
        "messages": [
            {
                "id": m.id,
                "username": m.username,
                "message": m.message,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in messages
        ]
    }


@chat_bp.route("/api/chat/moderate/<int:message_id>", methods=["POST"])
def moderate_message_route(message_id):
    if not current_user or not current_user.has_permission("moderate_forum"):
        return {"error": "Unauthorized"}, 403

    msg = ChatMessage.query.get(message_id)
    if not msg:
        return {"error": "Message not found"}, 404

    action = request.json.get("action")
    if action == "approve":
        msg.moderated = True
    elif action == "reject":
        msg.moderated = False
    elif action == "flag":
        msg.flagged = True

    db.session.commit()
    return {"status": "updated"}


@chat_bp.route("/api/admin/chat-messages")
def admin_chat_messages():
    if not current_user or not current_user.has_permission("moderate_forum"):
        return {"error": "Unauthorized"}, 403

    tab = request.args.get("tab", "pending")

    if tab == "pending":
        messages = (
            ChatMessage.query.filter_by(moderated=False)
            .order_by(ChatMessage.timestamp.desc())
            .limit(50)
            .all()
        )
    elif tab == "flagged":
        messages = (
            ChatMessage.query.filter_by(flagged=True)
            .order_by(ChatMessage.timestamp.desc())
            .limit(50)
            .all()
        )
    else:
        messages = (
            ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(50).all()
        )

    return {
        "messages": [
            {
                "id": m.id,
                "username": m.username,
                "message": m.message,
                "room": m.room,
                "timestamp": m.timestamp.isoformat(),
                "moderated": m.moderated,
                "flagged": m.flagged,
            }
            for m in messages
        ]
    }
