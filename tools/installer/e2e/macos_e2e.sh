#!/usr/bin/env bash
set -euo pipefail

# End-to-end macOS test using Homebrew. WARNING: installs and uninstalls packages on the runner.

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not available on runner; aborting"
  exit 1
fi

echo "[e2e] Brew update"
brew update

echo "[e2e] Installing packages: postgresql redis nginx"
brew install postgresql redis nginx

echo "[e2e] Starting services (best-effort)"
brew services start postgresql || true
brew services start redis || true
brew services start nginx || true

echo "[e2e] Verifying binaries..."
command -v psql || (echo "psql missing" && exit 2)
command -v redis-server || (echo "redis-server missing" && exit 2)
command -v nginx || (echo "nginx missing" && exit 2)

echo "[e2e] Stopping services and uninstalling"
brew services stop postgresql || true
brew services stop redis || true
brew services stop nginx || true

brew uninstall --force postgresql redis nginx || true

# verify removals
if command -v psql >/dev/null; then echo "psql still present after removal"; fi

echo "[e2e] macOS E2E completed successfully."
