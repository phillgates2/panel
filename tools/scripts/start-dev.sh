#!/usr/bin/env bash
set -euo pipefail

# Deprecated dev start script.
# Delegates to the unified panel CLI.

cd "$(cd "$(dirname "$0")" && pwd)"

echo "[DEPRECATED] Use ./panel.sh start instead of start-dev.sh" >&2

if [[ ! -x ./panel.sh ]]; then
    echo "Error: ./panel.sh not found or not executable." >&2
    exit 1
fi

exec ./panel.sh start "$@"
