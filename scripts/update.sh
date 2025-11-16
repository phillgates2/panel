#!/usr/bin/env bash
set -euo pipefail

# Deprecated update/migration script.
# This script now delegates to the unified panel CLI.

HERE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$HERE_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "[DEPRECATED] Use ./panel.sh update instead of scripts/update.sh" >&2

if [[ ! -x ./panel.sh ]]; then
  echo "Error: ./panel.sh not found or not executable." >&2
  exit 1
fi

exec ./panel.sh update "$@"
