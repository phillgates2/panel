# Panel

**Modern web platform for managing ET: Legacy game servers with integrated CMS and community features**

A clean, secure Flask application with PostgreSQL database, user authentication, community forum, blog system, and a beautiful interface. Perfect for managing game servers with real-time monitoring, administrative tools, and community engagement.

---

## 🎯 What is This?

Panel is a comprehensive web-based control system for ET: Legacy game servers. It provides:
- User-friendly web interface with modern design
- **Community Forum** - Public discussions with role-based moderation
- **Blog System** - Share news and updates with your community
- Secure login system with CAPTCHA protection
- Database management tools
- Real-time server monitoring
- Background job processing
- Security features (rate limiting, audit logging)
- User management with granular permissions

---

## ✨ Key Features

### 🎮 Server Management
- Start/stop/restart game servers
- Real-time server monitoring
- Configure server settings via web UI
- Monitor player activity and statistics
- View and analyze server logs
- Multiple server support

### 💬 Community Forum
- **Public Access** - Anyone can view forum and threads
- **User Participation** - Registered users can create threads and post replies
- **Moderator Tools** - Pin important threads, lock discussions
- **Rich Content** - Markdown support for formatted posts
- **User Profiles** - Author attribution with avatars
- **Thread Management** - Edit, delete, organize discussions

### 📰 Blog System
- **Public Blog** - Share news, updates, and announcements
- **Homepage Integration** - Recent posts displayed on homepage
- **Admin Dashboard** - Create, edit, and manage blog posts
- **Draft/Publish Workflow** - Prepare content before going live
- **Markdown Support** - Rich text formatting
- **Author Attribution** - Posts linked to user accounts

### 👥 User Management
- **Role-Based Permissions**:
  - 👤 **User** - Basic forum access, can post and create threads
  - 🛡️ **Moderator** - Forum management (edit/delete posts, pin/lock threads)
  - 🔧 **Server Mod** - Game server moderation
  - 🖥️ **Server Admin** - Full server administration
  - ⚙️ **System Admin** - Complete system access
- Visual role management interface
- Audit logging for permission changes
- User activity tracking

### 🔒 Security
- Session-based authentication
- CSRF protection on all forms
- Password hashing (bcrypt)
- CAPTCHA verification
- Rate limiting to prevent abuse
- Comprehensive audit logging
- Role-based access control

---

## 🚀 Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

The installer will guide you through:
1. **Mode Selection**: Choose Development, Production, or Custom
2. **Database Setup**: PostgreSQL (recommended) or SQLite
3. **Network Config**: Set your domain/IP and port
4. **Admin Account**: Create your login credentials
5. **Services**: Optionally setup systemd, Nginx, and SSL

That's it! The installer handles everything automatically.

---

## 📖 Installation Modes Explained

### 🔧 Development Mode
**Best for**: Testing on your local machine

What you get:
- Debug mode ON (detailed error messages)
- Runs on port 8080
- Fast SQLite database
- No extra services needed
- Auto-starts when installation completes

Perfect for trying out Panel or developing features.

### 🏢 Production Mode
**Best for**: Running on a real server

What you get:
- Production-optimized settings
- PostgreSQL database (faster, more reliable)
- Systemd services (auto-restart if crashes)
- Nginx web server (better performance)
- SSL certificate support (HTTPS)
- Auto-starts on server reboot

Recommended for actual game server hosting.

### ⚙️ Custom Mode
**Best for**: Advanced users with specific needs

Pick and choose:
- Enable/disable individual features
- Mix development and production settings
- Control which services to install
- Fine-tune your setup

---

## 🎮 Using Panel

### First Time Access

After installation completes, open your browser:
```
http://localhost:8080
```

**If accessing from another computer:**
```
http://YOUR_SERVER_IP:8080
```

Login with the credentials you created during installation.

### Main Features

**Dashboard**
- Overview of your servers and system status
- Quick actions and controls
- Recent activity feed
- Access to admin tools

