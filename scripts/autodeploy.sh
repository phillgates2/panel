#!/usr/bin/env bash
# autodeploy.sh - resilient auto-downloader and deployer for ET:Legacy + n!tmod
#
# Environment variables:
# - DOWNLOAD_URL: URL to download (zip/tar.gz)
# - DOWNLOAD_CHECKSUM: optional sha256 checksum to verify
# - INSTALL_DIR: installation directory (default /opt/etlegacy)
# - BACKUP_DIR: directory to store previous releases
# - SERVICE_NAME: systemd service name to restart after deploy

set -euo pipefail

DOWNLOAD_URL="${DOWNLOAD_URL:-https://example.com/etlegacy.zip}"
DOWNLOAD_CHECKSUM="${DOWNLOAD_CHECKSUM:-}"  # sha256 hex string
INSTALL_DIR="${INSTALL_DIR:-/opt/etlegacy}"
BACKUP_DIR="${BACKUP_DIR:-/opt/etlegacy_backups}"
TMP_DIR="${TMP_DIR:-/tmp/et_download_$$}"
SERVICE_NAME="${SERVICE_NAME:-etlegacy}"
LOG_DIR=${LOG_DIR:-/var/log/panel}
DISCORD_WEBHOOK=${DISCORD_WEBHOOK:-${PANEL_DISCORD_WEBHOOK:-}}

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/autodeploy.log"

log(){
  echo "[$(date --iso-8601=seconds)] $*" | tee -a "$LOGFILE"
}

mkdir -p "$TMP_DIR"
mkdir -p "$BACKUP_DIR"

log "Downloading server from $DOWNLOAD_URL to $TMP_DIR"
DL_FILE="$TMP_DIR/server.download"
if command -v curl >/dev/null 2>&1; then
  curl -L "$DOWNLOAD_URL" -o "$DL_FILE"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$DL_FILE" "$DOWNLOAD_URL"
else
  echo "[autodeploy] No curl/wget available"
  exit 1
fi

if [ -n "$DOWNLOAD_CHECKSUM" ]; then
  log "Verifying checksum"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "$DOWNLOAD_CHECKSUM  $DL_FILE" | sha256sum -c - || { log "Checksum mismatch"; [ -n "$DISCORD_WEBHOOK" ] && curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"autodeploy: checksum mismatch for $DOWNLOAD_URL\"}" "$DISCORD_WEBHOOK" || true; exit 2; }
  else
    log "sha256sum not available, cannot verify checksum"
    exit 3
  fi
fi

echo "[autodeploy] Preparing extraction"
EXTRACT_DIR="$TMP_DIR/extracted"
mkdir -p "$EXTRACT_DIR"

if file "$DL_FILE" | grep -q "Zip archive"; then
  if command -v unzip >/dev/null 2>&1; then
    unzip -o "$DL_FILE" -d "$EXTRACT_DIR"
  else
    echo "[autodeploy] unzip not available"
    exit 4
  fi
elif file "$DL_FILE" | grep -q "gzip compressed"; then
  if command -v tar >/dev/null 2>&1; then
    tar -xzf "$DL_FILE" -C "$EXTRACT_DIR"
  else
    echo "[autodeploy] tar not available"
    exit 4
  fi
else
  echo "[autodeploy] Unknown archive type; attempting unzip"
  if command -v unzip >/dev/null 2>&1; then
    unzip -o "$DL_FILE" -d "$EXTRACT_DIR" || true
  fi
fi

log "Backing up existing install (if present)"
if [ -d "$INSTALL_DIR" ]; then
  ts=$(date +%Y%m%d%H%M%S)
  mkdir -p "$BACKUP_DIR"
  mv "$INSTALL_DIR" "$BACKUP_DIR/etlegacy_backup_$ts"
fi

log "Moving new files into $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a "$EXTRACT_DIR/." "$INSTALL_DIR/"

log "Setting permissions"
chown -R root:root "$INSTALL_DIR" || true

if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-units --full -all | grep -q "$SERVICE_NAME"; then
    log "Restarting $SERVICE_NAME"
    systemctl daemon-reload || true
    if systemctl restart "$SERVICE_NAME"; then
      log "Service $SERVICE_NAME restarted"
      [ -n "$DISCORD_WEBHOOK" ] && curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"autodeploy: deployed $DOWNLOAD_URL and restarted $SERVICE_NAME\"}" "$DISCORD_WEBHOOK" || true
    else
      log "Failed to restart $SERVICE_NAME"
      [ -n "$DISCORD_WEBHOOK" ] && curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"autodeploy: deployed $DOWNLOAD_URL but failed to restart $SERVICE_NAME\"}" "$DISCORD_WEBHOOK" || true
    fi
  fi
fi

log "Cleanup $TMP_DIR"
rm -rf "$TMP_DIR"

log "Deploy complete"
[ -n "$DISCORD_WEBHOOK" ] && curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"autodeploy: completed deployment of $DOWNLOAD_URL\"}" "$DISCORD_WEBHOOK" || true
