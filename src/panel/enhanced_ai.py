"""
Enhanced AI Integration with Multiple Providers
Advanced AI features including image analysis, predictive analytics, and content generation
"""

import os
import asyncio
import base64
from io import BytesIO
from typing import Dict, List, Optional, Any, Union
import logging
import json
from datetime import datetime, timedelta
from PIL import Image
import requests
from functools import wraps

logger = logging.getLogger(__name__)

class EnhancedAIAgent:
    """Enhanced AI agent with multiple capabilities and providers"""

    def __init__(self):
        self.providers = {}
        self._init_providers()
        self.cache = {}
        self.cache_expiry = {}

    def _init_providers(self):
        """Initialize available AI providers"""
        # Azure OpenAI (existing)
        if os.getenv('AZURE_OPENAI_API_KEY'):
            try:
                from src.panel.ai_integration import AzureOpenAIClient
                self.providers['azure'] = AzureOpenAIClient()
                logger.info("Azure OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI: {e}")

        # Google Vertex AI (new)
        if os.getenv('GOOGLE_CLOUD_PROJECT'):
            try:
                from src.panel.gcp_ai_integration import GCPAIAgent
                self.providers['gcp'] = GCPAIAgent()
                logger.info("Google Vertex AI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Vertex AI: {e}")

        # OpenAI API (direct)
        if os.getenv('OPENAI_API_KEY'):
            try:
                import openai
                self.providers['openai'] = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                logger.info("OpenAI API provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI API: {e}")

    async def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if still valid"""
        if cache_key in self.cache:
            if datetime.utcnow() < self.cache_expiry.get(cache_key, datetime.min):
                return self.cache[cache_key]
            else:
                # Clean up expired cache
                del self.cache[cache_key]
                del self.cache_expiry[cache_key]
        return None

    async def _cache_result(self, cache_key: str, result: Any, ttl_minutes: int = 30):
        """Cache result with TTL"""
        self.cache[cache_key] = result
        self.cache_expiry[cache_key] = datetime.utcnow() + timedelta(minutes=ttl_minutes)

    async def analyze_image(self, image_data: Union[str, bytes], content_type: str = "url") -> Dict[str, Any]:
        """Advanced image analysis with multiple AI providers"""
        try:
            cache_key = f"image_analysis_{hash(str(image_data))}"

            # Check cache first
            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            results = {}

            # Try GCP Vertex AI first (better for images)
            if 'gcp' in self.providers:
                try:
                    if content_type == "url":
                        result = await self.providers['gcp'].analyze_image(image_data)
                        results['gcp'] = result
                    elif content_type == "base64":
                        # Convert base64 to image for analysis
                        image_bytes = base64.b64decode(image_data)
                        # For now, use Azure for base64 (GCP needs URL)
                        pass
                except Exception as e:
                    logger.warning(f"GCP image analysis failed: {e}")

            # Fallback to Azure OpenAI
            if 'azure' in self.providers and not results:
                try:
                    # Azure OpenAI can analyze images via vision models
                    prompt = f"Analyze this image and provide: 1) Main subjects, 2) Content appropriateness, 3) Suggested tags, 4) Overall mood/tone\n\nImage: {image_data}"
                    analysis = await self.providers['azure'].generate_response(prompt)
                    results['azure'] = {
                        'analysis': analysis,
                        'moderated': self._check_content_safety(analysis),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                except Exception as e:
                    logger.warning(f"Azure image analysis failed: {e}")

            # Combine results
            final_result = self._combine_image_analysis(results)

            # Cache result
            await self._cache_result(cache_key, final_result, 60)  # Cache for 1 hour

            return final_result

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {
                'error': str(e),
                'moderated': True,  # Default to safe
                'timestamp': datetime.utcnow().isoformat()
            }

    async def predict_user_behavior(self, user_history: List[Dict], user_profile: Dict = None) -> Dict[str, Any]:
        """Predict user behavior and preferences using advanced analytics"""
        try:
            cache_key = f"user_prediction_{hash(str(user_history) + str(user_profile))}"

            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            # Prepare context
            context = {
                'history': user_history[-20:],  # Last 20 actions
                'profile': user_profile or {},
                'timestamp': datetime.utcnow().isoformat()
            }

            prompt = f"""Based on this user activity history and profile, predict:

