#!/usr/bin/env bash
set -euo pipefail

# Panel Quick Installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)

REPO_URL="https://github.com/phillgates2/panel.git"
INSTALL_DIR="${PANEL_INSTALL_DIR:-$HOME/panel}"
BRANCH="${PANEL_BRANCH:-main}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
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
    echo -e "${BLUE}Press Enter to keep current value, or type new value${NC}"
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
        echo -e "  ${CYAN}6)${NC} 🔍 Test connection with current settings"
        echo -e "  ${YELLOW}7)${NC} 🔄 Reset all to original values"
        echo -e "  ${GREEN}8)${NC} 💾 Save configuration and continue"
        echo -e "${BLUE}═══════════════════════════════════════${NC}"
        echo
    }
    
    display_mariadb_menu
    
    while true; do
        echo -n -e "${BLUE}Select setting to modify (1-8)${NC} (default: 8): "
        read setting_choice
        setting_choice="${setting_choice:-8}"
        
        case "$setting_choice" in
            1)
                echo
                echo -e "${BLUE}Current host: ${YELLOW}$DB_HOST${NC}"
                echo -n -e "${BLUE}Enter new MariaDB Host${NC} (default: $DB_HOST): "
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
                    echo -n -e "${BLUE}Enter new MariaDB Port (1-65535)${NC} (default: $DB_PORT): "
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
                echo -n -e "${BLUE}Enter new Database Name${NC} (default: $DB_NAME): "
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
                echo -n -e "${BLUE}Enter new Database User${NC} (default: $DB_USER): "
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
                        echo -n -e "${BLUE}Enter new password (leave empty for no password)${NC}: "
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
                    # Test connection with timeout
                    if [[ -n "$DB_PASS" ]]; then
                        if timeout 10 mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "SELECT 1 as test;" 2>/dev/null | grep -q "test"; then
                            echo -e "${GREEN}✓ Connection successful!${NC}"
                            echo -e "${GREEN}✓ MariaDB server is accessible${NC}"
                        else
                            echo -e "${RED}✗ Connection failed${NC}"
                            echo -e "${YELLOW}Possible issues:${NC}"
                            echo -e "  • MariaDB server not running on $DB_HOST:$DB_PORT"
                            echo -e "  • Incorrect username/password"
                            echo -e "  • Firewall blocking connection"
                            echo -e "  • User '$DB_USER' doesn't exist or lacks permissions"
                        fi
                    else
                        if timeout 10 mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1 as test;" 2>/dev/null | grep -q "test"; then
                            echo -e "${GREEN}✓ Connection successful!${NC}"
                            echo -e "${GREEN}✓ Passwordless access working${NC}"
                        else
                            echo -e "${RED}✗ Connection failed${NC}"
                            echo -e "${YELLOW}Possible issues:${NC}"
                            echo -e "  • MariaDB server requires a password for user '$DB_USER'"
                            echo -e "  • User '$DB_USER' doesn't exist"
                            echo -e "  • Server not running on $DB_HOST:$DB_PORT"
                        fi
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
                echo -e "${BLUE}Final MariaDB settings:${NC}"
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
        DISCORD_WEBHOOK=""
        INSTALL_ML_DEPS="false"
        return 0
    fi
    
    log "🔧 Interactive Configuration"
    echo -e "${BLUE}Configure your Panel installation step by step${NC}"
    echo
    
    # Installation mode
    echo -e "${BLUE}Installation Mode:${NC}"
    echo "  1) Development (SQLite, quick setup)"
    echo "  2) Production (MariaDB, full setup)"
    echo "  3) Custom (configure everything)"
    echo
    
    while true; do
        echo -n -e "${BLUE}Select installation mode (1-3)${NC} (default: 1): "
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
    
    # Database configuration (always show for all modes)
    echo
    echo -e "${BLUE}Database Configuration:${NC}"
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
    elif [[ "$INSTALL_MODE" == "production" ]]; then
        if prompt_confirm "Use MariaDB? (recommended for production)" "y"; then
            DB_TYPE="mysql"
            echo -e "${GREEN}✓ Selected: MariaDB${NC}"
        else
            DB_TYPE="sqlite"
            echo -e "${GREEN}✓ Selected: SQLite${NC}"
        fi
    else  # custom mode
        echo "  1) SQLite (simple, file-based)"
        echo "  2) MariaDB (scalable, production-ready)"
        echo
        while true; do
            echo -n -e "${BLUE}Select database type (1-2)${NC} (default: 1): "
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
    
    # MariaDB configuration if selected
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
        
        # Allow user to review and modify MariaDB settings
        if prompt_confirm "Review/modify MariaDB settings?" "n"; then
            configure_mariadb_settings
        fi
        
    else
        echo
        echo -e "${GREEN}✓ Using SQLite - database will be created automatically${NC}"
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
    
    # Production services
    if [[ "$INSTALL_MODE" == "production" ]] || [[ "$INSTALL_MODE" == "custom" ]]; then
        echo
        echo -e "${BLUE}Production Services:${NC}"
        
        if [[ "$INSTALL_MODE" == "production" ]] || prompt_confirm "Configure Nginx reverse proxy?" "y"; then
            SETUP_NGINX="true"
            DOMAIN_NAME=$(prompt_input "Domain name" "panel.localhost")
        else
            SETUP_NGINX="false"
        fi
        
        if [[ "$INSTALL_MODE" == "production" ]] || prompt_confirm "Setup SSL certificate?" "y"; then
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
    if [[ "$INSTALL_MODE" == "production" ]]; then
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
    
    # Show comprehensive configuration summary
    echo
    log "📋 Complete Configuration Summary:"
    echo -e "  ${BLUE}Installation Mode:${NC} $INSTALL_MODE"
    echo -e "  ${BLUE}Install Directory:${NC} $INSTALL_DIR"
    echo
    echo -e "  ${BLUE}Database Configuration:${NC}"
    echo -e "    Type: $DB_TYPE"
    [[ "$DB_TYPE" == "mysql" ]] && echo -e "    MariaDB: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
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
    
    # Install packages
    if [[ $EUID -eq 0 ]]; then
        $PKG_INSTALL $packages
    else
        sudo $PKG_INSTALL $packages
    fi
    
    log "✓ System dependencies installed"
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
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "FLUSH PRIVILEGES;"
        else
            warn "MariaDB/MySQL client not found, skipping database setup"
        fi
    fi
    
    # Initialize application database
    if [[ "$DB_TYPE" == "sqlite" ]]; then
        PANEL_USE_SQLITE=1 python3 -c "
