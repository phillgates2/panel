#!/bin/bash
# ============================================================================
# Panel Application Installer
# Interactive and Comprehensive Installation Script
# ============================================================================
#
# This script provides a complete, interactive installation experience for
# the Panel application with support for multiple deployment scenarios.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
#   wget -qO- https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
#
# WARNING: Always review scripts before piping to bash for security!
#
# ============================================================================

set -euo pipefail

# ============================================================================
# Configuration Variables
# ============================================================================

# Repository settings
readonly REPO_URL="https://github.com/phillgates2/panel.git"
readonly REPO_BRANCH="${PANEL_BRANCH:-main}"

# Installation paths (can be overridden via environment variables)
INSTALL_DIR="${PANEL_INSTALL_DIR:-/opt/panel}"
CONFIG_DIR="${PANEL_CONFIG_DIR:-/etc/panel}"
DATA_DIR="${PANEL_DATA_DIR:-/var/lib/panel}"
LOG_DIR="${PANEL_LOG_DIR:-/var/log/panel}"
BACKUP_DIR="${PANEL_BACKUP_DIR:-/var/backups/panel}"
SSL_DIR="${PANEL_SSL_DIR:-/etc/ssl/panel}"

# Runtime settings
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="$(basename "$0")"
START_TIME=$(date +%s)

# ============================================================================
# Color and Formatting Functions
# ============================================================================

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Emoji indicators
readonly CHECK_MARK="?"
readonly CROSS_MARK="?"
readonly WARNING="??"
readonly INFO="??"
readonly GEAR="??"
readonly ROCKET="??"
readonly LOCK="??"
readonly DATABASE="???"
readonly GLOBE="??"

# ============================================================================
# Logging and Output Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}${INFO}${NC} $1"
}

log_success() {
    echo -e "${GREEN}${CHECK_MARK}${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}${WARNING}${NC} $1"
}

log_error() {
    echo -e "${RED}${CROSS_MARK}${NC} $1" >&2
}

log_header() {
    echo
    echo -e "${PURPLE}${BOLD}================================${NC}"
    echo -e "${PURPLE}${BOLD}$1${NC}"
    echo -e "${PURPLE}${BOLD}================================${NC}"
    echo
}

log_step() {
    echo -e "${CYAN}${GEAR}${NC} $1"
}

log_complete() {
    echo -e "${GREEN}${ROCKET}${NC} $1"
}

# Progress indicator
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local percentage=$((current * 100 / total))
    local progress_bar=""

    # Create progress bar
    for ((i=0; i<50; i++)); do
        if ((i < percentage / 2)); then
            progress_bar+="#"
        else
            progress_bar+=" "
        fi
    done

    printf "\r${CYAN}[%-50s] %d%%${NC} %s" "$progress_bar" "$percentage" "$message"
}

# ============================================================================
# Utility Functions
# ============================================================================

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This will install system-wide."
        echo
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installation cancelled by user."
            exit 0
        fi
    fi
}

# Detect operating system and version
detect_os() {
    log_step "Detecting operating system..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v lsb_release >/dev/null 2>&1; then
            OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
            OS_VERSION=$(lsb_release -sr)
            OS_CODENAME=$(lsb_release -sc)
        elif [[ -f /etc/os-release ]]; then
            # shellcheck source=/dev/null
            . /etc/os-release
            OS=${ID,,}
            OS_VERSION=$VERSION_ID
            OS_CODENAME=${VERSION_CODENAME:-}
        elif [[ -f /etc/redhat-release ]]; then
            OS="rhel"
            OS_VERSION=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release | head -1)
        else
            OS=$(uname -s | tr '[:upper:]' '[:lower:]')
            OS_VERSION=$(uname -r)
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
        OS_VERSION=$(uname -r)
    else
        OS="unknown"
        OS_VERSION="unknown"
    fi

    log_success "Detected: $OS $OS_VERSION"
}