**Community Forum** (`/forum`)
- Browse and read threads (no login required)
- Create threads and post replies (login required)
- Moderator tools for managing discussions
- Pin important threads to the top
- Lock threads to prevent further replies
- Markdown formatting for rich content

**Blog** (`/cms/blog`)
- Read latest news and updates
- Recent posts featured on homepage
- Markdown-formatted articles
- Author information displayed

**Server Management**
- Start/stop game servers
- Configure server settings
- Monitor player activity
- View server logs in real-time
- Manage multiple servers

**Database Admin** (`/admin/database`)
- Browse database tables
- Run custom SQL queries
- Export data to CSV/JSON
- Built-in web interface
- System admin access only

**User Management** (`/admin/users`)
- View all registered users
- Change user roles and permissions
- Visual role hierarchy display
- Audit trail for role changes
- System admin access only

**Blog Management** (`/cms/admin/blog`)
- Create and edit blog posts
- Draft/publish workflow
- Manage post slugs and excerpts
- Delete outdated posts
- System admin access only

---

## 📚 Community Features Guide

### Using the Forum

**For Visitors (No Login Required)**
- Browse all forum threads
- Read discussions and posts
- View user profiles and post counts
- See pinned and locked threads

**For Registered Users**
1. **Create a Thread**:
   - Navigate to Forum
   - Click "✨ New Thread"
   - Enter title and content (Markdown supported)
   - Click "🚀 Create Thread"

2. **Post a Reply**:
   - Open any thread
   - Scroll to the reply form
   - Write your message (Markdown supported)
   - Click "📤 Post Reply"

3. **Edit Your Posts**:
   - Find your post in a thread
   - Click "✏️ Edit" button
   - Update content and save

**For Moderators**
- **Pin Threads**: Click 📌 to pin important discussions to the top
- **Lock Threads**: Click 🔒 to prevent new replies
- **Edit Any Post**: Use ✏️ button on any post
- **Delete Posts**: Use 🗑️ button to remove inappropriate content
- **Manage Threads**: Edit thread titles, toggle pin/lock status

### Using the Blog

**Reading Blog Posts**
- Visit `/cms/blog` to see all published posts
- Recent posts appear on the homepage
- Click post title to read full article
- Posts show author and publication date

**Creating Blog Posts (Admin Only)**
1. Login as system admin
2. Go to Dashboard → "📝 Blog Management"
3. Click "✨ New Post"
4. Fill in:
   - **Title**: Post headline
   - **Slug**: URL-friendly identifier (auto-generated)
   - **Excerpt**: Short preview (optional)
   - **Content**: Full article (Markdown supported)
   - **Publish**: Check to make public immediately
5. Click "✨ Create Post"

**Markdown Formatting**
Both forum and blog support Markdown:
```markdown
# Heading 1
## Heading 2
**bold text**
*italic text*
- Bullet list
1. Numbered list
[link text](https://example.com)
```

### Managing User Roles

**System Admin Access Required**

1. Navigate to Dashboard → "👥 User Management"
2. Find the user in the table
3. Select new role from dropdown:
   - 👤 **User** - Basic access
   - 🛡️ **Moderator** - Forum management
   - 🔧 **Server Mod** - Server moderation
   - 🖥️ **Server Admin** - Server administration
   - ⚙️ **System Admin** - Full system access
4. Click "Update Role"
5. Confirm if granting system admin

**Role Permissions**:
- **User**: Create forum threads, post replies, manage own content
- **Moderator**: All User permissions + edit/delete any post, pin/lock threads
- **Server Mod**: Server moderation capabilities
- **Server Admin**: Full server management
- **System Admin**: Complete system control, user management, blog management

---

## 🛠️ Managing Panel

### Starting Panel

**If auto-start is enabled**: Panel runs automatically!

**To start manually**:
```bash
cd ~/panel
source venv/bin/activate

# Start the services
python3 run_worker.py &  # Background jobs
python3 app.py           # Web interface
```

Access Panel at: `http://localhost:8080`

### Stopping Panel

