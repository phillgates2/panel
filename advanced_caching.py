"""Advanced Caching Implementation

Provides Redis-based caching for improved performance and scalability.
Includes response caching, query result caching, and cache invalidation.
"""

import json
import hashlib
from functools import wraps
from typing import Any, Optional, Callable

from flask import request, g
from flask_caching import Cache
import redis

from simple_config import load_config


class AdvancedCache:
    """Advanced caching system with Redis backend."""

    def __init__(self, app=None):
        self.app = app
        self.cache = None
        self.redis_client = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize cache with Flask app."""
        config = load_config()

        # Redis configuration
        redis_url = config.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': redis_url,
            'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
            'CACHE_KEY_PREFIX': 'panel_cache:',
        }

        self.cache = Cache(app, config=cache_config)

        # Direct Redis client for advanced operations
        self.redis_client = redis.from_url(redis_url)

        # Register with app
        app.advanced_cache = self

    def memoize(self, timeout: int = 300, key_prefix: str = None, unless: Callable = None):
        """Enhanced memoize decorator with custom key generation."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Skip caching if condition met
                if unless and unless():
                    return f(*args, **kwargs)

                # Generate cache key
                cache_key = self._make_cache_key(f, args, kwargs, key_prefix)

                # Try to get from cache
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Execute function and cache result
                result = f(*args, **kwargs)
                self.cache.set(cache_key, result, timeout=timeout)
                return result

            return decorated_function
        return decorator

    def _make_cache_key(self, f, args, kwargs, key_prefix=None):
        """Generate a unique cache key for the function call."""
        # Start with function name
        key_parts = [f.__name__]

        # Add key prefix if provided
        if key_prefix:
            key_parts.insert(0, key_prefix)

        # Add user ID if available (for user-specific caching)
        if hasattr(g, 'user') and g.user:
            key_parts.append(f"user_{g.user.id}")

        # Add relevant args/kwargs (skip 'self' for methods)
        start_idx = 1 if args and hasattr(args[0], f.__name__) else 0

        for arg in args[start_idx:]:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif hasattr(arg, 'id'):
                key_parts.append(f"id_{arg.id}")
            else:
                # Hash complex objects
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add sorted kwargs
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}_{v}")
            else:
                key_parts.append(f"{k}_{hashlib.md5(str(v).encode()).hexdigest()[:8]}")

        return ':'.join(key_parts)

    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching a pattern."""
        try:
            keys = self.redis_client.keys(f"panel_cache:{pattern}")
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidation error: {e}")

    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a specific user."""
        self.invalidate_pattern(f"user_{user_id}:*")

    def invalidate_server_cache(self, server_id: int):
        """Invalidate all cache entries for a specific server."""
        self.invalidate_pattern(f"*server_{server_id}*")

    def get_cache_info(self):
        """Get cache statistics and information."""
        try:
            info = self.redis_client.info()
            keys = len(self.redis_client.keys("panel_cache:*"))
            return {
                'total_keys': keys,
                'redis_info': {
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'uptime_days': info.get('uptime_in_days', 0),
                }
            }
        except Exception as e:
            return {'error': str(e)}


# Global cache instance
advanced_cache = AdvancedCache()


# ===== Cached Functions =====

@advanced_cache.memoize(timeout=300, key_prefix='servers')
def get_user_servers_cached(user_id: int):
    """Cached version of user servers query."""
    from app import db
    from models import Server, User

    user = db.session.get(User, user_id)
    if not user:
        return []

    return [{
        'id': s.id,
        'name': s.name,
        'status': s.status,
        'host': s.host,
        'port': s.port,
        'created_at': s.created_at.isoformat() if s.created_at else None
    } for s in user.servers]


