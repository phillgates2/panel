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

ADMIN_USERNAME="${PANEL_ADMIN_USER:-admin}"
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
    PANEL_ADMIN_USER        Admin username (default: admin)
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
    PANEL_ADMIN_PASS=adminpass \
    curl -fsSL .../install.sh | bash

    # Custom directory
    bash install.sh --dir /opt/panel

    # Development with SQLite
    bash install.sh --sqlite --dir ~/panel-dev

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

install_system_deps() {
    if [[ "$SKIP_DEPS" == "true" ]]; then
        log "Skipping system dependencies (PANEL_SKIP_DEPS=true)"
        return 0
    fi
    
    log "Installing system dependencies..."
    
    case "$PKG_MANAGER" in
        apt-get)
            $SUDO apt-get update -qq
            $SUDO apt-get install -y -qq \
                python3 python3-pip python3-venv \
                git curl wget \
                redis-server \
                build-essential libssl-dev libffi-dev
            ;;
        dnf|yum)
            $SUDO $PKG_MANAGER install -y -q \
                python3 python3-pip python3-devel \
                git curl wget \
                redis \
                gcc openssl-devel libffi-devel
            ;;
        apk)
            $SUDO apk add --no-cache \
                python3 py3-pip \
                git curl wget \
                redis \
                gcc musl-dev linux-headers libffi-dev openssl-dev
            ;;
        pacman)
            $SUDO pacman -S --noconfirm --needed \
                python python-pip \
                git curl wget \
                redis \
                base-devel
            ;;
        brew)
            brew install python3 git curl wget redis
            ;;
    esac
    
    log "System dependencies installed"
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
    
    # Clone repository
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "Directory exists: $INSTALL_DIR"
        if ! prompt_confirm "Remove existing installation?" "n"; then
            error "Installation cancelled"
        fi
        rm -rf "$INSTALL_DIR"
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
    pip install -r requirements.txt
    
    # Create .env file
    log "Creating configuration..."
    
    cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
FLASK_APP=app.py
FLASK_ENV=production
DEBUG=$DEBUG_MODE

# Database
$(if [[ "$DB_TYPE" == "postgresql" ]]; then
    echo "SQLALCHEMY_DATABASE_URI=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
else
    echo "SQLALCHEMY_DATABASE_URI=sqlite:///instance/panel.db"
fi)

# Server
HOST=$APP_HOST
PORT=$APP_PORT
DOMAIN=${DOMAIN:-localhost}

# Admin
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF
    
    # Initialize database
    log "Initializing database..."
    python3 << 'PYEOF' || warn "Database initialization failed"
from app import app, db
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
PYEOF
    
    log "Panel installation complete"
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
    ADMIN_USERNAME=$(prompt_input "Admin username" "$ADMIN_USERNAME")
    ADMIN_EMAIL=$(prompt_input "Admin email" "$ADMIN_EMAIL")
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
    
    install_system_deps
    setup_postgresql
    install_panel
    
    echo
    echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   Installation Complete!                  ║${NC}"
    echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${GREEN}Database Type:${NC} $DB_TYPE"
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
                
                echo
                echo -e "${BOLD}${GREEN}✓ Panel is now running!${NC}"
                echo
                echo -e "${GREEN}Access Panel:${NC}"
                echo -e "  URL: ${BOLD}http://$DOMAIN:$APP_PORT${NC}"
                echo -e "  Username: ${BOLD}$ADMIN_USERNAME${NC}"
                echo -e "  Password: ${BOLD}[set during installation]${NC}"
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
            echo -e "  Username: ${BOLD}$ADMIN_USERNAME${NC}"
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
        echo -e "  Username: ${BOLD}$ADMIN_USERNAME${NC}"
        echo
    fi
    
    echo -e "${GREEN}Database Admin UI:${NC}"
    echo "  http://$DOMAIN:$APP_PORT/admin/database"
    echo
    echo -e "${YELLOW}Production Setup:${NC}"
    echo "  For production, set up systemd services:"
    echo "  sudo cp $INSTALL_DIR/deploy/panel-gunicorn.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable panel-gunicorn"
    echo "  sudo systemctl start panel-gunicorn"
    echo
}

# ============================================================================
# Execute
# ============================================================================

main "$@"
