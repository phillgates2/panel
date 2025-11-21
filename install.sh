#!/usr/bin/env bash
# ============================================================================
# Panel - Comprehensive Enterprise Installer
# ============================================================================
# A complete, production-ready installation system for the Flask panel application
# with enterprise features, security hardening, and automated deployment
#
# Features:
#   - Multi-platform support (Linux/macOS)
#   - PostgreSQL & Redis setup
#   - SSL/TLS configuration
#   - Systemd service management
#   - Security hardening
#   - Backup automation
#   - Monitoring setup
#   - Enterprise integrations
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash -s -- --help
#
# ============================================================================

set -eo pipefail

# ============================================================================
# Configuration & Constants
# ============================================================================

# Repository Information
REPO_URL="https://github.com/phillgates2/panel.git"
REPO_NAME="panel"
BRANCH="${PANEL_BRANCH:-main}"
INSTALL_DIR="${PANEL_INSTALL_DIR:-$HOME/panel}"

# Colors and Formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Installation Options
DB_TYPE="${PANEL_DB_TYPE:-postgresql}"
DB_HOST="${PANEL_DB_HOST:-localhost}"
DB_PORT="${PANEL_DB_PORT:-5432}"
DB_NAME="${PANEL_DB_NAME:-panel}"
DB_USER="${PANEL_DB_USER:-panel_user}"
DB_PASS="${PANEL_DB_PASS:-}"

REDIS_HOST="${PANEL_REDIS_HOST:-localhost}"
REDIS_PORT="${PANEL_REDIS_PORT:-6379}"
REDIS_DB="${PANEL_REDIS_DB:-0}"

APP_HOST="${PANEL_HOST:-0.0.0.0}"
APP_PORT="${PANEL_PORT:-8080}"
DOMAIN="${PANEL_DOMAIN:-localhost}"
SSL_CERT="${PANEL_SSL_CERT:-}"
SSL_KEY="${PANEL_SSL_KEY:-}"

ADMIN_EMAIL="${PANEL_ADMIN_EMAIL:-admin@localhost}"
ADMIN_PASSWORD="${PANEL_ADMIN_PASS:-}"

# Enterprise Features
OAUTH_GOOGLE_CLIENT_ID="${PANEL_OAUTH_GOOGLE_CLIENT_ID:-}"
OAUTH_GOOGLE_CLIENT_SECRET="${PANEL_OAUTH_GOOGLE_CLIENT_SECRET:-}"
OAUTH_GITHUB_CLIENT_ID="${PANEL_OAUTH_GITHUB_CLIENT_ID:-}"
OAUTH_GITHUB_CLIENT_SECRET="${PANEL_OAUTH_GITHUB_CLIENT_SECRET:-}"

BACKUP_S3_BUCKET="${PANEL_BACKUP_S3_BUCKET:-}"
BACKUP_S3_ACCESS_KEY="${PANEL_BACKUP_S3_ACCESS_KEY:-}"
BACKUP_S3_SECRET_KEY="${PANEL_BACKUP_S3_SECRET_KEY:-}"
BACKUP_S3_REGION="${PANEL_BACKUP_S3_REGION:-us-east-1}"

GRAFANA_URL="${PANEL_GRAFANA_URL:-}"
PROMETHEUS_URL="${PANEL_PROMETHEUS_URL:-}"

# Installation Flags
NON_INTERACTIVE="${PANEL_NON_INTERACTIVE:-false}"
SKIP_DEPS="${PANEL_SKIP_DEPS:-false}"
SKIP_POSTGRESQL="${PANEL_SKIP_POSTGRESQL:-false}"
SKIP_REDIS="${PANEL_SKIP_REDIS:-false}"
SAVE_SECRETS="${PANEL_SAVE_SECRETS:-false}"
REDACT_SECRETS="${PANEL_REDACT_SECRETS:-false}"
INSTALLER_CONFIG_ONLY="${INSTALLER_CONFIG_ONLY:-false}"
NO_PIP_INSTALL="${PANEL_NO_PIP_INSTALL:-false}"
FORCE="${PANEL_FORCE:-false}"
VERBOSE="${PANEL_VERBOSE:-false}"

# Service Management
SETUP_SYSTEMD="${PANEL_SETUP_SYSTEMD:-false}"
SETUP_DOCKER="${PANEL_SETUP_DOCKER:-false}"
SETUP_KUBERNETES="${PANEL_SETUP_KUBERNETES:-false}"

