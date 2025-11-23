#!/bin/bash
# Backup Management Script
# Manage backups and disaster recovery operations

set -e

# Configuration
BACKUP_DIR="backups"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup
create_backup() {
    local backup_type=$1
    local name=${2:-""}

    if [ -z "$backup_type" ]; then
        log_error "Backup type is required"
        echo "Usage: $0 create <type> [name]"
        echo "Types: database, filesystem, application, configuration"
        exit 1
    fi

    log_info "Creating $backup_type backup..."

    if [ -n "$name" ]; then
        python3 -c "
from src.panel.backup_recovery import create_backup
result = create_backup('$backup_type', '$name')
print(f'Backup created: {result[\"job_id\"]}')
print(f'File: {result[\"file_path\"]}')
print(f'Size: {result[\"size\"]} bytes')
"
    else
        python3 -c "
from src.panel.backup_recovery import create_backup
result = create_backup('$backup_type')
print(f'Backup created: {result[\"job_id\"]}')
print(f'File: {result[\"file_path\"]}')
print(f'Size: {result[\"size\"]} bytes')
"
    fi

    log_success "$backup_type backup completed"
}

# Restore backup
restore_backup() {
    local backup_type=$1
    local backup_file=$2

    if [ -z "$backup_type" ] || [ -z "$backup_file" ]; then
        log_error "Backup type and file are required"
        echo "Usage: $0 restore <type> <file>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Restoring $backup_type from $backup_file..."

    python3 -c "
from src.panel.backup_recovery import restore_backup
result = restore_backup('$backup_type', '$backup_file')
print('Restore completed:')
for key, value in result.items():
    print(f'  {key}: {value}')
"

    log_success "$backup_type restore completed"
}

# List backups
list_backups() {
    local backup_type=${1:-""}

    log_info "Listing backups..."

    python3 -c "
from src.panel.backup_recovery import list_backups
backups = list_backups('$backup_type' if '$backup_type' else None)
if not backups:
    print('No backups found')
else:
    print(f'Found {len(backups)} backups:')
    print()
    for backup in backups[:10]:  # Show last 10
        status_icon = '?' if backup['status'] == 'completed' else '?' if backup['status'] == 'failed' else '?'
        size_mb = backup['size_bytes'] / 1024 / 1024
        print(f'{status_icon} {backup[\"id\"]}')
        print(f'   Type: {backup[\"type\"]}')
        print(f'   Status: {backup[\"status\"]}')
        print(f'   Created: {backup[\"created_at\"]}')
        print(f'   Size: {size_mb:.2f} MB')
        if backup.get('file_path'):
            print(f'   File: {backup[\"file_path\"]}')
        if backup.get('error'):
            print(f'   Error: {backup[\"error\"]}')
        print()
"
}

# Show backup status
show_backup_status() {
    local job_id=$1

    if [ -z "$job_id" ]; then
        log_error "Job ID is required"
        echo "Usage: $0 status <job_id>"
        exit 1
    fi

    log_info "Getting status for backup: $job_id"

    python3 -c "
from src.panel.backup_recovery import get_backup_status
status = get_backup_status('$job_id')
if not status:
    print('Backup job not found')
else:
    print(f'Job ID: {status[\"id\"]}')
    print(f'Name: {status[\"name\"]}')
    print(f'Type: {status[\"type\"]}')
    print(f'Status: {status[\"status\"]}')
    print(f'Created: {status[\"created_at\"]}')
    if status.get('size_bytes'):
        size_mb = status['size_bytes'] / 1024 / 1024
        print(f'Size: {size_mb:.2f} MB')
    if status.get('error_message'):
        print(f'Error: {status[\"error_message\"]}')
    if status.get('metadata'):
        print('Metadata:')
        for key, value in status['metadata'].items():
            print(f'  {key}: {value}')
"
}

# Cleanup old backups
cleanup_backups() {
    log_info "Cleaning up old backups..."

    python3 -c "
from src.panel.backup_recovery import get_backup_manager
manager = get_backup_manager()
manager.cleanup_old_backups()
print('Cleanup completed')
"

    log_success "Backup cleanup completed"
}

# Create full backup
create_full_backup() {
    local name=${1:-"full_backup"}

    log_info "Creating full system backup..."

    # Create all backup types
    backup_types=("database" "filesystem" "configuration" "application")
    results=()

    for backup_type in "${backup_types[@]}"; do
        log_info "Creating $backup_type backup..."
        if create_backup "$backup_type" "${name}_${backup_type}"; then
            results+=("$backup_type: SUCCESS")
        else
            results+=("$backup_type: FAILED")
        fi
    done

    log_info "Full backup summary:"
    printf '%s\n' "${results[@]}"

    # Check if all succeeded
    failed_count=$(echo "${results[@]}" | grep -c "FAILED")
    if [ "$failed_count" -eq 0 ]; then
        log_success "Full backup completed successfully"
    else
        log_error "Full backup completed with $failed_count failures"
        exit 1
    fi
}

