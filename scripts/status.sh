#!/bin/bash

# Panel Application Status Checker
# Run with: bash status.sh

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Panel Application Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get installation directory
INSTALL_DIR=${1:-~/panel}
INSTALL_DIR=$(eval echo $INSTALL_DIR)

if [[ ! -d "$INSTALL_DIR" ]]; then
    echo -e "${RED}✗${NC} Panel not found at $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

# Check virtual environment
if [[ -d "venv" ]]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists"
    source venv/bin/activate 2>/dev/null
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
    echo -e "  ${BLUE}→${NC} Python version: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Virtual environment missing"
fi

# Check configuration
if [[ -f ".env" ]]; then
    echo -e "${GREEN}✓${NC} Configuration file exists"
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs) 2>/dev/null
    
    if [[ -n "$FLASK_ENV" ]]; then
        echo -e "  ${BLUE}→${NC} Environment: $FLASK_ENV"
    fi
    if [[ -n "$DATABASE_URL" ]]; then
        DB_TYPE=$(echo "$DATABASE_URL" | cut -d':' -f1)
        echo -e "  ${BLUE}→${NC} Database: $DB_TYPE"
    fi
else
    echo -e "${RED}✗${NC} Configuration file missing"
fi

# Check database
if [[ -f "panel.db" ]]; then
    DB_SIZE=$(du -h panel.db | cut -f1)
    echo -e "${GREEN}✓${NC} SQLite database exists (${DB_SIZE})"
elif [[ "$DATABASE_URL" == postgresql* ]]; then
    if command -v psql &> /dev/null; then
        if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw panel_db; then
            echo -e "${GREEN}✓${NC} PostgreSQL database exists"
        else
            echo -e "${RED}✗${NC} PostgreSQL database not found"
        fi
    fi
fi

# Check Redis
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        REDIS_VERSION=$(redis-cli --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        echo -e "${GREEN}✓${NC} Redis is running (v$REDIS_VERSION)"
        
        # Check Redis memory
        REDIS_MEM=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d':' -f2 | tr -d '\r')
        if [[ -n "$REDIS_MEM" ]]; then
            echo -e "  ${BLUE}→${NC} Memory usage: $REDIS_MEM"
        fi
    else
        echo -e "${RED}✗${NC} Redis is not responding"
    fi
else
    echo -e "${YELLOW}⚠${NC} Redis not installed"
fi

# Check if app is running
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -t -i:5000)
    echo -e "${GREEN}✓${NC} Application is running (PID: $PID)"
    echo -e "  ${BLUE}→${NC} Port: 5000"
    
    # Try to check health endpoint
    if command -v curl &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null || echo "000")
        if [[ "$HTTP_CODE" == "200" ]]; then
            echo -e "  ${BLUE}→${NC} Health check: ${GREEN}OK${NC}"
        else
            echo -e "  ${BLUE}→${NC} Health check: ${YELLOW}No endpoint${NC}"
        fi
    fi
else
    echo -e "${RED}✗${NC} Application is not running"
fi

# Check systemd service
if systemctl is-active --quiet panel 2>/dev/null; then
    SERVICE_STATUS=$(systemctl is-active panel)
    echo -e "${GREEN}✓${NC} Systemd service: $SERVICE_STATUS"
elif systemctl list-unit-files | grep -q panel.service; then
    SERVICE_STATUS=$(systemctl is-active panel 2>/dev/null || echo "inactive")
    echo -e "${YELLOW}⚠${NC} Systemd service: $SERVICE_STATUS"
fi

# Check nginx
if command -v nginx &> /dev/null; then
    if [[ -f /etc/nginx/sites-enabled/panel ]]; then
        if systemctl is-active --quiet nginx; then
            echo -e "${GREEN}✓${NC} Nginx is configured and running"
        else
            echo -e "${YELLOW}⚠${NC} Nginx configured but not running"
        fi
    fi
fi

# Check disk space
DISK_USAGE=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1)
echo -e "${BLUE}ℹ${NC} Installation size: $DISK_USAGE"

# Check logs
if [[ -d "logs" ]]; then
    LOG_COUNT=$(ls logs/*.log 2>/dev/null | wc -l)
    if [[ $LOG_COUNT -gt 0 ]]; then
        echo -e "${BLUE}ℹ${NC} Log files: $LOG_COUNT"
        LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)
        if [[ -n "$LATEST_LOG" ]]; then
            LOG_SIZE=$(du -h "$LATEST_LOG" | cut -f1)
            echo -e "  ${BLUE}→${NC} Latest: $(basename $LATEST_LOG) (${LOG_SIZE})"
        fi
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Quick actions
echo "Quick Actions:"
echo "  Start:  ./start.sh"
echo "  Test:   ./test.sh"
echo "  Logs:   tail -f logs/app.log"
if systemctl list-unit-files | grep -q panel.service; then
    echo "  Status: sudo systemctl status panel"
fi
echo ""
