#!/usr/bin/env bash
# Panel Installer - Streamlined PostgreSQL Version
# Usage: curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
# Uninstall: curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash

set -eo pipefail

# ============================================================================
# Configuration & Constants
# ============================================================================

REPO_URL="https://github.com/phillgates2/panel.git"
INSTALL_DIR="${PANEL_INSTALL_DIR:-$HOME/panel}"
BRANCH="${PANEL_BRANCH:-main}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Installation options
DB_TYPE="${PANEL_DB_TYPE:-sqlite}"  # sqlite or postgresql
DB_HOST="${PANEL_DB_HOST:-localhost}"
DB_PORT="${PANEL_DB_PORT:-5432}"
DB_NAME="${PANEL_DB_NAME:-panel}"
DB_USER="${PANEL_DB_USER:-panel_user}"
DB_PASS="${PANEL_DB_PASS:-}"

APP_HOST="${PANEL_HOST:-0.0.0.0}"
APP_PORT="${PANEL_PORT:-8080}"
DOMAIN="${PANEL_DOMAIN:-localhost}"
DEBUG_MODE="${PANEL_DEBUG:-false}"

ADMIN_EMAIL="${PANEL_ADMIN_EMAIL:-admin@localhost}"
ADMIN_PASSWORD="${PANEL_ADMIN_PASS:-}"

NON_INTERACTIVE="${PANEL_NON_INTERACTIVE:-false}"
SKIP_DEPS="${PANEL_SKIP_DEPS:-false}"
SKIP_POSTGRESQL="${PANEL_SKIP_POSTGRESQL:-false}"

# System detection
PKG_MANAGER=""
SUDO=""

# ============================================================================
# Help & Usage
# ============================================================================

show_help() {
    cat << 'EOF'
Panel Installer - PostgreSQL Edition

USAGE:
    # Installation
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
    bash install.sh [OPTIONS]

    # Uninstallation  
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash
    bash uninstall.sh [OPTIONS]

INSTALLATION OPTIONS:
    -h, --help              Show this help message
    -d, --dir DIR           Installation directory (default: ~/panel)
    -b, --branch BRANCH     Git branch to install (default: main)
    --sqlite                Use SQLite database (default)
    --postgresql            Use PostgreSQL database
    --non-interactive       Run without prompts (requires env vars)
    --skip-deps             Skip system dependency installation
    --skip-postgresql       Skip PostgreSQL setup (use existing)
    --verify-only           Verify existing installation without reinstalling
    --update                Update existing installation (git pull + pip upgrade)

ENVIRONMENT VARIABLES:
    # Installation
    PANEL_INSTALL_DIR       Installation directory
    PANEL_BRANCH            Git branch to use
    PANEL_DB_TYPE           Database type: sqlite or postgresql
    PANEL_DB_HOST           PostgreSQL host (default: localhost)
    PANEL_DB_PORT           PostgreSQL port (default: 5432)
    PANEL_DB_NAME           PostgreSQL database name (default: panel)
    PANEL_DB_USER           PostgreSQL username (default: panel_user)
    PANEL_DB_PASS           PostgreSQL password
    PANEL_ADMIN_EMAIL       Admin email (default: admin@localhost)
    PANEL_ADMIN_PASS        Admin password
    PANEL_NON_INTERACTIVE   Skip prompts (true/false)
    PANEL_SKIP_DEPS         Skip system dependencies (true/false)
    PANEL_SKIP_POSTGRESQL   Skip PostgreSQL setup (true/false)

INSTALLATION EXAMPLES:
    # Interactive installation (SQLite)
    curl -fsSL .../install.sh | bash

    # Non-interactive PostgreSQL installation
    PANEL_NON_INTERACTIVE=true \
    PANEL_DB_TYPE=postgresql \
    PANEL_DB_PASS=mypassword \
    PANEL_ADMIN_EMAIL=admin@example.com \
    PANEL_ADMIN_PASS=adminpass \
    curl -fsSL .../install.sh | bash

    # Custom directory
    bash install.sh --dir /opt/panel

    # Development with SQLite
    bash install.sh --sqlite --dir ~/panel-dev

AVAILABLE INSTALLER FUNCTIONS:
    Core Functions:
      • log()                  - Print informational messages
      • success()              - Print success messages
      • error()                - Print error messages and exit
      • warn()                 - Print warning messages
      • show_help()            - Display help message

    System Detection:
      • detect_pkg_manager()   - Detect OS package manager
      • detect_sudo()          - Detect if sudo is needed

    Validation Functions:
      • check_python_version() - Verify Python 3.8+ is available
      • check_disk_space()     - Ensure 500MB+ free space
      • check_network()        - Test internet connectivity
      • validate_port()        - Check if port is available
      • verify_installation()  - Verify existing installation

    Installation Functions:
      • install_dependencies() - Install system packages
      • setup_postgresql()     - Configure PostgreSQL database
      • install_nginx()        - Install and configure Nginx
      • install_panel()        - Main installation orchestrator
      • setup_python_env()     - Create venv and install deps
      • configure_database()   - Generate database config
      • create_admin_user()    - Create initial admin account
      • setup_services()       - Configure systemd services
      • setup_logrotate()      - Configure log rotation
      • health_check()         - Test panel startup

    Utility Functions:
      • generate_secret()      - Generate secure random key
      • prompt_user()          - Interactive user prompts
      • backup_installation()  - Backup existing installation

UNINSTALLATION:
    For complete uninstallation including system dependencies, use:
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash
    
    See 'bash uninstall.sh --help' for uninstallation options.

EOF
    exit 0
}

# ============================================================================
# Helper Functions
# ============================================================================

log() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# Cleanup on failure
cleanup_on_error() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        warn "Installation failed with exit code $exit_code"
        if [[ -n "$BACKUP_DIR" ]] && [[ -d "$BACKUP_DIR" ]]; then
            log "Backup available at: $BACKUP_DIR"
        fi
    fi
}

trap cleanup_on_error EXIT

# Validation functions
check_python_version() {
    log "Checking Python version..."
    if ! command -v python3 &>/dev/null; then
        error "Python 3 is not installed"
    fi
    
    local python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local required_version="3.8"
    
    # Compare versions using sort -V (version sort)
    local lowest=$(printf '%s\n%s' "$python_version" "$required_version" | sort -V | head -n1)
    if [[ "$lowest" != "$required_version" ]]; then
        error "Python $required_version or higher required (found: $python_version)"
    fi
    
    log "Python version: $python_version ✓"
}

check_disk_space() {
    log "Checking disk space..."
    local install_parent=$(dirname "$INSTALL_DIR")
    local available_mb=$(df -m "$install_parent" 2>/dev/null | awk 'NR==2 {print $4}')
    local required_mb=500
    
    if [[ -n "$available_mb" ]] && [[ "$available_mb" -lt "$required_mb" ]]; then
        warn "Low disk space: ${available_mb}MB available, ${required_mb}MB recommended"
        if ! prompt_confirm "Continue anyway?" "n"; then
            error "Installation cancelled due to insufficient disk space"
        fi
    else
        log "Disk space: ${available_mb}MB available ✓"
    fi
}

check_network() {
    log "Checking network connectivity..."
    if command -v curl &>/dev/null; then
        if ! curl -s --connect-timeout 5 https://github.com >/dev/null 2>&1; then
            warn "Cannot reach GitHub. Check your internet connection."
            if ! prompt_confirm "Continue anyway?" "n"; then
                error "Installation cancelled due to network issues"
            fi
        else
            log "Network connectivity ✓"
        fi
    fi
}

detect_system() {
    log "Detecting system..."
    
    # Detect package manager
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt-get"
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
    elif command -v yum &>/dev/null; then
        PKG_MANAGER="yum"
    elif command -v apk &>/dev/null; then
        PKG_MANAGER="apk"
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
    elif command -v brew &>/dev/null; then
        PKG_MANAGER="brew"
    else
        error "Unsupported package manager. Please install manually."
    fi
    
    # Setup sudo if needed
    if [[ $EUID -ne 0 ]]; then
        if command -v sudo &>/dev/null; then
            SUDO="sudo"
            log "Running as user with sudo"
        else
            warn "Running as non-root without sudo - some operations may fail"
        fi
    else
        log "Running as root"
    fi
    
    log "System: $PKG_MANAGER"
}

prompt_input() {
    local prompt="$1"
    local default="$2"
    local is_secret="${3:-false}"
    local response
    
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        echo "$default"
        return
    fi
    
    if [[ "$is_secret" == "true" ]]; then
        echo -e "${YELLOW}$prompt${NC} (default: [hidden]): " >&2
        if [[ -t 0 ]]; then
            read -s response
        else
            read -s response < /dev/tty
        fi
        echo >&2
    else
        echo -e "${YELLOW}$prompt${NC} (default: $default): " >&2
        if [[ -t 0 ]]; then
            read response
        else
            read response < /dev/tty
        fi
    fi
    
    echo "${response:-$default}"
}

prompt_confirm() {
    local prompt="$1"
    local default="${2:-n}"
    
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        [[ "$default" == "y" ]] && return 0 || return 1
    fi
    
    local response
    echo -e "${YELLOW}$prompt [y/n]${NC} (default: $default): " >&2
    
    # Read from /dev/tty to handle piped input
    if [[ -t 0 ]]; then
        read response
    else
        read response < /dev/tty
    fi
    
    response="${response:-$default}"
    
    [[ "$response" =~ ^[Yy] ]]
}

# ============================================================================
# System Dependencies
# ============================================================================

check_installed() {
    local pkg="$1"
    case "$PKG_MANAGER" in
        apt-get)
            dpkg -l "$pkg" 2>/dev/null | grep -q '^ii' && return 0
            ;;
        dnf|yum)
            rpm -q "$pkg" &>/dev/null && return 0
            ;;
        apk)
            apk info -e "$pkg" &>/dev/null && return 0
            ;;
        pacman)
            pacman -Q "$pkg" &>/dev/null && return 0
            ;;
        brew)
            brew list "$pkg" &>/dev/null && return 0
            ;;
    esac
    return 1
}