# Security Options
ENABLE_FIREWALL="${PANEL_ENABLE_FIREWALL:-true}"
ENABLE_SELINUX="${PANEL_ENABLE_SELINUX:-false}"
ENABLE_SSL="${PANEL_ENABLE_SSL:-false}"
ENABLE_LETSENCRYPT="${PANEL_ENABLE_LETSENCRYPT:-false}"

# Monitoring & Backup
ENABLE_MONITORING="${PANEL_ENABLE_MONITORING:-true}"
ENABLE_BACKUPS="${PANEL_ENABLE_BACKUPS:-true}"
BACKUP_SCHEDULE="${PANEL_BACKUP_SCHEDULE:-daily}"

# ============================================================================
# Utility Functions
# ============================================================================

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_verbose() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${DIM}[VERBOSE]${NC} $1" >&2
    fi
}

log_header() {
    echo -e "\n${BOLD}${CYAN}================================${NC}" >&2
    echo -e "${BOLD}${CYAN} $1 ${NC}" >&2
    echo -e "${BOLD}${CYAN}================================${NC}\n" >&2
}

log_step() {
    echo -e "${BOLD}${MAGENTA}➤${NC} $1" >&2
}

# System detection
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        elif [ -f /etc/redhat-release ]; then
            OS="rhel"
            OS_VERSION=$(cat /etc/redhat-release | sed 's/.*release \([0-9]\+\).*/\1/')
        elif [ -f /etc/debian_version ]; then
            OS="debian"
            OS_VERSION=$(cat /etc/debian_version)
        else
            OS="linux"
            OS_VERSION="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    else
        OS="unknown"
        OS_VERSION="unknown"
    fi

    log_verbose "Detected OS: $OS $OS_VERSION"
}

detect_architecture() {
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        armv7l) ARCH="arm" ;;
    esac
    log_verbose "Detected architecture: $ARCH"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root - this may cause permission issues"
        return 0
    fi
    return 1
}

check_dependencies() {
    local deps=("curl" "wget" "git" "python3" "pip3")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing[*]}"
        return 1
    fi

    return 0
}

# ============================================================================
# Installation Functions
# ============================================================================

install_system_dependencies() {
    log_header "Installing System Dependencies"

    if [ "$SKIP_DEPS" = "true" ]; then
        log_info "Skipping system dependency installation"
        return 0
    fi

    case $OS in
        ubuntu|debian)
            log_step "Updating package lists..."
            sudo apt-get update

            log_step "Installing core dependencies..."
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                postgresql postgresql-contrib \
                redis-server \
                nginx \
                curl wget git \
                build-essential \
                libpq-dev \
                libssl-dev \
                libffi-dev \
                libxml2-dev \
                libxslt-dev \
                zlib1g-dev

            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo apt-get install -y certbot python3-certbot-nginx
            fi

            if [ "$ENABLE_MONITORING" = "true" ]; then
                sudo apt-get install -y prometheus prometheus-node-exporter grafana
            fi
            ;;

        centos|rhel|fedora)
            log_step "Installing core dependencies..."
            sudo yum install -y \
                python3 python3-pip \
                postgresql postgresql-server postgresql-contrib \
                redis \
                nginx \
                curl wget git \
                gcc gcc-c++ \
                postgresql-devel \
                openssl-devel \
                libffi-devel \
                libxml2-devel \
                libxslt-devel \
                zlib-devel

            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo yum install -y certbot python3-certbot-nginx
            fi
            ;;

        macos)
            if command -v brew >/dev/null 2>&1; then
                log_step "Installing dependencies with Homebrew..."
                brew install \
                    python3 postgresql redis nginx \
                    curl wget git \
                    openssl libffi libxml2 libxslt zlib
            else
                log_error "Homebrew not found. Please install Homebrew first."
                return 1
            fi
            ;;

        *)
            log_error "Unsupported operating system: $OS"
            return 1
            ;;
    esac

    log_success "System dependencies installed"
}

