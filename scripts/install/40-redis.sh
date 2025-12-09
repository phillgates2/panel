#!/bin/bash

install_setup_redis() {
    log_info "Setting up Redis..."

    if [[ $INSTALL_REDIS == "y" ]]; then
        if ! command -v redis-cli &> /dev/null; then
            log_info "Installing Redis..."
            $PKG_UPDATE
            if [[ "$OSTYPE" == "linux-gnu"* ]]; then
                $PKG_INSTALL redis-server || {
                    log_error "Failed to install Redis"
                    exit 1
                }
                sudo systemctl enable redis-server
                sudo systemctl start redis-server
                add_rollback_step "sudo systemctl stop redis-server && sudo systemctl disable redis-server"
            elif [[ "$OSTYPE" == "darwin"* ]]; then
                $PKG_INSTALL redis || {
                    log_error "Failed to install Redis"
                    exit 1
                }
                brew services start redis
                add_rollback_step "brew services stop redis"
            fi
            sleep 2
        fi

        if redis-cli ping &> /dev/null; then
            log_success "Redis is running"
        else
            log_error "Redis is installed but not responding"
            exit 1
        fi

        export PANEL_REDIS_URL="redis://localhost:6379/0"
    else
        if [[ ${NON_INTERACTIVE:-false} != true ]]; then
            read -p "Redis URL (default: redis://localhost:6379/0): " REDIS_URL
            export PANEL_REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
        fi
        log_info "Using external Redis at $PANEL_REDIS_URL"
    fi
}