install_system_deps() {
    if [[ "$SKIP_DEPS" == "true" ]]; then
        log "Skipping system dependencies (PANEL_SKIP_DEPS=true)"
        return 0
    fi
    
    log "Checking and installing system dependencies..."
    
    local to_install=()
    local deps_map=()
    
    case "$PKG_MANAGER" in
        apt-get)
            deps_map=("python3" "python3-pip" "python3-venv" "git" "curl" "wget" "redis-server" "nginx" "build-essential" "libssl-dev" "libffi-dev" "libpq-dev" "postgresql-client")
            for dep in "${deps_map[@]}"; do
                if ! check_installed "$dep"; then
                    to_install+=("$dep")
                fi
            done
            if [[ ${#to_install[@]} -gt 0 ]]; then
                log "Installing: ${to_install[*]}"
                $SUDO apt-get update -qq
                $SUDO apt-get install -y -qq "${to_install[@]}"
            else
                log "All apt dependencies already installed ✓"
            fi
            ;;
        dnf|yum)
            deps_map=("python3" "python3-pip" "python3-devel" "git" "curl" "wget" "redis" "nginx" "gcc" "openssl-devel" "libffi-devel" "postgresql-devel")
            for dep in "${deps_map[@]}"; do
                if ! check_installed "$dep"; then
                    to_install+=("$dep")
                fi
            done
            if [[ ${#to_install[@]} -gt 0 ]]; then
                log "Installing: ${to_install[*]}"
                $SUDO $PKG_MANAGER install -y -q "${to_install[@]}"
            else
                log "All dnf/yum dependencies already installed ✓"
            fi
            ;;
        apk)
            deps_map=("python3" "py3-pip" "git" "curl" "wget" "redis" "nginx" "gcc" "musl-dev" "linux-headers" "libffi-dev" "openssl-dev" "postgresql-dev")
            for dep in "${deps_map[@]}"; do
                if ! check_installed "$dep"; then
                    to_install+=("$dep")
                fi
            done
            if [[ ${#to_install[@]} -gt 0 ]]; then
                log "Installing: ${to_install[*]}"
                $SUDO apk add --no-cache "${to_install[@]}"
            else
                log "All apk dependencies already installed ✓"
            fi
            ;;
        pacman)
            deps_map=("python" "python-pip" "git" "curl" "wget" "redis" "nginx" "base-devel" "postgresql-libs")
            for dep in "${deps_map[@]}"; do
                if ! check_installed "$dep"; then
                    to_install+=("$dep")
                fi
            done
            if [[ ${#to_install[@]} -gt 0 ]]; then
                log "Installing: ${to_install[*]}"
                $SUDO pacman -S --noconfirm --needed "${to_install[@]}"
            else
                log "All pacman dependencies already installed ✓"
            fi
            ;;
        brew)
            deps_map=("python3" "git" "curl" "wget" "redis" "nginx" "postgresql")
            for dep in "${deps_map[@]}"; do
                if ! check_installed "$dep"; then
                    to_install+=("$dep")
                fi
            done
            if [[ ${#to_install[@]} -gt 0 ]]; then
                log "Installing: ${to_install[*]}"
                brew install "${to_install[@]}"
            else
                log "All brew dependencies already installed ✓"
            fi
            ;;
    esac
    
    # Configure and start Redis
    log "Configuring Redis server..."
    if command -v systemctl &>/dev/null; then
        # Enable Redis to start on boot
        $SUDO systemctl enable redis 2>/dev/null || $SUDO systemctl enable redis-server 2>/dev/null || true
        # Start Redis now
        $SUDO systemctl start redis 2>/dev/null || $SUDO systemctl start redis-server 2>/dev/null || true
        # Check if Redis is running
        if systemctl is-active --quiet redis 2>/dev/null || systemctl is-active --quiet redis-server 2>/dev/null; then
            log "Redis server started ✓"
        else
            warn "Redis server not started via systemctl, attempting alternative methods..."
            if command -v redis-server &>/dev/null; then
                redis-server --daemonize yes 2>/dev/null || true
            fi
        fi
    elif command -v service &>/dev/null; then
        $SUDO service redis start 2>/dev/null || $SUDO service redis-server start 2>/dev/null || true
    elif command -v redis-server &>/dev/null; then
        redis-server --daemonize yes 2>/dev/null || true
    fi
    
    # Verify Redis is accessible
    if command -v redis-cli &>/dev/null; then
        if redis-cli ping &>/dev/null; then
            log "Redis server is running and accessible ✓"
        else
            warn "Redis installed but not responding. You may need to start it manually."
        fi
    fi
    
    # Configure Nginx
    log "Configuring Nginx server..."
    if command -v nginx &>/dev/null; then
        # On Debian/Ubuntu, remove default site that conflicts with port 80
        if [[ "$PKG_MANAGER" == "apt-get" ]]; then
            if [[ -L "/etc/nginx/sites-enabled/default" ]]; then
                log "Removing default nginx site..."
                $SUDO rm -f /etc/nginx/sites-enabled/default
            fi
        fi
        
        # Test nginx configuration
        if $SUDO nginx -t 2>&1 | grep -q "successful"; then
            log "Nginx configuration valid ✓"
        else
            warn "Nginx configuration test failed, attempting to fix..."
            # Create basic nginx config if missing
            if [[ ! -f "/etc/nginx/nginx.conf" ]]; then
                warn "Missing nginx.conf - reinstalling nginx"
                case "$PKG_MANAGER" in
                    apt-get)
                        $SUDO apt-get install --reinstall -y nginx
                        ;;
                esac
            fi
        fi
        
        # Enable and start Nginx
        if command -v systemctl &>/dev/null; then
            $SUDO systemctl enable nginx 2>/dev/null || true
            # Stop nginx first to clear any errors
            $SUDO systemctl stop nginx 2>/dev/null || true
            sleep 1
            # Start nginx
            if $SUDO systemctl start nginx 2>&1; then
                sleep 1
                if systemctl is-active --quiet nginx; then
                    log "Nginx server started ✓"
                else
                    warn "Nginx failed to start. Checking status..."
                    $SUDO systemctl status nginx --no-pager -l 2>&1 | head -20 || true
                    warn "You may need to configure nginx manually"
                fi
            else
                warn "Failed to start nginx service"
            fi
        elif command -v service &>/dev/null; then
            $SUDO service nginx stop 2>/dev/null || true
            sleep 1
            if $SUDO service nginx start 2>&1; then
                log "Nginx server started ✓"
            else
                warn "Failed to start nginx via service command"
            fi
        fi
        
        # Verify nginx is listening
        sleep 2
        if command -v netstat &>/dev/null; then
            if netstat -tlnp 2>/dev/null | grep -q ":80.*nginx"; then
                log "Nginx is listening on port 80 ✓"
            else
                warn "Nginx may not be listening on port 80"
            fi
        fi
    fi
    
    log "System dependencies installed and configured"
}

# ============================================================================
# PostgreSQL Setup
# ============================================================================

setup_postgresql() {
    if [[ "$DB_TYPE" != "postgresql" ]]; then
        log "Using SQLite - skipping PostgreSQL setup"
        return 0
    fi
    
    if [[ "$SKIP_POSTGRESQL" == "true" ]]; then
        log "Skipping PostgreSQL setup (PANEL_SKIP_POSTGRESQL=true)"
        return 0
    fi
    
    log "Setting up PostgreSQL..."
    
    # Install PostgreSQL
    case "$PKG_MANAGER" in
        apt-get)
            $SUDO apt-get install -y -qq postgresql postgresql-contrib
            ;;
        dnf|yum)
            $SUDO $PKG_MANAGER install -y -q postgresql postgresql-server
            $SUDO postgresql-setup --initdb 2>/dev/null || true
            ;;
        apk)
            $SUDO apk add --no-cache postgresql postgresql-contrib
            $SUDO mkdir -p /run/postgresql
            $SUDO chown postgres:postgres /run/postgresql
            ;;
        pacman)
            $SUDO pacman -S --noconfirm --needed postgresql
            $SUDO -u postgres initdb -D /var/lib/postgres/data 2>/dev/null || true
            ;;
        brew)
            brew install postgresql
            ;;
    esac
    
    # Start PostgreSQL
    if command -v systemctl &>/dev/null; then
        $SUDO systemctl enable postgresql 2>/dev/null || true
        $SUDO systemctl start postgresql 2>/dev/null || true
    fi
    
    # Create database and user
    log "Creating PostgreSQL database..."
    
    if [[ -z "$DB_PASS" ]]; then
        DB_PASS=$(openssl rand -base64 16)
        log "Generated database password: $DB_PASS"
    fi
    
    $SUDO -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
    $SUDO -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
    $SUDO -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    
    log "PostgreSQL setup complete"
}

# ============================================================================
# Panel Installation
# ============================================================================

install_panel() {
    log "Installing Panel to $INSTALL_DIR..."
    
    # Check if critical ports are available
    log "Checking port availability..."
    if command -v netstat &>/dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
            warn "Port $APP_PORT is already in use"
            if ! prompt_confirm "Continue anyway?" "y"; then
                error "Installation cancelled"
            fi
        fi
        if [[ "$DB_TYPE" == "postgresql" ]] && netstat -tlnp 2>/dev/null | grep -q ":$DB_PORT "; then
            warn "PostgreSQL port $DB_PORT is already in use (this may be normal if PostgreSQL is already running)"
        fi
    fi
    
    # Clone repository
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "Directory exists: $INSTALL_DIR"
        if ! prompt_confirm "Remove existing installation?" "n"; then
            error "Installation cancelled"
        fi
        # Backup existing installation
        BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%s)"
        log "Creating backup: $BACKUP_DIR"
        mv "$INSTALL_DIR" "$BACKUP_DIR"
        log "Backup created. To restore: mv $BACKUP_DIR $INSTALL_DIR"
    fi
    
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    log "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip install --upgrade pip wheel setuptools
    
    # Try installing requirements, fallback to binary-only for psycopg2 on Python 3.13+
    if ! pip install -r requirements.txt 2>&1 | tee /tmp/pip_install.log; then
        warn "Initial pip install failed, trying with binary-only psycopg2..."
        # Install everything except psycopg2 first
        grep -v "psycopg2" requirements.txt > /tmp/requirements_no_psycopg2.txt
        pip install -r /tmp/requirements_no_psycopg2.txt
        # Then install psycopg2-binary from prebuilt wheel only
        pip install psycopg2-binary --only-binary :all: || {
            warn "Could not install prebuilt psycopg2-binary wheel"
            warn "Attempting to build from source (may fail on Python 3.13)..."
            pip install psycopg2-binary
        }
        rm -f /tmp/requirements_no_psycopg2.txt
    fi
    rm -f /tmp/pip_install.log
    
    # Create .env file
    log "Creating configuration..."
    
    cat > .env << EOF
# Panel Configuration - Generated $(date)
PANEL_SECRET_KEY=$(openssl rand -hex 32)
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=$DEBUG_MODE

# Database
$(if [[ "$DB_TYPE" == "postgresql" ]]; then
    echo "PANEL_USE_SQLITE=0"
    echo "PANEL_DB_HOST=$DB_HOST"
    echo "PANEL_DB_PORT=$DB_PORT"
    echo "PANEL_DB_NAME=$DB_NAME"
    echo "PANEL_DB_USER=$DB_USER"
    echo "PANEL_DB_PASS=$DB_PASS"
else
    echo "PANEL_USE_SQLITE=1"
    echo "PANEL_SQLITE_URI=sqlite:///instance/panel.db"
fi)

# Server
FLASK_HOST=$APP_HOST
FLASK_PORT=$APP_PORT

# Redis
PANEL_REDIS_URL=redis://127.0.0.1:6379/0

# Admin (for reference - actual user created in database)
# Admin Email: $ADMIN_EMAIL
# Admin Role: system_admin
PANEL_ADMIN_EMAILS=$ADMIN_EMAIL

# Logging
LOG_LEVEL=INFO
LOG_DIR=instance/logs
AUDIT_LOG_ENABLED=True
AUDIT_LOG_DIR=instance/audit_logs
EOF
    
    # Initialize database
    log "Initializing database..."
    python3 << 'PYEOF' || warn "Database initialization failed"
from app import app, db
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
PYEOF
    
    # Create admin user
    log "Creating admin user..."
    python3 << PYEOF || warn "Admin user creation failed"
import os
from datetime import datetime, date
from app import app, db, User
from werkzeug.security import generate_password_hash

try:
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(email='${ADMIN_EMAIL}').first()
        if not admin:
            # User model requires: first_name, last_name, email, dob, password_hash
            admin = User(
                first_name='Admin',
                last_name='User',
                email='${ADMIN_EMAIL}',
                dob=date(2000, 1, 1),  # Default DOB
                password_hash=generate_password_hash('${ADMIN_PASSWORD}'),
                role='system_admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user '{ADMIN_EMAIL}' created successfully with role 'system_admin'")
        else:
            print(f"Admin user '{ADMIN_EMAIL}' already exists")
except Exception as e:
    print(f"Could not create admin user: {e}")
    import traceback
    traceback.print_exc()
PYEOF
    
    # Configure nginx
    log "Configuring nginx..."
    if [[ -f "deploy/nginx_game_chrisvanek.conf" ]]; then
        sed "s/YOUR_DOMAIN_HERE/$DOMAIN/g" deploy/nginx_game_chrisvanek.conf > deploy/nginx_panel.conf
        log "Nginx configuration created: deploy/nginx_panel.conf"
    fi
    
    # Configure systemd service files
    log "Configuring systemd services..."
    if [[ -f "deploy/panel-gunicorn.service" ]]; then
        sed -e "s|/home/YOUR_USER/panel|$INSTALL_DIR|g" \
            -e "s|YOUR_USER|$USER|g" \
            deploy/panel-gunicorn.service > deploy/panel-gunicorn.service.configured
        log "Gunicorn service configured: deploy/panel-gunicorn.service.configured"
    fi
    
    if [[ -f "deploy/rq-worker.service" ]]; then
        sed -e "s|/home/YOUR_USER/panel|$INSTALL_DIR|g" \
            -e "s|YOUR_USER|$USER|g" \
            deploy/rq-worker.service > deploy/rq-worker.service.configured
        log "RQ worker service configured: deploy/rq-worker.service.configured"
    fi
    
    # Setup log rotation
    log "Configuring log rotation..."
    if [[ -f "deploy/panel-logrotate.conf" ]]; then
        if [[ -d "/etc/logrotate.d" ]] && [[ -n "$SUDO" ]]; then
            $SUDO cp deploy/panel-logrotate.conf /etc/logrotate.d/panel 2>/dev/null || \
                log "Log rotation setup skipped (requires sudo)"
        fi
    fi
    
    # Validate configuration
    log "Validating configuration..."
    if [[ ! -f ".env" ]]; then
        error "Configuration file (.env) was not created"
    fi
    
    # Save installation info
    cat > "$INSTALL_DIR/.install_info" << INFOEOF
# Panel Installation Info - $(date)
INSTALL_DATE=$(date -Iseconds)
INSTALL_DIR=$INSTALL_DIR
DB_TYPE=$DB_TYPE
DOMAIN=$DOMAIN
APP_PORT=$APP_PORT
ADMIN_EMAIL=$ADMIN_EMAIL
BRANCH=$BRANCH
INFOEOF
    
    # Save credentials securely (only readable by owner)
    if [[ "$DB_TYPE" == "postgresql" ]] && [[ -n "$DB_PASS" ]]; then
        cat > "$INSTALL_DIR/.db_credentials" << CREDEOF
# Database Credentials - KEEP SECURE
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASS=$DB_PASS
CREDEOF
        chmod 600 "$INSTALL_DIR/.db_credentials"
        log "Database credentials saved to: $INSTALL_DIR/.db_credentials (chmod 600)"
    fi
    
    log "Panel installation complete"
}

# ============================================================================
# Installation Verification
# ============================================================================

verify_installation() {
    log "Verifying installation..."
    local errors=0
    
    # Check .env file
    if [[ ! -f "$INSTALL_DIR/.env" ]]; then
        warn "Missing .env file"
        ((errors++))
    fi
    
    # Check venv
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        warn "Missing virtual environment"
        ((errors++))
    fi
    
    # Check app.py
    if [[ ! -f "$INSTALL_DIR/app.py" ]]; then
        warn "Missing app.py"
        ((errors++))
    fi
    
    # Check Python packages
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        cd "$INSTALL_DIR"
        if ! venv/bin/python -c "import flask" 2>/dev/null; then
            warn "Flask not properly installed"
            ((errors++))
        fi
    fi
    
    # Check database connection
    cd "$INSTALL_DIR"
    if ! venv/bin/python << 'PYEOF' 2>/dev/null
from dotenv import load_dotenv
load_dotenv()
from app import app, db
with app.app_context():
    db.engine.connect()
    print("Database connection successful")
PYEOF
    then
        warn "Database connection test failed"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log "Installation verification passed ✓"
        return 0
    else
        warn "Installation verification found $errors issue(s)"
        return 1
    fi
}

# ============================================================================
# Interactive Setup
# ============================================================================

interactive_setup() {
    echo
    echo -e "${BOLD}${MAGENTA}Configuration${NC}"
    echo
    
    log "Starting interactive configuration..."
    
    # Database type
    if prompt_confirm "Use PostgreSQL (production)? [n=SQLite]" "n"; then
        DB_TYPE="postgresql"
        log "PostgreSQL selected"
        DB_HOST=$(prompt_input "PostgreSQL host" "$DB_HOST")
        DB_PORT=$(prompt_input "PostgreSQL port" "$DB_PORT")
        DB_NAME=$(prompt_input "Database name" "$DB_NAME")
        DB_USER=$(prompt_input "Database user" "$DB_USER")
        DB_PASS=$(prompt_input "Database password" "" "true")
    else
        DB_TYPE="sqlite"
        log "SQLite selected"
    fi
    
    echo
    INSTALL_DIR=$(prompt_input "Installation directory" "$INSTALL_DIR")
    log "Installation directory: $INSTALL_DIR"
    
    echo
    echo -e "${YELLOW}Domain/Hostname Configuration${NC}" >&2
    echo -e "${YELLOW}Enter the domain or IP address where Panel will be accessible${NC}" >&2
    echo -e "${YELLOW}Examples: panel.example.com, 192.168.1.100, localhost${NC}" >&2
    DOMAIN=$(prompt_input "Domain/IP address" "localhost")
    log "Domain/hostname: $DOMAIN"
    
    echo
    echo -e "${YELLOW}Admin Account Setup${NC}" >&2
    echo -e "${YELLOW}This will create a system administrator account${NC}" >&2
    ADMIN_EMAIL=$(prompt_input "Admin email address" "$ADMIN_EMAIL")
    ADMIN_PASSWORD=$(prompt_input "Admin password" "" "true")
    
    log "Interactive configuration complete"
}

# ============================================================================
# Main Installation Flow
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            --sqlite)
                DB_TYPE="sqlite"
                shift
                ;;
            --postgresql)
                DB_TYPE="postgresql"
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE="true"
                shift
                ;;
            --skip-deps)
                SKIP_DEPS="true"
                shift
                ;;
            --skip-postgresql)
                SKIP_POSTGRESQL="true"
                shift
                ;;
            --verify-only)
                # Just verify existing installation
                if [[ -d "$INSTALL_DIR" ]]; then
                    cd "$INSTALL_DIR"
                    verify_installation
                    exit $?
                else
                    error "No installation found at $INSTALL_DIR"
                fi
                ;;
            --update)
                # Update existing installation
                if [[ -d "$INSTALL_DIR" ]]; then
                    log "Updating existing installation at $INSTALL_DIR"
                    cd "$INSTALL_DIR"
                    
                    # Backup current version
                    BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%s)"
                    log "Creating backup: $BACKUP_DIR"
                    cp -r "$INSTALL_DIR" "$BACKUP_DIR"
                    
                    # Pull latest changes
                    git pull origin main
                    
                    # Update dependencies
                    source venv/bin/activate
                    pip install --upgrade -r requirements.txt
                    
                    # Run migrations if needed
                    if command -v flask &>/dev/null; then
                        flask db upgrade 2>/dev/null || true
                    fi
                    
                    log "Update complete"
                    exit 0
                else
                    error "No installation found at $INSTALL_DIR"
                fi
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

