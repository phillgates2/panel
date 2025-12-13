#!/bin/bash

# Comprehensive Interactive Installer for Panel Application
# Run with: 
#   curl -o install.sh https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh && bash install.sh
#   wget -O install.sh https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh && bash install.sh
# Or for non-interactive: bash install.sh --non-interactive
#
# WARNING: Always review scripts before running!
# NOTE: For interactive installation, download the script first. Piping to bash will run in non-interactive mode.

set -e

# Command line options
DRY_RUN=false
NON_INTERACTIVE=false
DEV_MODE=false
DOCKER_MODE=false
WIZARD_MODE=false
CLOUD_PRESET=""
OFFLINE_MODE=false
RUN_TESTS=false
MIGRATION_MODE=false
DEBUG_MODE=false
RESTORE_BACKUP=""
SSL_CERT_FILE=""
SSL_KEY_FILE=""
MONITORING=false
FIREWALL=true
BACKUPS=true
GUNICORN_WORKERS=""
GUNICORN_THREADS=""
GUNICORN_MAX_REQUESTS=""
MEMORY_LIMIT=""
ENABLE_SELINUX=false
ENABLE_APPARMOR=false
ENABLE_FAIL2BAN=false
ENABLE_CLAMAV=false
AWS_PROFILE=""
GCP_PROJECT=""
AZURE_SUBSCRIPTION=""
USE_TERRAFORM=false
BACKUP_METHOD="rsync"
REMOTE_BACKUP_URL=""
BACKUP_ENCRYPTION_KEY=""
RETENTION_POLICY="30"
ENABLE_GDPR=false
ENABLE_HIPAA=false
ENABLE_SOC2=false
AUDIT_LOG_DESTINATION=""
PLUGINS_TO_INSTALL=""
PLUGIN_REPOSITORY=""
CUSTOM_PLUGIN_DIR=""
DATADOG_API_KEY=""
NEWRELIC_LICENSE=""
ENABLE_OPENTELEMETRY=false
ENABLE_DISTRIBUTED_TRACING=false
SYSTEM_LOCALE=""
SYSTEM_TIMEZONE=""
LOCALES_TO_INSTALL=""
LOAD_BALANCER_TYPE=""
SSL_TERMINATION=""
CDN_PROVIDER=""
ENABLE_WAF=false
K8S_NAMESPACE=""
HELM_VALUES_FILE=""
INGRESS_CONTROLLER=""

# Rollback tracking
ROLLBACK_STEPS=()
INSTALL_START_TIME=$(date +%s)

# Progress tracking
STEP_DESCRIPTIONS=(
    "System validation and requirements check"
    "Package manager detection and updates"
    "System dependencies installation"
    "Python environment setup"
    "Repository cloning and updates"
    "Python dependencies installation"
    "Database configuration and setup"
    "Redis configuration and setup"
    "Application configuration"
    "Service setup and startup"
)

# Detect package manager
detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v yum &> /dev/null; then
        echo "yum"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v apk &> /dev/null; then
        echo "apk"
    else
        echo "unknown"
    fi
}

# Set Python command
PYTHON_CMD="python3"

# Function to install PostgreSQL
install_postgresql() {
    log_info "Installing PostgreSQL..."
    
    case $PKG_MANAGER in
        apt)
            # Try different package names for different Ubuntu versions
            if $PKG_INSTALL postgresql postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL installed via apt"
            elif $PKG_INSTALL postgresql-15 postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL 15 installed via apt"
            elif $PKG_INSTALL postgresql-14 postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL 14 installed via apt"
            elif $PKG_INSTALL postgresql-13 postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL 13 installed via apt"
            else
                log_error "Failed to install PostgreSQL via apt"
                return 1
            fi
            ;;
        yum)
            if $PKG_INSTALL postgresql postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL installed via yum"
            elif $PKG_INSTALL postgresql-server postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL server installed via yum"
            else
                log_error "Failed to install PostgreSQL via yum"
                return 1
            fi
            ;;
        dnf)
            if $PKG_INSTALL postgresql postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL installed via dnf"
            elif $PKG_INSTALL postgresql-server postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL server installed via dnf"
            else
                log_error "Failed to install PostgreSQL via dnf"
                return 1
            fi
            ;;
        zypper)
            if $PKG_INSTALL postgresql postgresql-contrib 2>/dev/null; then
                log_success "PostgreSQL installed via zypper"
            else
                log_error "Failed to install PostgreSQL via zypper"
                return 1
            fi
            ;;
        pacman)
            if $PKG_INSTALL postgresql 2>/dev/null; then
                log_success "PostgreSQL installed via pacman"
            else
                log_error "Failed to install PostgreSQL via pacman"
                return 1
            fi
            ;;
        apk)
            # Alpine Linux (OpenRC)
            $PKG_UPDATE || true
            # Try common Alpine package names
            if $PKG_INSTALL postgresql postgresql-client 2>/dev/null; then
                log_success "PostgreSQL installed via apk"
            elif $PKG_INSTALL postgresql16 postgresql16-client 2>/dev/null; then
                log_success "PostgreSQL 16 installed via apk"
            elif $PKG_INSTALL postgresql15 postgresql15-client 2>/dev/null; then
                log_success "PostgreSQL 15 installed via apk"
            elif $PKG_INSTALL postgresql14 postgresql14-client 2>/dev/null; then
                log_success "PostgreSQL 14 installed via apk"
            else
                log_error "Failed to install PostgreSQL via apk"
                return 1
            fi
            ;;
        brew)
            if $PKG_INSTALL postgresql 2>/dev/null; then
                log_success "PostgreSQL installed via brew"
            else
                log_error "Failed to install PostgreSQL via brew"
                return 1
            fi
            ;;
        *)
            log_error "Unsupported package manager for PostgreSQL installation"
            return 1
            ;;
    esac
    
    # Initialize and start PostgreSQL
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v systemctl &> /dev/null; then
            sudo systemctl enable postgresql || true
            sudo systemctl start postgresql || true
            add_rollback_step "sudo systemctl stop postgresql && sudo systemctl disable postgresql"
        elif command -v rc-service &> /dev/null; then
            # Alpine/OpenRC
            # Initialize data directory if missing
            if [ ! -d "/var/lib/postgresql/data" ] || [ -z "$(ls -A /var/lib/postgresql/data 2>/dev/null)" ]; then
                log_info "Initializing PostgreSQL data directory (Alpine)"
                sudo -u postgres initdb -D /var/lib/postgresql/data || sudo -u postgres initdb || true
            fi
            # Service name may vary; try generic name
            sudo rc-update add postgresql default || true
            sudo rc-service postgresql start || sudo rc-service postgresql16 start || sudo rc-service postgresql15 start || true
            add_rollback_step "sudo rc-service postgresql stop || true"
        else
            log_warning "No known service manager (systemctl/rc-service). Start PostgreSQL manually."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start postgresql
        add_rollback_step "brew services stop postgresql"
    fi
    
    sleep 2  # Wait for PostgreSQL to start
    return 0
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
# Enhanced logging with timestamps and levels
log_debug() {
    if [[ $DEBUG_MODE == true ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $(date '+%H:%M:%S') $1" | tee -a install.log
    fi
}

log_info() {
    echo -e "${PURPLE}[INFO]${NC} $(date '+%H:%M:%S') $1" | tee -a install.log
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $1" | tee -a install.log
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%H:%M:%S') $1" | tee -a install.log
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" | tee -a install.log
}

# Pre-flight checks for privilege and service management tools
preflight_checks() {
    if ! command -v sudo &> /dev/null; then
        log_warning "sudo not found. Package installation and service management may require elevated privileges."
        log_info "If installations fail, either run as root (not recommended) or install sudo."
    fi

    if ! command -v systemctl &> /dev/null && ! command -v rc-service &> /dev/null; then
        log_warning "No service manager detected (systemctl/rc-service)."
        print_postgres_manual_instructions
    fi
}

print_postgres_manual_instructions() {
    log_info "PostgreSQL manual start instructions (examples):"
    log_info "  • Initialize data dir (if needed): sudo -u postgres initdb -D /var/lib/postgresql/data"
    log_info "  • Start server:           sudo -u postgres pg_ctl -D /var/lib/postgresql/data start"
    log_info "  • Alternative start:       sudo -u postgres postgres -D /var/lib/postgresql/data"
    log_info "  • Verify connection:       psql -U postgres -c \"SELECT version();\""
}

# Enhanced progress tracking function with ETA
show_progress_with_eta() {
    local current=$1
    local total=$2
    local message=$3
    local start_time=$4
    
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))
    local elapsed=$(( $(date +%s) - start_time ))
    local eta=$(( (elapsed * total / current) - elapsed ))
    
    printf "\r[%s%s] %d%% - %s (ETA: %dm %ds)" \
        "$(printf '█%.0s' $(seq 1 $filled))" \
        "$(printf '░%.0s' $(seq 1 $empty))" \
        "$percent" "$message" "$((eta/60))" "$((eta%60))"
    
    if [[ $current -eq $total ]]; then
        echo ""
    fi
}

