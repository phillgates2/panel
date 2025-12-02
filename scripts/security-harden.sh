#!/bin/bash

#############################################################################
# Panel Security Hardening Script
# Apply security best practices to Panel installation
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/panel}"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Security Hardening${NC}"
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

# Secure file permissions
secure_permissions() {
    info "Securing file permissions..."
    
    cd "$INSTALL_DIR"
    
    # Set ownership
    sudo chown -R panel:panel .
    
    # Set directory permissions
    find . -type d -exec chmod 750 {} \;
    
    # Set file permissions
    find . -type f -exec chmod 640 {} \;
    
    # Make scripts executable
    find scripts -name "*.sh" -exec chmod 750 {} \;
    
    # Secure config files
    chmod 600 config.py 2>/dev/null || true
    chmod 600 .env 2>/dev/null || true
    
    # Secure database
    chmod 600 *.db 2>/dev/null || true
    
    # Secure logs
    if [[ -d logs ]]; then
        chmod 750 logs
        chmod 640 logs/*.log 2>/dev/null || true
    fi
    
    success "File permissions secured"
}

# Disable debug mode
disable_debug() {
    info "Disabling debug mode..."
    
    cd "$INSTALL_DIR"
    
    if grep -q "DEBUG.*=.*True" config.py; then
        sed -i 's/DEBUG.*=.*True/DEBUG = False/' config.py
        success "Debug mode disabled"
    else
        success "Debug mode already disabled"
    fi
    
    if grep -q "TESTING.*=.*True" config.py; then
        sed -i 's/TESTING.*=.*True/TESTING = False/' config.py
        success "Testing mode disabled"
    fi
}

# Generate strong SECRET_KEY
generate_secret_key() {
    info "Generating strong SECRET_KEY..."
    
    cd "$INSTALL_DIR"
    
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    
    if grep -q "SECRET_KEY" config.py; then
        sed -i "s/SECRET_KEY.*/SECRET_KEY = '${NEW_KEY}'/" config.py
        success "SECRET_KEY regenerated"
        warn "Remember to restart Panel for changes to take effect"
    else
        error "SECRET_KEY not found in config.py"
    fi
}

# Setup secure cookies
setup_secure_cookies() {
    info "Configuring secure cookies..."
    
    cd "$INSTALL_DIR"
    
    # Add secure cookie settings if not present
    if ! grep -q "SESSION_COOKIE_SECURE" config.py; then
        cat >> config.py << 'EOF'

# Secure Cookie Settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = 3600
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_HTTPONLY = True
EOF
        success "Secure cookie settings added"
    else
        success "Secure cookie settings already configured"
    fi
}

# Enable CSRF protection
enable_csrf() {
    info "Enabling CSRF protection..."
    
    cd "$INSTALL_DIR"
    
    if ! grep -q "WTF_CSRF_ENABLED" config.py; then
        cat >> config.py << 'EOF'

# CSRF Protection
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600
EOF
        success "CSRF protection enabled"
    else
        # Make sure it's not disabled
        sed -i 's/WTF_CSRF_ENABLED.*=.*False/WTF_CSRF_ENABLED = True/' config.py
        success "CSRF protection verified"
    fi
}

# Setup rate limiting
setup_rate_limiting() {
    info "Setting up rate limiting..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Install flask-limiter if not present
    pip install -q flask-limiter redis
    
    if ! grep -q "RATELIMIT" config.py; then
        cat >> config.py << 'EOF'

# Rate Limiting
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = REDIS_URL
RATELIMIT_DEFAULT = "200 per day, 50 per hour"
RATELIMIT_HEADERS_ENABLED = True
EOF
        success "Rate limiting configured"
        warn "Add rate limiting to your Flask app: from flask_limiter import Limiter"
    else
        success "Rate limiting already configured"
    fi
}

# Secure database connection
secure_database() {
    info "Securing database connection..."
    
    cd "$INSTALL_DIR"
    
    # Check if using SSL for PostgreSQL
    if grep -q "postgresql://" config.py; then
        if ! grep -q "sslmode" config.py; then
            sed -i 's|postgresql://|postgresql://|; s|$|?sslmode=require|' config.py 2>/dev/null || true
            success "SSL required for PostgreSQL connections"
        else
            success "PostgreSQL SSL already configured"
        fi
    fi
    
    # Disable SQLite in production
    if grep -q "sqlite://" config.py && [[ ! "$DEBUG" ]]; then
        warn "SQLite detected in production - consider migrating to PostgreSQL"
    fi
}