# Check system requirements
check_requirements() {
    log_header "System Requirements Check"

    local requirements_met=true

    # Check available memory
    if command -v free >/dev/null 2>&1; then
        local mem_kb
        mem_kb=$(free | awk 'NR==2{print $2}')
        local mem_gb=$((mem_kb / 1024 / 1024))

        if [[ $mem_gb -lt 2 ]]; then
            log_error "Insufficient memory: ${mem_gb}GB. Minimum 2GB required."
            requirements_met=false
        else
            log_success "Memory: ${mem_gb}GB"
        fi
    elif [[ "$OS" == "macos" ]]; then
        # macOS memory check
        local mem_gb
        mem_gb=$(echo "$(sysctl -n hw.memsize) / 1024 / 1024 / 1024" | bc)
        if [[ $mem_gb -lt 2 ]]; then
            log_error "Insufficient memory: ${mem_gb}GB. Minimum 2GB required."
            requirements_met=false
        else
            log_success "Memory: ${mem_gb}GB"
        fi
    fi

    # Check available disk space
    local disk_kb
    disk_kb=$(df "$PWD" | tail -1 | awk '{print $4}')
    local disk_gb=$((disk_kb / 1024 / 1024))

    if [[ $disk_gb -lt 5 ]]; then
        log_error "Insufficient disk space: ${disk_gb}GB. Minimum 5GB required."
        requirements_met=false
    else
        log_success "Disk space: ${disk_gb}GB available"
    fi

    # Check CPU cores
    local cpu_cores
    if command -v nproc >/dev/null 2>&1; then
        cpu_cores=$(nproc)
    elif [[ "$OS" == "macos" ]]; then
        cpu_cores=$(sysctl -n hw.ncpu | awk '{print $2}')
    else
        cpu_cores=1
    fi

    if [[ $cpu_cores -lt 1 ]]; then
        log_warning "Low CPU cores: $cpu_cores. Performance may be limited."
    else
        log_success "CPU cores: $cpu_cores"
    fi

    # Check required commands
    local required_commands=("curl" "git" "python3" "pip3")
    local missing_commands=()

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done

    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        echo
        log_info "Installation instructions:"
        echo "  Ubuntu/Debian: sudo apt-get install curl git python3 python3-pip"
        echo "  CentOS/RHEL: sudo yum install curl git python3 python3-pip"
        echo "  macOS: brew install curl git python3"
        echo "  Python: Download from https://python.org"
        requirements_met=false
    else
        log_success "All required commands found"
    fi

    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        local python_version
        python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            log_success "Python version: $python_version"
        else
            log_error "Python 3.8+ required. Found: $python_version"
            log_info "Please upgrade Python from https://python.org"
            requirements_met=false
        fi
    else
        log_error "Python 3 not found"
        requirements_met=false
    fi

    # Check internet connectivity
    if curl -s --connect-timeout 5 https://github.com >/dev/null 2>&1; then
        log_success "Internet connectivity: OK"
    else
        log_error "No internet connectivity detected"
        requirements_met=false
    fi

    if [[ $requirements_met == false ]]; then
        log_error "System requirements not met. Please resolve the issues above and try again."
        exit 1
    fi

    log_success "All system requirements met!"
}

# ============================================================================
# Interactive Configuration Functions
# ============================================================================

# Main configuration menu
interactive_config() {
    log_header "Panel Configuration Setup"

    echo -e "${CYAN}${BOLD}Welcome to the Panel Application Installer!${NC}"
    echo
    echo "This installer will guide you through setting up Panel with:"
    echo "  • Database configuration (SQLite/PostgreSQL/MySQL)"
    echo "  • Redis caching (optional)"
    echo "  • AI features (optional)"
    echo "  • SSL/HTTPS setup (optional)"
    echo "  • Production or development deployment"
    echo
    echo -e "${YELLOW}Press Enter to accept defaults, or type your preferred values.${NC}"
    echo

    # Installation directory
    while true; do
        read -p "Installation directory [$INSTALL_DIR]: " input
        INSTALL_DIR=${input:-$INSTALL_DIR}

        if [[ -d "$INSTALL_DIR" ]] && [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
            echo
            log_warning "Directory $INSTALL_DIR already exists and is not empty."
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        else
            break
        fi
    done

    # Domain name
    read -p "Domain name (leave empty for localhost): " DOMAIN_NAME

    # Deployment environment
    echo
    echo "Deployment Environment:"
    echo "1) Development (debug mode, local access)"
    echo "2) Production (optimized, secure)"
    echo "3) Staging (production-like testing)"
    read -p "Choose deployment type [1]: " -n 1 -r
    echo
    case $REPLY in
        2)
            DEPLOYMENT_TYPE="production"
            ;;
        3)
            DEPLOYMENT_TYPE="staging"
            ;;
        *)
            DEPLOYMENT_TYPE="development"
            ;;
    esac

    # Database configuration
    configure_database

    # Redis configuration
    configure_redis

    # AI features configuration
    configure_ai

    # SSL configuration
    configure_ssl

    # Additional features
    configure_features

    log_success "Configuration completed successfully!"
}

# Database configuration
configure_database() {
    log_step "Configuring database..."

    echo
    echo "Database Options:"
    echo "1) SQLite (simple, no setup required - recommended for testing)"
    echo "2) PostgreSQL (recommended for production)"
    echo "3) MySQL/MariaDB (alternative production option)"
    read -p "Choose database [1]: " -n 1 -r
    echo

    case $REPLY in
        2)
            DB_TYPE="postgresql"
            ;;
        3)
            DB_TYPE="mysql"
            ;;
        *)
            DB_TYPE="sqlite"
            ;;
    esac

    # Database-specific configuration
    case $DB_TYPE in
        postgresql)
            echo "PostgreSQL Configuration:"
            read -p "Host [localhost]: " DB_HOST
            DB_HOST=${DB_HOST:-localhost}
            read -p "Port [5432]: " DB_PORT
            DB_PORT=${DB_PORT:-5432}
            read -p "Database name [panel]: " DB_NAME
            DB_NAME=${DB_NAME:-panel}
            read -p "Username [panel]: " DB_USER
            DB_USER=${DB_USER:-panel}
            read -s -p "Password: " DB_PASSWORD
            echo
            read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
            echo

            if [[ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]]; then
                log_error "Passwords do not match"
                exit 1
            fi
            ;;
        mysql)
            echo "MySQL Configuration:"
            read -p "Host [localhost]: " DB_HOST
            DB_HOST=${DB_HOST:-localhost}
            read -p "Port [3306]: " DB_PORT
            DB_PORT=${DB_PORT:-3306}
            read -p "Database name [panel]: " DB_NAME
            DB_NAME=${DB_NAME:-panel}
            read -p "Username [panel]: " DB_USER
            DB_USER=${DB_USER:-panel}
            read -s -p "Password: " DB_PASSWORD
            echo
            read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
            echo

            if [[ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]]; then
                log_error "Passwords do not match"
                exit 1
            fi
            ;;
        sqlite)
            log_info "SQLite selected - no additional configuration needed"
            ;;
    esac
}

