#!/usr/bin/env bash
set -euo pipefail

# End-to-end test: install packages via detected package manager, verify binaries, and remove them.
# WARNING: This runs on the runner VM and will install/remove system packages. Use only on ephemeral runners.

echo "[e2e] Detecting package manager via Python helper..."
PM=$(python - <<'PY'
from tools.installer.deps import get_package_manager
print(get_package_manager() or '')
PY
)

if [[ -z "$PM" ]]; then
  echo "No package manager detected; aborting."
  exit 1
fi

echo "[e2e] Using package manager: $PM"

# Ensure we can run sudo
if ! sudo -n true 2>/dev/null; then
  echo "Requesting sudo (may ask for password in interactive runs)..."
fi

export DEBIAN_FRONTEND=noninteractive

echo "[e2e] Installing packages (postgresql, redis-server, nginx)"
if [[ "$PM" == "apt" || "$PM" == "" ]]; then
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends postgresql redis-server nginx
else
  echo "Unexpected package manager $PM on Linux runner; aborting"
  exit 1
fi

echo "[e2e] Verifying binaries..."
command -v psql || (echo "psql missing" && exit 2)
command -v redis-server || (echo "redis-server missing" && exit 2)
command -v nginx || (echo "nginx missing" && exit 2)

echo "[e2e] Stopping services (best-effort)"
sudo systemctl stop postgresql || true
sudo systemctl stop redis-server || true
sudo systemctl stop nginx || true

echo "[e2e] Removing packages"
sudo apt-get remove -y --purge postgresql redis-server nginx || true
sudo apt-get autoremove -y || true

# verify binaries removed
if command -v psql >/dev/null; then echo "psql still present after removal"; fi

echo "[e2e] Linux E2E completed successfully."
