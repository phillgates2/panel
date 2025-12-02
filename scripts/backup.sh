#!/bin/bash

#############################################################################
# Panel Backup Script
# Automated backup of Panel application, database, and configuration
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${PANEL_INSTALL_DIR:-/opt/panel}"
BACKUP_DIR="${PANEL_BACKUP_DIR:-/var/backups/panel}"
RETENTION_DAYS="${PANEL_BACKUP_RETENTION:-30}"
COMPRESS="${PANEL_BACKUP_COMPRESS:-true}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="panel_backup_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Backup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Timestamp: $(date)"
    echo "Install dir: $INSTALL_DIR"
    echo "Backup dir: $BACKUP_DIR"
    echo
}

error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

warn() {
    echo -e "${YELLOW}! $1${NC}"
}

# Create backup directory
create_backup_dir() {
    mkdir -p "$BACKUP_PATH"
    success "Backup directory created: $BACKUP_PATH"
}

# Backup configuration
backup_config() {
    info "Backing up configuration..."
    
    cp "$INSTALL_DIR/config.py" "$BACKUP_PATH/" 2>/dev/null || warn "config.py not found"
    
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        cp "$INSTALL_DIR/.env" "$BACKUP_PATH/"
    fi
    
    if [[ -d "$INSTALL_DIR/instance" ]]; then
        cp -r "$INSTALL_DIR/instance" "$BACKUP_PATH/"
    fi
    
    success "Configuration backed up"
}