# Redis configuration
configure_redis() {
    echo
    read -p "Enable Redis for caching and sessions? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        USE_REDIS=true
        echo "Redis Configuration:"
        read -p "Redis host [localhost]: " REDIS_HOST
        REDIS_HOST=${REDIS_HOST:-localhost}
        read -p "Redis port [6379]: " REDIS_PORT
        REDIS_PORT=${REDIS_PORT:-6379}
        read -p "Redis database [0]: " REDIS_DB
        REDIS_DB=${REDIS_DB:-0}
        read -s -p "Redis password (leave empty if no password): " REDIS_PASSWORD
        echo
    else
        USE_REDIS=false
        log_info "Redis disabled - using in-memory caching"
    fi
}

# AI features configuration
configure_ai() {
    echo
    echo "AI Features (optional):"
    read -p "Enable AI-powered features? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ENABLE_AI=true

        echo "AI Chat Assistant:"
        read -p "Enable AI chat assistant? (y/N): " -n 1 -r
        echo
        ENABLE_AI_CHAT=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

        if [[ $ENABLE_AI_CHAT == true ]]; then
            echo "AI Provider Options:"
            echo "1) Azure OpenAI (recommended - secure, enterprise)"
            echo "2) Google Vertex AI (Google Cloud)"
            echo "3) OpenAI API (direct API access)"
            echo "4) Local AI (Ollama, requires local setup)"
            read -p "Choose AI provider [1]: " -n 1 -r
            echo

            case $REPLY in
                2)
                    AI_PROVIDER="google"
                    read -p "Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT
                    read -p "Google Cloud Region [us-central1]: " GOOGLE_CLOUD_REGION
                    GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION:-us-central1}
                    ;;
                3)
                    AI_PROVIDER="openai"
                    read -p "OpenAI API Key: " OPENAI_API_KEY
                    ;;
                4)
                    AI_PROVIDER="local"
                    read -p "Ollama host [localhost]: " OLLAMA_HOST
                    OLLAMA_HOST=${OLLAMA_HOST:-localhost}
                    read -p "Ollama port [11434]: " OLLAMA_PORT
                    OLLAMA_PORT=${OLLAMA_PORT:-11434}
                    ;;
                *)
                    AI_PROVIDER="azure"
                    read -p "Azure OpenAI Endpoint: " AZURE_OPENAI_ENDPOINT
                    read -p "Azure OpenAI API Key: " AZURE_OPENAI_API_KEY
                    read -p "Azure OpenAI Deployment Name [gpt-4]: " AZURE_OPENAI_DEPLOYMENT
                    AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-4}
                    ;;
            esac
        fi

        echo "Voice Analysis:"
        read -p "Enable voice analysis features? (y/N): " -n 1 -r
        echo
        ENABLE_VOICE_ANALYSIS=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

        echo "Video Processing:"
        read -p "Enable video processing features? (y/N): " -n 1 -r
        echo
        ENABLE_VIDEO_PROCESSING=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

    else
        ENABLE_AI=false
        ENABLE_AI_CHAT=false
        ENABLE_VOICE_ANALYSIS=false
        ENABLE_VIDEO_PROCESSING=false
    fi
}

# SSL configuration
configure_ssl() {
    if [[ -n $DOMAIN_NAME ]]; then
        echo
        echo "SSL/HTTPS Configuration:"
        read -p "Enable SSL/HTTPS with Let's Encrypt? (y/N): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ENABLE_SSL=true
            read -p "Email for SSL certificate notifications: " SSL_EMAIL

            if [[ -z $SSL_EMAIL ]]; then
                log_error "Email is required for SSL certificates"
                exit 1
            fi
        else
            ENABLE_SSL=false
        fi
    else
        ENABLE_SSL=false
    fi
}

# Additional features configuration
configure_features() {
    echo
    echo "Additional Features:"

    # Backup configuration
    read -p "Enable automated backups? (y/N): " -n 1 -r
    echo
    ENABLE_BACKUPS=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

    if [[ $ENABLE_BACKUPS == true ]]; then
        read -p "Backup frequency (daily/weekly) [daily]: " BACKUP_FREQUENCY
        BACKUP_FREQUENCY=${BACKUP_FREQUENCY:-daily}
        read -p "Backup retention (days) [30]: " BACKUP_RETENTION
        BACKUP_RETENTION=${BACKUP_RETENTION:-30}
    fi

    # Monitoring
    read -p "Enable monitoring stack (Prometheus/Grafana)? (y/N): " -n 1 -r
    echo
    ENABLE_MONITORING=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

    # CDN integration
    read -p "Enable CDN integration? (y/N): " -n 1 -r
    echo
    ENABLE_CDN=$([[ $REPLY =~ ^[Yy]$ ]] && echo true || echo false)

    if [[ $ENABLE_CDN == true ]]; then
        echo "CDN Provider Options:"
        echo "1) Cloudflare"
        echo "2) AWS CloudFront"
        echo "3) Google Cloud CDN"
        read -p "Choose CDN provider [1]: " -n 1 -r
        echo

        case $REPLY in
            2)
                CDN_PROVIDER="cloudfront"
                read -p "AWS Region: " AWS_REGION
                read -p "CloudFront Distribution ID: " CLOUDFRONT_DISTRIBUTION_ID
                ;;
            3)
                CDN_PROVIDER="google"
                read -p "Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT_CDN
                ;;
            *)
                CDN_PROVIDER="cloudflare"
                read -p "Cloudflare Zone ID: " CLOUDFLARE_ZONE_ID
                read -p "Cloudflare API Token: " CLOUDFLARE_API_TOKEN
                ;;
        esac
    fi
}