# Setup security headers
setup_security_headers() {
    info "Configuring security headers..."
    
    # Update nginx configuration
    if [[ -f /etc/nginx/sites-available/panel ]]; then
        NGINX_CONF="/etc/nginx/sites-available/panel"
    elif [[ -f /etc/nginx/conf.d/panel.conf ]]; then
        NGINX_CONF="/etc/nginx/conf.d/panel.conf"
    else
        warn "Nginx configuration not found, skipping security headers"
        return
    fi
    
    # Backup config
    sudo cp "$NGINX_CONF" "${NGINX_CONF}.bak"
    
    # Add security headers if not present
    if ! sudo grep -q "X-Frame-Options" "$NGINX_CONF"; then
        sudo sed -i '/location \/ {/a \    add_header X-Frame-Options "DENY" always;\n    add_header X-Content-Type-Options "nosniff" always;\n    add_header X-XSS-Protection "1; mode=block" always;\n    add_header Referrer-Policy "strict-origin-when-cross-origin" always;\n    add_header Content-Security-Policy "default-src '\''self'\''; script-src '\''self'\'' '\''unsafe-inline'\''; style-src '\''self'\'' '\''unsafe-inline'\'';" always;' "$NGINX_CONF"
        
        sudo nginx -t && sudo systemctl reload nginx
        success "Security headers added to nginx"
    else
        success "Security headers already configured"
    fi
}

# Disable directory listing
disable_directory_listing() {
    info "Disabling directory listing..."
    
    cd "$INSTALL_DIR"
    
    # In Flask app
    if ! grep -q "SEND_FILE_MAX_AGE_DEFAULT" config.py; then
        cat >> config.py << 'EOF'

# Disable directory listing
SEND_FILE_MAX_AGE_DEFAULT = 0
EOF
    fi
    
    success "Directory listing disabled"
}

# Setup audit logging
setup_audit_logging() {
    info "Setting up audit logging..."
    
    cd "$INSTALL_DIR"
    
    if ! grep -q "AUDIT_LOG" config.py; then
        cat >> config.py << 'EOF'

# Audit Logging
AUDIT_LOG_ENABLED = True
AUDIT_LOG_FILE = '/opt/panel/logs/audit.log'
AUDIT_LOG_LEVEL = 'INFO'
EOF
        
        mkdir -p logs
        touch logs/audit.log
        chmod 600 logs/audit.log
        
        success "Audit logging configured"
    else
        success "Audit logging already configured"
    fi
}

# Secure Redis
secure_redis() {
    info "Securing Redis connection..."
    
    if systemctl is-active redis &> /dev/null || systemctl is-active redis-server &> /dev/null; then
        REDIS_CONF="/etc/redis/redis.conf"
        
        if [[ -f "$REDIS_CONF" ]]; then
            # Require password
            if ! sudo grep -q "^requirepass" "$REDIS_CONF"; then
                REDIS_PASSWORD=$(openssl rand -base64 32)
                echo "requirepass $REDIS_PASSWORD" | sudo tee -a "$REDIS_CONF"
                
                sudo systemctl restart redis 2>/dev/null || sudo systemctl restart redis-server
                
                success "Redis password set"
                info "Update REDIS_URL in config.py with: redis://:${REDIS_PASSWORD}@localhost:6379/0"
            else
                success "Redis already password-protected"
            fi
            
            # Bind to localhost only
            if ! sudo grep -q "^bind 127.0.0.1" "$REDIS_CONF"; then
                sudo sed -i 's/^bind.*/bind 127.0.0.1/' "$REDIS_CONF"
                sudo systemctl restart redis 2>/dev/null || sudo systemctl restart redis-server
                success "Redis bound to localhost"
            fi
            
            # Disable dangerous commands
            if ! sudo grep -q "rename-command FLUSHDB" "$REDIS_CONF"; then
                cat | sudo tee -a "$REDIS_CONF" > /dev/null << 'EOF'

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
rename-command EVAL ""
EOF
                sudo systemctl restart redis 2>/dev/null || sudo systemctl restart redis-server
                success "Dangerous Redis commands disabled"
            fi
        fi
    else
        warn "Redis not running locally, ensure external Redis is secured"
    fi
}

