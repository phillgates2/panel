#!/usr/bin/env bash
set -eo pipefail

# ==============================================================================
# -OZ- Panel Hub Enterprise - Master Background Execution Sentinel Utility
# This utility launches the application core daemon in the background using PM2
# or nohup, guaranteeing it completely survives SSH session terminations.
# ==============================================================================

echo "👑 -OZ- Panel Hub Enterprise Background Execution Sentinel Active"
echo "--------------------------------------------------------------------------------"

# 1. Verify working directory
if [ ! -f "src/index.js" ]; then
    echo "❌ Error: Please execute this script from the root /home/user/panel directory."
    exit 1
fi

# 2. Ensure NPM packages are fully synchronized
echo "📦 Auditing Node.js package dependencies..."
npm install --silent

# 3. Detect or install PM2 (Process Manager 2)
if ! command -v pm2 &> /dev/null && ! npx pm2 --version &> /dev/null; then
    echo "⚡ PM2 process orchestrator not detected globally. Installing PM2 locally..."
    npm install pm2 --save
fi

# 4. Power boot in background mode
echo "🚀 Starting Master Monolith Daemon in background mode via PM2..."

npx pm2 start src/index.js --name "oz-panel-hub" --time --watch="['src/database']" --ignore-watch="['mock_db.json', 'servers', 'logs']" || \
npx pm2 restart oz-panel-hub

echo "--------------------------------------------------------------------------------"
echo "✨ Execution complete! Your entire -OZ- Suite is now operational in the background."
echo "You can completely close your active SSH terminal connection without halting any game instances."
echo ""
echo "💡 Background Management Commands:"
echo "  • View Rolling Telemetry Logs : npx pm2 logs oz-panel-hub"
echo "  • Inspect Monolith Status   : npx pm2 status oz-panel-hub"
echo "  • Halt Background Daemon    : npx pm2 stop oz-panel-hub"
echo "  • Silky Smooth Reload       : npx pm2 reload oz-panel-hub"
echo "=============================================================================="
