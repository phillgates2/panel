#!/usr/bin/env bash
set -euo pipefail

# Panel Quick Installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) [OPTIONS]
#
# Features:
#   ✅ Professional logging infrastructure with audit trails
#   ✅ Database migrations with Flask-Migrate
#   ✅ Security headers (CSP, HSTS, XSS protection)
#   ✅ API rate limiting and DDoS protection
#   ✅ Health check endpoint for monitoring
#   ✅ Input validation with marshmallow
#   ✅ Comprehensive test suite with pytest
#   ✅ Complete documentation suite
#
# Options:
#   --help                Show this help message
#   --dir DIR             Installation directory (default: $HOME/panel)
#   --branch BRANCH       Git branch to install (default: main)
#   --db-type TYPE        Database type: sqlite or mariadb (default: interactive)
#   --skip-mariadb        Skip MariaDB installation
#   --skip-phpmyadmin     Skip phpMyAdmin installation
#   --skip-redis          Skip Redis installation
#   --skip-nginx          Skip Nginx configuration
#   --skip-ssl            Skip SSL/Let's Encrypt setup
#   --non-interactive     Run without prompts (use defaults)
#   --sqlite-only         Quick install with SQLite only
#   --full                Full installation with all components
#   --uninstall           Uninstall Panel and services

REPO_URL="https://github.com/phillgates2/panel.git"
INSTALL_DIR="${PANEL_INSTALL_DIR:-$HOME/panel}"
BRANCH="${PANEL_BRANCH:-main}"

# Installation options (can be overridden by command-line flags)
DB_TYPE=""
SKIP_MARIADB=false
SKIP_PHPMYADMIN=false
SKIP_REDIS=false
SKIP_NGINX=false
SKIP_SSL=false
NON_INTERACTIVE=false
SQLITE_ONLY=false
FULL_INSTALL=false
UNINSTALL_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

show_help() {
    printf "\n"
    printf "${MAGENTA}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}\n"
    printf "${MAGENTA}${BOLD}║                    Panel Installer v2.0                        ║${NC}\n"
    printf "${MAGENTA}${BOLD}║            Modern Game Server Management Platform              ║${NC}\n"
    printf "${MAGENTA}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}\n"
    printf "\n"
    printf "${YELLOW}USAGE:${NC}\n"
    printf "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- [OPTIONS]\n"
    printf "\n"
    printf "${YELLOW}INSTALLATION OPTIONS:${NC}\n"
    printf "  ${GREEN}--help, -h${NC}              Display this help message\n"
    printf "  ${GREEN}--dir DIR${NC}               Set installation directory (default: ~/panel)\n"
    printf "  ${GREEN}--branch BRANCH${NC}         Install from specific git branch (default: main)\n"
    printf "  ${GREEN}--db-type TYPE${NC}          Database: 'sqlite' or 'mariadb' (default: interactive)\n"
    printf "\n"
    printf "${YELLOW}COMPONENT SELECTION:${NC}\n"
    printf "  ${MAGENTA}--full${NC}                  Install everything (recommended for production)\n"
    printf "  ${MAGENTA}--sqlite-only${NC}           Quick dev setup: SQLite only, no extras\n"
    printf "  ${MAGENTA}--skip-mariadb${NC}          Don't install MariaDB server\n"
    printf "  ${MAGENTA}--skip-phpmyadmin${NC}       Don't install phpMyAdmin\n"
    printf "  ${MAGENTA}--skip-redis${NC}            Don't install Redis\n"
    printf "  ${MAGENTA}--skip-nginx${NC}            Don't configure Nginx\n"
    printf "  ${MAGENTA}--skip-ssl${NC}              Don't setup SSL/Let's Encrypt\n"
    printf "\n"
    printf "${YELLOW}AUTOMATION:${NC}\n"
    printf "  ${MAGENTA}--non-interactive${NC}       Unattended install with defaults\n"
    printf "  ${RED}--uninstall${NC}             Remove Panel and all data\n"
    printf "\n"
    printf "${YELLOW}QUICK START EXAMPLES:${NC}\n"
    printf "\n"
    printf "  ${WHITE}# Development (fastest)${NC}\n"
    printf "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --sqlite-only\n"
    printf "\n"
    printf "  ${WHITE}# Production (full featured)${NC}\n"
    printf "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --full\n"
    printf "\n"
    printf "  ${WHITE}# Custom location${NC}\n"
    printf "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --dir /opt/panel\n"
    printf "\n"
    printf "  ${WHITE}# Automated deployment${NC}\n"
    printf "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh | bash -s -- --non-interactive --db-type mariadb\n"
    printf "\n"
    printf "${YELLOW}NEW FEATURES:${NC}\n"
    printf "  ${GREEN}✓${NC} Professional logging with audit trails\n"
    printf "  ${GREEN}✓${NC} Database migrations & version control\n"
    printf "  ${GREEN}✓${NC} Security: CSP, HSTS, rate limiting, SQL injection protection\n"
    printf "  ${GREEN}✓${NC} Health check endpoint for monitoring\n"
    printf "  ${GREEN}✓${NC} Comprehensive test suite & documentation\n"
    printf "  ${GREEN}✓${NC} Input validation & secure sessions\n"
    printf "\n"
    printf "${YELLOW}AFTER INSTALLATION:${NC}\n"
    printf "  ${GREEN}•${NC} Health Check:    ${MAGENTA}http://localhost:8080/health${NC}\n"
    printf "  ${GREEN}•${NC} View Logs:       ${MAGENTA}tail -f instance/logs/panel.log${NC}\n"
    printf "  ${GREEN}•${NC} Documentation:   ${MAGENTA}cat docs/NEW_FEATURES.md${NC}\n"
    printf "  ${GREEN}•${NC} Run Tests:       ${MAGENTA}make test${NC}\n"
    printf "\n"
    printf "${YELLOW}ENVIRONMENT VARIABLES:${NC}\n"
    printf "  ${MAGENTA}PANEL_INSTALL_DIR${NC}      Override default installation directory\n"
    printf "  ${MAGENTA}PANEL_BRANCH${NC}           Override default git branch\n"
    printf "\n"
    printf "${YELLOW}SUPPORT:${NC}\n"
    printf "  Documentation: https://github.com/phillgates2/panel\n"
    printf "  Issues: https://github.com/phillgates2/panel/issues\n"
    printf "\n"
    exit 0
}

# Parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --branch)
                BRANCH="$2"
                shift 2
                ;;
            --db-type)
                DB_TYPE="$2"
                if [[ "$DB_TYPE" != "sqlite" && "$DB_TYPE" != "mariadb" ]]; then
                    error "Invalid --db-type. Must be 'sqlite' or 'mariadb'"
                fi
                shift 2
                ;;
            --skip-mariadb)
                SKIP_MARIADB=true
                shift
                ;;
            --skip-phpmyadmin)
                SKIP_PHPMYADMIN=true
                shift
                ;;
            --skip-redis)
                SKIP_REDIS=true
                shift
                ;;
            --skip-nginx)
                SKIP_NGINX=true
                shift
                ;;
            --skip-ssl)
                SKIP_SSL=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --sqlite-only)
                SQLITE_ONLY=true
                DB_TYPE="sqlite"
                SKIP_MARIADB=true
                SKIP_PHPMYADMIN=true
                shift
                ;;
            --full)
                FULL_INSTALL=true
                DB_TYPE="mariadb"
                shift
                ;;
            --uninstall)
                UNINSTALL_MODE=true
                shift
                ;;
            *)
                error "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
}

