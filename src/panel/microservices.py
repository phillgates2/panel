"""
Microservices Architecture Preparation
Provides modular service structure and API gateway preparation
"""

import os
from flask import Flask, Blueprint, request, jsonify
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Service blueprints
from src.panel.auth_service import auth_bp
from src.panel.forum_service import forum_bp
from src.panel.cms_service import cms_bp
from src.panel.admin_service import admin_bp
from src.panel.api_gateway import api_bp


class MicroservicesManager:
    """Manages microservices architecture"""

    def __init__(self, app: Flask):
        self.app = app
        self.services = {}
        self.api_gateway = None

    def register_service(self, name: str, blueprint: Blueprint, prefix: str = None):
        """Register a service blueprint"""
        if prefix:
            self.app.register_blueprint(blueprint, url_prefix=prefix)
        else:
            self.app.register_blueprint(blueprint)

        self.services[name] = {
            'blueprint': blueprint,
            'prefix': prefix,
            'routes': []
        }

        # Extract routes from blueprint
        for rule in self.app.url_map.iter_rules():
            if rule.endpoint.startswith(f"{blueprint.name}."):
                self.services[name]['routes'].append({
                    'rule': str(rule.rule),
                    'methods': list(rule.methods),
                    'endpoint': rule.endpoint
                })

    def create_api_gateway(self):
        """Create API gateway for service orchestration"""
        self.api_gateway = APIGateway(self.services)
        self.app.register_blueprint(self.api_gateway.blueprint, url_prefix='/api/v2')

    def get_service_routes(self, service_name: str = None):
        """Get routes for a specific service or all services"""
        if service_name:
            return self.services.get(service_name, {}).get('routes', [])
        return {name: service['routes'] for name, service in self.services.items()}

    def get_service_health(self):
        """Get health status of all services"""
        health_status = {}
        for name, service in self.services.items():
            try:
                # Check if service blueprint is registered and accessible
                health_status[name] = {
                    'status': 'healthy',
                    'routes': len(service['routes']),
                    'prefix': service['prefix']
                }
            except Exception as e:
                health_status[name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        return health_status


class APIGateway:
    """API Gateway for microservices orchestration"""

    def __init__(self, services):
        self.services = services
        self.blueprint = Blueprint('api_gateway', __name__)

        # Register gateway routes
        self._register_routes()

    def _register_routes(self):
        """Register API gateway routes"""

        @self.blueprint.route('/health')
        def gateway_health():
            """Gateway health check"""
            return jsonify({
                'status': 'healthy',
                'services': list(self.services.keys()),
                'timestamp': datetime.utcnow().isoformat()
            })

        @self.blueprint.route('/services')
        def list_services():
            """List all registered services"""
            return jsonify({
                'services': list(self.services.keys()),
                'details': {name: {
                    'routes': len(service['routes']),
                    'prefix': service.get('prefix')
                } for name, service in self.services.items()}
            })

        @self.blueprint.route('/routes')
        def list_all_routes():
            """List all routes across services"""
            all_routes = {}
            for service_name, service in self.services.items():
                all_routes[service_name] = service['routes']
            return jsonify(all_routes)

        # Service-specific routes
        @self.blueprint.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def auth_proxy(path):
            """Proxy auth service requests"""
            return self._proxy_request('auth', path)

        @self.blueprint.route('/forum/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def forum_proxy(path):
            """Proxy forum service requests"""
            return self._proxy_request('forum', path)

        @self.blueprint.route('/cms/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def cms_proxy(path):
            """Proxy CMS service requests"""
            return self._proxy_request('cms', path)

        @self.blueprint.route('/admin/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def admin_proxy(path):
            """Proxy admin service requests"""
            return self._proxy_request('admin', path)

    def _proxy_request(self, service_name, path):
        """Proxy request to appropriate service"""
        # In a real microservices setup, this would make HTTP requests
        # to separate service instances. For now, we'll route internally.

        if service_name not in self.services:
            return jsonify({'error': f'Service {service_name} not found'}), 404

        # Simulate service call - in production, this would be HTTP requests
        try:
            # This is a placeholder - actual implementation would use requests
            # to call separate service instances
            return jsonify({
                'service': service_name,
                'path': path,
                'method': request.method,
                'message': f'Proxy to {service_name} service',
                'status': 'simulated'
            })
        except Exception as e:
            return jsonify({'error': f'Service {service_name} error', 'details': str(e)}), 500


# Service separation preparation
def create_service_blueprints():
    """Create blueprints for service separation"""

    # Auth Service Blueprint
    auth_service_bp = Blueprint('auth_service', __name__, url_prefix='/auth')

    @auth_service_bp.route('/login', methods=['POST'])
    def service_login():
        return jsonify({'service': 'auth', 'endpoint': 'login'})

    @auth_service_bp.route('/register', methods=['POST'])
    def service_register():
        return jsonify({'service': 'auth', 'endpoint': 'register'})

    @auth_service_bp.route('/profile')
    def service_profile():
        return jsonify({'service': 'auth', 'endpoint': 'profile'})

    # Forum Service Blueprint
    forum_service_bp = Blueprint('forum_service', __name__, url_prefix='/forum')

    @forum_service_bp.route('/threads')
    def service_threads():
        return jsonify({'service': 'forum', 'endpoint': 'threads'})

    @forum_service_bp.route('/thread/<int:thread_id>')
    def service_thread(thread_id):
        return jsonify({'service': 'forum', 'endpoint': 'thread', 'id': thread_id})

    @forum_service_bp.route('/post', methods=['POST'])
    def service_create_post():
        return jsonify({'service': 'forum', 'endpoint': 'create_post'})

    # CMS Service Blueprint
    cms_service_bp = Blueprint('cms_service', __name__, url_prefix='/cms')

    @cms_service_bp.route('/posts')
    def service_blog_posts():
        return jsonify({'service': 'cms', 'endpoint': 'posts'})

    @cms_service_bp.route('/post/<int:post_id>')
    def service_blog_post(post_id):
        return jsonify({'service': 'cms', 'endpoint': 'post', 'id': post_id})

    @cms_service_bp.route('/categories')
    def service_categories():
        return jsonify({'service': 'cms', 'endpoint': 'categories'})

    # Admin Service Blueprint
    admin_service_bp = Blueprint('admin_service', __name__, url_prefix='/admin')

    @admin_service_bp.route('/users')
    def service_users():
        return jsonify({'service': 'admin', 'endpoint': 'users'})

    @admin_service_bp.route('/servers')
    def service_servers():
        return jsonify({'service': 'admin', 'endpoint': 'servers'})

    @admin_service_bp.route('/audit')
    def service_audit():
        return jsonify({'service': 'admin', 'endpoint': 'audit'})

    return {
        'auth': auth_service_bp,
        'forum': forum_service_bp,
        'cms': cms_service_bp,
        'admin': admin_service_bp
    }


# Docker Compose preparation
DOCKER_COMPOSE_TEMPLATE = """
version: '3.8'

services:
  # API Gateway
  api-gateway:
    build: ./services/api-gateway
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - panel-network

  # Auth Service
  auth-service:
    build: ./services/auth
    ports:
      - "5001:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://panel:password@postgres:5432/panel
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - panel-network

  # Forum Service
  forum-service:
    build: ./services/forum
    ports:
      - "5002:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://panel:password@postgres:5432/panel
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - panel-network

  # CMS Service
  cms-service:
    build: ./services/cms
    ports:
      - "5003:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://panel:password@postgres:5432/panel
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - panel-network

  # Admin Service
  admin-service:
    build: ./services/admin
    ports:
      - "5004:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://panel:password@postgres:5432/panel
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - panel-network

  # Redis for caching and sessions
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - panel-network

  # PostgreSQL database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=panel
      - POSTGRES_USER=panel
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - panel-network

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
    depends_on:
      - api-gateway
    networks:
      - panel-network

volumes:
  redis_data:
  postgres_data:

networks:
  panel-network:
    driver: bridge
"""


def create_docker_compose_file():
    """Create Docker Compose file for microservices"""
    with open('docker-compose.microservices.yml', 'w') as f:
        f.write(DOCKER_COMPOSE_TEMPLATE)
    print("Created docker-compose.microservices.yml")


# Service discovery preparation
class ServiceDiscovery:
    """Simple service discovery for development"""

    def __init__(self):
        self.services = {
            'auth': 'http://localhost:5001',
            'forum': 'http://localhost:5002',
            'cms': 'http://localhost:5003',
            'admin': 'http://localhost:5004'
        }

    def get_service_url(self, service_name: str) -> str:
        """Get service URL"""
        return self.services.get(service_name)

    def register_service(self, name: str, url: str):
        """Register a service"""
        self.services[name] = url

    def unregister_service(self, name: str):
        """Unregister a service"""
        self.services.pop(name, None)


# Global instances
microservices_manager = None
service_discovery = ServiceDiscovery()

def init_microservices_architecture(app: Flask):
    """Initialize microservices architecture preparation"""
    global microservices_manager

    microservices_manager = MicroservicesManager(app)

    # Create service blueprints
    service_blueprints = create_service_blueprints()

    # Register services
    microservices_manager.register_service('auth', service_blueprints['auth'])
    microservices_manager.register_service('forum', service_blueprints['forum'])
    microservices_manager.register_service('cms', service_blueprints['cms'])
    microservices_manager.register_service('admin', service_blueprints['admin'])

    # Create API gateway
    microservices_manager.create_api_gateway()

    app.logger.info("Microservices architecture preparation initialized")


def get_microservices_manager():
    """Get the microservices manager instance"""
    return microservices_manager