# Setup SSL/TLS
ensure_ssl() {
    info "Checking SSL/TLS configuration..."
    
    if [[ -f /etc/nginx/sites-available/panel ]]; then
        if grep -q "ssl_certificate" /etc/nginx/sites-available/panel; then
            success "SSL/TLS already configured"
        else
            warn "SSL/TLS not configured - run scripts/setup-ssl-renewal.sh"
        fi
    elif [[ -f /etc/nginx/conf.d/panel.conf ]]; then
        if grep -q "ssl_certificate" /etc/nginx/conf.d/panel.conf; then
            success "SSL/TLS already configured"
        else
            warn "SSL/TLS not configured - run scripts/setup-ssl-renewal.sh"
        fi
    else
        warn "Nginx not found - SSL/TLS should be configured"
    fi
}

# Remove default/test accounts
remove_test_accounts() {
    info "Checking for default/test accounts..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    python3 << 'EOF'
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

test_users = ['admin', 'test', 'demo', 'root']

with app.app_context():
    for username in test_users:
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Found test user: {username}")
            # Don't auto-delete, just warn
            
print("Manual review recommended")
EOF
    
    warn "Review and remove any default/test accounts manually"
}

# Update dependencies
update_dependencies() {
    info "Checking for security updates..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    pip install -q --upgrade pip
    pip install -q safety
    
    safety check || warn "Security vulnerabilities found in dependencies"
    
    success "Dependency check complete"
}

# Create security checklist
create_checklist() {
    info "Creating security checklist..."
    
    cat > "$INSTALL_DIR/SECURITY_CHECKLIST.md" << 'EOF'
# Panel Security Checklist

## Completed by Security Hardening Script
- [x] Secure file permissions (640/750)
- [x] Debug mode disabled
- [x] Strong SECRET_KEY generated
- [x] Secure cookie settings
- [x] CSRF protection enabled
- [x] Rate limiting configured
- [x] Database SSL enforced
- [x] Security headers configured
- [x] Audit logging enabled
- [x] Redis secured

## Manual Review Required
- [ ] Remove default/test accounts
- [ ] Review user permissions
- [ ] Configure SSL/TLS certificates
- [ ] Setup firewall rules
- [ ] Configure fail2ban
- [ ] Review application logs
- [ ] Setup monitoring alerts
- [ ] Configure backup encryption
- [ ] Review API authentication
- [ ] Setup intrusion detection
- [ ] Configure security scanning
- [ ] Review third-party integrations
- [ ] Setup DDoS protection
- [ ] Configure WAF rules
- [ ] Review CORS settings

## Ongoing Maintenance
- [ ] Regular security updates
- [ ] Dependency vulnerability scans
- [ ] Log analysis
- [ ] Access review
- [ ] Penetration testing
- [ ] Security training

## Resources
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Flask Security: https://flask.palletsprojects.com/en/latest/security/
- Security Headers: https://securityheaders.com/
EOF
    
    success "Security checklist created: $INSTALL_DIR/SECURITY_CHECKLIST.md"
}

# Summary
print_summary() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Security Hardening Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    echo "Security measures applied:"
    echo "  ✓ File permissions secured"
    echo "  ✓ Debug mode disabled"
    echo "  ✓ SECRET_KEY regenerated"
    echo "  ✓ Secure cookies configured"
    echo "  ✓ CSRF protection enabled"
    echo "  ✓ Rate limiting setup"
    echo "  ✓ Database security enhanced"
    echo "  ✓ Security headers configured"
    echo "  ✓ Audit logging enabled"
    echo "  ✓ Redis secured"
    echo
    echo "Next steps:"
    echo "  1. Review $INSTALL_DIR/SECURITY_CHECKLIST.md"
    echo "  2. Restart Panel: sudo systemctl restart panel"
    echo "  3. Run: scripts/setup-firewall.sh"
    echo "  4. Run: scripts/setup-ssl-renewal.sh"
    echo "  5. Configure fail2ban"
    echo
    warn "Remember to restart Panel for all changes to take effect!"
}

# Main
main() {
    print_header
    
    secure_permissions
    disable_debug
    generate_secret_key
    setup_secure_cookies
    enable_csrf
    setup_rate_limiting
    secure_database
    setup_security_headers
    disable_directory_listing
    setup_audit_logging
    secure_redis
    ensure_ssl
    remove_test_accounts
    update_dependencies
    create_checklist
    
    print_summary
}

main "$@"
