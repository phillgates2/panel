# AI Integration with Azure OpenAI

This guide explains the AI-powered features integrated into the Panel application using Azure OpenAI Service, providing intelligent content moderation, user assistance, and analytics capabilities.

## Overview

The AI integration includes:
- **Content Moderation**: Automatic detection of inappropriate content
- **AI Assistant**: Intelligent chat support for users
- **Smart Tagging**: AI-powered tag suggestions for posts
- **Sentiment Analysis**: Analysis of user feedback and content
- **Content Summarization**: Automatic summarization of long content
- **Language Detection**: Automatic language identification

## Prerequisites

### Azure OpenAI Setup

1. **Azure Subscription**: Active Azure subscription
2. **OpenAI Resource**: Create Azure OpenAI resource in Azure portal
3. **Model Deployment**: Deploy GPT-4 and GPT-3.5-turbo models
4. **API Access**: Configure API keys and endpoints

### Configuration

Add to your environment variables:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
AZURE_OPENAI_DEPLOYMENT_GPT35=gpt-35-turbo
```

## AI Features

### Content Moderation

Automatically moderates forum posts and comments for inappropriate content.

#### Features
- **Real-time Moderation**: Checks content before publishing
- **Category Detection**: Identifies specific types of inappropriate content
- **Confidence Scoring**: Provides confidence levels for moderation decisions
- **Audit Logging**: Logs all moderation actions

#### Usage
```python
from src.panel.ai_integration import get_content_moderator

moderator = get_content_moderator()
result = await moderator.moderate_post("content here", user_id)

if not result['approved']:
    # Handle flagged content
    print(f"Content flagged: {result['reason']}")
```

#### API Endpoint
```bash
POST /api/ai/moderate
{
  "content": "text to moderate"
}
```

### AI Assistant

Provides intelligent responses to user queries and support requests.

#### Features
- **Context Awareness**: Maintains conversation history
- **Gaming Expertise**: Specialized knowledge of gaming and server management
- **Community Guidelines**: Follows platform rules and best practices
- **Multi-language Support**: Handles multiple languages

#### Usage
```python
from src.panel.ai_integration import get_ai_assistant

assistant = get_ai_assistant()
response = await assistant.get_response(user_id, "How do I configure my server?")
```

#### API Endpoint
```bash
POST /api/ai/assistant
{
  "message": "How do I reset my password?",
  "context": "user is having login issues"
}
```

### Smart Tag Suggestions

Automatically suggests relevant tags for forum posts and content.

#### Features
- **Content Analysis**: Analyzes post content for relevant topics
- **Gaming Focus**: Specialized in gaming and technology topics
- **Duplicate Prevention**: Avoids suggesting existing tags
- **Relevance Scoring**: Prioritizes most relevant tags

#### Usage
```python
from src.panel.ai_integration import get_ai_client

ai_client = get_ai_client()
tags = await ai_client.suggest_tags("My Minecraft server keeps crashing")
# Returns: ["minecraft", "server-crash", "technical-support"]
```

#### API Endpoint
```bash
POST /api/ai/suggest-tags
{
  "content": "forum post content",
  "existing_tags": ["existing", "tags"]
}
```

### Sentiment Analysis

Analyzes the sentiment and emotions in user feedback and content.

#### Features
- **Multi-dimensional Analysis**: Detects positive, negative, neutral sentiment
- **Emotion Detection**: Identifies specific emotions (joy, anger, frustration, etc.)
- **Confidence Scoring**: Provides confidence levels for analysis
- **Trend Tracking**: Monitors sentiment trends over time

#### Usage
```python
from src.panel.ai_integration import get_ai_client

ai_client = get_ai_client()
sentiment = await ai_client.analyze_sentiment("This feature is amazing!")
# Returns: {
#   "sentiment": "positive",
#   "confidence": 0.95,
#   "emotions": ["joy", "satisfaction"],
#   "explanation": "User expresses strong positive feelings"
# }
```

#### API Endpoint
```bash
POST /api/ai/analyze-sentiment
{
  "text": "text to analyze"
}
```

### Content Summarization

Automatically summarizes long content for previews and notifications.

#### Features
- **Length Control**: Configurable summary length
- **Key Point Extraction**: Focuses on most important information
- **Context Preservation**: Maintains original meaning
- **Language Agnostic**: Works with multiple languages

#### Usage
```python
from src.panel.ai_integration import get_ai_client

ai_client = get_ai_client()
summary = await ai_client.summarize_content(long_text, max_length=200)
```

#### API Endpoint
```bash
POST /api/ai/summarize
{
  "content": "long text to summarize",
  "max_length": 200
}
```

## Integration Examples

### Forum Post Creation with AI

```python
@app.route('/api/forum/posts', methods=['POST'])
@login_required
async def create_forum_post():
    data = request.get_json()
    content = data.get('content', '')

    # AI moderation
    moderator = get_content_moderator()
    if moderator:
        moderation = await moderator.moderate_post(content, current_user.id)
        if not moderation['approved']:
            return jsonify({'error': moderation['reason']}), 400

    # AI tag suggestions
    ai_client = get_ai_client()
    suggested_tags = []
    if ai_client:
        suggested_tags = await ai_client.suggest_tags(content)

    # Create post with AI enhancements
    post = ForumPost(
        content=content,
        ai_suggested_tags=suggested_tags,
        moderated=True
    )

    return jsonify({
        'post': post_data,
        'ai_suggested_tags': suggested_tags
    })