```bash
# Stop all Panel processes
pkill -f "python.*app.py"
pkill -f "python.*run_worker.py"
```

**If using systemd**:
```bash
sudo systemctl stop panel-gunicorn
sudo systemctl stop rq-worker
```

### Viewing Logs

```bash
cd ~/panel

# See what's happening
tail -f logs/panel.log     # Main application
tail -f logs/worker.log    # Background jobs

# Check for errors
grep ERROR logs/panel.log
```

### Common Commands

```bash
cd ~/panel

# Check if Panel is running
ps aux | grep python3

# View status (if using systemd)
systemctl status panel-gunicorn

# Update Panel to latest version
git pull
pip install -r requirements.txt

# Run database migrations (if updating from older version)
python3 migrate_cms_forum.py

# Database backup
python3 scripts/backup_manager.py
```

### Database Migrations

When updating Panel, you may need to run migrations for new features:

**Forum and CMS Features** (v3.3.0+):
```bash
cd ~/panel
source venv/bin/activate
python3 migrate_cms_forum.py
```

This migration adds:
- BlogPost table for blog system
- Forum thread author tracking
- Thread pinning and locking
- User-based post authorship

The migration script is safe to run multiple times - it checks what's already migrated.

---

## 🔧 Troubleshooting

### Can't Connect to Panel

**Problem**: Browser shows "Connection refused" or timeout

**Solution**:
```bash
# 1. Is Panel running?
ps aux | grep "python3 app.py"

# 2. Is it listening on port 8080?
netstat -tlnp | grep 8080

# 3. Try connecting locally first
curl http://localhost:8080/

# 4. Check firewall (if accessing remotely)
sudo ufw allow 8080/tcp

# 5. Get your server's IP address
hostname -I

# 6. Try accessing via IP instead of localhost
```

### Redis Connection Error

**Problem**: Panel logs show "Connection refused" for Redis

**Solution**:
```bash
# Start Redis service
sudo systemctl start redis

# Enable Redis to start on boot
sudo systemctl enable redis

# If no systemd (Alpine/minimal systems)
redis-server --daemonize yes
```

### Database Connection Error

**Problem**: Can't connect to PostgreSQL

**Solution**:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l | grep panel
```

### Port Already in Use

**Problem**: Port 8080 is taken by another program

**Solution**:
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill that process
sudo kill [PID]

# Or change Panel's port in config.py
```

### Forum/Blog Pages Show Errors

**Problem**: Forum or blog pages return 500 errors after update

**Solution**:
```bash
# Run database migrations
cd ~/panel
source venv/bin/activate
python3 migrate_cms_forum.py

# Restart Panel
pkill -f "python3 app.py"
python3 app.py
```

### Can't Create Forum Posts

**Problem**: "Login required" message when trying to post

**Solution**:
- Forum viewing is public, but posting requires login
- Click "Login" in navigation
- Register an account if you don't have one
- After login, you'll be able to create threads and post replies

### Can't Pin or Lock Threads

**Problem**: Don't see moderator buttons in forum

**Solution**:
- Only moderators and system admins can pin/lock threads
- Login as system admin
- Go to Dashboard → User Management
- Change your role to "Moderator" or "System Admin"

### Blog Posts Not Showing on Homepage

**Problem**: Created blog posts but they don't appear

**Solution**:
- Check that posts are marked as "Published" (not Draft)
- In Blog Management, edit post and check the "Publish" checkbox
- Only published posts appear on homepage and public blog

---

## 🏗️ What's Under the Hood

### Technology Stack
- **Flask** - Python web framework
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Database (production)
- **SQLite** - Database (development)
- **Redis** - Background jobs and caching
- **Nginx** - Web server (production)
- **Gunicorn** - Application server (production)
- **Markdown** - Rich text formatting (forum & blog)
- **Bleach** - HTML sanitization

### Security Features
- Password hashing (bcrypt)
- CAPTCHA on login/registration
- Rate limiting (30 requests/minute)
- SQL injection protection (SQLAlchemy ORM)
- Security headers (CSP, HSTS)
- Audit logging for all admin actions
- CSRF protection on all forms
- Session-based authentication
- Role-based access control

