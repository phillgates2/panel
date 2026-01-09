<div align="center">

# 🎮 Panel

### Enterprise Game Server Management Platform

[![CI/CD](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/ci-cd.yml)
[![Code Quality](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/code-quality.yml)
[![Security](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml/badge.svg)](https://github.com/phillgates2/panel/actions/workflows/security-monitoring.yml)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0](https://img.shields.io/badge/flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![Release](https://img.shields.io/github/v/release/phillgates2/panel)](https://github.com/phillgates2/panel/releases)
[![codecov](https://codecov.io/gh/phillgates2/panel/branch/main/graph/badge.svg)](https://codecov.io/gh/phillgates2/panel)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**A production-ready, cloud-native platform for managing game servers with enterprise features including real-time monitoring, community engagement, automated operations, and AI-powered insights.**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🌟 Overview

Panel is a comprehensive Flask-based web application designed for professional game server management at scale. Built with modern DevOps practices, it provides a complete ecosystem for hosting, monitoring, and managing multiplayer game servers with integrated community features.

### Highlights

- 🚀 Production-ready architecture with Docker and multi-cloud docs
- 📊 Full observability: Prometheus, Grafana, structured logging
- 🔒 Enterprise security: OAuth2, JWT, RBAC, GDPR tools
- ⚡ High performance: Redis caching, connection pooling, async tasks
- 🤖 AI integrations available for automation and insights

---

## ✨ Features

### 🎮 Game Server Management
- Multi-game support (ET:Legacy, Minecraft; extensible)
- RCON integration for remote console access
- Pterodactyl egg tooling and server provisioning helpers
- Server templates for quick deployment
- Health monitoring and recovery scripts
- Player and admin management controls

### 👥 Community Platform
- Forum/CMS system with moderation workflows
- Real-time chat via WebSockets
- User profiles, roles, and achievements
- Optional payment/donation integrations

### 📊 Monitoring & Analytics
- Prometheus metrics (`/metrics`) with custom application metrics
- Grafana dashboards and alerting integration
- Health check endpoints and diagnostic scripts
- Load testing via included guides and tooling

### 🔒 Security & Compliance
- OAuth2/OIDC (Google, GitHub, Discord) and JWT auth
- Role-Based Access Control (RBAC) with granular permissions
- GDPR features: data export/deletion, privacy controls
- Security hardening: CSP, HSTS, rate limiting, input validation
- Audit logging and configurable session policies

### 🛠️ DevOps & Operations
- Docker Compose stacks for app and monitoring
- Alembic migrations and database management utilities
- Automated backups with cloud storage options
- Feature flags and API versioning support

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend"
        A[Web UI\nBootstrap 5 + JS]
        B[PWA / Mobile]
    end

    subgraph "Application"
        C[Flask App\nPython 3.8+]
        D[REST API\nFlask-RESTX]
        E[WebSockets]
    end

    subgraph "Services"
        F[Auth & RBAC]
        G[Game Management\nRCON + Templates]
        H[Background Workers]
    end

    subgraph "Data"
        I[(PostgreSQL)]
        J[(Redis)]
        K[Object Storage\nBackups/Media]
    end

    subgraph "Monitoring"
        L[Prometheus]
        M[Grafana]
        N[Alerting]
    end

    A --> C
    B --> D
    C --> F
    C --> G
    D --> F
    E --> H
    C --> I
    C --> J
    F --> I
    G --> I
    H --> J
    H --> K
    C --> L
    L --> M
    L --> N
```

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.8+, Flask 3.0, SQLAlchemy, Flask-Login, Flask-RESTX |
| Frontend | Bootstrap 5, ES6, Jinja2 Templates, Chart.js |
| Database | PostgreSQL, Alembic migrations, pooling |
| Cache/Queue | Redis, RQ/Celery (as configured) |
| Auth | OAuth2 (Google/GitHub/Discord), JWT |
| Monitoring | Prometheus, Grafana, Alertmanager |
| Deployment | Docker, Docker Compose |

---

## 🚀 Quick Start

### Option 1: Interactive Installer (Recommended)

The installer in `tools/installer` automates dependencies, database setup, SSL, and configuration.

```bash
# Run GUI (cross-platform PoC)
python -m tools.installer.gui

# Run CLI (guided)
python -m tools.installer

# Example: CLI install with domain and components
python -m tools.installer.cli install \
    --domain example.com \
    --components postgres,redis,nginx,python

# Uninstall (dry-run)
python -m tools.installer.cli uninstall --dry-run

# Help
python -m tools.installer.cli --help
```

### Option 2: Docker Compose (Fastest)

```bash
git clone https://github.com/phillgates2/panel.git
cd panel
docker-compose up -d

# Access the app at http://localhost:8080
```

Available compose files:
- `docker-compose.yml` — Base stack
- `docker-compose.monitoring.yml` — Prometheus + Grafana
- `docker-compose.microservices.yml` — Extended services

### Option 3: Manual Installation

```bash
# 1) Clone
git clone https://github.com/phillgates2/panel.git
cd panel

# 2) Virtualenv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3) Dependencies
pip install -r requirements/requirements.txt

# 4) Environment
cp .env.example .env
# Edit .env with your settings

# 5) Database
flask db upgrade
python migrations_init.py

# 6) Start
python app.py
```

First steps:
- Visit `http://localhost:8080`
- Configure Admin → Settings
- Add a game server via Servers → Add New
- Check monitoring at `/metrics` or see Grafana docs

---

## 📖 Documentation

### Core Docs
- Installation Guide: `docs/INSTALLER_GUIDE.md`
- Configuration Management: `docs/CONFIGURATION_MANAGEMENT.md`
- API Documentation: `docs/API_DOCUMENTATION.md`
- Database Management: `docs/DATABASE_MANAGEMENT.md`

### Feature Guides
- Game Server Setup: `docs/GAME_SERVER_SETUP.md`
- Pterodactyl Eggs: `docs/PTERO_EGGS_README.md`
- CMS/Forum: `docs/CMS_FORUM.md`
- RBAC: `docs/RBAC_README.md`
- OAuth Setup: `docs/OAUTH_SETUP.md`
- GDPR Compliance: `docs/GDPR_COMPLIANCE.md`

### Deployment & Ops
- Docker Optimization: `docs/DOCKER_OPTIMIZATION_README.md`
- Kubernetes Deployment: `docs/KUBERNETES_DEPLOYMENT.md`
- AWS/GCP/Azure Deployment: `docs/AWS_DEPLOYMENT.md`, `docs/GCP_DEPLOYMENT.md`, `docs/AZURE_DEPLOYMENT.md`
- Monitoring Setup: `docs/MONITORING_DASHBOARD_README.md`
- Backup & Recovery: `docs/BACKUP_RECOVERY.md`
- Load Testing: `docs/LOAD_TESTING.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`

### Developer Resources
- Contributing: `docs/CONTRIBUTING.md`
- Development Setup: `docs/README_DEV.md`
- Test Infrastructure: `docs/TEST_INFRASTRUCTURE_README.md`
- CI/CD Workflows: `docs/CI_CD_README.md`
- Code Quality: `docs/ADDITIONAL_LINTING_README.md`

---

## 🔧 Configuration

Panel uses environment variables via `.env` and config modules.

Example `.env`:

```bash
# Application
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False

# Database
DATABASE_URL=postgresql://panel_user:secure_password@localhost:5432/panel_db

# Redis
REDIS_URL=redis://localhost:6379/0

# OAuth (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
DISCORD_CLIENT_ID=...
DISCORD_CLIENT_SECRET=...

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_URL=http://localhost:3000
```

See `config.py`, `config_dev.py`, `simple_config.py`, and `config_schema.py` for details.

---

## 🧪 Testing

```bash
# Install dev deps
pip install -r requirements/requirements-dev.txt

# Run tests
make test

# Specific suites
make test-unit
make test-integration
make test-performance

# Coverage
make test-coverage
```

---

## 📊 Monitoring

Health checks:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/health/detailed
./panel-doctor.sh
```

Metrics:
- Prometheus at `/metrics`
- Grafana dashboards (see `docs/MONITORING_DASHBOARD_README.md`)

Logging:
- Structured logs with correlation IDs
- Configurable levels and rotation (`logging_config.py`)

---

## 🔒 Security

Key measures:
- OAuth2/OIDC and JWT-based auth
- RBAC with granular permissions
- bcrypt password hashing
- HTTPS enforcement with HSTS
- CSP, rate limiting, input validation
- GDPR tools and audit logging

Run security checks:

```bash
make security
```

See `docs/SECURITY_HARDENING_README.md` for the production checklist.

---

## 🚀 Deployment

Docker Compose:

```bash
docker-compose -f docker-compose.yml up -d
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

Traditional server setup is covered by the installer and systemd templates in `deploy/` (see docs for specifics).

Cloud and Kubernetes guides are available in the `docs/` folder.

---

## 🐛 Troubleshooting

Common checks:

```bash
# Database
sudo systemctl status postgresql
psql -U panel_user -d panel_db -h localhost

# Redis
redis-cli ping

# Debug mode
export FLASK_ENV=development
python app.py
```

More tips: `docs/TROUBLESHOOTING.md` and `panel-doctor.sh`.

---

## 🤝 Contributing

We welcome contributions!

```bash
# Dev setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/requirements-dev.txt
pre-commit install

# Quality checks
make lint
make format
make test
```

See `docs/CONTRIBUTING.md` for guidelines.

---

## 📞 Support

- Issues: https://github.com/phillgates2/panel/issues
- Discussions: https://github.com/phillgates2/panel/discussions
- Docs index: `docs/INDEX.md`

---

## 📄 License

Licensed under the MIT License. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- Flask, SQLAlchemy, Redis, PostgreSQL, Prometheus, Grafana, Docker
- And all open-source contributors who make this possible

---

## 🎯 Roadmap

High-level plans are tracked in `docs/ENTERPRISE_ROADMAP.md` and `docs/WORKFLOWS.md`.

---

<div align="center">

**Panel** — Built with ❤️ by the community

[🚀 Get Started](docs/INSTALLER_GUIDE.md) • [📖 Read the Docs](docs/README.md) • [🐛 Report Bug](https://github.com/phillgates2/panel/issues)

</div>