```

### User Support Chat

```python
@app.route('/api/support/chat', methods=['POST'])
@login_required
async def support_chat():
    data = request.get_json()
    message = data.get('message', '')

    assistant = get_ai_assistant()
    if assistant:
        response = await assistant.get_response(current_user.id, message)
        return jsonify({'response': response})

    return jsonify({'response': 'Support is currently unavailable.'})
```

### Content Analysis Dashboard

```python
@app.route('/api/admin/content-analysis')
@admin_required
async def content_analysis():
    # Get recent posts
    posts = ForumPost.query.limit(100).all()

    analyzer = get_content_analyzer()
    if analyzer:
        analysis = await analyzer.analyze_forum_trends([
            {'content': post.content} for post in posts
        ])

        return jsonify({
            'trends': analysis,
            'post_count': len(posts)
        })

    return jsonify({'error': 'Analysis not available'})
```

## Configuration

### Environment Variables

```bash
# Required for AI features
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4
AZURE_OPENAI_DEPLOYMENT_GPT35=gpt-35-turbo

# Optional: Rate limiting
AI_REQUESTS_PER_MINUTE=50
AI_TIMEOUT_SECONDS=30
```

### Feature Flags

```python
# In your configuration
AI_ENABLED=True
AI_MODERATION_ENABLED=True
AI_ASSISTANT_ENABLED=True
AI_TAG_SUGGESTIONS_ENABLED=True
AI_SENTIMENT_ANALYSIS_ENABLED=True
```

## Rate Limiting and Performance

### Built-in Protections

- **Rate Limiting**: 50 requests per minute per user
- **Timeout Handling**: 30-second timeout for AI requests
- **Fallback Behavior**: Graceful degradation when AI is unavailable
- **Caching**: Response caching for common queries

### Performance Optimization

```python
# Async processing for better performance
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_ai_request():
    with ThreadPoolExecutor() as executor:
        future = executor.submit(sync_ai_call)
        result = await asyncio.wrap_future(future)
    return result
```

## Monitoring and Analytics

### AI Usage Metrics

```python
@app.route('/api/admin/ai/stats')
@admin_required
def ai_stats():
    moderator = get_content_moderator()

    return jsonify({
        'moderation_stats': moderator.get_moderation_stats() if moderator else {},
        'ai_enabled': bool(get_ai_client()),
        'timestamp': datetime.utcnow().isoformat()
    })
```

### Logging

All AI interactions are logged for:
- **Usage Analytics**: Track feature adoption
- **Performance Monitoring**: Response times and success rates
- **Error Tracking**: Failed AI requests and reasons
- **Audit Trail**: Content moderation decisions

## Security Considerations

### Data Privacy
- **No Data Retention**: AI requests are not stored permanently
- **Anonymized Processing**: User data is anonymized for AI processing
- **Compliance**: GDPR and privacy regulation compliant

### Content Safety
- **Moderation Filters**: Multiple layers of content filtering
- **Human Oversight**: Admin review of moderation decisions
- **Appeal Process**: Users can appeal moderation decisions

### API Security
- **Authentication**: All AI endpoints require authentication
- **Rate Limiting**: Prevents abuse and ensures fair usage
- **Input Validation**: Sanitizes all input to AI services

## Cost Management

### Azure OpenAI Pricing

- **Pay-per-token**: Cost based on input/output tokens
- **Model Selection**: GPT-3.5-turbo for cost-effective responses
- **Caching**: Reduce API calls through intelligent caching
- **Usage Monitoring**: Track and optimize AI usage costs

### Cost Optimization Strategies

```python
# Use GPT-3.5 for routine tasks, GPT-4 for complex analysis
if complex_analysis_needed:
    model = ai_client.deployment_gpt4
else:
    model = ai_client.deployment_gpt35

# Cache common responses
@cache.memoize(timeout=3600)
async def get_cached_ai_response(query):
    return await ai_client.generate_response(query)
```

## Troubleshooting

### Common Issues

1. **AI Service Unavailable**
   ```python
   # Check if AI client is initialized
   if not get_ai_client():
       logger.warning("AI features disabled - check Azure OpenAI configuration")
   ```

2. **Rate Limiting**
   ```python
   # Implement exponential backoff
   import time
   time.sleep(2 ** attempt)  # Exponential backoff
   ```

3. **Timeout Errors**
   ```python
   # Reduce complexity or implement streaming
   response = await ai_client.generate_response(prompt, max_tokens=100)
   ```

### Debug Commands

```bash
# Test AI connectivity
python -c "
from src.panel.ai_integration import get_ai_client
client = get_ai_client()
if client:
    print('AI client initialized')
else:
    print('AI client not available')
"

# Test moderation
curl -X POST http://localhost:5000/api/ai/moderate \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "test content"}'
```

## Best Practices

### Implementation Guidelines

1. **Graceful Degradation**: Always provide fallback behavior
2. **User Consent**: Inform users about AI processing
3. **Transparency**: Be clear about AI-generated content
4. **Performance**: Optimize for speed and reliability
5. **Monitoring**: Track AI performance and user satisfaction

### Content Guidelines

1. **Moderation Standards**: Clear guidelines for content moderation
2. **Cultural Sensitivity**: Respect diverse cultures and languages
3. **Bias Mitigation**: Regular audits for bias in AI responses
4. **Quality Assurance**: Human review of AI decisions

### Maintenance

1. **Regular Updates**: Keep AI models and prompts updated
2. **Performance Monitoring**: Track response quality and speed
3. **User Feedback**: Collect feedback on AI features
4. **Cost Monitoring**: Track and optimize AI usage costs

This AI integration provides powerful intelligent features while maintaining security, performance, and user trust. The system is designed to enhance the user experience while providing administrators with valuable insights and automation capabilities.