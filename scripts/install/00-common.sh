#!/bin/bash

# Common functions and shared state for Panel installer

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Global flags (default values)
DRY_RUN=${DRY_RUN:-false}
NON_INTERACTIVE=${NON_INTERACTIVE:-false}
DEV_MODE=${DEV_MODE:-false}
DOCKER_MODE=${DOCKER_MODE:-false}
WIZARD_MODE=${WIZARD_MODE:-false}
CLOUD_PRESET=${CLOUD_PRESET:-""}
OFFLINE_MODE=${OFFLINE_MODE:-false}
MIGRATION_MODE=${MIGRATION_MODE:-false}
MONITORING=${MONITORING:-false}

ROLLBACK_STEPS=()
INSTALL_START_TIME=${INSTALL_START_TIME:-$(date +%s)}

log_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> install.log 2>/dev/null || true
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> install.log 2>/dev/null || true
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> install.log 2>/dev/null || true
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> install.log 2>/dev/null || true
}

log_debug() {
    if [[ ${DEBUG_MODE:-false} == true ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEBUG: $1" >> install.log 2>/dev/null || true
    fi
}

add_rollback_step() {
    ROLLBACK_STEPS+=("$1")
}

rollback_installation() {
    if [[ ${#ROLLBACK_STEPS[@]} -eq 0 ]]; then
        return
    fi

    log_error "Installation failed. Rolling back changes..."
    for ((i=${#ROLLBACK_STEPS[@]}-1; i>=0; i--)); do
        log_info "Rolling back: ${ROLLBACK_STEPS[$i]}"
        eval "${ROLLBACK_STEPS[$i]}" 2>/dev/null || true
    done
    log_success "Rollback completed"
    exit 1
}

show_elapsed_time() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - INSTALL_START_TIME))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    log_info "Installation took ${minutes}m ${seconds}s"
}

handle_error_trap() {
    local exit_code=$1
    local line_number=$2
    log_error "Installation failed at line $line_number with exit code $exit_code"

    if [[ ${NON_INTERACTIVE:-false} != true ]]; then
        echo "Recovery options:"
        echo "1. Retry failed step"
        echo "2. Skip failed step and continue"
        echo "3. Rollback and exit"
        read -p "Choose option [3]: " RECOVERY_CHOICE
        RECOVERY_CHOICE=${RECOVERY_CHOICE:-3}

        case $RECOVERY_CHOICE in
            1)
                log_info "Retrying failed step..."
                return 0
                ;;
            2)
                log_warning "Skipping failed step and continuing..."
                return 0
                ;;
            *)
                rollback_installation
                ;;
        esac
    else
        rollback_installation
    fi
}

validate_password() {
    local password=$1
    if [[ ${#password} -lt 12 ]]; then
        log_error "Password must be at least 12 characters"
        return 1
    fi
    if ! [[ $password =~ [A-Z] ]] || ! [[ $password =~ [a-z] ]] || ! [[ $password =~ [0-9] ]]; then
        log_error "Password must contain uppercase, lowercase, and numeric characters"
        return 1
    fi
    return 0
}

sanitize_input() {
    echo "$1" | sed 's/[^a-zA-Z0-9._@-]//g'
}

detect_package_manager() {
    if command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v yum &> /dev/null; then
        echo "yum"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    else
        echo "unknown"
    fi
}
