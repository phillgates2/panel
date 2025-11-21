#!/usr/bin/env bash
# memwatch.sh - Memory buffer watcher and core dump helper
#
# Behavior:
# - Checks /proc/meminfo for "Buffers:" value (kB). If > 1GB, attempts to produce
#   a core dump of the ET server process (PID read from $ET_PID_FILE or default).
# - Uses gcore (from gdb) to produce a core file under /var/tmp; requires gdb installed.
# - If systemctl is available and an `etlegacy` unit exists, attempts to restart it if not running.

set -euo pipefail

# Defaults (can be overridden by env)
ET_PID_FILE=${ET_PID_FILE:-/var/run/etlegacy.pid}
THRESH_BYTES=${THRESH_BYTES:-$((1024 * 1024 * 1024))}
CORE_DIR=${CORE_DIR:-/var/tmp}
SERVICE_NAME=${SERVICE_NAME:-etlegacy}
LOG_DIR=${LOG_DIR:-/var/log/panel}
DISCORD_WEBHOOK=${DISCORD_WEBHOOK:-${PANEL_DISCORD_WEBHOOK:-}}

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/memwatch.log"

log(){
  echo "[$(date --iso-8601=seconds)] $*" | tee -a "$LOGFILE"
}

get_buffers_kb(){
  awk '/^Buffers:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0
}

buffers_kb=$(get_buffers_kb)
buffers_bytes=$((buffers_kb * 1024))
echo "[memwatch] Buffers: ${buffers_kb} kB (${buffers_bytes} bytes)"

if [ "$buffers_bytes" -gt "$THRESH_BYTES" ]; then
  log "Buffers exceed threshold (${THRESH_BYTES} bytes) — attempting memdump"
  if [ -f "$ET_PID_FILE" ]; then
    pid=$(cat "$ET_PID_FILE" | tr -d '[:space:]') || true
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        log "Found PID $pid; creating core dump"
      if command -v gcore >/dev/null 2>&1; then
          corefile="$CORE_DIR/etlegacy_core_${pid}_$(date +%Y%m%d%H%M%S).core"
        # gcore writes to pid.N where N is the pid; using -o requires gdb 7.0+
        if gcore -o "$corefile" "$pid" >/dev/null 2>&1; then
            log "Core dumped to ${corefile}.${pid}"
            # Notify discord if configured
            if [ -n "$DISCORD_WEBHOOK" ]; then
              curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"memwatch: core dumped for PID $pid at ${corefile}.${pid}\"}" "$DISCORD_WEBHOOK" || true
            fi
        else
            log "gcore failed — attempting gdb --batch"
          if command -v gdb >/dev/null 2>&1; then
            gdb --batch --pid "$pid" -ex "gcore ${corefile}.gdb" >/dev/null 2>&1 || true
              log "gdb attempted core at ${corefile}.gdb"
              if [ -n "$DISCORD_WEBHOOK" ]; then
                curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"memwatch: gdb attempted core for PID $pid at ${corefile}.gdb\"}" "$DISCORD_WEBHOOK" || true
              fi
          else
              log "gdb not available"
          fi
        fi
      else
          log "gcore not found — install gdb to enable core dumps"
      fi
    else
        log "PID in $ET_PID_FILE ($pid) not running"
      # Attempt service restart if available
      if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-enabled --quiet "$SERVICE_NAME" || systemctl list-units --full -all | grep -q "$SERVICE_NAME"; then
            log "Attempting to restart service $SERVICE_NAME via systemctl"
            if systemctl restart "$SERVICE_NAME"; then
              log "Service $SERVICE_NAME restarted"
              if [ -n "$DISCORD_WEBHOOK" ]; then
                curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"memwatch: restarted $SERVICE_NAME after missing PID\"}" "$DISCORD_WEBHOOK" || true
              fi
            else
              log "systemctl restart failed"
              if [ -n "$DISCORD_WEBHOOK" ]; then
                curl -s -X POST -H "Content-Type: application/json" -d "{\"content\": \"memwatch: failed to restart $SERVICE_NAME\"}" "$DISCORD_WEBHOOK" || true
              fi
            fi
        fi
      fi
    fi
  else
      log "PID file $ET_PID_FILE not found"
  fi
fi