1. User's gaming interests and preferences
2. Likely next actions (next 7 days)
3. Engagement level (high/medium/low) with confidence score
4. Recommended content/features to suggest
5. Risk of churn (low/medium/high) with reasoning
6. Suggested personalized notifications or features

User Profile: {json.dumps(context['profile'])}
Recent Activity: {json.dumps(context['history'], default=str)}

Provide analysis in JSON format with keys: interests, predictions, engagement, recommendations, churn_risk, notifications"""

            # Try different providers
            result_text = None

            if 'gcp' in self.providers:
                try:
                    result = await self.providers['gcp'].predict_user_behavior(user_history)
                    result_text = result.get('predictions', '')
                except Exception as e:
                    logger.warning(f"GCP behavior prediction failed: {e}")

            if not result_text and 'azure' in self.providers:
                try:
                    result_text = await self.providers['azure'].generate_response(prompt)
                except Exception as e:
                    logger.warning(f"Azure behavior prediction failed: {e}")

            # Parse and structure result
            prediction = self._parse_behavior_prediction(result_text or "Unable to generate prediction")

            # Cache for 24 hours
            await self._cache_result(cache_key, prediction, 1440)

            return prediction

        except Exception as e:
            logger.error(f"Behavior prediction failed: {e}")
            return {
                'interests': [],
                'predictions': [],
                'engagement': {'level': 'unknown', 'confidence': 0.0},
                'recommendations': [],
                'churn_risk': {'level': 'unknown', 'reasoning': 'Analysis failed'},
                'notifications': [],
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def generate_personalized_content(self, user_id: int, content_type: str, context: Dict = None) -> Dict[str, Any]:
        """Generate personalized content for users"""
        try:
            context = context or {}
            cache_key = f"personalized_content_{user_id}_{content_type}_{hash(str(context))}"

            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            prompt_templates = {
                'welcome_message': "Create a personalized welcome message for a new user based on their profile and interests.",
                'recommendation': "Suggest personalized gaming content, servers, or features based on user preferences.",
                'notification': "Create a personalized notification message about new features or content.",
                'tutorial': "Generate a personalized tutorial or guide based on user's skill level and interests.",
                'motivational': "Create a motivational message to encourage continued engagement."
            }

            base_prompt = prompt_templates.get(content_type, "Generate personalized content")
            full_prompt = f"{base_prompt}\n\nUser Context: {json.dumps(context, default=str)}"

            # Generate content
            content = None

            if 'azure' in self.providers:
                try:
                    content = await self.providers['azure'].generate_response(full_prompt)
                except Exception as e:
                    logger.warning(f"Azure content generation failed: {e}")

            if not content and 'gcp' in self.providers:
                try:
                    content = await self.providers['gcp'].generate_content(full_prompt, content_type)
                except Exception as e:
                    logger.warning(f"GCP content generation failed: {e}")

            result = {
                'content': content or "Personalized content is currently unavailable.",
                'type': content_type,
                'user_id': user_id,
                'context': context,
                'generated_at': datetime.utcnow().isoformat()
            }

            # Cache for 1 hour
            await self._cache_result(cache_key, result, 60)

            return result

        except Exception as e:
            logger.error(f"Personalized content generation failed: {e}")
            return {
                'content': "Personalized content is currently unavailable.",
                'type': content_type,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }

    async def analyze_trends(self, data: List[Dict], analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze trends in forum posts, user activity, or other data"""
        try:
            cache_key = f"trend_analysis_{analysis_type}_{hash(str(data))}"

            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            # Prepare data summary
            data_summary = self._summarize_data_for_analysis(data)

            prompt = f"""Analyze these {analysis_type} trends and provide insights:

Data Summary: {json.dumps(data_summary, default=str)}

Provide analysis including:
1. Key trends and patterns
2. Significant changes over time
3. Anomalies or unusual patterns
4. Predictions for future trends
5. Recommendations based on the analysis

Format as JSON with keys: trends, changes, anomalies, predictions, recommendations"""

            analysis_text = None

            if 'gcp' in self.providers:
                try:
                    result = await self.providers['gcp'].analyze_forum_trends(data)
                    analysis_text = json.dumps(result)
                except Exception as e:
                    logger.warning(f"GCP trend analysis failed: {e}")

            if not analysis_text and 'azure' in self.providers:
                try:
                    analysis_text = await self.providers['azure'].generate_response(prompt)
                except Exception as e:
                    logger.warning(f"Azure trend analysis failed: {e}")

            # Parse analysis
            analysis = self._parse_trend_analysis(analysis_text or "Unable to analyze trends")

            # Cache for 2 hours
            await self._cache_result(cache_key, analysis, 120)

            return analysis

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {
                'trends': [],
                'changes': [],
                'anomalies': [],
                'predictions': [],
                'recommendations': [],
                'error': str(e),
                'analyzed_at': datetime.utcnow().isoformat()
            }

    async def moderate_content_advanced(self, content: str, content_type: str = "text", metadata: Dict = None) -> Dict[str, Any]:
        """Advanced content moderation with context and metadata"""
        try:
            metadata = metadata or {}
            cache_key = f"advanced_moderation_{hash(content + str(metadata))}"

            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            # Use existing moderation but enhance with context
            base_moderation = await self._basic_moderation(content)

            # Add contextual analysis
            context_analysis = await self._analyze_content_context(content, content_type, metadata)

            # Combine results
            advanced_result = {
                **base_moderation,
                'context_analysis': context_analysis,
                'risk_score': self._calculate_risk_score(base_moderation, context_analysis),
                'moderated_at': datetime.utcnow().isoformat()
            }

            # Cache for 30 minutes
            await self._cache_result(cache_key, advanced_result, 30)

            return advanced_result

        except Exception as e:
            logger.error(f"Advanced moderation failed: {e}")
            return {
                'approved': True,
                'risk_score': 0.0,
                'error': str(e),
                'moderated_at': datetime.utcnow().isoformat()
            }

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for semantic search and similarity"""
        try:
            # This would use embedding models from various providers
            # For now, return placeholder embeddings
            embeddings = []

            for text in texts:
                # Generate simple hash-based embedding (placeholder)
                import hashlib
                hash_obj = hashlib.md5(text.encode())
                embedding = [int(hash_obj.hexdigest()[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
                embeddings.append(embedding[:16])  # 16-dimensional embedding

            return embeddings

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [[0.0] * 16 for _ in texts]

    async def detect_anomalies(self, data_points: List[Dict], baseline: Dict = None) -> Dict[str, Any]:
        """Detect anomalies in user behavior or system metrics"""
        try:
            cache_key = f"anomaly_detection_{hash(str(data_points) + str(baseline))}"

            cached = await self._get_cached_result(cache_key)
            if cached:
                return cached

            # Analyze data for anomalies
            prompt = f"""Analyze these data points for anomalies:

