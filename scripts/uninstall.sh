#!/bin/bash

# Panel Application Uninstaller
# Run with: bash uninstall.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Welcome message
echo "========================================"
echo "  Panel Application Uninstaller"
echo "========================================"
echo ""
log_warning "This will remove Panel and all its data!"
echo ""

# Get installation directory
read -p "Installation directory (default: ~/panel): " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-~/panel}
INSTALL_DIR=$(eval echo $INSTALL_DIR)

if [[ ! -d "$INSTALL_DIR" ]]; then
    log_error "Directory $INSTALL_DIR does not exist"
    exit 1
fi

# Confirmation
echo ""
log_warning "This will remove:"
echo "  - Application files in $INSTALL_DIR"
echo "  - Database (if SQLite)"
echo "  - Virtual environment"
echo "  - Configuration files"
echo ""
read -p "Are you sure? Type 'yes' to confirm: " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    log_info "Uninstall cancelled"
    exit 0
fi

echo ""
log_info "Starting uninstallation..."

# Stop systemd service if exists
if systemctl is-active --quiet panel 2>/dev/null; then
    log_info "Stopping panel service..."
    sudo systemctl stop panel
    sudo systemctl disable panel
    sudo rm -f /etc/systemd/system/panel.service
    sudo systemctl daemon-reload
    log_success "Service stopped and removed"
fi

# Remove nginx configuration
if [[ -f /etc/nginx/sites-enabled/panel ]]; then
    log_info "Removing nginx configuration..."
    sudo rm -f /etc/nginx/sites-enabled/panel
    sudo rm -f /etc/nginx/sites-available/panel
    sudo systemctl reload nginx 2>/dev/null || true
    log_success "Nginx configuration removed"
fi

# Ask about PostgreSQL database
if command -v psql &> /dev/null; then
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw panel_db 2>/dev/null; then
        read -p "Remove PostgreSQL database 'panel_db'? (y/n): " REMOVE_DB
        if [[ "$REMOVE_DB" == "y" ]]; then
            sudo -u postgres dropdb panel_db 2>/dev/null || true
            sudo -u postgres dropuser panel_user 2>/dev/null || true
            log_success "PostgreSQL database and user removed"
        fi
    fi
fi

# Create backup before removal
BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
read -p "Create backup before removal? (y/n, default: y): " CREATE_BACKUP
CREATE_BACKUP=${CREATE_BACKUP:-y}

if [[ "$CREATE_BACKUP" == "y" ]]; then
    log_info "Creating backup at $BACKUP_DIR"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup important files
    [[ -f "$INSTALL_DIR/.env" ]] && cp "$INSTALL_DIR/.env" "$BACKUP_DIR/"
    [[ -f "$INSTALL_DIR/panel.db" ]] && cp "$INSTALL_DIR/panel.db" "$BACKUP_DIR/"
    [[ -d "$INSTALL_DIR/logs" ]] && cp -r "$INSTALL_DIR/logs" "$BACKUP_DIR/" 2>/dev/null || true
    
    log_success "Backup created at $BACKUP_DIR"
fi

# Remove installation directory
log_info "Removing installation directory..."
rm -rf "$INSTALL_DIR"
log_success "Installation directory removed"

# Clean up Redis data (optional)
read -p "Flush Redis database? (y/n): " FLUSH_REDIS
if [[ "$FLUSH_REDIS" == "y" ]] && command -v redis-cli &> /dev/null; then
    redis-cli FLUSHDB 2>/dev/null || log_warning "Could not flush Redis"
fi

echo ""
log_success "Uninstallation complete!"
echo ""
if [[ "$CREATE_BACKUP" == "y" ]]; then
    log_info "Your data has been backed up to: $BACKUP_DIR"
fi
echo ""
log_info "Panel has been removed from your system"
echo ""
