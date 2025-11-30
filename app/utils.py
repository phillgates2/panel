import os
import pickle
import time
from typing import Optional

import redis
from cryptography.fernet import Fernet
from flask import current_app, request
from marshmallow import Schema, ValidationError, fields
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from transformers import pipeline

from config import config

# --- Simple rate limiting helpers (Redis-backed, with in-process fallback) ---
_rl_fallback_store = {}


def _get_redis_conn() -> Optional[redis.Redis]:
    try:
        redis_url = os.environ.get(
            "PANEL_REDIS_URL", getattr(config, "REDIS_URL", "redis://127.0.0.1:6379/0")
        )
        return redis.from_url(redis_url)
    except Exception:
        return None


def _client_ip() -> str:
    # basic client IP detection; behind proxies you could trust X-Forwarded-For
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"


def rate_limit(action: str, limit: int, window_seconds: int) -> bool:
    """Return True if request allowed, False if rate-limited.
    Skips when TESTING mode is enabled.

    Args:
        action: The action to rate limit.
        limit: Maximum requests allowed.
        window_seconds: Time window in seconds.

    Returns:
        True if allowed, False if limited.
    """
    if current_app.config.get("TESTING", False):
        return True
    ip = _client_ip()
    key = f"rl:{action}:{ip}"
    now = int(time.time())
    rconn = _get_redis_conn()
    if rconn is not None:
        try:
            count = rconn.incr(key)
            if count == 1:
                rconn.expire(key, window_seconds)
            return count <= limit
        except Exception:
            pass
    # Fallback in-process store
    bucket = _rl_fallback_store.get(key)
    if not bucket:
        bucket = {"start": now, "count": 0}
        _rl_fallback_store[key] = bucket
    # reset window if expired
    if now - bucket["start"] >= window_seconds:
        bucket["start"] = now
        bucket["count"] = 0
    bucket["count"] += 1
    return bucket["count"] <= limit


class UserSchema(Schema):
    first_name = fields.Str(required=True, validate=lambda x: len(x) > 0)
    last_name = fields.Str(required=True)
    email = fields.Email(required=True)


def validate_input(schema_class):
    def decorator(f):
        def wrapper(*args, **kwargs):
            data = request.get_json() or request.form.to_dict()
            schema = schema_class()
            try:
                validated_data = schema.load(data)
                request.validated_data = validated_data
            except ValidationError as err:
                return {"errors": err.messages}, 400
            return f(*args, **kwargs)

        wrapper.__name__ = f.__name__
        return wrapper

    return decorator


# Encryption key (store securely in production)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher = Fernet(ENCRYPTION_KEY.encode())


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(encrypted_data.encode()).decode()


# Load pre-trained spam detection model
spam_detector = pipeline(
    "text-classification", model="mrm8488/bert-tiny-finetuned-sms-spam-detection"
)

# Simple training data (in production, use a larger dataset)
spam_examples = [
    "Buy cheap viagra now",
    "Win lottery money free",
    "Casino gambling online",
    "Free money no deposit",
    "Spam message here",
]

ham_examples = [
    "Hello, how are you?",
    "Meeting at 3 PM",
    "Thanks for the help",
    "What's the weather like?",
    "Let's discuss the project",
]

# Train model if not exists
model_path = os.path.join(os.path.dirname(__file__), "spam_model.pkl")
vectorizer_path = os.path.join(os.path.dirname(__file__), "vectorizer.pkl")

if not os.path.exists(model_path):
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(spam_examples + ham_examples)
    y = [1] * len(spam_examples) + [0] * len(ham_examples)

    model = MultinomialNB()
    model.fit(X, y)

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)

# Load model
with open(model_path, "rb") as f:
    spam_model = pickle.load(f)
with open(vectorizer_path, "rb") as f:
    spam_vectorizer = pickle.load(f)


def is_spam(message):
    """Simple spam detection"""
    spam_keywords = ["spam", "viagra", "casino", "lottery", "free money"]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in spam_keywords)


def moderate_message(message):
    """Auto-moderate message using ML"""
    if is_spam_ml(message):
        return False  # Reject spam
    return True


def is_spam_ml(message):
    """Advanced ML-based spam detection using pre-trained BERT model"""
    try:
        result = spam_detector(message)
        # Assuming the model outputs 'LABEL_1' for spam
        return result[0]["label"] == "LABEL_1" and result[0]["score"] > 0.8
    except Exception as e:
        print(f"Spam detection error: {e}")
        return False


from transformers import pipeline

# Content moderation models
text_moderator = pipeline("text-classification", model="unitary/toxic-bert")
# image_moderator = pipeline("image-classification", model="microsoft/DiNAT-base")  # Placeholder


def moderate_content(text=None, image_path=None):
    """AI-powered content moderation"""
    if text:
        result = text_moderator(text)
        return result[0]["label"] == "toxic" and result[0]["score"] > 0.8
    if image_path:
        # Implement image moderation
        return False
    return False
