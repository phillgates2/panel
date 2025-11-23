"""
AI Integration with Azure OpenAI
Intelligent features for content moderation, chat assistance, and analytics
"""

import os
import asyncio
import openai
from typing import Dict, List, Optional, Any
import logging
import json
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Azure OpenAI client for AI-powered features"""

    def __init__(self):
        # Initialize Azure OpenAI client
        self.client = openai.AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version="2023-12-01-preview",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )

        self.deployment_gpt4 = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT4', 'gpt-4')
        self.deployment_gpt35 = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT35', 'gpt-35-turbo')

        # Rate limiting
        self.request_count = 0
        self.last_reset = datetime.utcnow()

    async def _check_rate_limit(self):
        """Check and handle rate limiting"""
        now = datetime.utcnow()
        if (now - self.last_reset).seconds >= 60:  # Reset every minute
            self.request_count = 0
            self.last_reset = now

        if self.request_count >= 50:  # Azure OpenAI rate limit (adjust based on your tier)
            wait_time = 60 - (now - self.last_reset).seconds
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.request_count = 0

        self.request_count += 1

    async def moderate_content(self, content: str) -> Dict[str, Any]:
        """Moderate forum posts and comments for inappropriate content"""
        try:
            await self._check_rate_limit()

            response = await self.client.moderations.create(
                input=content
            )

            result = response.results[0]
            return {
                'flagged': result.flagged,
                'categories': result.categories.model_dump(),
                'category_scores': result.category_scores.model_dump(),
                'moderated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Content moderation failed: {e}")
            return {
                'flagged': False,
                'error': str(e),
                'moderated_at': datetime.utcnow().isoformat()
            }

    async def generate_response(self, prompt: str, context: str = "", user_history: List[Dict] = None) -> str:
        """Generate AI-powered responses for user queries"""
        system_prompt = """You are a helpful assistant for a gaming community platform called Panel.
        You help users with gaming, server management, community guidelines, and technical issues.
        Be friendly, accurate, and concise. If you don't know something, admit it and suggest asking the community.
        Always follow community guidelines and promote positive interactions."""

        try:
            await self._check_rate_limit()

            messages = [{"role": "system", "content": system_prompt}]

            # Add user history for context
            if user_history:
                for msg in user_history[-5:]:  # Last 5 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current context
            if context:
                messages.append({"role": "user", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return "I'm sorry, I'm having trouble generating a response right now. Please try again later."

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of user feedback and forum posts"""
        try:
            await self._check_rate_limit()

            prompt = f"""Analyze the sentiment of this text and provide:
1. Overall sentiment (positive, negative, neutral)
2. Confidence score (0-1)
3. Key emotions detected
4. Brief explanation (max 50 words)

Text: {text}

Format your response as JSON with keys: sentiment, confidence, emotions, explanation"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            # Try to parse as JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback parsing
                result = {
                    'sentiment': 'neutral',
                    'confidence': 0.5,
                    'emotions': [],
                    'explanation': result_text
                }

            result['analyzed_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'emotions': [],
                'explanation': 'Analysis failed',
                'error': str(e),
                'analyzed_at': datetime.utcnow().isoformat()
            }

    async def suggest_tags(self, content: str, existing_tags: List[str] = None) -> List[str]:
        """Suggest relevant tags for forum posts"""
        try:
            await self._check_rate_limit()

            prompt = f"""Based on this forum post content, suggest 3-5 relevant tags.
Return only the tags as a comma-separated list. Focus on gaming, technology, and community topics.
Avoid generic tags like "gaming" unless highly relevant.

Existing tags: {', '.join(existing_tags) if existing_tags else 'none'}

Content: {content}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5
            )

            tags_str = response.choices[0].message.content.strip()
            tags = [tag.strip().lower() for tag in tags_str.split(',') if tag.strip()]

            # Remove duplicates and limit to 5
            tags = list(set(tags))[:5]

            return tags

        except Exception as e:
            logger.error(f"Tag suggestion failed: {e}")
            return []

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect the language of user input"""
        try:
            await self._check_rate_limit()

            prompt = f"""Detect the primary language of this text.
