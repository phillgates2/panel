#!/usr/bin/env bash
set -euo pipefail

# Panel Doctor: diagnostics and auto-fix
# Usage: bash panel-doctor.sh [--fix]
# Checks: services, HTTP port, DB env, DB connectivity, migrations state

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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

load_env_file_if_present() {
    local env_file="/etc/panel/panel.env"
    if [[ -f "$env_file" ]]; then
        # shellcheck disable=SC1090
        set -a
        source "$env_file"
        set +a
        log "Loaded env file: $env_file"
    else
        warn "Env file missing: $env_file"
    fi
}

normalize_pg_url_for_psql() {
    # psql does not understand SQLAlchemy driver URLs like postgresql+psycopg2://
    local url="$1"
    echo "${url/postgresql+psycopg2:\/\//postgresql:\/\/}"
}

check_db_env() {
    if [[ -n "${DATABASE_URL:-}" || -n "${SQLALCHEMY_DATABASE_URI:-}" ]]; then
        log "DB env present (DATABASE_URL/SQLALCHEMY_DATABASE_URI)"
    else
        warn "DB env missing: set DATABASE_URL (recommended)"
    fi
}

check_db_connectivity() {
    local url="${DATABASE_URL:-${SQLALCHEMY_DATABASE_URI:-}}"
    if [[ -z "${url:-}" ]]; then
        warn "Skipping DB connectivity check (no DB URL in env)"
        return 0
    fi

    if command -v psql &>/dev/null; then
        local psql_url
        psql_url="$(normalize_pg_url_for_psql "$url")"
        if PGPASSWORD="${PANEL_DB_PASS:-${PGPASSWORD:-}}" psql "$psql_url" -Atc "select 1" &>/dev/null; then
            log "PostgreSQL connection OK"
        else
            warn "PostgreSQL connection FAILED"
        fi
    else
        warn "psql not found; skipping direct connectivity check"
    fi

    if command -v python3 &>/dev/null && [[ -f "$ROOT_DIR/tools/scripts/db_verify.py" ]]; then
        python3 "$ROOT_DIR/tools/scripts/db_verify.py" || warn "db_verify.py reported an issue"
    fi
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

check_migrations() {
    if command -v alembic &>/dev/null; then
        if alembic current &>/dev/null; then
            log "Alembic is runnable"
        else
            warn "Alembic current failed (check env + DB URL)"
        fi
    else
        warn "alembic not found; skipping alembic current"
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
load_env_file_if_present
check_db_env
check_http_port
check_db_connectivity
check_migrations
check_instance_dirs
log "Panel Doctor: Diagnostics complete."
if $FIX_MODE; then
    log "Auto-fix mode: attempted repairs where possible."
fi