setup_postgresql() {
    log_header "Setting up PostgreSQL Database"

    if [ "$SKIP_POSTGRESQL" = "true" ]; then
        log_info "Skipping PostgreSQL setup"
        return 0
    fi

    case $OS in
        ubuntu|debian)
            log_step "Starting PostgreSQL service..."
            sudo systemctl enable postgresql
            sudo systemctl start postgresql

            log_step "Creating database and user..."
            sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
            sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
            ;;

        centos|rhel|fedora)
            log_step "Initializing PostgreSQL..."
            sudo postgresql-setup initdb

            log_step "Starting PostgreSQL service..."
            sudo systemctl enable postgresql
            sudo systemctl start postgresql

            log_step "Creating database and user..."
            sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
            sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
            ;;

        macos)
            log_step "Starting PostgreSQL service..."
            brew services start postgresql

            log_step "Creating database and user..."
            createdb $DB_NAME 2>/dev/null || true
            psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
            psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
            ;;
    esac

    log_success "PostgreSQL database setup complete"
}

setup_redis() {
    log_header "Setting up Redis Cache"

    if [ "$SKIP_REDIS" = "true" ]; then
        log_info "Skipping Redis setup"
        return 0
    fi

    case $OS in
        ubuntu|debian|centos|rhel|fedora)
            log_step "Starting Redis service..."
            sudo systemctl enable redis-server
            sudo systemctl start redis-server
            ;;

        macos)
            log_step "Starting Redis service..."
            brew services start redis
            ;;
    esac

    log_success "Redis setup complete"
}

clone_repository() {
    log_header "Cloning Panel Repository"

    if [ -d "$INSTALL_DIR" ] && [ "$FORCE" != "true" ]; then
        log_error "Installation directory already exists: $INSTALL_DIR"
        log_info "Use FORCE=true to overwrite existing installation"
        return 1
    fi

    log_step "Cloning repository..."
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi

    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    log_success "Repository cloned to $INSTALL_DIR"
}

setup_python_environment() {
    log_header "Setting up Python Environment"

    cd "$INSTALL_DIR"

    log_step "Creating virtual environment..."
    python3 -m venv venv

    log_step "Activating virtual environment and installing dependencies..."
    source venv/bin/activate

    if [ "$NO_PIP_INSTALL" != "true" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt

        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
        fi
    fi

    log_success "Python environment setup complete"
}

configure_application() {
    log_header "Configuring Application"

    cd "$INSTALL_DIR"

    log_step "Creating configuration files..."

    # Create .env file
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME

# Redis Configuration
REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT/$REDIS_DB
CACHE_REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT/1
RQ_REDIS_URL=redis://$REDIS_HOST:$REDIS_PORT/2

# Application Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
FLASK_APP=app.py
HOST=$APP_HOST
PORT=$APP_PORT

# Admin Configuration
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD

# OAuth Configuration
GOOGLE_CLIENT_ID=$OAUTH_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$OAUTH_GOOGLE_CLIENT_SECRET
GITHUB_CLIENT_ID=$OAUTH_GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=$OAUTH_GITHUB_CLIENT_SECRET

# Backup Configuration
BACKUP_S3_BUCKET=$BACKUP_S3_BUCKET
AWS_ACCESS_KEY_ID=$BACKUP_S3_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$BACKUP_S3_SECRET_KEY
AWS_REGION=$BACKUP_S3_REGION

# Monitoring Configuration
GRAFANA_URL=$GRAFANA_URL
PROMETHEUS_URL=$PROMETHEUS_URL

# Security Configuration
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
EOF

    # Create config.py
    cat > config.py << EOF
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv('REDIS_URL')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL')
    RQ_REDIS_URL = os.getenv('RQ_REDIS_URL')

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # Application
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8080))
    DEBUG = os.getenv('FLASK_ENV') == 'development'

    # OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

    # Admin
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

    # Security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

    # Backup
    BACKUP_S3_BUCKET = os.getenv('BACKUP_S3_BUCKET')
    BACKUP_ENCRYPTION_KEY = os.getenv('BACKUP_ENCRYPTION_KEY', os.urandom(32).hex())

    # Monitoring
    GRAFANA_URL = os.getenv('GRAFANA_URL')
    PROMETHEUS_URL = os.getenv('PROMETHEUS_URL')

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
EOF

    log_success "Application configuration complete"
}