# Backup database
backup_database() {
    info "Backing up database..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Detect database type
    DB_URI=$(python -c "from config import Config; print(Config.SQLALCHEMY_DATABASE_URI)" 2>/dev/null || echo "")
    
    if [[ "$DB_URI" =~ ^sqlite:/// ]]; then
        # SQLite backup
        DB_FILE=$(echo "$DB_URI" | sed 's|sqlite:///||')
        
        if [[ -f "$DB_FILE" ]]; then
            cp "$DB_FILE" "$BACKUP_PATH/"
            success "SQLite database backed up"
        else
            warn "SQLite database file not found: $DB_FILE"
        fi
        
    elif [[ "$DB_URI" =~ ^postgresql:// ]]; then
        # PostgreSQL backup
        export PGPASSWORD=$(echo "$DB_URI" | grep -oP '(?<=:)[^@]+(?=@)' | cut -d':' -f2)
        PG_HOST=$(echo "$DB_URI" | grep -oP '(?<=@)[^:]+(?=:)')
        PG_PORT=$(echo "$DB_URI" | grep -oP '(?<=:)[0-9]+(?=/)')
        PG_DB=$(echo "$DB_URI" | grep -oP '(?<=/)[^?]+')
        PG_USER=$(echo "$DB_URI" | grep -oP '(?<=://)[^:]+(?=:)')
        
        pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -F c -f "$BACKUP_PATH/database.dump"
        
        if [[ $? -eq 0 ]]; then
            success "PostgreSQL database backed up"
        else
            warn "PostgreSQL backup failed"
        fi
        
        unset PGPASSWORD
    else
        warn "Unknown database type, skipping database backup"
    fi
}

# Backup uploaded files
backup_uploads() {
    info "Backing up uploaded files..."
    
    if [[ -d "$INSTALL_DIR/uploads" ]]; then
        cp -r "$INSTALL_DIR/uploads" "$BACKUP_PATH/"
        success "Uploads backed up"
    else
        warn "Uploads directory not found"
    fi
}

# Backup static files (if customized)
backup_static() {
    info "Backing up static files..."
    
    if [[ -d "$INSTALL_DIR/static/custom" ]]; then
        mkdir -p "$BACKUP_PATH/static"
        cp -r "$INSTALL_DIR/static/custom" "$BACKUP_PATH/static/"
        success "Custom static files backed up"
    fi
}

# Backup logs
backup_logs() {
    info "Backing up logs..."
    
    mkdir -p "$BACKUP_PATH/logs"
    
    if [[ -f "$INSTALL_DIR/panel.log" ]]; then
        cp "$INSTALL_DIR/panel.log" "$BACKUP_PATH/logs/"
    fi
    
    if [[ -d "$INSTALL_DIR/logs" ]]; then
        cp -r "$INSTALL_DIR/logs"/* "$BACKUP_PATH/logs/" 2>/dev/null || true
    fi
    
    if [[ $(ls -A "$BACKUP_PATH/logs" 2>/dev/null) ]]; then
        success "Logs backed up"
    fi
}

# Backup systemd service
backup_service() {
    info "Backing up systemd service..."
    
    if [[ -f "/etc/systemd/system/panel.service" ]]; then
        mkdir -p "$BACKUP_PATH/systemd"
        cp "/etc/systemd/system/panel.service" "$BACKUP_PATH/systemd/"
        success "Systemd service backed up"
    fi
}

# Backup nginx configuration
backup_nginx() {
    info "Backing up nginx configuration..."
    
    mkdir -p "$BACKUP_PATH/nginx"
    
    if [[ -f "/etc/nginx/sites-available/panel" ]]; then
        cp "/etc/nginx/sites-available/panel" "$BACKUP_PATH/nginx/"
        success "Nginx configuration backed up"
    elif [[ -f "/etc/nginx/conf.d/panel.conf" ]]; then
        cp "/etc/nginx/conf.d/panel.conf" "$BACKUP_PATH/nginx/"
        success "Nginx configuration backed up"
    fi
}

# Create backup manifest
create_manifest() {
    info "Creating backup manifest..."
    
    cat > "$BACKUP_PATH/MANIFEST.txt" << EOF
Panel Backup Manifest
=====================
Backup Date: $(date)
Install Directory: $INSTALL_DIR
Backup Directory: $BACKUP_PATH

Contents:
$(ls -lh "$BACKUP_PATH")

System Info:
- OS: $(uname -s)
- Kernel: $(uname -r)
- Hostname: $(hostname)

Panel Info:
- Python: $(cd "$INSTALL_DIR" && source venv/bin/activate && python --version 2>&1)
- Flask: $(cd "$INSTALL_DIR" && source venv/bin/activate && python -c "import flask; print(flask.__version__)" 2>&1 || echo "unknown")

Database:
- Type: $(cd "$INSTALL_DIR" && source venv/bin/activate && python -c "from config import Config; uri = Config.SQLALCHEMY_DATABASE_URI; print('SQLite' if 'sqlite' in uri else 'PostgreSQL' if 'postgresql' in uri else 'Unknown')" 2>&1)

Backup Size: $(du -sh "$BACKUP_PATH" | cut -f1)
EOF
    
    success "Manifest created"
}

# Compress backup
compress_backup() {
    if [[ "$COMPRESS" != "true" ]]; then
        return
    fi
    
    info "Compressing backup..."
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    if [[ $? -eq 0 ]]; then
        rm -rf "$BACKUP_NAME"
        success "Backup compressed: ${BACKUP_NAME}.tar.gz"
        
        BACKUP_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
        info "Backup size: $BACKUP_SIZE"
    else
        warn "Compression failed, keeping uncompressed backup"
    fi
}

# Clean old backups
cleanup_old_backups() {
    info "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
    
    if [[ "$COMPRESS" == "true" ]]; then
        find "$BACKUP_DIR" -name "panel_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
    else
        find "$BACKUP_DIR" -name "panel_backup_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
    fi
    
    REMAINING=$(find "$BACKUP_DIR" -name "panel_backup_*" | wc -l)
    success "Old backups cleaned, $REMAINING backup(s) remaining"
}

# List backups
list_backups() {
    echo -e "${BLUE}Available Backups:${NC}"
    echo "----------------------------------------"
    
    if [[ "$COMPRESS" == "true" ]]; then
        ls -lh "$BACKUP_DIR"/panel_backup_*.tar.gz 2>/dev/null || echo "No backups found"
    else
        ls -lhd "$BACKUP_DIR"/panel_backup_* 2>/dev/null || echo "No backups found"
    fi
}

# Restore backup
restore_backup() {
    local backup_file=$1
    
    if [[ ! -f "$backup_file" ]] && [[ ! -d "$backup_file" ]]; then
        error "Backup not found: $backup_file"
    fi
    
    warn "This will restore from backup and overwrite current installation"
    read -p "Continue? (yes/no): " CONFIRM
    
    if [[ "$CONFIRM" != "yes" ]]; then
        info "Restore cancelled"
        exit 0
    fi
    
    info "Restoring from backup..."
    
    # Extract if compressed
    if [[ "$backup_file" == *.tar.gz ]]; then
        EXTRACT_DIR="${backup_file%.tar.gz}"
        tar -xzf "$backup_file" -C "$BACKUP_DIR"
        backup_file="$EXTRACT_DIR"
    fi
    
    # Stop service
    if systemctl is-active panel.service &>/dev/null; then
        info "Stopping Panel service..."
        sudo systemctl stop panel.service
    fi
    
    # Restore files
    if [[ -f "$backup_file/config.py" ]]; then
        cp "$backup_file/config.py" "$INSTALL_DIR/"
        success "Configuration restored"
    fi
    
    if [[ -d "$backup_file/uploads" ]]; then
        rm -rf "$INSTALL_DIR/uploads"
        cp -r "$backup_file/uploads" "$INSTALL_DIR/"
        success "Uploads restored"
    fi
    
    # Restore database
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    if [[ -f "$backup_file/panel.db" ]]; then
        cp "$backup_file/panel.db" "$INSTALL_DIR/"
        success "SQLite database restored"
    elif [[ -f "$backup_file/database.dump" ]]; then
        DB_URI=$(python -c "from config import Config; print(Config.SQLALCHEMY_DATABASE_URI)")
        
        export PGPASSWORD=$(echo "$DB_URI" | grep -oP '(?<=:)[^@]+(?=@)' | cut -d':' -f2)
        PG_HOST=$(echo "$DB_URI" | grep -oP '(?<=@)[^:]+(?=:)')
        PG_PORT=$(echo "$DB_URI" | grep -oP '(?<=:)[0-9]+(?=/)')
        PG_DB=$(echo "$DB_URI" | grep -oP '(?<=/)[^?]+')
        PG_USER=$(echo "$DB_URI" | grep -oP '(?<=://)[^:]+(?=:)')
        
        pg_restore -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "$backup_file/database.dump"
        
        unset PGPASSWORD
        success "PostgreSQL database restored"
    fi
    
    # Restart service
    if systemctl list-unit-files | grep -q "panel.service"; then
        info "Starting Panel service..."
        sudo systemctl start panel.service
        success "Service started"
    fi
    
    success "Restore complete!"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Automated backup of Panel application

Options:
    --backup          Create backup (default)
    --list            List available backups
    --restore FILE    Restore from backup
    --cleanup         Clean old backups only
    --help            Show this help

Environment Variables:
    PANEL_INSTALL_DIR        Installation directory (default: /opt/panel)
    PANEL_BACKUP_DIR         Backup directory (default: /var/backups/panel)
    PANEL_BACKUP_RETENTION   Days to keep backups (default: 30)
    PANEL_BACKUP_COMPRESS    Compress backups (default: true)

Examples:
    # Create backup
    $0
    $0 --backup
    
    # List backups
    $0 --list
    
    # Restore backup
    $0 --restore /var/backups/panel/panel_backup_20250101_120000.tar.gz
    
    # Clean old backups
    $0 --cleanup

Systemd Timer:
    To schedule automatic backups, create /etc/systemd/system/panel-backup.timer

EOF
}

# Main
main() {
    case "${1:-backup}" in
        --backup|backup)
            print_header
            create_backup_dir
            backup_config
            backup_database
            backup_uploads
            backup_static
            backup_logs
            backup_service
            backup_nginx
            create_manifest
            compress_backup
            cleanup_old_backups
            echo
            success "Backup complete: ${BACKUP_PATH}"
            ;;
        --list|list)
            list_backups
            ;;
        --restore|restore)
            if [[ -z "$2" ]]; then
                error "Missing backup file argument"
            fi
            restore_backup "$2"
            ;;
        --cleanup|cleanup)
            cleanup_old_backups
            ;;
        --help|help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
}

main "$@"
