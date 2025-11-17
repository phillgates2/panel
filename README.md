# Panel

**Modern Flask-based game server management platform**

A lightweight, PostgreSQL-powered web application for managing ET: Legacy game servers with built-in database administration, security features, and real-time monitoring.

---

## 🚀 Quick Start

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

The installer supports both **PostgreSQL** (production) and **SQLite** (development) with interactive prompts.

### Installation Options

```bash
# Show all options
bash install.sh --help

# Custom installation directory
bash install.sh --dir /opt/panel

# Force SQLite (development)
bash install.sh --sqlite

# Force PostgreSQL (production)
bash install.sh --postgresql

# Non-interactive mode
bash install.sh --non-interactive

# Skip dependency installation
bash install.sh --skip-deps

# Use specific branch
bash install.sh --branch develop
```

### Non-Interactive Installation

**PostgreSQL Production:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_DB_TYPE=postgresql \
PANEL_DB_HOST=localhost \
PANEL_DB_PORT=5432 \
PANEL_DB_NAME=panel \
PANEL_DB_USER=panel_user \
PANEL_DB_PASS=secure_password \
PANEL_ADMIN_USER=admin \
PANEL_ADMIN_EMAIL=admin@example.com \
PANEL_ADMIN_PASS=admin_password \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

**SQLite Development:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_DB_TYPE=sqlite \
PANEL_ADMIN_USER=admin \
PANEL_ADMIN_PASS=admin123 \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

> **Note:** After installation completes, you'll be prompted to start the Panel immediately. Choose 'y' to auto-start both the web server and background worker. The Panel will be accessible at http://localhost:8080.

### Uninstallation

```bash
# Interactive uninstall (removes ALL files, folders, and system dependencies)
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash

# Show uninstall options
bash uninstall.sh --help

# Force uninstall without prompts
bash uninstall.sh --force

# Keep PostgreSQL database
bash uninstall.sh --keep-db

# Keep system dependencies (Python, PostgreSQL, Nginx, Redis, etc.)
bash uninstall.sh --no-remove-deps

# Uninstall from custom directory
bash uninstall.sh --dir /opt/panel
```

**What gets removed:**
- Installation directory and all files
- Python virtual environment
- Logs, audit logs, and database backups
- SQLite database file (if used)
- Systemd service files (panel-gunicorn, rq-worker, etc.)
- Nginx configuration
- PostgreSQL database and user (unless `--keep-db`)
- System dependencies (unless `--no-remove-deps`): Python3, PostgreSQL, Nginx, Redis, build tools

---

## ✨ Features

### 🔒 Security
- **Rate Limiting** - 30 requests/minute per IP with whitelist support
- **SQL Injection Protection** - Real-time query validation and blocking
- **Security Headers** - CSP, HSTS, X-Frame-Options, secure cookies
- **Audit Logging** - JSONL format with security event tracking
- **Password Security** - Argon2 hashing with secure reset workflows
- **Input Validation** - Marshmallow schemas for type-safe data handling

### 🗄️ Database Management
- **Built-in Database Admin UI** - Python-based web interface for PostgreSQL & SQLite
- **Flask-Migrate** - Database version control and schema migrations
- **PostgreSQL Support** - Production-ready with psycopg2-binary driver
- **SQLite Support** - Fast development setup with zero configuration
- **Query Validation** - SQL injection detection and prevention
- **UTF8MB4** - Full Unicode support for international characters

### 📊 Monitoring
- **Health Endpoints** - `/health` and `/health/detailed` for uptime monitoring
- **Professional Logging** - Rotating log files with structured output
- **Audit Trails** - Track security events and administrative actions
- **RQ Dashboard** - Background job monitoring with web interface
- **Metrics** - Query performance and system health tracking

### 🎨 Modern Interface
- **Responsive Design** - Mobile-friendly admin dashboard
- **Custom Themes** - Configurable CSS and logo support
- **Glass Morphism UI** - Modern gradient backgrounds and effects
- **Accessibility** - WCAG-compliant navigation and forms

### 🛠️ Developer Experience
- **Makefile Commands** - 20+ utilities for testing, linting, migrations, backups
- **Pre-commit Hooks** - Automatic code formatting with Black and isort
- **Comprehensive Tests** - pytest suite with 15+ test cases
- **CI/CD Pipeline** - GitHub Actions with multi-version Python testing

---

## 📋 After Installation

### Access the Panel
```bash
# Default URL (or the domain you specified during installation)
http://localhost:8080

# Login with credentials set during installation
Username: admin
Password: [your password]
```

