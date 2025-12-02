#!/bin/bash

#############################################################################
# Panel Distributed Setup Script
# Configure Panel in multi-server distributed architecture
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Distributed Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

error() { echo -e "${RED}✗ $1${NC}"; exit 1; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }
warn() { echo -e "${YELLOW}! $1${NC}"; }

# Server roles
setup_app_server() {
    local db_host=$1
    local redis_host=$2
    
    info "Setting up application server..."
    
    # Run installer with external database/redis
    bash scripts/install-interactive.sh \
        --non-interactive \
        --database-type=postgresql \
        --database-host="$db_host" \
        --redis-host="$redis_host"
    
    success "Application server configured"
}

# Setup database server
setup_db_server() {
    info "Setting up database server..."
    
    # Install PostgreSQL
    if [[ -f /etc/debian_version ]]; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
    elif [[ -f /etc/redhat-release ]]; then
        sudo yum install -y postgresql-server postgresql-contrib
        sudo postgresql-setup initdb
    fi
    
    # Configure PostgreSQL for remote connections
    PG_CONF="/etc/postgresql/$(ls /etc/postgresql | tail -1)/main/postgresql.conf"
    PG_HBA="/etc/postgresql/$(ls /etc/postgresql | tail -1)/main/pg_hba.conf"
    
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
    
    echo "host    all             all             10.0.0.0/8              md5" | sudo tee -a "$PG_HBA"
    
    sudo systemctl restart postgresql
    
    success "Database server configured"
}

# Setup Redis server
setup_redis_server() {
    info "Setting up Redis server..."
    
    if [[ -f /etc/debian_version ]]; then
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif [[ -f /etc/redhat-release ]]; then
        sudo yum install -y redis
    fi
    
    # Configure Redis for remote connections
    sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
    sudo sed -i 's/protected-mode yes/protected-mode no/' /etc/redis/redis.conf
    
    # Set password
    REDIS_PASSWORD=$(openssl rand -base64 32)
    echo "requirepass $REDIS_PASSWORD" | sudo tee -a /etc/redis/redis.conf
    
    sudo systemctl restart redis
    
    success "Redis server configured"
    info "Redis password: $REDIS_PASSWORD"
}

# Interactive setup
interactive_setup() {
    print_header
    
    echo "Distributed Architecture Setup"
    echo "==============================="
    echo
    echo "1. All-in-one (Single Server)"
    echo "2. Application Server"
    echo "3. Database Server"
    echo "4. Redis Server"
    echo "5. Load Balancer"
    echo
    read -p "Select server role: " ROLE
    
    case $ROLE in
        1)
            info "Setting up all-in-one server..."
            bash scripts/install-interactive.sh
            ;;
        2)
            read -p "Database host: " DB_HOST
            read -p "Redis host: " REDIS_HOST
            setup_app_server "$DB_HOST" "$REDIS_HOST"
            ;;
        3)
            setup_db_server
            ;;
        4)
            setup_redis_server
            ;;
        5)
            bash scripts/generate-lb-config.sh
            ;;
        *)
            error "Invalid selection"
            ;;
    esac
}

# Generate distributed config template
generate_config() {
    cat > distributed-config.yml << 'EOF'
# Panel Distributed Architecture Configuration

# Load Balancer
load_balancer:
  host: 10.0.1.10
  type: nginx
  ssl: true
  
# Application Servers
app_servers:
  - host: 10.0.1.20
    port: 5000
    workers: 4
  - host: 10.0.1.21
    port: 5000
    workers: 4
  - host: 10.0.1.22
    port: 5000
    workers: 4

# Database Server
database:
  host: 10.0.1.30
  port: 5432
  name: panel
  user: panel
  password: CHANGE_ME
  pool_size: 20
  max_overflow: 10
  
# Redis Server
redis:
  host: 10.0.1.40
  port: 6379
  password: CHANGE_ME
  db: 0
  
# Celery Workers
celery_workers:
  - host: 10.0.1.50
    concurrency: 4
  - host: 10.0.1.51
    concurrency: 4

# Monitoring
monitoring:
  prometheus: 10.0.1.60
  grafana: 10.0.1.61
EOF
    
    success "Configuration template created: distributed-config.yml"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup Panel in distributed architecture

Options:
    --interactive        Interactive setup (default)
    --app-server         Setup application server
    --db-server          Setup database server
    --redis-server       Setup Redis server
    --generate-config    Generate config template
    --help               Show this help

EOF
}

main() {
    case "${1:-interactive}" in
        --interactive|interactive)
            interactive_setup
            ;;
        --app-server)
            setup_app_server "$2" "$3"
            ;;
        --db-server)
            setup_db_server
            ;;
        --redis-server)
            setup_redis_server
            ;;
        --generate-config)
            generate_config
            ;;
        --help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
}

main "$@"
