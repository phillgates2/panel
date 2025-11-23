"""
Interactive API Documentation with Flask-RESTX
Provides Swagger/OpenAPI documentation and interactive API explorer
"""

from flask import Flask, Blueprint, request, jsonify
from flask_restx import Api, Resource, fields, Namespace
from werkzeug.exceptions import BadRequest, NotFound
import json
from datetime import datetime

# Create API blueprint
api_bp = Blueprint('api_docs', __name__, url_prefix='/api/v1')

# Initialize Flask-RESTX API
api = Api(
    api_bp,
    version='1.0',
    title='Panel API',
    description='Professional game server management and community platform API',
    doc='/docs',
    contact='Panel Team',
    contact_email='api@panel.local',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT'
)

# Namespaces for different API sections
auth_ns = api.namespace('auth', description='Authentication operations')
user_ns = api.namespace('users', description='User management')
forum_ns = api.namespace('forum', description='Forum operations')
admin_ns = api.namespace('admin', description='Administrative operations')
gdpr_ns = api.namespace('gdpr', description='GDPR compliance')
health_ns = api.namespace('health', description='System health')

# Data models for API documentation
user_model = api.model('User', {
    'id': fields.Integer(readonly=True, description='User unique identifier'),
    'email': fields.String(required=True, description='User email address'),
    'first_name': fields.String(required=True, description='User first name'),
    'last_name': fields.String(required=True, description='User last name'),
    'role': fields.String(enum=['user', 'moderator', 'admin'], description='User role'),
    'is_active': fields.Boolean(description='User account status'),
    'created_at': fields.DateTime(readonly=True, description='Account creation timestamp'),
    'last_login': fields.DateTime(readonly=True, description='Last login timestamp')
})

login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email'),
    'password': fields.String(required=True, description='User password'),
    'captcha': fields.String(description='CAPTCHA response')
})

