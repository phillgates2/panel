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

WHAT GETS REMOVED:
    - All systemd services and timers
    - Nginx configuration files
    - Logrotate configuration
    - Sudoers configuration
    - Application files and virtual environment
    - SQLite database (if present)
    - User data directories (optional)
    - SSL certificates (optional)
    - PostgreSQL database (optional)
    - All files and configs related to the new stylish database admin UI and navigation enhancements

EXAMPLES:
    # Interactive uninstall
    curl -fsSL .../uninstall.sh | bash

    # Force uninstall without prompts
    PANEL_FORCE_UNINSTALL=true bash uninstall.sh

    # Uninstall custom directory
    bash uninstall.sh --dir /opt/panel

    # Keep database during uninstall
    bash uninstall.sh --keep-db

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
    log "Stopping Panel services and timers..."

    local services=(
        "panel-gunicorn"
        "gunicorn"
        "rq-worker"
        "rq-worker-supervised"
        "panel-etlegacy"
        "etlegacy"
        "check-worker"
        "memwatch"
        "backup"
        "autodeploy"
        "session-cleanup"
        "ssl-renew"
        "ssl-renewal"
        "panel-logrotate"
    )

    local timers=(
        "check-worker.timer"
        "memwatch.timer"
        "backup.timer"
        "autodeploy.timer"
        "session-cleanup.timer"
        "ssl-renew.timer"
        "ssl-renewal.timer"
        "panel-logrotate.timer"
    )

    # Stop and disable timers first
    for timer in "${timers[@]}"; do
        if systemctl is-active --quiet "$timer" 2>/dev/null; then
            log "Stopping $timer..."
            $SUDO systemctl stop "$timer" 2>/dev/null || true
            $SUDO systemctl disable "$timer" 2>/dev/null || true
        fi
    done

    # Stop and disable services
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log "Stopping $service..."
            $SUDO systemctl stop "$service" 2>/dev/null || true
            $SUDO systemctl disable "$service" 2>/dev/null || true
        fi
    done

    # Remove systemd service and timer files
    local systemd_files=(
        "/etc/systemd/system/panel-gunicorn.service"
        "/etc/systemd/system/gunicorn.service"
        "/etc/systemd/system/rq-worker.service"
        "/etc/systemd/system/rq-worker-supervised.service"
        "/etc/systemd/system/panel-etlegacy.service"
        "/etc/systemd/system/etlegacy.service"
        "/etc/systemd/system/check-worker.service"
        "/etc/systemd/system/check-worker.timer"
        "/etc/systemd/system/memwatch.service"
        "/etc/systemd/system/memwatch.timer"
        "/etc/systemd/system/backup.service"
        "/etc/systemd/system/backup.timer"
        "/etc/systemd/system/autodeploy.service"
        "/etc/systemd/system/autodeploy.timer"
        "/etc/systemd/system/session-cleanup.service"
        "/etc/systemd/system/session-cleanup.timer"
        "/etc/systemd/system/ssl-renew.service"
        "/etc/systemd/system/ssl-renew.timer"
        "/etc/systemd/system/ssl-renewal.service"
        "/etc/systemd/system/ssl-renewal.timer"
        "/etc/systemd/system/panel-logrotate.service"
        "/etc/systemd/system/panel-logrotate.timer"
    )

    for file in "${systemd_files[@]}"; do
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
        "/etc/nginx/conf.d/nginx_game_chrisvanek.conf"
    )

    for config in "${nginx_configs[@]}"; do
        if [[ -f "$config" ]]; then
            log "Removing $config..."
            $SUDO rm -f "$config"
        fi
    done

    # Test and reload nginx if it's running
    if command -v nginx &>/dev/null && systemctl is-active --quiet nginx 2>/dev/null; then
        $SUDO nginx -t && $SUDO systemctl reload nginx || warn "Nginx reload failed"
    fi
}

remove_logrotate_config() {
    log "Removing logrotate configuration..."

    local logrotate_configs=(
        "/etc/logrotate.d/panel"
        "/etc/logrotate.d/panel-logrotate"
    )

    for config in "${logrotate_configs[@]}"; do
        if [[ -f "$config" ]]; then
            log "Removing $config..."
            $SUDO rm -f "$config"
        fi
    done
}

remove_sudoers_config() {
    log "Removing sudoers configuration..."

    local sudoers_files=(
        "/etc/sudoers.d/panel"
        "/etc/sudoers.d/panel-sudoers"
    )

    for sudoers in "${sudoers_files[@]}"; do
        if [[ -f "$sudoers" ]]; then
            log "Removing $sudoers..."
            $SUDO rm -f "$sudoers"
        fi
    done
}

remove_ssl_certificates() {
    log "Checking for SSL certificates..."

    local cert_dirs=(
        "/etc/letsencrypt/live/panel"
        "/etc/letsencrypt/archive/panel"
        "/etc/letsencrypt/renewal/panel.conf"
    )

    local has_certs=false
    for cert_path in "${cert_dirs[@]}"; do
        if [[ -e "$cert_path" ]]; then
            has_certs=true
            break
        fi
    done

    if [[ "$has_certs" == "true" ]]; then
        echo
        if confirm "Remove SSL certificates?" "n"; then
            for cert_path in "${cert_dirs[@]}"; do
                if [[ -e "$cert_path" ]]; then
                    log "Removing $cert_path..."
                    $SUDO rm -rf "$cert_path"
                fi
            done
            log "SSL certificates removed"
        else
            log "Keeping SSL certificates"
        fi
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
    echo "  - Configuration files"
    echo "  - Forum and CMS data"
    echo

    log "Prompting user for installation directory removal confirmation..."
    if ! confirm "Remove installation directory?"; then
        log "Skipping directory removal"
        return
    fi

    rm -rf "$INSTALL_DIR"
    log "Installation directory removed"
}

remove_user_data() {
    log "Checking for user data directories..."

    local data_dirs=(
        "$HOME/.local/share/panel"
        "$HOME/.config/panel"
    )

    local has_data=false
    for data_dir in "${data_dirs[@]}"; do
        if [[ -d "$data_dir" ]]; then
            has_data=true
            break
        fi
    done

    if [[ "$has_data" == "true" ]]; then
        echo
        echo -e "${YELLOW}User data directories found:${NC}"
        for data_dir in "${data_dirs[@]}"; do
            if [[ -d "$data_dir" ]]; then
                echo "  - $data_dir"
            fi
        done
        echo

        if confirm "Remove user data directories?" "n"; then
            for data_dir in "${data_dirs[@]}"; do
                if [[ -d "$data_dir" ]]; then
                    log "Removing $data_dir..."
                    rm -rf "$data_dir"
                fi
            done
            log "User data directories removed"
        else
            log "Keeping user data directories"
        fi
    fi
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
    remove_logrotate_config
    remove_sudoers_config
    remove_ssl_certificates
    remove_installation
    remove_user_data

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
    log "Thank you for using Panel!"
    echo
}

# ============================================================================
# Execute
# ============================================================================

main "$@"
