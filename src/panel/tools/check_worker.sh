#!/usr/bin/env bash
# check_worker.sh - checks rq-worker service and restarts if inactive
# Sends a discord alert if repeated failures exceed threshold

SERVICE=${1:-rq-worker.service}
MAX_FAILS=${MAX_FAILS:-3}
STATE_DIR=${STATE_DIR:-/var/log/panel}
FAIL_FILE="$STATE_DIR/worker_failures"
DISCORD_WEBHOOK=${PANEL_DISCORD_WEBHOOK:-${DISCORD_WEBHOOK:-}}

mkdir -p "$STATE_DIR"
touch "$FAIL_FILE"

status=$(systemctl is-active "$SERVICE" 2>/dev/null || echo unknown)
if [ "$status" != "active" ]; then
  echo "$(date --iso-8601=seconds) - $SERVICE status=$status" >> "$STATE_DIR/worker_watch.log"
  systemctl restart "$SERVICE" || true
  # increment failure counter
  count=$(cat "$FAIL_FILE" 2>/dev/null || echo 0)
  count=$((count+1))
  echo "$count" > "$FAIL_FILE"
  if [ "$count" -ge "$MAX_FAILS" ]; then
    # send discord alert
    if [ -n "$DISCORD_WEBHOOK" ] && command -v curl >/dev/null 2>&1; then
      # construct simple JSON payload without jq
      desc="Service $SERVICE restarted $count times"
      json=$(printf '{"content":null,"embeds":[{"title":"RQ Worker Alert","description":"%s","color":15158332}]}' "$(echo "$desc" | sed 's/"/\\"/g')")
      curl -s -X POST -H "Content-Type: application/json" -d "$json" "$DISCORD_WEBHOOK" || true
    fi
    # reset counter
    echo 0 > "$FAIL_FILE"
  fi
else
  # healthy, reset counter
  echo 0 > "$FAIL_FILE"
fi
