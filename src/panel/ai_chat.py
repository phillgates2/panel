"""
Real-Time AI Chat Integration
WebSocket-based AI chat with conversation memory and multi-modal support
"""

import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import uuid

from flask_socketio import emit, join_room, leave_room, disconnect
from src.panel.ai_integration import get_ai_client
from src.panel.enhanced_ai import get_enhanced_ai_agent

logger = logging.getLogger(__name__)


class AIChatManager:
    """Manages real-time AI chat conversations"""

    def __init__(self):
        self.active_conversations = {}  # user_id -> conversation data
        self.online_users = set()
        self.typing_users = defaultdict(set)  # room -> set of typing users
        self.ai_client = get_ai_client()
        self.enhanced_ai = get_enhanced_ai_agent()
        self.conversation_timeout = timedelta(hours=24)  # Keep conversations for 24 hours

    def start_conversation(self, user_id: int, room: str = None) -> str:
        """Start a new AI conversation for user"""
        conversation_id = str(uuid.uuid4())

        self.active_conversations[user_id] = {
            "id": conversation_id,
            "user_id": user_id,
            "room": room,
            "messages": [],
            "started_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "ai_personality": "helpful_assistant",
            "context": {},
        }

        logger.info(f"Started AI conversation {conversation_id} for user {user_id}")
        return conversation_id

    def add_message(self, user_id: int, message: Dict[str, Any]) -> bool:
        """Add a message to user's conversation"""
        if user_id not in self.active_conversations:
            return False

        conversation = self.active_conversations[user_id]
        conversation["messages"].append(message)
        conversation["last_activity"] = datetime.utcnow()

        # Keep only last 50 messages to prevent memory issues
        if len(conversation["messages"]) > 50:
            conversation["messages"] = conversation["messages"][-50:]

        return True

    def get_conversation_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent conversation history for user"""
        if user_id not in self.active_conversations:
            return []

        conversation = self.active_conversations[user_id]
        return conversation["messages"][-limit:]

    async def generate_ai_response(
        self, user_id: int, user_message: str, message_type: str = "text"
    ) -> Dict[str, Any]:
        """Generate AI response for user message"""
        if not self.enhanced_ai:
            return {
                "response": "AI assistant is currently unavailable.",
                "type": "text",
                "timestamp": datetime.utcnow().isoformat(),
            }

        conversation = self.active_conversations.get(user_id, {})
        history = conversation.get("messages", [])

        # Prepare context for AI
        context = {
            "conversation_history": history[-10:],  # Last 10 messages
            "user_id": user_id,
            "message_type": message_type,
            "personality": conversation.get("ai_personality", "helpful_assistant"),
        }

        try:
            if message_type == "voice":
                # Handle voice messages differently
                response = await self._process_voice_message(user_message, context)
            elif message_type == "image":
                # Handle image messages
                response = await self._process_image_message(user_message, context)
            else:
                # Text message
                response = await self.enhanced_ai.generate_response(
                    user_message, json.dumps(context)
                )

            ai_response = {
                "response": response,
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                "conversation_id": conversation.get("id"),
            }

            # Add AI response to conversation
            self.add_message(
                user_id,
                {
                    "role": "assistant",
                    "content": response,
                    "type": message_type,
                    "timestamp": ai_response["timestamp"],
                },
            )

            return ai_response

        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return {
                "response": "I apologize, but I encountered an error. Please try again.",
                "type": "text",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def _process_voice_message(self, audio_data: str, context: Dict) -> str:
        """Process voice messages with speech-to-text and analysis"""
        try:
            # Convert speech to text (placeholder - would integrate with speech service)
            text_content = await self._speech_to_text(audio_data)

            # Analyze voice characteristics
            voice_analysis = await self._analyze_voice_characteristics(audio_data)

            # Generate response based on both text and voice analysis
            prompt = f"""User said (via voice): "{text_content}"

Voice analysis: {json.dumps(voice_analysis)}

Conversation context: {json.dumps(context)}

Generate a helpful response that acknowledges both the spoken content and any emotional cues from the voice analysis."""

            response = await self.enhanced_ai.generate_response(prompt)
            return f"[Voice message processed] {response}"

        except Exception as e:
            logger.error(f"Voice message processing failed: {e}")
            return "I heard your voice message but had trouble processing it. Could you please type your message instead?"

    async def _process_image_message(self, image_data: str, context: Dict) -> str:
        """Process image messages with vision AI"""
        try:
            # Analyze image
            analysis = await self.enhanced_ai.analyze_image(image_data)

            # Generate contextual response
            prompt = f"""User shared an image with analysis: {analysis.get('analysis', 'Unable to analyze')}

Conversation context: {json.dumps(context)}

