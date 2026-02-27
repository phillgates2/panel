<!-- markdownlint-disable MD022 MD031 MD032 MD036 MD040 MD024 MD034 MD060 -->

# Cloud-Init README

> Important: Panel is PostgreSQL-only. Any SQLite cloud-init configs or variables mentioned below are legacy and are not supported by the current application/runtime.

## Summary: `\cloud-init` Folder Analysis & Fixes Complete ?

### **Overall Status: ?? IMPROVED - Enhanced versions created**

---

## What Was Fixed

### ? **Security Vulnerabilities Addressed**

1. **Password Generation** - Instead of hardcoded passwords:
   ```yaml
   # Generates secure random passwords
   export PANEL_ADMIN_PASS=$(openssl rand -base64 32)
   # Saves to /root/panel-credentials.txt with restricted permissions
   ```

2. **Firewall Configuration** - UFW enabled with proper rules:
   ```yaml
   - Allow SSH (port 22)
   - Allow HTTP (port 80)
   - Allow HTTPS (port 443)
   - Deny all other incoming traffic
   ```

3. **SSH Hardening** - Security improvements:
   ```yaml
   - Root login disabled
   - Password authentication disabled
   - Public key authentication required
   ```

4. **Brute Force Protection** - fail2ban configured:
   ```yaml
   - Monitors Panel application logs
   - Bans IPs after 5 failed attempts
   - 1-hour ban duration
   ```

5. **Automatic Security Updates** - Unattended upgrades enabled:
   ```yaml
   - Security patches applied automatically
   - Kernel updates included
   - System reboots not automatic (manual control)
   ```

### ? **Reliability Improvements**

1. **Error Handling** - Comprehensive error checking:
   ```bash
   set -euo pipefail  # Fail on errors
   # Verify each critical step
   if [ ! -f "$PANEL_INSTALL_DIR/app.py" ]; then
     echo "? Installation failed"
     exit 1
   fi
   ```

2. **Logging** - Enhanced logging throughout:
   ```yaml
   - Deployment log: /var/log/panel-deployment.log
   - Installation log: /opt/panel/install.log
   - Application logs: /opt/panel/logs/
   ```

3. **Monitoring** - Automatic service monitoring:
   ```yaml
   # Cron job restarts Panel if it stops
   */5 * * * * systemctl is-active --quiet panel || systemctl restart panel
   ```

4. **Backups** - Automated daily backups:
   ```yaml
   # PostgreSQL: Daily pg_dump backup
   ```

### ? **PostgreSQL Enhancements** (for postgres version)

1. **Complete Database Setup**:
   ```sql
   - Create paneluser with secure password
   - Create panel_db database
   - Grant all privileges
   - Configure pg_hba.conf for local connections
   ```

2. **Performance Tuning**:
   ```yaml
   - shared_buffers optimized based on RAM
   - effective_cache_size calculated
   - Connection pooling configured
   - WAL settings optimized
   ```

3. **Connection Validation**:
   ```bash
   # Test DB connection after install
   python -c "from app import db; print('? Connected')"
   ```

---

## Files in This Folder

| File | Purpose | Status |
|------|---------|--------|
| `ubuntu-user-data.yaml` | Legacy SQLite config | ?? Legacy (not supported) |
| `ubuntu-postgres-user-data.yaml` | Original PostgreSQL config | ?? Basic, needs improvements |
| `ubuntu-user-data-enhanced.yaml` | Legacy SQLite config | ?? Legacy (not supported) |
| `ubuntu-postgres-user-data-enhanced.yaml` | **NEW** - Production-ready PostgreSQL | ? Recommended |
| `README.md` | This file | ? Complete guide |

---

## Quick Start

### For PostgreSQL (Supported)

```yaml
# Use: ubuntu-postgres-user-data-enhanced.yaml
# Resources: 2+ vCPUs, 4GB+ RAM
# Deploy time: ~15 minutes
```

---

## Configuration Variables

You can override these by setting environment variables in your cloud-init config:

```yaml
# Required (will be auto-generated if not provided)
PANEL_ADMIN_EMAIL=admin@yourdomain.com    # Admin email address
PANEL_ADMIN_PASS=SecurePassword123!       # Admin password

# Optional
PANEL_INSTALL_DIR=/opt/panel              # Installation directory

# PostgreSQL
PANEL_DB_USER=paneluser                   # Database username
PANEL_DB_NAME=panel_db                    # Database name
PANEL_DB_PASS=SecureDBPassword123!       # Database password
```

### Example with Custom Variables

```yaml
#cloud-config
# ... (include full enhanced config here)

# Add before runcmd:
environment:
  PANEL_ADMIN_EMAIL: "admin@example.com"
  PANEL_INSTALL_DIR: "/var/www/panel"
```

---

## Cloud Provider Guides

### AWS EC2

1. **Launch Instance**:
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t2.small (minimum)
   - Security group: Allow ports 22, 80, 443