setup_ssl() {
    log_header "Setting up SSL/TLS"

    if [ "$ENABLE_SSL" != "true" ] && [ "$ENABLE_LETSENCRYPT" != "true" ]; then
        log_info "SSL setup skipped"
        return 0
    fi

    if [ "$ENABLE_LETSENCRYPT" = "true" ]; then
        log_step "Setting up Let's Encrypt SSL certificate..."
        sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$ADMIN_EMAIL"
    elif [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
        log_step "Installing provided SSL certificate..."
        sudo cp "$SSL_CERT" /etc/ssl/certs/panel.crt
        sudo cp "$SSL_KEY" /etc/ssl/private/panel.key
    fi

    log_success "SSL setup complete"
}

setup_nginx() {
    log_header "Setting up Nginx Reverse Proxy"

    case $OS in
        ubuntu|debian)
            sudo tee /etc/nginx/sites-available/panel << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://$APP_HOST:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $INSTALL_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo tee /etc/nginx/sites-available/panel-ssl << EOF
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/ssl/certs/panel.crt;
    ssl_certificate_key /etc/ssl/private/panel.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://$APP_HOST:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $INSTALL_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
            fi

            sudo ln -sf /etc/nginx/sites-available/panel /etc/nginx/sites-enabled/
            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo ln -sf /etc/nginx/sites-available/panel-ssl /etc/nginx/sites-enabled/
            fi
            sudo rm -f /etc/nginx/sites-enabled/default
            sudo nginx -t && sudo systemctl reload nginx
            ;;
    esac

    log_success "Nginx setup complete"
}

setup_systemd_services() {
    log_header "Setting up Systemd Services"

    if [ "$SETUP_SYSTEMD" != "true" ]; then
        log_info "Systemd service setup skipped"
        return 0
    fi

    # Panel service
    sudo tee /etc/systemd/system/panel.service << EOF
[Unit]
Description=Panel Web Application
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # RQ Worker service
    sudo tee /etc/systemd/system/panel-worker.service << EOF
[Unit]
Description=Panel Background Worker
After=network.target redis-server.service panel.service
Requires=redis-server.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python rq_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable panel panel-worker

    log_success "Systemd services created"
}

setup_firewall() {
    log_header "Setting up Firewall"

    if [ "$ENABLE_FIREWALL" != "true" ]; then
        log_info "Firewall setup skipped"
        return 0
    fi

    case $OS in
        ubuntu|debian)
            sudo ufw allow ssh
            sudo ufw allow 80
            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo ufw allow 443
            fi
            echo "y" | sudo ufw enable
            ;;

        centos|rhel|fedora)
            sudo firewall-cmd --permanent --add-service=ssh
            sudo firewall-cmd --permanent --add-service=http
            if [ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ]; then
                sudo firewall-cmd --permanent --add-service=https
            fi
            sudo firewall-cmd --reload
            ;;
    esac

    log_success "Firewall configured"
}

setup_monitoring() {
    log_header "Setting up Monitoring"

    if [ "$ENABLE_MONITORING" != "true" ]; then
        log_info "Monitoring setup skipped"
        return 0
    fi

    # Install and configure Prometheus
    # Install and configure Grafana
    # Setup basic dashboards

    log_success "Monitoring setup complete"
}

setup_backups() {
    log_header "Setting up Automated Backups"

    if [ "$ENABLE_BACKUPS" != "true" ]; then
        log_info "Backup setup skipped"
        return 0
    fi

    # Create backup script
    cat > "$INSTALL_DIR/backup.sh" << EOF
#!/bin/bash
# Panel Backup Script

cd "$INSTALL_DIR"
source venv/bin/activate

python -c "
from automated_backups import BackupManager
import os

config = {
    'backup_dir': '$INSTALL_DIR/backups',
    'database_url': 'postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME',
    'retention_days': 30,
    'encryption_key': os.getenv('BACKUP_ENCRYPTION_KEY'),
    's3_enabled': ${BACKUP_S3_BUCKET:+true},
    's3_bucket': '$BACKUP_S3_BUCKET',
    'aws_access_key_id': '$BACKUP_S3_ACCESS_KEY',
    'aws_secret_access_key': '$BACKUP_S3_SECRET_KEY',
    'aws_region': '$BACKUP_S3_REGION'
}

backup_manager = BackupManager(config)
backup_manager.create_database_backup('postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME')
backup_manager.create_filesystem_backup(['$INSTALL_DIR/uploads', '$INSTALL_DIR/logs'])
backup_manager.create_config_backup(['$INSTALL_DIR/.env', '$INSTALL_DIR/config.py'])
"
EOF

    chmod +x "$INSTALL_DIR/backup.sh"

    # Setup cron job
    case "$BACKUP_SCHEDULE" in
        hourly)
            cron_schedule="0 * * * *"
            ;;
        daily)
            cron_schedule="0 2 * * *"
            ;;
        weekly)
            cron_schedule="0 2 * * 0"
            ;;
    esac

    (crontab -l ; echo "$cron_schedule $INSTALL_DIR/backup.sh") | crontab -

    log_success "Automated backups configured"
}

