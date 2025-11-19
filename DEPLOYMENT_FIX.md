# Fix Internal Server Error on Login

## Problem
The production server is running old code with critical bugs that were just fixed:
1. `app.run()` code was executing on module import (causing conflicts)
2. Indentation errors in `config_manager.py`
3. Missing exception handlers

## Solution - Run on Production Server

```bash
# 1. Stop all services
sudo systemctl stop panel-gunicorn rq-worker

# 2. Navigate to panel directory
cd /home/admin/panel  # or wherever your panel is installed

# 3. Pull latest fixes
git pull origin main

# 4. Restart services
sudo systemctl start panel-gunicorn rq-worker

# 5. Check service status
sudo systemctl status panel-gunicorn

# 6. Check logs for any errors
tail -50 /home/admin/panel/logs/panel.log
```

## If Services Don't Start

Check detailed logs:
```bash
# Check gunicorn service logs
sudo journalctl -u panel-gunicorn -n 50 --no-pager

# Check application logs
tail -100 /home/admin/panel/logs/panel.log

# Test app directly
cd /home/admin/panel
source venv/bin/activate
python -c "from app import app; print('Import successful')"
```

## What Was Fixed

- **Commit bf29525**: Fixed module-level execution causing server conflicts
- **Commit d67ebf7**: Refactored monitoring systems to prevent context errors  
- **Commit 2a87e0f**: Fixed app context checks in create_default_templates

## Verify Fix

After restarting, the server should:
- Start without "Address in use" errors
- Handle login requests without Internal Server Error
- Show "Panel application ready for use" in logs
