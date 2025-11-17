#!/usr/bin/env bash
# Panel Uninstaller
# Usage: curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash

set -eo pipefail

# ============================================================================
# Configuration
# ============================================================================

INSTALL_DIR="${PANEL_INSTALL_DIR:-$HOME/panel}"
FORCE="${PANEL_FORCE_UNINSTALL:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# System detection
SUDO=""

# ============================================================================
# Help
# ============================================================================

show_help() {
    cat << 'EOF'
Panel Uninstaller

USAGE:
    curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash
    bash uninstall.sh [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -d, --dir DIR           Installation directory (default: ~/panel)
    -f, --force             Skip confirmation prompts
    --keep-db               Keep PostgreSQL database
    --keep-data             Keep logs and backups

ENVIRONMENT VARIABLES:
    PANEL_INSTALL_DIR       Installation directory
    PANEL_FORCE_UNINSTALL   Skip prompts (true/false)

EXAMPLES:
    # Interactive uninstall
    curl -fsSL .../uninstall.sh | bash

    # Force uninstall without prompts
    PANEL_FORCE_UNINSTALL=true bash uninstall.sh

    # Uninstall custom directory
    bash uninstall.sh --dir /opt/panel

EOF
    exit 0
}

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
    exit 1
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    
    if [[ "$FORCE" == "true" ]]; then
        return 0
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

detect_system() {
    # Setup sudo if needed
    if [[ $EUID -ne 0 ]]; then
        if command -v sudo &>/dev/null; then
            SUDO="sudo"
        fi
    fi
}

# ============================================================================
# Uninstallation Functions
# ============================================================================

stop_services() {
    log "Stopping Panel services..."
    
    local services=(
        "panel-gunicorn"
        "rq-worker"
        "rq-worker-supervised"
        "panel-etlegacy"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log "Stopping $service..."
            $SUDO systemctl stop "$service" 2>/dev/null || true
            $SUDO systemctl disable "$service" 2>/dev/null || true
        fi
    done
    
    # Remove systemd service files
    local service_files=(
        "/etc/systemd/system/panel-gunicorn.service"
        "/etc/systemd/system/rq-worker.service"
        "/etc/systemd/system/rq-worker-supervised.service"
        "/etc/systemd/system/panel-etlegacy.service"
    )
    
    for file in "${service_files[@]}"; do
        if [[ -f "$file" ]]; then
            log "Removing $file..."
            $SUDO rm -f "$file"
        fi
    done
    
    $SUDO systemctl daemon-reload 2>/dev/null || true
}

remove_nginx_config() {
    log "Removing Nginx configuration..."
    
    local nginx_configs=(
        "/etc/nginx/sites-enabled/panel"
        "/etc/nginx/sites-available/panel"
        "/etc/nginx/conf.d/panel.conf"
    )
    
    for config in "${nginx_configs[@]}"; do
        if [[ -f "$config" ]]; then
            $SUDO rm -f "$config"
        fi
    done
    
    # Test and reload nginx if it's running
    if command -v nginx &>/dev/null && systemctl is-active --quiet nginx 2>/dev/null; then
        $SUDO nginx -t && $SUDO systemctl reload nginx || warn "Nginx reload failed"
    fi
}

remove_installation() {
    log "Checking installation directory: $INSTALL_DIR"
    
    if [[ ! -d "$INSTALL_DIR" ]]; then
        warn "Installation directory not found: $INSTALL_DIR"
        return
    fi
    
    log "Installation directory exists, preparing to remove: $INSTALL_DIR"
    
    # Show what will be removed
    echo
    echo -e "${YELLOW}The following will be removed:${NC}"
    echo "  - Application files: $INSTALL_DIR"
    echo "  - Python virtual environment"
    echo "  - Logs: $INSTALL_DIR/instance/logs/"
    echo "  - Audit logs: $INSTALL_DIR/instance/audit_logs/"
    echo "  - Database backups: $INSTALL_DIR/instance/backups/"
    echo "  - SQLite database (if present): $INSTALL_DIR/instance/panel.db"
    echo
    
    log "Prompting user for installation directory removal confirmation..."
    if ! confirm "Remove installation directory?"; then
        log "Skipping directory removal"
        return
    fi
    
    rm -rf "$INSTALL_DIR"
    log "Installation directory removed"
}

drop_postgresql_db() {
    if ! command -v psql &>/dev/null; then
        log "PostgreSQL not found, skipping database removal"
        return
    fi
    
    log "PostgreSQL found, checking if database should be dropped..."
    echo
    if ! confirm "Drop PostgreSQL database 'panel'?" "n"; then
        log "Keeping PostgreSQL database"
        return
    fi
    
    log "Dropping PostgreSQL database..."
    
    # Try to drop database and user
    $SUDO -u postgres psql -c "DROP DATABASE IF EXISTS panel;" 2>/dev/null || warn "Could not drop database"
    $SUDO -u postgres psql -c "DROP USER IF EXISTS panel_user;" 2>/dev/null || warn "Could not drop user"
    
    log "PostgreSQL database dropped"
}

# ============================================================================
# Main Uninstallation Flow
# ============================================================================

parse_args() {
    KEEP_DB=false
    KEEP_DATA=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -f|--force)
                FORCE="true"
                shift
                ;;
            --keep-db)
                KEEP_DB=true
                shift
                ;;
            --keep-data)
                KEEP_DATA=true
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
    echo -e "${BOLD}${RED}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${RED}║         Panel Uninstaller                 ║${NC}"
    echo -e "${BOLD}${RED}╚═══════════════════════════════════════════╝${NC}"
    echo
    
    detect_system
    
    log "FORCE=$FORCE"
    log "Installation directory: $INSTALL_DIR"
    
    echo -e "${YELLOW}WARNING: This will remove Panel and its data!${NC}"
    echo -e "${YELLOW}Installation directory: $INSTALL_DIR${NC}"
    echo
    
    log "Prompting user for initial confirmation..."
    if ! confirm "Continue with uninstallation?" "n"; then
        log "Uninstallation cancelled"
        exit 0
    fi
    
    log "User confirmed uninstallation, proceeding..."
    echo
    stop_services
    remove_nginx_config
    remove_installation
    
    if [[ "$KEEP_DB" != "true" ]]; then
        drop_postgresql_db
    fi
    
    echo
    echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   Uninstallation Complete!                ║${NC}"
    echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo
    
    if [[ "$KEEP_DB" == "true" ]]; then
        echo -e "${YELLOW}Note:${NC} PostgreSQL database was preserved"
    fi
    
    log "Panel has been removed from your system"
    echo
}

# ============================================================================
# Execute
# ============================================================================

main "$@"
