#!/bin/bash

install_setup_database() {
    log_info "Configuring database..."

    if [[ $DB_CHOICE -eq 1 ]]; then
        export PANEL_DATABASE_URI="sqlite:///$INSTALL_DIR/panel.db"
        log_success "SQLite database will be created at: $INSTALL_DIR/panel.db"
        return
    fi

    if [[ $DB_CHOICE -eq 2 ]]; then
        log_info "Setting up PostgreSQL..."
        if ! command -v psql &> /dev/null; then
            log_warning "PostgreSQL not found. Installing..."
            $PKG_UPDATE
            $PKG_INSTALL postgresql postgresql-contrib || {
                log_error "Failed to install PostgreSQL"
                exit 1
            }
            sudo systemctl enable postgresql
            sudo systemctl start postgresql
            add_rollback_step "sudo systemctl stop postgresql && sudo systemctl disable postgresql"
        fi

        sleep 2

        if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='panel_user'" | grep -q 1; then
            log_warning "User 'panel_user' already exists"
        else
            sudo -u postgres psql -c "CREATE USER panel_user WITH CREATEDB PASSWORD 'changeme';" || {
                log_error "Failed to create database user"
                exit 1
            }
            add_rollback_step "sudo -u postgres psql -c \"DROP USER IF EXISTS panel_user;\""
        fi

        if sudo -u postgres psql -lqt | cut -d '|' -f 1 | grep -qw panel_db; then
            log_warning "Database 'panel_db' already exists"
        else
            sudo -u postgres createdb -O panel_user panel_db || {
                log_error "Failed to create database"
                exit 1
            }
            add_rollback_step "sudo -u postgres dropdb panel_db"
        fi

        if [[ ${NON_INTERACTIVE:-false} != true ]]; then
            read -p "PostgreSQL password for panel_user (press Enter for default 'changeme'): " -s DB_PASSWORD
            echo ""
            DB_PASSWORD=${DB_PASSWORD:-changeme}
            if [[ "$DB_PASSWORD" != "changeme" ]]; then
                sudo -u postgres psql -c "ALTER USER panel_user WITH PASSWORD '$DB_PASSWORD';"
            fi
        else
            DB_PASSWORD="changeme"
        fi

        export PANEL_DATABASE_URI="postgresql://panel_user:$DB_PASSWORD@localhost/panel_db"
        log_success "PostgreSQL database configured"
        return
    fi

    if [[ $DB_CHOICE -eq 3 ]]; then
        export PANEL_DATABASE_URI="postgresql://$EXTERNAL_DB_USER:$EXTERNAL_DB_PASS@$EXTERNAL_DB_HOST:$EXTERNAL_DB_PORT/$EXTERNAL_DB_NAME"
        log_success "External database configured"
        return
    fi

    log_error "Unknown DB_CHOICE: $DB_CHOICE"
    exit 1
}
