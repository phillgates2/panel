#!/bin/bash

#############################################################################
# Panel Load Balancer Configuration Generator
# Generate nginx load balancer configuration for Panel
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
    echo -e "${BLUE}  Load Balancer Config Generator${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; exit 1; }

# Generate nginx upstream config
generate_upstream() {
    local servers=("$@")
    
    cat << EOF
upstream panel_backend {
    # Load balancing method
    least_conn;  # Options: round_robin (default), least_conn, ip_hash
    
    # Backend servers
EOF
    
    for server in "${servers[@]}"; do
        echo "    server $server max_fails=3 fail_timeout=30s;"
    done
    
    cat << 'EOF'
    
    # Keepalive connections
    keepalive 32;
}
EOF
}

# Generate nginx server config
generate_server_config() {
    local domain=$1
    
    cat << 'EOF'
# Rate limiting
limit_req_zone $binary_remote_addr zone=panel_limit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=panel_conn:10m;

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name DOMAIN;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name DOMAIN;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/panel-lb-access.log combined;
    error_log /var/log/nginx/panel-lb-error.log warn;
    
    # Rate limiting
    limit_req zone=panel_limit burst=20 nodelay;
    limit_conn panel_conn 10;
    
    # Client settings
    client_max_body_size 100M;
    client_body_timeout 60s;
    
    # Proxy settings
    location / {
        proxy_pass http://panel_backend;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # HTTP version
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_next_upstream_tries 3;
        proxy_next_upstream_timeout 10s;
    }
    
    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://panel_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
    
    # Static files caching
    location /static/ {
        proxy_pass http://panel_backend;
        proxy_cache_valid 200 1d;
        proxy_cache_bypass $http_cache_control;
        add_header X-Cache-Status $upstream_cache_status;
        expires 1d;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://panel_backend;
        access_log off;
    }
    
    # Status page (restrict access)
    location /nginx_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}
EOF
    sed "s/DOMAIN/$domain/g"
}

# Generate HAProxy config
generate_haproxy_config() {
    local servers=("$@")
    
    cat << 'EOF'
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon
    
    # SSL
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

defaults
    log global
    mode http
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor except 127.0.0.0/8
    option redispatch
    retries 3
    timeout connect 5000
    timeout client 50000
    timeout server 50000
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

frontend panel_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/panel.pem
    
    # HTTP to HTTPS redirect
    redirect scheme https code 301 if !{ ssl_fc }
    
    # Security headers
    http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains"
    http-response set-header X-Frame-Options "DENY"
    http-response set-header X-Content-Type-Options "nosniff"
    
    default_backend panel_backend

backend panel_backend
    balance leastconn
    option httpchk GET /health
    http-check expect status 200
    
EOF
    
    local i=1
    for server in "${servers[@]}"; do
        echo "    server app$i $server check inter 5000 rise 2 fall 3"
        ((i++))
    done
    
    cat << 'EOF'

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats auth admin:CHANGE_PASSWORD
EOF
}

# Interactive configuration
interactive_config() {
    print_header
    
    read -p "Load balancer type (nginx/haproxy) [nginx]: " LB_TYPE
    LB_TYPE=${LB_TYPE:-nginx}
    
    read -p "Domain name: " DOMAIN
    
    read -p "Number of backend servers: " NUM_SERVERS
    
    SERVERS=()
    for ((i=1; i<=$NUM_SERVERS; i++)); do
        read -p "Backend server $i (host:port): " SERVER
        SERVERS+=("$SERVER")
    done
    
    OUTPUT_FILE="/tmp/panel-lb-$LB_TYPE.conf"
    
    case "$LB_TYPE" in
        nginx)
            {
                generate_upstream "${SERVERS[@]}"
                echo
                generate_server_config "$DOMAIN"
            } > "$OUTPUT_FILE"
            ;;
        haproxy)
            generate_haproxy_config "${SERVERS[@]}" > "$OUTPUT_FILE"
            ;;
        *)
            error "Unknown load balancer type: $LB_TYPE"
            ;;
    esac
    
    success "Configuration generated: $OUTPUT_FILE"
    
    echo
    info "To apply configuration:"
    case "$LB_TYPE" in
        nginx)
            echo "  sudo cp $OUTPUT_FILE /etc/nginx/sites-available/panel-lb"
            echo "  sudo ln -s /etc/nginx/sites-available/panel-lb /etc/nginx/sites-enabled/"
            echo "  sudo nginx -t"
            echo "  sudo systemctl reload nginx"
            ;;
        haproxy)
            echo "  sudo cp $OUTPUT_FILE /etc/haproxy/haproxy.cfg"
            echo "  sudo haproxy -c -f /etc/haproxy/haproxy.cfg"
            echo "  sudo systemctl reload haproxy"
            ;;
    esac
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate load balancer configuration for Panel

Options:
    --interactive           Interactive setup (default)
    --nginx DOMAIN SERVERS  Generate nginx config
    --haproxy SERVERS       Generate HAProxy config
    --help                  Show this help

Examples:
    # Interactive
    $0
    
    # Nginx with servers
    $0 --nginx panel.example.com 10.0.1.20:5000 10.0.1.21:5000
    
    # HAProxy
    $0 --haproxy 10.0.1.20:5000 10.0.1.21:5000

EOF
}

main() {
    case "${1:-interactive}" in
        --interactive|interactive)
            interactive_config
            ;;
        --nginx)
            DOMAIN=$2
            shift 2
            {
                generate_upstream "$@"
                echo
                generate_server_config "$DOMAIN"
            } > "/tmp/panel-lb-nginx.conf"
            success "Config generated: /tmp/panel-lb-nginx.conf"
            ;;
        --haproxy)
            shift
            generate_haproxy_config "$@" > "/tmp/panel-lb-haproxy.conf"
            success "Config generated: /tmp/panel-lb-haproxy.conf"
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