Return a JSON object with:
- language: The language name (e.g., "English", "Spanish", "French")
- confidence: Confidence score (0-1)
- code: ISO language code (e.g., "en", "es", "fr")

Text: {text}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1
            )

            result_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    'language': 'unknown',
                    'confidence': 0.0,
                    'code': 'unknown'
                }

            result['detected_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                'language': 'unknown',
                'confidence': 0.0,
                'code': 'unknown',
                'error': str(e),
                'detected_at': datetime.utcnow().isoformat()
            }

    async def summarize_content(self, content: str, max_length: int = 200) -> str:
        """Summarize long content for previews or notifications"""
        try:
            await self._check_rate_limit()

            prompt = f"""Summarize this content in {max_length} characters or less.
Keep the most important information and maintain the original meaning.

Content: {content}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length // 4,  # Rough token estimate
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()

            # Ensure it's within limits
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."

            return summary

        except Exception as e:
            logger.error(f"Content summarization failed: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content

    async def classify_content(self, content: str, categories: List[str]) -> Dict[str, Any]:
        """Classify content into predefined categories"""
        try:
            await self._check_rate_limit()

            categories_str = ", ".join(categories)
            prompt = f"""Classify this content into one of these categories: {categories_str}

Return a JSON object with:
- category: The best matching category
- confidence: Confidence score (0-1)
- explanation: Brief reason for classification (max 50 words)

Content: {content}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.2
            )

            result_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    'category': categories[0] if categories else 'unknown',
                    'confidence': 0.0,
                    'explanation': 'Classification failed'
                }

            result['classified_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            return {
                'category': categories[0] if categories else 'unknown',
                'confidence': 0.0,
                'explanation': 'Classification failed',
                'error': str(e),
                'classified_at': datetime.utcnow().isoformat()
            }

# Global AI client instance
ai_client = None

def init_ai_client():
    """Initialize the AI client"""
    global ai_client
    if os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT'):
        ai_client = AzureOpenAIClient()
        logger.info("Azure OpenAI client initialized")
    else:
        logger.warning("Azure OpenAI not configured - AI features disabled")

def get_ai_client() -> Optional[AzureOpenAIClient]:
    """Get the AI client instance"""
    return ai_client

# Decorators for AI features
def with_content_moderation(f):
    """Decorator to add content moderation to functions"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        # Extract content from arguments (assuming first string argument is content)
        content = None
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10:  # Simple heuristic
                content = arg
                break

        if content:
            ai_client = get_ai_client()
            if ai_client:
                moderation = await ai_client.moderate_content(content)
                if moderation.get('flagged'):
                    # Handle flagged content (log, reject, etc.)
                    logger.warning(f"Content flagged by AI moderation: {moderation}")
                    # You could raise an exception or return an error response

        return await f(*args, **kwargs)
    return wrapper

def with_sentiment_analysis(f):
    """Decorator to add sentiment analysis to functions"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        result = await f(*args, **kwargs)

        # Analyze sentiment of result if it's a string
        if isinstance(result, str) and len(result) > 20:
            ai_client = get_ai_client()
            if ai_client:
                sentiment = await ai_client.analyze_sentiment(result)
                # Add sentiment to result or log it
                logger.info(f"Response sentiment: {sentiment}")

        return result
    return wrapper

# Utility functions
async def moderate_text(text: str) -> bool:
    """Quick function to check if text is appropriate"""
    ai_client = get_ai_client()
    if ai_client:
        result = await ai_client.moderate_content(text)
        return not result.get('flagged', False)
    return True  # Default to allowed if AI not available

async def generate_ai_response(prompt: str, context: str = None) -> str:
    """Generate an AI response for user queries"""
    ai_client = get_ai_client()
    if ai_client:
        return await ai_client.generate_response(prompt, context)
    return "AI features are currently unavailable."

async def analyze_user_feedback(text: str) -> Dict[str, Any]:
    """Analyze user feedback or reviews"""
    ai_client = get_ai_client()
    if ai_client:
        return await ai_client.analyze_sentiment(text)
    return {'sentiment': 'neutral', 'confidence': 0.0}

