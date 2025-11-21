#!/bin/bash
# Panel Backup System Setup Script
# This script installs and enables the automated backup timers

set -e

echo "Panel Backup System Setup"
echo "========================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Please run as the panel user."
   exit 1
fi

# Get the panel directory
PANEL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Panel directory: $PANEL_DIR"

# Copy service files
echo "Installing systemd services..."
sudo cp "$PANEL_DIR/deploy/backup-"*.service /etc/systemd/system/
sudo cp "$PANEL_DIR/deploy/backup-"*.timer /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start timers
echo "Enabling backup timers..."
sudo systemctl enable backup-database.timer
sudo systemctl enable backup-config.timer
sudo systemctl enable backup-servers.timer
sudo systemctl enable backup-cleanup.timer

echo "Starting backup timers..."
sudo systemctl start backup-database.timer
sudo systemctl start backup-config.timer
sudo systemctl start backup-servers.timer
sudo systemctl start backup-cleanup.timer

# Show status
echo ""
echo "Backup system status:"
echo "====================="
sudo systemctl list-timers --all | grep backup

echo ""
echo "Backup system setup complete!"
echo ""
echo "Schedule:"
echo "- Database backup: Daily"
echo "- Configuration backup: Weekly"
echo "- Server backups: Every 6 hours"
echo "- Backup cleanup: Monthly"
echo ""
echo "You can check timer status with: sudo systemctl list-timers"
echo "View logs with: journalctl -u backup-database.service"