# ============================================================================
# Installation Functions
# ============================================================================

# Install system dependencies
install_system_deps() {
    log_header "Installing System Dependencies"

    case $OS in
        ubuntu|debian)
            log_step "Installing for Ubuntu/Debian..."

            # Update package list
            sudo apt-get update

            # Install base packages
            sudo apt-get install -y \
                build-essential \
                python3-dev \
                python3-pip \
                python3-venv \
                git \
                curl \
                wget \
                htop \
                tree \
                jq \
                unzip

            # Install database packages
            case $DB_TYPE in
                postgresql)
                    sudo apt-get install -y postgresql postgresql-contrib libpq-dev
                    ;;
                mysql)
                    sudo apt-get install -y mysql-server libmysqlclient-dev
                    ;;
            esac

            # Install Redis if enabled
            if [[ $USE_REDIS == true ]]; then
                sudo apt-get install -y redis-server
            fi

            # Install web server for production
            if [[ $DEPLOYMENT_TYPE == "production" ]]; then
                sudo apt-get install -y nginx certbot python3-certbot-nginx
            fi

            # Install monitoring stack
            if [[ $ENABLE_MONITORING == true ]]; then
                sudo apt-get install -y prometheus prometheus-node-exporter grafana
            fi

            # Install AI dependencies
            if [[ $ENABLE_AI == true ]]; then
                sudo apt-get install -y ffmpeg libsm6 libxext6 libgl1-mesa-glx
                if [[ $AI_PROVIDER == "local" ]]; then
                    # Install Ollama
                    curl -fsSL https://ollama.ai/install.sh | sh
                fi
            fi

            ;;
        centos|rhel|fedora)
            log_step "Installing for CentOS/RHEL/Fedora..."

            # Install base packages
            sudo yum groupinstall -y "Development Tools"
            sudo yum install -y \
                python3-devel \
                git \
                curl \
                wget \
                htop \
                tree \
                jq \
                unzip

            # Install database packages
            case $DB_TYPE in
                postgresql)
                    sudo yum install -y postgresql-server postgresql-contrib libpq-devel
                    ;;
                mysql)
                    sudo yum install -y mysql-server mysql-devel
                    ;;
            esac

            # Install Redis if enabled
            if [[ $USE_REDIS == true ]]; then
                sudo yum install -y redis
            fi

            # Install web server for production
            if [[ $DEPLOYMENT_TYPE == "production" ]]; then
                sudo yum install -y nginx certbot python3-certbot-nginx
            fi

            ;;
        macos)
            log_step "Installing for macOS..."

            if ! command -v brew >/dev/null 2>&1; then
                log_error "Homebrew not found. Please install from https://brew.sh"
                exit 1
            fi

            brew install \
                python3 \
                git \
                curl \
                wget \
                htop \
                tree \
                jq \
                unzip

            # Install database packages
            case $DB_TYPE in
                postgresql)
                    brew install postgresql
                    ;;
                mysql)
                    brew install mysql
                    ;;
            esac

            # Install Redis if enabled
            if [[ $USE_REDIS == true ]]; then
                brew install redis
            fi

            ;;
        *)
            log_warning "Unsupported OS: $OS. Please install dependencies manually."
            log_info "Required packages: python3, pip, git, curl, database client libraries"
            ;;
    esac

    log_success "System dependencies installed"
}

# Setup database
setup_database() {
    log_header "Setting up Database"

    case $DB_TYPE in
        postgresql)
            log_step "Setting up PostgreSQL..."

            # Start PostgreSQL service
            if command -v systemctl >/dev/null 2>&1; then
                sudo systemctl enable postgresql
                sudo systemctl start postgresql
            fi

            # Create database and user
            sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
            sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true

            log_success "PostgreSQL database created"
            ;;
        mysql)
            log_step "Setting up MySQL..."

            # Start MySQL service
            if command -v systemctl >/dev/null 2>&1; then
                sudo systemctl enable mysqld
                sudo systemctl start mysqld
            fi

            # Secure MySQL installation (basic)
            mysql -u root << EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

            log_success "MySQL database created"
            ;;
        sqlite)
            log_info "SQLite selected - no setup required"
            ;;
    esac

    # Setup Redis if enabled
    if [[ $USE_REDIS == true ]]; then
        log_step "Setting up Redis..."

        if command -v systemctl >/dev/null 2>&1; then
            sudo systemctl enable redis
            sudo systemctl start redis
        fi

        log_success "Redis configured"
    fi
}

