# Panel — Modern Game Server Management

**🎮 Production-Ready ET: Legacy Server Management Platform**

A comprehensive Flask-based web application for managing game servers with enterprise security, database management, and real-time monitoring.

---

## 🚀 Quick Start

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash
```

**That's it!** The installer will guide you through the setup interactively.

### Installation Options

```bash
# Development (fastest - SQLite only)
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --sqlite-only

# Production (full features)
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --full

# Custom directory
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --dir /opt/panel

# Non-interactive (automated deployments)
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --non-interactive --db-type mariadb

# See all options
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --help
```

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --uninstall
```

---

## ✨ Key Features

### 🔒 **Enterprise Security**
- **Rate Limiting** - 30 requests/minute with IP whitelisting
- **SQL Injection Protection** - Real-time query validation and blocking
- **Security Headers** - CSP, HSTS, X-Frame-Options, secure sessions
- **Audit Logging** - JSONL format with security event tracking
- **Input Validation** - Marshmallow schemas for type-safe data
- **Password Security** - Argon2 hashing with secure reset flows

### 📊 **Monitoring & Health**
- **Health Endpoint** - `/health` for uptime monitoring
- **Professional Logging** - Rotating files with structured output
- **Metrics Tracking** - Query performance and audit trails
- **RQ Dashboard** - Web UI for background job monitoring

### 🗄️ **Database Management**
- **Built-in phpMyAdmin** - Full database admin UI (no Apache needed!)
- **Served via Nginx** - Port 8081, integrated authentication
- **Flask-Migrate** - Database version control and migrations
- **Query Validation** - SQL injection detection and prevention
- **SQLite & MariaDB** - Flexible database support with UTF8MB4

### 🎨 **Modern Interface**
- **Responsive Design** - Mobile-friendly admin dashboard
- **Glass Morphism UI** - Professional gradient backgrounds
- **Theme System** - Customizable CSS with logo support
- **Accessibility** - WCAG compliant navigation

