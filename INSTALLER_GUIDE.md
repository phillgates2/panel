# Panel Installer Guide

## Quick Start

### One-Line Interactive Install
```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

## Installation Modes

### 1. Development Mode (Quick Local Testing)
- Debug mode enabled
- Direct port access (8080)
- No systemd services
- No nginx proxy
- Perfect for: Local development, testing features

**Interactive:** Select option `1` when prompted

**Non-Interactive:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_DEBUG=true \
PANEL_DB_PASS=devpass \
PANEL_ADMIN_PASS=admin123 \
bash install.sh
```

### 2. Production Mode (Enterprise Deployment)
- Production configuration
- Systemd service management
- Nginx reverse proxy
- SSL certificate support
- Perfect for: Production servers, public deployment

**Interactive:** Select option `2` when prompted

**Non-Interactive:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_SETUP_SYSTEMD=true \
PANEL_SETUP_NGINX=true \
PANEL_SETUP_SSL=false \
PANEL_DOMAIN=panel.example.com \
PANEL_ADMIN_EMAIL=admin@example.com \
PANEL_DB_PASS=$(openssl rand -base64 24) \
PANEL_ADMIN_PASS=$(openssl rand -base64 16) \
bash install.sh
```

### 3. Custom Mode (Choose Components)
- Select individual features
- Mix development and production options
- Perfect for: Specific requirements, hybrid setups

**Interactive:** Select option `3` when prompted and answer each question

## Environment Variables

### Required (Non-Interactive Mode)
```bash
PANEL_DB_PASS=<database_password>
PANEL_ADMIN_PASS=<admin_password>
```

### Database Configuration
```bash
PANEL_DB_HOST=localhost          # PostgreSQL host
PANEL_DB_PORT=5432              # PostgreSQL port
PANEL_DB_NAME=panel             # Database name
PANEL_DB_USER=panel_user        # Database user
PANEL_DB_PASS=<password>        # Database password
```

### Application Settings
```bash
PANEL_INSTALL_DIR=~/panel       # Installation directory
PANEL_DOMAIN=localhost          # Domain or IP address
PANEL_PORT=8080                 # Application port
PANEL_DEBUG=false               # Debug mode (true/false)
PANEL_ADMIN_EMAIL=admin@localhost
PANEL_ADMIN_PASS=<password>
```

### Service Options
```bash
PANEL_SETUP_SYSTEMD=false       # Setup systemd services
PANEL_SETUP_NGINX=false         # Setup nginx reverse proxy
PANEL_SETUP_SSL=false           # Setup SSL certificates
PANEL_AUTO_START=true           # Auto-start after install
```

### Installer Behavior
```bash
PANEL_NON_INTERACTIVE=false     # Skip prompts
PANEL_SKIP_DEPS=false           # Skip system dependencies
PANEL_SKIP_POSTGRESQL=false     # Skip PostgreSQL setup
PANEL_SAVE_SECRETS=true         # Save credentials to .install_secrets
PANEL_FORCE=false               # Auto-yes to all prompts
```

## Installation Process

The installer performs these steps:

1. **System Detection** - Identifies OS and package manager
2. **Pre-flight Checks** - Verifies Python, disk space, network
3. **Interactive Configuration** - Collects all settings (if interactive)
4. **System Dependencies** - Installs nginx, redis, postgresql, build tools
5. **Service Verification** - Ensures Redis and PostgreSQL are running
6. **Panel Installation** - Clones repo, creates venv, installs Python packages
7. **Database Setup** - Creates database, runs migrations, creates admin user
8. **Service Configuration** - Sets up systemd/nginx/ssl (if requested)
9. **Auto-start Services** - Starts Panel and background worker
10. **Health Check** - Verifies Panel is responding
11. **Next Steps** - Shows access info and management commands

## What Gets Installed

### System Packages
- Python 3.8+ with pip and venv
- PostgreSQL server and client
- Redis server
- Nginx web server
- Build tools (gcc, make, etc.)
- SSL/TLS libraries

### Python Packages
- Flask (web framework)
- SQLAlchemy (database ORM)
- Gunicorn (production server)
- RQ (background jobs)
- Redis client
- PostgreSQL driver (psycopg2)
- Security libraries
- See `requirements.txt` for full list

### Services Created
- `panel-gunicorn.service` - Web application
- `rq-worker.service` - Background worker
- Nginx reverse proxy (optional)
- SSL certificates (optional)

## Post-Installation

### Accessing Panel
```
URL: http://localhost:8080 (dev) or http://your-domain (production)
Email: admin@localhost (or your configured email)
Password: <password you set or was generated>
```

### Managing Services (Production Mode)
```bash
# Start services
sudo systemctl start panel-gunicorn
sudo systemctl start rq-worker

