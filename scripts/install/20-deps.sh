#!/bin/bash

install_setup_virtualenv() {
    log_info "Setting up Python virtual environment..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    add_rollback_step "rm -rf '$INSTALL_DIR/venv'"
    log_success "Virtual environment ready"
}

install_install_dependencies() {
    log_info "Installing Python dependencies..."

    if [[ -f "requirements/requirements.txt" ]]; then
        REQUIREMENTS_FILE="requirements/requirements.txt"
    elif [[ -f "requirements.txt" ]]; then
        REQUIREMENTS_FILE="requirements.txt"
    else
        log_error "requirements.txt not found"
        exit 1
    fi

    if [[ ${OFFLINE_MODE:-false} == true ]]; then
        log_info "Offline installation mode enabled"
        OFFLINE_CACHE="$INSTALL_DIR/offline-packages"
        if [[ ! -d "$OFFLINE_CACHE" ]]; then
            log_error "Offline package cache not found at $OFFLINE_CACHE"
            exit 1
        fi
        pip install --upgrade --no-index --find-links="$OFFLINE_CACHE" pip || log_warning "Failed to upgrade pip offline"
        pip install --no-index --find-links="$OFFLINE_CACHE" -r "$REQUIREMENTS_FILE" || {
            log_error "Failed to install Python dependencies from offline cache"
            exit 1
        }
    else
        pip install --upgrade pip || {
            log_error "Failed to upgrade pip"
            exit 1
        }
        pip install -r "$REQUIREMENTS_FILE" || {
            log_error "Failed to install Python dependencies"
            exit 1
        }
    fi

    log_success "Python dependencies installed"
}