# Enhanced error handling with recovery options
handle_error() {
    local exit_code=$1
    local line_number=$2
    local command_failed=${3:-"Unknown command"}
    
    log_error "Installation failed at line $line_number (exit code: $exit_code)"
    log_error "Failed command: $command_failed"
    log_error "Current working directory: $(pwd)"
    log_error "System information: $(uname -a)"
    
    # Create error report
    {
        echo "=== INSTALLATION ERROR REPORT ==="
        echo "Timestamp: $(date)"
        echo "Exit code: $exit_code"
        echo "Line number: $line_number"
        echo "Failed command: $command_failed"
        echo "Working directory: $(pwd)"
        echo "System: $(uname -a)"
        echo "User: $(whoami)"
        echo "Environment variables:"
        env | grep -E "^(PANEL_|FLASK_|PYTHONPATH|PATH)=" | head -10
        echo "Disk usage:"
        df -h . | tail -1
        echo "Memory usage:"
        free -h 2>/dev/null || echo "free command not available"
        echo "=== END ERROR REPORT ==="
    } >> install-error.log
    
    if [[ $NON_INTERACTIVE != true ]]; then
        echo ""
        echo "Error details have been saved to: install-error.log"
        echo "Please include this file when reporting the issue."
        echo ""
        echo "Recovery options:"
        echo "1. Retry failed step"
        echo "2. Skip failed step and continue"
        echo "3. Rollback and exit"
        echo "4. Generate support bundle and exit"
        read -p "Choose option [3]: " RECOVERY_CHOICE
        RECOVERY_CHOICE=${RECOVERY_CHOICE:-3}
        
        case $RECOVERY_CHOICE in
            1) 
                log_info "Retrying failed step..."
                return 0
                ;;
            2) 
                log_warning "Skipping failed step and continuing..."
                return 0
                ;;
            4)
                log_info "Generating support bundle..."
                generate_support_bundle
                ;;
            *) 
                rollback_installation
                ;;
        esac
    else
        log_info "Error details saved to install-error.log"
        rollback_installation
    fi
}

# Generate support bundle for troubleshooting
generate_support_bundle() {
    local bundle_name="panel-support-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    log_info "Creating support bundle: $bundle_name"
    
    # Collect system information
    {
        echo "=== SYSTEM INFORMATION ==="
        uname -a
        echo "OS: $OSTYPE"
        echo "User: $(whoami)"
        echo "Working directory: $(pwd)"
        echo "Python version: $(python3 --version 2>/dev/null || echo 'Not found')"
        echo "Pip version: $(pip3 --version 2>/dev/null || echo 'Not found')"
        echo "Git version: $(git --version 2>/dev/null || echo 'Not found')"
        echo ""
        echo "=== ENVIRONMENT ==="
        env | grep -E "^(PANEL_|FLASK_|PYTHON|PATH|HOME|USER)=" | sort
        echo ""
        echo "=== DISK USAGE ==="
        df -h
        echo ""
        echo "=== INSTALLED PACKAGES ==="
        if command -v dpkg &> /dev/null; then
            dpkg -l | grep -E "(python|postgresql|redis|nginx)" | head -20
        elif command -v rpm &> /dev/null; then
            rpm -qa | grep -E "(python|postgresql|redis|nginx)" | head -20
        fi
    } > system-info.txt
    
    # Create bundle
    tar -czf "$bundle_name" install.log install-error.log system-info.txt requirements/ 2>/dev/null || true
    
    log_success "Support bundle created: $bundle_name"
    log_info "Please attach this file when seeking support"
}