# Stop services
sudo systemctl stop panel-gunicorn
sudo systemctl stop rq-worker

# Restart services
sudo systemctl restart panel-gunicorn
sudo systemctl restart rq-worker

# View status
sudo systemctl status panel-gunicorn
sudo systemctl status rq-worker

# View logs
sudo journalctl -u panel-gunicorn -f
sudo journalctl -u rq-worker -f
```

### Managing Services (Development Mode)
```bash
# Start Panel
cd ~/panel
source venv/bin/activate
python3 app.py

# Start worker (in another terminal)
cd ~/panel
source venv/bin/activate
python3 run_worker.py
```

### Viewing Logs
```bash
# Application logs
tail -f ~/panel/logs/panel.log

# Worker logs
tail -f ~/panel/logs/worker.log

# Nginx logs (if configured)
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Installation Fails
1. Check the error message
2. Verify system requirements (Python 3.8+, 500MB disk space)
3. Ensure network connectivity
4. Try with `PANEL_FORCE=true` to bypass confirmations

### Services Won't Start
```bash
# Check if ports are in use
netstat -tlnp | grep 8080
netstat -tlnp | grep 6379  # Redis
netstat -tlnp | grep 5432  # PostgreSQL

# Verify Redis is running
redis-cli ping

# Verify PostgreSQL is running
psql -U panel_user -d panel -c "SELECT 1"

# Check service logs
sudo journalctl -u panel-gunicorn -n 50
sudo journalctl -u rq-worker -n 50
```

### Health Check Fails
```bash
# Check if Panel is running
ps aux | grep "python.*app.py"

# Test manually
curl http://localhost:8080/health

# Check logs for errors
tail -100 ~/panel/logs/panel.log
```

### Database Connection Issues
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Check credentials
cat ~/panel/.db_credentials

# Test connection
psql -U panel_user -d panel -h localhost
```

## Updating Panel

### Pull Latest Changes
```bash
cd ~/panel
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Restart Services
```bash
# Production
sudo systemctl restart panel-gunicorn
sudo systemctl restart rq-worker

# Development
# Stop current processes (Ctrl+C) and restart
python3 app.py
```

## Uninstallation

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash
```

Or manually:
```bash
# Stop services
sudo systemctl stop panel-gunicorn rq-worker
sudo systemctl disable panel-gunicorn rq-worker

# Remove service files
sudo rm /etc/systemd/system/panel-gunicorn.service
sudo rm /etc/systemd/system/rq-worker.service
sudo systemctl daemon-reload

# Remove installation
rm -rf ~/panel

# Remove database (optional)
sudo -u postgres psql -c "DROP DATABASE panel;"
sudo -u postgres psql -c "DROP USER panel_user;"
```

## Support

- **Issues**: https://github.com/phillgates2/panel/issues
- **Documentation**: See `docs/` directory
- **Health Check**: Run `~/panel/panel-doctor.sh`

## Security Notes

1. **Change Default Credentials** - Always use strong, unique passwords
2. **Enable SSL** - Use HTTPS in production
3. **Firewall** - Only expose necessary ports
4. **Updates** - Keep Panel and dependencies updated
5. **Backups** - Regular database backups recommended
6. **Secrets File** - `.install_secrets` contains passwords (chmod 600)

## Advanced Options

### Custom PostgreSQL Location
```bash
PANEL_DB_HOST=postgres.example.com \
PANEL_DB_PORT=5432 \
PANEL_SKIP_POSTGRESQL=true \
bash install.sh
```

### Installing to Custom Directory
```bash
PANEL_INSTALL_DIR=/opt/panel \
bash install.sh
```

### Skip Dependencies (If Already Installed)
```bash
PANEL_SKIP_DEPS=true \
bash install.sh
```

### Config-Only Mode (Testing)
```bash
INSTALLER_CONFIG_ONLY=true \
PANEL_NON_INTERACTIVE=true \
PANEL_DB_PASS=testpass \
PANEL_ADMIN_PASS=testpass \
bash install.sh
```

This validates configuration without actually installing.
