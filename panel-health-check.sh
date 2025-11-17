#!/usr/bin/env bash
# Panel Health Check and Diagnostic Tool
# Helps troubleshoot connection and startup issues

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}${BLUE}Panel Health Check & Diagnostics${NC}"
echo -e "${BLUE}=================================${NC}"
echo

# Check if panel directory exists
PANEL_DIR="${1:-/home/admin/panel}"
if [[ ! -d "$PANEL_DIR" ]]; then
    echo -e "${RED}✗ Panel directory not found: $PANEL_DIR${NC}"
    exit 1
fi

cd "$PANEL_DIR"
echo -e "${GREEN}✓ Panel directory: $PANEL_DIR${NC}"

# Check Python virtual environment
if [[ -d "venv" ]]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    if [[ -f "venv/bin/python3" ]]; then
        PYTHON_VERSION=$(venv/bin/python3 --version 2>&1)
        echo -e "  Python: $PYTHON_VERSION"
    fi
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
fi

# Check if processes are running
echo
echo -e "${BOLD}Process Status:${NC}"
if pgrep -f "python.*app.py" > /dev/null 2>&1; then
    APP_PIDS=$(pgrep -f "python.*app.py" | tr '\n' ' ')
    echo -e "${GREEN}✓ Panel web server running (PIDs: $APP_PIDS)${NC}"
else
    echo -e "${RED}✗ Panel web server not running${NC}"
fi

if pgrep -f "python.*run_worker.py" > /dev/null 2>&1; then
    WORKER_PIDS=$(pgrep -f "python.*run_worker.py" | tr '\n' ' ')
    echo -e "${GREEN}✓ Background worker running (PIDs: $WORKER_PIDS)${NC}"
else
    echo -e "${YELLOW}⚠ Background worker not running${NC}"
fi

# Check Redis
echo
echo -e "${BOLD}Service Status:${NC}"
if pgrep -x redis-server > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis server running${NC}"
    if command -v redis-cli &>/dev/null; then
        if redis-cli ping &>/dev/null; then
            echo -e "${GREEN}✓ Redis responding to commands${NC}"
        else
            echo -e "${YELLOW}⚠ Redis not responding${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Redis server not running${NC}"
fi