register_model = api.model('Register', {
    'first_name': fields.String(required=True, description='First name'),
    'last_name': fields.String(required=True, description='Last name'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password'),
    'dob': fields.Date(description='Date of birth'),
    'captcha': fields.String(description='CAPTCHA response')
})

thread_model = api.model('ForumThread', {
    'id': fields.Integer(readonly=True, description='Thread ID'),
    'title': fields.String(required=True, description='Thread title'),
    'content': fields.String(required=True, description='Thread content'),
    'author_id': fields.Integer(readonly=True, description='Author user ID'),
    'is_pinned': fields.Boolean(description='Thread pinned status'),
    'is_locked': fields.Boolean(description='Thread locked status'),
    'created_at': fields.DateTime(readonly=True, description='Creation timestamp'),
    'updated_at': fields.DateTime(readonly=True, description='Last update timestamp')
})

post_model = api.model('ForumPost', {
    'id': fields.Integer(readonly=True, description='Post ID'),
    'thread_id': fields.Integer(required=True, description='Parent thread ID'),
    'content': fields.String(required=True, description='Post content'),
    'author_id': fields.Integer(readonly=True, description='Author user ID'),
    'created_at': fields.DateTime(readonly=True, description='Creation timestamp')
})

health_model = api.model('Health', {
    'status': fields.String(enum=['healthy', 'degraded', 'unhealthy'], description='System health status'),
    'timestamp': fields.DateTime(description='Health check timestamp'),
    'version': fields.String(description='API version'),
    'uptime': fields.String(description='System uptime'),
    'database': fields.String(description='Database status'),
    'cache': fields.String(description='Cache status')
})

gdpr_export_model = api.model('GDPRExport', {
    'user_id': fields.Integer(required=True, description='User ID for data export'),
    'include_sensitive': fields.Boolean(default=False, description='Include sensitive data'),
    'format': fields.String(enum=['json', 'csv'], default='json', description='Export format')
})

# Authentication endpoints
@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Login successful', user_model)
    @auth_ns.response(401, 'Invalid credentials')
    @auth_ns.response(429, 'Too many requests')
    def post(self):
        """Authenticate user and return session token"""
        data = request.get_json()

        # Validate input
        if not data or not data.get('email') or not data.get('password'):
            api.abort(400, 'Email and password are required')

        # Mock authentication (replace with actual logic)
        if data['email'] == 'admin@example.com' and data['password'] == 'admin123':
            return {
                'id': 1,
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_active': True,
                'token': 'mock_jwt_token'
            }

        api.abort(401, 'Invalid credentials')


@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.response(201, 'User registered successfully', user_model)
    @auth_ns.response(400, 'Validation error')
    @auth_ns.response(409, 'User already exists')
    def post(self):
        """Register a new user account"""
        data = request.get_json()

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                api.abort(400, f'{field} is required')

        # Mock user creation (replace with actual logic)
        return {
            'id': 2,
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'role': 'user',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }, 201


@auth_ns.route('/logout')
class Logout(Resource):
    @auth_ns.response(200, 'Logout successful')
    @auth_ns.response(401, 'Not authenticated')
    def post(self):
        """Logout current user"""
        # Mock logout (replace with actual session invalidation)
        return {'message': 'Logged out successfully'}


@auth_ns.route('/profile')
class Profile(Resource):
    @auth_ns.response(200, 'Profile retrieved', user_model)
    @auth_ns.response(401, 'Not authenticated')
    def get(self):
        """Get current user profile"""
        # Mock profile retrieval (replace with actual user lookup)
        return {
            'id': 1,
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin',
            'is_active': True,
            'last_login': datetime.utcnow().isoformat()
        }

    @auth_ns.expect(user_model)
    @auth_ns.response(200, 'Profile updated', user_model)
    @auth_ns.response(400, 'Validation error')
    @auth_ns.response(401, 'Not authenticated')
    def put(self):
        """Update current user profile"""
        data = request.get_json()

        # Mock profile update
        return {
            'id': 1,
            'email': data.get('email', 'admin@example.com'),
            'first_name': data.get('first_name', 'Admin'),
            'last_name': data.get('last_name', 'User'),
            'role': 'admin',
            'is_active': True,
            'last_login': datetime.utcnow().isoformat()
        }


# User management endpoints
@user_ns.route('/')
class UserList(Resource):
    @user_ns.response(200, 'Users retrieved', [user_model])
    @user_ns.response(401, 'Not authenticated')
    @user_ns.response(403, 'Insufficient permissions')
    def get(self):
        """Get list of users (admin only)"""
        # Mock user list (replace with actual database query)
        return [{
            'id': 1,
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin',
            'is_active': True,
            'created_at': '2023-01-01T00:00:00Z'
        }, {
            'id': 2,
            'email': 'user@example.com',
            'first_name': 'Regular',
            'last_name': 'User',
            'role': 'user',
            'is_active': True,
            'created_at': '2023-01-02T00:00:00Z'
        }]


@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @user_ns.response(200, 'User retrieved', user_model)
    @user_ns.response(404, 'User not found')
    @user_ns.response(401, 'Not authenticated')
    def get(self, user_id):
        """Get user details by ID"""
        # Mock user lookup
        if user_id == 1:
            return {
                'id': 1,
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_active': True,
                'created_at': '2023-01-01T00:00:00Z'
            }

        api.abort(404, 'User not found')

    @user_ns.expect(user_model)
    @user_ns.response(200, 'User updated', user_model)
    @user_ns.response(404, 'User not found')
    @user_ns.response(401, 'Not authenticated')
    @user_ns.response(403, 'Insufficient permissions')
    def put(self, user_id):
        """Update user details"""
        data = request.get_json()

        # Mock user update
        return {
            'id': user_id,
            'email': data.get('email', 'user@example.com'),
            'first_name': data.get('first_name', 'Updated'),
            'last_name': data.get('last_name', 'User'),
            'role': data.get('role', 'user'),
            'is_active': data.get('is_active', True)
        }

    @user_ns.response(204, 'User deleted')
    @user_ns.response(404, 'User not found')
    @user_ns.response(401, 'Not authenticated')
    @user_ns.response(403, 'Insufficient permissions')
    def delete(self, user_id):
        """Delete user account"""
        # Mock user deletion
        return '', 204


# Forum endpoints
@forum_ns.route('/threads')
class ThreadList(Resource):
    @forum_ns.response(200, 'Threads retrieved', [thread_model])
    def get(self):
        """Get list of forum threads"""
        # Mock thread list
        return [{
            'id': 1,
            'title': 'Welcome to the forum!',
            'content': 'Welcome message content...',
            'author_id': 1,
            'is_pinned': True,
            'is_locked': False,
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z'
        }, {
            'id': 2,
            'title': 'General discussion',
            'content': 'General discussion content...',
            'author_id': 2,
            'is_pinned': False,
            'is_locked': False,
            'created_at': '2023-01-02T00:00:00Z',
            'updated_at': '2023-01-02T00:00:00Z'
        }]

    @forum_ns.expect(thread_model)
    @forum_ns.response(201, 'Thread created', thread_model)
    @forum_ns.response(400, 'Validation error')
    @forum_ns.response(401, 'Not authenticated')
    def post(self):
        """Create a new forum thread"""
        data = request.get_json()

        if not data.get('title') or not data.get('content'):
            api.abort(400, 'Title and content are required')

        # Mock thread creation
        return {
            'id': 3,
            'title': data['title'],
            'content': data['content'],
            'author_id': 1,  # Mock current user
            'is_pinned': False,
            'is_locked': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }, 201


@forum_ns.route('/threads/<int:thread_id>')
class ThreadDetail(Resource):
    @forum_ns.response(200, 'Thread retrieved', thread_model)
    @forum_ns.response(404, 'Thread not found')
    def get(self, thread_id):
        """Get thread details"""
        # Mock thread lookup
        if thread_id == 1:
            return {
                'id': 1,
                'title': 'Welcome to the forum!',
                'content': 'Welcome message content...',
                'author_id': 1,
                'is_pinned': True,
                'is_locked': False,
                'created_at': '2023-01-01T00:00:00Z',
                'updated_at': '2023-01-01T00:00:00Z'
            }

        api.abort(404, 'Thread not found')

    @forum_ns.expect(thread_model)
    @forum_ns.response(200, 'Thread updated', thread_model)
    @forum_ns.response(404, 'Thread not found')
    @forum_ns.response(401, 'Not authenticated')
    @forum_ns.response(403, 'Insufficient permissions')
    def put(self, thread_id):
        """Update thread"""
        data = request.get_json()

        # Mock thread update
        return {
            'id': thread_id,
            'title': data.get('title', 'Updated Thread'),
            'content': data.get('content', 'Updated content...'),
            'author_id': 1,
            'is_pinned': data.get('is_pinned', False),
            'is_locked': data.get('is_locked', False),
            'updated_at': datetime.utcnow().isoformat()
        }

    @forum_ns.response(204, 'Thread deleted')
    @forum_ns.response(404, 'Thread not found')
    @forum_ns.response(401, 'Not authenticated')
    @forum_ns.response(403, 'Insufficient permissions')
    def delete(self, thread_id):
        """Delete thread"""
        # Mock thread deletion
        return '', 204


@forum_ns.route('/threads/<int:thread_id>/posts')
class PostList(Resource):
    @forum_ns.response(200, 'Posts retrieved', [post_model])
    @forum_ns.response(404, 'Thread not found')
    def get(self, thread_id):
        """Get posts in a thread"""
        # Mock posts
        return [{
            'id': 1,
            'thread_id': thread_id,
            'content': 'First post content...',
            'author_id': 1,
            'created_at': '2023-01-01T00:00:00Z'
        }, {
            'id': 2,
            'thread_id': thread_id,
            'content': 'Second post content...',
            'author_id': 2,
            'created_at': '2023-01-02T00:00:00Z'
        }]

    @forum_ns.expect(post_model)
    @forum_ns.response(201, 'Post created', post_model)
    @forum_ns.response(400, 'Validation error')
    @forum_ns.response(401, 'Not authenticated')
    @forum_ns.response(404, 'Thread not found')
    def post(self, thread_id):
        """Create a new post in thread"""
        data = request.get_json()

        if not data.get('content'):
            api.abort(400, 'Content is required')

        # Mock post creation
        return {
            'id': 3,
            'thread_id': thread_id,
            'content': data['content'],
            'author_id': 1,  # Mock current user
            'created_at': datetime.utcnow().isoformat()
        }, 201


# Admin endpoints
@admin_ns.route('/stats')
class AdminStats(Resource):
    @admin_ns.response(200, 'Statistics retrieved')
    @admin_ns.response(401, 'Not authenticated')
    @admin_ns.response(403, 'Insufficient permissions')
    def get(self):
        """Get system statistics"""
        return {
            'total_users': 150,
            'active_users': 45,
            'total_threads': 25,
            'total_posts': 340,
            'server_status': 'online',
            'uptime': '7 days, 4 hours',
            'last_backup': '2023-12-01T02:00:00Z'
        }


@admin_ns.route('/users/<int:user_id>/ban')
class UserBan(Resource):
    @admin_ns.response(200, 'User banned successfully')
    @admin_ns.response(404, 'User not found')
    @admin_ns.response(401, 'Not authenticated')
    @admin_ns.response(403, 'Insufficient permissions')
    def post(self, user_id):
        """Ban a user account"""
        # Mock user ban
        return {'message': f'User {user_id} has been banned'}


# GDPR endpoints
@gdpr_ns.route('/export')
class GDPRExport(Resource):
    @gdpr_ns.expect(gdpr_export_model)
    @gdpr_ns.response(200, 'Data export initiated')
    @gdpr_ns.response(400, 'Invalid request')
    @gdpr_ns.response(401, 'Not authenticated')
    @gdpr_ns.response(404, 'User not found')
    def post(self):
        """Request GDPR data export"""
        data = request.get_json()

        if not data.get('user_id'):
            api.abort(400, 'user_id is required')

        # Mock export request
        return {
            'message': 'Data export request submitted',
            'user_id': data['user_id'],
            'format': data.get('format', 'json'),
            'estimated_completion': '2023-12-15T10:00:00Z',
            'request_id': 'gdpr_export_12345'
        }


@gdpr_ns.route('/delete')
class GDPRDelete(Resource):
    @gdpr_ns.expect(api.model('GDPRDelete', {
        'user_id': fields.Integer(required=True, description='User ID to delete'),
        'confirmation': fields.String(required=True, description='Confirmation text')
    }))
    @gdpr_ns.response(200, 'Account deletion initiated')
    @gdpr_ns.response(400, 'Invalid confirmation')
    @gdpr_ns.response(401, 'Not authenticated')
    @gdpr_ns.response(404, 'User not found')
    def post(self):
        """Request GDPR account deletion"""
        data = request.get_json()

        if not data.get('user_id') or not data.get('confirmation'):
            api.abort(400, 'user_id and confirmation are required')

        # Mock deletion request
        return {
            'message': 'Account deletion request submitted',
            'user_id': data['user_id'],
            'estimated_completion': '2023-12-15T10:00:00Z',
            'request_id': 'gdpr_delete_12345'
        }


# Health check endpoints
@health_ns.route('/')
class HealthCheck(Resource):
    @health_ns.response(200, 'System healthy', health_model)
    def get(self):
        """Get system health status"""
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'uptime': '7 days, 4 hours',
            'database': 'connected',
            'cache': 'connected'
        }


