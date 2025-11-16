# Panel — Modern Game Server Management Platform

**🎮 OZ Panel**  
Modern Flask-based ET: Legacy server management with optimized user experience and enterprise-ready features.

## ✨ **Key Features**

### **🔐 Enhanced Security & Authentication**
- **Ultra-Compact Captcha System** - Optimized 50x25 pixel captcha with quality filters
- **Advanced Authentication** - Secure login/register/password reset flows
- **Role-Based Access Control** - Admin and user permission management
- **Audit Logging** - Comprehensive security event tracking

### **🗄️ Integrated Database Management**
- **Built-in phpMyAdmin** - Complete database management within Panel
- **No External Dependencies** - No separate web server or phpMyAdmin installation needed
- **Secure Access** - Admin-only authentication with session management
- **Full SQL IDE** - Query interface, table browser, CSV export
- **Cross-Database Support** - Works with SQLite and MySQL/MariaDB

### **🎨 Modern User Interface**
- **Professional Design** - Glass morphism effects with gradient backgrounds
- **Responsive Layout** - Mobile-friendly dashboard and forms
- **Theme System** - Customizable CSS with logo support
- **Accessibility** - WCAG compliant navigation and interactions

### **🛠️ Server Management**
- **RCON Integration** - Direct game server communication
- **Multi-Server Support** - Manage multiple ET: Legacy instances
- **Configuration Management** - Centralized server settings
- **Real-Time Status** - Live server monitoring and health checks

### **🚀 Development Features**
- **Flask Backend** - Modern Python web framework
- **SQLite/MariaDB Support** - Flexible database configurations
- **Virtual Environment** - Clean dependency management
- **Systemd Integration** - Production service management

## ⚡ **Quick Start**

### **One-Command Installation**

The Panel installer now supports comprehensive command-line options for flexible deployment:

```bash
# Interactive installation (default - recommended)
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)

# Quick SQLite-only installation (development)
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --sqlite-only

# Full installation with all components (production)
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --full

# Custom installation directory
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --dir /opt/panel

# Install specific branch
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --branch develop

# Non-interactive with MariaDB
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --non-interactive --db-type mariadb

# Skip specific components
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --skip-nginx --skip-ssl

# View all options
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --help
```

**📋 Installation Options:**
- `--help` - Show detailed usage information
- `--dir DIR` - Custom installation directory
- `--branch BRANCH` - Install specific git branch
- `--db-type TYPE` - Pre-select database (sqlite/mariadb)
- `--skip-mariadb` - Skip MariaDB installation
- `--skip-phpmyadmin` - Skip phpMyAdmin installation (use built-in instead)
- `--skip-redis` - Skip Redis installation
- `--skip-nginx` - Skip Nginx configuration
- `--skip-ssl` - Skip SSL/Let's Encrypt setup
- `--non-interactive` - Run without prompts (use defaults)
- `--sqlite-only` - Quick SQLite-only setup
- `--full` - Complete installation with all components
- `--uninstall` - Uninstall Panel and services

### **One-Command Uninstallation**
```bash
# Uninstall Panel completely
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --uninstall

# Uninstall from custom directory
bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh) --dir /opt/panel --uninstall
```

The uninstaller automatically removes:
- 🗂️ **Installation Directory** - Complete Panel installation
- 🔧 **System Services** - Systemd services (gunicorn, workers)  
- 🌐 **Nginx Configuration** - Reverse proxy and SSL configs
- 👤 **System User** - Optional panel user removal (interactive prompt)
- 📋 **Service Registration** - All systemd service files
- 🔄 **Service Reload** - Automatic systemd daemon reload and nginx restart

**Safety Features:**
- ⚠️ **Confirmation Required** - Interactive confirmation before removal
- 📊 **Preview Changes** - Shows what will be removed before proceeding
- 🛡️ **Graceful Cleanup** - Stops services safely before removal
- 📝 **Preserves Logs** - Database backups and logs remain in `/var/log/panel`

**🎯 Interactive Configuration Options:**
- **Installation Mode:** Development, Production, or Custom
- **Database Setup:** SQLite (quick) or MariaDB (production)
- **Database Management:** Embedded phpMyAdmin-like interface (no external installation needed)
- **Admin User:** Username, email, and password
- **Application Settings:** Host, port, debug mode, CAPTCHA
- **Production Services:** Nginx, SSL certificates, systemd
- **Optional Features:** Redis, Discord webhooks, ML dependencies