# Check PostgreSQL
if pgrep -x postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL running${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL not running (SQLite may be in use)${NC}"
fi

# Check Nginx
if pgrep nginx > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx running${NC}"
else
    echo -e "${YELLOW}⚠ Nginx not running (direct access required)${NC}"
fi

# Check environment and configuration
echo
echo -e "${BOLD}Configuration:${NC}"
if [[ -f ".env" ]]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
    if grep -q "PANEL_SECRET_KEY" .env 2>/dev/null; then
        echo -e "  - SECRET_KEY: configured"
    fi
    if grep -q "PANEL_USE_SQLITE" .env 2>/dev/null; then
        USE_SQLITE=$(grep "PANEL_USE_SQLITE" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [[ "$USE_SQLITE" == "True" ]]; then
            echo -e "  - Database: SQLite"
        else
            echo -e "  - Database: PostgreSQL"
        fi
    fi
    if grep -q "FLASK_PORT" .env 2>/dev/null; then
        PORT=$(grep "FLASK_PORT" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        echo -e "  - Port: $PORT"
    else
        PORT=8080
        echo -e "  - Port: $PORT (default)"
    fi
else
    echo -e "${RED}✗ .env file not found${NC}"
    PORT=8080
fi

# Check port availability
echo
echo -e "${BOLD}Network Status:${NC}"
if command -v netstat &>/dev/null; then
    if netstat -tuln | grep -q ":${PORT:-8080} "; then
        echo -e "${GREEN}✓ Port ${PORT:-8080} is in use (panel likely listening)${NC}"
        netstat -tuln | grep ":${PORT:-8080} " | head -1
    else
        echo -e "${YELLOW}⚠ Port ${PORT:-8080} is not in use${NC}"
    fi
elif command -v ss &>/dev/null; then
    if ss -tuln | grep -q ":${PORT:-8080} "; then
        echo -e "${GREEN}✓ Port ${PORT:-8080} is in use (panel likely listening)${NC}"
        ss -tuln | grep ":${PORT:-8080} " | head -1
    else
        echo -e "${YELLOW}⚠ Port ${PORT:-8080} is not in use${NC}"
    fi
fi

# Try HTTP health check
echo
echo -e "${BOLD}HTTP Health Check:${NC}"
if command -v curl &>/dev/null; then
    # Try health endpoint
    if curl -f -s -m 5 "http://localhost:${PORT:-8080}/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Health endpoint responding${NC}"
    else
        # Try root endpoint
        if curl -f -s -m 5 "http://localhost:${PORT:-8080}/" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Root endpoint responding (health endpoint may not exist)${NC}"
        else
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "http://localhost:${PORT:-8080}/" 2>/dev/null || echo "000")
            if [[ "$HTTP_CODE" == "000" ]]; then
                echo -e "${RED}✗ Cannot connect to http://localhost:${PORT:-8080}/${NC}"
                echo -e "  ${YELLOW}Possible causes:${NC}"
                echo -e "    - Application still starting up (wait 10-20 seconds)"
                echo -e "    - Application crashed (check logs)"
                echo -e "    - Firewall blocking connection"
                echo -e "    - Wrong port configuration"
            else
                echo -e "${YELLOW}⚠ HTTP response code: $HTTP_CODE${NC}"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠ curl not available, skipping HTTP check${NC}"
fi

# Check logs
echo
echo -e "${BOLD}Recent Logs:${NC}"
if [[ -f "logs/panel.log" ]]; then
    echo -e "${GREEN}Panel log (last 10 lines):${NC}"
    tail -10 logs/panel.log | sed 's/^/  /'
    echo
else
    echo -e "${YELLOW}⚠ No panel.log found${NC}"
fi

if [[ -f "instance/logs/app.log" ]]; then
    echo -e "${GREEN}Application log (last 10 lines):${NC}"
    tail -10 instance/logs/app.log | sed 's/^/  /'
    echo
fi

# Check for errors in logs
if [[ -f "logs/panel.log" ]]; then
    ERROR_COUNT=$(grep -c "ERROR" logs/panel.log 2>/dev/null || echo "0")
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo -e "${RED}Found $ERROR_COUNT errors in panel.log${NC}"
        echo -e "${YELLOW}Recent errors:${NC}"
        grep "ERROR" logs/panel.log | tail -3 | sed 's/^/  /'
        echo
    fi
fi

# Summary and recommendations
echo
echo -e "${BOLD}${BLUE}Summary & Recommendations:${NC}"
echo -e "${BLUE}===========================${NC}"

# Determine overall status
ISSUES=0

if ! pgrep -f "python.*app.py" > /dev/null 2>&1; then
    echo -e "${RED}✗ Panel not running${NC}"
    echo -e "  ${YELLOW}To start:${NC}"
    echo -e "    cd $PANEL_DIR"
    echo -e "    source venv/bin/activate"
    echo -e "    python3 app.py"
    ((ISSUES++))
fi

if ! pgrep -x redis-server > /dev/null 2>&1; then
    echo -e "${RED}✗ Redis not running${NC}"
    echo -e "  ${YELLOW}To start:${NC} sudo systemctl start redis"
    ((ISSUES++))
fi

if [[ $ISSUES -eq 0 ]]; then
    if curl -f -s -m 5 "http://localhost:${PORT:-8080}/" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Panel appears healthy and accessible${NC}"
        echo -e "  Access at: ${BOLD}http://localhost:${PORT:-8080}${NC}"
    else
        echo -e "${YELLOW}⚠ Panel running but not responding to HTTP requests${NC}"
        echo -e "  ${YELLOW}Possible causes:${NC}"
        echo -e "    - Still initializing (wait 20-30 seconds after startup)"
        echo -e "    - Check logs for errors: tail -f $PANEL_DIR/logs/panel.log"
        echo -e "    - Try restarting: pkill -f 'python.*app.py' && cd $PANEL_DIR && source venv/bin/activate && python3 app.py"
    fi
else
    echo -e "${YELLOW}Found $ISSUES issue(s) - see recommendations above${NC}"
fi

echo