@health_ns.route('/detailed')
class DetailedHealth(Resource):
    @health_ns.response(200, 'Detailed health information')
    def get(self):
        """Get detailed system health information"""
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': {'status': 'healthy', 'response_time': 45},
                'cache': {'status': 'healthy', 'response_time': 12},
                'email': {'status': 'healthy', 'response_time': 234},
                'storage': {'status': 'healthy', 'response_time': 67}
            },
            'metrics': {
                'active_users': 45,
                'total_users': 150,
                'requests_per_minute': 1250,
                'error_rate': 0.02
            },
            'system': {
                'cpu_usage': 45.2,
                'memory_usage': 62.8,
                'disk_usage': 34.1
            }
        }


# Custom error handlers
@api.errorhandler(BadRequest)
def handle_bad_request(error):
    """Handle bad request errors"""
    return {'message': 'Bad request', 'error': str(error)}, 400


@api.errorhandler(NotFound)
def handle_not_found(error):
    """Handle not found errors"""
    return {'message': 'Resource not found', 'error': str(error)}, 404


@api.errorhandler(Exception)
def handle_internal_error(error):
    """Handle internal server errors"""
    return {'message': 'Internal server error', 'error': str(error)}, 500


# API documentation customization
api.init_app(api_bp)

# Add custom CSS for API documentation
api_doc_css = """
.swagger-ui .topbar { display: none; }
.swagger-ui .info .title { color: #1f6feb; }
.swagger-ui .scheme-container { background: #f6f8fa; }
"""

# Override the default API documentation template
@api_bp.route('/docs')
def api_docs():
    """Serve custom API documentation"""
    return api.render_doc()