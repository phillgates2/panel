# Fix Internal Server Error on Login

## Problem
The login error is caused by **missing database tables**. The login function tries to insert records into `user_activity` and `user_session` tables (from `models_extended.py`), but these tables don't exist.

Error: `sqlite3.OperationalError: no such table: user_activity`

## Solution - Run on Production Server

```bash
# 1. Navigate to panel directory
cd /home/admin/panel  # or wherever your panel is installed

# 2. Pull latest fixes
git pull origin main

# 3. Activate virtual environment
source venv/bin/activate  # or: source .venv/bin/activate

# 4. Run database migration to create missing tables
python scripts/migrate_database.py

# 5. Restart services
sudo systemctl restart panel-gunicorn rq-worker

# 6. Check service status
sudo systemctl status panel-gunicorn

# 7. Verify tables were created
python -c "from app import app, db; from sqlalchemy import inspect; app.app_context().push(); tables = inspect(db.engine).get_table_names(); print(f'Tables: {len(tables)}'); print('user_activity:', 'user_activity' in tables)"
```

## What the Migration Does

The `migrate_database.py` script creates all missing database tables, including:
- `user_session` - Track active user sessions for security
- `user_activity` - Log all user actions
- `api_key` - API key management
- `two_factor_auth` - 2FA support
- `notification` - User notifications
- `server_template` - Server configuration templates
- `performance_metric` - Performance monitoring data

## If Services Don't Start

Check detailed logs:
```bash
# Check gunicorn service logs
sudo journalctl -u panel-gunicorn -n 50 --no-pager

# Check application logs
tail -100 ~/.local/share/panel/logs/panel.log

# Test app import
cd /home/admin/panel
source venv/bin/activate
python -c "from app import app; from models_extended import UserActivity; print('Import successful')"

# Manual table creation if script fails
python -c "from app import app, db; from models_extended import *; app.app_context().push(); db.create_all(); print('Tables created')"
```

## Verify Fix

After migration and restart:
```bash
# Test login page loads
curl -s http://localhost:8080/login | head -50

# Check database has required tables
cd /home/admin/panel
source venv/bin/activate
python -c "from app import db, app; from sqlalchemy import inspect; app.app_context().push(); inspector = inspect(db.engine); tables = inspector.get_table_names(); print('\n'.join(sorted(tables)))"
```

## What Was Previously Fixed in Code

- **Commit bf29525**: Fixed module-level execution causing server conflicts
- **Commit d67ebf7**: Refactored monitoring systems to prevent context errors
- **Commit 2a87e0f**: Fixed app context checks in create_default_templates
- **Commit afb9deb**: Updated UI with Server Management button and modern admin_servers page