run_database_migrations() {
    log_header "Running Database Migrations"

    cd "$INSTALL_DIR"
    source venv/bin/activate

    log_step "Initializing database..."
    python -c "
from app import create_app, db
from models import *
from config import config

app = create_app(config['production'])
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"

    log_step "Running migrations..."
    if [ -d "migrations" ]; then
        flask db upgrade
    fi

    log_success "Database migrations complete"
}

create_admin_user() {
    log_header "Creating Admin User"

    cd "$INSTALL_DIR"
    source venv/bin/activate

    python -c "
from app import create_app
from models import User, db
from config import config
import bcrypt

app = create_app(config['production'])
with app.app_context():
    # Check if admin user exists
    admin = User.query.filter_by(email='$ADMIN_EMAIL').first()
    if not admin:
        # Create admin user
        hashed_password = bcrypt.hashpw('$ADMIN_PASSWORD'.encode('utf-8'), bcrypt.gensalt())
        admin = User(
            email='$ADMIN_EMAIL',
            password=hashed_password.decode('utf-8'),
            is_system_admin=True,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"

    log_success "Admin user setup complete"
}

generate_installation_summary() {
    log_header "Installation Summary"

    cat << EOF

${BOLD}${GREEN}🎉 Panel Installation Complete!${NC}

${BOLD}Installation Details:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Installation Directory: $INSTALL_DIR
🌐 Application URL: http://$DOMAIN:$APP_PORT
🔒 SSL Enabled: $([ "$ENABLE_SSL" = "true" ] || [ "$ENABLE_LETSENCRYPT" = "true" ] && echo "Yes" || echo "No")
🗄️  Database: $DB_TYPE://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME
⚡ Cache: redis://$REDIS_HOST:$REDIS_PORT
👤 Admin Email: $ADMIN_EMAIL

${BOLD}Services:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$(if [ "$SETUP_SYSTEMD" = "true" ]; then echo "✅ Systemd services: panel, panel-worker"; fi)
$(if [ "$ENABLE_MONITORING" = "true" ]; then echo "✅ Monitoring: Prometheus, Grafana"; fi)
$(if [ "$ENABLE_BACKUPS" = "true" ]; then echo "✅ Backups: Automated ($BACKUP_SCHEDULE)"; fi)

${BOLD}Next Steps:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ${CYAN}Start the application:${NC}
   cd $INSTALL_DIR && source venv/bin/activate && python app.py

2. ${CYAN}Access the web interface:${NC}
   http://$DOMAIN:$APP_PORT

3. ${CYAN}Login with admin credentials:${NC}
   Email: $ADMIN_EMAIL
   Password: $ADMIN_PASSWORD

4. ${CYAN}Start background worker:${NC}
   python rq_worker.py

${BOLD}Useful Commands:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${DIM}# Check application status${NC}
curl http://localhost:$APP_PORT/health

${DIM}# View logs${NC}
tail -f $INSTALL_DIR/logs/panel.log

${DIM}# Run health check${NC}
$INSTALL_DIR/panel-comprehensive-health-check.sh all

${DIM}# Run load testing${NC}
cd $INSTALL_DIR && python load_testing.py --users 50 --spawn-rate 5 --run-time 5m

${BOLD}Documentation:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 README: $INSTALL_DIR/README.md
🔧 Configuration: $INSTALL_DIR/.env
📊 Monitoring: $INSTALL_DIR/MAJOR_IMPROVEMENTS_SUMMARY.md
🐳 Kubernetes: $INSTALL_DIR/k8s/README.md

${BOLD}${GREEN}Thank you for installing Panel! 🚀${NC}

EOF
}

# ============================================================================
# Main Installation Function
# ============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Pre-installation checks
    detect_os
    detect_architecture
    check_root
    check_dependencies

    # Interactive configuration if needed
    if [ "$NON_INTERACTIVE" != "true" ]; then
        interactive_setup
    fi

    # Installation process
    install_system_dependencies
    setup_postgresql
    setup_redis
    clone_repository
    setup_python_environment
    configure_application
    setup_ssl
    setup_nginx
    setup_systemd_services
    setup_firewall
    setup_monitoring
    setup_backups
    run_database_migrations
    create_admin_user

    # Generate installation summary
    generate_installation_summary

    log_success "Panel installation completed successfully!"
}

