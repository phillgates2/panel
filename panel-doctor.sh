#!/usr/bin/env bash
set -euo pipefail

# Panel Doctor: Self-healing diagnostics and auto-fix
# Usage: bash panel-doctor.sh [--fix]
# Checks: systemd/OpenRC services, MariaDB socket, HTTP port, Flask migrations, instance dirs

FIX_MODE=false
for arg in "$@"; do
    [[ "$arg" == "--fix" ]] && FIX_MODE=true
    [[ "$arg" == "-f" ]] && FIX_MODE=true
    [[ "$arg" == "help" || "$arg" == "--help" || "$arg" == "-h" ]] && echo "Usage: bash panel-doctor.sh [--fix]" && exit 0
    done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect privilege escalation
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

# 1. Check systemd/OpenRC services
check_service() {
    local svc="$1"
    if command -v systemctl &>/dev/null; then
        if systemctl is-active --quiet "$svc"; then
            log "$svc is active (systemd)"
        else
            warn "$svc is NOT active (systemd)"
            if $FIX_MODE; then
                $SUDO systemctl restart "$svc" && log "Restarted $svc" || warn "Failed to restart $svc"
            fi
        fi
    elif command -v rc-service &>/dev/null; then
        if rc-service "$svc" status 2>/dev/null | grep -q "started"; then
            log "$svc is started (OpenRC)"
        else
            warn "$svc is NOT started (OpenRC)"
            if $FIX_MODE; then
                $SUDO rc-service "$svc" restart && log "Restarted $svc" || warn "Failed to restart $svc"
            fi
        fi
    else
        warn "No service manager detected for $svc"
    fi
}

# 2. Check MariaDB socket
check_mariadb_socket() {
    local socket="/var/run/mysqld/mysqld.sock"
    [[ -S "$socket" ]] && log "MariaDB socket found: $socket" && return 0
    socket="/var/lib/mysql/mysql.sock"
    [[ -S "$socket" ]] && log "MariaDB socket found: $socket" && return 0
    warn "MariaDB socket not found"
    return 1
}

# 3. Check HTTP port (default 8080)
check_http_port() {
    local port="8080"
    if ss -ltn | grep -q ":$port "; then
        log "HTTP port $port is listening"
    else
        warn "HTTP port $port is NOT listening"
        if $FIX_MODE; then
            check_service "panel-gunicorn.service"
        fi
    fi
}

# 4. Check Flask migrations
check_migrations() {
    local db="instance/panel_dev.db"
    if [[ -f "$db" ]]; then
        log "SQLite DB exists: $db"
    else
        warn "SQLite DB missing: $db"
        if $FIX_MODE; then
            log "Attempting Flask DB migration..."
            $SUDO bash -c 'source venv/bin/activate && flask db upgrade' && log "Migration attempted" || warn "Migration failed"
        fi
    fi
}

# 5. Check instance dirs
check_instance_dirs() {
    for d in instance instance/logs instance/audit_logs instance/backups; do
        if [[ -d "$d" ]]; then
            log "Dir exists: $d"
        else
            warn "Dir missing: $d"
            if $FIX_MODE; then
                mkdir -p "$d" && log "Created $d" || warn "Failed to create $d"
            fi
        fi
    done
}

# Run checks
log "Panel Doctor: Starting diagnostics..."
check_service "panel-gunicorn.service"
check_service "rq-worker-supervised.service"
check_service "mariadb"
check_mariadb_socket
check_http_port
check_migrations
check_instance_dirs
log "Panel Doctor: Diagnostics complete."
if $FIX_MODE; then
    log "Auto-fix mode: attempted repairs where possible."
fi