# Clone and setup application
setup_application() {
    log_header "Setting up Panel Application"

    # Create directories
    sudo mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR" "$BACKUP_DIR" "$SSL_DIR"
    sudo chown -R "$USER:$USER" "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR" "$BACKUP_DIR"

    # Backup existing installation if it exists
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_warning "Existing installation found. Creating backup..."
        local backup_name="panel_backup_$(date +%Y%m%d_%H%M%S)"
        sudo cp -r "$INSTALL_DIR" "$BACKUP_DIR/$backup_name"
        log_success "Backup created: $BACKUP_DIR/$backup_name"
    fi

    # Clone or update repository
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_step "Updating existing installation..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "$REPO_BRANCH"
        git pull origin "$REPO_BRANCH"
    else
        log_step "Cloning Panel repository..."
        git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    # Create virtual environment
    log_step "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip setuptools wheel

    # Install Python dependencies
    log_step "Installing Python dependencies..."
    pip install -r requirements/requirements.txt

    # Install additional dependencies based on configuration
    if [[ $ENABLE_AI == true ]]; then
        log_step "Installing AI dependencies..."
        pip install openai google-cloud-aiplatform azure-cognitiveservices-speech opencv-python-headless

        if [[ $AI_PROVIDER == "google" ]]; then
            pip install google-cloud-storage
        fi
    fi

    if [[ $ENABLE_MONITORING == true ]]; then
        log_step "Installing monitoring dependencies..."
        pip install prometheus-client
    fi

    if [[ $ENABLE_CDN == true ]]; then
        log_step "Installing CDN dependencies..."
        case $CDN_PROVIDER in
            cloudflare)
                pip install cloudflare
                ;;
            cloudfront)
                pip install boto3
                ;;
            google)
                pip install google-cloud-cdn
                ;;
        esac
    fi

    log_success "Application setup completed"
}

# Configure application
configure_application() {
    log_header "Configuring Panel Application"

    cd "$INSTALL_DIR"

    # Copy configuration template
    cp config/config.py.example config/config.py

    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)

    # Update configuration
    cat > config/config.py << EOF
import os

# ============================================================================
# Panel Configuration - Generated by installer v$SCRIPT_VERSION
# ============================================================================

# Security
SECRET_KEY = "$SECRET_KEY"

# Database configuration
EOF

    case $DB_TYPE in
        postgresql)
        cat >> config/config.py << EOF
SQLALCHEMY_DATABASE_URI = f"postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
EOF
        ;;
        mysql)
        cat >> config/config.py << EOF
SQLALCHEMY_DATABASE_URI = f"mysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
EOF
        ;;
        sqlite)
        cat >> config/config.py << EOF
SQLALCHEMY_DATABASE_URI = f"sqlite:///$DATA_DIR/panel.db"
EOF
        ;;
    esac

    # Redis configuration
    if [[ $USE_REDIS == true ]]; then
        cat >> config/config.py << EOF

# Redis configuration
REDIS_URL = f"redis://$([[ -n "$REDIS_PASSWORD" ]] && echo ":$REDIS_PASSWORD@")$REDIS_HOST:$REDIS_PORT/$REDIS_DB"
CACHE_TYPE = "redis"
CACHE_REDIS_URL = REDIS_URL
SESSION_TYPE = "redis"
SESSION_REDIS_URL = REDIS_URL
EOF
    fi

    # AI configuration
    if [[ $ENABLE_AI == true ]]; then
        cat >> config/config.py << EOF

# AI Configuration
AI_ENABLED = True
EOF

        if [[ $ENABLE_AI_CHAT == true ]]; then
            cat >> config/config.py << EOF
AI_CHAT_ENABLED = True
EOF

            case $AI_PROVIDER in
                azure)
                    cat >> config/config.py << EOF
AZURE_OPENAI_ENDPOINT = "$AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_API_KEY = "$AZURE_OPENAI_API_KEY"
AZURE_OPENAI_DEPLOYMENT = "$AZURE_OPENAI_DEPLOYMENT"
EOF
                    ;;
                google)
                    cat >> config/config.py << EOF
GOOGLE_CLOUD_PROJECT = "$GOOGLE_CLOUD_PROJECT"
GOOGLE_CLOUD_REGION = "$GOOGLE_CLOUD_REGION"
VERTEX_AI_ENABLED = True
EOF
                    ;;
                openai)
                    cat >> config/config.py << EOF
OPENAI_API_KEY = "$OPENAI_API_KEY"
EOF
                    ;;
                local)
                    cat >> config/config.py << EOF
OLLAMA_HOST = "$OLLAMA_HOST"
OLLAMA_PORT = "$OLLAMA_PORT"
AI_PROVIDER = "local"
EOF
                    ;;
            esac
        fi

        if [[ $ENABLE_VOICE_ANALYSIS == true ]]; then
            cat >> config/config.py << EOF
VOICE_ANALYSIS_ENABLED = True
EOF
        fi

        if [[ $ENABLE_VIDEO_PROCESSING == true ]]; then
            cat >> config/config.py << EOF
VIDEO_PROCESSING_ENABLED = True
EOF
        fi
    fi

    # CDN configuration
    if [[ $ENABLE_CDN == true ]]; then
        cat >> config/config.py << EOF

# CDN Configuration
CDN_ENABLED = True
CDN_PROVIDER = "$CDN_PROVIDER"
EOF

        case $CDN_PROVIDER in
            cloudflare)
                cat >> config/config.py << EOF
CLOUDFLARE_ZONE_ID = "$CLOUDFLARE_ZONE_ID"
CLOUDFLARE_API_TOKEN = "$CLOUDFLARE_API_TOKEN"
EOF
                ;;
            cloudfront)
                cat >> config/config.py << EOF
AWS_REGION = "$AWS_REGION"
CLOUDFRONT_DISTRIBUTION_ID = "$CLOUDFRONT_DISTRIBUTION_ID"
EOF
                ;;
            google)
                cat >> config/config.py << EOF
