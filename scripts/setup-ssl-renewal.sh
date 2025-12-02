#!/bin/bash

#############################################################################
# Panel SSL Auto-Renewal Setup Script
# Configure certbot automatic SSL certificate renewal
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
    echo -e "${BLUE}  SSL Auto-Renewal Setup${NC}"
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

# Install certbot
install_certbot() {
    info "Installing certbot..."
    
    if command -v certbot &> /dev/null; then
        success "certbot already installed"
        return
    fi
    
    if [[ -f /etc/debian_version ]]; then
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    elif [[ -f /etc/redhat-release ]]; then
        sudo yum install -y epel-release
        sudo yum install -y certbot python3-certbot-nginx
    else
        # Snap installation (universal)
        sudo snap install --classic certbot
        sudo ln -sf /snap/bin/certbot /usr/bin/certbot
    fi
    
    success "certbot installed"
}

# Obtain SSL certificate
obtain_certificate() {
    local domain=$1
    local email=$2
    
    info "Obtaining SSL certificate for $domain..."
    
    # Check if nginx is running
    if ! systemctl is-active nginx &> /dev/null; then
        warn "Nginx is not running, starting it..."
        sudo systemctl start nginx
    fi
    
    # Obtain certificate
    sudo certbot --nginx -d "$domain" --non-interactive --agree-tos --email "$email" --redirect
    
    if [[ $? -eq 0 ]]; then
        success "SSL certificate obtained for $domain"
    else
        error "Failed to obtain SSL certificate"
    fi
}

# Setup auto-renewal timer
setup_renewal_timer() {
    info "Setting up auto-renewal timer..."
    
    # Check if certbot timer already exists
    if systemctl list-timers | grep -q "certbot.timer"; then
        success "certbot timer already configured"
        return
    fi
    
    # Create systemd timer
    sudo tee /etc/systemd/system/certbot-renewal.timer > /dev/null << 'EOF'
[Unit]
Description=Certbot SSL Certificate Renewal Timer
Requires=certbot-renewal.service

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Create systemd service
    sudo tee /etc/systemd/system/certbot-renewal.service > /dev/null << 'EOF'
[Unit]
Description=Certbot SSL Certificate Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
EOF
    
    # Enable and start timer
    sudo systemctl daemon-reload
    sudo systemctl enable certbot-renewal.timer
    sudo systemctl start certbot-renewal.timer
    
    success "Auto-renewal timer configured"
}

