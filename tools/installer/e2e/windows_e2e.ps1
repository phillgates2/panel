# End-to-end Windows E2E script using Chocolatey (runner must have admin privileges)
# WARNING: This will install/uninstall packages on the runner.

$ErrorActionPreference = 'Stop'

function Ensure-Command($name) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $c) { Write-Host "$name not found"; exit 1 }
}

# Ensure choco exists
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Chocolatey not found on runner; aborting"
    exit 1
}

Write-Host "[e2e] Installing packages: postgresql, redis-64, nginx"
choco install postgresql -y --no-progress
choco install redis-64 -y --no-progress
choco install nginx -y --no-progress

Write-Host "[e2e] Verifying commands"
Ensure-Command psql
Ensure-Command redis-server
Ensure-Command nginx

Write-Host "[e2e] Uninstalling packages"
choco uninstall postgresql -y --remove-dependencies --no-progress || Write-Host "Failed to uninstall postgresql"
choco uninstall redis-64 -y --remove-dependencies --no-progress || Write-Host "Failed to uninstall redis-64"
choco uninstall nginx -y --remove-dependencies --no-progress || Write-Host "Failed to uninstall nginx"

Write-Host "[e2e] Windows E2E completed successfully."