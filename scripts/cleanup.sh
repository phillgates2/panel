#!/usr/bin/env bash
# Cleanup helper for Panel repository
# Usage:
#   bash scripts/cleanup.sh           # interactive, asks before removing common artifacts
#   bash scripts/cleanup.sh --yes     # non-interactive, proceed
#   bash scripts/cleanup.sh --dry-run # show what would be removed
#   bash scripts/cleanup.sh --preview # same as --dry-run

set -euo pipefail

DRY_RUN=false
YES=false
PREVIEW=false

for arg in "$@"; do
    case "$arg" in
        --dry-run|--preview)
            DRY_RUN=true
            PREVIEW=true
            ;;
        --yes|-y|--force)
            YES=true
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run|--preview] [--yes]"
            exit 0
            ;;
        *)
            ;;
    esac
done

# List of default targets relative to repository root
TARGETS=(
    "venv"
    "app.log"
    "app.pid"
    "install.log"
    "install-error.log"
    ".env"
    ".env.backup.*"
    "offline-packages"
    "requirements/"  # sometimes created by tools
    "build/"
    "dist/"
    "*.egg-info"
    "node_modules"
    "tmp/"
    "*.pyc"
)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Panel repository cleanup helper"
echo "Repository root: $REPO_ROOT"

to_remove=()

# Expand glob patterns and collect existing targets
for t in "${TARGETS[@]}"; do
    matches=( $t )
    # If pattern didn't match, the literal pattern stays; check for existence
    found=false
    for m in "${matches[@]}"; do
        # Expand relative to repo root
        if [[ -e "$m" || -d "$m" ]]; then
            to_remove+=("$m")
            found=true
        fi
    done
    # also handle explicit patterns like .env.backup.* using glob
    if [[ "$found" == false ]]; then
        shopt -s nullglob
        globmatches=( $t )
        for gm in "${globmatches[@]}"; do
            if [[ -e "$gm" ]]; then
                to_remove+=("$gm")
            fi
        done
        shopt -u nullglob
    fi
done

if [[ ${#to_remove[@]} -eq 0 ]]; then
    echo "Nothing to clean. No common artifacts found."
    exit 0
fi

echo "The following items were found and will be removed:"
for item in "${to_remove[@]}"; do
    echo "  - $item"
done

if [[ "$DRY_RUN" == true ]]; then
    echo "\nDry run enabled; no files will be deleted."
    exit 0
fi

if [[ "$YES" != true ]]; then
    read -p "Proceed and delete the above items? (y/N): " answer
    answer=${answer:-N}
    if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
        echo "Aborting. No changes made."
        exit 0
    fi
fi

# Safety checks: prevent accidental deletion of root or home
safe_remove() {
    local path="$1"
    # Resolve absolute path
    if [[ -z "$path" ]]; then return; fi
    abs=$(realpath -m "$path")
    if [[ "$abs" == "/" || "$abs" == "$HOME" || "$abs" == "$REPO_ROOT/.." ]]; then
        echo "Refusing to delete unsafe path: $abs"
        return 1
    fi
    if [[ -d "$abs" || -f "$abs" || -L "$abs" ]]; then
        rm -rf -- "$abs"
        echo "Removed: $abs"
    fi
}

# Perform removals
for item in "${to_remove[@]}"; do
    safe_remove "$item" || echo "Skipping: $item"
done

echo "Cleanup complete."