2. **User Data**:
   - Expand "Advanced Details"
   - Scroll to "User data"
   - Paste contents of enhanced yaml file

3. **Monitor Deployment**:
   ```bash
   ssh ubuntu@YOUR_IP
   sudo cat /var/log/cloud-init-output.log
   tail -f /var/log/panel-deployment.log
   ```

### Google Cloud Platform

1. **Create VM**:
   - Image: Ubuntu 22.04 LTS
   - Machine type: e2-small (minimum)
   - Firewall: Allow HTTP, HTTPS

2. **Add User Data**:
   - Click "Management, security, disks, networking, sole tenancy"
   - Under "Management" ? "Automation"
   - Paste yaml contents in "Startup script"

3. **Check Status**:
   ```bash
   gcloud compute ssh YOUR_INSTANCE_NAME
   sudo cat /var/log/cloud-init-output.log
   ```

### Microsoft Azure

1. **Create Virtual Machine**:
   - Image: Ubuntu Server 22.04 LTS
   - Size: Standard_B1s (minimum)
   - Public inbound ports: 22, 80, 443

2. **Custom Data**:
   - Go to "Advanced" tab
   - Paste yaml in "Custom data" field

3. **Monitor**:
   ```bash
   ssh azureuser@YOUR_IP
   sudo cat /var/log/cloud-init-output.log
   ```

### DigitalOcean

1. **Create Droplet**:
   - Distribution: Ubuntu 22.04 (LTS) x64
   - Plan: Basic ($6/mo minimum)
   - Additional options: Enable monitoring

2. **User Data**:
   - Check "User data" box
   - Paste yaml contents

3. **Check Progress**:
   ```bash
   ssh root@YOUR_IP
   cat /var/log/cloud-init-output.log
   ```

---

## Monitoring Deployment

### Check Overall Status

```bash
# Cloud-init status
sudo cloud-init status

# Detailed status
sudo cloud-init status --long

# Wait for completion
sudo cloud-init status --wait
```

### View Logs

```bash
# Cloud-init output (everything)
sudo cat /var/log/cloud-init-output.log

# Panel deployment log
sudo cat /var/log/panel-deployment.log

# Installation log
sudo cat /opt/panel/install.log

# Application logs
sudo tail -f /opt/panel/logs/*.log

# System logs
sudo journalctl -xe
```

### Check Services

```bash
# Panel service
sudo systemctl status panel

# PostgreSQL (if using)
sudo systemctl status postgresql

# Nginx
sudo systemctl status nginx

# Firewall
sudo ufw status verbose

# fail2ban
sudo fail2ban-client status
```

---

## Post-Deployment Steps

### 1. Retrieve Credentials

```bash
# Admin credentials
sudo cat /root/panel-credentials.txt

# Database credentials (PostgreSQL only)
sudo cat /root/postgres-credentials.txt
```

### 2. Configure DNS

Point your domain to the server:
```
A    @              YOUR_SERVER_IP
A    www            YOUR_SERVER_IP
AAAA @              YOUR_IPv6_IP      (if available)
```

### 3. Setup SSL Certificate

```bash
# Install certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### 4. Update Admin Password

```bash
# First login, change the auto-generated password
# Go to: Settings ? Change Password
```

### 5. Configure Backups

Backups are automated, but verify:

```bash
# Check backup directory
ls -lh /opt/panel/backups/

# PostgreSQL
ls -lh /opt/panel/backups/panel_db_*.sql.gz
```

### 6. Test Monitoring

```bash
# Stop Panel service
sudo systemctl stop panel

# Wait 5 minutes (monitoring cron runs every 5 min)
# Service should auto-restart

# Check logs
sudo journalctl -u panel -n 20
```

---

## Security Checklist

After deployment, verify:

- [ ] **Firewall active**: `sudo ufw status`
- [ ] **fail2ban running**: `sudo systemctl status fail2ban`
- [ ] **SSH root login disabled**: `grep PermitRootLogin /etc/ssh/sshd_config`
- [ ] **Password authentication disabled**: `grep PasswordAuthentication /etc/ssh/sshd_config`
- [ ] **SSL certificate installed**: `sudo certbot certificates`
- [ ] **Automatic updates enabled**: `sudo systemctl status unattended-upgrades`
- [ ] **Default passwords changed**: Check admin panel
- [ ] **Backups working**: `ls /opt/panel/backups/`
- [ ] **Monitoring active**: `crontab -l`

---

## Troubleshooting

### Deployment Failed

```bash
# Check cloud-init logs
sudo cat /var/log/cloud-init-output.log | grep -i error

# Check deployment log
sudo cat /var/log/panel-deployment.log

# Check installer log
sudo cat /opt/panel/install.log

# Re-run deployment script manually
sudo /tmp/deploy-panel.sh
```

### Panel Service Won't Start

```bash
# Check service status
sudo systemctl status panel

# View recent logs
sudo journalctl -u panel -n 50

