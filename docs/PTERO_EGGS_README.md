# Ptero-Eggs Auto-Update and Management System

Comprehensive system for automatically fetching, managing, and applying game server templates from the [Ptero-Eggs](https://github.com/Ptero-Eggs/game-eggs) repository.

## Features

### 🔄 Auto-Update System
- **Automatic Syncing**: Periodically fetch latest templates from Ptero-Eggs GitHub
- **Version Tracking**: Track template versions with commit hash linking
- **Smart Updates**: Detect changes, skip unchanged templates
- **Update Notifications**: Discord webhook integration for sync status

### 🖥️ Web UI
- **Template Browser**: Browse 240+ game server templates with search and filtering
- **Advanced Search**: Filter by name, description, or game type
- **Pagination**: Handle large template collections efficiently
- **Template Preview**: View full template details including variables, commands, and Docker images
- **One-Click Apply**: Apply templates to servers with a single click

### 📊 Version Management
- **Version History**: Track every template update with commit hashes
- **Changelog View**: See what changed between template versions
- **Rollback Support**: Revert to previous template versions if needed

### 🛠️ Custom Templates
- **Template Creator**: Build custom templates in Ptero-Eggs format
- **Variable Editor**: Define environment variables with validation rules
- **Docker Images**: Specify Docker images for server containers
- **Command Builder**: Configure startup and stop commands

### 🔀 Migration Tools
- **Template Comparison**: Side-by-side diff of two templates
- **Unified Diff View**: See exact changes between templates
- **Bulk Migration**: Migrate multiple servers to new templates at once
- **Progress Tracking**: Monitor migration progress with detailed logging

## Installation

### 1. Database Migration

Run the database migration to create required tables:

```bash
cd /home/runner/work/panel/panel
source venv/bin/activate  # if using virtualenv
flask db upgrade
# or
python3 migrations_init.py
```

This creates:
- `ptero_eggs_update_metadata` - Sync status tracking
- `ptero_eggs_template_version` - Template version history

### 2. Initial Sync

Perform the first sync to import templates:

```bash
# Via Web UI
Navigate to: /admin/ptero-eggs/browser
Click: "Sync Templates"

# Or via Python
python3 << 'EOF'
from app import app, User
from ptero_eggs_updater import PteroEggsUpdater

with app.app_context():
    admin = User.query.filter_by(role='system_admin').first()
    updater = PteroEggsUpdater()
    stats = updater.sync_templates(admin.id)
    print(stats)
EOF
```

### 3. Configure Auto-Updates (Optional)

#### Option A: Systemd Timer

Create `/etc/systemd/system/ptero-eggs-sync.service`:
```ini
[Unit]
Description=Ptero-Eggs Template Sync
After=network.target

[Service]
Type=oneshot
User=panel
WorkingDirectory=/home/panel/panel
ExecStart=/home/panel/panel/venv/bin/python3 -c "from tasks import run_ptero_eggs_sync; run_ptero_eggs_sync()"
```

Create `/etc/systemd/system/ptero-eggs-sync.timer`:
```ini
[Unit]
Description=Daily Ptero-Eggs Template Sync
Requires=ptero-eggs-sync.service

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ptero-eggs-sync.timer
sudo systemctl start ptero-eggs-sync.timer
```

#### Option B: Crontab

```bash
crontab -e
# Add:
0 3 * * * cd /home/panel/panel && /home/panel/panel/venv/bin/python3 -c "from tasks import run_ptero_eggs_sync; run_ptero_eggs_sync()"
```

#### Option C: RQ Scheduler (Recommended)

If using Redis Queue for background tasks:

```python
from rq_scheduler import Scheduler
from redis import Redis
from tasks import run_ptero_eggs_sync

redis_conn = Redis()
scheduler = Scheduler(connection=redis_conn)

# Schedule daily at 3 AM
scheduler.cron(
    "0 3 * * *",
    func=run_ptero_eggs_sync,
    queue_name="default"
)
```

## Usage

### Web Interface

#### Browse Templates
1. Navigate to `/admin/ptero-eggs/browser`
2. Use search box to find specific games
3. Filter by game type using dropdown
4. Sort by name, game type, or update date
5. Click "Preview" to see full template details

#### Apply Template to Server
1. From template browser, click "Apply" on desired template
2. Select target server from dropdown
3. Confirm application
4. New configuration version is created for the server

#### Compare Templates
1. From template browser, click "Compare" icon on first template
2. Click "Compare" icon on second template
3. View side-by-side comparison with:
   - Startup commands
   - Variables and defaults
   - Docker images
   - Unified diff of JSON

#### Create Custom Template
1. Navigate to `/admin/ptero-eggs/create-custom`
2. Fill in basic information (name, game type, description)
3. Configure startup and stop commands
4. Add environment variables with:
   - Name and display name
   - Description and default value
   - User visibility and editability
   - Validation rules
5. Add Docker images
6. Optionally configure installation script
7. Add feature tags
8. Preview JSON before creating
9. Click "Create Template"

#### Bulk Migration
1. Navigate to `/admin/ptero-eggs/migrate`
2. Select multiple servers from list
3. Choose target Ptero-Eggs template
4. Click "Start Migration"
5. Monitor progress in real-time
6. Review results showing success/failure for each server

### Manual Sync
```bash
# Command line
python3 << 'EOF'
from tasks import run_ptero_eggs_sync
result = run_ptero_eggs_sync()
print(f"Success: {result['ok']}")
EOF

# Web UI
Visit /admin/ptero-eggs/browser and click "Sync Templates"
```

### API Usage

#### List Servers
```bash
curl -X GET http://localhost:8080/api/servers/list \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

#### Trigger Sync
```bash
curl -X POST http://localhost:8080/admin/ptero-eggs/sync \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

#### Get Template Preview
```bash
curl -X GET http://localhost:8080/admin/ptero-eggs/template/123/preview \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

#### Apply Template
```bash
curl -X POST http://localhost:8080/admin/ptero-eggs/apply/TEMPLATE_ID/SERVER_ID \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

## Architecture

### Components

1. **ptero_eggs_updater.py**
   - `PteroEggsUpdater`: Main sync engine
   - `PteroEggsUpdateMetadata`: Database model for sync status
   - `PteroEggsTemplateVersion`: Database model for version history

2. **routes_config.py**
   - 9 new routes for Ptero-Eggs management
   - Authentication helpers
   - API endpoints

3. **tasks.py**
   - `run_ptero_eggs_sync()`: Background task for auto-updates

4. **Templates**
   - `admin_ptero_eggs_browser.html`: Main browser interface
   - `admin_ptero_eggs_compare.html`: Template comparison
   - `admin_ptero_eggs_migrate.html`: Bulk migration tool
   - `admin_ptero_eggs_create.html`: Custom template creator

### Database Schema

#### ptero_eggs_update_metadata
```sql
CREATE TABLE ptero_eggs_update_metadata (
    id INTEGER PRIMARY KEY,
    repository_url VARCHAR(255),
    last_sync_at DATETIME,
    last_commit_hash VARCHAR(64),
    last_commit_message TEXT,
    last_sync_status VARCHAR(32),
    last_error_message TEXT,
    total_templates_imported INTEGER,
    templates_updated INTEGER,
    templates_added INTEGER,
    created_at DATETIME,
    updated_at DATETIME
);
```

#### ptero_eggs_template_version
```sql
CREATE TABLE ptero_eggs_template_version (
    id INTEGER PRIMARY KEY,
    template_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    commit_hash VARCHAR(64),
    template_data_snapshot TEXT NOT NULL,
    changes_summary TEXT,
    imported_at DATETIME,
    is_current BOOLEAN DEFAULT 1,
    FOREIGN KEY (template_id) REFERENCES config_template(id)
);
```

### Data Flow

1. **Auto-Sync Process**:
   ```
   Cron/Timer → run_ptero_eggs_sync() → PteroEggsUpdater.sync_templates()
      → clone_or_update_repository()
      → find_egg_files()
      → import_or_update_template() for each file
      → Update metadata
      → Send Discord notification
   ```

2. **Template Application**:
   ```
   User → Browser UI → Apply Template → API Route
      → ConfigManager.create_version()
      → Update server config
      → Store template reference
   ```

3. **Version Tracking**:
   ```
   Template Update → Check if changed
      → Create PteroEggsTemplateVersion entry
      → Mark previous version as not current
      → Update ConfigTemplate
   ```

## Testing

Run the test suite:

```bash
# All tests
python -m pytest tests/test_ptero_eggs_features.py -v

# Specific tests
python -m pytest tests/test_ptero_eggs_features.py -k "updater" -v
python -m pytest tests/test_ptero_eggs_features.py -k "metadata" -v
```

Test coverage includes:
- Database models (metadata, version tracking)
- PteroEggsUpdater class methods
- Repository clone and update operations
- Background task integration
- Route registration

## Troubleshooting

### Sync Fails with Git Error
```bash
# Ensure git is installed
git --version

# Check repository access
git ls-remote https://github.com/Ptero-Eggs/game-eggs.git

# Manually clone to test
git clone https://github.com/Ptero-Eggs/game-eggs.git /tmp/test-eggs
```

### Templates Not Appearing
```bash
# Check sync status
python3 << 'EOF'
from app import app
from ptero_eggs_updater import PteroEggsUpdater

with app.app_context():
    updater = PteroEggsUpdater()
    status = updater.get_sync_status()
    print(status)
EOF

# Check database
sqlite3 instance/panel.db "SELECT COUNT(*) FROM config_template WHERE name LIKE '%(Ptero-Eggs)%';"
```

### Authentication Errors
See [AUTH_PATTERN_UPDATE.md](AUTH_PATTERN_UPDATE.md) for details on authentication pattern that needs to be applied throughout routes_config.py.

### Database Migration Issues
```bash
# Check current migration version
flask db current

# Force upgrade
flask db upgrade head

# Or manually run migration
python3 migrations/versions/add_ptero_eggs_tracking.py
```

## Security Considerations

1. **Admin Only**: All management routes require system admin role
2. **CSRF Protection**: All forms include CSRF tokens
3. **Input Validation**: Custom template creation validates all inputs
4. **Session Auth**: Uses secure session-based authentication
5. **Git Operations**: Repository cloning uses HTTPS (no credentials stored)
6. **SQL Injection**: All queries use SQLAlchemy ORM (parameterized queries)

## Performance

- **Pagination**: Browser supports 20 templates per page (configurable)
- **Lazy Loading**: Templates loaded on-demand
- **Caching**: Sync status cached in database
- **Background Jobs**: Long-running operations use background tasks
- **Bulk Operations**: Optimized for batch processing

## Contributing

When adding new features:

1. Follow existing code patterns
2. Add tests to `tests/test_ptero_eggs_features.py`
3. Update this README
4. Ensure security best practices

## License

Same as panel project license.

## Credits

- Ptero-Eggs templates from https://github.com/Ptero-Eggs/game-eggs
- Panel project: https://github.com/phillgates2/panel