### 🛠️ **Developer Tools**
- **Makefile** - 20+ commands (test, lint, migrate, backup)
- **Pre-commit Hooks** - Automatic code formatting
- **Docker Dev Env** - docker-compose.dev.yml ready to go
- **Comprehensive Tests** - pytest suite with 15+ tests
- **CI/CD Pipeline** - GitHub Actions with multi-Python versions

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| **[NEW_FEATURES.md](docs/NEW_FEATURES.md)** | Complete features guide with examples |
| **[DATABASE_MANAGEMENT.md](docs/DATABASE_MANAGEMENT.md)** | Database admin and migration guide |
| **[API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** | REST API reference with curl examples |
| **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues and solutions |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute to Panel |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and release notes |

---

## �� After Installation

### Access Panel
```bash
# Default URL (adjust port if configured differently)
http://localhost:8080

# Default credentials (change immediately!)
Username: admin
Password: [set during installation]
```

### Access phpMyAdmin
```bash
# Served via Nginx on port 8081
http://localhost:8081
```

### Useful Commands
```bash
# Navigate to installation
cd ~/panel  # or your custom directory

# Preferred: use the unified panel CLI
./panel.sh help          # See available commands
./panel.sh start         # Start development server
./panel.sh start-prod    # Start production server
./panel.sh status        # Check service status
./panel.sh update        # Update installation
./panel.sh uninstall     # Remove installation

# Legacy helper scripts (deprecated)
# These now forward to panel.sh and will be removed in a future release:
#   scripts/install.sh
#   scripts/update.sh
#   scripts/uninstall.sh
#   start-dev.sh
```

---

## 🎯 What's Included

### Core Components
- ✅ **Flask 3.0** - Modern Python web framework
- ✅ **SQLAlchemy** - Powerful ORM with migrations
- ✅ **Nginx** - High-performance reverse proxy
- ✅ **Gunicorn** - Production WSGI server
- ✅ **Redis** - Session storage and job queue
- ✅ **RQ** - Background task processing

### Optional Components
- 🔹 **MariaDB** - Production-grade database
- 🔹 **phpMyAdmin** - Database management (via Nginx)
- 🔹 **Let's Encrypt** - Free SSL certificates
- 🔹 **Systemd** - Service management

### Security Features
- 🔐 Rate limiting (Flask-Limiter)
- 🔐 SQL injection detection
- 🔐 CSRF protection (Flask-WTF)
- 🔐 Secure password hashing (Argon2)
- 🔐 Security headers (CSP, HSTS)
- 🔐 Audit logging (JSONL)

---

## 🚀 Production Deployment

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, or Alpine 3.18+
- **Python**: 3.8 or higher
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ available
- **Network**: Ports 80, 443 (Panel), 8081 (phpMyAdmin)

### Production Checklist

1. **Install with full components**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --full
   ```

2. **Configure environment** (`.env`)
   - Set strong `SECRET_KEY`
   - Configure database credentials
   - Enable SSL if using domain

3. **Setup firewall**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8081/tcp  # phpMyAdmin
   sudo ufw enable
   ```

4. **Enable services**
   ```bash
   sudo systemctl enable panel-gunicorn
   sudo systemctl enable rq-worker-supervised
   sudo systemctl start panel-gunicorn
   ```

5. **Setup SSL** (if using domain)
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

6. **Test health endpoint**
   ```bash
   curl http://localhost:8080/health
   ```

---

## 🧪 Development

### Clone & Setup
```bash
git clone https://github.com/phillgates2/panel.git
cd panel

# Quick dev setup
make install-dev

# Run development server
make dev
```

### Development Tools
```bash
# Code formatting
make format

# Linting
make lint

# Run tests
make test

# Coverage report
make coverage

# Database migrations
make db-migrate
make db-upgrade
make db-downgrade
```

### Pre-commit Hooks
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📦 Architecture

```
panel/
├── app.py                  # Main Flask application
├── models.py               # SQLAlchemy models
├── tasks.py                # Background tasks (RQ)
├── db_security.py          # SQL injection protection
├── db_audit.py             # Audit logging
├── logging_config.py       # Professional logging
├── security_headers.py     # CSP, HSTS headers
├── input_validation.py     # Marshmallow schemas
├── rate_limiting.py        # Flask-Limiter config
├── templates/              # Jinja2 templates
├── static/                 # CSS, JS, images
├── instance/               # Runtime data
│   ├── logs/               # Application logs
│   ├── audit_logs/         # Security audit logs
│   └── backups/            # Database backups
├── migrations/             # Flask-Migrate
├── tests/                  # pytest test suite
├── docs/                   # Documentation
├── deploy/                 # Systemd, Nginx configs
└── tools/                  # Utilities, Makefile
```

---

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Make changes with tests
4. Run `make test lint format`
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing`)
7. Open Pull Request

---

## 📊 CI/CD Status

![CI Status](https://github.com/phillgates2/panel/workflows/Panel%20CI%2FCD/badge.svg)

- ✅ Multi-Python version testing (3.8, 3.9, 3.10, 3.11)
- ✅ Code coverage reporting
- ✅ Security scanning
- ✅ Automated formatting checks
- ✅ Dependency vulnerability scanning

---

## 📄 License

This project is open source. See repository for details.

---

## 🔗 Links

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Discussions**: https://github.com/phillgates2/panel/discussions
- **Documentation**: [docs/](docs/)

---

## 💡 Support

- 📖 Check the [Documentation](docs/)
- 🐛 Report bugs via [Issues](https://github.com/phillgates2/panel/issues)
- 💬 Ask questions in [Discussions](https://github.com/phillgates2/panel/discussions)
- 🔧 See [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

---

**Panel** — Modern, secure, production-ready game server management. Built with Flask. Optimized for ET: Legacy.