# Disaster recovery
disaster_recovery() {
    local backup_dir=${1:-"$BACKUP_DIR"}

    if [ ! -d "$backup_dir" ]; then
        log_error "Backup directory not found: $backup_dir"
        exit 1
    fi

    log_warn "Starting disaster recovery from: $backup_dir"
    log_warn "This will overwrite existing data. Make sure you have a backup!"

    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Disaster recovery cancelled"
        exit 0
    fi

    # Find latest backups
    log_info "Finding latest backups..."

    latest_db=$(find "$backup_dir" -name "db_backup_*.sql*" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    latest_fs=$(find "$backup_dir" -name "fs_backup_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    latest_config=$(find "$backup_dir" -name "config_backup_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)

    # Restore in order
    if [ -n "$latest_config" ]; then
        log_info "Restoring configuration..."
        restore_backup "configuration" "$latest_config"
    fi

    if [ -n "$latest_db" ]; then
        log_info "Restoring database..."
        restore_backup "database" "$latest_db"
    fi

    if [ -n "$latest_fs" ]; then
        log_info "Restoring filesystem..."
        restore_backup "filesystem" "$latest_fs"
    fi

    log_success "Disaster recovery completed"
    log_info "Please restart the application to apply changes"
}

# Verify backup integrity
verify_backup() {
    local backup_file=$1

    if [ -z "$backup_file" ]; then
        log_error "Backup file is required"
        echo "Usage: $0 verify <file>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Verifying backup integrity: $backup_file"

    # Check file exists and is readable
    if [ ! -r "$backup_file" ]; then
        log_error "Backup file is not readable"
        exit 1
    fi

    # Get file size
    file_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
    if [ -z "$file_size" ] || [ "$file_size" -eq 0 ]; then
        log_error "Backup file is empty or corrupted"
        exit 1
    fi

    # Check file type and try to extract/validate
    if [[ "$backup_file" == *.tar.gz ]]; then
        if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
            log_error "Backup file is corrupted (tar.gz)"
            exit 1
        fi
    elif [[ "$backup_file" == *.sql ]]; then
        # Basic SQL file validation
        if ! head -1 "$backup_file" | grep -q "PostgreSQL\|MySQL\|SQLite"; then
            log_warn "SQL file may not be a valid database dump"
        fi
    fi

    log_success "Backup integrity verified"
    echo "File size: $file_size bytes"
}

# Show backup statistics
show_stats() {
    log_info "Backup system statistics..."

    python3 -c "
import os
from pathlib import Path
from src.panel.backup_recovery import get_backup_manager

manager = get_backup_manager()
backups = manager.list_backups()

if not backups:
    print('No backups found')
    exit(0)

# Calculate statistics
total_backups = len(backups)
completed_backups = sum(1 for b in backups if b['status'] == 'completed')
failed_backups = sum(1 for b in backups if b['status'] == 'failed')
total_size = sum(b['size_bytes'] for b in backups if b['size_bytes'] > 0)

# Group by type
by_type = {}
for backup in backups:
    backup_type = backup['type']
    if backup_type not in by_type:
        by_type[backup_type] = {'count': 0, 'size': 0}
    by_type[backup_type]['count'] += 1
    by_type[backup_type]['size'] += backup['size_bytes']

print(f'Total backups: {total_backups}')
print(f'Completed: {completed_backups}')
print(f'Failed: {failed_backups}')
print(f'Total size: {total_size / 1024 / 1024:.2f} MB')
print()
print('By type:')
for backup_type, stats in by_type.items():
    size_mb = stats['size'] / 1024 / 1024
    print(f'  {backup_type}: {stats[\"count\"]} backups, {size_mb:.2f} MB')
"

    # Show disk usage
    if [ -d "$BACKUP_DIR" ]; then
        disk_usage=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
        echo "Backup directory size: $disk_usage"
    fi
}

# Main function
main() {
    case "$1" in
        "create")
            create_backup "$2" "$3"
            ;;
        "restore")
            restore_backup "$2" "$3"
            ;;
        "list")
            list_backups "$2"
            ;;
        "status")
            show_backup_status "$2"
            ;;
        "cleanup")
            cleanup_backups
            ;;
        "full")
            create_full_backup "$2"
            ;;
        "recovery")
            disaster_recovery "$2"
            ;;
        "verify")
            verify_backup "$2"
            ;;
        "stats")
            show_stats
            ;;
        *)
            echo "Backup Management Script"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  create <type> [name]    Create backup (database, filesystem, application, configuration)"
            echo "  restore <type> <file>   Restore from backup"
            echo "  list [type]            List backups (optionally filter by type)"
            echo "  status <job_id>        Show backup job status"
            echo "  cleanup                Remove old backups (based on retention policy)"
            echo "  full [name]            Create full system backup"
            echo "  recovery [dir]         Disaster recovery from backup directory"
            echo "  verify <file>          Verify backup file integrity"
            echo "  stats                  Show backup statistics"
            echo ""
            echo "Examples:"
            echo "  $0 create database"
            echo "  $0 create filesystem my_backup"
            echo "  $0 restore database backups/db_backup_20231201.sql"
            echo "  $0 list database"
            echo "  $0 full"
            echo "  $0 recovery backups/"
            exit 1
            ;;
    esac
}

main "$@"