### Database Schema
**Core Tables**:
- `user` - User accounts and authentication
- `server` - Game server configurations
- `audit_log` - Security and activity tracking

**Forum Tables**:
- `forum_thread` - Discussion threads with pin/lock status
- `forum_post` - User posts with author tracking

**CMS Tables**:
- `cms_page` - Static pages
- `cms_blog_post` - Blog articles with publication status

### Key Files
```
panel/
├── app.py                      # Main application & routes
├── install.sh                  # Automated installer
├── config.py                   # Configuration settings
├── migrate_cms_forum.py        # Database migrations
├── forum/
│   └── __init__.py             # Forum routes & models
├── cms/
│   └── __init__.py             # Blog routes & models
├── templates/
│   ├── base.html               # Base template
│   ├── index.html              # Homepage with blog posts
│   ├── forum/                  # Forum templates
│   └── cms/                    # Blog templates
├── static/
│   ├── css/style.css           # Main stylesheet
│   └── js/                     # JavaScript files
├── logs/                       # Application logs
└── instance/                   # Runtime data & SQLite DB
```

---

## 📚 Advanced Topics

### Environment Variables

Control Panel behavior without editing code:

```bash
# Development mode
export PANEL_USE_SQLITE=1
export PANEL_DEBUG=true

# Production database
export PANEL_DB_HOST=localhost
export PANEL_DB_NAME=panel
export PANEL_DB_USER=panel_user
export PANEL_DB_PASS=your_password

# Application settings
export PANEL_PORT=8080
export PANEL_DOMAIN=panel.example.com
```

### Non-Interactive Installation

For automated deployments:

```bash
# Development setup
PANEL_NON_INTERACTIVE=true \
PANEL_DEBUG=true \
PANEL_DB_PASS=devpass \
PANEL_ADMIN_PASS=admin123 \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash

# Production setup
PANEL_NON_INTERACTIVE=true \
PANEL_SETUP_SYSTEMD=true \
PANEL_SETUP_NGINX=true \
PANEL_DOMAIN=panel.example.com \
PANEL_DB_PASS=$(openssl rand -base64 24) \
PANEL_ADMIN_PASS=$(openssl rand -base64 16) \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

### Uninstalling Panel

```bash
# Remove everything
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash

# Keep database
bash uninstall.sh --keep-db

# Keep system packages
bash uninstall.sh --no-remove-deps
```

---

## 👨‍💻 For Developers

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/phillgates2/panel.git
cd panel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Run development server
python3 app.py
```

### Making Changes

```bash
# Format code
black .
isort .

# Run tests
pytest

# Check for issues
flake8 .

# Database migrations
flask db migrate -m "Description"
flask db upgrade
```

### Project Structure

```
Key components:
- app.py           → Flask application setup, routes
- models.py        → Database models (User, Server, etc.)
- templates/       → HTML pages (login, dashboard, etc.)
- static/css/      → Stylesheets
- config.py        → Configuration settings
- tasks.py         → Background jobs
```

---

## 📄 More Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute code
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[README_DEV.md](README_DEV.md)** - Detailed developer docs
- **[INSTALLER_GUIDE.md](INSTALLER_GUIDE.md)** - Complete installer reference

---

## 💬 Get Help