**Accessing from another machine:**
```bash
# 1. Find your server's IP address
hostname -I    # Shows all IPs
# or
ip addr show   # Detailed network info

# 2. Access Panel via server IP
http://[SERVER_IP]:8080

# Example:
http://192.168.1.100:8080
http://10.0.2.73:8080
```

**If using a domain:**
```bash
# Make sure DNS points to your server
# Access via your configured domain
http://your-domain.com:8080
```

### Start the Panel

**If you chose auto-start during installation**, the Panel is already running!

**To start manually:**
```bash
cd ~/panel  # or your installation directory
source venv/bin/activate

# Create necessary directories
mkdir -p logs instance/logs instance/audit_logs instance/backups

# Start background worker
nohup python3 run_worker.py > logs/worker.log 2>&1 &

# Start web server
nohup python3 app.py > logs/panel.log 2>&1 &

# Panel is now accessible at http://localhost:8080
```

> **Note:** The first startup may take a few seconds as the application initializes the database and creates necessary tables.

**Alternative - Using Make commands:**
```bash
cd ~/panel

# Start development server (SQLite, debug mode)
make dev

# Start production server (PostgreSQL, no debug)
make prod
```

### Stop the Panel

```bash
# Stop all Panel processes
pkill -f "python.*app.py"
pkill -f "python.*run_worker.py"

# Or find specific PIDs first
ps aux | grep "python3 app.py"
ps aux | grep "python3 run_worker.py"

# Then kill by PID
kill [PID_OF_APP] [PID_OF_WORKER]
```

> **Note:** Flask's debug mode creates multiple processes (parent + reloader), so using `pkill -f` is more reliable than killing individual PIDs.

**If using systemd services:**
```bash
# Stop the service
sudo systemctl stop panel-gunicorn

# Check status
sudo systemctl status panel-gunicorn
```

### Manage Database
```bash
# Built-in database admin UI
http://localhost:8080/admin/database
```

### Common Commands
```bash
cd ~/panel  # or your installation directory

# Check if Panel is running
ps aux | grep "python3 app.py"

# View logs
tail -f logs/panel.log
tail -f logs/worker.log

# Check service status (if using systemd)
systemctl status panel-gunicorn

# Database migrations
make db-migrate
make db-upgrade

# Run tests
make test

# Update installation
git pull && make install
```

### Troubleshooting

**Cannot connect to Panel** (`Connection refused` or timeout):
```bash
# 1. Check if Panel is actually running
ps aux | grep "python.*app.py"

# 2. Check if port 8080 is listening
netstat -tlnp | grep 8080
# or
ss -tlnp | grep 8080

# 3. Test local connection
curl http://localhost:8080/

# 4. Check firewall (if accessing remotely)
sudo ufw status
sudo ufw allow 8080/tcp

# 5. If in Docker/container, ensure port is forwarded
# Check your container's port mapping

# 6. Get your server's IP address
hostname -I
ip addr show

# 7. Try accessing via IP instead of localhost
curl http://[YOUR_IP]:8080/
```

**Redis Connection Error** (`Connection refused` on port 6379):
```bash
# Check if Redis is running
ps aux | grep redis-server

# Start Redis
sudo systemctl start redis
# or
sudo systemctl start redis-server
# or (Alpine/manual)
redis-server --daemonize yes

# Enable Redis to start on boot
sudo systemctl enable redis
```

**Panel won't start**:
```bash
# Check logs for errors
tail -f ~/panel/logs/panel.log
tail -f ~/panel/logs/worker.log

# Check if port 8080 is already in use
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep 8080

# Kill process using port 8080
sudo kill [PID]
```

**Database Connection Error**:
```bash
# PostgreSQL - check if service is running
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l | grep panel

# SQLite - check file permissions
ls -la ~/panel/instance/panel.db
```

**Worker not processing jobs**:
```bash
# Ensure Redis is running (see above)

# Check worker logs
tail -f ~/panel/logs/worker.log

# Restart worker
pkill -f "run_worker.py"
cd ~/panel && source venv/bin/activate
nohup python3 run_worker.py > logs/worker.log 2>&1 &
```

---

## 🎯 What's Inside

### Core Stack
- **Flask 3.0** - Modern Python web framework
- **SQLAlchemy** - Powerful ORM with model relationships
- **PostgreSQL** - Production database with psycopg2-binary driver
- **SQLite** - Development database (zero config)
- **Nginx** - High-performance reverse proxy
- **Gunicorn** - Production WSGI server
- **Redis** - Session storage and job queue
- **RQ** - Background task processing