from app import app, db, User
with app.app_context():
    db.create_all()
    # Create admin user
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
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"
    else
        python3 -c "
from app import app, db, User
with app.app_context():
    db.create_all()
    # Create admin user
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
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"
    fi
    
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
    echo -e "${BLUE}Configuration Summary:${NC}"
    echo "  📁 Install Directory: $INSTALL_DIR"
    echo "  🗄️ Database: $DB_TYPE"
    echo "  👤 Admin User: $ADMIN_USERNAME"
    echo "  📧 Admin Email: $ADMIN_EMAIL"
    echo "  🌐 Port: $APP_PORT"
    [[ "$SETUP_NGINX" == "true" ]] && echo "  🔗 Domain: https://$DOMAIN_NAME"
    [[ "$SETUP_SSL" == "true" ]] && echo "  🔒 SSL: Enabled"
    echo
    
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Navigate to the installation directory:"
    echo "     cd $INSTALL_DIR"
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
    echo -e "${BLUE}Login Credentials:${NC}"
    echo "  Username: $ADMIN_USERNAME"
    echo "  Password: [as configured during setup]"
    echo
    
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  ./panel.sh start      # Start development server"
    echo "  ./panel.sh start-prod # Start production server"
    echo "  ./panel.sh status     # Check service status"
    echo "  ./panel.sh update     # Update installation"
    echo "  ./panel.sh uninstall  # Remove installation"
    echo
    
    echo -e "${BLUE}Configuration file:${NC}"
    echo "  .env                  # Environment variables"
    echo
    
    echo -e "${BLUE}Documentation:${NC}"
    echo "  README.md             # Full documentation"
    echo "  README_DEV.md         # Development guide"
    echo "  CHANGELOG.md          # Version history"
    echo
}

