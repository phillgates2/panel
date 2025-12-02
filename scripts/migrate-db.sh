#!/bin/bash

#############################################################################
# Panel Database Migration Helper
# Migrate between SQLite and PostgreSQL databases
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/panel}"
BACKUP_DIR="${2:-/var/backups/panel}"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Database Migration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

warn() {
    echo -e "${YELLOW}! $1${NC}"
}

cd "$INSTALL_DIR" || error "Install directory not found: $INSTALL_DIR"

# Detect current database type
detect_current_db() {
    if [[ ! -f "config.py" ]]; then
        error "config.py not found"
    fi
    
    source venv/bin/activate
    
    DB_URI=$(python -c "from config import Config; print(Config.SQLALCHEMY_DATABASE_URI)")
    
    if [[ "$DB_URI" =~ ^sqlite:/// ]]; then
        echo "sqlite"
    elif [[ "$DB_URI" =~ ^postgresql:// ]]; then
        echo "postgresql"
    else
        error "Unknown database type: $DB_URI"
    fi
}

# Export data from current database
export_data() {
    local format=$1
    local output_file=$2
    
    info "Exporting data from current database..."
    
    python -c "
from app import create_app
from app.extensions import db
from sqlalchemy import inspect
import json
import sys

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    data = {}
    
    for table in tables:
        if table.startswith('alembic_'):
            continue
        
        try:
            result = db.session.execute(db.text(f'SELECT * FROM {table}'))
            rows = [dict(row._mapping) for row in result]
            data[table] = rows
            print(f'Exported {len(rows)} rows from {table}', file=sys.stderr)
        except Exception as e:
            print(f'Error exporting {table}: {e}', file=sys.stderr)
    
    with open('$output_file', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print('Export complete', file=sys.stderr)
"
    
    success "Data exported to $output_file"
}

# Import data to new database
import_data() {
    local input_file=$1
    
    info "Importing data to new database..."
    
    python -c "
from app import create_app
from app.extensions import db
from sqlalchemy import text
import json
import sys

app = create_app()

with open('$input_file', 'r') as f:
    data = json.load(f)

with app.app_context():
    for table, rows in data.items():
        if not rows:
            continue
        
        try:
            # Get column names from first row
            columns = list(rows[0].keys())
            
            for row in rows:
                placeholders = ', '.join([f':{col}' for col in columns])
                cols_str = ', '.join(columns)
                
                query = text(f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders})')
                db.session.execute(query, row)
            
            db.session.commit()
            print(f'Imported {len(rows)} rows into {table}', file=sys.stderr)
        except Exception as e:
            db.session.rollback()
            print(f'Error importing into {table}: {e}', file=sys.stderr)
    
    print('Import complete', file=sys.stderr)
"
    
    success "Data imported from $input_file"
}

# Backup current database
backup_database() {
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.json"
    
    export_data "json" "$BACKUP_FILE"
    
    success "Database backed up to $BACKUP_FILE"
    echo "$BACKUP_FILE"
}

# Migrate SQLite to PostgreSQL
migrate_sqlite_to_postgresql() {
    local pg_host=$1
    local pg_port=${2:-5432}
    local pg_db=$3
    local pg_user=$4
    local pg_pass=$5
    
    info "Migrating from SQLite to PostgreSQL..."
    
    # Backup current database
    BACKUP_FILE=$(backup_database)
    
    # Update config.py
    info "Updating config.py..."
    
    NEW_DB_URI="postgresql://${pg_user}:${pg_pass}@${pg_host}:${pg_port}/${pg_db}"
    
    sed -i.bak "s|SQLALCHEMY_DATABASE_URI.*|SQLALCHEMY_DATABASE_URI = '${NEW_DB_URI}'|" config.py
    
    success "Config updated"
    
    # Create PostgreSQL database if it doesn't exist
    info "Setting up PostgreSQL database..."
    
    PGPASSWORD="$pg_pass" psql -h "$pg_host" -p "$pg_port" -U "$pg_user" -tc "SELECT 1 FROM pg_database WHERE datname = '$pg_db'" | grep -q 1 || \
    PGPASSWORD="$pg_pass" psql -h "$pg_host" -p "$pg_port" -U "$pg_user" -c "CREATE DATABASE $pg_db"
    
    success "PostgreSQL database ready"
    
    # Run migrations
    info "Running database migrations..."
    source venv/bin/activate
    flask db upgrade
    
    success "Migrations complete"
    
    # Import data
    import_data "$BACKUP_FILE"
    
    success "Migration from SQLite to PostgreSQL complete!"
}

# Migrate PostgreSQL to SQLite
migrate_postgresql_to_sqlite() {
    local sqlite_path=$1
    
    info "Migrating from PostgreSQL to SQLite..."
    
    # Backup current database
    BACKUP_FILE=$(backup_database)
    
    # Update config.py
    info "Updating config.py..."
    
    NEW_DB_URI="sqlite:///${sqlite_path}"
    
    sed -i.bak "s|SQLALCHEMY_DATABASE_URI.*|SQLALCHEMY_DATABASE_URI = '${NEW_DB_URI}'|" config.py
    
    success "Config updated"
    
    # Create SQLite database
    info "Setting up SQLite database..."
    
    source venv/bin/activate
    flask db upgrade
    
    success "SQLite database created"
    
    # Import data
    import_data "$BACKUP_FILE"
    
    success "Migration from PostgreSQL to SQLite complete!"
    warn "Note: SQLite is not recommended for production use"
}

# Interactive mode
interactive_migration() {
    print_header
    
    CURRENT_DB=$(detect_current_db)
    
    echo "Current database: ${CURRENT_DB}"
    echo
    
    if [[ "$CURRENT_DB" == "sqlite" ]]; then
        echo "Migrate to PostgreSQL"
        echo "----------------------------------------"
        
        read -p "PostgreSQL host [localhost]: " PG_HOST
        PG_HOST=${PG_HOST:-localhost}
        
        read -p "PostgreSQL port [5432]: " PG_PORT
        PG_PORT=${PG_PORT:-5432}
        
        read -p "Database name [panel]: " PG_DB
        PG_DB=${PG_DB:-panel}
        
        read -p "Database user [panel]: " PG_USER
        PG_USER=${PG_USER:-panel}
        
        read -sp "Database password: " PG_PASS
        echo
        
        echo
        warn "This will migrate your database from SQLite to PostgreSQL"
        warn "A backup will be created before migration"
        read -p "Continue? (yes/no): " CONFIRM
        
        if [[ "$CONFIRM" == "yes" ]]; then
            migrate_sqlite_to_postgresql "$PG_HOST" "$PG_PORT" "$PG_DB" "$PG_USER" "$PG_PASS"
        else
            info "Migration cancelled"
        fi
        
    elif [[ "$CURRENT_DB" == "postgresql" ]]; then
        echo "Migrate to SQLite"
        echo "----------------------------------------"
        
        read -p "SQLite database path [./panel.db]: " SQLITE_PATH
        SQLITE_PATH=${SQLITE_PATH:-./panel.db}
        
        echo
        warn "This will migrate your database from PostgreSQL to SQLite"
        warn "SQLite is not recommended for production use"
        warn "A backup will be created before migration"
        read -p "Continue? (yes/no): " CONFIRM
        
        if [[ "$CONFIRM" == "yes" ]]; then
            migrate_postgresql_to_sqlite "$SQLITE_PATH"
        else
            info "Migration cancelled"
        fi
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Migrate Panel database between SQLite and PostgreSQL

Options:
    --to-postgresql HOST PORT DB USER PASS    Migrate to PostgreSQL
    --to-sqlite PATH                          Migrate to SQLite
    --backup                                  Backup current database
    --help                                    Show this help

Examples:
    # Interactive migration
    $0
    
    # Migrate to PostgreSQL
    $0 --to-postgresql localhost 5432 panel panel password123
    
    # Migrate to SQLite
    $0 --to-sqlite ./panel.db
    
    # Backup only
    $0 --backup

EOF
}

# Main
main() {
    if [[ $# -eq 0 ]]; then
        interactive_migration
    else
        case "$1" in
            --to-postgresql)
                if [[ $# -lt 6 ]]; then
                    error "Missing arguments for --to-postgresql"
                fi
                print_header
                migrate_sqlite_to_postgresql "$2" "$3" "$4" "$5" "$6"
                ;;
            --to-sqlite)
                if [[ $# -lt 2 ]]; then
                    error "Missing argument for --to-sqlite"
                fi
                print_header
                migrate_postgresql_to_sqlite "$2"
                ;;
            --backup)
                print_header
                backup_database
                ;;
            --help)
                usage
                ;;
            *)
                error "Unknown option: $1"
                usage
                ;;
        esac
    fi
}

main "$@"
