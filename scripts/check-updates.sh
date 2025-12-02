#!/bin/bash

#############################################################################
# Panel Update Checker
# Check for new Panel releases on GitHub
#############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO="phillgates2/panel"
INSTALL_DIR="${1:-/opt/panel}"
CURRENT_VERSION_FILE="$INSTALL_DIR/VERSION"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Panel Update Checker${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
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

error() {
    echo -e "${RED}✗ $1${NC}"
}

# Get current version
get_current_version() {
    if [[ -f "$CURRENT_VERSION_FILE" ]]; then
        cat "$CURRENT_VERSION_FILE"
    else
        # Try to get from git
        cd "$INSTALL_DIR"
        git describe --tags 2>/dev/null || echo "unknown"
    fi
}

# Get latest version from GitHub
get_latest_version() {
    curl -s "https://api.github.com/repos/$REPO/releases/latest" | \
        grep '"tag_name":' | \
        sed -E 's/.*"([^"]+)".*/\1/'
}

# Get all releases
get_all_releases() {
    curl -s "https://api.github.com/repos/$REPO/releases" | \
        grep -E '"tag_name"|"name"|"published_at"' | \
        sed -E 's/.*"([^"]+)".*/\1/' | \
        paste - - - | \
        head -n 10
}

# Compare versions
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

# Check for updates
check_updates() {
    CURRENT=$(get_current_version)
    LATEST=$(get_latest_version)
    
    if [[ -z "$LATEST" ]]; then
        error "Failed to fetch latest version from GitHub"
        return 1
    fi
    
    echo "Current version: $CURRENT"
    echo "Latest version: $LATEST"
    echo
    
    if [[ "$CURRENT" == "$LATEST" ]]; then
        success "You are running the latest version"
        return 0
    elif version_gt "$LATEST" "$CURRENT"; then
        warn "A new version is available: $LATEST"
        return 2
    else
        info "You are running a development version: $CURRENT"
        return 0
    fi
}

# Show release notes
show_release_notes() {
    local version=$1
    
    echo -e "${BLUE}Release Notes for $version:${NC}"
    echo "----------------------------------------"
    
    curl -s "https://api.github.com/repos/$REPO/releases/tags/$version" | \
        grep -A 100 '"body":' | \
        sed '1d' | \
        sed -E 's/^[[:space:]]+"//; s/"[[:space:]]*$//' | \
        sed '/^--$/,$d'
}

# Show changelog
show_changelog() {
    echo -e "${BLUE}Recent Releases:${NC}"
    echo "----------------------------------------"
    
    get_all_releases | while IFS=$'\t' read -r tag name date; do
        echo -e "${GREEN}$tag${NC} - $name"
        echo "   Released: $(date -d "$date" '+%Y-%m-%d %H:%M' 2>/dev/null || echo "$date")"
    done
}

# Perform update
perform_update() {
    local version=$1
    
    warn "This will update Panel to version $version"
    read -p "Continue? (yes/no): " CONFIRM
    
    if [[ "$CONFIRM" != "yes" ]]; then
        info "Update cancelled"
        return 0
    fi
    
    info "Creating backup..."
    bash "$INSTALL_DIR/scripts/backup.sh" || warn "Backup failed"
    
    info "Updating Panel..."
    
    cd "$INSTALL_DIR"
    
    # Stop service
    if systemctl is-active panel.service &>/dev/null; then
        sudo systemctl stop panel.service
    fi
    
    # Fetch updates
    git fetch origin
    
    if [[ "$version" == "latest" ]]; then
        git checkout main
        git pull origin main
    else
        git checkout "$version"
    fi
    
    # Update dependencies
    source venv/bin/activate
    pip install --upgrade -r requirements/production.txt
    
    # Run migrations
    flask db upgrade
    
    # Update version file
    echo "$version" > "$CURRENT_VERSION_FILE"
    
    # Start service
    if systemctl list-unit-files | grep -q "panel.service"; then
        sudo systemctl start panel.service
    fi
    
    success "Update complete!"
    
    # Run post-install tests
    read -p "Run post-installation tests? (yes/no) [yes]: " RUN_TESTS
    RUN_TESTS=${RUN_TESTS:-yes}
    
    if [[ "$RUN_TESTS" == "yes" ]]; then
        bash "$INSTALL_DIR/scripts/post-install-test.sh"
    fi
}

# Auto-update check (for cron)
auto_check() {
    CURRENT=$(get_current_version)
    LATEST=$(get_latest_version)
    
    if [[ -z "$LATEST" ]]; then
        exit 1
    fi
    
    if version_gt "$LATEST" "$CURRENT"; then
        echo "UPDATE_AVAILABLE:$LATEST"
        
        # Send notification if mail is available
        if command -v mail &> /dev/null; then
            echo "A new version of Panel is available: $LATEST (current: $CURRENT)" | \
                mail -s "Panel Update Available" admin@example.com
        fi
        
        exit 2
    fi
    
    exit 0
}

# Setup auto-update checker
setup_auto_check() {
    info "Setting up automatic update checking..."
    
    # Create cron job
    CRON_JOB="0 2 * * * $INSTALL_DIR/scripts/check-updates.sh --auto-check"
    
    (crontab -l 2>/dev/null | grep -v "check-updates.sh"; echo "$CRON_JOB") | crontab -
    
    success "Auto-update checker configured (runs daily at 2 AM)"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Check for Panel updates and manage versions

Options:
    --check              Check for updates (default)
    --update [VERSION]   Update to latest or specific version
    --changelog          Show recent releases
    --notes VERSION      Show release notes for version
    --auto-check         Auto-check mode (for cron)
    --setup-auto         Setup automatic update checking
    --help               Show this help

Examples:
    # Check for updates
    $0
    $0 --check
    
    # Update to latest version
    $0 --update
    
    # Update to specific version
    $0 --update v1.2.3
    
    # Show recent releases
    $0 --changelog
    
    # Show release notes
    $0 --notes v1.2.3
    
    # Setup auto-check (cron)
    $0 --setup-auto

EOF
}

# Main
main() {
    case "${1:-check}" in
        --check|check)
            print_header
            check_updates
            STATUS=$?
            
            if [[ $STATUS -eq 2 ]]; then
                echo
                read -p "View release notes? (yes/no) [yes]: " VIEW_NOTES
                VIEW_NOTES=${VIEW_NOTES:-yes}
                
                if [[ "$VIEW_NOTES" == "yes" ]]; then
                    echo
                    show_release_notes "$(get_latest_version)"
                fi
                
                echo
                read -p "Update now? (yes/no) [no]: " UPDATE_NOW
                if [[ "$UPDATE_NOW" == "yes" ]]; then
                    perform_update "latest"
                fi
            fi
            ;;
            
        --update|update)
            print_header
            VERSION=${2:-latest}
            
            if [[ "$VERSION" == "latest" ]]; then
                VERSION=$(get_latest_version)
            fi
            
            perform_update "$VERSION"
            ;;
            
        --changelog|changelog)
            print_header
            show_changelog
            ;;
            
        --notes|notes)
            if [[ -z "$2" ]]; then
                error "Version required for --notes"
                exit 1
            fi
            print_header
            show_release_notes "$2"
            ;;
            
        --auto-check|auto-check)
            auto_check
            ;;
            
        --setup-auto|setup-auto)
            print_header
            setup_auto_check
            ;;
            
        --help|help)
            usage
            ;;
            
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
