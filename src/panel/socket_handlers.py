"""
Real-time WebSocket handlers using Flask-SocketIO
Provides live updates for forum, user status, and server monitoring
"""

import json
from datetime import datetime

from flask import request
from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room
from sqlalchemy import desc

from src.panel import db
from src.panel.forum import Post, Thread
from src.panel.models import Server, User
from src.panel.services.cache_service import get_cache_service

socketio = SocketIO(cors_allowed_origins="*")


# Import AI chat handlers
from src.panel.ai_chat import register_ai_chat_handlers, start_ai_chat_cleanup

# Register AI chat handlers
register_ai_chat_handlers(socketio)

# Start AI chat cleanup
start_ai_chat_cleanup(socketio)


class RealTimeManager:
    """Manages real-time connections and events"""

    def __init__(self):
        self.user_sockets = {}  # user_id -> list of socket_ids
        self.room_members = {}  # room_name -> set of user_ids
        self.cache = get_cache_service()

    def add_user_connection(self, user_id, socket_id):
        """Add user connection"""
        if user_id not in self.user_sockets:
            self.user_sockets[user_id] = []
        self.user_sockets[user_id].append(socket_id)

        # Update user online status
        self.update_user_status(user_id, True)

    def remove_user_connection(self, user_id, socket_id):
        """Remove user connection"""
        if user_id in self.user_sockets:
            self.user_sockets[user_id].remove(socket_id)
            if not self.user_sockets[user_id]:
                del self.user_sockets[user_id]
                # Update user offline status
                self.update_user_status(user_id, False)

    def update_user_status(self, user_id, online):
        """Update user online status"""
        try:
            user = User.query.get(user_id)
            if user:
                user.last_login = datetime.utcnow() if online else user.last_login
                db.session.commit()

                # Broadcast status change
                socketio.emit(
                    "user_status_change",
                    {
                        "user_id": user_id,
                        "username": user.first_name + " " + user.last_name,
                        "online": online,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

        except Exception as e:
            print(f"Error updating user status: {e}")

    def join_forum_room(self, user_id, thread_id):
        """Join user to forum thread room"""
        room_name = f"forum_{thread_id}"
        join_room(room_name)

        if room_name not in self.room_members:
            self.room_members[room_name] = set()
        self.room_members[room_name].add(user_id)

        # Send recent activity
        self.send_recent_forum_activity(thread_id)

    def leave_forum_room(self, user_id, thread_id):
        """Leave user from forum thread room"""
        room_name = f"forum_{thread_id}"
        leave_room(room_name)

        if room_name in self.room_members:
            self.room_members[room_name].discard(user_id)
            if not self.room_members[room_name]:
                del self.room_members[room_name]

    def send_forum_update(self, thread_id, update_type, data):
        """Send forum update to thread room"""
        room_name = f"forum_{thread_id}"
        socketio.emit(
            "forum_update",
            {
                "type": update_type,
                "thread_id": thread_id,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=room_name,
        )

    def send_recent_forum_activity(self, thread_id):
        """Send recent forum activity to user"""
        try:
            # Get recent posts for this thread
            recent_posts = (
                Post.query.filter_by(thread_id=thread_id)
                .order_by(desc(Post.created_at))
                .limit(10)
                .all()
            )

            activity_data = []
            for post in recent_posts:
                activity_data.append(
                    {
                        "id": post.id,
                        "author": (
                            post.author.display_name if post.author else "Unknown"
                        ),
                        "content": (
                            post.content[:200] + "..."
                            if len(post.content) > 200
                            else post.content
                        ),
                        "timestamp": post.created_at.isoformat(),
                        "is_recent": True,
                    }
                )

            socketio.emit(
                "forum_activity",
                {"thread_id": thread_id, "activity": activity_data},
                room=request.sid,
            )

        except Exception as e:
            print(f"Error sending forum activity: {e}")

    def broadcast_server_status(self, server_id, status_data):
        """Broadcast server status update"""
        socketio.emit(
            "server_status_update",
            {
                "server_id": server_id,
                "status": status_data,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def send_notification(self, user_id, notification_data):
        """Send notification to specific user"""
        if user_id in self.user_sockets:
            for socket_id in self.user_sockets[user_id]:
                socketio.emit("notification", notification_data, room=socket_id)

    def get_online_users(self):
        """Get list of currently online users"""
        return list(self.user_sockets.keys())

    def get_room_members(self, room_name):
        """Get members of a room"""
        return list(self.room_members.get(room_name, set()))


# Global instance
realtime_manager = RealTimeManager()


# SocketIO event handlers
@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit("connected", {"status": "success", "timestamp": datetime.utcnow().isoformat()})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

    # Find and remove user connection
    for user_id, sockets in realtime_manager.user_sockets.items():
        if request.sid in sockets:
            realtime_manager.remove_user_connection(user_id, request.sid)
            break


@socketio.on("authenticate")
def handle_authenticate(data):
    """Handle user authentication for real-time features"""
    try:
        user_id = data.get("user_id")
        if user_id:
            realtime_manager.add_user_connection(user_id, request.sid)
            emit(
                "authenticated",
                {
                    "status": "success",
                    "online_users": len(realtime_manager.get_online_users()),
                },
            )

            # Send push notification if user just came online
            from src.panel.push_notifications import get_push_service

            push_service = get_push_service()
            if push_service:
                push_service.send_notification(
                    user_id=user_id,
                    title="Welcome back!",
                    body="You're now connected to Panel.",
                    url="/dashboard",
                )

    except Exception as e:
        print(f"Authentication error: {e}")
        emit("error", {"message": "Authentication failed"})


@socketio.on("join_forum")
def handle_join_forum(data):
    """Join forum thread room"""
    try:
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")

        if user_id and thread_id:
            realtime_manager.join_forum_room(user_id, thread_id)
            emit("forum_joined", {"thread_id": thread_id, "status": "success"})

    except Exception as e:
        print(f"Join forum error: {e}")
        emit("error", {"message": "Failed to join forum"})


@socketio.on("leave_forum")
def handle_leave_forum(data):
    """Leave forum thread room"""
    try:
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")

        if user_id and thread_id:
            realtime_manager.leave_forum_room(user_id, thread_id)
            emit("forum_left", {"thread_id": thread_id, "status": "success"})

    except Exception as e:
        print(f"Leave forum error: {e}")
        emit("error", {"message": "Failed to leave forum"})


@socketio.on("forum_post")
def handle_forum_post(data):
    """Handle new forum post"""
    try:
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")
        content = data.get("content")

        if user_id and thread_id and content:
            # Create the post (this would normally be done via API)
            # For real-time demo, we'll just broadcast
            user = User.query.get(user_id)
            if user:
                realtime_manager.send_forum_update(
                    thread_id,
                    "new_post",
                    {
                        "author": user.display_name,
                        "content": (
                            content[:200] + "..." if len(content) > 200 else content
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # Send notification to thread participants
                thread_members = realtime_manager.get_room_members(f"forum_{thread_id}")
                for member_id in thread_members:
                    if member_id != user_id:  # Don't notify the poster
                        realtime_manager.send_notification(
                            member_id,
                            {
                                "type": "forum_reply",
                                "title": "New reply in forum",
                                "body": f"{user.display_name} replied to a thread you're following",
                                "url": f"/forum/thread/{thread_id}",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )

    except Exception as e:
        print(f"Forum post error: {e}")
        emit("error", {"message": "Failed to post"})


@socketio.on("typing_start")
def handle_typing_start(data):
    """Handle user started typing"""
    try:
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")

        if user_id and thread_id:
            user = User.query.get(user_id)
            if user:
                room_name = f"forum_{thread_id}"
                emit(
                    "user_typing",
                    {
                        "user_id": user_id,
                        "username": user.display_name,
                        "action": "start",
                    },
                    room=room_name,
                    skip_sid=request.sid,
                )

    except Exception as e:
        print(f"Typing start error: {e}")


@socketio.on("typing_stop")
def handle_typing_stop(data):
    """Handle user stopped typing"""
    try:
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")

        if user_id and thread_id:
            user = User.query.get(user_id)
            if user:
                room_name = f"forum_{thread_id}"
                emit(
                    "user_typing",
                    {
                        "user_id": user_id,
                        "username": user.display_name,
                        "action": "stop",
                    },
                    room=room_name,
                    skip_sid=request.sid,
                )

    except Exception as e:
        print(f"Typing stop error: {e}")


@socketio.on("get_online_users")
def handle_get_online_users():
    """Get list of online users"""
    try:
        online_users = []
        for user_id in realtime_manager.get_online_users():
            user = User.query.get(user_id)
            if user:
                online_users.append(
                    {"id": user.id, "name": user.display_name, "avatar": user.avatar}
                )

        emit("online_users_list", {"users": online_users, "count": len(online_users)})

    except Exception as e:
        print(f"Get online users error: {e}")
        emit("error", {"message": "Failed to get online users"})


@socketio.on("server_status_request")
def handle_server_status_request(data):
    """Request server status updates"""
    try:
        server_ids = data.get("server_ids", [])

        # Send current status for requested servers
        for server_id in server_ids:
            server = Server.query.get(server_id)
            if server:
                # This would normally get real server status
                # For demo, send mock status
                status_data = {
                    "status": "online",  # Could be 'online', 'offline', 'maintenance'
                    "players": 15,
                    "max_players": 32,
                    "map": "etl_sp_delivery",
                    "ping": 45,
                }
                realtime_manager.broadcast_server_status(server_id, status_data)

    except Exception as e:
        print(f"Server status request error: {e}")
        emit("error", {"message": "Failed to get server status"})


# Utility functions for external use
def notify_forum_reply(thread_id, post_data):
    """Notify forum thread members of new reply"""
    realtime_manager.send_forum_update(thread_id, "new_reply", post_data)


def notify_server_status_change(server_id, status_data):
    """Notify about server status changes"""
    realtime_manager.broadcast_server_status(server_id, status_data)


def notify_user_online(user_id):
    """Notify when user comes online"""
    realtime_manager.update_user_status(user_id, True)


def notify_user_offline(user_id):
    """Notify when user goes offline"""
    realtime_manager.update_user_status(user_id, False)


def get_realtime_manager():
    """Get the global realtime manager instance"""
    return realtime_manager