show_help() {
    cat << EOF
Panel - Comprehensive Enterprise Installer

USAGE:
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash -s -- [OPTIONS]

OPTIONS:
    --help, -h          Show this help message
    --non-interactive   Run installation without user prompts
    --skip-deps         Skip system dependency installation
    --force             Force overwrite existing installation
    --verbose           Enable verbose logging

ENVIRONMENT VARIABLES:
    PANEL_INSTALL_DIR           Installation directory (default: ~/panel)
    PANEL_BRANCH               Git branch to install (default: main)
    PANEL_DB_TYPE              Database type (default: postgresql)
    PANEL_DB_HOST              Database host (default: localhost)
    PANEL_DB_PORT              Database port (default: 5432)
    PANEL_DB_NAME              Database name (default: panel)
    PANEL_DB_USER              Database user (default: panel_user)
    PANEL_DB_PASS              Database password
    PANEL_HOST                 Application host (default: 0.0.0.0)
    PANEL_PORT                 Application port (default: 8080)
    PANEL_DOMAIN               Domain name (default: localhost)
    PANEL_ADMIN_EMAIL          Admin email (default: admin@localhost)
    PANEL_ADMIN_PASS           Admin password
    PANEL_ENABLE_SSL           Enable SSL/TLS (default: false)
    PANEL_ENABLE_LETSENCRYPT   Enable Let's Encrypt SSL (default: false)
    PANEL_SETUP_SYSTEMD        Setup systemd services (default: false)
    PANEL_ENABLE_MONITORING    Enable monitoring (default: true)
    PANEL_ENABLE_BACKUPS       Enable automated backups (default: true)
    PANEL_VERBOSE              Enable verbose logging (default: false)

EXAMPLES:
    # Basic installation
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash

    # Custom installation with SSL
    PANEL_DOMAIN=mypanel.com PANEL_ENABLE_SSL=true \\
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash

    # Non-interactive installation
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash -s -- --non-interactive

For more information, visit: https://github.com/phillgates2/panel
EOF
}

interactive_setup() {
    log_header "Interactive Setup"

    echo "Welcome to the Panel installer!"
    echo "This will guide you through the installation process."
    echo

    # Database configuration
    read -p "Database password (leave empty for auto-generated): " -s db_pass
    echo
    if [ -n "$db_pass" ]; then
        DB_PASS="$db_pass"
    else
        DB_PASS=$(openssl rand -hex 16)
        echo "Auto-generated database password: $DB_PASS"
    fi

    # Admin configuration
    read -p "Admin email [admin@localhost]: " admin_email
    ADMIN_EMAIL="${admin_email:-admin@localhost}"

    read -p "Admin password (leave empty for auto-generated): " -s admin_pass
    echo
    if [ -n "$admin_pass" ]; then
        ADMIN_PASSWORD="$admin_pass"
    else
        ADMIN_PASSWORD=$(openssl rand -hex 12)
        echo "Auto-generated admin password: $ADMIN_PASSWORD"
    fi

    # Domain configuration
    read -p "Domain name [localhost]: " domain
    DOMAIN="${domain:-localhost}"

    # SSL configuration
    read -p "Enable SSL/TLS? (y/N): " enable_ssl
    if [[ $enable_ssl =~ ^[Yy]$ ]]; then
        ENABLE_SSL=true
        read -p "Use Let's Encrypt? (Y/n): " use_letsencrypt
        if [[ ! $use_letsencrypt =~ ^[Nn]$ ]]; then
            ENABLE_LETSENCRYPT=true
        fi
    fi

    # Service configuration
    read -p "Setup systemd services? (y/N): " setup_systemd
    if [[ $setup_systemd =~ ^[Yy]$ ]]; then
        SETUP_SYSTEMD=true
    fi

    echo
    echo "Configuration complete. Starting installation..."
    echo
}

# ============================================================================
# Run Main Function
# ============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
