"""
AI Extensions

This module initializes AI and machine learning related Flask extensions.
"""

from typing import Any, Dict

from flask import Flask

from src.panel.ai_chat import init_ai_chat
from src.panel.ai_integration import init_ai_features
from src.panel.custom_ai_training import init_model_trainer
from src.panel.enhanced_ai import init_advanced_ai_features
from src.panel.video_processing import init_video_processor
from src.panel.voice_analysis import init_voice_analyzer


def init_ai_extensions(app: Flask) -> Dict[str, Any]:
    """Initialize AI and machine learning related Flask extensions.

    Args:
        app: The Flask application instance.

    Returns:
        Dictionary of initialized AI extension instances.
    """
    # Initialize AI features
    init_ai_features()

    # Initialize advanced AI features
    init_advanced_ai_features()

    # Initialize AI chat functionality
    init_ai_chat()

    # Initialize voice analysis
    init_voice_analyzer()

    # Initialize video processing
    init_video_processor()

    # Initialize custom model training
    init_model_trainer()

    # Configure AI settings
    ai_config = {
        'ai_chat_enabled': True,
        'voice_analysis_enabled': True,
        'video_processing_enabled': True,
        'custom_training_enabled': True,
        'advanced_ai_features_enabled': True,
    }

    return {
        "ai_config": ai_config,
    }