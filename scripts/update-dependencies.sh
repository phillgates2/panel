#!/bin/bash
# Dependency Update Script
# Handles automated dependency updates and security patches

set -e

# Configuration
REQUIREMENTS_FILE="requirements/requirements-dev.txt"
PIP_COMPILE="${PIP_COMPILE:-pip-tools}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for outdated packages
check_outdated() {
    log_info "Checking for outdated packages..."

    if command -v pip-outdated >/dev/null 2>&1; then
        pip-outdated --format=table
    else
        log_warn "pip-outdated not installed. Install with: pip install pip-outdated"
        pip list --outdated --format=table
    fi
}

# Update pip-tools if available
update_pip_tools() {
    if command -v pip-compile >/dev/null 2>&1; then
        log_info "Updating pip-tools..."
        pip install --upgrade pip-tools
    fi
}

# Update requirements files
update_requirements() {
    log_info "Updating requirements files..."

    if command -v pip-compile >/dev/null 2>&1; then
        # Use pip-tools for reproducible builds
        pip-compile requirements/requirements.in --output-file requirements/requirements.txt
        pip-compile requirements/requirements-dev.in --output-file requirements/requirements-dev.txt
        log_success "Requirements files updated with pip-tools"
    else
        log_warn "pip-tools not available. Using pip freeze (less reliable)"
        pip freeze > requirements.txt.backup
        log_info "Backup created: requirements.txt.backup"
    fi
}

# Security audit
security_audit() {
    log_info "Running security audit..."

    if command -v safety >/dev/null 2>&1; then
        safety check --full-report --output=text
    else
        log_warn "safety not installed. Install with: pip install safety"
    fi

    if command -v bandit >/dev/null 2>&1; then
        bandit -r src/ -f text
    else
        log_warn "bandit not installed. Install with: pip install bandit"
    fi
}

# Update specific package
update_package() {
    local package=$1
    local version=${2:-latest}

    if [ -z "$package" ]; then
        log_error "Package name required"
        echo "Usage: $0 update <package> [version]"
        exit 1
    fi

    log_info "Updating $package to $version..."

    if [ "$version" = "latest" ]; then
        pip install --upgrade "$package"
    else
        pip install "$package==$version"
    fi

    log_success "$package updated"
}

# Check for breaking changes
check_breaking_changes() {
    log_info "Checking for potential breaking changes..."

    # Check for major version updates
    pip list --outdated --format=json | jq -r '.[] | select(.latest_version | split(".")[0] != .version | split(".")[0]) | "\(.name): \(.version) -> \(.latest_version)"'

    # Check for deprecated features
    python -c "
import warnings
warnings.simplefilter('always')
import flask, sqlalchemy, werkzeug
print('Deprecation warnings checked')
"
}

# Generate update report
generate_report() {
    log_info "Generating dependency update report..."

    local report_file="dependency-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# Dependency Update Report
Generated: $(date)

## Outdated Packages
$(pip list --outdated --format=table 2>/dev/null || echo "pip list --outdated failed")

## Security Issues
$(safety check --full-report --output=text 2>/dev/null || echo "Safety check not available")

## Recommendations
1. Review major version updates carefully
2. Test all changes in staging environment
3. Update dependencies gradually
4. Monitor for deprecation warnings

## Next Steps
- Run tests after updates
- Check for breaking changes
- Update documentation if needed
- Deploy to staging for validation
EOF

    log_success "Report generated: $report_file"
}

# Interactive update mode
interactive_update() {
    log_info "Starting interactive dependency update..."

    echo "Current outdated packages:"
    pip list --outdated --format=columns

    echo
    read -p "Do you want to update all packages? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install --upgrade pip
        pip install --upgrade -r requirements/requirements-dev.txt
        log_success "All packages updated"
    else
        echo "Interactive update cancelled"
    fi
}

# Main function
main() {
    case "$1" in
        "check")
            check_outdated
            ;;
        "update")
            update_package "$2" "$3"
            ;;
        "security")
            security_audit
            ;;
        "report")
            generate_report
            ;;
        "breaking")
            check_breaking_changes
            ;;
        "interactive")
            interactive_update
            ;;
        "all")
            check_outdated
            update_pip_tools
            update_requirements
            security_audit
            check_breaking_changes
            generate_report
            ;;
        *)
            echo "Usage: $0 {check|update|security|report|breaking|interactive|all}"
            echo ""
            echo "Commands:"
            echo "  check       - Check for outdated packages"
            echo "  update      - Update specific package"
            echo "  security    - Run security audit"
            echo "  report      - Generate update report"
            echo "  breaking    - Check for breaking changes"
            echo "  interactive - Interactive update mode"
            echo "  all         - Run all update tasks"
            echo ""
            echo "Examples:"
            echo "  $0 check"
            echo "  $0 update requests 2.28.0"
            echo "  $0 security"
            exit 1
            ;;
    esac
}

main "$@"