# Security enhancements
validate_password() {
    local password=$1
    if [[ ${#password} -lt 12 ]]; then
        log_error "Password must be at least 12 characters"
        return 1
    fi
    if ! [[ $password =~ [A-Z] ]] || ! [[ $password =~ [a-z] ]] || ! [[ $password =~ [0-9] ]]; then
        log_error "Password must contain uppercase, lowercase, and numeric characters"
        return 1
    fi
    return 0
}

generate_secure_password() {
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
}

sanitize_input() {
    echo "$1" | sed 's/[^a-zA-Z0-9._@-]//g'
}

# Enhanced input validation
validate_install_dir() {
    local dir=$1
    if [[ -z "$dir" ]]; then
        log_error "Installation directory cannot be empty"
        return 1
    fi
    if [[ "$dir" =~ [^a-zA-Z0-9._/-] ]]; then
        log_error "Installation directory contains invalid characters"
        return 1
    fi
    if [[ "$dir" == /* ]]; then
        # Absolute path - check if writable
        if [[ ! -w "$(dirname "$dir")" ]]; then
            log_error "Cannot write to parent directory of $dir"
            return 1
        fi
    fi
    return 0
}

# Validate database choices
validate_db_choice() {
    local choice=$1
    case $choice in
        1|2|3) return 0 ;;
        *) log_error "Invalid database choice: $choice"; return 1 ;;
    esac
}

# Validate environment choice
validate_env_choice() {
    local choice=$1
    case $choice in
        1|2) return 0 ;;
        *) log_error "Invalid environment choice: $choice"; return 1 ;;
    esac
}

# Add rollback step
add_rollback_step() {
    ROLLBACK_STEPS+=("$1")
}

# Rollback installation on failure
rollback_installation() {
    if [[ ${#ROLLBACK_STEPS[@]} -eq 0 ]]; then
        return
    fi
    
    log_error "Installation failed. Rolling back changes..."
    
    for ((i=${#ROLLBACK_STEPS[@]}-1; i>=0; i--)); do
        log_info "Rolling back: ${ROLLBACK_STEPS[$i]}"
        eval "${ROLLBACK_STEPS[$i]}" 2>/dev/null || true
    done
    
    log_success "Rollback completed"
    exit 1
}

# Show elapsed time
show_elapsed_time() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - INSTALL_START_TIME))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    log_info "Installation took ${minutes}m ${seconds}s"
}

# Set trap for automatic rollback on error
trap 'handle_error $? $LINENO' ERR

# Check if running interactively
if [[ ! -t 0 ]]; then
    log_warning "Script is not running interactively (stdin is not a TTY)."
    log_warning "For interactive installation, please download the script first:"
    log_info "curl -o install.sh https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh && bash install.sh"
    log_info "Or run with --non-interactive for automated installation."
    NON_INTERACTIVE=true
fi

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Welcome message
echo "========================================"
echo "  Panel Application Installer"
echo "========================================"
echo ""
log_info "Welcome to the interactive installer for the Panel application!"
echo ""

# Run pre-flight checks early to surface environment limitations
preflight_checks

# Source common installer helpers (env checks)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -f "$SCRIPT_DIR/install/10-env-checks.sh" ]]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/install/10-env-checks.sh"
    install_env_checks
else
    log_warning "Installer helpers not found at $SCRIPT_DIR/install/10-env-checks.sh; continuing without extended env checks"
    # Fallback minimal package manager setup
    PKG_MANAGER=$(detect_package_manager)
    # Use sudo if available
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi
    case $PKG_MANAGER in
        apt)    PKG_UPDATE="$SUDO apt-get update"; PKG_INSTALL="$SUDO apt-get install -y" ;;
        yum)    PKG_UPDATE="$SUDO yum check-update || true"; PKG_INSTALL="$SUDO yum install -y" ;;
        dnf)    PKG_UPDATE="$SUDO dnf check-update || true"; PKG_INSTALL="$SUDO dnf install -y" ;;
        zypper) PKG_UPDATE="$SUDO zypper refresh"; PKG_INSTALL="$SUDO zypper install -y" ;;
        pacman) PKG_UPDATE="$SUDO pacman -Sy"; PKG_INSTALL="$SUDO pacman -S --noconfirm" ;;
        apk)    PKG_UPDATE="$SUDO apk update"; PKG_INSTALL="$SUDO apk add --no-cache" ;;
        brew)   PKG_UPDATE="brew update"; PKG_INSTALL="brew install" ;;
        *)      log_warning "Unknown package manager; some installations may fail" ;;
    esac
    log_info "Package manager detected: $PKG_MANAGER"
fi

# Handle Development mode
if [[ $DEV_MODE == true ]]; then
    log_info "Setting up development environment..."
    NON_INTERACTIVE=false  # Allow prompts in dev mode for some options
    ENV_CHOICE=1
    DB_CHOICE=1  # Use SQLite for dev
    INSTALL_REDIS="y"
fi

# Interactive prompts
if [[ $NON_INTERACTIVE != true ]]; then
    echo ""
    log_info "Please provide the following information for installation:"
    
    # Configuration Wizard Mode
    if [[ $WIZARD_MODE == true ]]; then
        echo ""
        echo "╔══════════════════════════════════════════════════╗"
        echo "║      Advanced Configuration Wizard              ║"
        echo "╚══════════════════════════════════════════════════╝"
        echo ""
        
        # Installation directory
        read -p "Installation directory (default: ~/panel): " INSTALL_DIR
        INSTALL_DIR=${INSTALL_DIR:-~/panel}
        
        # Sanitize installation directory
        INSTALL_DIR=$(sanitize_input "$INSTALL_DIR")
        
        # Deployment type
        echo ""
        echo "Deployment Type:"
        echo "  1. Development (single server, SQLite)"
        echo "  2. Production (single server, PostgreSQL)"
        echo "  3. High Availability (multiple servers, load balanced)"
        echo "  4. Container (Docker/Kubernetes)"
        read -p "Select deployment type [1-4]: " DEPLOY_TYPE
        DEPLOY_TYPE=${DEPLOY_TYPE:-1}
        
        case $DEPLOY_TYPE in
            1)
                ENV_CHOICE=1
                DB_CHOICE=1
                INSTALL_REDIS="y"
                ;;
            2)
                ENV_CHOICE=2
                DB_CHOICE=2
                INSTALL_REDIS="y"
                ;;
            3)
                ENV_CHOICE=2
                DB_CHOICE=2
                INSTALL_REDIS="n"
                read -p "Number of application servers: " NUM_APP_SERVERS
                read -p "Database server host: " DB_HOST
                read -p "Redis server host: " REDIS_HOST
                read -p "Load balancer domain: " DOMAIN
                HA_MODE=true
                ;;
            4)
                DOCKER_MODE=true
                ;;
        esac
        
        if [[ $DOCKER_MODE != true && $HA_MODE != true ]]; then
            # Database choice
            echo ""
            echo "Database Configuration:"
            echo "  1. SQLite (file-based, easy)"
            echo "  2. PostgreSQL (recommended)"
            echo "  3. External PostgreSQL"
            read -p "Choose database [1-3]: " DB_CHOICE
            DB_CHOICE=${DB_CHOICE:-1}
            
            if [[ $DB_CHOICE -eq 3 ]]; then
                read -p "Database host: " EXTERNAL_DB_HOST
                read -p "Database port [5432]: " EXTERNAL_DB_PORT
                EXTERNAL_DB_PORT=${EXTERNAL_DB_PORT:-5432}
                read -p "Database name: " EXTERNAL_DB_NAME
                read -p "Database user: " EXTERNAL_DB_USER
                read -sp "Database password: " EXTERNAL_DB_PASS
                echo ""
            fi
            
            # Redis configuration
            echo ""
            echo "Redis Configuration:"
            echo "  1. Install locally"
            echo "  2. External Redis server"
            echo "  3. Redis Cluster"
            read -p "Choose Redis setup [1-3]: " REDIS_CHOICE
            
            case $REDIS_CHOICE in
                1)
                    INSTALL_REDIS="y"
                    ;;
                2)
                    INSTALL_REDIS="n"
                    read -p "Redis host: " REDIS_HOST
                    read -p "Redis port [6379]: " REDIS_PORT
                    REDIS_PORT=${REDIS_PORT:-6379}
                    read -p "Redis password (optional): " -s REDIS_PASSWORD
                    echo ""
                    ;;
                3)
                    INSTALL_REDIS="n"
                    read -p "Redis cluster nodes (comma-separated): " REDIS_CLUSTER
                    ;;
            esac
            
            # Performance tuning
            echo ""
            echo "Performance Tuning:"
            read -p "Number of worker processes [auto]: " WORKER_PROCESSES
            WORKER_PROCESSES=${WORKER_PROCESSES:-auto}
            read -p "Worker connections [1000]: " WORKER_CONNECTIONS
            WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
            
            # Security options
            echo ""
            echo "Security Options:"
            read -p "Enable firewall configuration? (y/n) [y]: " SETUP_FIREWALL
            SETUP_FIREWALL=${SETUP_FIREWALL:-y}
            read -p "Enable fail2ban? (y/n) [y]: " SETUP_FAIL2BAN
            SETUP_FAIL2BAN=${SETUP_FAIL2BAN:-y}
            read -p "Run security hardening? (y/n) [y]: " SETUP_HARDENING
            SETUP_HARDENING=${SETUP_HARDENING:-y}
            
            # Monitoring
            echo ""
            echo "Monitoring:"
            read -p "Setup Prometheus & Grafana? (y/n) [n]: " SETUP_MONITORING
            SETUP_MONITORING=${SETUP_MONITORING:-n}
            
            # Backup configuration
            echo ""
            echo "Backup Configuration:"
            read -p "Enable automated backups? (y/n) [y]: " SETUP_BACKUPS
            SETUP_BACKUPS=${SETUP_BACKUPS:-y}
            if [[ $SETUP_BACKUPS == "y" ]]; then
                read -p "Backup retention days [30]: " BACKUP_RETENTION
                BACKUP_RETENTION=${BACKUP_RETENTION:-30}
                read -p "Backup directory [/var/backups/panel]: " BACKUP_DIR
                BACKUP_DIR=${BACKUP_DIR:-/var/backups/panel}
            fi
        fi
        
        # SSL/TLS
        if [[ $ENV_CHOICE -eq 2 ]]; then
            echo ""
            echo "SSL/TLS Configuration:"
            read -p "Domain name: " DOMAIN
            DOMAIN=$(sanitize_input "$DOMAIN")
            read -p "Email for SSL certificates: " SSL_EMAIL
            SSL_EMAIL=$(sanitize_input "$SSL_EMAIL")
            read -p "Use Let's Encrypt? (y/n) [y]: " USE_LETSENCRYPT
            USE_LETSENCRYPT=${USE_LETSENCRYPT:-y}
        fi
        
    else
        # Standard installation prompts
        # Installation directory
        read -p "Installation directory (default: ~/panel): " INSTALL_DIR
        INSTALL_DIR=${INSTALL_DIR:-~/panel}
        
        # Sanitize installation directory
        INSTALL_DIR=$(sanitize_input "$INSTALL_DIR")
        
        # Database choice
        echo ""
        echo "Database options:"
        echo "1. SQLite (default, easy setup)"
        echo "2. PostgreSQL (recommended for production)"
        read -p "Choose database [1-2]: " DB_CHOICE
        DB_CHOICE=${DB_CHOICE:-1}
        
        # Redis setup
        read -p "Install Redis locally? (y/n, default: y): " INSTALL_REDIS
        INSTALL_REDIS=${INSTALL_REDIS:-y}
        
        # Environment
        echo ""
        echo "Environment options:"
        echo "1. Development"
        echo "2. Production"
        read -p "Choose environment [1-2]: " ENV_CHOICE
        ENV_CHOICE=${ENV_CHOICE:-1}
        
        # Additional settings
        echo ""
        read -p "Enable monitoring with Prometheus & Grafana? (y/n) [n]: " ENABLE_MONITORING
        ENABLE_MONITORING=${ENABLE_MONITORING:-n}
        if [[ $ENABLE_MONITORING == "y" ]]; then MONITORING=true; fi
        
        read -p "Enable automated backups? (y/n) [y]: " ENABLE_BACKUPS
        ENABLE_BACKUPS=${ENABLE_BACKUPS:-y}
        if [[ $ENABLE_BACKUPS == "y" ]]; then BACKUPS=true; fi
        
        if [[ $ENV_CHOICE -eq 2 ]]; then
            read -p "Domain name (for SSL): " DOMAIN
            DOMAIN=$(sanitize_input "$DOMAIN")
            read -p "Email for SSL certificates: " SSL_EMAIL
            SSL_EMAIL=$(sanitize_input "$SSL_EMAIL")
        fi
    fi
else
    log_info "Running in non-interactive mode with defaults"
    INSTALL_DIR=${INSTALL_DIR:-~/panel}
    DB_CHOICE=${DB_CHOICE:-1}
    INSTALL_REDIS=${INSTALL_REDIS:-y}
    ENV_CHOICE=${ENV_CHOICE:-1}
fi
INSTALL_DIR=$(eval echo $INSTALL_DIR)  # Expand ~ if used

# Set deployment type based on environment choice
if [[ $ENV_CHOICE -eq 1 ]]; then
    DEPLOYMENT_TYPE="development"
else
    DEPLOYMENT_TYPE="production"
fi

# Display configuration summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Installation Configuration Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📁 Install Directory: $INSTALL_DIR"
echo "  🗄️  Database: $(if [[ $DB_CHOICE -eq 1 ]]; then echo 'SQLite (Development)'; else echo 'PostgreSQL (Production)'; fi)"
echo "  ⚡ Redis: $(if [[ $INSTALL_REDIS == 'y' ]]; then echo 'Local Installation'; else echo 'External Connection'; fi)"
echo "  🌍 Environment: $(if [[ $ENV_CHOICE -eq 1 ]]; then echo 'Development'; else echo 'Production'; fi)"
if [[ $ENV_CHOICE -eq 2 && -n "$DOMAIN" ]]; then
    echo "  🔒 Domain: $DOMAIN"
    echo "  📧 SSL Email: $SSL_EMAIL"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ $DRY_RUN == true ]]; then
    log_info "DRY RUN MODE: Would install with above configuration"
    exit 0
fi

if [[ $NON_INTERACTIVE != true ]]; then
    read -p "Proceed with installation? (y/n): " PROCEED
    if [[ $PROCEED != "y" ]]; then
        log_info "Installation cancelled by user"
        exit 0
    fi
fi

# Validate and create installation directory
log_info "Preparing installation directory..."
if [[ -d "$INSTALL_DIR" ]]; then
    log_warning "Directory $INSTALL_DIR already exists."
    if [[ $NON_INTERACTIVE == true ]]; then
        log_info "Non-interactive mode: updating existing installation"
        DIR_ACTION=1
    else
        read -p "Choose action: [1] Update existing, [2] Backup and reinstall, [3] Abort: " DIR_ACTION
        DIR_ACTION=${DIR_ACTION:-1}
    fi
    
    case $DIR_ACTION in
        1)
            log_info "Updating existing installation..."
            cd "$INSTALL_DIR"
            if [[ -d ".git" ]]; then
                git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)" || true
                git pull origin main || {
                    log_error "Failed to update repository"
                    exit 1
                }
            else
                log_error "Directory exists but is not a git repository"
                exit 1
            fi
            ;;
        2)
            BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "Creating backup at $BACKUP_DIR"
            mv "$INSTALL_DIR" "$BACKUP_DIR"
            git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR" || {
                log_error "Failed to clone repository. Restoring backup..."
                mv "$BACKUP_DIR" "$INSTALL_DIR"
                exit 1
            }
            cd "$INSTALL_DIR"
            log_success "Backup created at $BACKUP_DIR"
            ;;
        3)
            log_info "Installation aborted by user"
            exit 0
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac
else
    log_info "Cloning Panel repository..."
    show_progress_with_eta 1 10 "Cloning repository..." $(date +%s)
    git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR" || {
        log_error "Failed to clone repository"
        exit 1
    }
    cd "$INSTALL_DIR"
    add_rollback_step "rm -rf '$INSTALL_DIR'"
    show_progress_with_eta 2 10 "Repository cloned" $(date +%s)
fi

# Create virtual environment
log_info "Setting up Python virtual environment..."
show_progress_with_eta 3 10 "Creating virtual environment..." $(date +%s)
$PYTHON_CMD -m venv venv
source venv/bin/activate
add_rollback_step "rm -rf '$INSTALL_DIR/venv'"
show_progress_with_eta 4 10 "Virtual environment ready" $(date +%s)

# Install dependencies
log_info "Installing Python dependencies..."
show_progress_with_eta 5 10 "Upgrading pip..." $(date +%s)

# Offline installation mode
if [[ $OFFLINE_MODE == true ]]; then
    log_info "Offline installation mode enabled"
    
    # Check for offline package cache
    OFFLINE_CACHE="$INSTALL_DIR/offline-packages"
    if [[ ! -d "$OFFLINE_CACHE" ]]; then
        log_error "Offline package cache not found at $OFFLINE_CACHE"
        log_info "To create offline cache, run on connected machine:"
        log_info "  mkdir -p offline-packages"
        log_info "  pip download -r requirements.txt -d offline-packages"
        exit 1
    fi
    
    log_info "Using offline package cache from $OFFLINE_CACHE"
    pip install --upgrade --no-index --find-links="$OFFLINE_CACHE" pip || {
        log_warning "Failed to upgrade pip offline"
    }
else
    pip install --upgrade pip || {
        log_error "Failed to upgrade pip"
        exit 1
    }
fi

log_info "Installing required packages (this may take a few minutes)..."
if [[ -f "requirements/requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements/requirements.txt"
elif [[ -f "requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements.txt"
else
    log_error "requirements.txt not found"
    exit 1
fi

# Count packages
PKG_COUNT=$(grep -v '^#' "$REQUIREMENTS_FILE" | grep -v '^$' | wc -l)
log_info "Installing $PKG_COUNT packages from $REQUIREMENTS_FILE"

# Start timer
START_TIME=$(date +%s)

# Dependency conflict detection and resolution
if [[ -f "requirements/production.txt" && $OFFLINE_MODE != true ]]; then
    log_info "Checking for dependency conflicts..."
    pip install pip-tools 2>/dev/null || true
    if command -v pip-compile >/dev/null 2>&1; then
        pip-compile --generate-hashes requirements/production.txt 2>&1 | grep -i "conflict\|incompatible" && {
            log_warning "Dependency conflicts detected. Attempting resolution..."
            pip-compile --upgrade --generate-hashes requirements/production.txt
        }
    fi
fi

show_progress_with_eta 6 10 "Installing dependencies ($PKG_COUNT packages)..." $(date +%s)
if [[ $OFFLINE_MODE == true ]]; then
    pip install --no-index --find-links="$OFFLINE_CACHE" -r "$REQUIREMENTS_FILE" || {
        log_error "Failed to install Python dependencies from offline cache"
        log_info "Ensure all dependencies are downloaded in $OFFLINE_CACHE"
        exit 1
    }
else
    pip install -r "$REQUIREMENTS_FILE" || {
        log_error "Failed to install Python dependencies"
        log_info "Try running: pip install -r $REQUIREMENTS_FILE manually"
        exit 1
    }
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log_success "Python dependencies installed successfully ($ELAPSED seconds)"
show_progress_with_eta 7 10 "Dependencies installed" $(date +%s)

# Database setup
show_progress_with_eta 8 10 "Configuring database..." $(date +%s)
if [[ $DB_CHOICE -eq 1 ]]; then
    log_info "Using SQLite database"
    
    # Check if sqlite3 is available
    if ! command -v sqlite3 &> /dev/null; then
        log_warning "sqlite3 not found. Installing..."
        $PKG_UPDATE
        $PKG_INSTALL sqlite3 || {
            log_error "Failed to install sqlite3"
            exit 1
        }
    fi
    
    export PANEL_DATABASE_URI="sqlite:///$INSTALL_DIR/panel.db"
    log_success "SQLite database will be created at: $INSTALL_DIR/panel.db"
elif [[ $DB_CHOICE -eq 2 ]]; then
    log_info "Setting up PostgreSQL..."
    
    # Install PostgreSQL if not present
    if ! command -v psql &> /dev/null; then
        install_postgresql || {
            log_error "Failed to install PostgreSQL"
            exit 1
        }
    else
        log_success "PostgreSQL is already installed"
    fi
    
    log_success "PostgreSQL is available"
    
    # Create database and user
    log_info "Creating database and user..."
    
    # Check if user already exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='panel_user'" | grep -q 1; then
        log_warning "User 'panel_user' already exists"
    else
        sudo -u postgres psql -c "CREATE USER panel_user WITH CREATEDB PASSWORD 'changeme';" || {
            log_error "Failed to create database user"
            exit 1
        }
        add_rollback_step "sudo -u postgres psql -c \"DROP USER IF EXISTS panel_user;\""
    fi
    
    # Check if database already exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw panel_db; then
        log_warning "Database 'panel_db' already exists"
        if [[ $NON_INTERACTIVE == true ]]; then
            log_info "Non-interactive mode: using existing database"
        else
            read -p "Drop and recreate? (y/n): " DROP_DB
            if [[ $DROP_DB == "y" ]]; then
                sudo -u postgres dropdb panel_db
                sudo -u postgres createdb -O panel_user panel_db
            fi
        fi
    else
        sudo -u postgres createdb -O panel_user panel_db || {
            log_error "Failed to create database"
            exit 1
        }
        add_rollback_step "sudo -u postgres dropdb panel_db"
    fi
    
    read -p "PostgreSQL password for panel_user (press Enter for default 'changeme'): " -s DB_PASSWORD
    echo ""
    DB_PASSWORD=${DB_PASSWORD:-changeme}
    
    # Update user password if changed
    if [[ "$DB_PASSWORD" != "changeme" ]]; then
        sudo -u postgres psql -c "ALTER USER panel_user WITH PASSWORD '$DB_PASSWORD';"
    fi
    
    export PANEL_DATABASE_URI="postgresql://panel_user:$DB_PASSWORD@localhost/panel_db"
    log_success "PostgreSQL database configured"
elif [[ $DB_CHOICE -eq 3 ]]; then
    log_info "Using external PostgreSQL database"
    export PANEL_DATABASE_URI="postgresql://$EXTERNAL_DB_USER:$EXTERNAL_DB_PASS@$EXTERNAL_DB_HOST:$EXTERNAL_DB_PORT/$EXTERNAL_DB_NAME"
    log_success "External database configured"
fi

# Redis setup
show_progress_with_eta 9 10 "Setting up Redis..." $(date +%s)
if [[ $INSTALL_REDIS == "y" ]]; then
    if ! command -v redis-cli &> /dev/null; then
        log_info "Installing Redis..."
        $PKG_UPDATE
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            $PKG_INSTALL redis-server || {
                log_error "Failed to install Redis"
                exit 1
            }
            sudo systemctl enable redis-server
            sudo systemctl start redis-server
            add_rollback_step "sudo systemctl stop redis-server && sudo systemctl disable redis-server"
            sleep 2
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            $PKG_INSTALL redis || {
                log_error "Failed to install Redis"
                exit 1
            }
            brew services start redis
            add_rollback_step "brew services stop redis"
            sleep 2
        fi
    fi
    
    # Verify Redis is running
    if redis-cli ping &> /dev/null; then
        REDIS_VERSION=$(redis-cli --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Redis $REDIS_VERSION is running"
    else
        log_error "Redis is installed but not responding"
        exit 1
    fi
    
    export PANEL_REDIS_URL="redis://localhost:6379/0"
else
    read -p "Redis URL (default: redis://localhost:6379/0): " REDIS_URL
    export PANEL_REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
    
    # Test Redis connection
    log_info "Testing Redis connection..."
    if command -v timeout &> /dev/null; then
        if timeout 3 redis-cli -u "$PANEL_REDIS_URL" ping &> /dev/null; then
            log_success "Redis connection successful"
        else
            log_warning "Could not connect to Redis at $PANEL_REDIS_URL"
            read -p "Continue anyway? (y/n): " CONTINUE
            if [[ $CONTINUE != "y" ]]; then
                exit 1
            fi
        fi
    else
        log_warning "timeout command not available, skipping Redis connection test"
    fi
fi

# Generate secret key
if ! command -v openssl &> /dev/null; then
    log_warning "openssl not found. Using python secrets instead."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
else
    SECRET_KEY=$(openssl rand -hex 32)
fi
export PANEL_SECRET_KEY="$SECRET_KEY"

# Create .env file
log_info "Creating configuration file..."

# Backup existing .env if present
if [[ -f ".env" ]]; then
    cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
    log_info "Existing .env backed up"
fi

ENV_TYPE=$(if [[ $ENV_CHOICE -eq 1 ]]; then echo "development"; else echo "production"; fi)

cat > .env << EOF
# Database Configuration
DATABASE_URL=$PANEL_DATABASE_URI
PANEL_DATABASE_URI=$PANEL_DATABASE_URI

# Redis Configuration
REDIS_URL=$PANEL_REDIS_URL
PANEL_REDIS_URL=$PANEL_REDIS_URL

# Application Configuration
SECRET_KEY=$SECRET_KEY
PANEL_SECRET_KEY=$SECRET_KEY
FLASK_ENV=$ENV_TYPE
PANEL_ENV=$ENV_TYPE

# Server Configuration
FLASK_APP=app.py
HOST=0.0.0.0
PORT=5000

# Security
SESSION_COOKIE_SECURE=$(if [[ $ENV_CHOICE -eq 2 ]]; then echo "True"; else echo "False"; fi)
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=$(if [[ $ENV_CHOICE -eq 1 ]]; then echo "DEBUG"; else echo "INFO"; fi)
EOF

# Add development-specific settings if in dev mode
if [[ $DEV_MODE == true ]]; then
    cat >> .env << 'EOF'

# Development Mode Settings
FLASK_DEBUG=True
TESTING=False
EXPLAIN_TEMPLATE_LOADING=True
PRESERVE_CONTEXT_ON_EXCEPTION=True

# Development Tools
SQLALCHEMY_ECHO=True
SQLALCHEMY_RECORD_QUERIES=True
SEND_FILE_MAX_AGE_DEFAULT=0

# Hot reload
FLASK_RUN_RELOAD=True
FLASK_RUN_DEBUGGER=True
EOF
    
    # Install development dependencies
    log_info "Installing development dependencies..."
    pip install -q -r requirements/development.txt || pip install -q pytest pytest-cov black flake8 mypy
    
    # Create development helper scripts
    cat > dev.sh << 'DEVSCRIPT'
#!/bin/bash
# Development helper script

case "${1:-run}" in
    run)
        echo "Starting development server with hot reload..."
        export FLASK_ENV=development
        export FLASK_DEBUG=1
        python -m flask run --reload --debugger
        ;;
    test)
        echo "Running tests..."
        pytest tests/ -v
        ;;
    lint)
        echo "Running linters..."
        black --check .
        flake8 app tests
        mypy app
        ;;
    format)
        echo "Formatting code..."
        black .
        ;;
    shell)
        echo "Starting Flask shell..."
        python -m flask shell
        ;;
    *)
        echo "Usage: ./dev.sh [run|test|lint|format|shell]"
        ;;
esac
DEVSCRIPT
    
    chmod +x dev.sh
    log_success "Development mode configured"
    log_info "Use ./dev.sh to run development server"
fi

# Interactive admin user setup
if [[ $NON_INTERACTIVE != true ]]; then
    echo ""
    log_info "Creating admin user for the application:"
    while true; do
        read -p "Admin username: " ADMIN_USERNAME
        ADMIN_USERNAME=$(sanitize_input "$ADMIN_USERNAME")
        
        # Validate admin username (alphanumeric, 3-16 chars)
        if [[ ! "$ADMIN_USERNAME" =~ ^[a-zA-Z0-9]{3,16}$ ]]; then
            log_error "Invalid username. Only alphanumeric characters, 3-16 chars."
        else
            break
        fi
    done
    
    # Password complexity requirements:
    # - At least 12 characters
    # - Upper and lower case letters
    # - At least one number
    while true; do
        read -p "Admin password: " -s ADMIN_PASSWORD
        echo ""
        read -p "Confirm password: " -s ADMIN_PASSWORD_CONFIRM
        echo ""
        
        # Validate password strength
        if ! validate_password "$ADMIN_PASSWORD"; then
            log_error "Password does not meet security requirements. Please try again."
            continue
        fi
        
        if [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]]; then
            log_error "Passwords do not match. Please re-enter."
            continue
        fi
        
        break
    done
    
    # Create admin user in the database
    log_info "Creating admin user in the database..."
    if [[ $DB_CHOICE -eq 1 ]]; then
        # SQLite
        PASSWORD_HASH=$(printf '%s\n' "$ADMIN_PASSWORD" | python3 -c "from werkzeug.security import generate_password_hash; import sys; print(generate_password_hash(sys.stdin.read().strip()))")
        ADMIN_CREATION_QUERY="INSERT INTO users (username, password_hash, is_admin) VALUES ('$ADMIN_USERNAME', '$PASSWORD_HASH', 1);"
        sqlite3 "$INSTALL_DIR/panel.db" "$ADMIN_CREATION_QUERY" || {
            log_error "Failed to create admin user"
            exit 1
        }
    elif [[ $DB_CHOICE -eq 2 ]]; then
        # PostgreSQL: create role using postgres superuser to avoid CREATEROLE permission issues
          create_pg_role_and_grants() {
                local psql_cmd="$1"
                # Create role if missing; if exists, continue and ensure password is set
                # Avoid complex DO blocks to prevent shell quoting issues
                # Create role (ignore error if it exists)
                $psql_cmd -v ON_ERROR_STOP=0 -c "CREATE ROLE \"$ADMIN_USERNAME\" WITH LOGIN PASSWORD '$ADMIN_PASSWORD';" || true
                # Ensure role has login and correct password
                $psql_cmd -v ON_ERROR_STOP=1 -c "ALTER ROLE \"$ADMIN_USERNAME\" WITH LOGIN PASSWORD '$ADMIN_PASSWORD' LOGIN;" || {
                    log_error "Failed to alter admin role password"
                    return 1
                }
                # Grant privileges on target database
                $psql_cmd -d panel_db -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE panel_db TO \"$ADMIN_USERNAME\";" || {
                    log_error "Failed to grant privileges to admin role"
                    return 1
                }
          }

        # Try with sudo, then without sudo using local postgres user, then TCP auth
        if command -v sudo &> /dev/null && sudo -u postgres psql -c 'SELECT 1;' >/dev/null 2>&1; then
            if create_pg_role_and_grants "sudo -u postgres psql"; then
                log_success "Admin role created and privileges granted in PostgreSQL (sudo)."
            else
                log_error "Failed to create admin role via sudo -u postgres"
                exit 1
            fi
        elif psql -U postgres -c 'SELECT 1;' >/dev/null 2>&1; then
            if create_pg_role_and_grants "psql -U postgres"; then
                log_success "Admin role created and privileges granted in PostgreSQL (local user)."
            else
                log_error "Failed to create admin role via local postgres user"
                exit 1
            fi
        elif psql -h localhost -U postgres -c 'SELECT 1;' >/dev/null 2>&1; then
            if create_pg_role_and_grants "psql -h localhost -U postgres"; then
                log_success "Admin role created and privileges granted in PostgreSQL (localhost)."
            else
                log_error "Failed to create admin role via localhost postgres"
                exit 1
            fi
        else
            log_error "Could not authenticate as postgres superuser to create admin role."
            log_info "Ensure postgres is running and pg_hba.conf allows local connections for postgres user."
            exit 1
        fi
    fi
    
    echo ""
    log_success "Admin user setup complete!"
    echo ""
fi

# Initialize monitoring stack if requested
if [[ $MONITORING == true ]]; then
    log_info "Setting up monitoring with Prometheus & Grafana..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Kubernetes CLI is required for monitoring setup."
        log_info "Please install kubectl from https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    
    # Check if helm is available
    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Helm is required for monitoring setup."
        log_info "Please install Helm from https://helm.sh/docs/intro/install/"
        exit 1
    fi
    
    # Create a dedicated namespace for monitoring
    kubectl create namespace monitoring || log_warning "Monitoring namespace may already exist"
    
    # Install Prometheus using Helm
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    helm install prometheus prometheus-community/prometheus --namespace monitoring || {
        log_error "Failed to install Prometheus"
        exit 1
    }
    
    # Install Grafana using Helm
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    helm install grafana grafana/grafana --namespace monitoring || {
        log_error "Failed to install Grafana"
        exit 1
    }
    
    log_success "Monitoring stack installed: Prometheus and Grafana"
    log_info "Access Grafana at: http://localhost:3000 (admin/admin)"
    log_info "Prometheus metrics available at: http://localhost:9090"
fi

# Setup advanced features
setup_security_hardening() { log_info "Security hardening: not implemented"; }
setup_multi_cloud() { log_info "Multi-cloud setup: not implemented"; }
setup_advanced_backup() { log_info "Advanced backup: not implemented"; }
setup_compliance() { log_info "Compliance setup: not implemented"; }
setup_plugin_system() { log_info "Plugin system: not implemented"; }
setup_advanced_monitoring() { log_info "Advanced monitoring: not implemented"; }
setup_internationalization() { log_info "Internationalization: not implemented"; }
setup_advanced_networking() { log_info "Advanced networking: not implemented"; }
setup_container_orchestration() { log_info "Container orchestration: not implemented"; }
setup_performance_optimization() { log_info "Performance optimization: not implemented"; }

# Auto-deploy the application
log_info "Starting the application..."
if [[ $DEPLOYMENT_TYPE == "development" ]]; then
    log_info "Starting development server..."
    source venv/bin/activate
    nohup python app.py > app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > app.pid
    log_success "Development server started (PID: $APP_PID)"
    log_info "Application is running at http://localhost:5000"
    log_info "Logs: tail -f app.log"
    log_info "Stop: kill $APP_PID"
elif [[ $DEPLOYMENT_TYPE == "production" ]]; then
    if command -v systemctl &> /dev/null && [[ -f /etc/systemd/system/panel.service ]]; then
        log_info "Starting production service..."
        sudo systemctl start panel
        log_success "Production service started"
        log_info "Check status: sudo systemctl status panel"
        log_info "View logs: sudo journalctl -u panel -f"
    else
        log_info "Starting production server..."
        source venv/bin/activate
        if command -v gunicorn &> /dev/null; then
            log_info "Using Gunicorn for production..."
            nohup gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-2} app:app > app.log 2>&1 &
        else
            log_warning "Gunicorn not found, using Python directly..."
            nohup python app.py > app.log 2>&1 &
        fi
        APP_PID=$!
        echo $APP_PID > app.pid
        log_success "Production server started (PID: $APP_PID)"
        log_info "Application is running at http://localhost:5000"
        log_info "Logs: tail -f app.log"
        log_info "Stop: kill $APP_PID"
    fi
fi

# Final messages
log_info "Installation completed. Please follow any post-installation steps above."
show_elapsed_time

echo "🎮 Enhanced Discord Integration:"
echo "   • Real-time server status updates with player counts"
echo "   • Automated alerts for server events and issues"
echo "   • Backup completion notifications"
echo "   • Deployment status updates"
echo "   • Log-based alerts with server statistics"