main() {
    parse_args "$@"
    
    echo
    echo -e "${BOLD}${MAGENTA}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${MAGENTA}║         Panel Installer v3.0              ║${NC}"
    echo -e "${BOLD}${MAGENTA}║         PostgreSQL Edition                ║${NC}"
    echo -e "${BOLD}${MAGENTA}╚═══════════════════════════════════════════╝${NC}"
    echo
    
    detect_system
    
    log "NON_INTERACTIVE=$NON_INTERACTIVE"
    
    if [[ "$NON_INTERACTIVE" != "true" ]]; then
        log "Running interactive setup..."
        interactive_setup
    else
        log "Skipping interactive setup (non-interactive mode)"
    fi
    
    # Pre-installation checks
    echo
    log "Running pre-installation checks..."
    check_python_version
    check_disk_space
    check_network
    echo
    
    # Install and configure system dependencies BEFORE panel installation
    install_system_deps
    
    # Verify critical services are running before proceeding
    log "Verifying critical services..."
    
    # Check Redis
    if ! pgrep -x redis-server > /dev/null 2>&1; then
        warn "Redis is not running. Attempting to start..."
        if command -v systemctl &>/dev/null; then
            $SUDO systemctl start redis 2>/dev/null || $SUDO systemctl start redis-server 2>/dev/null || true
        fi
        sleep 2
        if ! pgrep -x redis-server > /dev/null 2>&1; then
            error "Redis failed to start. Please start it manually: sudo systemctl start redis"
        fi
    fi
    log "Redis is running ✓"
    
    # Check Nginx - REQUIRED for production
    if command -v nginx &>/dev/null; then
        if ! systemctl is-active --quiet nginx 2>/dev/null && ! pgrep nginx > /dev/null 2>&1; then
            warn "Nginx is not running. Attempting to start..."
            if command -v systemctl &>/dev/null; then
                $SUDO systemctl start nginx 2>/dev/null || true
            elif command -v service &>/dev/null; then
                $SUDO service nginx start 2>/dev/null || true
            fi
            sleep 2
            # Verify again
            if ! systemctl is-active --quiet nginx 2>/dev/null && ! pgrep nginx > /dev/null 2>&1; then
                error "Nginx failed to start. Please check nginx configuration and start it manually: sudo systemctl start nginx"
            fi
        fi
        log "Nginx is running ✓"
    else
        warn "Nginx is not installed. For production use, install nginx manually."
    fi
    
    echo
    
    setup_postgresql
    install_panel
    verify_installation
    
    echo
    echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   Installation Complete!                  ║${NC}"
    echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${GREEN}Database Type:${NC} $DB_TYPE"
    echo -e "${GREEN}Domain:${NC} $DOMAIN"
    echo -e "${GREEN}Admin Email:${NC} $ADMIN_EMAIL"
    echo -e "${GREEN}Admin Role:${NC} system_admin"
    if [[ -f "$INSTALL_DIR/.db_credentials" ]]; then
        echo -e "${YELLOW}Database credentials saved:${NC} $INSTALL_DIR/.db_credentials"
    fi
    if [[ -n "$BACKUP_DIR" ]] && [[ -d "$BACKUP_DIR" ]]; then
        echo -e "${YELLOW}Previous installation backed up:${NC} $BACKUP_DIR"
    fi
    echo
    
    # Ask if user wants to start the panel now
    if [[ "$NON_INTERACTIVE" != "true" ]]; then
        echo -e "${YELLOW}Would you like to start the Panel now? (y/n)${NC}" >&2
        read -r -p "> " START_NOW < /dev/tty || START_NOW="n"
        
        if [[ "$START_NOW" =~ ^[Yy] ]]; then
            echo
            echo -e "${GREEN}Starting Panel services...${NC}"
            
            # Check if Redis is running, start if needed
            if ! pgrep -x redis-server > /dev/null 2>&1; then
                echo -e "${YELLOW}Starting Redis...${NC}"
                if command -v systemctl &>/dev/null; then
                    $SUDO systemctl start redis 2>/dev/null || $SUDO systemctl start redis-server 2>/dev/null || true
                elif command -v service &>/dev/null; then
                    $SUDO service redis start 2>/dev/null || $SUDO service redis-server start 2>/dev/null || true
                else
                    redis-server --daemonize yes 2>/dev/null || true
                fi
                sleep 1
            fi
            
            # Verify Redis is running
            if ! pgrep -x redis-server > /dev/null 2>&1; then
                warn "Redis is not running. Background worker may fail."
                echo -e "${YELLOW}To start Redis manually:${NC}"
                echo "  sudo systemctl start redis"
                echo "  # or"
                echo "  redis-server --daemonize yes"
            else
                echo -e "${GREEN}✓ Redis is running${NC}"
            fi
            
            # Start worker in background
            cd "$INSTALL_DIR" || exit 1
            source venv/bin/activate
            
            # Create logs and instance directories if they don't exist
            mkdir -p logs instance/logs instance/audit_logs instance/backups
            
            # Start worker
            echo -e "${YELLOW}Starting background worker...${NC}"
            nohup python3 run_worker.py > logs/worker.log 2>&1 &
            WORKER_PID=$!
            echo -e "${GREEN}Worker started with PID: $WORKER_PID${NC}"
            
            # Start web server
            echo -e "${YELLOW}Starting web server...${NC}"
            nohup python3 app.py > logs/panel.log 2>&1 &
            SERVER_PID=$!
            echo -e "${GREEN}Web server started with PID: $SERVER_PID${NC}"
            
            # Wait for services to initialize (Flask debug mode takes longer)
            echo -e "${YELLOW}Waiting for services to initialize...${NC}"
            sleep 5
            
            # Check if Panel is actually running (check for python process, not just PID)
            # Flask debug mode spawns child processes, so we check for the actual app.py process
            PANEL_RUNNING=false
            RETRY_COUNT=0
            MAX_RETRIES=3
            
            while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
                if pgrep -f "python3 app.py" > /dev/null 2>&1 || pgrep -f "python.*app.py" > /dev/null 2>&1; then
                    PANEL_RUNNING=true
                    break
                fi
                RETRY_COUNT=$((RETRY_COUNT + 1))
                if [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; then
                    echo -e "${YELLOW}Checking process status... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)${NC}"
                    sleep 2
                fi
            done
            
            if [[ "$PANEL_RUNNING" == "true" ]]; then
                # Get actual PIDs
                ACTUAL_SERVER_PIDS=$(pgrep -f "python.*app.py" | tr '\n' ' ')
                ACTUAL_WORKER_PIDS=$(pgrep -f "python.*run_worker.py" | tr '\n' ' ')
                
                # Health check
                log "Performing health check..."
                sleep 2
                if command -v curl &>/dev/null; then
                    if curl -f -s http://localhost:$APP_PORT/health >/dev/null 2>&1 || \
                       curl -f -s http://localhost:$APP_PORT/ >/dev/null 2>&1; then
                        echo -e "${GREEN}✓ Panel health check passed${NC}"
                    else
                        warn "Panel health check failed (but process is running)"
                    fi
                fi
                
                echo
                echo -e "${BOLD}${GREEN}✓ Panel is now running!${NC}"
                echo
                echo -e "${GREEN}Access Panel:${NC}"
                echo -e "  URL: ${BOLD}http://$DOMAIN:$APP_PORT${NC}"
                echo -e "  Email: ${BOLD}$ADMIN_EMAIL${NC}"
                echo -e "  Password: ${BOLD}[set during installation]${NC}"
                echo -e "  Role: ${BOLD}system_admin${NC}"
                echo
                echo -e "${YELLOW}Running Processes:${NC}"
                echo "  Panel PIDs: $ACTUAL_SERVER_PIDS"
                echo "  Worker PIDs: $ACTUAL_WORKER_PIDS"
                echo
                echo -e "${YELLOW}To view logs:${NC}"
                echo "  Panel: tail -f $INSTALL_DIR/logs/panel.log"
                echo "  Worker: tail -f $INSTALL_DIR/logs/worker.log"
                echo
                echo -e "${YELLOW}To stop the Panel:${NC}"
                echo "  pkill -f 'python.*app.py'"
                echo "  pkill -f 'python.*run_worker.py'"
            else
                echo
                echo -e "${YELLOW}⚠ Panel startup taking longer than expected${NC}"
                echo
                if [[ -f "$INSTALL_DIR/logs/panel.log" ]]; then
                    echo -e "${YELLOW}Last 30 lines from panel.log:${NC}"
                    tail -30 "$INSTALL_DIR/logs/panel.log"
                    echo
                    echo -e "${GREEN}If you see initialization messages above, the Panel is starting.${NC}"
                    echo -e "${GREEN}Wait a few seconds and check: http://$DOMAIN:$APP_PORT${NC}"
                else
                    echo "  Log file not created: $INSTALL_DIR/logs/panel.log"
                    echo "  Try starting manually:"
                    echo "    cd $INSTALL_DIR"
                    echo "    source venv/bin/activate"
                    echo "    python3 app.py"
                fi
            fi
        else
            echo
            echo -e "${YELLOW}To start the Panel manually:${NC}"
            echo "  cd $INSTALL_DIR"
            echo "  source venv/bin/activate"
            echo "  nohup python3 run_worker.py > logs/worker.log 2>&1 &"
            echo "  nohup python3 app.py > logs/panel.log 2>&1 &"
            echo
            echo -e "${GREEN}Access Panel (once started):${NC}"
            echo -e "  URL: ${BOLD}http://$DOMAIN:$APP_PORT${NC}"
            echo -e "  Email: ${BOLD}$ADMIN_EMAIL${NC}"
            echo
        fi
    else
        # Non-interactive mode - show manual start instructions
        echo -e "${YELLOW}To start the Panel:${NC}"
        echo "  cd $INSTALL_DIR"
        echo "  source venv/bin/activate"
        echo "  nohup python3 run_worker.py > logs/worker.log 2>&1 &"
        echo "  nohup python3 app.py > logs/panel.log 2>&1 &"
        echo
        echo -e "${GREEN}Access Panel (once started):${NC}"
        echo -e "  URL: ${BOLD}http://$DOMAIN:$APP_PORT${NC}"
        echo -e "  Email: ${BOLD}$ADMIN_EMAIL${NC}"
        echo
    fi
    
    echo -e "${GREEN}Database Admin UI:${NC}"
    echo "  http://$DOMAIN:$APP_PORT/admin/database"
    echo
    echo -e "${BOLD}${YELLOW}📋 Next Steps:${NC}"
    echo
    echo -e "${YELLOW}1. Start the Panel:${NC}"
    echo "   cd $INSTALL_DIR"
    echo "   source venv/bin/activate"
    echo "   python3 app.py"
    echo
    echo -e "${YELLOW}2. Access the Panel:${NC}"
    echo "   http://$DOMAIN:$APP_PORT"
    echo "   Login with: $ADMIN_EMAIL"
    echo
    echo -e "${YELLOW}3. For Production (Optional):${NC}"
    echo "   - Setup systemd services (see instructions below)"
    echo "   - Configure nginx reverse proxy"
    echo "   - Setup SSL with Let's Encrypt"
    echo "   - Configure firewall rules"
    echo
    echo -e "${YELLOW}Production Setup:${NC}"
    echo "  For production, set up systemd services and nginx:"
    echo
    echo "  # Setup Gunicorn service"
    if [[ -f "$INSTALL_DIR/deploy/panel-gunicorn.service.configured" ]]; then
        echo "  sudo cp $INSTALL_DIR/deploy/panel-gunicorn.service.configured /etc/systemd/system/panel-gunicorn.service"
    else
        echo "  sudo cp $INSTALL_DIR/deploy/panel-gunicorn.service /etc/systemd/system/"
        echo "  # Edit /etc/systemd/system/panel-gunicorn.service to set correct paths"
    fi
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable panel-gunicorn"
    echo "  sudo systemctl start panel-gunicorn"
    echo
    echo "  # Setup RQ Worker service"
    if [[ -f "$INSTALL_DIR/deploy/rq-worker.service.configured" ]]; then
        echo "  sudo cp $INSTALL_DIR/deploy/rq-worker.service.configured /etc/systemd/system/rq-worker.service"
    else
        echo "  sudo cp $INSTALL_DIR/deploy/rq-worker.service /etc/systemd/system/"
        echo "  # Edit /etc/systemd/system/rq-worker.service to set correct paths"
    fi
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable rq-worker"
    echo "  sudo systemctl start rq-worker"
    echo
    echo "  # Setup Nginx reverse proxy (configured for: $DOMAIN)"
    if [[ -f "$INSTALL_DIR/deploy/nginx_panel.conf" ]]; then
        case "$PKG_MANAGER" in
            apt-get)
                echo "  sudo cp $INSTALL_DIR/deploy/nginx_panel.conf /etc/nginx/sites-available/panel"
                echo "  sudo ln -s /etc/nginx/sites-available/panel /etc/nginx/sites-enabled/"
                ;;
            *)
                echo "  sudo cp $INSTALL_DIR/deploy/nginx_panel.conf /etc/nginx/conf.d/panel.conf"
                ;;
        esac
    else
        echo "  # Nginx config needs domain configuration"
        case "$PKG_MANAGER" in
            apt-get)
                echo "  sudo cp $INSTALL_DIR/deploy/nginx_game_chrisvanek.conf /etc/nginx/sites-available/panel"
                echo "  sudo ln -s /etc/nginx/sites-available/panel /etc/nginx/sites-enabled/"
                ;;
            *)
                echo "  sudo cp $INSTALL_DIR/deploy/nginx_game_chrisvanek.conf /etc/nginx/conf.d/panel.conf"
                ;;
        esac
    fi
    echo "  sudo nginx -t"
    echo "  sudo systemctl enable nginx"
    echo "  sudo systemctl restart nginx"
    echo
    echo "  # Setup SSL with Let's Encrypt (optional)"
    case "$PKG_MANAGER" in
        apt-get)
            echo "  sudo apt install certbot python3-certbot-nginx"
            ;;
        dnf|yum)
            echo "  sudo $PKG_MANAGER install certbot python3-certbot-nginx"
            ;;
        apk)
            echo "  sudo apk add certbot certbot-nginx"
            ;;
        pacman)
            echo "  sudo pacman -S certbot certbot-nginx"
            ;;
        brew)
            echo "  brew install certbot"
            ;;
    esac
    echo "  sudo certbot --nginx -d $DOMAIN"
    echo
    echo "  # Open firewall ports (if firewall is active)"
    echo "  sudo ufw allow 80/tcp   # HTTP"
    echo "  sudo ufw allow 443/tcp  # HTTPS"
    echo "  sudo ufw allow 8080/tcp # Panel (if not using nginx proxy)"
    echo
}

# ============================================================================
# Execute
# ============================================================================

main "$@"
