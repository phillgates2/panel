#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d node_modules ]; then
  npm install
fi

if [ -f /usr/local/lib/workshop-devguard.sh ]; then
  source /usr/local/lib/workshop-devguard.sh
  devguard_acquire "${APP_PORT:-3001}"
fi

PORT="${APP_PORT:-3001}" node src/index.js
