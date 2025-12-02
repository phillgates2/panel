#!/bin/bash

#############################################################################
# Panel Cluster Setup Script
# Setup multi-instance Panel cluster with shared database
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
    echo -e "${BLUE}  Panel Cluster Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; exit 1; }
warn() { echo -e "${YELLOW}! $1${NC}"; }

# Setup cluster node
setup_cluster_node() {
    local node_id=$1
    local db_host=$2
    local redis_host=$3
    local install_dir="/opt/panel-node${node_id}"
    
    info "Setting up cluster node $node_id..."
    
    # Clone and setup
    git clone https://github.com/phillgates2/panel.git "$install_dir"
    cd "$install_dir"
    
    # Run installer
    bash scripts/install-interactive.sh \
        --non-interactive \
        --install-dir="$install_dir" \
        --database-host="$db_host" \
        --redis-host="$redis_host"
    
    # Configure for cluster
    cat >> config.py << EOF

# Cluster Configuration
CLUSTER_NODE_ID = '$node_id'
CLUSTER_ENABLED = True
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url(REDIS_URL)
EOF
    
    # Use different port
    PORT=$((5000 + node_id))
    
    # Update systemd service
    sudo tee /etc/systemd/system/panel-node${node_id}.service > /dev/null << EOSERVICE
[Unit]
Description=Panel Application Node $node_id
After=network.target

[Service]
Type=notify
User=panel
Group=panel
WorkingDirectory=$install_dir
Environment="PATH=$install_dir/venv/bin"
ExecStart=$install_dir/venv/bin/gunicorn -c gunicorn_config.py -b 0.0.0.0:$PORT app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOSERVICE
    
    sudo systemctl daemon-reload
    sudo systemctl enable panel-node${node_id}
    sudo systemctl start panel-node${node_id}
    
    success "Cluster node $node_id ready on port $PORT"
}

# Setup shared database
setup_shared_database() {
    info "Setting up shared database..."
    
    bash scripts/setup-distributed.sh --db-server
    
    success "Shared database ready"
}

# Setup shared Redis
setup_shared_redis() {
    info "Setting up shared Redis..."
    
    bash scripts/setup-distributed.sh --redis-server
    
    success "Shared Redis ready"
}

# Configure session sharing
configure_session_sharing() {
    info "Configuring session sharing..."
    
    for node_dir in /opt/panel-node*; do
        if [[ -d "$node_dir" ]]; then
            cd "$node_dir"
            source venv/bin/activate
            
            pip install -q flask-session redis
            
            cat >> config.py << 'EOF'

# Session Configuration
SESSION_TYPE = 'redis'
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True
SESSION_KEY_PREFIX = 'panel:'
EOF
        fi
    done
    
    success "Session sharing configured"
}

# Setup health checks
setup_health_checks() {
    info "Setting up health checks..."
    
    # Create health check script
    sudo tee /usr/local/bin/panel-cluster-health.sh > /dev/null << 'EOF'
#!/bin/bash

for service in /etc/systemd/system/panel-node*.service; do
    node=$(basename "$service" .service)
    
    if systemctl is-active "$node" >/dev/null 2>&1; then
        echo "✓ $node: running"
    else
        echo "✗ $node: not running"
    fi
done
EOF
    
    sudo chmod +x /usr/local/bin/panel-cluster-health.sh
    
    success "Health checks configured"
}

# Generate load balancer config for cluster
generate_cluster_lb_config() {
    local num_nodes=$1
    local domain=$2
    
    info "Generating load balancer configuration..."
    
    SERVERS=()
    for ((i=1; i<=$num_nodes; i++)); do
        PORT=$((5000 + i))
        SERVERS+=("127.0.0.1:$PORT")
    done
    
    bash scripts/generate-lb-config.sh --nginx "$domain" "${SERVERS[@]}"
    
    success "Load balancer configuration generated"
}

# Interactive cluster setup
interactive_setup() {
    print_header
    
    read -p "Number of cluster nodes: " NUM_NODES
    read -p "Domain name: " DOMAIN
    read -p "Setup shared database? (yes/no) [yes]: " SETUP_DB
    SETUP_DB=${SETUP_DB:-yes}
    read -p "Setup shared Redis? (yes/no) [yes]: " SETUP_REDIS
    SETUP_REDIS=${SETUP_REDIS:-yes}
    
    # Setup shared services
    if [[ "$SETUP_DB" == "yes" ]]; then
        setup_shared_database
        read -p "Database host: " DB_HOST
    else
        read -p "Existing database host: " DB_HOST
    fi
    
    if [[ "$SETUP_REDIS" == "yes" ]]; then
        setup_shared_redis
        read -p "Redis host: " REDIS_HOST
    else
        read -p "Existing Redis host: " REDIS_HOST
    fi
    
    # Setup cluster nodes
    for ((i=1; i<=$NUM_NODES; i++)); do
        setup_cluster_node "$i" "$DB_HOST" "$REDIS_HOST"
    done
    
    # Configure session sharing
    configure_session_sharing
    
    # Setup health checks
    setup_health_checks
    
    # Generate load balancer config
    generate_cluster_lb_config "$NUM_NODES" "$DOMAIN"
    
    echo
    success "Cluster setup complete!"
    echo
    echo "Cluster nodes:"
    for ((i=1; i<=$NUM_NODES; i++)); do
        PORT=$((5000 + i))
        echo "  - Node $i: http://localhost:$PORT"
    done
    echo
    echo "Next steps:"
    echo "  1. Configure and install load balancer"
    echo "  2. Test cluster: /usr/local/bin/panel-cluster-health.sh"
    echo "  3. Monitor logs: journalctl -u panel-node*"
}

# Scale cluster (add/remove nodes)
scale_cluster() {
    local action=$1
    local node_id=$2
    
    case "$action" in
        add)
            read -p "Database host: " DB_HOST
            read -p "Redis host: " REDIS_HOST
            setup_cluster_node "$node_id" "$DB_HOST" "$REDIS_HOST"
            ;;
        remove)
            info "Removing node $node_id..."
            sudo systemctl stop panel-node${node_id}
            sudo systemctl disable panel-node${node_id}
            sudo rm /etc/systemd/system/panel-node${node_id}.service
            sudo systemctl daemon-reload
            success "Node $node_id removed"
            ;;
        *)
            error "Unknown action: $action"
            ;;
    esac
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup Panel in cluster mode with multiple instances

Options:
    --interactive       Interactive setup (default)
    --add-node ID       Add cluster node
    --remove-node ID    Remove cluster node
    --health            Check cluster health
    --help              Show this help

Examples:
    # Interactive setup
    $0
    
    # Add node
    $0 --add-node 4
    
    # Remove node
    $0 --remove-node 3
    
    # Check health
    $0 --health

EOF
}

main() {
    case "${1:-interactive}" in
        --interactive|interactive)
            interactive_setup
            ;;
        --add-node)
            scale_cluster add "$2"
            ;;
        --remove-node)
            scale_cluster remove "$2"
            ;;
        --health)
            /usr/local/bin/panel-cluster-health.sh
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