GOOGLE_CLOUD_PROJECT_CDN = "$GOOGLE_CLOUD_PROJECT_CDN"
EOF
                ;;
        esac
    fi

    # Environment-specific settings
    case $DEPLOYMENT_TYPE in
        production)
            cat >> config/config.py << EOF

# Production settings
DEBUG = False
TESTING = False
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
EOF
            ;;
        staging)
            cat >> config/config.py << EOF

# Staging settings
DEBUG = False
TESTING = False
SESSION_COOKIE_SECURE = False
EOF
            ;;
        development)
            cat >> config/config.py << EOF

# Development settings
DEBUG = True
TESTING = False
SESSION_COOKIE_SECURE = False
EOF
            ;;
    esac

    # Domain and SSL
    if [[ -n $DOMAIN_NAME ]]; then
        cat >> config/config.py << EOF

# Domain configuration
SERVER_NAME = "$DOMAIN_NAME"
EOF

        if [[ $ENABLE_SSL == true ]]; then
            cat >> config/config.py << EOF
PREFERRED_URL_SCHEME = "https"
EOF
        fi
    fi

    # Monitoring configuration
    if [[ $ENABLE_MONITORING == true ]]; then
        cat >> config/config.py << EOF

# Monitoring configuration
MONITORING_ENABLED = True
PROMETHEUS_ENABLED = True
GRAFANA_ENABLED = True
EOF
    fi

    # Backup configuration
    if [[ $ENABLE_BACKUPS == true ]]; then
        cat >> config/config.py << EOF

# Backup configuration
BACKUP_ENABLED = True
BACKUP_FREQUENCY = "$BACKUP_FREQUENCY"
BACKUP_RETENTION_DAYS = $BACKUP_RETENTION
EOF
    fi

    log_success "Configuration completed"
}

# Setup web server
setup_web_server() {
    if [[ $DEPLOYMENT_TYPE == "development" ]]; then
        log_info "Development mode - skipping web server setup"
        return
    fi

    log_header "Setting up Web Server"

    case $OS in
        ubuntu|debian|centos|rhel|fedora)
            # Setup Nginx
            log_step "Configuring Nginx..."

            local nginx_config="/etc/nginx/sites-available/panel"

            cat > "$nginx_config" << EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME:-localhost};

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static {
        alias $INSTALL_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ \.(env|git|gitignore|htaccess|htpasswd)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

            # Enable site
            sudo ln -sf "$nginx_config" /etc/nginx/sites-enabled/
            sudo rm -f /etc/nginx/sites-enabled/default

            # Test configuration
            if sudo nginx -t; then
                sudo systemctl reload nginx
                log_success "Nginx configured and reloaded"
            else
                log_error "Nginx configuration test failed"
                exit 1
            fi

            ;;
        macos)
            log_warning "macOS web server setup not implemented. Please configure manually."
            ;;
        *)
            log_warning "Unsupported OS for web server setup. Please configure manually."
            ;;
    esac
}

# Setup SSL certificate
setup_ssl() {
    if [[ $ENABLE_SSL != true ]] || [[ -z $DOMAIN_NAME ]]; then
        return
    fi

    log_header "Setting up SSL Certificate"

    case $OS in
        ubuntu|debian|centos|rhel|fedora)
            log_step "Obtaining SSL certificate with Let's Encrypt..."

            # Stop nginx temporarily for certbot standalone mode
            sudo systemctl stop nginx

            # Get certificate
            if sudo certbot certonly --standalone -d "$DOMAIN_NAME" --non-interactive --agree-tos --email "$SSL_EMAIL"; then
                log_success "SSL certificate obtained"

                # Configure nginx for SSL
                local nginx_ssl_config="/etc/nginx/sites-available/panel-ssl"

                cat > "$nginx_ssl_config" << EOF
server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Include non-SSL configuration
    include /etc/nginx/sites-available/panel;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN_NAME;
    return 301 https://\$server_name\$request_uri;
}
EOF

                sudo cp "$nginx_ssl_config" /etc/nginx/sites-available/
                sudo ln -sf /etc/nginx/sites-available/panel-ssl /etc/nginx/sites-enabled/
                sudo rm -f /etc/nginx/sites-enabled/panel

                # Test and reload
                if sudo nginx -t; then
                    sudo systemctl start nginx
                    log_success "SSL configured and nginx restarted"
                else
                    log_error "Nginx SSL configuration test failed"
                    sudo systemctl start nginx  # Restart nginx even if config failed
                    exit 1
                fi

                # Setup certbot renewal
                sudo systemctl enable certbot.timer
                sudo systemctl start certbot.timer
                log_success "SSL certificate renewal configured"

            else
                log_error "Failed to obtain SSL certificate"
                sudo systemctl start nginx  # Restart nginx
                exit 1
            fi

            ;;
        *)
            log_warning "SSL setup not supported on this OS. Please configure manually."
            ;;
    esac
}

