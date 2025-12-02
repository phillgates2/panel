# Panel - Enterprise Game Server Management Platform

[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Code Quality](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0](https://img.shields.io/badge/flask-3.0-green.svg)](https://flask.palletsprojects.com/)

**A comprehensive, enterprise-grade web platform for game server management, community engagement, and real-time monitoring.**

Panel is a modern, scalable Flask application designed for managing game servers with advanced features like real-time monitoring, community forums, automated backups, and enterprise security. Built with production-ready architecture and extensive monitoring capabilities.

## ✨ Key Features

### 🎮 Game Server Management
- **Real-time Monitoring**: Live server status, player counts, and performance metrics
- **Automated Scaling**: Dynamic resource allocation based on player activity
- **Multi-Game Support**: ET:Legacy, Minecraft, and extensible for other games
- **RCON Integration**: Secure remote console access and command execution
- **Server Templates**: Pre-configured setups for quick deployment

### 👥 Community Platform
- **Integrated Forum**: Thread-based discussions with rich text support
- **Blog/CMS System**: News publishing with markdown and media uploads
- **User Management**: Role-based permissions (User, Moderator, Admin, System Admin)
- **Real-time Chat**: WebSocket-powered chat rooms with moderation
- **Achievement System**: Gamification with badges and progress tracking

### 🔒 Enterprise Security
- **OAuth2 Integration**: Google, GitHub, and custom providers
- **JWT Authentication**: Secure token-based API access
- **Role-Based Access Control**: Granular permissions system
- **GDPR Compliance**: Data export/deletion and privacy controls
- **Security Hardening**: CSP, HSTS, rate limiting, and input validation
- **Audit Logging**: Comprehensive activity tracking

### 📊 Monitoring & Analytics
- **Prometheus Metrics**: Real-time performance monitoring
- **Grafana Dashboards**: Visual analytics and alerting
- **Health Checks**: Automated system validation
- **Load Testing**: Built-in performance testing with Locust
- **Performance Profiling**: Bottleneck identification and optimization

### 🚀 Production Ready
- **Docker & Kubernetes**: Containerized deployment with Helm charts
- **Automated Backups**: S3 integration with encryption
- **Background Processing**: Celery/RQ for async tasks
- **Caching Layers**: Redis clustering with HTTP caching
- **SSL/TLS**: Let's Encrypt integration and custom certificates

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   API Gateway   │    │  Microservices  │
│   (Flask/Jinja) │◄──►│   (Flask-RESTX) │◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   Monitoring    │
│   (Primary DB)  │    │   (Cache/Queue) │    │ (Prometheus)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Backend**: Python 3.8+, Flask 3.0, SQLAlchemy, Redis
- **Frontend**: Bootstrap 5, JavaScript ES6+, WebSockets
- **Database**: PostgreSQL with connection pooling
- **Cache/Queue**: Redis with clustering support
- **Deployment**: Docker, Kubernetes, systemd
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **Security**: OAuth2, JWT, bcrypt, SSL/TLS

## 🚀 Quick Start

### One-Line Installation
```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/tools/scripts/install.sh | bash
```

### Docker Deployment
```bash
# Clone repository
git clone https://github.com/phillgates2/panel.git
cd panel

# Start with Docker Compose
docker-compose up -d

# Access at http://localhost:8080
```

### Manual Installation
```bash
# Clone and setup
git clone https://github.com/phillgates2/panel.git
cd panel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"

# Start application
python app.py
```

## 📖 Documentation

### 📚 Getting Started
- [Installation Guide](docs/INSTALLER_GUIDE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Deployment](docs/DEPLOYMENT.md)

### 🎯 User Guides
- [Server Management](docs/SERVER_MANAGEMENT.md)
- [Forum Usage](docs/FORUM_GUIDE.md)
- [Admin Panel](docs/ADMIN_GUIDE.md)

### 🔧 Developer Resources
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Testing](docs/TESTING.md)

### 🚀 Advanced Topics
- [Kubernetes Deployment](docs/KUBERNETES_DEPLOYMENT.md)
- [Monitoring Setup](docs/MONITORING.md)
- [Security Hardening](docs/SECURITY.md)
- [Performance Tuning](docs/PERFORMANCE.md)

## 🔧 Configuration

Panel uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/panel

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GITHUB_CLIENT_ID=your-github-client-id

# Monitoring (optional)
PROMETHEUS_ENABLED=true
GRAFANA_URL=http://localhost:3000
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install -r requirements/requirements-dev.txt

# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-e2e          # End-to-end tests

# Run with coverage
make test-coverage

# Load testing
make test-performance
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Install development dependencies**: `pip install -r requirements/requirements-dev.txt`
4. **Run tests**: `make test`
5. **Format code**: `make format`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Development Setup
```bash
# Clone and setup
git clone https://github.com/phillgates2/panel.git
cd panel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run development server
python app.py
```

### Code Quality
- **Linting**: `make lint` (ruff, flake8, bandit)
- **Formatting**: `make format` (black, isort)
- **Type Checking**: `make mypy`
- **Security**: `make security`

