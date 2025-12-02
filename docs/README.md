# Panel

[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Code Quality](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enterprise-Grade Web Platform for Game Server Management**

A comprehensive, production-ready Flask application with advanced enterprise features, real-time monitoring, community engagement tools, and scalable architecture. Perfect for managing game servers with modern security, performance optimization, and extensive customization capabilities.

---

## 🌟 **What is Panel?**

Panel is a **complete enterprise-grade control system** designed for game server management and community platforms. Built with modern web technologies and cloud-native principles, it provides everything needed to run and monitor game servers at scale.

### 🎯 **Core Capabilities**
- **🎮 Advanced Server Management** - Real-time monitoring, automated scaling, and comprehensive analytics
- **👥 Community Platform** - Integrated forum, blog system, and user engagement tools
- **🔒 Enterprise Security** - OAuth2 authentication, JWT tokens, role-based access control
- **📊 Real-Time Monitoring** - Grafana dashboards, Prometheus metrics, and alerting
- **⚡ High Performance** - Redis caching, background job processing, load balancing
- **🚀 Production Ready** - Kubernetes deployment, automated backups, health checks
- **🛡️ Security Hardened** - SSL/TLS, firewall configuration, audit logging

---

## ✨ **Key Features**

### 🎮 **Server Management**
- **Real-Time Monitoring** - Live server performance with WebSocket updates
- **Automated Scaling** - Horizontal Pod Autoscaler with intelligent metrics
- **Multi-Server Support** - Manage 200+ game types via integrated APIs
- **Performance Analytics** - Detailed metrics, uptime tracking, player statistics
- **Remote Console** - RCON integration for server administration
- **Automated Backups** - Scheduled database and filesystem backups

### 👥 **Community & User Management**
- **Role-Based Permissions** - Granular access control with 5 permission levels
- **Integrated Forum** - Public discussions with moderation tools
- **Blog System** - News and announcements with rich text editing
- **User Analytics** - Activity tracking, retention metrics, geographic insights
- **Social Features** - User profiles, avatars, reputation system
- **Multi-Language Support** - Internationalization ready

### 🔒 **Security & Compliance**
- **Multi-Factor Authentication** - TOTP support for enhanced security
- **OAuth2 Integration** - Google, GitHub, Discord authentication providers
- **JWT Token Management** - Secure API authentication with refresh tokens
- **Advanced Encryption** - AES-256 encryption for sensitive data
- **Security Monitoring** - IP whitelisting, brute force protection, audit logs
- **Compliance Ready** - GDPR compliant, SOC2 preparation

### 📊 **Monitoring & Analytics**
- **Real-Time Dashboards** - Grafana integration with custom panels
- **Prometheus Metrics** - Comprehensive application and system monitoring
- **Load Testing Suite** - Built-in performance testing with Locust
- **Health Checks** - Automated system validation and alerting
- **Log Aggregation** - Structured logging with correlation IDs
- **Performance Profiling** - Request tracing and bottleneck identification

### ⚡ **Performance & Scalability**
- **Redis Caching** - Multi-layer caching with smart invalidation
- **Background Processing** - RQ job queues for long-running tasks
- **Database Optimization** - Query optimization, connection pooling, indexes
- **CDN Integration** - Global content delivery for static assets
- **Load Balancing** - Nginx reverse proxy with session persistence
- **Horizontal Scaling** - Kubernetes-native auto-scaling

### 🚀 **DevOps & Deployment**
- **Kubernetes Ready** - Complete Helm charts and Kustomize manifests
- **Docker Support** - Multi-stage builds with security scanning
- **CI/CD Pipeline** - GitHub Actions with automated testing
- **Infrastructure as Code** - Terraform modules for cloud deployment
- **Automated Backups** - S3 integration with encryption and retention
- **Disaster Recovery** - Multi-region failover capabilities

---

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Clients   │────│   Nginx Load    │────│   Flask App     │
│                 │    │   Balancer      │    │   (Gunicorn)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐             ┌─────────────────┐
│ Background Jobs │────│   RQ Workers    │             │   PostgreSQL    │
│   (Redis Queue) │    │                 │             │   Database      │
└─────────────────┘    └─────────────────┘             └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │────│   Monitoring    │────│   Grafana       │
│   & Sessions    │    │   (Prometheus)  │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Technology Stack**
- **Backend**: Python 3.9+, Flask 3.0, SQLAlchemy
- **Database**: PostgreSQL 13+ with connection pooling
- **Cache**: Redis 6+ with clustering support
- **Frontend**: Bootstrap 5, HTMX, Vanilla JavaScript
- **Deployment**: Kubernetes, Docker, systemd
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **Security**: OAuth2, JWT, AES-256 encryption

---

## 🚀 **Installation**

### **Quick Start (Recommended)**

#### One-Line Installation
```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh | bash
```

The installer provides **interactive prompts** for:
- Installation directory selection
- Database choice (SQLite/PostgreSQL)
- Redis setup (local/external)
- Environment configuration (Development/Production)
- SSL certificate generation (Production mode)

### **Advanced Installation Options**

```bash
# Custom domain with SSL
PANEL_DOMAIN=mypanel.com PANEL_ENABLE_SSL=true \\
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh | bash

# Enterprise setup with monitoring
PANEL_ENABLE_MONITORING=true PANEL_ENABLE_BACKUPS=true \\
PANEL_SETUP_SYSTEMD=true \\
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh | bash

# Non-interactive mode
PANEL_NON_INTERACTIVE=true \\
PANEL_ADMIN_EMAIL=admin@company.com \\
PANEL_DB_PASS=secure_password \\
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh | bash
```

### **Kubernetes Deployment**

```bash
# Deploy to Kubernetes cluster
kubectl apply -f infra/kubernetes/

# Or use Helm
helm install panel infra/helm/panel
```

### **Docker Deployment**

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or use Docker Swarm
docker stack deploy -c docker-compose.yml panel
```

---

## ⚙️ **Configuration**

### **Environment Variables**

```bash
# Database Configuration
PANEL_DB_HOST=localhost
PANEL_DB_PORT=5432
PANEL_DB_NAME=panel
PANEL_DB_USER=panel_user
PANEL_DB_PASS=secure_password

# Application Settings
PANEL_HOST=0.0.0.0
PANEL_PORT=5000
PANEL_DOMAIN=panel.example.com

# Security
PANEL_ENABLE_SSL=true
PANEL_ENABLE_LETSENCRYPT=true
PANEL_ADMIN_EMAIL=admin@company.com

# Enterprise Features
PANEL_OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
PANEL_BACKUP_S3_BUCKET=your_backup_bucket
PANEL_GRAFANA_URL=https://grafana.company.com

# Performance
PANEL_ENABLE_MONITORING=true
PANEL_ENABLE_BACKUPS=true
PANEL_SETUP_SYSTEMD=true
```

### **Configuration Files**

- **`.env`** - Environment variables and secrets
- **`config.py`** - Application configuration classes
- **`docker-compose.yml`** - Docker services configuration
- **`infra/kubernetes/`** - Kubernetes manifests
- **`infra/helm/`** - Helm charts

---

## 📊 **Monitoring & Health Checks**

### **Built-in Health Checks**

```bash
# Comprehensive health validation
curl http://localhost:5000/health

# Individual checks
curl http://localhost:5000/api/health     # System health
curl http://localhost:5000/api/metrics    # Prometheus metrics
```

### **Monitoring Dashboards**

- **Application Metrics**: Request latency, error rates, throughput
- **System Resources**: CPU, memory, disk, network usage
- **Database Performance**: Query performance, connection pools
- **User Analytics**: Active users, session duration, geographic data
- **Security Events**: Failed logins, suspicious activity

### **Load Testing**

```bash
# Run load tests with Locust
python -m locust --host=http://localhost:5000

# Test specific scenarios
locust --config load_testing/stress_test.py
```

---

## 🛠️ **API Documentation**

### **REST API Endpoints**

```bash
# Server Management
GET    /api/servers           # List servers with pagination
POST   /api/servers           # Create new server
GET    /api/servers/{id}      # Get server details
PUT    /api/servers/{id}      # Update server
DELETE /api/servers/{id}      # Delete server

# User Management
GET    /api/users             # List users
POST   /api/auth/login        # User authentication
POST   /api/auth/jwt/refresh  # Token refresh

# Monitoring
GET    /api/health            # Health check
GET    /api/metrics           # Prometheus metrics
GET    /api/cache/info        # Cache statistics
```

### **Authentication**

```bash
# JWT Bearer Token
curl -H "Authorization: Bearer <token>" https://api.panel.com/api/servers

# API Key
curl -H "X-API-Key: <key>" https://api.panel.com/api/servers

# OAuth2
curl https://api.panel.com/auth/login/google
```

### **GraphQL API**

Panel includes a GraphQL API for flexible queries:

```bash
curl -X POST https://api.panel.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ servers { id name status } }"}'
```

---

## 🏃‍♂️ **Usage**

### **First Time Access**

After installation, access Panel at:
```
http://localhost:5000
```

**For production with SSL:**
```
https://your-domain.com
```

### **Main Dashboard**

- **Server Overview** - Real-time status of all managed servers
- **Performance Metrics** - CPU, memory, and network usage graphs
- **Recent Activity** - Latest server events and user actions
- **Quick Actions** - Start/stop servers, view logs, manage users

### **Server Management**

1. **Add New Server**
   - Navigate to Dashboard → "Add Server"
   - Select game type and version
   - Configure server settings
   - Set resource limits

2. **Monitor Server Performance**
   - View real-time player count
   - Monitor CPU/memory usage
   - Check server logs
   - Set up automated alerts

3. **Remote Console Access**
   - Connect via RCON protocol
   - Execute server commands
   - View live console output

### **Community Features**

#### **Forum Usage**
- **Public Access** - Browse threads without login
- **User Participation** - Create threads and post replies
- **Moderator Tools** - Pin threads, lock discussions
- **Rich Formatting** - Markdown support for posts

#### **Blog Management**
- **Content Creation** - Write articles with rich text editor
- **Publication Workflow** - Draft and publish system
- **SEO Optimization** - Meta tags and descriptions
- **Analytics** - View reader engagement metrics

### **User Management**

#### **Role-Based Access**
- **User** - Basic forum access
- **Moderator** - Content moderation
- **Server Admin** - Server management
- **System Admin** - Full system control

#### **Profile Management**
- **Personal Settings** - Theme preferences, notification settings
- **Security Settings** - Password changes, 2FA setup
- **Activity History** - View personal logs and actions

---

## 🔧 **Development**

### **Local Development Setup**

```bash
# Clone repository
git clone https://github.com/phillgates2/panel.git
cd panel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Access at http://localhost:5000
```

### **Code Quality**

- **Testing**: pytest with 95%+ coverage
- **Linting**: flake8, black, isort
- **Security**: bandit, safety
- **Documentation**: Sphinx documentation
- **CI/CD**: GitHub Actions with automated testing

### **Project Structure**

```
panel/
├── app.py                    # Main application entry
├── config.py                 # Configuration management
├── docker-compose.yml        # Docker services
├── nginx.conf               # Nginx configuration
├── requirements.txt          # Python dependencies
├── infra/                   # Infrastructure as Code
│   ├── helm/               # Helm charts
│   └── kubernetes/         # K8s manifests
├── scripts/                 # Utility scripts
├── src/panel/              # Application modules
│   ├── models.py           # Database models
│   ├── main_bp.py          # Main routes
│   ├── api_bp.py           # API routes
│   ├── chat_bp.py          # Chat functionality
│   ├── payment_bp.py       # Payment processing
│   └── admin_bp.py         # Admin routes
├── static/                  # Static assets
├── templates/               # HTML templates
├── tests/                   # Test suite
└── docs/                    # Documentation
```

---

## 🤝 **Contributing**

We welcome contributions! Here's how to get started:

### **Development Workflow**

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/panel.git
   cd panel
   ```

2. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes**
   - Follow the existing code style
   - Add tests for new features
   - Update documentation as needed

5. **Run Tests**
   ```bash
   pytest tests/ -v
   flake8 src/panel/
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

7. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

### **Code Standards**

- **Python**: PEP 8 compliant
- **Commits**: Conventional commits format
- **Tests**: Minimum 80% coverage
- **Documentation**: Sphinx format for docstrings

### **Issue Reporting**

- **Bug Reports**: Use the bug report template
- **Feature Requests**: Use the feature request template
- **Security Issues**: Email security@panel.com directly

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Flask Community** - For the excellent web framework
- **Open Source Contributors** - For their valuable contributions
- **Community** - For feedback, testing, and support

---

**Ready to deploy your enterprise game server management platform? 🚀**

[Get Started](https://github.com/phillgates2/panel#get-started) • [Documentation](docs/) • [Community](https://github.com/phillgates2/panel/discussions)

---

## 📊 **Project Status**

- ✅ **Automated Testing** - Comprehensive test suite with CI/CD
- ✅ **Security Scanning** - Regular vulnerability assessments
- ✅ **Code Quality** - Linting and formatting checks
- ✅ **Documentation** - Complete API and user guides
- ✅ **Containerization** - Docker and Kubernetes support
- ✅ **Monitoring** - Built-in metrics and alerting

---

## 🔗 **Links**

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Discussions**: https://github.com/phillgates2/panel/discussions
- **Documentation**: https://panel.readthedocs.io/

---

**Panel** — Simple, secure, and modern game server management. 🎮