# Setup renewal hooks
setup_renewal_hooks() {
    info "Setting up renewal hooks..."
    
    sudo mkdir -p /etc/letsencrypt/renewal-hooks/{pre,post,deploy}
    
    # Pre-renewal hook
    sudo tee /etc/letsencrypt/renewal-hooks/pre/stop-services.sh > /dev/null << 'EOF'
#!/bin/bash
# Stop services that might interfere with renewal
systemctl stop panel.service 2>/dev/null || true
EOF
    
    # Post-renewal hook
    sudo tee /etc/letsencrypt/renewal-hooks/post/start-services.sh > /dev/null << 'EOF'
#!/bin/bash
# Restart services after renewal
systemctl start panel.service 2>/dev/null || true
EOF
    
    # Deploy hook (runs only on successful renewal)
    sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh > /dev/null << 'EOF'
#!/bin/bash
# Reload nginx after successful renewal
systemctl reload nginx

# Send notification (optional)
if command -v mail &> /dev/null; then
    echo "SSL certificate renewed successfully on $(hostname)" | mail -s "SSL Renewal Success" admin@example.com
fi
EOF
    
    # Make hooks executable
    sudo chmod +x /etc/letsencrypt/renewal-hooks/{pre,post,deploy}/*.sh
    
    success "Renewal hooks configured"
}

# Configure nginx for SSL
configure_nginx_ssl() {
    local domain=$1
    
    info "Configuring nginx SSL settings..."
    
    # Backup existing config
    if [[ -f "/etc/nginx/sites-available/panel" ]]; then
        sudo cp /etc/nginx/sites-available/panel /etc/nginx/sites-available/panel.bak
    fi
    
    # SSL configuration snippet
    sudo tee /etc/nginx/snippets/ssl-params.conf > /dev/null << 'EOF'
# SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_ecdh_curve secp384r1;
ssl_session_timeout 10m;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
EOF
    
    success "Nginx SSL configuration updated"
}

# Test SSL configuration
test_ssl() {
    local domain=$1
    
    info "Testing SSL configuration..."
    
    # Test nginx config
    if sudo nginx -t; then
        success "Nginx configuration is valid"
    else
        error "Nginx configuration has errors"
    fi
    
    # Test certificate
    echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | grep -q "Verify return code: 0" && \
        success "SSL certificate is valid" || \
        warn "SSL certificate validation failed"
}

# Setup monitoring for expiration
setup_expiration_monitoring() {
    info "Setting up SSL expiration monitoring..."
    
    # Create monitoring script
    sudo tee /usr/local/bin/check-ssl-expiration.sh > /dev/null << 'EOF'
#!/bin/bash

DOMAINS=$(certbot certificates 2>/dev/null | grep "Domains:" | cut -d: -f2 | tr -d ' ')
THRESHOLD=30  # Days before expiration to warn

for domain in $DOMAINS; do
    EXPIRY=$(echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | \
             openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [[ -n "$EXPIRY" ]]; then
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
        
        echo "$domain: $DAYS_LEFT days until expiration"
        
        if [[ $DAYS_LEFT -lt $THRESHOLD ]]; then
            echo "WARNING: Certificate for $domain expires in $DAYS_LEFT days!"
            
            # Send alert (optional)
            if command -v mail &> /dev/null; then
                echo "SSL certificate for $domain expires in $DAYS_LEFT days" | \
                    mail -s "SSL Expiration Warning" admin@example.com
            fi
        fi
    fi
done
EOF
    
    sudo chmod +x /usr/local/bin/check-ssl-expiration.sh
    
    # Add to crontab
    (sudo crontab -l 2>/dev/null; echo "0 9 * * * /usr/local/bin/check-ssl-expiration.sh") | sudo crontab -
    
    success "SSL expiration monitoring configured"
}

# Show status
show_status() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  SSL Status${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    
    # Show certificates
    echo -e "${BLUE}Installed Certificates:${NC}"
    sudo certbot certificates
    
    echo
    echo -e "${BLUE}Renewal Timer Status:${NC}"
    systemctl status certbot-renewal.timer --no-pager || \
    systemctl status certbot.timer --no-pager || \
    echo "No renewal timer found"
    
    echo
    echo -e "${BLUE}Next Renewal Check:${NC}"
    systemctl list-timers | grep certbot || echo "No scheduled renewal"
}

# Manual renewal test
test_renewal() {
    info "Testing certificate renewal (dry-run)..."
    
    sudo certbot renew --dry-run
    
    if [[ $? -eq 0 ]]; then
        success "Renewal test successful"
    else
        error "Renewal test failed"
    fi
}

# Main
main() {
    print_header
    
    read -p "Domain name: " DOMAIN
    if [[ -z "$DOMAIN" ]]; then
        error "Domain name is required"
    fi
    
    read -p "Email address: " EMAIL
    if [[ -z "$EMAIL" ]]; then
        error "Email address is required"
    fi
    
    install_certbot
    obtain_certificate "$DOMAIN" "$EMAIL"
    setup_renewal_timer
    setup_renewal_hooks
    configure_nginx_ssl "$DOMAIN"
    setup_expiration_monitoring
    test_ssl "$DOMAIN"
    
    echo
    read -p "Test renewal now (dry-run)? (yes/no) [yes]: " TEST
    TEST=${TEST:-yes}
    
    if [[ "$TEST" == "yes" ]]; then
        test_renewal
    fi
    
    show_status
    
    echo
    success "SSL auto-renewal setup complete!"
    echo
    echo "Certificate will be automatically renewed when it has 30 days or less remaining."
    echo "Check renewal status with: sudo certbot renew --dry-run"
}

main "$@"