Data: {json.dumps(data_points, default=str)}
Baseline: {json.dumps(baseline or {}, default=str)}

Identify:
1. Statistical anomalies (unusual values)
2. Pattern anomalies (unusual sequences)
3. Contextual anomalies (unusual for this context)
4. Severity levels for each anomaly
5. Potential causes and recommendations

Format as JSON with keys: statistical_anomalies, pattern_anomalies, contextual_anomalies, severity_assessment, recommendations"""

            analysis_text = None

            if 'azure' in self.providers:
                try:
                    analysis_text = await self.providers['azure'].generate_response(prompt)
                except Exception as e:
                    logger.warning(f"Azure anomaly detection failed: {e}")

            anomalies = self._parse_anomaly_detection(analysis_text or "Unable to detect anomalies")

            # Cache for 15 minutes
            await self._cache_result(cache_key, anomalies, 15)

            return anomalies

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {
                'statistical_anomalies': [],
                'pattern_anomalies': [],
                'contextual_anomalies': [],
                'severity_assessment': {},
                'recommendations': [],
                'error': str(e),
                'detected_at': datetime.utcnow().isoformat()
            }

    # Helper methods
    async def _basic_moderation(self, content: str) -> Dict[str, Any]:
        """Basic content moderation using available providers"""
        if 'azure' in self.providers:
            return await self.providers['azure'].moderate_content(content)
        elif 'gcp' in self.providers:
            # GCP doesn't have direct moderation, use classification
            return {'approved': True, 'categories': {}, 'category_scores': {}}
        else:
            return {'approved': True, 'categories': {}, 'category_scores': {}}

    async def _analyze_content_context(self, content: str, content_type: str, metadata: Dict) -> Dict[str, Any]:
        """Analyze content in context"""
        context_prompt = f"""Analyze this {content_type} content in context:

Content: {content}
Metadata: {json.dumps(metadata, default=str)}

Assess:
1. Contextual appropriateness
2. Potential intent behind the content
3. Cultural sensitivity considerations
4. Age-appropriateness
5. Potential for misunderstanding

Provide contextual analysis."""

        try:
            if 'azure' in self.providers:
                analysis = await self.providers['azure'].generate_response(context_prompt)
                return {'analysis': analysis, 'risk_factors': []}
            else:
                return {'analysis': 'Context analysis unavailable', 'risk_factors': []}
        except Exception:
            return {'analysis': 'Context analysis failed', 'risk_factors': []}

    def _calculate_risk_score(self, base_moderation: Dict, context_analysis: Dict) -> float:
        """Calculate overall risk score"""
        base_score = 0.0

        # Base moderation score
        if not base_moderation.get('approved', True):
            base_score += 0.7

        # Category scores
        category_scores = base_moderation.get('category_scores', {})
        for category, score in category_scores.items():
            if score > 0.5:  # Threshold for concern
                base_score += score * 0.3

        return min(base_score, 1.0)  # Cap at 1.0

    def _check_content_safety(self, analysis: str) -> bool:
        """Check if content analysis indicates safety concerns"""
        unsafe_keywords = [
            'inappropriate', 'explicit', 'violent', 'harmful', 'offensive',
            'nsfw', 'adult', 'nudity', 'unsafe', 'dangerous'
        ]

        analysis_lower = analysis.lower()
        return not any(keyword in analysis_lower for keyword in unsafe_keywords)

    def _combine_image_analysis(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine results from multiple image analysis providers"""
        if not results:
            return {'error': 'No analysis results available'}

        # Use the most comprehensive result
        if 'gcp' in results:
            return results['gcp']
        elif 'azure' in results:
            return results['azure']
        else:
            return {'error': 'No valid analysis results'}

    def _parse_behavior_prediction(self, text: str) -> Dict[str, Any]:
        """Parse behavior prediction response"""
        try:
            # Try to parse as JSON first
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                'interests': [],
                'predictions': [text],
                'engagement': {'level': 'medium', 'confidence': 0.5},
                'recommendations': [],
                'churn_risk': {'level': 'medium', 'reasoning': 'Analysis inconclusive'},
                'notifications': []
            }

    def _summarize_data_for_analysis(self, data: List[Dict]) -> Dict[str, Any]:
        """Summarize data for AI analysis"""
        if not data:
            return {'count': 0, 'summary': 'No data available'}

        # Basic statistics
        summary = {
            'count': len(data),
            'date_range': {
                'start': min((item.get('created_at') for item in data if item.get('created_at')), default=None),
                'end': max((item.get('created_at') for item in data if item.get('created_at')), default=None)
            },
            'types': {},
            'metrics': {}
        }

        # Count by type/category
        for item in data:
            item_type = item.get('type', item.get('category', 'unknown'))
            summary['types'][item_type] = summary['types'].get(item_type, 0) + 1

        return summary

    def _parse_trend_analysis(self, text: str) -> Dict[str, Any]:
        """Parse trend analysis response"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                'trends': [text],
                'changes': [],
                'anomalies': [],
                'predictions': [],
                'recommendations': []
            }

    def _parse_anomaly_detection(self, text: str) -> Dict[str, Any]:
        """Parse anomaly detection response"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                'statistical_anomalies': [],
                'pattern_anomalies': [text],
                'contextual_anomalies': [],
                'severity_assessment': {},
                'recommendations': []
            }

