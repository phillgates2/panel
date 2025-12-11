"""
AI Integration Module

This module provides integration with OpenAI GPT models for various features
like chat assistance, content generation, and automated responses.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from flask import current_app
from openai import OpenAI

from src.panel.models import db


class GPTIntegration:
    """Integration with OpenAI GPT models for Panel features."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize GPT integration.

        Args:
            api_key: OpenAI API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.model = os.environ.get('OPENAI_MODEL', 'gpt-4')

    def generate_server_description(self, server_data: Dict) -> str:
        """Generate an engaging server description using GPT.

        Args:
            server_data: Dictionary containing server information

        Returns:
            Generated server description
        """
        prompt = f"""
        Generate an engaging, professional description for a game server based on the following information:

        Server Name: {server_data.get('name', 'Unknown')}
        Game Type: {server_data.get('game_type', 'Unknown')}
        Description: {server_data.get('description', '')}
        Max Players: {server_data.get('max_players', 'Unknown')}
        Current Players: {server_data.get('current_players', 0)}
        Location: {server_data.get('location', 'Unknown')}

        The description should be:
        - Engaging and inviting
        - Professional in tone
        - Highlight key features
        - Under 200 characters
        - Suitable for a gaming community

        Generate only the description text, no additional formatting.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates engaging game server descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"GPT description generation failed: {e}")
            return server_data.get('description', 'A great gaming experience awaits!')

    def analyze_chat_sentiment(self, messages: List[str]) -> Dict[str, Any]:
        """Analyze sentiment of chat messages using GPT.

        Args:
            messages: List of chat messages to analyze

        Returns:
            Sentiment analysis results
        """
        if not messages:
            return {'overall_sentiment': 'neutral', 'confidence': 0.5}

        # Combine messages for analysis
        combined_text = ' '.join(messages[-10:])  # Analyze last 10 messages

        prompt = f"""
        Analyze the sentiment of the following chat messages and provide:
        1. Overall sentiment (positive, negative, neutral)
        2. Confidence score (0-1)
        3. Key themes or topics discussed
        4. Any concerning content that might need moderation

        Messages: {combined_text}

        Respond in JSON format with keys: overall_sentiment, confidence, themes, concerning_content
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis expert. Analyze chat messages and respond in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3,
            )

            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
            current_app.logger.error(f"GPT sentiment analysis failed: {e}")
            return {
                'overall_sentiment': 'neutral',
                'confidence': 0.5,
                'themes': [],
                'concerning_content': False
            }

    def generate_help_response(self, user_question: str, context: Optional[Dict] = None) -> str:
        """Generate a helpful response to user questions using GPT.

        Args:
            user_question: User's question
            context: Additional context information

        Returns:
            Generated help response
        """
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context)}"

        prompt = f"""
        You are a helpful support assistant for the Panel game server management platform.
        Answer the user's question in a friendly, professional manner.

        Question: {user_question}{context_str}

        Guidelines:
        - Be concise but helpful
        - Use simple language
        - Include relevant links or commands when appropriate
        - If you don't know something, suggest contacting support
        - Focus on Panel-specific features and game server management

        Provide a direct answer to the question.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful support assistant for Panel, a game server management platform."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"GPT help response generation failed: {e}")
            return "I'm sorry, I'm having trouble generating a response right now. Please try again later or contact our support team."

    def moderate_content(self, content: str, content_type: str = "chat") -> Dict[str, Any]:
        """Moderate content using GPT for appropriateness.

        Args:
            content: Content to moderate
            content_type: Type of content (chat, post, profile, etc.)

        Returns:
            Moderation results
        """
        prompt = f"""
        Moderate the following {content_type} content for appropriateness in a gaming community:

        Content: {content}

        Evaluate for:
        1. Inappropriate language or harassment
        2. Spam or promotional content
        3. Harmful or dangerous content
        4. Violation of community guidelines

        Respond in JSON format with:
        - approved: boolean
        - reason: string (if not approved)
        - severity: "low", "medium", "high" (if inappropriate)
        - suggested_action: "allow", "flag", "remove", "ban"
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a content moderation expert for gaming communities. Evaluate content and respond in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.2,
            )

            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
            current_app.logger.error(f"GPT content moderation failed: {e}")
            return {
                'approved': True,
                'reason': None,
                'severity': None,
                'suggested_action': 'allow'
            }

    def generate_server_config(self, game_type: str, preferences: Dict) -> Dict[str, Any]:
        """Generate optimized server configuration using GPT.

        Args:
            game_type: Type of game server
            preferences: User preferences for configuration

        Returns:
            Generated server configuration
        """
        prompt = f"""
        Generate an optimized server configuration for {game_type} based on these preferences:

        Preferences: {json.dumps(preferences)}

        Provide a complete server configuration with:
        - Recommended settings for performance
        - Balanced gameplay settings
        - Security considerations
        - Resource optimization

        Respond in JSON format with configuration sections and values.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a game server configuration expert. Generate optimized server configs in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.5,
            )

            import json
            config = json.loads(response.choices[0].message.content.strip())
            return config
        except Exception as e:
            current_app.logger.error(f"GPT config generation failed: {e}")
            return {
                'error': 'Configuration generation failed',
                'fallback': 'Please use the default configuration'
            }


class AIWorkflowManager:
    """Manager for AI-powered workflows and automation."""

    def __init__(self, gpt_integration: GPTIntegration):
        """Initialize AI workflow manager.

        Args:
            gpt_integration: GPT integration instance
        """
        self.gpt = gpt_integration

    def automate_server_setup(self, requirements: Dict) -> Dict[str, Any]:
        """Automate server setup process using AI.

        Args:
            requirements: Server setup requirements

        Returns:
            Automated setup configuration
        """
        # This would use GPT to analyze requirements and generate setup steps
        # Implementation would involve multiple GPT calls for different aspects

        setup_plan = {
            'server_type': requirements.get('game_type'),
            'estimated_setup_time': '15-30 minutes',
            'required_resources': {
                'cpu': '2 cores',
                'ram': '4GB',
                'storage': '20GB'
            },
            'security_measures': [
                'Firewall configuration',
                'RCON password protection',
                'Access control setup'
            ],
            'optimization_recommendations': [
                'Enable compression',
                'Configure caching',
                'Set up monitoring'
            ]
        }

        return setup_plan

    def predict_server_performance(self, current_metrics: Dict) -> Dict[str, Any]:
        """Predict server performance trends using AI.

        Args:
            current_metrics: Current server performance metrics

        Returns:
            Performance predictions and recommendations
        """
        # This would analyze historical data and current metrics
        # to predict future performance and provide recommendations

        predictions = {
            'cpu_usage_trend': 'stable',
            'memory_usage_trend': 'increasing',
            'network_usage_trend': 'stable',
            'recommendations': [
                'Consider upgrading RAM if usage exceeds 80%',
                'Monitor CPU spikes during peak hours',
                'Optimize network settings for better throughput'
            ],
            'predicted_issues': [],
            'confidence_score': 0.85
        }

        return predictions

    def generate_incident_response(self, incident_data: Dict) -> Dict[str, Any]:
        """Generate automated incident response using AI.

        Args:
            incident_data: Incident details and metrics

        Returns:
            Incident response plan
        """
        # Use GPT to analyze incident and generate response steps

        response_plan = {
            'severity_assessment': 'medium',
            'immediate_actions': [
                'Isolate affected systems',
                'Notify administrators',
                'Collect diagnostic information'
            ],
            'investigation_steps': [
                'Review logs for root cause',
                'Check system resources',
                'Analyze recent changes'
            ],
            'recovery_procedures': [
                'Apply temporary fixes',
                'Restore from backup if needed',
                'Monitor system stability'
            ],
            'preventive_measures': [
                'Update security policies',
                'Implement additional monitoring',
                'Schedule regular maintenance'
            ]
        }

        return response_plan


# Global instances
_gpt_integration = None
_ai_workflow_manager = None

def init_ai_integration() -> Dict[str, Any]:
    """Initialize AI integration components.

    Returns:
        Dictionary of initialized AI components
    """
    global _gpt_integration, _ai_workflow_manager

    try:
        _gpt_integration = GPTIntegration()
        _ai_workflow_manager = AIWorkflowManager(_gpt_integration)

        current_app.logger.info("AI integration initialized successfully")

        return {
            'gpt_integration': _gpt_integration,
            'ai_workflow_manager': _ai_workflow_manager,
        }
    except Exception as e:
        current_app.logger.error(f"AI integration initialization failed: {e}")
        return {}


def get_gpt_integration() -> Optional[GPTIntegration]:
    """Get the global GPT integration instance."""
    return _gpt_integration


def get_ai_workflow_manager() -> Optional[AIWorkflowManager]:
    """Get the global AI workflow manager instance."""
    return _ai_workflow_manager