## 📊 Monitoring

Panel includes comprehensive monitoring capabilities:

### Health Checks
```bash
# Application health
curl http://localhost:8080/health

# Detailed health check
curl http://localhost:8080/health/detailed

# Run comprehensive health check
./panel-doctor.sh
```

### Metrics
- **Prometheus**: `/metrics` endpoint
- **Grafana**: Pre-built dashboards included
- **Custom Metrics**: Application-specific monitoring

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log rotation and cleanup

## 🔒 Security

Panel implements enterprise-grade security measures:

### Authentication & Authorization
- JWT tokens with configurable expiration
- OAuth2 social login integration
- Multi-factor authentication support
- Session management with secure cookies

### Data Protection
- Password hashing with bcrypt
- Sensitive data encryption
- GDPR compliance features
- Audit logging for all actions

### Network Security
- HTTPS enforcement with HSTS
- Content Security Policy (CSP)
- Rate limiting and DDoS protection
- Input validation and sanitization

## 🚀 Deployment

### Production Deployment Options

#### Docker Compose (Recommended)
```bash
# Production setup
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

#### Kubernetes
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# With Helm
helm install panel ./helm
```

#### Traditional Server
```bash
# Automated installation
PANEL_DOMAIN=yourdomain.com PANEL_ENABLE_SSL=true \
bash tools/scripts/install.sh

# Manual systemd setup
sudo cp deploy/panel.service /etc/systemd/system/
sudo systemctl enable panel
sudo systemctl start panel
```

### Environment Variables
```bash
# Production settings
export FLASK_ENV=production
export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="postgresql://user:pass@db:5432/panel"
export REDIS_URL="redis://redis:6379/0"

# SSL Configuration
export SSL_CERT_PATH="/etc/ssl/certs/panel.crt"
export SSL_KEY_PATH="/etc/ssl/private/panel.key"

# Monitoring
export PROMETHEUS_ENABLED=true
export GRAFANA_URL="http://monitoring:3000"
```

## 📈 Performance

Panel is optimized for high performance:

### Caching Strategy
- **Multi-level Caching**: Memory → Redis → Database
- **HTTP Caching**: ETags, Cache-Control headers
- **Template Caching**: Jinja2 template optimization

### Database Optimization
- **Connection Pooling**: SQLAlchemy with optimized pools
- **Query Optimization**: N+1 query prevention
- **Indexing**: Strategic database indexes
- **Read Replicas**: Support for database scaling

### Background Processing
- **Task Queues**: RQ and Celery for async tasks
- **Job Scheduling**: Cron-based automated tasks
- **Resource Management**: Worker process optimization

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check database status
sudo systemctl status postgresql

# Test connection
psql -U panel_user -d panel -h localhost

# Reset database
make db-init
```

#### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Restart Redis
sudo systemctl restart redis
```

#### Permission Errors
```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/panel

# Fix permissions
chmod 755 /opt/panel
chmod 644 /opt/panel/.env
```

#### SSL Certificate Problems
```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Check certificate validity
openssl x509 -in /etc/ssl/certs/panel.crt -text -noout
```

### Debug Mode
```bash
# Enable debug logging
export FLASK_ENV=development
export LOG_LEVEL=DEBUG

# Run with debug mode
python app.py
```

### Health Check Script
```bash
# Run comprehensive health check
./panel-doctor.sh all

# Check specific components
./panel-doctor.sh --database
./panel-doctor.sh --redis
./panel-doctor.sh --nginx
```

## 📞 Support

### Community Support
- **GitHub Issues**: [Report bugs and request features](https://github.com/phillgates2/panel/issues)
- **Discussions**: [Community forum](https://github.com/phillgates2/panel/discussions)
- **Documentation**: [Full docs](docs/README.md)

### Professional Support
- **Enterprise Support**: Contact for commercial licensing
- **Consulting**: Custom development and deployment services
- **Training**: Team training and onboarding

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flask Community**: For the excellent web framework
- **SQLAlchemy Team**: For the powerful ORM
- **Redis Community**: For the high-performance data structure store
- **Open Source Contributors**: For their valuable contributions

## 🎯 Roadmap

### Upcoming Features
- [ ] Mobile application (React Native)
- [ ] Advanced AI features (GPT integration)
- [ ] Multi-tenant architecture
- [ ] Real-time notifications (WebSockets)
- [ ] Advanced analytics dashboard
- [ ] Plugin system for extensibility
- [ ] Multi-language support (i18n)
- [ ] API rate limiting per user
- [ ] Automated scaling policies
- [ ] Backup encryption and compression

### Version History
See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

**Panel** — Modern, secure, and scalable game server management platform.

[🚀 Get Started](docs/INSTALLER_GUIDE.md) • [📖 Documentation](docs/README.md) • [🐛 Report Issues](https://github.com/phillgates2/panel/issues) • [💬 Community](https://github.com/phillgates2/panel/discussions)