# Initialize database
initialize_database() {
    log_header "Initializing Database"

    cd "$INSTALL_DIR"
    source venv/bin/activate

    # Initialize database schema
    log_step "Creating database tables..."
    flask db upgrade

    # Create admin user
    log_step "Creating admin user..."
    python3 -c "
from app import create_app, db
from src.panel.models import User

app = create_app()
with app.app_context():
    db.create_all()

    # Create admin user if it doesn't exist
    admin = User.query.filter_by(email='admin@$DOMAIN_NAME').first()
    if not admin:
        admin = User(
            first_name='System',
            last_name='Administrator',
            email='admin@$DOMAIN_NAME',
            dob='1990-01-01'
        )
        admin.set_password('ChangeMe123!')
        admin.role = 'system_admin'
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@$DOMAIN_NAME / ChangeMe123!')
    else:
        print('Admin user already exists')
    "

    log_success "Database initialized"
}

# Setup monitoring stack
setup_monitoring() {
    if [[ $ENABLE_MONITORING != true ]]; then
        return
    fi

    log_header "Setting up Monitoring Stack"

    case $OS in
        ubuntu|debian)
            log_step "Configuring Prometheus..."

            # Configure Prometheus
            cat > /tmp/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'panel'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: /metrics

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

            sudo cp /tmp/prometheus.yml /etc/prometheus/prometheus.yml
            sudo systemctl enable prometheus
            sudo systemctl restart prometheus

            log_step "Configuring Grafana..."
            sudo systemctl enable grafana-server
            sudo systemctl start grafana-server

            log_success "Monitoring stack configured"
            ;;
        *)
            log_warning "Monitoring setup not supported on this OS. Please configure manually."
            ;;
    esac
}