The installer automatically:
- ✅ Checks system requirements (Python 3.8+, Git, Curl)
- ✅ Guides you through interactive configuration
- ✅ Installs system dependencies based on your choices
- ✅ Sets up Python virtual environment
- ✅ Creates database and admin user
- ✅ Configures production services (nginx, SSL, systemd)
- ✅ Generates secure environment configuration
- ✅ Sets up integrated database management interface

### **Manual Installation**
```bash
# Clone repository
git clone https://github.com/phillgates2/panel.git
cd panel

# Use the built-in installer
./panel.sh install

# Or install manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run in development mode with SQLite
PANEL_USE_SQLITE=1 python app.py

# Access at: http://localhost:8080
```

### **Management Commands**
```bash
./panel.sh install      # Full installation with setup wizard
./panel.sh start        # Start development server
./panel.sh start-prod   # Start production server  
./panel.sh status       # Check service health
./panel.sh update       # Update installation
./panel.sh uninstall    # Remove installation
```

### **Production Installation**

#### **Automated Setup**
```bash
# Install to production directory
sudo PANEL_INSTALL_DIR=/opt/panel bash <(curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/getpanel.sh)

# Or clone and run installer
git clone https://github.com/phillgates2/panel.git /opt/panel
cd /opt/panel
sudo ./panel.sh install
```

#### **Manual Production Setup**

1. **Install System Dependencies**
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx mariadb-server git curl
```

2. **Setup Application**
```bash
# Create installation directory
sudo mkdir -p /opt/panel
cd /opt/panel

# Clone repository
sudo git clone https://github.com/phillgates2/panel.git .
sudo ./panel.sh install
```

The installer will guide you through:
- Python virtual environment setup
- Database configuration (MariaDB/SQLite)
- Admin user creation
- SSL certificate setup
- Systemd service configuration
- Nginx reverse proxy setup

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Database Configuration
PANEL_DB_USER=your_db_user          # MariaDB username
PANEL_DB_PASS=your_db_password      # MariaDB password  
PANEL_DB_HOST=127.0.0.1             # Database host
PANEL_DB_NAME=panel                 # Database name
PANEL_USE_SQLITE=1                  # Use SQLite for development

# Security
PANEL_SECRET_KEY=your-secret-key    # Flask secret key
PANEL_DISABLE_CAPTCHA=false         # Disable captcha (testing only)

# Optional Features
PANEL_DISCORD_WEBHOOK=webhook_url   # Discord notifications
```

### **Captcha System**
The panel features an optimized captcha system with:
- **Ultra-compact design** - 50x25 pixel images for seamless UI integration
- **Quality filters** - SMOOTH and SHARPEN filters for enhanced readability
- **Smart sizing** - Automatic font scaling based on character count
- **Security focused** - Excludes confusing characters (0, O, I, 1, L)

### **Integrated Database Management**

Panel includes a complete phpMyAdmin-like interface built directly into the application:

**✨ Features:**
- **🔍 Database Browser** - View all tables with structure and data
- **📝 SQL Query Interface** - Execute custom queries with real-time results
- **📊 Table Viewer** - Browse table data with pagination (50 rows per page)
- **📤 CSV Export** - Export individual tables as CSV files
- **🔒 Secure Access** - Admin-only with session authentication
- **🎨 Responsive Design** - Works on desktop and mobile devices

**🚀 Access:**
1. Login to Panel as admin (admin@localhost / admin123 by default)
2. Navigate to **Admin Tools** in the main menu
3. Click **🗄️ Database Manager**
4. Start managing your database!

**💡 Common Tasks:**
```sql
-- View all users
SELECT * FROM user LIMIT 10;

-- Count total records
SELECT COUNT(*) as total FROM user;

-- View game servers
SELECT * FROM game_server;

-- Check all tables (SQLite)
SELECT name FROM sqlite_master WHERE type='table';

-- Check all tables (MySQL/MariaDB)
SHOW TABLES;
```

**No external phpMyAdmin installation required!** Everything is integrated seamlessly within the Panel interface with proper security and authentication.

### **System Services**

#### **Gunicorn Service**
```bash
sudo cp deploy/panel-gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now panel-gunicorn.service
```

