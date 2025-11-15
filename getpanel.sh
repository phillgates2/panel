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
    
    if [[ "$secret" == "true" ]]; then
        echo -n -e "${BLUE}$prompt${NC}"
        [[ -n "$default" ]] && echo -n " (default: [hidden])"
        echo -n ": "
        read -s value
        echo
    else
        echo -n -e "${BLUE}$prompt${NC}"
        [[ -n "$default" ]] && echo -n " (default: $default)"
        echo -n ": "
        read value
    fi
    
    echo "${value:-$default}"
}

prompt_confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
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

interactive_config() {
    log "🔧 Interactive Configuration"
    echo
    
    # Installation mode
    echo -e "${BLUE}Installation Mode:${NC}"
    echo "  1) Development (SQLite, quick setup)"
    echo "  2) Production (MySQL, full setup)"
    echo "  3) Custom (configure everything)"
    
    while true; do
        mode=$(prompt_input "Select installation mode (1-3)" "1")
        case "$mode" in
            1|dev|development) INSTALL_MODE="development"; break;;
            2|prod|production) INSTALL_MODE="production"; break;;
            3|custom) INSTALL_MODE="custom"; break;;
            *) echo -e "${RED}Please select 1, 2, or 3${NC}";;
        esac
    done
    
    echo
    log "Selected: $INSTALL_MODE mode"
    
    # Database configuration
    if [[ "$INSTALL_MODE" == "production" ]] || [[ "$INSTALL_MODE" == "custom" ]]; then
        echo
        echo -e "${BLUE}Database Configuration:${NC}"
        
        if [[ "$INSTALL_MODE" == "custom" ]]; then
            if prompt_confirm "Use SQLite for development?" "y"; then
                DB_TYPE="sqlite"
            else
                DB_TYPE="mysql"
            fi
        else
            DB_TYPE="mysql"
        fi
        
        if [[ "$DB_TYPE" == "mysql" ]]; then
            DB_HOST=$(prompt_input "MySQL Host" "localhost")
            DB_PORT=$(prompt_input "MySQL Port" "3306")
            DB_NAME=$(prompt_input "Database Name" "panel")
            DB_USER=$(prompt_input "Database User" "paneluser")
            DB_PASS=$(prompt_input "Database Password" "" "true")
        fi
    else
        DB_TYPE="sqlite"
    fi
    
    # Admin user configuration
    echo
    echo -e "${BLUE}Admin User Setup:${NC}"
    ADMIN_USERNAME=$(prompt_input "Admin Username" "admin")
    ADMIN_EMAIL=$(prompt_input "Admin Email" "admin@localhost")
    ADMIN_PASSWORD=$(prompt_input "Admin Password" "" "true")
    
    # Application settings
    if [[ "$INSTALL_MODE" == "custom" ]]; then
        echo
        echo -e "${BLUE}Application Settings:${NC}"
        APP_HOST=$(prompt_input "Application Host" "0.0.0.0")
        APP_PORT=$(prompt_input "Application Port" "8080")
        
        if prompt_confirm "Enable debug mode?" "n"; then
            DEBUG_MODE="true"
        else
            DEBUG_MODE="false"
        fi
        
        if prompt_confirm "Disable CAPTCHA for testing?" "n"; then
            DISABLE_CAPTCHA="true"
        else
            DISABLE_CAPTCHA="false"
        fi
    else
        APP_HOST="0.0.0.0"
        APP_PORT="8080"
        DEBUG_MODE="false"
        DISABLE_CAPTCHA="false"
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
    
    # Optional features
    if [[ "$INSTALL_MODE" == "custom" ]]; then
        echo
        echo -e "${BLUE}Optional Features:${NC}"
        
        if prompt_confirm "Setup Discord webhooks?" "n"; then
            DISCORD_WEBHOOK=$(prompt_input "Discord Webhook URL" "")
        fi
        
        if prompt_confirm "Enable Redis for background tasks?" "n"; then
            SETUP_REDIS="true"
        else
            SETUP_REDIS="false"
        fi
    else
        SETUP_REDIS="false"
    fi
    
    # Show configuration summary
    echo
    log "📋 Configuration Summary:"
    echo -e "  ${BLUE}Mode:${NC} $INSTALL_MODE"
    echo -e "  ${BLUE}Database:${NC} $DB_TYPE"
    [[ "$DB_TYPE" == "mysql" ]] && echo -e "  ${BLUE}MySQL:${NC} $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    echo -e "  ${BLUE}Admin:${NC} $ADMIN_USERNAME ($ADMIN_EMAIL)"
    echo -e "  ${BLUE}Port:${NC} $APP_PORT"
    [[ "$SETUP_NGINX" == "true" ]] && echo -e "  ${BLUE}Domain:${NC} $DOMAIN_NAME"
    [[ "$SETUP_SSL" == "true" ]] && echo -e "  ${BLUE}SSL:${NC} enabled"
    [[ "$SETUP_SYSTEMD" == "true" ]] && echo -e "  ${BLUE}Systemd:${NC} enabled"
    [[ "$SETUP_REDIS" == "true" ]] && echo -e "  ${BLUE}Redis:${NC} enabled"
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
    
    # Check Python version
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
    local min_version="3.8"
    
    if [[ $(echo -e "$python_version\n$min_version" | sort -V | head -n1) != "$min_version" ]]; then
        error "Python 3.8+ required, found $python_version"
    fi
    
    log "✓ All requirements satisfied"
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
    
    cat >> .env << EOF

# Application Settings
PANEL_HOST=$APP_HOST
PANEL_PORT=$APP_PORT
PANEL_DEBUG=$DEBUG_MODE
PANEL_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)

# Security Settings
PANEL_DISABLE_CAPTCHA=$DISABLE_CAPTCHA

# Admin User
PANEL_ADMIN_USERNAME=$ADMIN_USERNAME
PANEL_ADMIN_EMAIL=$ADMIN_EMAIL
PANEL_ADMIN_PASSWORD=$ADMIN_PASSWORD
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
    if [[ "$INSTALL_MODE" == "development" ]]; then
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
    
    # Install base dependencies
    local packages="python3-venv python3-pip"
    
    if [[ "$DB_TYPE" == "mysql" ]]; then
        case "$PKG_MANAGER" in
            apt-get) packages="$packages mysql-server libmysqlclient-dev";;
            yum) packages="$packages mysql-server mysql-devel";;
            apk) packages="$packages mysql mysql-dev";;
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
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Create environment file
    create_env_file
    
    # Initialize database
    log "Initializing database..."
    if [[ "$DB_TYPE" == "mysql" ]]; then
        # Setup MySQL database
        if command -v mysql &> /dev/null; then
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u root -e "FLUSH PRIVILEGES;"
        else
            warn "MySQL not found, skipping database setup"
        fi
    fi
    
    # Initialize application database
    PANEL_USE_SQLITE="${DB_TYPE}" python3 -c "
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
    echo "Examples:"
    echo "  # Interactive installation (recommended)"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)"
    echo
    echo "  # Install to custom directory"
    echo "  PANEL_INSTALL_DIR=/opt/panel bash <(curl -fsSL ...)"
    echo
    echo "  # Install specific branch"
    echo "  PANEL_BRANCH=develop bash <(curl -fsSL ...)"
    echo
    echo "  # Non-interactive installation"
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