# Global enhanced AI agent
enhanced_ai_agent = None

def init_enhanced_ai():
    """Initialize the enhanced AI agent"""
    global enhanced_ai_agent
    enhanced_ai_agent = EnhancedAIAgent()
    logger.info("Enhanced AI agent initialized")

def get_enhanced_ai_agent() -> Optional[EnhancedAIAgent]:
    """Get the enhanced AI agent instance"""
    return enhanced_ai_agent

# Enhanced AI features for the application
class ContentAnalyzer:
    """Advanced content analysis system"""

    def __init__(self):
        self.ai_agent = get_enhanced_ai_agent()

    async def analyze_image_upload(self, image_data: bytes, filename: str, user_id: int) -> Dict[str, Any]:
        """Analyze uploaded images for content and safety"""
        if not self.ai_agent:
            return {'approved': True, 'reason': 'AI analysis unavailable'}

        try:
            # Convert to base64 for analysis
            image_b64 = base64.b64encode(image_data).decode()

            analysis = await self.ai_agent.analyze_image(image_b64, "base64")

            return {
                'approved': analysis.get('moderated', True),
                'analysis': analysis.get('analysis', ''),
                'tags': analysis.get('tags', []),
                'filename': filename,
                'user_id': user_id,
                'analyzed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Image upload analysis failed: {e}")
            return {'approved': True, 'error': str(e)}

    async def analyze_user_content_patterns(self, user_id: int, content_history: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in user's content creation"""
        if not self.ai_agent:
            return {'patterns': [], 'insights': 'Analysis unavailable'}

        try:
            analysis = await self.ai_agent.analyze_trends(content_history, "user_content")

            return {
                'user_id': user_id,
                'patterns': analysis.get('trends', []),
                'insights': analysis.get('recommendations', []),
                'analyzed_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"User content pattern analysis failed: {e}")
            return {'patterns': [], 'insights': [], 'error': str(e)}

class UserBehaviorPredictor:
    """Predict user behavior and preferences"""

    def __init__(self):
        self.ai_agent = get_enhanced_ai_agent()

    async def predict_user_engagement(self, user_id: int, activity_history: List[Dict]) -> Dict[str, Any]:
        """Predict user engagement levels and next actions"""
        if not self.ai_agent:
            return {'engagement_level': 'unknown', 'predictions': []}

        try:
            prediction = await self.ai_agent.predict_user_behavior(activity_history)

            return {
                'user_id': user_id,
                'engagement_level': prediction.get('engagement', {}).get('level', 'unknown'),
                'confidence': prediction.get('engagement', {}).get('confidence', 0.0),
                'next_actions': prediction.get('predictions', []),
                'recommendations': prediction.get('recommendations', []),
                'churn_risk': prediction.get('churn_risk', {}),
                'predicted_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"User engagement prediction failed: {e}")
            return {'engagement_level': 'unknown', 'predictions': [], 'error': str(e)}

class PersonalizedContentGenerator:
    """Generate personalized content for users"""

    def __init__(self):
        self.ai_agent = get_enhanced_ai_agent()

    async def generate_welcome_message(self, user_profile: Dict) -> str:
        """Generate personalized welcome message"""
        if not self.ai_agent:
            return "Welcome to Panel! We're excited to have you here."

        try:
            result = await self.ai_agent.generate_personalized_content(
                user_profile.get('id', 0), 'welcome_message', user_profile
            )
            return result.get('content', "Welcome to Panel!")
        except Exception as e:
            logger.error(f"Welcome message generation failed: {e}")
            return "Welcome to Panel! We're excited to have you here."

    async def generate_recommendations(self, user_id: int, user_interests: List[str]) -> List[str]:
        """Generate personalized recommendations"""
        if not self.ai_agent:
            return ["Explore our gaming forums", "Check out server listings"]

        try:
            context = {'interests': user_interests}
            result = await self.ai_agent.generate_personalized_content(
                user_id, 'recommendation', context
            )

            # Parse recommendations from content
            content = result.get('content', '')
            recommendations = [line.strip('- ').strip() for line in content.split('\n') if line.strip()]
            return recommendations[:5]  # Limit to 5 recommendations
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Explore our gaming forums", "Check out server listings"]

class AnomalyDetector:
    """Detect anomalies in system metrics and user behavior"""

    def __init__(self):
        self.ai_agent = get_enhanced_ai_agent()

    async def detect_system_anomalies(self, metrics_data: List[Dict]) -> Dict[str, Any]:
        """Detect anomalies in system metrics"""
        if not self.ai_agent:
            return {'anomalies': [], 'severity': 'low'}

        try:
            # Calculate baseline from historical data
            baseline = self._calculate_baseline(metrics_data)

            anomalies = await self.ai_agent.detect_anomalies(metrics_data, baseline)

            return {
                'anomalies': anomalies,
                'severity': self._assess_severity(anomalies),
                'detected_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"System anomaly detection failed: {e}")
            return {'anomalies': [], 'severity': 'unknown', 'error': str(e)}

    def _calculate_baseline(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate baseline metrics"""
        if not data:
            return {}

        # Simple baseline calculation
        numeric_fields = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate']

        baseline = {}
        for field in numeric_fields:
            values = [item.get(field) for item in data if item.get(field) is not None]
            if values:
                baseline[field] = {
                    'mean': sum(values) / len(values),
                    'std_dev': (sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5
                }

        return baseline

    def _assess_severity(self, anomalies: Dict) -> str:
        """Assess overall severity of anomalies"""
        total_anomalies = (
            len(anomalies.get('statistical_anomalies', [])) +
            len(anomalies.get('pattern_anomalies', [])) +
            len(anomalies.get('contextual_anomalies', []))
        )

        if total_anomalies > 10:
            return 'critical'
        elif total_anomalies > 5:
            return 'high'
        elif total_anomalies > 2:
            return 'medium'
        elif total_anomalies > 0:
            return 'low'
        else:
            return 'none'

# Global instances
content_analyzer = None
behavior_predictor = None
content_generator = None
anomaly_detector = None

def init_advanced_ai_features():
    """Initialize all advanced AI features"""
    global content_analyzer, behavior_predictor, content_generator, anomaly_detector

    init_enhanced_ai()

    if get_enhanced_ai_agent():
        content_analyzer = ContentAnalyzer()
        behavior_predictor = UserBehaviorPredictor()
        content_generator = PersonalizedContentGenerator()
        anomaly_detector = AnomalyDetector()
        logger.info("Advanced AI features initialized")
    else:
        logger.warning("Advanced AI features not available - AI providers not configured")

def get_content_analyzer() -> Optional[ContentAnalyzer]:
    """Get the content analyzer instance"""
    return content_analyzer

def get_behavior_predictor() -> Optional[UserBehaviorPredictor]:
    """Get the behavior predictor instance"""
    return behavior_predictor

def get_content_generator() -> Optional[PersonalizedContentGenerator]:
    """Get the content generator instance"""
    return content_generator

def get_anomaly_detector() -> Optional[AnomalyDetector]:
    """Get the anomaly detector instance"""
    return anomaly_detector