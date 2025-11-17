#!/usr/bin/env bash
set -euo pipefail

# Panel management script
# Unified interface for install, update, and uninstall operations

HERE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE_DIR"

show_help() {
  cat <<'HELP'
Panel Management Script

Usage:
  ./panel.sh <command> [options]

Commands:
  install     Install the panel application
  update      Update an existing installation
  uninstall   Remove the panel application
  help        Show this help message

Options:
  --dry-run   Preview actions without making changes (install only)

Examples:
  ./panel.sh install
  ./panel.sh install --dry-run
  ./panel.sh update
  ./panel.sh uninstall

HELP
}

# Parse command
COMMAND="${1:-}"
shift || true

case "$COMMAND" in
  install)
    exec bash scripts/install.sh "$@"
    ;;
  update)
    exec bash scripts/update.sh "$@"
    ;;
  uninstall)
    exec bash scripts/uninstall.sh "$@"
    ;;
  help|--help|-h)
    show_help
    exit 0
    ;;
  "")
    echo "Error: No command specified"
    echo ""
    show_help
    exit 1
    ;;
  *)
    echo "Error: Unknown command '$COMMAND'"
    echo ""
    show_help
    exit 1
    ;;
esac