async def suggest_post_tags(content: str) -> List[str]:
    """Suggest tags for forum posts"""
    ai_client = get_ai_client()
    if ai_client:
        return await ai_client.suggest_tags(content)
    return []

# AI-powered features for the application
class AIContentModerator:
    """AI-powered content moderation system"""

    def __init__(self):
        self.ai_client = get_ai_client()
        self.moderation_stats = {
            'total_checked': 0,
            'flagged': 0,
            'categories': {}
        }

    async def moderate_post(self, content: str, user_id: int = None) -> Dict[str, Any]:
        """Moderate a forum post"""
        if not self.ai_client:
            return {'approved': True, 'reason': 'AI not available'}

        self.moderation_stats['total_checked'] += 1

        result = await self.ai_client.moderate_content(content)

        if result.get('flagged'):
            self.moderation_stats['flagged'] += 1

            # Update category stats
            for category, flagged in result.get('categories', {}).items():
                if flagged:
                    self.moderation_stats['categories'][category] = \
                        self.moderation_stats['categories'].get(category, 0) + 1

            return {
                'approved': False,
                'reason': 'Content flagged by AI moderation',
                'categories': result.get('categories', {}),
                'moderated_at': result.get('moderated_at')
            }

        return {
            'approved': True,
            'moderated_at': result.get('moderated_at')
        }

    def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation statistics"""
        return {
            **self.moderation_stats,
            'flagged_percentage': (self.moderation_stats['flagged'] / max(self.moderation_stats['total_checked'], 1)) * 100
        }

class AIAssistant:
    """AI-powered assistant for user support"""

    def __init__(self):
        self.ai_client = get_ai_client()
        self.conversation_history = {}

    async def get_response(self, user_id: int, message: str, context: str = None) -> str:
        """Get AI response for user message"""
        if not self.ai_client:
            return "I'm sorry, the AI assistant is currently unavailable."

        # Get conversation history
        history = self.conversation_history.get(user_id, [])

        # Add current message to history
        history.append({"role": "user", "content": message})

        # Generate response
        response = await self.ai_client.generate_response(message, context, history)

        # Add response to history
        history.append({"role": "assistant", "content": response})

        # Keep only last 10 messages
        self.conversation_history[user_id] = history[-10:]

        return response

    def clear_history(self, user_id: int):
        """Clear conversation history for user"""
        self.conversation_history.pop(user_id, None)

class AIContentAnalyzer:
    """AI-powered content analysis for insights"""

    def __init__(self):
        self.ai_client = get_ai_client()

    async def analyze_forum_trends(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze forum posts for trends and insights"""
        if not self.ai_client or not posts:
            return {'error': 'AI not available or no posts to analyze'}

        # Combine post content for analysis
        combined_content = "\n".join([post.get('content', '') for post in posts[:10]])

        prompt = f"""Analyze these forum posts and provide insights:

1. Main topics discussed
2. Overall sentiment
3. Common themes or issues
4. Suggested improvements

Posts:
{combined_content}

Provide a JSON response with keys: topics, sentiment, themes, suggestions"""

        try:
            response = await self.ai_client.client.chat.completions.create(
                model=self.ai_client.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                return {'error': 'Failed to parse AI response'}

        except Exception as e:
            logger.error(f"Forum trend analysis failed: {e}")
            return {'error': str(e)}

# Global instances
content_moderator = None
ai_assistant = None
content_analyzer = None

def init_ai_features():
    """Initialize all AI features"""
    global content_moderator, ai_assistant, content_analyzer

    init_ai_client()

    if get_ai_client():
        content_moderator = AIContentModerator()
        ai_assistant = AIAssistant()
        content_analyzer = AIContentAnalyzer()
        logger.info("AI features initialized")
    else:
        logger.warning("AI features not available - Azure OpenAI not configured")

def get_content_moderator() -> Optional[AIContentModerator]:
    """Get the content moderator instance"""
    return content_moderator

def get_ai_assistant() -> Optional[AIAssistant]:
    """Get the AI assistant instance"""
    return ai_assistant

def get_content_analyzer() -> Optional[AIContentAnalyzer]:
    """Get the content analyzer instance"""
    return content_analyzer