print_banner() {
    echo -e "${MAGENTA}${BOLD}"
    cat << 'EOF'
  ____                  _ 
 |  _ \ __ _ _ __   ___| |
 | |_) / _` | '_ \ / _ \ |
 |  __/ (_| | | | |  __/ |
 |_|   \__,_|_| |_|\___|_|
                          
    Modern Game Server Management
EOF
    echo -e "${NC}"
}

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

prompt_input() {
    local prompt="$1"
    local default="$2"
    local secret="${3:-false}"
    local value
    
    # Check for non-interactive mode
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        [[ "$secret" != "true" ]] && log "Using default for '$prompt': $default"
        echo "$default"
        return 0
    fi
    
    # Check if we can read from stdin
    if [[ ! -t 0 ]]; then
        warn "Cannot read input in non-interactive mode, using default: $default"
        echo "$default"
        return 0
    fi
    
    # Output prompt to stderr so it doesn't get captured by command substitution
    if [[ "$secret" == "true" ]]; then
        echo -n -e "${BLUE}$prompt${NC}" >&2
        [[ -n "$default" ]] && echo -n " (default: [hidden])" >&2
        echo -n ": " >&2
        read -s value
        echo >&2
    else
        echo -n -e "${BLUE}$prompt${NC}" >&2
        [[ -n "$default" ]] && echo -n " (default: $default)" >&2
        echo -n ": " >&2
        read value
    fi
    
    # Return just the value or default to stdout
    echo "${value:-$default}"
}

prompt_confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    # Check for non-interactive mode
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        if [[ "$default" == "y" ]]; then
            log "Auto-confirming '$prompt': yes"
            echo "y"; return 0
        else
            log "Auto-declining '$prompt': no"
            echo "n"; return 1
        fi
    fi
    
    # Check if we can read from stdin
    if [[ ! -t 0 ]]; then
        warn "Cannot read input in non-interactive mode, using default: $default"
        if [[ "$default" == "y" ]]; then
            echo "y"; return 0
        else
            echo "n"; return 1
        fi
    fi
    
    while true; do
        echo -n -e "${YELLOW}$prompt${NC} "
        if [[ "$default" == "y" ]]; then
            echo -n "(Y/n): "
        else
            echo -n "(y/N): "
        fi
        read -n 1 response
        echo
        
        case "$response" in
            [yY]) echo "y"; return 0;;
            [nN]) echo "n"; return 1;;
            "") 
                if [[ "$default" == "y" ]]; then
                    echo "y"; return 0
                else
                    echo "n"; return 1
                fi
                ;;
            *) echo -e "${RED}Please answer y or n${NC}";;
        esac
    done
}

configure_mariadb_settings() {
    # Store original values for reset functionality (these don't need to be local)
    ORIGINAL_DB_HOST="$DB_HOST"
    ORIGINAL_DB_PORT="$DB_PORT"
    ORIGINAL_DB_NAME="$DB_NAME"
    ORIGINAL_DB_USER="$DB_USER"
    ORIGINAL_DB_PASS="$DB_PASS"
    
    echo
    echo -e "${BLUE}🔧 MariaDB Settings Configuration${NC}"
    echo -e "${YELLOW}Review and modify your MariaDB connection settings${NC}"
    echo -e "${MAGENTA}Press Enter to keep current value, or type new value${NC}"
    echo
    
    display_mariadb_menu() {
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        echo -e "${BLUE}📋 MariaDB Configuration Menu${NC}"
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        
        # Show current values with visual indicators
        echo -e "  ${BLUE}1)${NC} Host: ${YELLOW}$DB_HOST${NC}"
        echo -e "  ${BLUE}2)${NC} Port: ${YELLOW}$DB_PORT${NC}"
        echo -e "  ${BLUE}3)${NC} Database: ${YELLOW}$DB_NAME${NC}"
        echo -e "  ${BLUE}4)${NC} User: ${YELLOW}$DB_USER${NC}"
        echo -e "  ${BLUE}5)${NC} Password: ${DB_PASS:+${GREEN}[Set - Hidden]${NC}}${DB_PASS:-${RED}[Not Set]${NC}}"
        echo
        echo -e "  ${MAGENTA}6)${NC} 🔍 Test connection with current settings"
        echo -e "  ${YELLOW}7)${NC} 🔄 Reset all to original values"
        echo -e "  ${GREEN}8)${NC} 💾 Save configuration and continue"
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        echo
    }
    
    display_mariadb_menu
    
    while true; do
        echo -n -e "${MAGENTA}Select setting to modify (1-8)${NC} (default: 8): "
        read setting_choice
        setting_choice="${setting_choice:-8}"
        
        case "$setting_choice" in
            1)
                echo
                echo -e "${BLUE}Current host: ${YELLOW}$DB_HOST${NC}"
                echo -n -e "${MAGENTA}Enter new MariaDB Host${NC} (default: $DB_HOST): "
                read NEW_DB_HOST
                NEW_DB_HOST="${NEW_DB_HOST:-$DB_HOST}"
                if [[ "$NEW_DB_HOST" != "$DB_HOST" ]]; then
                    DB_HOST="$NEW_DB_HOST"
                    echo -e "${GREEN}✓ Host updated to: ${BLUE}$DB_HOST${NC}"
                else
                    echo -e "${YELLOW}Host unchanged${NC}"
                fi
                echo
                ;;
            2)
                echo
                echo -e "${BLUE}Current port: ${YELLOW}$DB_PORT${NC}"
                while true; do
                    echo -n -e "${MAGENTA}Enter new MariaDB Port (1-65535)${NC} (default: $DB_PORT): "
                    read NEW_DB_PORT
                    NEW_DB_PORT="${NEW_DB_PORT:-$DB_PORT}"
                    if [[ "$NEW_DB_PORT" =~ ^[0-9]+$ ]] && [[ "$NEW_DB_PORT" -ge 1 ]] && [[ "$NEW_DB_PORT" -le 65535 ]]; then
                        if [[ "$NEW_DB_PORT" != "$DB_PORT" ]]; then
                            DB_PORT="$NEW_DB_PORT"
                            echo -e "${GREEN}✓ Port updated to: ${BLUE}$DB_PORT${NC}"
                        else
                            echo -e "${YELLOW}Port unchanged${NC}"
                        fi
                        break
                    else
                        echo -e "${RED}Please enter a valid port number (1-65535)${NC}"
                    fi
                done
                echo
                ;;
            3)
                echo
                echo -e "${BLUE}Current database: ${YELLOW}$DB_NAME${NC}"
                echo -n -e "${MAGENTA}Enter new Database Name${NC} (default: $DB_NAME): "
                read NEW_DB_NAME
                NEW_DB_NAME="${NEW_DB_NAME:-$DB_NAME}"
                if [[ "$NEW_DB_NAME" != "$DB_NAME" ]]; then
                    DB_NAME="$NEW_DB_NAME"
                    echo -e "${GREEN}✓ Database name updated to: ${BLUE}$DB_NAME${NC}"
                else
                    echo -e "${YELLOW}Database name unchanged${NC}"
                fi
                echo
                ;;
            4)
                echo
                echo -e "${BLUE}Current user: ${YELLOW}$DB_USER${NC}"
                echo -n -e "${MAGENTA}Enter new Database User${NC} (default: $DB_USER): "
                read NEW_DB_USER
                NEW_DB_USER="${NEW_DB_USER:-$DB_USER}"
                if [[ "$NEW_DB_USER" != "$DB_USER" ]]; then
                    DB_USER="$NEW_DB_USER"
                    echo -e "${GREEN}✓ User updated to: ${BLUE}$DB_USER${NC}"
                else
                    echo -e "${YELLOW}User unchanged${NC}"
                fi
                echo
                ;;
            5)
                echo
                echo -e "${BLUE}Current password status: ${DB_PASS:+${GREEN}[Set]${NC}}${DB_PASS:-${RED}[Empty]${NC}}"
                if prompt_confirm "Change database password?" "y"; then
                    while true; do
                        echo
                        echo -n -e "${MAGENTA}Enter new password (leave empty for no password)${NC}: "
                        read -s NEW_DB_PASS
                        echo
                        if [[ -n "$NEW_DB_PASS" ]]; then
                            echo -n -e "${BLUE}Confirm new password${NC}: "
                            read -s DB_PASS_CONFIRM
                            echo
                            if [[ "$NEW_DB_PASS" == "$DB_PASS_CONFIRM" ]]; then
                                DB_PASS="$NEW_DB_PASS"
                                echo -e "${GREEN}✓ Password updated successfully${NC}"
                                break
                            else
                                echo -e "${RED}Passwords do not match. Please try again.${NC}"
                            fi
                        else
                            if prompt_confirm "Use empty password?" "n"; then
                                DB_PASS=""
                                echo -e "${YELLOW}✓ Password cleared (empty)${NC}"
                                break
                            fi
                        fi
                    done
                else
                    echo -e "${YELLOW}Password unchanged${NC}"
                fi
                echo
                ;;
            6)
                echo
                echo -e "${BLUE}🔍 Testing MariaDB connection...${NC}"
                echo -e "${BLUE}Connecting to: ${YELLOW}$DB_USER@$DB_HOST:$DB_PORT${NC}"
                
                if command -v mysql &> /dev/null; then
                    echo -e "${BLUE}Testing connection (this may take a few seconds)...${NC}"
                    
                    # Test connection with timeout and better error handling
                    local connection_success=false
                    
                    if [[ -n "$DB_PASS" ]]; then
                        if timeout 10 mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "SELECT 1 as test;" 2>/dev/null | grep -q "test"; then
                            echo -e "${GREEN}✓ Connection successful!${NC}"
                            echo -e "${GREEN}✓ Authentication with password working${NC}"
                            connection_success=true
                        fi
                    else
                        if timeout 10 mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1 as test;" 2>/dev/null | grep -q "test"; then
                            echo -e "${GREEN}✓ Connection successful!${NC}"
                            echo -e "${GREEN}✓ Passwordless authentication working${NC}"
                            connection_success=true
                        fi
                    fi
                    
                    if [[ "$connection_success" == "false" ]]; then
                        echo -e "${RED}✗ Connection failed${NC}"
                        echo -e "${YELLOW}Possible issues:${NC}"
                        echo -e "  • MariaDB server not running on $DB_HOST:$DB_PORT"
                        if [[ -n "$DB_PASS" ]]; then
                            echo -e "  • Incorrect password for user '$DB_USER'"
                        else
                            echo -e "  • User '$DB_USER' requires a password"
                        fi
                        echo -e "  • User '$DB_USER' doesn't exist or lacks permissions"
                        echo -e "  • Firewall blocking connection"
                        echo -e "  • MariaDB server not accepting connections"
                        echo
                        echo -e "${BLUE}💡 Troubleshooting tips:${NC}"
                        echo -e "  • Check if MariaDB is running: sudo systemctl status mariadb"
                        echo -e "  • Verify user exists: sudo mysql -e \"SELECT User,Host FROM mysql.user WHERE User='$DB_USER';\""
                        echo -e "  • Test root access: sudo mysql"
                    fi
                else
                    echo -e "${YELLOW}⚠️  MariaDB/MySQL client not available for testing${NC}"
                    echo -e "${BLUE}Connection will be tested during installation${NC}"
                fi
                echo
                ;;
            7)
                echo
                echo -e "${YELLOW}🔄 Resetting MariaDB settings to original values...${NC}"
                DB_HOST="$ORIGINAL_DB_HOST"
                DB_PORT="$ORIGINAL_DB_PORT"  
                DB_NAME="$ORIGINAL_DB_NAME"
                DB_USER="$ORIGINAL_DB_USER"
                DB_PASS="$ORIGINAL_DB_PASS"
                echo -e "${GREEN}✓ Settings reset to original values${NC}"
                echo
                ;;
            8)
                echo
                echo -e "${GREEN}💾 Saving MariaDB configuration...${NC}"
                echo -e "${MAGENTA}Final MariaDB settings:${NC}"
                echo -e "  🏠 Host: ${BLUE}$DB_HOST:$DB_PORT${NC}"
                echo -e "  🗄️  Database: ${BLUE}$DB_NAME${NC}"
                echo -e "  👤 User: ${BLUE}$DB_USER${NC}"
                echo -e "  🔑 Password: ${DB_PASS:+${GREEN}[Set]${NC}}${DB_PASS:-${RED}[Empty]${NC}}"
                echo
                return 0
                ;;
            *)
                echo -e "${RED}❌ Invalid selection '$setting_choice'${NC}"
                echo -e "${YELLOW}Please enter a number between 1-8${NC}"
                echo
                ;;
        esac
        
        # Show updated menu after each change
        display_mariadb_menu
    done
}

interactive_config() {
    # Check if running in interactive terminal
    if [[ ! -t 0 ]] || [[ ! -t 1 ]]; then
        warn "Non-interactive terminal detected. Using development defaults."
        warn "For interactive setup, run the script directly: ./getpanel.sh"
        INSTALL_MODE="development"
        DB_TYPE="sqlite"
        ADMIN_USERNAME="admin"
        ADMIN_EMAIL="admin@localhost"
        ADMIN_PASSWORD="${PANEL_ADMIN_PASSWORD:-admin123}"
        APP_HOST="0.0.0.0"
        APP_PORT="8080"
        DEBUG_MODE="true"
        DISABLE_CAPTCHA="false"
        SETUP_NGINX="false"
        SETUP_SSL="false"
        SETUP_SYSTEMD="false"
        SETUP_REDIS="false"
        SETUP_MARIADB="false"
        SETUP_PHPMYADMIN="false"
        DISCORD_WEBHOOK=""
        INSTALL_ML_DEPS="false"
        SECRET_KEY_GENERATE="true"
        ENABLE_LOGGING="true"
        LOG_LEVEL="INFO"
        return 0
    fi
    
    log "🔧 Interactive Configuration"
    echo -e "${MAGENTA}Configure your Panel installation step by step${NC}"
    echo
    
    # Installation mode
    echo -e "${MAGENTA}Installation Mode:${NC}"
    echo "  1) Development (SQLite, quick setup)"
    echo "  2) Production (MariaDB, full setup)"
    echo "  3) Custom (configure everything)"
    echo
    
    while true; do
        echo -n -e "${MAGENTA}Select installation mode (1-3)${NC} (default: 1): "
        read mode
        mode="${mode:-1}"  # Use default if empty
        
        case "$mode" in
            1|dev|development) 
                INSTALL_MODE="development"
                echo -e "${GREEN}✓ Selected: Development mode${NC}"
                break
                ;;
            2|prod|production) 
                INSTALL_MODE="production"
                echo -e "${GREEN}✓ Selected: Production mode${NC}"
                break
                ;;
            3|custom) 
                INSTALL_MODE="custom"
                echo -e "${GREEN}✓ Selected: Custom mode${NC}"
                break
                ;;
            *) 
                echo -e "${RED}Invalid selection '$mode'. Please enter 1, 2, or 3${NC}"
                ;;
        esac
    done
    
    echo
    log "Selected: $INSTALL_MODE mode"
    
    # ============================================================================
    # PRODUCTION MODE: Install and configure database infrastructure FIRST
    # ============================================================================
    if [[ "$INSTALL_MODE" == "production" ]]; then
        echo
        echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}${WHITE}  Production Mode: Database Infrastructure Setup${NC}"
        echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo
        echo -e "${YELLOW}Production deployments require MariaDB and phpMyAdmin.${NC}"
        echo -e "${YELLOW}We'll set these up first to ensure database connectivity.${NC}"
        echo
        
        # Force MariaDB setup for production
        DB_TYPE="mysql"
        SETUP_MARIADB="true"
        
        # MariaDB configuration
        echo -e "${BLUE}📊 MariaDB Database Configuration${NC}"
        echo -e "${YELLOW}Configure your MariaDB connection settings${NC}"
        echo
        
        DB_HOST=$(prompt_input "MariaDB Host" "localhost")
        
        # Port validation for MariaDB
        while true; do
            DB_PORT=$(prompt_input "MariaDB Port" "3306")
            if [[ "$DB_PORT" =~ ^[0-9]+$ ]] && [[ "$DB_PORT" -ge 1 ]] && [[ "$DB_PORT" -le 65535 ]]; then
                break
            else
                echo -e "${RED}Please enter a valid port number (1-65535)${NC}"
            fi
        done
        
        DB_NAME=$(prompt_input "Database Name" "panel")
        DB_USER=$(prompt_input "Database User" "paneluser")
        
        # Password with confirmation
        while true; do
            DB_PASS=$(prompt_input "Database Password (leave empty for no password)" "" "true")
            if [[ -n "$DB_PASS" ]]; then
                DB_PASS_CONFIRM=$(prompt_input "Confirm Database Password" "" "true")
                if [[ "$DB_PASS" == "$DB_PASS_CONFIRM" ]]; then
                    break
                else
                    echo -e "${RED}Passwords do not match. Please try again.${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  Using empty password - ensure MariaDB allows passwordless access for user '$DB_USER'${NC}"
                break
            fi
        done
        
        echo
        echo -e "${GREEN}✓ MariaDB configuration complete${NC}"
        echo -e "  Host: $DB_HOST:$DB_PORT"
        echo -e "  Database: $DB_NAME"
        echo -e "  User: $DB_USER"
        echo
        
        # Install MariaDB immediately
        echo -e "${BOLD}${YELLOW}Installing MariaDB server...${NC}"
        if setup_mariadb; then
            check_section_complete "MariaDB Installation"
            
            # Verify MariaDB is running
            if ! check_mariadb_ready; then
                echo -e "${RED}Failed to verify MariaDB installation${NC}"
                if ! prompt_confirm "Continue anyway? (not recommended)" "n"; then
                    exit 1
                fi
            fi
            
            # Verify database connection
            if ! check_database_connection; then
                echo -e "${RED}Failed to connect to database${NC}"
                if ! prompt_confirm "Continue anyway? (not recommended)" "n"; then
                    exit 1
                fi
            fi
        else
            echo -e "${RED}MariaDB installation failed${NC}"
            if ! prompt_confirm "Continue anyway? (not recommended)" "n"; then
                exit 1
            fi
        fi
        
        # Install phpMyAdmin immediately
        if [[ "$SKIP_PHPMYADMIN" != "true" ]]; then
            echo
            echo -e "${BOLD}${YELLOW}Installing phpMyAdmin for database management...${NC}"
            SETUP_PHPMYADMIN="true"
            
            if setup_phpmyadmin; then
                check_section_complete "phpMyAdmin Installation"
                
                # Verify phpMyAdmin installation
                if ! check_phpmyadmin_ready; then
                    warn "phpMyAdmin installation could not be verified"
                fi
            else
                warn "phpMyAdmin installation encountered issues"
            fi
        else
            SETUP_PHPMYADMIN="false"
            log "Skipping phpMyAdmin installation (--skip-phpmyadmin flag)"
        fi
        
        echo
        echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}${GREEN}  Database Infrastructure Ready!${NC}"
        echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo
        
        if prompt_confirm "Review database configuration summary?" "y"; then
            echo
            echo -e "${BLUE}Database Configuration Summary:${NC}"
            echo -e "  Type: MariaDB"
            echo -e "  Host: $DB_HOST:$DB_PORT"
            echo -e "  Database: $DB_NAME"
            echo -e "  User: $DB_USER"
            echo -e "  phpMyAdmin: http://localhost:8081"
            echo
        fi
    fi
    
    # ============================================================================
    # Database Configuration (for non-production modes)
    # ============================================================================
    if [[ "$INSTALL_MODE" != "production" ]]; then
        echo
        echo -e "${MAGENTA}Database Configuration:${NC}"
        echo -e "${YELLOW}Choose your database backend${NC}"
        
        # Database type selection with mode-specific defaults
        if [[ "$INSTALL_MODE" == "development" ]]; then
            if prompt_confirm "Use SQLite? (recommended for development)" "y"; then
                DB_TYPE="sqlite"
                echo -e "${GREEN}✓ Selected: SQLite${NC}"
            else
                DB_TYPE="mysql"
                echo -e "${GREEN}✓ Selected: MariaDB${NC}"
            fi
        else  # custom mode
            echo "  1) SQLite (simple, file-based)"
            echo "  2) MariaDB (scalable, production-ready)"
            echo
            while true; do
                echo -n -e "${MAGENTA}Select database type (1-2)${NC} (default: 1): "
                read db_choice
                db_choice="${db_choice:-1}"
                
                case "$db_choice" in
                    1|sqlite|SQLite) 
                        DB_TYPE="sqlite"
                        echo -e "${GREEN}✓ Selected: SQLite${NC}"
                        break
                        ;;
                    2|mysql|MySQL|mariadb|MariaDB) 
                        DB_TYPE="mysql"
                        echo -e "${GREEN}✓ Selected: MariaDB${NC}"
                        break
                        ;;
                    *) 
                        echo -e "${RED}Invalid selection '$db_choice'. Please enter 1 or 2${NC}"
                        ;;
                esac
            done
        fi
        
        echo -e "${BLUE}Database Type:${NC} $DB_TYPE"
        
        # MariaDB configuration if selected (non-production modes)
        if [[ "$DB_TYPE" == "mysql" ]]; then
            echo
            echo -e "${BLUE}📊 MariaDB Database Configuration${NC}"
            echo -e "${YELLOW}Configure your MariaDB connection settings${NC}"
            echo
            
            DB_HOST=$(prompt_input "MariaDB Host" "localhost")
            
            # Port validation for MariaDB
            while true; do
                DB_PORT=$(prompt_input "MariaDB Port" "3306")
                if [[ "$DB_PORT" =~ ^[0-9]+$ ]] && [[ "$DB_PORT" -ge 1 ]] && [[ "$DB_PORT" -le 65535 ]]; then
                    break
                else
                    echo -e "${RED}Please enter a valid port number (1-65535)${NC}"
                fi
            done
            
            DB_NAME=$(prompt_input "Database Name" "panel")
            DB_USER=$(prompt_input "Database User" "paneluser")
            
            # Password with confirmation
            while true; do
                DB_PASS=$(prompt_input "Database Password (leave empty for no password)" "" "true")
                if [[ -n "$DB_PASS" ]]; then
                    DB_PASS_CONFIRM=$(prompt_input "Confirm Database Password" "" "true")
                    if [[ "$DB_PASS" == "$DB_PASS_CONFIRM" ]]; then
                        break
                    else
                        echo -e "${RED}Passwords do not match. Please try again.${NC}"
                    fi
                else
                    echo -e "${YELLOW}⚠️  Using empty password - ensure MariaDB allows passwordless access for user '$DB_USER'${NC}"
                    break
                fi
            done
            
            echo
            echo -e "${GREEN}✓ MariaDB configuration complete${NC}"
            echo -e "  Host: $DB_HOST:$DB_PORT"
            echo -e "  Database: $DB_NAME"
            echo -e "  User: $DB_USER"
            echo
            
            # MariaDB setup options (non-production modes)
            echo
            echo -e "${BLUE}MariaDB Installation Options:${NC}"
            
            # Respect command-line flags
            if [[ "$SKIP_MARIADB" == "true" ]]; then
                SETUP_MARIADB="false"
                log "Skipping MariaDB installation (--skip-mariadb flag)"
            elif [[ "$FULL_INSTALL" == "true" ]]; then
                SETUP_MARIADB="true"
                log "Installing MariaDB (--full flag)"
            elif prompt_confirm "Install and configure MariaDB server?" "y"; then
                SETUP_MARIADB="true"
                echo -e "${GREEN}✓ Will install and configure MariaDB server${NC}"
            else
                SETUP_MARIADB="false"
                warn "Assuming MariaDB is already installed and configured"
            fi
            
            # phpMyAdmin setup (non-production modes)
            if [[ "$SKIP_PHPMYADMIN" == "true" ]]; then
                SETUP_PHPMYADMIN="false"
                log "Skipping phpMyAdmin installation (--skip-phpmyadmin flag)"
            elif [[ "$FULL_INSTALL" == "true" ]]; then
                SETUP_PHPMYADMIN="true"
                log "Installing phpMyAdmin (--full flag)"
            elif [[ "$SETUP_MARIADB" == "true" ]] || prompt_confirm "Install phpMyAdmin for database management?" "y"; then
                SETUP_PHPMYADMIN="true"
                echo -e "${GREEN}✓ Will install phpMyAdmin${NC}"
            else
                SETUP_PHPMYADMIN="false"
            fi
        else
            echo
            echo -e "${GREEN}✓ Using SQLite - database will be created automatically${NC}"
            SETUP_MARIADB="false"
            SETUP_PHPMYADMIN="false"
        fi
        
        check_section_complete "Database Configuration"
    fi
    
    # Admin user configuration
    echo
    echo -e "${BLUE}Admin User Setup:${NC}"
    echo -e "${YELLOW}Configure the initial administrator account${NC}"
    ADMIN_USERNAME=$(prompt_input "Admin Username" "admin")
    ADMIN_EMAIL=$(prompt_input "Admin Email" "admin@localhost")
    
    # Password with validation
    while true; do
        ADMIN_PASSWORD=$(prompt_input "Admin Password (min 8 characters)" "" "true")
        if [[ -z "$ADMIN_PASSWORD" ]]; then
            ADMIN_PASSWORD="admin123"
            echo -e "${YELLOW}Using default password: admin123${NC}"
            break
        elif [[ ${#ADMIN_PASSWORD} -ge 8 ]]; then
            break
        else
            echo -e "${RED}Password must be at least 8 characters long${NC}"
        fi
    done
    
    check_section_complete "Admin User Configuration"
    
    # Application settings (always show for better user control)
    echo
    echo -e "${BLUE}Application Settings:${NC}"
    echo -e "${YELLOW}Configure how Panel runs and behaves${NC}"
    
    APP_HOST=$(prompt_input "Application Host (0.0.0.0 for all interfaces)" "0.0.0.0")
    
    # Port validation
    while true; do
        APP_PORT=$(prompt_input "Application Port (1024-65535)" "8080")
        if [[ "$APP_PORT" =~ ^[0-9]+$ ]] && [[ "$APP_PORT" -ge 1024 ]] && [[ "$APP_PORT" -le 65535 ]]; then
            break
        else
            echo -e "${RED}Please enter a valid port number (1024-65535)${NC}"
        fi
    done
    
    # Debug mode
    if [[ "$INSTALL_MODE" == "development" ]]; then
        if prompt_confirm "Enable debug mode? (recommended for development)" "y"; then
            DEBUG_MODE="true"
        else
            DEBUG_MODE="false"
        fi
    else
        if prompt_confirm "Enable debug mode? (not recommended for production)" "n"; then
            DEBUG_MODE="true"
        else
            DEBUG_MODE="false"
        fi
    fi
    
    # CAPTCHA settings
    if prompt_confirm "Disable CAPTCHA for testing/development?" "n"; then
        DISABLE_CAPTCHA="true"
    else
        DISABLE_CAPTCHA="false"
    fi
    
    check_section_complete "Application Settings"
    
    # Security settings
    echo
    echo -e "${BLUE}Security Settings:${NC}"
    if prompt_confirm "Generate random SECRET_KEY? (recommended)" "y"; then
        SECRET_KEY_GENERATE="true"
    else
        SECRET_KEY=$(prompt_input "Custom SECRET_KEY (leave empty for random)" "")
        if [[ -z "$SECRET_KEY" ]]; then
            SECRET_KEY_GENERATE="true"
        else
            SECRET_KEY_GENERATE="false"
        fi
    fi
    
    check_section_complete "Security Configuration"
    
    # Production services
    if [[ "$INSTALL_MODE" == "production" ]] || [[ "$INSTALL_MODE" == "custom" ]]; then
        echo
        echo -e "${BLUE}Production Services:${NC}"
        
        # Nginx setup with flag support
        if [[ "$SKIP_NGINX" == "true" ]]; then
            SETUP_NGINX="false"
            log "Skipping Nginx setup (--skip-nginx flag)"
        elif [[ "$FULL_INSTALL" == "true" ]] || [[ "$INSTALL_MODE" == "production" ]] || prompt_confirm "Configure Nginx reverse proxy?" "y"; then
            SETUP_NGINX="true"
            DOMAIN_NAME=$(prompt_input "Domain name" "panel.localhost")
        else
            SETUP_NGINX="false"
        fi
        
        # SSL setup with flag support
        if [[ "$SKIP_SSL" == "true" ]]; then
            SETUP_SSL="false"
            log "Skipping SSL setup (--skip-ssl flag)"
        elif [[ "$FULL_INSTALL" == "true" ]] || [[ "$INSTALL_MODE" == "production" ]] || prompt_confirm "Setup SSL certificate?" "y"; then
            SETUP_SSL="true"
        else
            SETUP_SSL="false"
        fi
        
        if [[ "$INSTALL_MODE" == "production" ]] || prompt_confirm "Create systemd services?" "y"; then
            SETUP_SYSTEMD="true"
        else
            SETUP_SYSTEMD="false"
        fi
    else
        SETUP_NGINX="false"
        SETUP_SSL="false"
        SETUP_SYSTEMD="false"
    fi
    
    if [[ "$INSTALL_MODE" == "production" ]] || [[ "$INSTALL_MODE" == "custom" ]]; then
        check_section_complete "Production Services Configuration"
    fi
    
    # Optional features (always show for all modes)
    echo
    echo -e "${BLUE}Optional Features & Integrations:${NC}"
    echo -e "${YELLOW}Enable additional functionality and external integrations${NC}"
    
    # Discord integration
    if prompt_confirm "Setup Discord webhooks for notifications?" "n"; then
        DISCORD_WEBHOOK=$(prompt_input "Discord Webhook URL" "")
        if [[ -z "$DISCORD_WEBHOOK" ]]; then
            echo -e "${YELLOW}No webhook URL provided, Discord integration will be disabled${NC}"
        fi
    else
        DISCORD_WEBHOOK=""
    fi
    
    # Redis for background tasks
    if [[ "$SKIP_REDIS" == "true" ]]; then
        SETUP_REDIS="false"
        log "Skipping Redis installation (--skip-redis flag)"
    elif [[ "$FULL_INSTALL" == "true" ]]; then
        SETUP_REDIS="true"
        log "Installing Redis (--full flag)"
    elif [[ "$INSTALL_MODE" == "production" ]]; then
        if prompt_confirm "Enable Redis for background task queue? (recommended for production)" "y"; then
            SETUP_REDIS="true"
        else
            SETUP_REDIS="false"
        fi
    else
        if prompt_confirm "Enable Redis for background task queue?" "n"; then
            SETUP_REDIS="true"
        else
            SETUP_REDIS="false"
        fi
    fi
    
    # ML/Analytics dependencies
    if prompt_confirm "Install ML/Analytics dependencies (numpy, scikit-learn, boto3)?" "n"; then
        INSTALL_ML_DEPS="true"
        echo -e "${BLUE}This will install: numpy, scikit-learn, boto3${NC}"
    else
        INSTALL_ML_DEPS="false"
    fi
    
    check_section_complete "Optional Features"
    
    # Logging configuration
    echo
    echo -e "${BLUE}Logging & Monitoring:${NC}"
    if prompt_confirm "Enable detailed application logging?" "y"; then
        ENABLE_LOGGING="true"
        LOG_LEVEL=$(prompt_input "Log level (DEBUG/INFO/WARNING/ERROR)" "INFO")
        case "${LOG_LEVEL^^}" in
            DEBUG|INFO|WARNING|ERROR) ;;
            *) LOG_LEVEL="INFO"; echo -e "${YELLOW}Invalid log level, using INFO${NC}";;
        esac
    else
        ENABLE_LOGGING="false"
        LOG_LEVEL="WARNING"
    fi
    
    check_section_complete "Logging Configuration"
    
    # Show comprehensive configuration summary
    echo
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${WHITE}  Complete Configuration Summary${NC}"
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    log "📋 Installation Configuration:"
    echo -e "  ${BLUE}Installation Mode:${NC} $INSTALL_MODE"
    echo -e "  ${BLUE}Install Directory:${NC} $INSTALL_DIR"
    echo
    echo -e "  ${BLUE}Database Configuration:${NC}"
    echo -e "    Type: $DB_TYPE"
    if [[ "$DB_TYPE" == "mysql" ]]; then
        echo -e "    MariaDB: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
        echo -e "    MariaDB Installation: ${SETUP_MARIADB}"
        echo -e "    phpMyAdmin: ${SETUP_PHPMYADMIN}"
        [[ "$SETUP_PHPMYADMIN" == "true" ]] && echo -e "    phpMyAdmin Access: http://localhost:8081"
    fi
    echo
    echo -e "  ${BLUE}Application Settings:${NC}"
    echo -e "    Host: $APP_HOST"
    echo -e "    Port: $APP_PORT"
    echo -e "    Debug Mode: $DEBUG_MODE"
    echo -e "    CAPTCHA Disabled: $DISABLE_CAPTCHA"
    echo -e "    Secret Key: ${SECRET_KEY_GENERATE:+[Generated]}${SECRET_KEY:+[Custom]}"
    echo
    echo -e "  ${BLUE}Admin Account:${NC}"
    echo -e "    Username: $ADMIN_USERNAME"
    echo -e "    Email: $ADMIN_EMAIL"
    echo -e "    Password: [Configured]"
    echo
    echo -e "  ${BLUE}Production Services:${NC}"
    echo -e "    Nginx: ${SETUP_NGINX}"
    [[ "$SETUP_NGINX" == "true" ]] && echo -e "    Domain: $DOMAIN_NAME"
    echo -e "    SSL: ${SETUP_SSL}"
    echo -e "    Systemd: ${SETUP_SYSTEMD}"
    echo
    echo -e "  ${BLUE}Optional Features:${NC}"
    echo -e "    Redis Queue: ${SETUP_REDIS}"
    echo -e "    ML/Analytics: ${INSTALL_ML_DEPS}"
    echo -e "    Discord Webhooks: ${DISCORD_WEBHOOK:+Enabled}${DISCORD_WEBHOOK:-Disabled}"
    echo -e "    Logging: ${ENABLE_LOGGING} (Level: ${LOG_LEVEL})"
    echo
    
    if ! prompt_confirm "Proceed with installation?" "y"; then
        error "Installation cancelled by user"
    fi
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check for required commands
    local missing_commands=()
    for cmd in git python3 curl; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        error "Missing required commands: ${missing_commands[*]}"
    fi
    
    # Check Python version (require 3.8+ for modern features)
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    local min_version="3.8"
    local recommended_version="3.11"
    
    if [[ $(echo -e "$python_version\n$min_version" | sort -V | head -n1) != "$min_version" ]]; then
        error "Python 3.8+ required, found $python_version"
    fi
    
    # Recommend newer Python versions
    if [[ $(echo -e "$python_version\n$recommended_version" | sort -V | head -n1) == "$python_version" ]]; then
        warn "Consider upgrading to Python $recommended_version+ for better performance"
    fi
    
    # Python 3.13 compatibility notice
    if [[ $(echo -e "$python_version\n3.13" | sort -V | head -n1) == "3.13" ]]; then
        log "Python $python_version detected - using latest compatible package versions"
    fi
    
    # Check pip version and recommend upgrade if old
    if command -v pip3 &> /dev/null; then
        local pip_version=$(pip3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1)
        if [[ "${pip_version:-0}" -lt 23 ]]; then
            warn "Old pip version detected. Will upgrade during installation."
        fi
    fi
    
    log "✓ All requirements satisfied (Python $python_version)"
}

create_env_file() {
    log "Creating environment configuration..."
    
    cat > .env << EOF
# Panel Configuration
# Generated by Panel installer on $(date)

# Database Configuration
EOF
    
    if [[ "$DB_TYPE" == "sqlite" ]]; then
        cat >> .env << EOF
PANEL_USE_SQLITE=1
EOF
    else
        cat >> .env << EOF
PANEL_DB_HOST=$DB_HOST
PANEL_DB_PORT=$DB_PORT
PANEL_DB_NAME=$DB_NAME
PANEL_DB_USER=$DB_USER
PANEL_DB_PASS=$DB_PASS
EOF
    fi
    
    # Generate or use custom secret key
    if [[ "${SECRET_KEY_GENERATE:-true}" == "true" ]]; then
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)
    fi
    
    cat >> .env << EOF

# Application Settings
PANEL_HOST=$APP_HOST
PANEL_PORT=$APP_PORT
PANEL_DEBUG=$DEBUG_MODE
PANEL_SECRET_KEY=$SECRET_KEY

# Security Settings
PANEL_DISABLE_CAPTCHA=$DISABLE_CAPTCHA

# Admin User
PANEL_ADMIN_USERNAME=$ADMIN_USERNAME
PANEL_ADMIN_EMAIL=$ADMIN_EMAIL
PANEL_ADMIN_PASSWORD=$ADMIN_PASSWORD

# Logging Configuration
PANEL_ENABLE_LOGGING=${ENABLE_LOGGING:-true}
PANEL_LOG_LEVEL=${LOG_LEVEL:-INFO}
EOF
    
    if [[ -n "${DISCORD_WEBHOOK:-}" ]]; then
        cat >> .env << EOF

# Optional Features
PANEL_DISCORD_WEBHOOK=$DISCORD_WEBHOOK
EOF
    fi
    
    if [[ "$SETUP_NGINX" == "true" ]]; then
        cat >> .env << EOF

# Nginx Configuration
PANEL_DOMAIN=$DOMAIN_NAME
PANEL_SETUP_NGINX=true
EOF
    fi
    
    if [[ "$SETUP_SSL" == "true" ]]; then
        cat >> .env << EOF
PANEL_SETUP_SSL=true
EOF
    fi
    
    log "✓ Environment file created"
}

setup_mariadb() {
    log "Setting up MariaDB..."
    
    # Detect package manager if not already set
    if [[ -z "${PKG_MANAGER:-}" ]]; then
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt-get"
            PKG_INSTALL="apt-get install -y"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            PKG_INSTALL="yum install -y"
        elif command -v apk &> /dev/null; then
            PKG_MANAGER="apk"
            PKG_INSTALL="apk add"
        else
            echo -e "${RED}✗ Could not detect package manager${NC}"
            return 1
        fi
    fi
    
    # Install MariaDB server
    case "$PKG_MANAGER" in
        apt-get) 
            if [[ $EUID -eq 0 ]]; then
                $PKG_INSTALL mariadb-server mariadb-client
                # Try both service names (mariadb and mysql)
                systemctl enable mariadb 2>/dev/null || systemctl enable mysql 2>/dev/null
                systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null
            else
                sudo $PKG_INSTALL mariadb-server mariadb-client
                # Try both service names (mariadb and mysql)
                sudo systemctl enable mariadb 2>/dev/null || sudo systemctl enable mysql 2>/dev/null
                sudo systemctl start mariadb 2>/dev/null || sudo systemctl start mysql 2>/dev/null
            fi
            ;;
        yum) 
            if [[ $EUID -eq 0 ]]; then
                $PKG_INSTALL mariadb-server mariadb
                systemctl enable mariadb 2>/dev/null || systemctl enable mysql 2>/dev/null
                systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null
            else
                sudo $PKG_INSTALL mariadb-server mariadb
                sudo systemctl enable mariadb 2>/dev/null || sudo systemctl enable mysql 2>/dev/null
                sudo systemctl start mariadb 2>/dev/null || sudo systemctl start mysql 2>/dev/null
            fi
            ;;
        apk) 
            if [[ $EUID -eq 0 ]]; then
                $PKG_INSTALL mariadb mariadb-client
                rc-update add mariadb default
                /etc/init.d/mariadb setup
                rc-service mariadb start
            else
                sudo $PKG_INSTALL mariadb mariadb-client
                sudo rc-update add mariadb default
                sudo /etc/init.d/mariadb setup
                sudo rc-service mariadb start
            fi
            ;;
    esac
    
    # Wait for MariaDB to start and verify
    log "Waiting for MariaDB to initialize..."
    sleep 5
    
    # Verify service is running
    local service_check_attempts=0
    while [[ $service_check_attempts -lt 6 ]]; do
        if systemctl is-active --quiet mariadb 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then
            log "✓ MariaDB service is active"
            break
        elif rc-service mariadb status 2>/dev/null | grep -q "started" || rc-service mysql status 2>/dev/null | grep -q "started"; then
            log "✓ MariaDB service is active"
            break
        fi
        
        service_check_attempts=$((service_check_attempts + 1))
        if [[ $service_check_attempts -lt 6 ]]; then
            echo -e "${YELLOW}Waiting for MariaDB service... ($service_check_attempts/6)${NC}"
            sleep 2
        else
            warn "MariaDB service may not be running"
            if [[ $EUID -eq 0 ]]; then
                systemctl status mariadb 2>&1 | head -10 || systemctl status mysql 2>&1 | head -10 || true
            else
                sudo systemctl status mariadb 2>&1 | head -10 || sudo systemctl status mysql 2>&1 | head -10 || true
            fi
        fi
    done
    
    # Secure MariaDB installation
    log "Securing MariaDB installation..."
    
    # Set root password and secure installation
    local mysql_root_password=""
    if [[ -t 0 ]] && [[ -t 1 ]]; then
        mysql_root_password=$(prompt_input "Set MariaDB root password (leave empty for no password)" "" "true")
    fi
    
    # Run mysql_secure_installation equivalent
    if [[ -n "$mysql_root_password" ]]; then
        mysql -u root -e "
        SET PASSWORD FOR 'root'@'localhost' = PASSWORD('$mysql_root_password');
        DELETE FROM mysql.user WHERE User='';
        DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
        DROP DATABASE IF EXISTS test;
        DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
        FLUSH PRIVILEGES;
        " 2>/dev/null || warn "Could not secure MariaDB automatically"
    else
        mysql -u root -e "
        DELETE FROM mysql.user WHERE User='';
        DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
        DROP DATABASE IF EXISTS test;
        DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
        FLUSH PRIVILEGES;
        " 2>/dev/null || warn "Could not secure MariaDB automatically"
    fi
    
    log "✓ MariaDB installation complete"
}

# Validation checker functions
check_mariadb_ready() {
    log "Checking MariaDB status..."
    
    local max_attempts=10
    local attempt=0
    
    # First, check if MariaDB service exists - try multiple methods
    local service_exists=false
    local service_name=""
    
    # Check for mariadb service
    if systemctl list-unit-files 2>/dev/null | grep -qE '^mariadb\.service'; then
        service_exists=true
        service_name="mariadb"
    elif systemctl list-unit-files 2>/dev/null | grep -qE '^mysql\.service'; then
        service_exists=true
        service_name="mysql"
    elif rc-service --list 2>/dev/null | grep -q mariadb; then
        service_exists=true
        service_name="mariadb"
    elif rc-service --list 2>/dev/null | grep -q mysql; then
        service_exists=true
        service_name="mysql"
    # Check if mariadb/mysql binaries exist (service might be installed but not via systemd)
    elif command -v mariadbd &>/dev/null || command -v mysqld &>/dev/null; then
        service_exists=true
        service_name="mariadb"
        log "MariaDB binaries found, attempting direct connection..."
    fi
    
    if [[ "$service_exists" == "false" ]]; then
        echo -e "${RED}✗ MariaDB/MySQL service not found${NC}"
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo "  - Check if mariadb-server is installed"
        echo "  - Run: systemctl list-unit-files | grep -i maria"
        echo "  - Run: systemctl list-unit-files | grep -i mysql"
        return 1
    fi
    
    log "Detected service name: $service_name"
    
    # Try to start the service if not running
    if [[ -n "$service_name" ]]; then
        if [[ $EUID -eq 0 ]]; then
            systemctl is-active --quiet "$service_name" || systemctl start "$service_name" 2>/dev/null
        else
            systemctl is-active --quiet "$service_name" || sudo systemctl start "$service_name" 2>/dev/null
        fi
    fi
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Check both mariadb and mysql service names
        local service_running=false
        if systemctl is-active --quiet mariadb 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then
            service_running=true
        elif rc-service mariadb status 2>/dev/null | grep -q "started" || rc-service mysql status 2>/dev/null | grep -q "started"; then
            service_running=true
        fi
        
        if [[ "$service_running" == "true" ]]; then
            # Try to connect
            if mysql -u root -e "SELECT 1;" &>/dev/null; then
                echo -e "${GREEN}✓ MariaDB is running and accessible${NC}"
                return 0
            else
                echo -e "${YELLOW}MariaDB service running but connection failed (attempt $((attempt + 1))/$max_attempts)${NC}"
            fi
        fi
        
        attempt=$((attempt + 1))
        if [[ $attempt -lt $max_attempts ]]; then
            if [[ $attempt -eq 1 ]]; then
                echo -e "${YELLOW}Waiting for MariaDB to start...${NC}"
            fi
            sleep 2
        fi
    done
    
    echo -e "${RED}✗ MariaDB is not running or not accessible${NC}"
    echo -e "${YELLOW}Troubleshooting:${NC}"
    if [[ $EUID -eq 0 ]]; then
        echo "  Check status: systemctl status mariadb"
        echo "  View logs: journalctl -xeu mariadb"
    else
        echo "  Check status: sudo systemctl status mariadb"
        echo "  View logs: sudo journalctl -xeu mariadb"
    fi
    return 1
}

check_phpmyadmin_ready() {
    log "Checking phpMyAdmin installation..."
    
    # Check if phpMyAdmin files exist
    if [[ -d "/var/www/phpmyadmin" ]] && [[ -f "/var/www/phpmyadmin/index.php" ]]; then
        echo -e "${GREEN}✓ phpMyAdmin files installed successfully${NC}"
        
        # Check if Nginx is serving it
        if systemctl is-active --quiet nginx 2>/dev/null || rc-service nginx status 2>/dev/null | grep -q "started"; then
            # Try to access phpMyAdmin
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 | grep -q "200\|302"; then
                echo -e "${GREEN}✓ phpMyAdmin is accessible at http://localhost:8081${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠ phpMyAdmin installed but not yet accessible (Nginx may need configuration)${NC}"
                return 0
            fi
        else
            echo -e "${YELLOW}⚠ phpMyAdmin installed but Nginx is not running${NC}"
            return 0
        fi
    else
        echo -e "${RED}✗ phpMyAdmin installation failed${NC}"
        return 1
    fi
}

check_database_connection() {
    log "Verifying database connection..."
    
    if [[ "$DB_TYPE" == "mysql" ]]; then
        # Build connection command
        local mysql_cmd="mysql -h ${DB_HOST} -P ${DB_PORT} -u ${DB_USER}"
        
        if [[ -n "$DB_PASS" ]]; then
            mysql_cmd="$mysql_cmd -p${DB_PASS}"
        fi
        
        # Try to connect and create database if needed
        if echo "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" | $mysql_cmd 2>/dev/null; then
            echo -e "${GREEN}✓ Database connection successful${NC}"
            echo -e "${GREEN}✓ Database '$DB_NAME' is ready${NC}"
            return 0
        else
            echo -e "${RED}✗ Cannot connect to database${NC}"
            echo -e "${YELLOW}Please verify:${NC}"
            echo -e "  - MariaDB is running"
            echo -e "  - Host: ${DB_HOST}:${DB_PORT}"
            echo -e "  - User: ${DB_USER}"
            echo -e "  - Password is correct"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Using SQLite - database will be created automatically${NC}"
        return 0
    fi
}

check_section_complete() {
    local section_name="$1"
    echo
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ $section_name completed successfully${NC}"
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

setup_phpmyadmin() {
    log "Setting up phpMyAdmin with Nginx..."
    
    # Detect package manager if not already set
    if [[ -z "${PKG_MANAGER:-}" ]]; then
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt-get"
            PKG_INSTALL="apt-get install -y"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            PKG_INSTALL="yum install -y"
        elif command -v apk &> /dev/null; then
            PKG_MANAGER="apk"
            PKG_INSTALL="apk add"
        else
            echo -e "${RED}✗ Could not detect package manager${NC}"
            return 1
        fi
    fi
    
    # Note: Panel has built-in phpMyAdmin at /admin/database
    # This standalone phpMyAdmin is optional
    
    warn "Note: Panel includes built-in database management at /admin/database"
    warn "Standalone phpMyAdmin will be served via Nginx on port 8081"
    
    case "$PKG_MANAGER" in
        apt-get)
            # Install phpMyAdmin without Apache2 dependency
            if [[ $EUID -eq 0 ]]; then
                echo 'phpmyadmin phpmyadmin/dbconfig-install boolean true' | debconf-set-selections
                echo 'phpmyadmin phpmyadmin/app-password-confirm password' | debconf-set-selections
                echo 'phpmyadmin phpmyadmin/mysql/admin-pass password' | debconf-set-selections
                echo 'phpmyadmin phpmyadmin/mysql/app-pass password' | debconf-set-selections
                echo 'phpmyadmin phpmyadmin/reconfigure-webserver multiselect' | debconf-set-selections
                
                # Install phpMyAdmin and PHP-FPM (without Apache2)
                $PKG_INSTALL phpmyadmin php-fpm php-mysql php-mbstring php-zip php-gd php-json php-curl
                
                # Ensure PHP-FPM is running
                # Detect PHP-FPM service name (varies by PHP version)
                PHP_FPM_SERVICE=$(systemctl list-unit-files | grep -E "php[0-9.]*-fpm.service" | head -1 | awk '{print $1}')
                if [[ -n "$PHP_FPM_SERVICE" ]]; then
                    systemctl enable "$PHP_FPM_SERVICE"
                    systemctl start "$PHP_FPM_SERVICE"
                else
                    systemctl enable php-fpm 2>/dev/null || true
                    systemctl start php-fpm 2>/dev/null || true
                fi
                
                # Create symlink for phpMyAdmin web files
                mkdir -p /var/www/phpmyadmin
                ln -sf /usr/share/phpmyadmin/* /var/www/phpmyadmin/ 2>/dev/null || cp -r /usr/share/phpmyadmin/* /var/www/phpmyadmin/
                
                # Create Nginx configuration for phpMyAdmin on port 8081
                cat > /etc/nginx/sites-available/phpmyadmin.conf <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                
                # Enable the site
                ln -sf /etc/nginx/sites-available/phpmyadmin.conf /etc/nginx/sites-enabled/
                
                # Test and reload Nginx
                if nginx -t 2>/dev/null; then
                    systemctl reload nginx
                    log "✓ phpMyAdmin configured successfully on http://localhost:8081/phpmyadmin"
                else
                    warn "Nginx configuration test failed - phpMyAdmin may not be accessible"
                fi
            else
                echo 'phpmyadmin phpmyadmin/dbconfig-install boolean true' | sudo debconf-set-selections
                echo 'phpmyadmin phpmyadmin/app-password-confirm password' | sudo debconf-set-selections
                echo 'phpmyadmin phpmyadmin/mysql/admin-pass password' | sudo debconf-set-selections
                echo 'phpmyadmin phpmyadmin/mysql/app-pass password' | sudo debconf-set-selections
                echo 'phpmyadmin phpmyadmin/reconfigure-webserver multiselect' | sudo debconf-set-selections
                
                # Install phpMyAdmin and PHP-FPM (without Apache2)
                sudo $PKG_INSTALL phpmyadmin php-fpm php-mysql php-mbstring php-zip php-gd php-json php-curl
                
                # Ensure PHP-FPM is running
                # Detect PHP-FPM service name (varies by PHP version)
                PHP_FPM_SERVICE=$(systemctl list-unit-files | grep -E "php[0-9.]*-fpm.service" | head -1 | awk '{print $1}')
                if [[ -n "$PHP_FPM_SERVICE" ]]; then
                    sudo systemctl enable "$PHP_FPM_SERVICE"
                    sudo systemctl start "$PHP_FPM_SERVICE"
                else
                    sudo systemctl enable php-fpm 2>/dev/null || true
                    sudo systemctl start php-fpm 2>/dev/null || true
                fi
                
                # Create symlink for phpMyAdmin web files
                sudo mkdir -p /var/www/phpmyadmin
                sudo ln -sf /usr/share/phpmyadmin/* /var/www/phpmyadmin/ 2>/dev/null || sudo cp -r /usr/share/phpmyadmin/* /var/www/phpmyadmin/
                
                # Create Nginx configuration for phpMyAdmin on port 8081
                sudo tee /etc/nginx/sites-available/phpmyadmin.conf > /dev/null <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                
                # Enable the site
                sudo ln -sf /etc/nginx/sites-available/phpmyadmin.conf /etc/nginx/sites-enabled/
                
                # Test and reload Nginx
                if sudo nginx -t 2>/dev/null; then
                    sudo systemctl reload nginx
                    log "✓ phpMyAdmin configured successfully on http://localhost:8081/phpmyadmin"
                else
                    warn "Nginx configuration test failed - phpMyAdmin may not be accessible"
                fi
            fi
            ;;
        yum|dnf)
            # Install PHP-FPM and phpMyAdmin (Nginx will already be installed)
            if [[ $EUID -eq 0 ]]; then
                $PKG_INSTALL epel-release
                $PKG_INSTALL https://rpms.remirepo.net/enterprise/remi-release-8.rpm || true
                $PKG_INSTALL php-fpm php-mysqlnd php-mbstring php-zip php-gd php-json php-curl
                systemctl enable php-fpm
                systemctl start php-fpm
            else
                sudo $PKG_INSTALL epel-release
                sudo $PKG_INSTALL https://rpms.remirepo.net/enterprise/remi-release-8.rpm || true
                sudo $PKG_INSTALL php-fpm php-mysqlnd php-mbstring php-zip php-gd php-json php-curl
                sudo systemctl enable php-fpm
                sudo systemctl start php-fpm
            fi
            
            # Download and install phpMyAdmin manually
            local pma_version="5.2.1"
            local pma_url="https://files.phpmyadmin.net/phpMyAdmin/${pma_version}/phpMyAdmin-${pma_version}-all-languages.tar.gz"
            
            cd /tmp
            wget "$pma_url" -O phpmyadmin.tar.gz
            tar xzf phpmyadmin.tar.gz
            
            if [[ $EUID -eq 0 ]]; then
                mkdir -p /var/www/phpmyadmin
                cp -r "phpMyAdmin-${pma_version}-all-languages"/* /var/www/phpmyadmin/
                chown -R nginx:nginx /var/www/phpmyadmin
                
                # Create Nginx config for phpMyAdmin on port 8081
                cat > /etc/nginx/conf.d/phpmyadmin.conf <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm/www.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                nginx -t && systemctl reload nginx
            else
                sudo mkdir -p /var/www/phpmyadmin
                sudo cp -r "phpMyAdmin-${pma_version}-all-languages"/* /var/www/phpmyadmin/
                sudo chown -R nginx:nginx /var/www/phpmyadmin
                
                # Create Nginx config for phpMyAdmin on port 8081
                sudo tee /etc/nginx/conf.d/phpmyadmin.conf > /dev/null <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php-fpm/www.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                sudo nginx -t && sudo systemctl reload nginx
            fi
            ;;
        apk)
            # Install PHP-FPM and phpMyAdmin (Nginx will already be installed)
            if [[ $EUID -eq 0 ]]; then
                $PKG_INSTALL php-fpm php php-mysqli php-mbstring php-zip php-gd php-json php-curl
                rc-update add php-fpm default
                rc-service php-fpm start
            else
                sudo $PKG_INSTALL php-fpm php php-mysqli php-mbstring php-zip php-gd php-json php-curl
                sudo rc-update add php-fpm default
                sudo rc-service php-fpm start
            fi
            
            # Download phpMyAdmin
            local pma_version="5.2.1"
            local pma_url="https://files.phpmyadmin.net/phpMyAdmin/${pma_version}/phpMyAdmin-${pma_version}-all-languages.tar.gz"
            
            cd /tmp
            wget "$pma_url" -O phpmyadmin.tar.gz
            tar xzf phpmyadmin.tar.gz
            
            if [[ $EUID -eq 0 ]]; then
                mkdir -p /var/www/phpmyadmin
                cp -r "phpMyAdmin-${pma_version}-all-languages"/* /var/www/phpmyadmin/
                chown -R nginx:nginx /var/www/phpmyadmin
                
                # Create Nginx config for phpMyAdmin
                cat > /etc/nginx/http.d/phpmyadmin.conf <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/run/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                rc-service nginx reload
            else
                sudo mkdir -p /var/www/phpmyadmin
                sudo cp -r "phpMyAdmin-${pma_version}-all-languages"/* /var/www/phpmyadmin/
                sudo chown -R nginx:nginx /var/www/phpmyadmin
                
                # Create Nginx config for phpMyAdmin
                sudo tee /etc/nginx/http.d/phpmyadmin.conf > /dev/null <<'NGINXEOF'
server {
    listen 8081;
    server_name localhost;
    root /var/www/phpmyadmin;
    index index.php;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/run/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINXEOF
                sudo rc-service nginx reload
            fi
            ;;
    esac
    
    log "✓ phpMyAdmin installation complete"
    log "  Standalone phpMyAdmin (Nginx): http://localhost:8081/"
    log "  Panel built-in database manager: http://localhost:8080/admin/database"
}

install_system_deps() {
    if [[ "$INSTALL_MODE" == "development" && "$DB_TYPE" == "sqlite" && "$SETUP_NGINX" == "false" && "$SETUP_REDIS" == "false" ]]; then
        # Skip system deps for simple development setups
        return 0
    fi
    
    log "Installing system dependencies..."
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
        PKG_UPDATE="apt-get update"
        PKG_INSTALL="apt-get install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_UPDATE="yum update -y"
        PKG_INSTALL="yum install -y"
    elif command -v apk &> /dev/null; then
        PKG_MANAGER="apk"
        PKG_UPDATE="apk update"
        PKG_INSTALL="apk add"
    else
        warn "Unknown package manager, skipping system dependencies"
        return 0
    fi
    
    # Update package list
    if [[ $EUID -eq 0 ]]; then
        $PKG_UPDATE
    else
        sudo $PKG_UPDATE
    fi
    
    # Install base dependencies with build essentials and Pillow dependencies
    case "$PKG_MANAGER" in
        apt-get) 
            local packages="python3-venv python3-pip python3-dev build-essential"
            packages="$packages libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev"
            packages="$packages libopenjp2-7-dev libtiff5-dev libwebp-dev libharfbuzz-dev"
            packages="$packages libfribidi-dev libxcb1-dev"
            ;;
        yum) 
            local packages="python3-venv python3-pip python3-devel gcc gcc-c++"
            packages="$packages libjpeg-devel zlib-devel freetype-devel lcms2-devel"
            packages="$packages openjpeg2-devel libtiff-devel libwebp-devel harfbuzz-devel"
            packages="$packages fribidi-devel libxcb-devel"
            ;;
        apk) 
            local packages="python3-dev py3-pip gcc g++ musl-dev"
            packages="$packages jpeg-dev zlib-dev freetype-dev lcms2-dev"
            packages="$packages openjpeg-dev tiff-dev libwebp-dev harfbuzz-dev"
            packages="$packages fribidi-dev libxcb-dev"
            ;;
    esac
    
    if [[ "$DB_TYPE" == "mysql" ]]; then
        case "$PKG_MANAGER" in
            apt-get) packages="$packages mariadb-server libmariadb-dev";;
            yum) packages="$packages mariadb-server mariadb-devel";;
            apk) packages="$packages mariadb mariadb-dev mariadb-client";;
        esac
    fi
    
    if [[ "$SETUP_NGINX" == "true" ]]; then
        packages="$packages nginx"
    fi
    
    if [[ "$SETUP_REDIS" == "true" ]]; then
        packages="$packages redis"
    fi
    
    if [[ "$SETUP_SSL" == "true" ]]; then
        case "$PKG_MANAGER" in
            apt-get) packages="$packages certbot python3-certbot-nginx";;
            yum) packages="$packages certbot python3-certbot-nginx";;
            apk) packages="$packages certbot certbot-nginx";;
        esac
    fi
    
    # Install packages (excluding MariaDB if we're setting it up separately)
    if [[ "$SETUP_MARIADB" != "true" ]]; then
        if [[ $EUID -eq 0 ]]; then
            $PKG_INSTALL $packages
        else
            sudo $PKG_INSTALL $packages
        fi
    else
        # Install packages without MariaDB (we'll set it up separately)
        local filtered_packages=""
        for pkg in $packages; do
            if [[ "$pkg" != *"mariadb"* ]] && [[ "$pkg" != *"mysql"* ]]; then
                filtered_packages="$filtered_packages $pkg"
            fi
        done
        
        if [[ $EUID -eq 0 ]]; then
            $PKG_INSTALL $filtered_packages
        else
            sudo $PKG_INSTALL $filtered_packages
        fi
    fi
    
    log "✓ System dependencies installed"
    
    # Setup MariaDB if requested
    if [[ "$SETUP_MARIADB" == "true" ]]; then
        setup_mariadb
    fi
    
    # Setup phpMyAdmin if requested
    if [[ "$SETUP_PHPMYADMIN" == "true" ]]; then
        setup_phpmyadmin
    fi
}

install_panel() {
    log "Installing Panel to $INSTALL_DIR..."
    
    # Create install directory
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "Directory $INSTALL_DIR already exists"
        if ! prompt_confirm "Continue and overwrite?" "n"; then
            error "Installation cancelled"
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone repository
    log "Cloning repository from $REPO_URL (branch: $BRANCH)..."
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
    
    # Change to install directory
    cd "$INSTALL_DIR"
    
    # Make scripts executable
    chmod +x panel.sh
    chmod +x getpanel.sh
    find scripts -name "*.sh" -exec chmod +x {} \;
    
    # Install system dependencies
    install_system_deps
    
    # Create virtual environment
    log "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip and essential tools to latest versions
    log "Upgrading pip and build tools..."
    pip install --upgrade pip setuptools wheel
    
    # Install Python dependencies with latest versions
    log "Installing Python dependencies..."
    
    # First install/upgrade core build dependencies
    pip install --upgrade pip setuptools wheel Cython
    
    # Install requirements with dependency resolution
    pip install --upgrade -r requirements.txt
    
    # Install optional ML dependencies if requested
    if [[ "${INSTALL_ML_DEPS:-}" == "true" ]]; then
        log "Installing optional ML/Analytics dependencies..."
        
        # Check Python version for ML compatibility
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
        if [[ $(echo -e "$python_version\n3.13" | sort -V | head -n1) == "3.13" ]]; then
            log "Python $python_version detected - using latest ML package versions"
            pip install --upgrade numpy>=1.26.0 scikit-learn>=1.4.0 boto3>=1.35.0
        elif [[ $(echo -e "$python_version\n3.11" | sort -V | head -n1) == "3.11" ]]; then
            log "Python $python_version detected - using stable ML package versions"
            pip install --upgrade numpy>=1.24.0 scikit-learn>=1.3.0 boto3>=1.34.0
        else
            log "Python $python_version detected - using compatible ML package versions"
            pip install --upgrade numpy>=1.21.0 scikit-learn>=1.1.0 boto3>=1.30.0
        fi
    fi
    
    # Verify critical packages are installed
    log "Verifying installation..."
    python3 -c "import flask, sqlalchemy, PIL, gunicorn; print('✓ Core dependencies verified')" || error "Failed to verify core dependencies"
    
    # Create environment file
    create_env_file
    
    # Initialize database
    log "Initializing database..."
    if [[ "$DB_TYPE" == "mysql" ]]; then
        # Setup MariaDB database
        if command -v mysql &> /dev/null; then
            log "Setting up MariaDB database and user..."
            
            # First check if MariaDB server is actually running
            if ! pgrep -x "mysqld\|mariadbd" >/dev/null 2>&1 && ! ss -tlnp 2>/dev/null | grep -q ":3306 " 2>/dev/null; then
                warn "⚠️  MariaDB server does not appear to be running"
                warn "In development environments, consider using SQLite instead"
                warn ""
                
                if [[ -t 0 ]] && [[ -t 1 ]] && prompt_confirm "Switch to SQLite for this installation?" "y"; then
                    log "Switching to SQLite database..."
                    DB_TYPE="sqlite"
                    # Update .env file if it exists
                    if [[ -f ".env" ]]; then
                        sed -i '/^PANEL_DB_/d' .env
                        echo "PANEL_USE_SQLITE=1" >> .env
                    fi
                else
                    warn "Continuing with MariaDB setup (may fail if server not available)..."
                fi
            fi
            
            # Try different authentication methods for MariaDB root access
            local mysql_auth_success=false
            local mysql_cmd=""
            
            # Method 1: Try with sudo (unix_socket authentication) - most common on modern systems
            log "Attempting MariaDB authentication via unix_socket..."
            if [[ $EUID -eq 0 ]]; then
                mysql_cmd="mysql -u root"
            else
                mysql_cmd="sudo mysql -u root"
            fi
            
            # Test connection and create database/user (suppress error output for clean testing)
            if $mysql_cmd -e "SELECT 1 as test;" >/dev/null 2>&1; then
                log "Using sudo/root authentication for MariaDB setup"
                
                # Create database
                log "Creating database: $DB_NAME"
                $mysql_cmd -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || warn "Database $DB_NAME may already exist"
                
                # Create users
                log "Creating database user: $DB_USER"
                if [[ -n "$DB_PASS" ]]; then
                    $mysql_cmd -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER may already exist"
                    $mysql_cmd -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER@% may already exist"
                else
                    $mysql_cmd -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost';" || warn "User $DB_USER may already exist"
                    $mysql_cmd -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%';" || warn "User $DB_USER@% may already exist"
                fi
                
                # Grant privileges
                log "Granting privileges to $DB_USER on $DB_NAME"
                $mysql_cmd -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';" || warn "Failed to grant privileges to $DB_USER@localhost"
                $mysql_cmd -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';" || warn "Failed to grant privileges to $DB_USER@%"
                $mysql_cmd -e "FLUSH PRIVILEGES;" || warn "Failed to flush privileges"
                
                # Verify database was created
                if $mysql_cmd -e "USE \`$DB_NAME\`; SELECT 1;" >/dev/null 2>&1; then
                    mysql_auth_success=true
                    log "✓ Database '$DB_NAME' created and verified"
                    log "✓ User '$DB_USER' created with full privileges"
                    log "✓ MariaDB setup completed successfully via unix_socket"
                else
                    warn "Database creation verification failed"
                    mysql_auth_success=false
                fi
                
            else
                log "Unix_socket authentication failed, trying password authentication..."
                
                # Method 2: Try with empty root password (default on some installations)
                if mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "SELECT 1 as test;" >/dev/null 2>&1; then
                    log "Using empty root password for MariaDB setup"
                    
                    log "Creating database: $DB_NAME"
                    mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || warn "Database $DB_NAME may already exist"
                    
                    log "Creating database user: $DB_USER"
                    if [[ -n "$DB_PASS" ]]; then
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER may already exist"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER@% may already exist"
                    else
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost';" || warn "User $DB_USER may already exist"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%';" || warn "User $DB_USER@% may already exist"
                    fi
                    
                    log "Granting privileges to $DB_USER on $DB_NAME"
                    mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';" || warn "Failed to grant privileges to $DB_USER@localhost"
                    mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';" || warn "Failed to grant privileges to $DB_USER@%"
                    mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "FLUSH PRIVILEGES;" || warn "Failed to flush privileges"
                    
                    # Verify database was created
                    if mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "USE \`$DB_NAME\`; SELECT 1;" >/dev/null 2>&1; then
                        mysql_auth_success=true
                        log "✓ Database '$DB_NAME' created and verified"
                        log "✓ User '$DB_USER' created with full privileges"
                        log "✓ MariaDB setup completed successfully via password authentication"
                    else
                        warn "Database creation verification failed"
                        mysql_auth_success=false
                    fi
                    
                # Method 3: Try interactive password prompt (last resort)
                elif [[ -t 0 ]] && [[ -t 1 ]]; then
                    log "Attempting interactive root password authentication..."
                    echo -e "${BLUE}MariaDB root password required for database setup${NC}"
                    
                    if mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "SELECT 1 as test;" >/dev/null 2>&1; then
                        log "Using interactive root password for MariaDB setup"
                        
                        log "Creating database: $DB_NAME"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || warn "Database $DB_NAME may already exist"
                        
                        log "Creating database user: $DB_USER"
                        if [[ -n "$DB_PASS" ]]; then
                            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER may already exist"
                            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';" || warn "User $DB_USER@% may already exist"
                        else
                            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost';" || warn "User $DB_USER may already exist"
                            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%';" || warn "User $DB_USER@% may already exist"
                        fi
                        
                        log "Granting privileges to $DB_USER on $DB_NAME"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';" || warn "Failed to grant privileges to $DB_USER@localhost"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';" || warn "Failed to grant privileges to $DB_USER@%"
                        mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "FLUSH PRIVILEGES;" || warn "Failed to flush privileges"
                        
                        # Verify database was created
                        if mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p -e "USE \`$DB_NAME\`; SELECT 1;" >/dev/null 2>&1; then
                            mysql_auth_success=true
                            log "✓ Database '$DB_NAME' created and verified"
                            log "✓ User '$DB_USER' created with full privileges"
                            log "✓ MariaDB setup completed successfully via interactive password"
                        else
                            warn "Database creation verification failed"
                            mysql_auth_success=false
                        fi
                    else
                        mysql_auth_success=false
                    fi
                else
                    mysql_auth_success=false
                fi
            fi
            
            # If all authentication methods failed, provide manual instructions
            if [[ "$mysql_auth_success" == "false" ]]; then
                warn "❌ All MariaDB authentication methods failed"
                warn "This usually happens when:"
                warn "  • MariaDB is not running"
                warn "  • Root password is set but not provided"
                warn "  • MariaDB security plugin configuration is strict"
                warn ""
                warn "🔧 Manual database setup required:"
                warn "  1. Start MariaDB service:"
                warn "     sudo systemctl start mariadb"
                warn ""
                warn "  2. Secure MariaDB installation (if not done):"
                warn "     sudo mysql_secure_installation"
                warn ""
                warn "  3. Create database and user manually:"
                warn "     sudo mysql"
                warn "     CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                if [[ -n "$DB_PASS" ]]; then
                    warn "     CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';"
                    warn "     CREATE USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
                else
                    warn "     CREATE USER '$DB_USER'@'localhost';"
                    warn "     CREATE USER '$DB_USER'@'%';"
                fi
                warn "     GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';"
                warn "     GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';"
                warn "     FLUSH PRIVILEGES;"
                warn "     EXIT;"
                warn ""
                warn "  4. Then re-run the Panel installer"
                warn ""
                warn "💡 Alternative: Use SQLite for development:"
                warn "     Set DB_TYPE=sqlite in your configuration"
            fi
        else
            warn "MariaDB/MySQL client not found, skipping database setup"
            warn "Please install MariaDB client and manually create:"
            warn "  Database: $DB_NAME"
            warn "  User: $DB_USER"
        fi
    fi
    
    # Initialize application database schema
    log "Setting up database schema..."
    
    # Check if migrations directory exists
    if [[ -d "migrations" ]]; then
        log "Using Flask-Migrate for database schema..."
        
        # Run migrations
        if [[ "$DB_TYPE" == "sqlite" ]]; then
            PANEL_USE_SQLITE=1 python3 -c "
from flask_migrate import upgrade
from app import app
with app.app_context():
    upgrade()
    print('✓ Database schema migrated successfully')
" 2>&1 | grep -v "INFO" || log "Database migrations applied"
        else
            python3 -c "
from flask_migrate import upgrade
from app import app
with app.app_context():
    upgrade()
    print('✓ Database schema migrated successfully')
" 2>&1 | grep -v "INFO" || log "Database migrations applied"
        fi
    else
        # Fallback to create_all if migrations not initialized
        log "Using db.create_all() for database schema..."
        
        if [[ "$DB_TYPE" == "sqlite" ]]; then
            PANEL_USE_SQLITE=1 python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✓ Database schema created successfully')
"
        else
            python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✓ Database schema created successfully')
"
        fi
    fi
    
    # Create admin user
    log "Creating admin user..."
    if [[ "$DB_TYPE" == "sqlite" ]]; then
        PANEL_USE_SQLITE=1 python3 -c "
from app import app, db, User
with app.app_context():
    admin = User.query.filter_by(username='$ADMIN_USERNAME').first()
    if not admin:
        admin = User(
            username='$ADMIN_USERNAME',
            email='$ADMIN_EMAIL',
            role='system_admin'
        )
        admin.set_password('$ADMIN_PASSWORD')
        db.session.add(admin)
        db.session.commit()
        print('✓ Admin user created: $ADMIN_USERNAME')
    else:
        print('✓ Admin user already exists: $ADMIN_USERNAME')
"
    else
        python3 -c "
from app import app, db, User
with app.app_context():
    admin = User.query.filter_by(username='$ADMIN_USERNAME').first()
    if not admin:
        admin = User(
            username='$ADMIN_USERNAME',
            email='$ADMIN_EMAIL',
            role='system_admin'
        )
        admin.set_password('$ADMIN_PASSWORD')
        db.session.add(admin)
        db.session.commit()
        print('✓ Admin user created: $ADMIN_USERNAME')
    else:
        print('✓ Admin user already exists: $ADMIN_USERNAME')
"
    fi
    
    log "✓ Database initialization complete"
    
    # Setup production services
    if [[ "$SETUP_SYSTEMD" == "true" ]]; then
        setup_systemd_services
    fi
    
    if [[ "$SETUP_NGINX" == "true" ]]; then
        setup_nginx_config
    fi
    
    if [[ "$SETUP_SSL" == "true" ]]; then
        setup_ssl_certificate
    fi
    
    log "✓ Installation complete!"
}

setup_systemd_services() {
    log "Setting up systemd services..."
    
    # Copy service files
    if [[ $EUID -eq 0 ]]; then
        cp deploy/panel-gunicorn.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable panel-gunicorn.service
    else
        sudo cp deploy/panel-gunicorn.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable panel-gunicorn.service
    fi
    
    log "✓ Systemd services configured"
}

setup_nginx_config() {
    log "Setting up Nginx configuration..."
    
    # Create nginx config from template
    sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" deploy/nginx_game_chrisvanek.conf > /tmp/panel.conf
    
    if [[ $EUID -eq 0 ]]; then
        cp /tmp/panel.conf /etc/nginx/sites-available/panel.conf
        ln -sf /etc/nginx/sites-available/panel.conf /etc/nginx/sites-enabled/
        nginx -t && systemctl reload nginx
    else
        sudo cp /tmp/panel.conf /etc/nginx/sites-available/panel.conf
        sudo ln -sf /etc/nginx/sites-available/panel.conf /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
    fi
    
    log "✓ Nginx configuration complete"
}

setup_ssl_certificate() {
    log "Setting up SSL certificate..."
    
    if command -v certbot &> /dev/null; then
        if [[ $EUID -eq 0 ]]; then
            certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --email "$ADMIN_EMAIL"
        else
            sudo certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --email "$ADMIN_EMAIL"
        fi
        log "✓ SSL certificate configured"
    else
        warn "Certbot not found, skipping SSL setup"
    fi
}

show_next_steps() {
    echo
    echo -e "${GREEN}🎉 Panel installed successfully!${NC}"
    echo
    echo -e "${MAGENTA}Configuration Summary:${NC}"
    echo "  📁 Install Directory: $INSTALL_DIR"
    echo "  🗄️ Database: $DB_TYPE"
    echo "  👤 Admin User: $ADMIN_USERNAME"
    echo "  📧 Admin Email: $ADMIN_EMAIL"
    echo "  🌐 Port: $APP_PORT"
    [[ "$SETUP_NGINX" == "true" ]] && echo "  🔗 Domain: https://$DOMAIN_NAME"
    [[ "$SETUP_SSL" == "true" ]] && echo "  🔒 SSL: Enabled"
    echo
    
    echo -e "${MAGENTA}✨ New Features Included:${NC}"
    echo "  🔒 Security: Rate limiting, SQL injection detection, audit logging"
    echo "  📊 Monitoring: /health endpoint, structured logging, metrics tracking"
    echo "  🧪 Testing: Comprehensive test suite with pytest"
    echo "  📝 Documentation: Complete guides in docs/ directory"
    echo "  🛠️ DevTools: Makefile, pre-commit hooks, Docker dev environment"
    echo "  🔐 Hardened: CSP headers, HSTS, input validation, secure sessions"
    echo "  🎛️ Database: phpMyAdmin integration, query validation, backups"
    echo "  ⚡ Performance: Query optimization, caching ready, migrations"
    echo
    
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  ${WHITE}1.${NC} Navigate to the installation directory:"
    echo "     ${MAGENTA}cd $INSTALL_DIR${NC}"
    echo
    
    if [[ "$INSTALL_MODE" == "development" ]]; then
        echo "  2. Start Panel in development mode:"
        echo "     source venv/bin/activate"
        echo "     PANEL_USE_SQLITE=1 python app.py"
        echo
        echo "  3. Access the web interface:"
        echo "     http://localhost:$APP_PORT"
    elif [[ "$SETUP_SYSTEMD" == "true" ]]; then
        echo "  2. Start Panel services:"
        echo "     sudo systemctl start panel-gunicorn"
        echo
        echo "  3. Access the web interface:"
        if [[ "$SETUP_NGINX" == "true" ]]; then
            echo "     https://$DOMAIN_NAME"
        else
            echo "     http://localhost:$APP_PORT"
        fi
    else
        echo "  2. Start Panel manually:"
        echo "     source venv/bin/activate"
        echo "     source .env"
        echo "     gunicorn -w 4 -b 0.0.0.0:$APP_PORT app:app"
        echo
        echo "  3. Access the web interface:"
        echo "     http://localhost:$APP_PORT"
    fi
    
    echo
    echo -e "${MAGENTA}Login Credentials:${NC}"
    echo "  Username: $ADMIN_USERNAME"
    echo "  Password: [as configured during setup]"
    
    # Show database management info
    if [[ "$SETUP_PHPMYADMIN" == "true" ]]; then
        echo
        echo -e "${MAGENTA}Database Management:${NC}"
        echo "  Panel Built-in: http://localhost:$APP_PORT/admin/database"
        echo "  Standalone phpMyAdmin (Nginx): http://localhost:8081/"
        echo
        echo "  Note: Both use the same database credentials"
        
        if [[ "$SETUP_MARIADB" == "true" ]]; then
            echo "  MariaDB Root: Use root credentials set during installation"
        fi
        echo "  Panel DB User: $DB_USER (for database: $DB_NAME)"
    elif [[ "$DB_TYPE" == "mysql" ]] || [[ "$DB_TYPE" == "mariadb" ]]; then
        echo
        echo -e "${MAGENTA}Database Management:${NC}"
        echo "  Panel Built-in: http://localhost:$APP_PORT/admin/database"
        echo "  Database: $DB_NAME on $DB_HOST:$DB_PORT"
        echo "  User: $DB_USER"
        echo "  MySQL client: mysql -h $DB_HOST -u $DB_USER -p $DB_NAME"
    else
        echo
        echo -e "${MAGENTA}Database Management:${NC}"
        echo "  Panel Built-in: http://localhost:$APP_PORT/admin/database"
        echo "  SQLite database: $INSTALL_DIR/panel_dev.db"
    fi
    echo
    
    echo -e "${YELLOW}Useful commands:${NC}"
    echo "  ${MAGENTA}./panel.sh start${NC}      # Start development server"
    echo "  ${MAGENTA}./panel.sh start-prod${NC} # Start production server"
    echo "  ${MAGENTA}./panel.sh status${NC}     # Check service status"
    echo "  ${MAGENTA}./panel.sh update${NC}     # Update installation"
    echo "  ${MAGENTA}./panel.sh uninstall${NC}  # Remove installation"
    echo "  ${MAGENTA}make test${NC}             # Run test suite"
    echo "  ${MAGENTA}make lint${NC}             # Check code quality"
    echo "  ${MAGENTA}make db-migrate${NC}       # Create database migration"
    echo
    
    echo -e "${MAGENTA}Configuration files:${NC}"
    echo "  ${MAGENTA}.env${NC}                  # Environment variables (copy from .env.example)"
    echo "  ${MAGENTA}config.py${NC}             # Application configuration"
    echo
    
    echo -e "${GREEN}Documentation:${NC}"
    echo "  ${MAGENTA}README.md${NC}             # Main documentation"
    echo "  ${MAGENTA}docs/NEW_FEATURES.md${NC}  # New features guide"
    echo "  ${MAGENTA}docs/DATABASE_MANAGEMENT.md${NC}  # Database admin guide"
    echo "  ${MAGENTA}docs/API_DOCUMENTATION.md${NC}    # REST API reference"
    echo "  ${MAGENTA}docs/TROUBLESHOOTING.md${NC}      # Common issues & solutions"
    echo "  ${MAGENTA}CHANGELOG.md${NC}          # Version history"
    echo
    
    echo -e "${YELLOW}Monitoring & Health:${NC}"
    echo "  ${MAGENTA}http://localhost:$APP_PORT/health${NC}  # Health check endpoint"
    echo "  ${MAGENTA}instance/logs/panel.log${NC}            # Application logs"
    echo "  ${MAGENTA}instance/audit_logs/${NC}               # Security audit logs"
    echo
}

uninstall_panel() {
    print_banner
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo -e "${RED}  Panel Uninstaller${NC}"
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo
    
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "Panel installation not found at: $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    warn "This will remove Panel and all its data!"
    echo
    echo "The following will be removed:"
    echo "  - Panel application directory: $INSTALL_DIR"
    echo "  - Python virtualenv"
    echo "  - Database and instance files"
    echo "  - Log files and audit logs"
    echo "  - Database backups"
    echo "  - Systemd services (if installed)"
    echo "  - Nginx configuration (if installed)"
    echo
    
    if ! prompt_confirm "Are you sure you want to uninstall Panel?" "n"; then
        log "Uninstall cancelled"
        exit 0
    fi
    
    # Stop services
    if command -v systemctl >/dev/null 2>&1; then
        log "Stopping systemd services..."
        $SUDO systemctl stop panel-gunicorn.service 2>/dev/null || true
        $SUDO systemctl stop rq-worker-supervised.service 2>/dev/null || true
        $SUDO systemctl stop panel-etlegacy.service 2>/dev/null || true
        $SUDO systemctl disable panel-gunicorn.service 2>/dev/null || true
        $SUDO systemctl disable rq-worker-supervised.service 2>/dev/null || true
        $SUDO systemctl disable panel-etlegacy.service 2>/dev/null || true
        
        # Remove service files
        $SUDO rm -f /etc/systemd/system/panel-gunicorn.service
        $SUDO rm -f /etc/systemd/system/rq-worker-supervised.service
        $SUDO rm -f /etc/systemd/system/panel-etlegacy.service
        $SUDO systemctl daemon-reload
    fi
    
    # Remove Nginx configuration
    if [[ -f /etc/nginx/sites-enabled/panel ]]; then
        log "Removing Nginx configuration..."
        $SUDO rm -f /etc/nginx/sites-enabled/panel
        $SUDO rm -f /etc/nginx/sites-available/panel
        $SUDO systemctl reload nginx 2>/dev/null || true
    fi
    
    # Remove log files and backups
    log "Removing logs and backups..."
    rm -rf "$INSTALL_DIR/instance/logs" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/instance/audit_logs" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/instance/backups" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/backups" 2>/dev/null || true
    rm -rf "$INSTALL_DIR"/*.log 2>/dev/null || true
    
    # Remove installation directory
    log "Removing Panel directory: $INSTALL_DIR"
    cd "$HOME"
    rm -rf "$INSTALL_DIR"
    
    log "✅ Panel uninstalled successfully"
    echo
    echo -e "${BLUE}To reinstall Panel:${NC}"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)"
}

main() {
    # Parse command-line arguments first
    parse_args "$@"
    
    # Handle uninstall mode
    if [[ "$UNINSTALL_MODE" == "true" ]]; then
        uninstall_panel
        exit 0
    fi
    
    print_banner
    
    # Show installation mode
    if [[ "$SQLITE_ONLY" == "true" ]]; then
        echo -e "${MAGENTA}📦 Quick Installation Mode: SQLite Only${NC}"
        echo
    elif [[ "$FULL_INSTALL" == "true" ]]; then
        echo -e "${MAGENTA}🚀 Full Installation Mode: All Components${NC}"
        echo
    elif [[ "$NON_INTERACTIVE" == "true" ]]; then
        echo -e "${MAGENTA}⚡ Non-Interactive Mode: Using Defaults${NC}"
        echo
    fi
    
    # Check if running via curl and provide guidance
    if [[ ! -t 0 ]] && [[ "${PANEL_NONINTERACTIVE:-}" != "true" ]] && [[ "$NON_INTERACTIVE" != "true" ]]; then
        echo -e "${YELLOW}⚠️  Running in non-interactive mode (curl pipe detected)${NC}"
        echo -e "${YELLOW}   Using development defaults for quick setup.${NC}"
        echo
        echo -e "${BLUE}For full interactive configuration:${NC}"
        echo "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh -o getpanel.sh"
        echo "  chmod +x getpanel.sh && ./getpanel.sh"
        echo
        echo -e "${BLUE}Or use command-line options:${NC}"
        echo "  bash <(curl -fsSL ...) --sqlite-only  # Quick SQLite install"
        echo "  bash <(curl -fsSL ...) --full         # Full install"
        echo "  bash <(curl -fsSL ...) --help         # Show all options"
        echo
        echo -e "${BLUE}Proceeding with development setup in 3 seconds...${NC}"
        sleep 3
        echo
    fi
    
    log "Panel Interactive Installer"
    log "Install directory: $INSTALL_DIR"
    log "Repository branch: $BRANCH"
    echo
    
    check_requirements
    
    # Skip interactive config if running non-interactively or with specific modes
    if [[ "${PANEL_NONINTERACTIVE:-}" == "true" ]] || [[ "$NON_INTERACTIVE" == "true" ]] || [[ "$SQLITE_ONLY" == "true" ]]; then
        log "Running in non-interactive mode with defaults"
        INSTALL_MODE="development"
        DB_TYPE="${DB_TYPE:-sqlite}"
        ADMIN_USERNAME="admin"
        ADMIN_EMAIL="admin@localhost"
        ADMIN_PASSWORD="${PANEL_ADMIN_PASSWORD:-admin123}"
        APP_HOST="0.0.0.0"
        APP_PORT="8080"
        DEBUG_MODE="true"
        DISABLE_CAPTCHA="false"
        SETUP_NGINX="false"
        SETUP_SSL="false"
        SETUP_SYSTEMD="false"
        SETUP_REDIS="false"
        SETUP_MARIADB="false"
        SETUP_PHPMYADMIN="false"
        DISCORD_WEBHOOK=""
        INSTALL_ML_DEPS="false"
        SECRET_KEY_GENERATE="true"
        ENABLE_LOGGING="true"
        LOG_LEVEL="INFO"
    else
        interactive_config
    fi
    
    install_panel
    show_next_steps
}

uninstall_panel() {
    log "🗑️ Panel Uninstaller"
    echo
    
    # Check if installation exists
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "Panel installation not found at $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    
    # Show what will be removed
    echo -e "${YELLOW}The following will be removed:${NC}"
    echo "  📁 Installation directory: $INSTALL_DIR"
    echo "  📝 Log files and audit logs"
    echo "  💾 Database backups"
    
    # Check for services
    local services_found=()
    if systemctl is-enabled panel-gunicorn.service &>/dev/null; then
        services_found+=("panel-gunicorn.service")
    fi
    if systemctl is-enabled rq-worker-supervised.service &>/dev/null; then
        services_found+=("rq-worker-supervised.service")
    fi
    
    if [[ ${#services_found[@]} -gt 0 ]]; then
        echo "  🔧 Systemd services: ${services_found[*]}"
    fi
    
    # Check for nginx config
    if [[ -f "/etc/nginx/sites-enabled/panel.conf" ]]; then
        echo "  🌐 Nginx configuration: /etc/nginx/sites-*/panel.conf"
    fi
    
    # Check for database
    if [[ -f "instance/panel_dev.db" ]]; then
        echo "  🗄️ SQLite database: instance/panel_dev.db"
    fi
    
    echo
    warn "This action cannot be undone!"
    
    if ! prompt_confirm "Are you sure you want to uninstall Panel?" "n"; then
        log "Uninstall cancelled"
        exit 0
    fi
    
    # Stop services
    log "Stopping services..."
    for service in "${services_found[@]}"; do
        if [[ $EUID -eq 0 ]]; then
            systemctl stop "$service" || true
            systemctl disable "$service" || true
            rm -f "/etc/systemd/system/$service"
        else
            sudo systemctl stop "$service" || true
            sudo systemctl disable "$service" || true
            sudo rm -f "/etc/systemd/system/$service"
        fi
        log "✓ Removed service: $service"
    done
    
    if [[ ${#services_found[@]} -gt 0 ]]; then
        if [[ $EUID -eq 0 ]]; then
            systemctl daemon-reload
        else
            sudo systemctl daemon-reload
        fi
    fi
    
    # Remove nginx config
    if [[ -f "/etc/nginx/sites-enabled/panel.conf" ]]; then
        if [[ $EUID -eq 0 ]]; then
            rm -f /etc/nginx/sites-enabled/panel.conf
            rm -f /etc/nginx/sites-available/panel.conf
            nginx -t && systemctl reload nginx || true
        else
            sudo rm -f /etc/nginx/sites-enabled/panel.conf
            sudo rm -f /etc/nginx/sites-available/panel.conf
            sudo nginx -t && sudo systemctl reload nginx || true
        fi
        log "✓ Removed Nginx configuration"
    fi
    
    # Remove log files and backups
    log "Removing logs and backups..."
    rm -rf "$INSTALL_DIR/instance/logs" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/instance/audit_logs" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/instance/backups" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/backups" 2>/dev/null || true
    rm -rf "$INSTALL_DIR"/*.log 2>/dev/null || true
    log "✓ Removed logs and backups"
    
    # Remove installation directory
    log "Removing installation directory..."
    cd /
    rm -rf "$INSTALL_DIR"
    log "✓ Removed: $INSTALL_DIR"
    
    # Remove panel user (optional)
    if id panel &>/dev/null; then
        if prompt_confirm "Remove panel system user?" "n"; then
            if [[ $EUID -eq 0 ]]; then
                userdel panel || true
            else
                sudo userdel panel || true
            fi
            log "✓ Removed panel user"
        fi
    fi
    
    echo
    echo -e "${GREEN}🎉 Panel uninstalled successfully!${NC}"
    echo
    echo -e "${BLUE}Cleanup complete:${NC}"
    echo "  ✅ Installation directory removed"
    echo "  ✅ Systemd services removed"
    echo "  ✅ Nginx configuration removed"
    echo
    echo -e "${YELLOW}Note:${NC} Database backups and log files may remain in /var/log/panel"
    echo
}

# Execute main function with all arguments
# This allows the script to work both as:
#   bash getpanel.sh [options]
#   bash <(curl ...) [options]
main "$@"

# Handle command line arguments
# Execute main function with all arguments
# This allows the script to work both as:
#   bash getpanel.sh [options]
#   bash <(curl ...) [options]
main "$@"