### Security Components
- **Flask-Limiter** - Rate limiting middleware
- **Flask-WTF** - CSRF protection
- **Argon2** - Password hashing
- **Marshmallow** - Input validation schemas
- **Custom SQL Validator** - Injection detection engine
- **Security Headers** - CSP, HSTS, X-Frame-Options

### Admin Tools
- **Database Admin UI** - Python-based management interface
- **Flask-Migrate** - Alembic database migrations
- **Audit Logging** - JSONL security event log
- **RQ Dashboard** - Background job monitoring
- **Health Checks** - System status endpoints

---

## 🏗️ Architecture

```
panel/
├── app.py                    # Main Flask application
├── models.py                 # SQLAlchemy models
├── database_admin.py         # Built-in database UI
├── tasks.py                  # Background tasks (RQ)
├── config.py                 # Production configuration
├── config_dev.py             # Development configuration
├── db_security.py            # SQL injection protection
├── db_audit.py               # Audit logging
├── logging_config.py         # Professional logging
├── security_headers.py       # CSP, HSTS headers
├── input_validation.py       # Marshmallow schemas
├── rate_limiting.py          # Flask-Limiter config
├── rcon_client.py            # ET:Legacy RCON client
├── captcha.py                # CAPTCHA generation
├── templates/                # Jinja2 templates
├── static/css/               # Stylesheets
├── instance/                 # Runtime data
│   ├── logs/                 # Application logs
│   ├── audit_logs/           # Security audit logs
│   └── backups/              # Database backups
├── tests/                    # pytest test suite
├── deploy/                   # Systemd & Nginx configs
├── scripts/                  # Utility scripts
└── tools/                    # Makefile & utilities
```

---

## 🚀 Production Deployment

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, Alpine 3.18+, or similar
- **Python**: 3.8 or higher
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ available
- **Ports**: 8080 (Panel), 8081 (Database Admin)

### Production Checklist

1. **Run installer**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
   # Choose PostgreSQL when prompted
   ```

2. **Configure environment** (`.env` or `config.py`)
   ```python
   SECRET_KEY = 'your-strong-random-key-here'
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/panel'
   REDIS_URL = 'redis://localhost:6379/0'
   ```

3. **Setup firewall**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8080/tcp
   sudo ufw enable
   ```

4. **Enable services**
   ```bash
   sudo systemctl enable panel-gunicorn
   sudo systemctl enable rq-worker-supervised
   sudo systemctl start panel-gunicorn
   ```

5. **Setup SSL** (optional, if using domain)
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

6. **Verify health**
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status": "healthy"}
   ```

---

## 🧪 Development

### Clone & Setup
```bash
git clone https://github.com/phillgates2/panel.git
cd panel

# Install dependencies
make install-dev

# Run development server (SQLite)
make dev
```

### Development Workflow
```bash
# Code formatting
make format

# Linting
make lint

# Run tests with coverage
make test
make coverage

# Database migrations
make db-migrate      # Create migration
make db-upgrade      # Apply migrations
make db-downgrade    # Rollback migration

# Database backup
make db-backup
```

### Pre-commit Hooks
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Environment Variables
```bash
# Development mode (SQLite)
export PANEL_USE_SQLITE=1

# Production mode (PostgreSQL)
export PANEL_DB_TYPE=postgresql
export PANEL_DB_HOST=localhost
export PANEL_DB_NAME=panel
export PANEL_DB_USER=panel_user
export PANEL_DB_PASS=secure_password
```

---

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[README_DEV.md](README_DEV.md)** - Developer documentation
- **`docs/`** - Additional documentation (if present)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Make your changes with tests
4. Run quality checks (`make test lint format`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing`)
7. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📊 CI/CD Status

![CI Status](https://github.com/phillgates2/panel/workflows/Panel%20CI%2FCD/badge.svg)

- Multi-Python version testing (3.8, 3.9, 3.10, 3.11)
- Code coverage reporting
- Security vulnerability scanning
- Automated code formatting checks
- Dependency auditing

---

## 📄 License

This project is open source. See the repository for license details.

---

## 🔗 Links

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Discussions**: https://github.com/phillgates2/panel/discussions

---

## 💡 Support

- �� Check the documentation in `docs/` folder
- 🐛 Report bugs via [Issues](https://github.com/phillgates2/panel/issues)
- 💬 Ask questions in [Discussions](https://github.com/phillgates2/panel/discussions)

---

**Panel** — Modern, secure, production-ready game server management for ET: Legacy. Built with Flask and PostgreSQL.