#### **Nginx Configuration**
```bash
sudo cp deploy/nginx_game_chrisvanek.conf /etc/nginx/sites-available/panel.conf
sudo ln -s /etc/nginx/sites-available/panel.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

#### **SSL Certificate**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🎮 **Game Server Integration**

### **ET: Legacy Server Setup**
```bash
# Copy service file
sudo cp deploy/etlegacy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now etlegacy.service
```

### **Server Utilities**

#### **Memory Monitoring (Memwatch)**
```bash
sudo cp deploy/memwatch.service /etc/systemd/system/
sudo cp deploy/memwatch.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now memwatch.timer
```

#### **Auto-deployment**
```bash
sudo cp deploy/autodeploy.service /etc/systemd/system/
sudo cp deploy/autodeploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now autodeploy.timer
```

### **Security & Permissions**

#### **Dedicated User Setup**
```bash
# Create panel user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin panel
sudo mkdir -p /opt/panel /var/log/panel
sudo chown -R panel:panel /opt/panel /var/log/panel
```

#### **Sudo Configuration**
```bash
# Allow controlled access for wrapper
echo "www-data ALL=(root) NOPASSWD: /opt/panel/bin/panel-wrapper *" | sudo tee /etc/sudoers.d/panel
```

### **Panel Wrapper**

Build the security wrapper for safe command execution:

```bash
# Build wrapper
cd tools
make
sudo make install

# Set secure permissions
sudo chown root:root /opt/panel/bin/panel-wrapper
sudo chmod 750 /opt/panel/bin/panel-wrapper
```

**Wrapper Commands:**
- `panel-wrapper autodeploy [url]` - Deploy server updates
- `panel-wrapper memwatch [pid_file]` - Monitor server memory

## 🔄 **Background Services**

### **Redis & Task Queue**
```bash
# Install Redis
sudo apt install redis-server
sudo systemctl enable --now redis

# Setup RQ worker
source venv/bin/activate
pip install -r requirements.txt
python run_worker.py
```

### **Worker Management**
```bash
# Install supervised worker
sudo cp deploy/rq-worker-supervised.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rq-worker-supervised.service

# Health monitoring
sudo cp deploy/check-worker.service /etc/systemd/system/
sudo cp deploy/check-worker.timer /etc/systemd/system/
sudo systemctl enable --now check-worker.timer
```

### **Log Management**
```bash
# Setup log rotation
sudo cp deploy/panel-logrotate.conf /etc/logrotate.d/panel
sudo mkdir -p /var/log/panel
sudo chown panel:panel /var/log/panel
```

## 🎨 **Customization**

### **Theme Editor**
- Access at `/admin/theme` (system admin required)
- Edit CSS in real-time with live preview
- Upload server logos and assets
- Mobile-responsive design tools

### **Server Logos**
- Upload via Theme Editor interface  
- Served at `/theme_asset/<filename>`
- Secure filename sanitization
- Multiple format support

## 🧪 **Testing**

```bash
# Install test dependencies
pip install -r requirements.txt
python -m playwright install

# Run tests
python -m pytest tests/
python -m playwright test
```

## 📚 **API Reference**

### **RCON Integration**
- Direct ET: Legacy server communication
- Command validation and sanitization
- Real-time response handling
- Connection pooling and timeout management

### **Admin Features**
- User management and role assignment
- Server configuration and monitoring
- Audit log viewing and export
- Task queue monitoring and management
- **Integrated Database Management** - Full phpMyAdmin functionality built-in
- **SQL Query Interface** - Execute queries with syntax highlighting
- **Database Browser** - View and export table data
- **No External Tools Required** - All database management within Panel

## 🚀 **Deployment**

### **Docker Support** (Optional)
```bash
# Build container
docker build -t panel .

# Run with SQLite
docker run -p 8080:8080 -e PANEL_USE_SQLITE=1 panel

# Run with MariaDB
docker run -p 8080:8080 \
  -e PANEL_DB_HOST=mariadb-host \
  -e PANEL_DB_USER=user \
  -e PANEL_DB_PASS=pass \
  -e PANEL_DB_NAME=panel \
  panel
```

## 📋 **Requirements**

- **Python**: 3.8+
- **Database**: MariaDB 10.3+ or SQLite 3.31+
- **System**: Linux (Ubuntu/Debian/Alpine)
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ available space

## 🔗 **Links**

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Documentation**: See `README_DEV.md` for development details
- **Changelog**: See `CHANGELOG.md` for version history

---

**Panel** - Modern game server management made simple. Built with Flask, optimized for ET: Legacy, designed for scalability.

