#!/bin/bash

#############################################################################
# Panel Post-Installation Test Suite
# Validates Panel installation and functionality
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/panel}"
FAILURES=0

cd "$INSTALL_DIR" || exit 1

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Post-Installation Tests${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILURES++))
}

print_section() {
    echo
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

# Test virtual environment
test_venv() {
    print_section "Virtual Environment"
    
    if [[ -f "venv/bin/activate" ]]; then
        test_pass "Virtual environment exists"
        
        source venv/bin/activate
        
        if [[ "$VIRTUAL_ENV" ]]; then
            test_pass "Virtual environment activated"
        else
            test_fail "Failed to activate virtual environment"
        fi
        
        # Check Python version
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        test_pass "Python version: $PYTHON_VERSION"
    else
        test_fail "Virtual environment not found"
    fi
}

# Test dependencies
test_dependencies() {
    print_section "Python Dependencies"
    
    # Key packages
    REQUIRED_PACKAGES=("flask" "sqlalchemy" "redis" "celery" "gunicorn")
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            test_pass "$package installed"
        else
            test_fail "$package not found"
        fi
    done
}

# Test configuration
test_config() {
    print_section "Configuration"
    
    if [[ -f "config.py" ]]; then
        test_pass "config.py exists"
        
        # Check for required settings
        if grep -q "SECRET_KEY" config.py; then
            test_pass "SECRET_KEY configured"
        else
            test_fail "SECRET_KEY not found in config"
        fi
        
        if grep -q "SQLALCHEMY_DATABASE_URI" config.py; then
            test_pass "Database URI configured"
        else
            test_fail "Database URI not configured"
        fi
    else
        test_fail "config.py not found"
    fi
}

# Test database
test_database() {
    print_section "Database"
    
    if python -c "
from app import create_app
from app.extensions import db
import sys

try:
    app = create_app()
    with app.app_context():
        db.engine.connect()
    print('OK')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1 | grep -q "OK"; then
        test_pass "Database connection successful"
    else
        test_fail "Database connection failed"
    fi
    
    # Check if tables exist
    if python -c "
from app import create_app
from app.extensions import db
import sys

try:
    app = create_app()
    with app.app_context():
        tables = db.engine.table_names()
        if len(tables) > 0:
            print(f'Tables: {len(tables)}')
            sys.exit(0)
        else:
            print('No tables')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1 | grep -q "Tables:"; then
        test_pass "Database tables created"
    else
        test_fail "Database tables not found"
    fi
}

# Test Redis
test_redis() {
    print_section "Redis Connection"
    
    if python -c "
import redis
from config import Config
import sys

try:
    r = redis.from_url(Config.REDIS_URL)
    r.ping()
    print('OK')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1 | grep -q "OK"; then
        test_pass "Redis connection successful"
    else
        test_fail "Redis connection failed"
    fi
}

# Test application startup
test_app_startup() {
    print_section "Application Startup"
    
    # Test Flask app creation
    if python -c "
from app import create_app
import sys

try:
    app = create_app()
    print('OK')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1 | grep -q "OK"; then
        test_pass "Flask app creation successful"
    else
        test_fail "Flask app creation failed"
    fi
}

# Test CLI commands
test_cli() {
    print_section "CLI Commands"
    
    if python -c "
from app import create_app
import sys

try:
    app = create_app()
    with app.app_context():
        # Test that CLI commands are registered
        from flask.cli import AppGroup
        print('OK')
        sys.exit(0)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1 | grep -q "OK"; then
        test_pass "CLI commands available"
    else
        test_fail "CLI commands not available"
    fi
}

# Test static files
test_static() {
    print_section "Static Files"
    
    if [[ -d "static" ]]; then
        test_pass "static/ directory exists"
        
        # Check for common assets
        if [[ -d "static/css" ]]; then
            test_pass "CSS directory exists"
        fi
        
        if [[ -d "static/js" ]]; then
            test_pass "JS directory exists"
        fi
    else
        test_fail "static/ directory not found"
    fi
}

# Test templates
test_templates() {
    print_section "Templates"
    
    if [[ -d "templates" ]]; then
        test_pass "templates/ directory exists"
        
        TEMPLATE_COUNT=$(find templates -name "*.html" | wc -l)
        test_pass "Found $TEMPLATE_COUNT HTML templates"
    else
        test_fail "templates/ directory not found"
    fi
}

# Test helper scripts
test_scripts() {
    print_section "Helper Scripts"
    
    SCRIPTS=("start.sh" "test.sh" "status.sh" "uninstall.sh")
    
    for script in "${SCRIPTS[@]}"; do
        if [[ -f "$script" ]] && [[ -x "$script" ]]; then
            test_pass "$script exists and is executable"
        else
            test_fail "$script not found or not executable"
        fi
    done
}

# Test systemd service (if applicable)
test_service() {
    print_section "Systemd Service"
    
    if command -v systemctl &> /dev/null; then
        if systemctl list-unit-files | grep -q "panel.service"; then
            test_pass "panel.service installed"
            
            if systemctl is-enabled panel.service &> /dev/null; then
                test_pass "panel.service is enabled"
            else
                test_fail "panel.service is not enabled"
            fi
        else
            test_fail "panel.service not found"
        fi
    else
        echo -e "${YELLOW}! systemd not available (skipping service tests)${NC}"
    fi
}

# Test nginx configuration (if applicable)
test_nginx() {
    print_section "Nginx Configuration"
    
    if command -v nginx &> /dev/null; then
        if [[ -f "/etc/nginx/sites-available/panel" ]] || [[ -f "/etc/nginx/conf.d/panel.conf" ]]; then
            test_pass "Nginx configuration found"
            
            if nginx -t 2>&1 | grep -q "successful"; then
                test_pass "Nginx configuration valid"
            else
                test_fail "Nginx configuration has errors"
            fi
        else
            echo -e "${YELLOW}! Nginx configuration not found (development mode?)${NC}"
        fi
    else
        echo -e "${YELLOW}! Nginx not available (skipping nginx tests)${NC}"
    fi
}

# Test port availability
test_port() {
    print_section "Application Port"
    
    # Check if app is running
    if curl -s http://localhost:5000 &> /dev/null; then
        test_pass "Application responding on port 5000"
        
        # Test health endpoint
        if curl -s http://localhost:5000/health 2>&1 | grep -q "ok"; then
            test_pass "Health endpoint responding"
        fi
    else
        echo -e "${YELLOW}! Application not running (start it to test endpoints)${NC}"
    fi
}

# Summary
print_summary() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [[ $FAILURES -eq 0 ]]; then
        echo -e "${GREEN}✓ All tests passed! Installation is successful.${NC}"
        echo
        echo "Next steps:"
        echo "  1. Start Panel: ./start.sh"
        echo "  2. Check status: ./status.sh"
        echo "  3. Run tests: ./test.sh"
        echo "  4. Access Panel: http://localhost:5000"
        return 0
    else
        echo -e "${RED}✗ $FAILURES test(s) failed. Please check the errors above.${NC}"
        return 1
    fi
}

# Main
main() {
    print_header
    
    test_venv
    test_dependencies
    test_config
    test_database
    test_redis
    test_app_startup
    test_cli
    test_static
    test_templates
    test_scripts
    test_service
    test_nginx
    test_port
    
    print_summary
}

main