main() {
    print_banner
    
    # Check if running via curl and provide guidance
    if [[ ! -t 0 ]] && [[ "${PANEL_NONINTERACTIVE:-}" != "true" ]]; then
        echo -e "${YELLOW}⚠️  Running in non-interactive mode (curl pipe detected)${NC}"
        echo -e "${YELLOW}   Using development defaults for quick setup.${NC}"
        echo
        echo -e "${BLUE}For full interactive configuration:${NC}"
        echo "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh -o getpanel.sh"
        echo "  chmod +x getpanel.sh && ./getpanel.sh"
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
    
    # Skip interactive config if running non-interactively
    if [[ "${PANEL_NONINTERACTIVE:-}" == "true" ]]; then
        log "Running in non-interactive mode with defaults"
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

show_help() {
    echo "Panel Installer & Manager"
    echo
    echo "Usage:"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) [command]"
    echo
    echo "Commands:"
    echo "  install     Install Panel (default if no command specified)"
    echo "  uninstall   Uninstall Panel and remove all components"
    echo "  --help      Show this help message"
    echo
    echo "Environment variables:"
    echo "  PANEL_INSTALL_DIR      Installation directory (default: \$HOME/panel)"
    echo "  PANEL_BRANCH           Git branch to install (default: main)"
    echo "  PANEL_NONINTERACTIVE   Skip interactive prompts (default: false)"
    echo "  PANEL_ADMIN_PASSWORD   Admin password for non-interactive mode"
    echo
    echo "Interactive Configuration Options:"
    echo "  • Installation Mode: Development, Production, or Custom"
    echo "  • Database: SQLite (development) or MariaDB (production)"
    echo "  • Application Settings: Host, Port, Debug Mode, CAPTCHA"
    echo "  • Security: Secret Key generation, Admin account setup"
    echo "  • Production Services: Nginx, SSL certificates, Systemd"
    echo "  • Optional Features: Redis, Discord webhooks, ML dependencies"
    echo "  • Logging: Level configuration and detailed monitoring"
    echo
    echo "Examples:"
    echo "  # Quick development setup (non-interactive)"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)"
    echo
    echo "  # Interactive setup (download first, then run)"
    echo "  curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh -o getpanel.sh"
    echo "  chmod +x getpanel.sh && ./getpanel.sh"
    echo
    echo "  # Install to custom directory"
    echo "  PANEL_INSTALL_DIR=/opt/panel bash <(curl -fsSL ...)"
    echo
    echo "  # Install specific branch"
    echo "  PANEL_BRANCH=develop bash <(curl -fsSL ...)"
    echo
    echo "  # Non-interactive installation with custom password"
    echo "  PANEL_NONINTERACTIVE=true PANEL_ADMIN_PASSWORD=secure123 bash <(curl -fsSL ...)"
    echo
    echo "  # Uninstall Panel"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) uninstall"
    echo
    echo "  # Uninstall from custom directory"
    echo "  PANEL_INSTALL_DIR=/opt/panel bash <(curl -fsSL ...) uninstall"
}

# Handle command line arguments
case "${1:-install}" in
    install)
        main "${@:2}"
        ;;
    uninstall)
        print_banner
        log "Panel Uninstaller"
        log "Target directory: $INSTALL_DIR"
        echo
        check_requirements
        uninstall_panel
        ;;
    --help|-h|help)
        show_help
        exit 0
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}"
        echo
        show_help
        exit 1
        ;;
esac