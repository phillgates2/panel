#!/usr/bin/env bash

# create-offline-cache.sh
# Creates an offline package cache for Panel installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
CACHE_DIR="offline-packages"
REPO_DIR="$(pwd)"
PYTHON_VERSION="3.10"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        -r|--repo)
            REPO_DIR="$2"
            shift 2
            ;;
        -p|--python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -d, --dir DIR       Output directory for offline cache (default: offline-packages)"
            echo "  -r, --repo DIR      Repository directory (default: current directory)"
            echo "  -p, --python VER    Python version (default: 3.10)"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Panel Offline Package Cache Creator            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

log_info "Creating offline package cache..."
log_info "Repository: $REPO_DIR"
log_info "Cache directory: $CACHE_DIR"
log_info "Python version: $PYTHON_VERSION"
echo ""

# Check if we're in the Panel repository
if [[ ! -f "$REPO_DIR/app.py" ]]; then
    log_error "Not in Panel repository. Please run from Panel directory or use --repo option"
    exit 1
fi

cd "$REPO_DIR"

# Find requirements file
REQUIREMENTS_FILE=""
if [[ -f "requirements/requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements/requirements.txt"
elif [[ -f "requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements.txt"
else
    log_error "requirements.txt not found"
    exit 1
fi

log_success "Found requirements file: $REQUIREMENTS_FILE"

# Count packages
PKG_COUNT=$(grep -v '^#' "$REQUIREMENTS_FILE" | grep -v '^$' | wc -l)
log_info "Will download $PKG_COUNT packages"

# Create cache directory
mkdir -p "$CACHE_DIR"
log_success "Cache directory created: $CACHE_DIR"

# Download packages
log_info "Downloading packages (this may take several minutes)..."
echo ""

pip download -r "$REQUIREMENTS_FILE" -d "$CACHE_DIR" --python-version "$PYTHON_VERSION" || {
    log_error "Failed to download packages"
    exit 1
}

# Download optional development dependencies
if [[ -f "requirements/development.txt" ]]; then
    log_info "Downloading development dependencies..."
    pip download -r "requirements/development.txt" -d "$CACHE_DIR" --python-version "$PYTHON_VERSION" 2>/dev/null || true
fi

# Download optional production dependencies
if [[ -f "requirements/production.txt" ]]; then
    log_info "Downloading production dependencies..."
    pip download -r "requirements/production.txt" -d "$CACHE_DIR" --python-version "$PYTHON_VERSION" 2>/dev/null || true
fi

# Create README
cat > "$CACHE_DIR/README.md" <<EOF
# Offline Package Cache

This directory contains Python packages for offline Panel installation.

## Usage

1. Copy this directory to the target machine
2. Run the installer with --offline flag:
   \`\`\`bash
   ./scripts/install-interactive.sh --offline
   \`\`\`

## Details

- Created: $(date)
- Python version: $PYTHON_VERSION
- Package count: $PKG_COUNT
- Requirements file: $REQUIREMENTS_FILE

## Regenerating

To update this cache with latest packages:
\`\`\`bash
./scripts/create-offline-cache.sh -d $CACHE_DIR
\`\`\`
EOF

# Count downloaded files
DOWNLOADED_COUNT=$(find "$CACHE_DIR" -name "*.whl" -o -name "*.tar.gz" | wc -l)
CACHE_SIZE=$(du -sh "$CACHE_DIR" | cut -f1)

echo ""
log_success "Offline package cache created successfully!"
echo ""
echo "Cache Statistics:"
echo "- Location: $CACHE_DIR"
echo "- Files downloaded: $DOWNLOADED_COUNT"
echo "- Total size: $CACHE_SIZE"
echo ""
echo "To use this cache for offline installation:"
echo "  1. Copy the '$CACHE_DIR' directory to target machine"
echo "  2. Place it in the Panel repository root"
echo "  3. Run: ./scripts/install-interactive.sh --offline"
echo ""