Generate a helpful response that acknowledges the image and provides relevant assistance."""

            response = await self.enhanced_ai.generate_response(prompt)
            return f"[Image shared] {response}"

        except Exception as e:
            logger.error(f"Image message processing failed: {e}")
            return "I see you shared an image! I'm having trouble analyzing it right now, but I'd be happy to help with any questions about it."

    async def _speech_to_text(self, audio_data: str) -> str:
        """Convert speech to text using AI services"""
        # Placeholder - would integrate with Azure Speech Services or Google Speech-to-Text
        # For now, return a mock transcription
        return "This is a transcribed voice message. [Speech-to-text integration needed]"

    async def _analyze_voice_characteristics(self, audio_data: str) -> Dict[str, Any]:
        """Analyze voice characteristics like emotion, speed, etc."""
        # Placeholder - would integrate with voice analysis services
        return {"emotion": "neutral", "confidence": 0.8, "speed": "normal", "clarity": "good"}

    def end_conversation(self, user_id: int) -> bool:
        """End conversation for user"""
        if user_id in self.active_conversations:
            del self.active_conversations[user_id]
            logger.info(f"Ended AI conversation for user {user_id}")
            return True
        return False

    def cleanup_old_conversations(self):
        """Clean up old inactive conversations"""
        current_time = datetime.utcnow()
        to_remove = []

        for user_id, conversation in self.active_conversations.items():
            if current_time - conversation["last_activity"] > self.conversation_timeout:
                to_remove.append(user_id)

        for user_id in to_remove:
            del self.active_conversations[user_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old conversations")

    def get_online_users(self) -> List[int]:
        """Get list of online users"""
        return list(self.online_users)

    def user_online(self, user_id: int):
        """Mark user as online"""
        self.online_users.add(user_id)

    def user_offline(self, user_id: int):
        """Mark user as offline"""
        self.online_users.discard(user_id)

    def user_typing(self, user_id: int, room: str, is_typing: bool):
        """Update typing status"""
        if is_typing:
            self.typing_users[room].add(user_id)
        else:
            self.typing_users[room].discard(user_id)

    def get_typing_users(self, room: str) -> List[int]:
        """Get users currently typing in room"""
        return list(self.typing_users[room])


# Global AI chat manager
ai_chat_manager = None


def init_ai_chat():
    """Initialize AI chat manager"""
    global ai_chat_manager
    ai_chat_manager = AIChatManager()
    logger.info("AI chat manager initialized")


def get_ai_chat_manager() -> Optional[AIChatManager]:
    """Get the AI chat manager instance"""
    return ai_chat_manager


# WebSocket event handlers
def register_ai_chat_handlers(socketio):
    """Register AI chat WebSocket event handlers"""

    @socketio.on("ai_chat_join")
    def handle_ai_chat_join(data):
        """User joins AI chat"""
        user_id = data.get("user_id")
        room = f"ai_chat_{user_id}"

        join_room(room)
        emit(
            "ai_chat_joined",
            {
                "conversation_id": ai_chat_manager.start_conversation(user_id, room),
                "message": "AI assistant is ready to help!",
            },
        )

        ai_chat_manager.user_online(user_id)

    @socketio.on("ai_chat_message")
    async def handle_ai_chat_message(data):
        """Handle AI chat message"""
        user_id = data.get("user_id")
        message = data.get("message", "")
        message_type = data.get("type", "text")

        if not message:
            return

        room = f"ai_chat_{user_id}"

        # Add user message to conversation
        ai_chat_manager.add_message(
            user_id,
            {
                "role": "user",
                "content": message,
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Emit user message to room
        emit(
            "ai_chat_message",
            {
                "role": "user",
                "content": message,
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=room,
        )

        # Generate AI response
        ai_response = await ai_chat_manager.generate_ai_response(user_id, message, message_type)

        # Emit AI response to room
        emit(
            "ai_chat_message",
            {
                "role": "assistant",
                "content": ai_response["response"],
                "type": ai_response["type"],
                "timestamp": ai_response["timestamp"],
            },
            room=room,
        )

    @socketio.on("ai_chat_typing")
    def handle_ai_chat_typing(data):
        """Handle typing indicators"""
        user_id = data.get("user_id")
        room = f"ai_chat_{user_id}"
        is_typing = data.get("typing", False)

        ai_chat_manager.user_typing(user_id, room, is_typing)

        # Broadcast typing status to room
        emit(
            "ai_chat_typing_update",
            {"typing_users": ai_chat_manager.get_typing_users(room)},
            room=room,
            skip_sid=True,
        )

    @socketio.on("ai_chat_leave")
    def handle_ai_chat_leave(data):
        """User leaves AI chat"""
        user_id = data.get("user_id")
        room = f"ai_chat_{user_id}"

        leave_room(room)
        ai_chat_manager.end_conversation(user_id)
        ai_chat_manager.user_offline(user_id)

        emit("ai_chat_left", {"message": "AI chat ended"})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle user disconnection"""
        # Note: In a real implementation, you'd track user sessions
        # and clean up conversations on disconnect
        pass


# Background task for cleanup
async def cleanup_ai_conversations():
    """Background task to clean up old conversations"""
    while True:
        if ai_chat_manager:
            ai_chat_manager.cleanup_old_conversations()
        await asyncio.sleep(3600)  # Run every hour


# Start cleanup task
def start_ai_chat_cleanup(socketio):
    """Start the AI chat cleanup background task"""
    socketio.start_background_task(cleanup_ai_conversations)
