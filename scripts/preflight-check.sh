#!/bin/bash

#############################################################################
# Panel Preflight Check Script
# Validates system requirements before installation
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Preflight Check${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}!${NC} $1"
    ((WARNINGS++))
}

print_section() {
    echo
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

# Check OS
check_os() {
    print_section "Operating System"
    
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        check_pass "Detected: $PRETTY_NAME"
        
        case "$ID" in
            ubuntu|debian|centos|rhel|fedora|alpine)
                check_pass "Supported OS detected"
                ;;
            *)
                check_warn "OS '$ID' may not be fully supported"
                ;;
        esac
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        check_pass "Detected: macOS"
    else
        check_fail "Unknown operating system"
    fi
}

# Check system architecture
check_architecture() {
    print_section "System Architecture"
    
    ARCH=$(uname -m)
    check_pass "Architecture: $ARCH"
    
    case "$ARCH" in
        x86_64|amd64)
            check_pass "64-bit architecture supported"
            ;;
        aarch64|arm64)
            check_pass "ARM64 architecture supported"
            ;;
        *)
            check_warn "Architecture '$ARCH' may have limited support"
            ;;
    esac
}

# Check Python version
check_python() {
    print_section "Python"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        check_pass "Python3 found: $PYTHON_VERSION"
        
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 8 ]]; then
            check_pass "Python version >= 3.8 requirement met"
        else
            check_fail "Python 3.8 or higher required (found $PYTHON_VERSION)"
        fi
    else
        check_fail "Python3 not found"
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        check_pass "pip3 found"
    else
        check_fail "pip3 not found"
    fi
    
    # Check venv
    if python3 -c "import venv" 2>/dev/null; then
        check_pass "venv module available"
    else
        check_fail "venv module not found (install python3-venv)"
    fi
}

# Check Git
check_git() {
    print_section "Git"
    
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | cut -d' ' -f3)
        check_pass "Git found: $GIT_VERSION"
    else
        check_fail "Git not found"
    fi
}

# Check available disk space
check_disk_space() {
    print_section "Disk Space"
    
    AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    
    if [[ $AVAILABLE -ge 5 ]]; then
        check_pass "Available disk space: ${AVAILABLE}GB"
    elif [[ $AVAILABLE -ge 2 ]]; then
        check_warn "Low disk space: ${AVAILABLE}GB (5GB+ recommended)"
    else
        check_fail "Insufficient disk space: ${AVAILABLE}GB (minimum 2GB required)"
    fi
}

# Check memory
check_memory() {
    print_section "Memory"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TOTAL_MEM_KB=$(sysctl -n hw.memsize)
        TOTAL_MEM_MB=$((TOTAL_MEM_KB / 1024 / 1024))
    else
        TOTAL_MEM_MB=$(free -m | awk '/^Mem:/{print $2}')
    fi
    
    if [[ $TOTAL_MEM_MB -ge 2048 ]]; then
        check_pass "Total memory: ${TOTAL_MEM_MB}MB"
    elif [[ $TOTAL_MEM_MB -ge 1024 ]]; then
        check_warn "Limited memory: ${TOTAL_MEM_MB}MB (2GB+ recommended)"
    else
        check_fail "Insufficient memory: ${TOTAL_MEM_MB}MB (minimum 1GB required)"
    fi
}

# Check network connectivity
check_network() {
    print_section "Network Connectivity"
    
    if ping -c 1 8.8.8.8 &> /dev/null; then
        check_pass "Internet connectivity available"
    else
        check_fail "No internet connectivity"
    fi
    
    if curl -s https://pypi.org &> /dev/null; then
        check_pass "Can reach PyPI"
    else
        check_warn "Cannot reach PyPI (may affect package installation)"
    fi
    
    if curl -s https://github.com &> /dev/null; then
        check_pass "Can reach GitHub"
    else
        check_warn "Cannot reach GitHub (may affect installation)"
    fi
}

# Check ports
check_ports() {
    print_section "Port Availability"
    
    check_port() {
        local port=$1
        local service=$2
        
        if command -v netstat &> /dev/null; then
            if netstat -tuln | grep -q ":${port} "; then
                check_warn "Port $port already in use (needed for $service)"
            else
                check_pass "Port $port available ($service)"
            fi
        elif command -v ss &> /dev/null; then
            if ss -tuln | grep -q ":${port} "; then
                check_warn "Port $port already in use (needed for $service)"
            else
                check_pass "Port $port available ($service)"
            fi
        else
            check_warn "Cannot check port $port (netstat/ss not available)"
        fi
    }
    
    check_port 5000 "Panel app"
    check_port 80 "HTTP (nginx)"
    check_port 443 "HTTPS (nginx)"
    check_port 6379 "Redis (if local)"
    check_port 5432 "PostgreSQL (if local)"
}

# Check optional dependencies
check_optional() {
    print_section "Optional Dependencies"
    
    # PostgreSQL
    if command -v psql &> /dev/null; then
        check_pass "PostgreSQL client available"
    else
        check_warn "PostgreSQL client not found (optional)"
    fi
    
    # Redis
    if command -v redis-cli &> /dev/null; then
        check_pass "Redis CLI available"
    else
        check_warn "Redis CLI not found (optional)"
    fi
    
    # Nginx
    if command -v nginx &> /dev/null; then
        check_pass "Nginx available"
    else
        check_warn "Nginx not found (optional, for production)"
    fi
    
    # systemd
    if command -v systemctl &> /dev/null; then
        check_pass "systemd available"
    else
        check_warn "systemd not found (service management will be limited)"
    fi
    
    # Docker (for --docker mode)
    if command -v docker &> /dev/null; then
        check_pass "Docker available"
    else
        check_warn "Docker not found (needed for --docker mode)"
    fi
}

# Check write permissions
check_permissions() {
    print_section "Permissions"
    
    TEST_DIR="${1:-/opt/panel}"
    
    if [[ -d "$TEST_DIR" ]]; then
        if [[ -w "$TEST_DIR" ]]; then
            check_pass "Write permission to $TEST_DIR"
        else
            check_warn "No write permission to $TEST_DIR (may need sudo)"
        fi
    else
        PARENT_DIR=$(dirname "$TEST_DIR")
        if [[ -w "$PARENT_DIR" ]]; then
            check_pass "Can create $TEST_DIR"
        else
            check_warn "Cannot create $TEST_DIR (may need sudo)"
        fi
    fi
}

# Summary
print_summary() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}✓ All checks passed! System is ready for installation.${NC}"
        return 0
    elif [[ $ERRORS -eq 0 ]]; then
        echo -e "${YELLOW}! $WARNINGS warning(s) found. Installation may proceed with limitations.${NC}"
        return 0
    else
        echo -e "${RED}✗ $ERRORS error(s) found. Please resolve issues before installation.${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}! $WARNINGS warning(s) also found.${NC}"
        fi
        return 1
    fi
}

# Main
main() {
    print_header
    
    check_os
    check_architecture
    check_python
    check_git
    check_disk_space
    check_memory
    check_network
    check_ports
    check_optional
    check_permissions "$@"
    
    print_summary
}

main "$@"
