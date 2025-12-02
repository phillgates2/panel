#!/bin/bash

#############################################################################
# Panel Configuration Validator
# Validates config.py against schema and best practices
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONFIG_FILE="${1:-config.py}"
ERRORS=0
WARNINGS=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Configuration Validator${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Config file: $CONFIG_FILE"
    echo
}

validate_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

validate_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

validate_warn() {
    echo -e "${YELLOW}!${NC} $1"
    ((WARNINGS++))
}

print_section() {
    echo
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

# Check if file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "${RED}Error: Configuration file '$CONFIG_FILE' not found${NC}"
    exit 1
fi

# Validate Python syntax
validate_syntax() {
    print_section "Python Syntax"
    
    if python3 -m py_compile "$CONFIG_FILE" 2>/dev/null; then
        validate_pass "Valid Python syntax"
    else
        validate_fail "Invalid Python syntax"
    fi
}

# Check required settings
validate_required() {
    print_section "Required Settings"
    
    REQUIRED=(
        "SECRET_KEY"
        "SQLALCHEMY_DATABASE_URI"
        "REDIS_URL"
    )
    
    for setting in "${REQUIRED[@]}"; do
        if grep -q "^[[:space:]]*${setting}[[:space:]]*=" "$CONFIG_FILE"; then
            validate_pass "$setting is set"
        else
            validate_fail "$setting is missing"
        fi
    done
}

# Validate SECRET_KEY
validate_secret_key() {
    print_section "SECRET_KEY Security"
    
    if grep -q "^[[:space:]]*SECRET_KEY[[:space:]]*=" "$CONFIG_FILE"; then
        # Check if using default/weak key
        if grep "SECRET_KEY" "$CONFIG_FILE" | grep -qE "(changeme|secret|password|12345|default)"; then
            validate_fail "SECRET_KEY appears to be a default/weak value"
        else
            validate_pass "SECRET_KEY is set"
        fi
        
        # Check key length
        KEY=$(python3 -c "exec(open('$CONFIG_FILE').read()); print(len(SECRET_KEY) if 'SECRET_KEY' in dir() else 0)" 2>/dev/null || echo 0)
        if [[ $KEY -ge 32 ]]; then
            validate_pass "SECRET_KEY length adequate (${KEY} chars)"
        else
            validate_warn "SECRET_KEY should be at least 32 characters (found ${KEY})"
        fi
    fi
}

# Validate database configuration
validate_database() {
    print_section "Database Configuration"
    
    if grep -q "SQLALCHEMY_DATABASE_URI" "$CONFIG_FILE"; then
        DB_URI=$(python3 -c "exec(open('$CONFIG_FILE').read()); print(SQLALCHEMY_DATABASE_URI if 'SQLALCHEMY_DATABASE_URI' in dir() else '')" 2>/dev/null || echo "")
        
        if [[ "$DB_URI" =~ ^sqlite:/// ]]; then
            validate_pass "Using SQLite database"
            validate_warn "SQLite not recommended for production"
        elif [[ "$DB_URI" =~ ^postgresql:// ]]; then
            validate_pass "Using PostgreSQL database"
        elif [[ "$DB_URI" =~ ^mysql:// ]]; then
            validate_pass "Using MySQL database"
        else
            validate_warn "Unknown database type"
        fi
        
        # Check for database password in config
        if [[ "$DB_URI" =~ :.*@.* ]]; then
            validate_warn "Database password in config file (consider using environment variables)"
        fi
    fi
    
    # Check SQLALCHEMY settings
    if grep -q "SQLALCHEMY_TRACK_MODIFICATIONS.*True" "$CONFIG_FILE"; then
        validate_warn "SQLALCHEMY_TRACK_MODIFICATIONS=True (should be False)"
    fi
}

# Validate Redis configuration
validate_redis() {
    print_section "Redis Configuration"
    
    if grep -q "REDIS_URL" "$CONFIG_FILE"; then
        REDIS_URL=$(python3 -c "exec(open('$CONFIG_FILE').read()); print(REDIS_URL if 'REDIS_URL' in dir() else '')" 2>/dev/null || echo "")
        
        if [[ "$REDIS_URL" =~ ^redis:// ]]; then
            validate_pass "Redis URL configured"
            
            # Check for password
            if [[ "$REDIS_URL" =~ :.*@.* ]]; then
                validate_warn "Redis password in config file (consider using environment variables)"
            else
                validate_warn "Redis has no password (security risk)"
            fi
        else
            validate_fail "Invalid Redis URL format"
        fi
    fi
}

# Validate debug settings
validate_debug() {
    print_section "Debug & Security Settings"
    
    if grep -q "^[[:space:]]*DEBUG[[:space:]]*=[[:space:]]*True" "$CONFIG_FILE"; then
        validate_fail "DEBUG=True (must be False in production)"
    else
        validate_pass "DEBUG is False or not set"
    fi
    
    if grep -q "^[[:space:]]*TESTING[[:space:]]*=[[:space:]]*True" "$CONFIG_FILE"; then
        validate_warn "TESTING=True (should be False in production)"
    fi
}

# Validate security headers
validate_security() {
    print_section "Security Headers"
    
    SECURITY_SETTINGS=(
        "SESSION_COOKIE_SECURE"
        "SESSION_COOKIE_HTTPONLY"
        "SESSION_COOKIE_SAMESITE"
        "PERMANENT_SESSION_LIFETIME"
    )
    
    for setting in "${SECURITY_SETTINGS[@]}"; do
        if grep -q "$setting" "$CONFIG_FILE"; then
            validate_pass "$setting configured"
        else
            validate_warn "$setting not configured"
        fi
    done
    
    # Check CSRF protection
    if grep -q "WTF_CSRF_ENABLED.*False" "$CONFIG_FILE"; then
        validate_fail "CSRF protection disabled"
    fi
}

# Validate email configuration
validate_email() {
    print_section "Email Configuration"
    
    EMAIL_SETTINGS=(
        "MAIL_SERVER"
        "MAIL_PORT"
        "MAIL_USERNAME"
        "MAIL_PASSWORD"
    )
    
    EMAIL_FOUND=0
    for setting in "${EMAIL_SETTINGS[@]}"; do
        if grep -q "$setting" "$CONFIG_FILE"; then
            ((EMAIL_FOUND++))
        fi
    done
    
    if [[ $EMAIL_FOUND -eq ${#EMAIL_SETTINGS[@]} ]]; then
        validate_pass "Email configuration complete"
    elif [[ $EMAIL_FOUND -gt 0 ]]; then
        validate_warn "Email configuration incomplete ($EMAIL_FOUND/${#EMAIL_SETTINGS[@]} settings)"
    else
        echo -e "${YELLOW}! Email not configured (optional)${NC}"
    fi
}

# Validate logging
validate_logging() {
    print_section "Logging Configuration"
    
    if grep -q "LOG_LEVEL" "$CONFIG_FILE"; then
        LOG_LEVEL=$(python3 -c "exec(open('$CONFIG_FILE').read()); print(LOG_LEVEL if 'LOG_LEVEL' in dir() else '')" 2>/dev/null || echo "")
        
        case "$LOG_LEVEL" in
            DEBUG)
                validate_warn "LOG_LEVEL=DEBUG (verbose, may impact performance)"
                ;;
            INFO|WARNING|ERROR|CRITICAL)
                validate_pass "LOG_LEVEL=$LOG_LEVEL"
                ;;
            *)
                validate_warn "Unknown LOG_LEVEL: $LOG_LEVEL"
                ;;
        esac
    else
        validate_warn "LOG_LEVEL not configured"
    fi
    
    if grep -q "LOG_FILE" "$CONFIG_FILE"; then
        validate_pass "LOG_FILE configured"
    else
        validate_warn "LOG_FILE not configured"
    fi
}

# Validate performance settings
validate_performance() {
    print_section "Performance Settings"
    
    if grep -q "SQLALCHEMY_POOL_SIZE" "$CONFIG_FILE"; then
        validate_pass "Database pool size configured"
    else
        validate_warn "SQLALCHEMY_POOL_SIZE not set (using defaults)"
    fi
    
    if grep -q "REDIS_CACHE_TTL" "$CONFIG_FILE"; then
        validate_pass "Cache TTL configured"
    fi
    
    if grep -q "CELERY_" "$CONFIG_FILE"; then
        validate_pass "Celery configuration found"
    else
        echo -e "${YELLOW}! Celery not configured (optional)${NC}"
    fi
}

# Validate environment-specific settings
validate_environment() {
    print_section "Environment Configuration"
    
    if grep -q "ENV" "$CONFIG_FILE"; then
        ENV=$(python3 -c "exec(open('$CONFIG_FILE').read()); print(ENV if 'ENV' in dir() else '')" 2>/dev/null || echo "")
        
        case "$ENV" in
            production)
                validate_pass "ENV=production"
                ;;
            development)
                validate_warn "ENV=development (should be 'production' in production)"
                ;;
            testing)
                validate_warn "ENV=testing (should be 'production' in production)"
                ;;
            *)
                validate_warn "Unknown ENV: $ENV"
                ;;
        esac
    else
        validate_warn "ENV not set"
    fi
}

# Check for hardcoded credentials
validate_credentials() {
    print_section "Hardcoded Credentials Check"
    
    CREDENTIAL_PATTERNS=(
        "password.*=.*['\"].*['\"]"
        "api_key.*=.*['\"].*['\"]"
        "token.*=.*['\"].*['\"]"
        "secret.*=.*['\"].*['\"]"
    )
    
    for pattern in "${CREDENTIAL_PATTERNS[@]}"; do
        if grep -iE "$pattern" "$CONFIG_FILE" | grep -v "os.environ" | grep -q .; then
            validate_warn "Potential hardcoded credentials found (pattern: $pattern)"
        fi
    done
    
    # Check for environment variable usage
    if grep -q "os.environ\|os.getenv" "$CONFIG_FILE"; then
        validate_pass "Using environment variables for configuration"
    else
        validate_warn "Not using environment variables (consider for sensitive data)"
    fi
}

# Summary
print_summary() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}✓ Configuration is valid and follows best practices${NC}"
        return 0
    elif [[ $ERRORS -eq 0 ]]; then
        echo -e "${YELLOW}! Configuration is valid but has $WARNINGS warning(s)${NC}"
        return 0
    else
        echo -e "${RED}✗ Configuration has $ERRORS error(s)${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}! Also has $WARNINGS warning(s)${NC}"
        fi
        return 1
    fi
}

# Main
main() {
    print_header
    
    validate_syntax
    validate_required
    validate_secret_key
    validate_database
    validate_redis
    validate_debug
    validate_security
    validate_email
    validate_logging
    validate_performance
    validate_environment
    validate_credentials
    
    print_summary
}

main