# Create startup scripts and services
create_startup_scripts() {
    log_header "Creating Startup Scripts and Services"

    # Create convenience scripts
    cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
export PYTHONPATH="$INSTALL_DIR"
exec python app.py
EOF

    cat > "$INSTALL_DIR/stop.sh" << EOF
#!/bin/bash
pkill -f "python app.py"
EOF

    cat > "$INSTALL_DIR/restart.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
./stop.sh
sleep 3
./start.sh
EOF

    cat > "$INSTALL_DIR/status.sh" << EOF
#!/bin/bash
if pgrep -f "python app.py" > /dev/null; then
    echo "Panel is running"
    exit 0
else
    echo "Panel is not running"
    exit 1
fi
EOF

    chmod +x "$INSTALL_DIR"/*.sh

    # Create systemd service for production
    if [[ $DEPLOYMENT_TYPE == "production" ]] && command -v systemctl >/dev/null 2>&1; then
        log_step "Creating systemd service..."

        cat > /tmp/panel.service << EOF
[Unit]
Description=Panel Application
After=network.target
Wants=postgresql.service redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$DATA_DIR $LOG_DIR
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

        sudo cp /tmp/panel.service /etc/systemd/system/panel.service
        sudo systemctl daemon-reload
        sudo systemctl enable panel
        sudo systemctl start panel

        log_success "Systemd service created and started"
    fi

    log_success "Startup scripts created"
}

# Setup backup system
setup_backups() {
    if [[ $ENABLE_BACKUPS != true ]]; then
        return
    fi

    log_header "Setting up Backup System"

    # Create backup script
    cat > "$INSTALL_DIR/backup.sh" << EOF
#!/bin/bash
# Panel Backup Script

BACKUP_DIR="$BACKUP_DIR"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="panel_backup_\$TIMESTAMP"

echo "Creating backup: \$BACKUP_NAME"

# Create backup directory
mkdir -p "\$BACKUP_DIR/\$BACKUP_NAME"

# Backup database
case "$DB_TYPE" in
    postgresql)
        pg_dump -U $DB_USER -h $DB_HOST -p $DB_PORT $DB_NAME > "\$BACKUP_DIR/\$BACKUP_NAME/database.sql"
        ;;
    mysql)
        mysqldump -u $DB_USER -p$DB_PASSWORD -h $DB_HOST -P $DB_PORT $DB_NAME > "\$BACKUP_DIR/\$BACKUP_NAME/database.sql"
        ;;
    sqlite)
        cp "$DATA_DIR/panel.db" "\$BACKUP_DIR/\$BACKUP_NAME/"
        ;;
esac

# Backup configuration and data
cp -r "$CONFIG_DIR" "\$BACKUP_DIR/\$BACKUP_NAME/"
cp -r "$DATA_DIR" "\$BACKUP_DIR/\$BACKUP_NAME/"

# Compress backup
cd "\$BACKUP_DIR"
tar -czf "\$BACKUP_NAME.tar.gz" "\$BACKUP_NAME"
rm -rf "\$BACKUP_NAME"

echo "Backup completed: \$BACKUP_DIR/\$BACKUP_NAME.tar.gz"

# Cleanup old backups
find "\$BACKUP_DIR" -name "panel_backup_*.tar.gz" -mtime +$BACKUP_RETENTION -delete
EOF

    chmod +x "$INSTALL_DIR/backup.sh"

    # Setup cron job for automated backups
    if [[ $BACKUP_FREQUENCY == "daily" ]]; then
        CRON_SCHEDULE="0 2 * * *"  # Daily at 2 AM
    else
        CRON_SCHEDULE="0 2 * * 0"  # Weekly on Sunday at 2 AM
    fi

    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $INSTALL_DIR/backup.sh") | crontab -

    log_success "Backup system configured"
}

# ============================================================================
# Main Installation Flow
# ============================================================================

# Display banner
show_banner() {
    echo
    echo -e "${PURPLE}${BOLD}"
    echo "????????????????????????????????????????????????????????????????"
    echo "?                      PANEL INSTALLER                        ?"
    echo "?                 Interactive Setup Script                    ?"
    echo "????????????????????????????????????????????????????????????????"
    echo -e "${NC}"
    echo -e "${CYAN}Version: $SCRIPT_VERSION${NC}"
    echo -e "${CYAN}Repository: https://github.com/phillgates2/panel${NC}"
    echo
}

# Display completion message
show_completion() {
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - START_TIME))

    log_header "Installation Completed Successfully! ${ROCKET}"

    echo -e "${GREEN}${BOLD}Panel has been installed and configured!${NC}"
    echo
    echo -e "${WHITE}Installation Summary:${NC}"
    echo -e "  ${CHECK_MARK} Installation directory: ${CYAN}$INSTALL_DIR${NC}"
    echo -e "  ${CHECK_MARK} Configuration: ${CYAN}$CONFIG_DIR${NC}"
    echo -e "  ${CHECK_MARK} Data directory: ${CYAN}$DATA_DIR${NC}"
    echo -e "  ${CHECK_MARK} Logs: ${CYAN}$LOG_DIR${NC}"
    echo -e "  ${CHECK_MARK} Database: ${CYAN}$DB_TYPE${NC}"
    echo -e "  ${CHECK_MARK} Deployment: ${CYAN}$DEPLOYMENT_TYPE${NC}"

    if [[ -n $DOMAIN_NAME ]]; then
        local protocol="http"
        [[ $ENABLE_SSL == true ]] && protocol="https"
        echo -e "  ${GLOBE} URL: ${CYAN}$protocol://$DOMAIN_NAME${NC}"
    else
        echo -e "  ${GLOBE} URL: ${CYAN}http://localhost:8080${NC}"
    fi

    echo
    echo -e "${WHITE}Admin Credentials:${NC}"
    echo -e "  ${LOCK} Email: ${CYAN}admin@$DOMAIN_NAME${NC}"
    echo -e "  ${LOCK} Password: ${CYAN}ChangeMe123!${NC} ${YELLOW}(Change immediately!)${NC}"

    echo
    echo -e "${WHITE}Useful Commands:${NC}"
    echo -e "  ${GEAR} Start: ${CYAN}cd $INSTALL_DIR && ./start.sh${NC}"
    echo -e "  ${GEAR} Stop: ${CYAN}cd $INSTALL_DIR && ./stop.sh${NC}"
    echo -e "  ${GEAR} Restart: ${CYAN}cd $INSTALL_DIR && ./restart.sh${NC}"
    echo -e "  ${GEAR} Status: ${CYAN}cd $INSTALL_DIR && ./status.sh${NC}"
    echo -e "  ${GEAR} Logs: ${CYAN}sudo journalctl -u panel -f${NC} (production)"

    if [[ $ENABLE_BACKUPS == true ]]; then
        echo -e "  ${DATABASE} Backup: ${CYAN}cd $INSTALL_DIR && ./backup.sh${NC}"
        echo -e "  ${DATABASE} Backup location: ${CYAN}$BACKUP_DIR${NC}"
    fi

    echo
    echo -e "${WHITE}Next Steps:${NC}"
    echo -e "  1. ${YELLOW}Change the admin password immediately${NC}"
    echo -e "  2. Configure your domain DNS (if applicable)"
    echo -e "  3. Review and adjust security settings"
    echo -e "  4. Set up monitoring and alerting"
    echo -e "  5. Configure backups and recovery"

    echo
    echo -e "${WHITE}Documentation:${NC}"
    echo -e "  ${CYAN}https://github.com/phillgates2/panel${NC}"

    echo
    echo -e "${GREEN}${BOLD}Installation completed in ${duration} seconds!${NC}"
    echo
    echo -e "${PURPLE}${BOLD}Thank you for choosing Panel! ${ROCKET}${NC}"
}

# Main installation function
main() {
    show_banner

    # Pre-installation checks
    check_root
    detect_os
    check_requirements

    # Interactive configuration
    interactive_config

    # Installation steps with progress
    local steps=("System Dependencies" "Database Setup" "Application Setup" "Configuration" "Web Server" "SSL Setup" "Database Init" "Monitoring" "Backups" "Startup Scripts")
    local current_step=0
    local total_steps=${#steps[@]}

    install_system_deps
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_database
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_application
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    configure_application
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_web_server
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_ssl
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    initialize_database
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_monitoring
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    setup_backups
    show_progress $((++current_step)) $total_steps "${steps[$((current_step-1))]}"

    create_startup_scripts
    show_progress $total_steps $total_steps "Installation Complete"

    # Completion
    show_completion
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Panel Interactive Installer"
        echo
        echo "Usage:"
        echo "  $0                    # Interactive installation"
        echo "  $0 --help            # Show this help"
        echo "  $0 --version         # Show version"
        echo
        echo "Environment variables:"
        echo "  PANEL_INSTALL_DIR    # Installation directory"
        echo "  PANEL_CONFIG_DIR     # Configuration directory"
        echo "  PANEL_DATA_DIR       # Data directory"
        echo "  PANEL_LOG_DIR        # Log directory"
        echo "  PANEL_BACKUP_DIR     # Backup directory"
        echo "  PANEL_BRANCH         # Git branch to install"
        echo
        exit 0
        ;;
    --version|-v)
        echo "Panel Installer v$SCRIPT_VERSION"
        exit 0
        ;;
    *)
        # Run main installation
        main "$@"
        ;;
esac