@advanced_cache.memoize(timeout=60, key_prefix='server_details')
def get_server_details_cached(server_id: int):
    """Cached server details with metrics."""
    from app import db
    from models import Server

    server = db.session.get(Server, server_id)
    if not server:
        return None

    server_data = {
        'id': server.id,
        'name': server.name,
        'status': server.status,
        'host': server.host,
        'port': server.port,
        'created_at': server.created_at.isoformat() if server.created_at else None,
    }

    # Add latest metrics if available
    try:
        from monitoring_system import ServerMetrics
        latest_metric = ServerMetrics.query.filter_by(server_id=server.id)\
            .order_by(ServerMetrics.timestamp.desc()).first()
        if latest_metric:
            server_data['metrics'] = {
                'cpu_usage': latest_metric.cpu_usage,
                'memory_usage': latest_metric.memory_usage,
                'player_count': latest_metric.player_count,
                'timestamp': latest_metric.timestamp.isoformat()
            }
    except:
        pass

    return server_data


@advanced_cache.memoize(timeout=600, key_prefix='system_stats')
def get_system_stats_cached():
    """Cached system statistics."""
    from app import db
    from models import User, Server

    return {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_servers': Server.query.count(),
        'online_servers': Server.query.filter_by(status='online').count(),
    }


# ===== Cache Invalidation Helpers =====

def invalidate_user_servers_cache(user_id: int):
    """Invalidate cached server list for a user."""
    advanced_cache.invalidate_user_cache(user_id)
    advanced_cache.invalidate_pattern(f"servers:*user_{user_id}*")


def invalidate_server_details_cache(server_id: int):
    """Invalidate cached server details."""
    advanced_cache.invalidate_server_cache(server_id)
    advanced_cache.invalidate_pattern(f"server_details:*server_{server_id}*")


def invalidate_system_stats_cache():
    """Invalidate cached system statistics."""
    advanced_cache.invalidate_pattern("system_stats:*")


# ===== Response Caching =====

def cache_response(timeout: int = 300, key_prefix: str = None):
    """Decorator to cache API responses."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key from request
            cache_key = f"response:{request.method}:{request.path}"
            if request.args:
                cache_key += f"?{request.args.to_dict()}"

            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"

            # Try to get cached response
            cached_response = advanced_cache.cache.get(cache_key)
            if cached_response:
                return cached_response

            # Execute and cache response
            response = f(*args, **kwargs)

            # Only cache successful JSON responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                try:
                    # Cache the response data, not the Response object
                    response_data = response.get_json() if hasattr(response, 'get_json') else None
                    if response_data:
                        advanced_cache.cache.set(cache_key, response_data, timeout=timeout)
                except:
                    pass

            return response

        return decorated_function
    return decorator


# ===== Cache Management Routes =====

def init_cache_routes(app):
    """Initialize cache management routes."""
    from flask import Blueprint, jsonify, request
    from app import db

    cache_bp = Blueprint('cache', __name__, url_prefix='/api/cache')

    @cache_bp.route('/info')
    def cache_info():
        """Get cache information."""
        from flask import session
        from app import User

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(User, uid)
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        return jsonify(advanced_cache.get_cache_info())

    @cache_bp.route('/clear', methods=['POST'])
    def clear_cache():
        """Clear all cache."""
        from flask import session
        from app import User

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(User, uid)
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        try:
            advanced_cache.redis_client.flushdb()
            return jsonify({"message": "Cache cleared successfully"})
        except Exception as e:
            return jsonify({"error": f"Failed to clear cache: {str(e)}"}), 500

    @cache_bp.route('/invalidate/user/<int:user_id>', methods=['POST'])
    def invalidate_user(user_id):
        """Invalidate cache for specific user."""
        from flask import session
        from app import User

        uid = session.get("user_id")
        if not uid:
            return jsonify({"error": "Authentication required"}), 401

        user = db.session.get(User, uid)
        if not user or not user.is_system_admin():
            return jsonify({"error": "Admin access required"}), 403

        invalidate_user_servers_cache(user_id)
        return jsonify({"message": f"Cache invalidated for user {user_id}"})

    app.register_blueprint(cache_bp)


def init_advanced_caching(app):
    """Initialize advanced caching system."""
    advanced_cache.init_app(app)
    init_cache_routes(app)

    # Add cache headers to responses
    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/api/'):
            # Add cache control headers for API responses
            response.headers['Cache-Control'] = 'private, max-age=300'
        return response