#!/bin/bash

# Panel Interactive Installer (orchestrator)
# This script now delegates most logic to scripts in scripts/install/

set -e

# Basic logging function for early use
log_info() {
    echo "[INFO] $1"
}

# Ensure we are in repo root when sourced remotely
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# If running from pipe (e.g., curl | bash), SCRIPT_DIR might be wrong
if [[ ! -f "$SCRIPT_DIR/install/00-common.sh" ]]; then
    # Running remotely, download helper scripts to temp
    TEMP_DIR=$(mktemp -d)
    log_info "Running remotely, downloading helper scripts to $TEMP_DIR"
    for script in 00-common.sh 10-env-checks.sh 20-deps.sh 30-database.sh 40-redis.sh 50-config.sh 60-monitoring.sh; do
        curl -fsSL "https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install/$script" -o "$TEMP_DIR/$script"
    done
    SCRIPT_DIR="$TEMP_DIR"
    # Create log file in temp dir to avoid permission issues
    touch "$TEMP_DIR/install.log"
fi

cd "$REPO_ROOT" 2>/dev/null || true  # Ignore if repo not cloned yet

# Source shared and step scripts
. "$SCRIPT_DIR/00-common.sh"
. "$SCRIPT_DIR/10-env-checks.sh"
. "$SCRIPT_DIR/20-deps.sh"
. "$SCRIPT_DIR/30-database.sh"
. "$SCRIPT_DIR/40-redis.sh"
. "$SCRIPT_DIR/50-config.sh"
. "$SCRIPT_DIR/60-monitoring.sh"

# Override logging functions for remote execution to avoid permission issues
if [[ -n "$TEMP_DIR" ]]; then
    log_info() {
        echo "[INFO] $1"
    }
    log_warning() {
        echo "[WARNING] $1"
    }
    log_error() {
        echo "[ERROR] $1"
    }
    log_success() {
        echo "[SUCCESS] $1"
    }
fi

PYTHON_CMD="python3"

install_parse_args() {
    for arg in "$@"; do
        case $arg in
            --dry-run) DRY_RUN=true ;;
            --non-interactive) NON_INTERACTIVE=true ;;
            --dev) DEV_MODE=true ;;
            --docker) DOCKER_MODE=true ;;
            --wizard) WIZARD_MODE=true ;;
            --cloud=*) CLOUD_PRESET="${arg#*=}" ;;
            --offline) OFFLINE_MODE=true ;;
            --migrate) MIGRATION_MODE=true ;;
            --monitoring) MONITORING=true ;;
            --debug) DEBUG_MODE=true; set -x ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "  --dry-run          Show what would be installed without making changes"
                echo "  --non-interactive  Use default values for all prompts"
                echo "  --dev              Setup development environment"
                echo "  --docker           Install via Docker Compose"
                echo "  --wizard           Advanced configuration wizard"
                echo "  --cloud=PROVIDER   Cloud preset (aws, gcp, azure, digitalocean)"
                echo "  --offline          Install from offline package cache"
                echo "  --migrate          Migration mode"
                echo "  --monitoring       Setup Prometheus & Grafana (if supported)"
                echo "  --help, -h         Show this help message"
                exit 0
                ;;
        esac
    done
}

install_preflight() {
    log_info "Welcome to the interactive installer for the Panel application!"
    if [[ ${OFFLINE_MODE:-false} != true && -f "scripts/preflight-check.sh" ]]; then
        bash scripts/preflight-check.sh || log_warning "Pre-installation checks failed or script missing"
    fi
}

install_select_profile() {
    if [[ ${DEV_MODE:-false} == true ]]; then
        ENV_CHOICE=1
        DB_CHOICE=1
        INSTALL_REDIS="y"
        INSTALL_DIR=${INSTALL_DIR:-"$HOME/panel"}
        return
    fi

    if [[ ${NON_INTERACTIVE:-false} == true ]]; then
        INSTALL_DIR=${INSTALL_DIR:-"$HOME/panel"}
        DB_CHOICE=${DB_CHOICE:-1}
        INSTALL_REDIS=${INSTALL_REDIS:-y}
        ENV_CHOICE=${ENV_CHOICE:-1}
        return
    fi

    read -p "Installation directory (default: ~/panel): " INSTALL_DIR
    INSTALL_DIR=${INSTALL_DIR:-"$HOME/panel"}
    INSTALL_DIR=$(sanitize_input "$INSTALL_DIR")

    echo ""; echo "Database options:"; echo "1. SQLite (default)"; echo "2. PostgreSQL";
    read -p "Choose database [1-2]: " DB_CHOICE; DB_CHOICE=${DB_CHOICE:-1}

    read -p "Install Redis locally? (y/n, default: y): " INSTALL_REDIS; INSTALL_REDIS=${INSTALL_REDIS:-y}

    echo ""; echo "Environment options:"; echo "1. Development"; echo "2. Production";
    read -p "Choose environment [1-2]: " ENV_CHOICE; ENV_CHOICE=${ENV_CHOICE:-1}
}

install_prepare_directory() {
    INSTALL_DIR=$(eval echo "$INSTALL_DIR")
    log_info "Preparing installation directory at $INSTALL_DIR"
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Directory $INSTALL_DIR already exists. Using existing checkout."
        cd "$INSTALL_DIR"
    else
        git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR" || {
            log_error "Failed to clone repository"
            exit 1
        }
        cd "$INSTALL_DIR"
        add_rollback_step "rm -rf '$INSTALL_DIR'"
    fi
}

main() {
    trap 'handle_error_trap $? $LINENO' ERR

    install_parse_args "$@"
    install_preflight
    install_env_checks
    install_select_profile

    if [[ ${DRY_RUN:-false} == true ]]; then
        log_info "DRY RUN: would install to $INSTALL_DIR with DB_CHOICE=$DB_CHOICE, ENV_CHOICE=$ENV_CHOICE"
        exit 0
    fi

    install_prepare_directory
    install_setup_virtualenv
    install_install_dependencies
    install_setup_database
    install_setup_redis
    install_write_env
    install_create_admin
    install_optional_monitoring
    show_elapsed_time
    log_success "Panel installation completed."
}

main "$@"