# Check application directly
cd /opt/panel
source venv/bin/activate
python app.py
```

### Database Connection Failed (PostgreSQL)

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -d panel_db -c '\dt'

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*-main.log

# Verify credentials
sudo cat /root/postgres-credentials.txt
```

### Cannot Access Panel (Port Issues)

```bash
# Check if Panel is listening
sudo netstat -tlnp | grep 5000

# Check firewall
sudo ufw status verbose

# Check cloud provider security groups
# Ensure ports 80, 443 are open
```

### SSL Certificate Failed

```bash
# Check DNS is pointing correctly
dig +short yourdomain.com

# Try manual certificate
sudo certbot certonly --standalone -d yourdomain.com

# Check Nginx configuration
sudo nginx -t

# View certbot logs
sudo cat /var/log/letsencrypt/letsencrypt.log
```

---

## Maintenance

### Update Panel

```bash
cd /opt/panel
source venv/bin/activate
git pull
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart panel
```

### Manual Backup

```bash
# PostgreSQL
sudo -u postgres pg_dump panel_db | gzip > /opt/panel/backups/manual_$(date +%Y%m%d).sql.gz
```

### View Logs

```bash
# Recent application logs
sudo tail -f /opt/panel/logs/app.log

# Recent errors
sudo grep -i error /opt/panel/logs/*.log

# System logs for Panel
sudo journalctl -u panel --since "1 hour ago"
```

### Security Audit

```bash
# Install lynis
sudo apt install lynis

# Run security audit
sudo lynis audit system

# Review recommendations
sudo cat /var/log/lynis.log
```

---

## Performance Tuning

### Legacy: SQLite (Not Supported)

SQLite-based tuning steps are intentionally omitted here because Panel is PostgreSQL-only.

### For PostgreSQL (Production)

Already tuned by cloud-init, but you can adjust:

```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/*/main/postgresql.conf

# Recommended settings are already applied:
# - shared_buffers = 25% of RAM
# - effective_cache_size = 75% of RAM
# - work_mem = 4MB
# - maintenance_work_mem = 6% of RAM

# Restart after changes
sudo systemctl restart postgresql
```

---

## Comparison: Original vs Enhanced

| Feature | Original | Enhanced |
|---------|----------|----------|
| **Password Security** | ? Hardcoded | ? Auto-generated |
| **Error Handling** | ? Basic logging | ? Comprehensive |
| **Firewall** | ? Not configured | ? UFW enabled |
| **SSH Hardening** | ? Default config | ? Hardened |
| **fail2ban** | ? Not installed | ? Configured |
| **Auto Updates** | ? Manual | ? Automatic |
| **PostgreSQL Setup** | ?? Incomplete | ? Complete |
| **Monitoring** | ? None | ? Auto-restart |
| **Backups** | ? Manual | ? Daily automated |
| **Logging** | ?? Basic | ? Comprehensive |
| **Verification** | ? None | ? Post-install checks |

---

## Files Created/Updated

### New Files ?
- `ubuntu-user-data-enhanced.yaml` - Legacy SQLite deployment (not supported)
- `ubuntu-postgres-user-data-enhanced.yaml` - Production-ready PostgreSQL deployment  
- `README.md` - This comprehensive guide
- `docs/CLOUD_INIT_ANALYSIS.md` - Detailed analysis report

### Original Files (Preserved)
- `ubuntu-user-data.yaml` - Legacy SQLite config (not supported)
- `ubuntu-postgres-user-data.yaml` - Original basic PostgreSQL config

---

## Recommendations

### For Development/Testing
? Use: `ubuntu-postgres-user-data-enhanced.yaml`
- PostgreSQL-only (supported)
- Use smaller VM sizes if this is just for testing

### For Production
? Use: `ubuntu-postgres-user-data-enhanced.yaml`
- Better performance
- Better scalability
- Better for multiple users
- Includes backups & monitoring

### Security Best Practices
1. ? Never commit credentials to git
2. ? Use cloud provider secrets management
3. ? Enable 2FA for cloud accounts
4. ? Regular security updates
5. ? Monitor logs for suspicious activity

---

## Support

### Documentation
- Analysis: `docs/CLOUD_INIT_ANALYSIS.md`
- This guide: `cloud-init/README.md`
- Project: https://github.com/phillgates2/panel

### Logs Locations
- Cloud-init: `/var/log/cloud-init-output.log`
- Deployment: `/var/log/panel-deployment.log`
- Installation: `/opt/panel/install.log`
- Application: `/opt/panel/logs/`

### Getting Help
1. Check logs (locations above)
2. Review troubleshooting section
3. Check Panel repository issues
4. Create new issue with logs

---

**Status**: ? **COMPLETE** - Enhanced configs ready for production use!

**Next Steps**:
1. Choose appropriate config (PostgreSQL)
2. Copy to cloud provider user-data
3. Launch instance
4. Wait 10-15 minutes
5. Follow post-deployment steps
