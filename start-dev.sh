#!/bin/bash

# Development Start Script - Minimal Background Monitoring
# Use this for development to reduce log noise from background processes

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "🚀 Starting OZ Panel in development mode (minimal monitoring)..."
echo "📱 Access at: http://localhost:8080"
echo "⚠️  Background monitoring is disabled for cleaner development experience"
echo ""

# Set development mode environment
export PANEL_USE_SQLITE=1
export PANEL_DEV_MODE=1
export FLASK_ENV=development

# Start the application
python3 app.py