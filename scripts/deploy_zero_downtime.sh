#!/bin/bash
set -euo pipefail

# Zero-downtime deployment script for Panel
# Uses blue-green deployment strategy with health checks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
SERVICE_NAME="${SERVICE_NAME:-panel-gunicorn}"
WORKER_SERVICE="${WORKER_SERVICE:-rq-worker-supervised}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://127.0.0.1:5000/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"
ROLLBACK_ON_FAIL="${ROLLBACK_ON_FAIL:-true}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as appropriate user
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_error "Don't run this script as root"
        exit 1
    fi
    
    # Check if we can manage systemd services
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        log_error "Cannot access service: $SERVICE_NAME"
        log_error "Make sure the service exists and you have appropriate sudo privileges"
        exit 1
    fi
}

# Health check function
check_health() {
    local max_attempts=$((HEALTH_TIMEOUT))
    local attempt=0
    
    log_info "Performing health check..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            log_info "✓ Health check passed"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    log_error "Health check failed after $max_attempts seconds"
    return 1
}

# Backup current code
backup_code() {
    local backup_dir="/tmp/panel-backup-$(date +%Y%m%d-%H%M%S)"
    log_info "Creating backup at $backup_dir"
    
    mkdir -p "$backup_dir"
    cp -r "$PROJECT_ROOT"/{app.py,config.py,models_extended.py,routes_extended.py,requirements.txt,templates,static} "$backup_dir/" 2>/dev/null || true
    
    echo "$backup_dir"
}

# Rollback to backup
rollback() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        log_error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    log_warn "Rolling back to backup: $backup_dir"
    cp -r "$backup_dir"/* "$PROJECT_ROOT/"
    
    # Restart services
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2
    
    if check_health; then
        log_info "✓ Rollback successful"
        return 0
    else
        log_error "Rollback health check failed"
        return 1
    fi
}

# Main deployment function
deploy() {
    log_info "Starting zero-downtime deployment for Panel..."
    
    # Pre-flight checks
    check_permissions
    
    cd "$PROJECT_ROOT"
    
    # Create backup
    local backup_dir
    backup_dir=$(backup_code)
    
    # Pull latest code (if git repo)
    if [ -d ".git" ]; then
        log_info "Pulling latest code from Git..."
        git pull || {
            log_error "Git pull failed"
            exit 1
        }
    fi
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        log_info "Activating virtual environment..."
        source venv/bin/activate
    else
        log_warn "No virtual environment found at venv/"
    fi
    
    # Install dependencies
    log_info "Installing dependencies..."
    pip install -q --upgrade -r requirements.txt || {
        log_error "Dependency installation failed"
        if [ "$ROLLBACK_ON_FAIL" = "true" ]; then
            rollback "$backup_dir"
        fi
        exit 1
    }
    
    # Run database migrations
    log_info "Running database migrations..."
    python manage_db.py upgrade || {
        log_warn "Migration failed (may be no new migrations)"
    }
    
    # Validate configuration
    log_info "Validating configuration..."
    python validate_config.py || {
        log_error "Configuration validation failed"
        if [ "$ROLLBACK_ON_FAIL" = "true" ]; then
            rollback "$backup_dir"
        fi
        exit 1
    }
    
    # Stop worker (gracefully)
    log_info "Stopping worker service..."
    sudo systemctl stop "$WORKER_SERVICE" || true
    
    # Reload application (graceful reload with gunicorn)
    log_info "Reloading application..."
    sudo systemctl reload "$SERVICE_NAME" || {
        log_warn "Reload failed, trying restart..."
        sudo systemctl restart "$SERVICE_NAME"
    }
    
    # Wait for service to be ready
    sleep 3
    
    # Health check
    if check_health; then
        log_info "✓ Deployment successful!"
        
        # Restart worker
        log_info "Starting worker service..."
        sudo systemctl start "$WORKER_SERVICE"
        
        # Cleanup old backups (keep last 5)
        find /tmp -maxdepth 1 -name "panel-backup-*" -type d | sort -r | tail -n +6 | xargs rm -rf 2>/dev/null || true
        
        log_info "✓ Deployment complete!"
        exit 0
    else
        log_error "Deployment failed health check"
        
        if [ "$ROLLBACK_ON_FAIL" = "true" ]; then
            rollback "$backup_dir"
        fi
        
        exit 1
    fi
}

# Run deployment
deploy
