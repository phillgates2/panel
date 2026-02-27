# Panel Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Python Version Error
```
ERROR: Python 3.8+ required
```
**Solution:**
```bash
python3 --version  # Check version
# Install Python 3.11
sudo apt update && sudo apt install python3.11 python3.11-venv
```

#### Permission Denied During Installation
```
Permission denied: '/opt/panel'
```
**Solution:**
```bash
# Install to user directory instead
bash <(curl -fsSL ...) --dir ~/panel

# Or use sudo for system-wide install
sudo bash <(curl -fsSL ...)
```

#### Missing Dependencies
```
ModuleNotFoundError: No module named 'flask'
```
**Solution:**
```bash
cd /path/to/panel
source venv/bin/activate
pip install -r requirements.txt
```

### Database Issues

#### Database Connection Failed
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Check PostgreSQL service:
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

2. Verify connectivity and credentials:
```bash
psql -h 127.0.0.1 -p 5432 -U paneluser -d paneldb -c 'SELECT 1'
```

3. Check firewall (if connecting remotely):
```bash
sudo ufw allow 5432/tcp
```

Note: Panel is PostgreSQL-only; SQLite is not supported.

#### Database Migration Failed
```
alembic.util.exc.CommandError: Can't locate revision
```

**Solution:**
```bash
# Reset migrations
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Database Manager Issues

#### Query Timeout
```
Query execution timeout (30 seconds)
```

**Solutions:**
1. Add WHERE clause to limit rows:
```sql
-- Instead of
SELECT * FROM large_table;

-- Use
SELECT * FROM large_table WHERE created_at > '2025-01-01' LIMIT 1000;
```

2. Add indexes:
```sql
CREATE INDEX idx_created_at ON large_table(created_at);
```

3. Break into smaller queries:
```sql
-- Process in chunks
SELECT * FROM large_table WHERE id BETWEEN 1 AND 10000;
SELECT * FROM large_table WHERE id BETWEEN 10001 AND 20000;
```

#### Rate Limit Exceeded
```
Rate limit exceeded. Maximum 30 queries per minute.
```

**Solutions:**
1. Wait 60 seconds before retrying
2. Optimize queries to reduce count
3. Use batch operations
4. Contact admin to increase limit

#### Permission Denied
```
403 Forbidden: Insufficient permissions
```

**Solutions:**
1. Check user role:
```sql
SELECT email, role FROM user WHERE email = 'your@email.com';
```

2. Update role (as admin):
```sql
UPDATE user SET role = 'system_admin' WHERE email = 'your@email.com';
```

3. Login with admin account

### Application Issues

#### Port Already in Use
```
OSError: [Errno 98] Address already in use
```

**Solutions:**
1. Find process using port:
```bash
lsof -i :8080
# or
netstat -tulpn | grep 8080
```

2. Kill the process:
```bash
kill -9 <PID>
```

3. Use different port:
```bash
PANEL_PORT=8081 python app.py
```

#### Redis Connection Failed
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solutions:**
1. Start Redis:
```bash
sudo systemctl start redis
```

2. Check Redis status:
```bash
redis-cli ping  # Should return PONG
```

3. Disable Redis (use in-memory fallback):
```bash
# In config
PANEL_REDIS_URL=''
```

#### Template Not Found
```
jinja2.exceptions.TemplateNotFound: admin_tools.html
```

**Solutions:**
1. Verify templates directory:
```bash
ls -la templates/
```

2. Check file permissions:
```bash
chmod 644 templates/*.html
```

3. Reinstall:
```bash
git pull origin main
```

### Performance Issues

#### Slow Page Load
**Diagnosis:**
```bash
# Enable debug mode
export FLASK_DEBUG=1
export FLASK_ENV=development
python app.py
```

**Solutions:**
1. Enable caching:
```python
# Add to config
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/1'
```

2. Optimize database queries:
```sql
EXPLAIN SELECT * FROM your_query;
```

3. Add database indexes:
```sql
CREATE INDEX idx_user_email ON user(email);
```

#### High Memory Usage
**Diagnosis:**
```bash
ps aux | grep python
htop
```

**Solutions:**
1. Reduce worker count:
```bash
# In gunicorn config
workers = 2  # Instead of 4
```

2. Enable garbage collection:
```python
import gc
gc.collect()
```

3. Restart application:
```bash
sudo systemctl restart panel-gunicorn
```

### Security Issues

#### CSRF Token Missing
```
400 Bad Request: CSRF token missing
```

**Solutions:**
1. Ensure form includes token:
```html
<input type="hidden" name="csrf_token" value="{{ session.csrf_token }}">
```

2. Check session configuration:
```python
SECRET_KEY = 'your-secret-key'  # Must be set
```

3. Clear browser cookies

#### Captcha Not Loading
**Solutions:**
1. Check Pillow installation:
```bash
pip install --upgrade Pillow
```

2. Verify font files exist:
```bash
ls -la /usr/share/fonts/truetype/
```

3. Disable captcha for testing:
```bash
export PANEL_DISABLE_CAPTCHA=true
```

### Logging and Debugging

#### Enable Debug Logging
```bash
# In environment or config
LOG_LEVEL=DEBUG
FLASK_DEBUG=1
```

#### View Application Logs
```bash
# Systemd service logs
sudo journalctl -u panel-gunicorn -f

# Application logs
tail -f /var/log/panel/app.log

# Audit logs
tail -f instance/audit_logs/query_audit.jsonl
```

#### Enable Query Logging
```python
# In config
SQLALCHEMY_ECHO = True  # Log all SQL queries
```

### Backup and Recovery

#### Backup Database
Panel is PostgreSQL-only.

**PostgreSQL:**
```bash
pg_dump -h 127.0.0.1 -p 5432 -U paneluser paneldb | gzip > paneldb_backup_$(date +%Y%m%d).sql.gz
```

#### Restore Database
**PostgreSQL:**
```bash
gunzip -c paneldb_backup_20251116.sql.gz | psql -h 127.0.0.1 -p 5432 -U paneluser -d paneldb
```

### Network Issues

#### Cannot Access from Remote Host
**Solutions:**
1. Bind to all interfaces:
```python
app.run(host='0.0.0.0', port=8080)
```

2. Check firewall:
```bash
sudo ufw allow 8080/tcp
```

3. Verify Nginx configuration:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL Certificate Issues
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**
1. Renew certificate:
```bash
sudo certbot renew
```

2. Check certificate expiry:
```bash
sudo certbot certificates
```

3. Force renewal:
```bash
sudo certbot renew --force-renewal
```

## Getting Help

### Collect Debug Information
```bash
# System info
uname -a
python3 --version
pip list

# Service status
sudo systemctl status panel-gunicorn
sudo systemctl status postgresql
sudo systemctl status redis

# Logs
sudo journalctl -u panel-gunicorn --since "1 hour ago"
tail -n 100 /var/log/panel/app.log
```

### Report Issues
1. Check existing issues: https://github.com/phillgates2/panel/issues
2. Collect debug information
3. Create new issue with:
   - Panel version
   - Operating system
   - Error messages
   - Steps to reproduce
   - Logs

### Community Support
- GitHub Discussions
- Issue Tracker
- Documentation: README.md, docs/

## Preventive Maintenance

### Regular Tasks
```bash
# Weekly
- Check disk space: df -h
- Review logs for errors
- Backup database

# Monthly
- Update dependencies: pip install --upgrade -r requirements.txt
- Review security updates
- Clean old log files

# Quarterly
- Review user permissions
- Audit database performance
- Update SSL certificates
```