- **Bug reports**: [GitHub Issues](https://github.com/phillgates2/panel/issues)
- **Questions**: [GitHub Discussions](https://github.com/phillgates2/panel/discussions)
- **Documentation**: Check the `docs/` folder

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-idea`
3. Make your changes
4. Test your changes: `pytest`
5. Format code: `black . && isort .`
6. Commit: `git commit -m "Add cool feature"`
7. Push: `git push origin feature/your-idea`
8. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

---

## 📊 Project Status

![CI Status](https://github.com/phillgates2/panel/workflows/Panel%20CI%2FCD/badge.svg)

- ✅ Automated testing (Python 3.10, 3.11, 3.12)
- ✅ Code quality checks
- ✅ Security scanning
- ✅ Continuous integration

---

## 🔗 Links

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Discussions**: https://github.com/phillgates2/panel/discussions

---

**Panel** — Simple, secure, and modern game server management. 🎮

---

## 🚀 Quick Start

### One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

The installer features **interactive mode selection**, automatic service orchestration, and comprehensive health checks. Choose between Development, Production, or Custom installation modes.

### Installation Modes

#### 1. Development Mode (Interactive)
Perfect for local testing and development:
- Debug mode enabled
- Direct port access (8080)
- No systemd services
- SQLite or PostgreSQL
- Auto-start Panel services

#### 2. Production Mode (Interactive)
Enterprise-ready deployment:
- Production configuration
- Systemd service management
- Nginx reverse proxy
- SSL certificate support
- PostgreSQL database
- Automatic service startup

#### 3. Custom Mode (Interactive)
Mix and match components to suit your needs:
- Choose individual features
- Select systemd/nginx/SSL
- Configure debug mode
- Flexible port configuration

### Installation Options

```bash
# Show all options and available functions
bash install.sh --help

# Custom installation directory
bash install.sh --dir /opt/panel

# Force PostgreSQL (production - recommended)
bash install.sh --postgresql

# Non-interactive mode
bash install.sh --non-interactive

# Skip dependency installation
bash install.sh --skip-deps

# Use specific branch
bash install.sh --branch develop

# Verify existing installation
bash install.sh --verify-only

# Update existing installation (git pull + pip upgrade)
bash install.sh --update
```

### Non-Interactive Installation

**Development Quick Start:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_DEBUG=true \
PANEL_DB_PASS=devpass \
PANEL_ADMIN_PASS=admin123 \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

**Production Deployment:**
```bash
PANEL_NON_INTERACTIVE=true \
PANEL_SETUP_SYSTEMD=true \
PANEL_SETUP_NGINX=true \
PANEL_DOMAIN=panel.example.com \
PANEL_ADMIN_EMAIL=admin@example.com \
PANEL_DB_PASS=$(openssl rand -base64 24) \
PANEL_ADMIN_PASS=$(openssl rand -base64 16) \
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
```

**Available Environment Variables:**
```bash
# Database Configuration
PANEL_DB_HOST=localhost          # PostgreSQL host
PANEL_DB_PORT=5432              # PostgreSQL port
PANEL_DB_NAME=panel             # Database name
PANEL_DB_USER=panel_user        # Database username
PANEL_DB_PASS=<password>        # Database password (required)

# Application Settings
PANEL_INSTALL_DIR=~/panel       # Installation directory
PANEL_DOMAIN=localhost          # Domain or IP address
PANEL_PORT=8080                 # Application port
PANEL_DEBUG=false               # Debug mode (true/false)
PANEL_ADMIN_EMAIL=admin@localhost
PANEL_ADMIN_PASS=<password>     # Admin password (required)

# Service Options (NEW)
PANEL_SETUP_SYSTEMD=false       # Setup systemd services
PANEL_SETUP_NGINX=false         # Setup nginx reverse proxy
PANEL_SETUP_SSL=false           # Setup SSL certificates
PANEL_AUTO_START=true           # Auto-start after install

# Installer Behavior
PANEL_NON_INTERACTIVE=false     # Skip interactive prompts
PANEL_SKIP_DEPS=false           # Skip system dependencies
PANEL_SKIP_POSTGRESQL=false     # Skip PostgreSQL setup
PANEL_SAVE_SECRETS=true         # Save credentials to .install_secrets
PANEL_FORCE=false               # Auto-yes to all prompts
```

> **Note:** The installer now features automatic service orchestration. After installation, Panel services will auto-start (unless `PANEL_AUTO_START=false`), and a health check will verify everything is working correctly.

### Uninstallation

```bash
# Interactive uninstall (removes ALL files, folders, and system dependencies)
curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/uninstall.sh | bash

# Show uninstall options
bash uninstall.sh --help

# Force uninstall without prompts
bash uninstall.sh --force

# Keep PostgreSQL database
bash uninstall.sh --keep-db

# Keep system dependencies (Python, PostgreSQL, Nginx, Redis, etc.)
bash uninstall.sh --no-remove-deps

# Uninstall from custom directory
bash uninstall.sh --dir /opt/panel
```

**What gets removed:**
- Installation directory and all files
- Python virtual environment
- Logs, audit logs, and database backups
- SQLite database file (if used)
- Systemd service files (panel-gunicorn, rq-worker, etc.)
- Nginx configuration
- PostgreSQL database and user (unless `--keep-db`)
- System dependencies (unless `--no-remove-deps`): Python3, PostgreSQL, Nginx, Redis, build tools

---

## ✨ Features

### 🔒 Security
- **Rate Limiting** - 30 requests/minute per IP with whitelist support
- **SQL Injection Protection** - Real-time query validation and blocking
- **Security Headers** - CSP, HSTS, X-Frame-Options, secure cookies
- **Audit Logging** - JSONL format with security event tracking
- **Password Security** - Argon2 hashing with secure reset workflows
- **Input Validation** - Marshmallow schemas for type-safe data handling

### 🗄️ Database Management
- **Built-in Database Admin UI** - Python-based web interface for PostgreSQL & SQLite
- **Flask-Migrate** - Database version control and schema migrations
- **PostgreSQL Support** - Production-ready with psycopg2-binary driver
- **SQLite Support** - Fast development setup with zero configuration
- **Query Validation** - SQL injection detection and prevention
- **UTF8MB4** - Full Unicode support for international characters

### 📊 Monitoring
- **Health Endpoints** - `/health` and `/health/detailed` for uptime monitoring
- **Professional Logging** - Rotating log files with structured output
- **Audit Trails** - Track security events and administrative actions
- **RQ Dashboard** - Background job monitoring with web interface
- **Metrics** - Query performance and system health tracking

### 🎨 Modern Interface
- **Responsive Design** - Mobile-friendly admin dashboard
- **Custom Themes** - Configurable CSS and logo support
- **Glass Morphism UI** - Modern gradient backgrounds and effects
- **Accessibility** - WCAG-compliant navigation and forms

### 🛠️ Developer Experience
- **Makefile Commands** - 20+ utilities for testing, linting, migrations, backups
- **Pre-commit Hooks** - Automatic code formatting with Black and isort
- **Comprehensive Tests** - pytest suite with 15+ test cases
- **CI/CD Pipeline** - GitHub Actions with multi-version Python testing

---

## 📋 After Installation

### Access the Panel
```bash
# Default URL (or the domain you specified during installation)
http://localhost:8080

# Login with credentials set during installation
Email: admin@localhost (or your specified email)
Password: [your password]
```

**Accessing from another machine:**
```bash
# 1. Find your server's IP address
hostname -I    # Shows all IPs
# or
ip addr show   # Detailed network info

# 2. Access Panel via server IP
http://[SERVER_IP]:8080

# Example:
http://192.168.1.100:8080
http://10.0.2.73:8080
```

**If using a domain:**
```bash
# Make sure DNS points to your server
# Access via your configured domain
http://your-domain.com:8080
```

### Start the Panel

**If you chose auto-start during installation**, the Panel is already running!

**To start manually:**
```bash
cd ~/panel  # or your installation directory
source venv/bin/activate

# Create necessary directories
mkdir -p logs instance/logs instance/audit_logs instance/backups

# Start background worker
nohup python3 run_worker.py > logs/worker.log 2>&1 &

# Start web server
nohup python3 app.py > logs/panel.log 2>&1 &

# Panel is now accessible at http://localhost:8080
```

> **Note:** The first startup may take a few seconds as the application initializes the database and creates necessary tables.

**Alternative - Using Make commands:**
```bash
cd ~/panel

# Start development server (SQLite, debug mode)
make dev

# Start production server (PostgreSQL, no debug)
make prod
```

### Stop the Panel

```bash
# Stop all Panel processes
pkill -f "python.*app.py"
pkill -f "python.*run_worker.py"

# Or find specific PIDs first
ps aux | grep "python3 app.py"
ps aux | grep "python3 run_worker.py"

# Then kill by PID
kill [PID_OF_APP] [PID_OF_WORKER]
```

> **Note:** Flask's debug mode creates multiple processes (parent + reloader), so using `pkill -f` is more reliable than killing individual PIDs.

**If using systemd services:**
```bash
# Stop the service
sudo systemctl stop panel-gunicorn

# Check status
sudo systemctl status panel-gunicorn
```

### Manage Database
```bash
# Built-in database admin UI
http://localhost:8080/admin/database
```

### Common Commands
```bash
cd ~/panel  # or your installation directory

# Check if Panel is running
ps aux | grep "python3 app.py"

# View logs
tail -f logs/panel.log
tail -f logs/worker.log

# Check service status (if using systemd)
systemctl status panel-gunicorn

# Database migrations
make db-migrate
make db-upgrade

# Run tests
make test

# Update installation
git pull && make install
```

### Troubleshooting

**Cannot connect to Panel** (`Connection refused` or timeout):
```bash
# 1. Check if Panel is actually running
ps aux | grep "python.*app.py"

# 2. Check if port 8080 is listening
netstat -tlnp | grep 8080
# or
ss -tlnp | grep 8080

# 3. Test local connection
curl http://localhost:8080/

# 4. Check firewall (if accessing remotely)
sudo ufw status
sudo ufw allow 8080/tcp

# 5. If in Docker/container, ensure port is forwarded
# Check your container's port mapping

# 6. Get your server's IP address
hostname -I
ip addr show

# 7. Try accessing via IP instead of localhost
curl http://[YOUR_IP]:8080/
```

**Redis Connection Error** (`Connection refused` on port 6379):
```bash
# Check if Redis is running
ps aux | grep redis-server

# Start Redis
sudo systemctl start redis
# or
sudo systemctl start redis-server
# or (Alpine/manual)
redis-server --daemonize yes

# Enable Redis to start on boot
sudo systemctl enable redis
```

**Panel won't start**:
```bash
# Check logs for errors
tail -f ~/panel/logs/panel.log
tail -f ~/panel/logs/worker.log

# Check if port 8080 is already in use
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep 8080

# Kill process using port 8080
sudo kill [PID]
```

**Database Connection Error**:
```bash
# PostgreSQL - check if service is running
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check database exists
sudo -u postgres psql -l | grep panel

# SQLite - check file permissions
ls -la ~/panel/instance/panel.db
```

**Worker not processing jobs**:
```bash
# Ensure Redis is running (see above)

# Check worker logs
tail -f ~/panel/logs/worker.log

# Restart worker
pkill -f "run_worker.py"
cd ~/panel && source venv/bin/activate
nohup python3 run_worker.py > logs/worker.log 2>&1 &
```

---

## 🎯 What's Inside

### Core Stack
- **Flask 3.0** - Modern Python web framework
- **SQLAlchemy** - Powerful ORM with model relationships
- **PostgreSQL** - Production database with psycopg2-binary driver
- **SQLite** - Development database (zero config)
- **Nginx** - High-performance reverse proxy
- **Gunicorn** - Production WSGI server
- **Redis** - Session storage and job queue
- **RQ** - Background task processing

### Security Components
- **Flask-Limiter** - Rate limiting middleware
- **Flask-WTF** - CSRF protection
- **Argon2** - Password hashing
- **Marshmallow** - Input validation schemas
- **Custom SQL Validator** - Injection detection engine
- **Security Headers** - CSP, HSTS, X-Frame-Options

### Admin Tools
- **Database Admin UI** - Python-based management interface
- **Flask-Migrate** - Alembic database migrations
- **Audit Logging** - JSONL security event log
- **RQ Dashboard** - Background job monitoring
- **Health Checks** - System status endpoints

---

## 🏗️ Architecture

```
panel/
├── app.py                    # Main Flask application
├── models.py                 # SQLAlchemy models
├── database_admin.py         # Built-in database UI
├── tasks.py                  # Background tasks (RQ)
├── config.py                 # Production configuration
├── config_dev.py             # Development configuration
├── db_security.py            # SQL injection protection
├── db_audit.py               # Audit logging
├── logging_config.py         # Professional logging
├── security_headers.py       # CSP, HSTS headers
├── input_validation.py       # Marshmallow schemas
├── rate_limiting.py          # Flask-Limiter config
├── rcon_client.py            # ET:Legacy RCON client
├── captcha.py                # CAPTCHA generation
├── templates/                # Jinja2 templates
├── static/css/               # Stylesheets
├── instance/                 # Runtime data
│   ├── logs/                 # Application logs
│   ├── audit_logs/           # Security audit logs
│   └── backups/              # Database backups
├── tests/                    # pytest test suite
├── deploy/                   # Systemd & Nginx configs
├── scripts/                  # Utility scripts
└── tools/                    # Makefile & utilities
```

---

## 🚀 Production Deployment

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, Alpine 3.18+, or similar
- **Python**: 3.8 or higher
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ available
- **Ports**: 8080 (Panel), 8081 (Database Admin)

### Production Checklist

1. **Run installer**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install.sh | bash
   # Choose PostgreSQL when prompted
   ```

2. **Configure environment** (`.env` or `config.py`)
   ```python
   SECRET_KEY = 'your-strong-random-key-here'
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/panel'
   REDIS_URL = 'redis://localhost:6379/0'
   ```

3. **Setup firewall**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8080/tcp
   sudo ufw enable
   ```

4. **Enable services**
   ```bash
   sudo systemctl enable panel-gunicorn
   sudo systemctl enable rq-worker-supervised
   sudo systemctl start panel-gunicorn
   ```

5. **Setup SSL** (optional, if using domain)
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

6. **Verify health**
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status": "healthy"}
   ```

---

## 🧪 Development

### Clone & Setup
```bash
git clone https://github.com/phillgates2/panel.git
cd panel

# Install dependencies
make install-dev

# Run development server (SQLite)
make dev
```

### Development Workflow
```bash
# Code formatting
make format

# Linting
make lint

# Run tests with coverage
make test
make coverage

# Database migrations
make db-migrate      # Create migration
make db-upgrade      # Apply migrations
make db-downgrade    # Rollback migration

# Database backup
make db-backup
```

### Pre-commit Hooks
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Environment Variables
```bash
# Development mode (SQLite)
export PANEL_USE_SQLITE=1

# Production mode (PostgreSQL)
export PANEL_DB_TYPE=postgresql
export PANEL_DB_HOST=localhost
export PANEL_DB_NAME=panel
export PANEL_DB_USER=panel_user
export PANEL_DB_PASS=secure_password
```

---

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[README_DEV.md](README_DEV.md)** - Developer documentation
- **`docs/`** - Additional documentation (if present)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Make your changes with tests
4. Run quality checks (`make test lint format`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing`)
7. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📊 CI/CD Status

![CI Status](https://github.com/phillgates2/panel/workflows/Panel%20CI%2FCD/badge.svg)

- Multi-Python version testing (3.8, 3.9, 3.10, 3.11)
- Code coverage reporting
- Security vulnerability scanning
- Automated code formatting checks
- Dependency auditing

---

## 📄 License

This project is open source. See the repository for license details.

---

## 🔗 Links

- **Repository**: https://github.com/phillgates2/panel
- **Issues**: https://github.com/phillgates2/panel/issues
- **Discussions**: https://github.com/phillgates2/panel/discussions

---

## 💡 Support

- �� Check the documentation in `docs/` folder
- 🐛 Report bugs via [Issues](https://github.com/phillgates2/panel/issues)
- 💬 Ask questions in [Discussions](https://github.com/phillgates2/panel/discussions)

---

**Panel** — Modern, secure, production-ready game server management for ET: Legacy. Built with Flask and PostgreSQL.
