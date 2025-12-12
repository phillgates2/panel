#!/bin/bash

install_write_env() {
    log_info "Creating configuration file (.env)..."

    if [[ -f ".env" ]]; then
        cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Existing .env backed up"
    fi

    local env_type
    if [[ $ENV_CHOICE -eq 1 ]]; then
        env_type="development"
    else
        env_type="production"
    fi

    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    export PANEL_SECRET_KEY="$SECRET_KEY"

    cat > .env << EOF
# Database Configuration
DATABASE_URL=$PANEL_DATABASE_URI
PANEL_DATABASE_URI=$PANEL_DATABASE_URI

# Redis Configuration
REDIS_URL=$PANEL_REDIS_URL
PANEL_REDIS_URL=$PANEL_REDIS_URL

# Application Configuration
SECRET_KEY=$SECRET_KEY
PANEL_SECRET_KEY=$SECRET_KEY
FLASK_ENV=$env_type
PANEL_ENV=$env_type

# Server Configuration
FLASK_APP=app.py
HOST=0.0.0.0
PORT=5000

# Security
SESSION_COOKIE_SECURE=$(if [[ $ENV_CHOICE -eq 2 ]]; then echo "True"; else echo "False"; fi)
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=$(if [[ $ENV_CHOICE -eq 1 ]]; then echo "DEBUG"; else echo "INFO"; fi)
EOF

    log_success ".env configuration written"
}

install_create_admin() {
    if [[ ${NON_INTERACTIVE:-false} == true ]]; then
        log_info "Non-interactive mode: skipping admin user creation"
        return
    fi

    echo ""
    log_info "Creating admin user for the application:"

    while true; do
        read -p "Admin username: " ADMIN_USERNAME
        ADMIN_USERNAME=$(sanitize_input "$ADMIN_USERNAME")
        if [[ ! "$ADMIN_USERNAME" =~ ^[a-zA-Z0-9]{3,16}$ ]]; then
            log_error "Invalid username. Only alphanumeric characters, 3-16 chars."
        else
            break
        fi
    done

    while true; do
        read -p "Admin password: " -s ADMIN_PASSWORD
        echo ""
        read -p "Confirm password: " -s ADMIN_PASSWORD_CONFIRM
        echo ""
        if ! validate_password "$ADMIN_PASSWORD"; then
            continue
        fi
        if [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]]; then
            log_error "Passwords do not match"
            continue
        fi
        break
    done

    log_info "Creating admin user in the database..."

    if [[ $DB_CHOICE -eq 1 ]]; then
        python3 - << PYCODE
from werkzeug.security import generate_password_hash
import sqlite3
import os

install_dir = os.getenv("INSTALL_DIR", ".")
password = "$ADMIN_PASSWORD"
username = "$ADMIN_USERNAME"

conn = sqlite3.connect(os.path.join(install_dir, "panel.db"))
cur = conn.cursor()
cur.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)", (username, generate_password_hash(password)))
conn.commit()
conn.close()
PYCODE
    else
        PGPASSWORD=$DB_PASSWORD psql -h localhost -U panel_user -d panel_db -c "CREATE ROLE $ADMIN_USERNAME WITH LOGIN PASSWORD '$ADMIN_PASSWORD' CREATEDB CREATEROLE;" || {
            log_error "Failed to create admin user role"
            exit 1
        }
        PGPASSWORD=$DB_PASSWORD psql -h localhost -U panel_user -d panel_db -c "GRANT ALL PRIVILEGES ON DATABASE panel_db TO $ADMIN_USERNAME;" || {
            log_error "Failed to grant privileges to admin user"
            exit 1
        }
    fi

    log_success "Admin user setup complete"
}
