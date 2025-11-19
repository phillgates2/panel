# Changelog

All notable changes to this project will be documented in this file.

## [3.3.0] - 2025-11-19

### 🚀 **Major Features**

#### CMS Blog System (Public)
- **BlogPost Model** - Full-featured blog system with:
  - Title, slug, content, excerpt fields
  - Author attribution (linked to User model)
  - Publication status (draft/published)
  - Created/updated timestamps
  - Markdown support for rich content

- **Public Blog Pages**
  - `/cms/blog` - Public blog index showing all published posts
  - `/cms/blog/<slug>` - Individual blog post pages
  - Homepage integration - 5 most recent posts displayed on homepage
  - Panel-styled templates with cards, shadows, and hover effects

- **Admin Blog Management**
  - `/cms/admin/blog` - Blog post dashboard
  - Create, edit, delete blog posts
  - Draft/publish workflow
  - Auto-slug generation from title
  - Markdown editor with preview support

#### Forum System Overhaul
- **Public Access** - Anyone can view forum and read threads (no login required)
- **Login-Required Actions** - Must be logged in to create threads or post replies
- **User-Based System** - Posts linked to User accounts instead of anonymous strings
- **Thread Management**
  - Pin threads (appear at top of forum)
  - Lock threads (prevent new replies)
  - Thread badges showing pinned/locked status

#### Role-Based Permissions
- **User Roles**
  - 👤 **User** - Can create forum threads and post replies
  - 🛡️ **Moderator** - Can manage forum (edit/delete posts, pin/lock threads)
  - 🔧 **Server Mod** - Can moderate game servers
  - 🖥️ **Server Admin** - Full server administration
  - ⚙️ **System Admin** - Full system access

- **Forum Permissions**
  - Basic users can create threads and replies
  - Moderators can edit/delete any post
  - Moderators can pin and lock threads
  - Authors can edit their own posts
  - Locked threads prevent new replies

#### User Management UI
- **Modernized /admin/users Page**
  - Role information cards explaining each permission level
  - Color-coded role badges for visual identification
  - User avatars with initials
  - Inline role editing with dropdown
  - Confirmation dialog for system admin grants
  - Responsive design for mobile devices

### 📊 **Database Changes**
- **New Table: cms_blog_post**
  - Full blog post storage with author, publication status
  
- **Updated Table: forum_thread**
  - Added `author_id` (FK to User)
  - Added `is_pinned` (Boolean)
  - Added `is_locked` (Boolean)

- **Updated Table: forum_post**
  - Changed `author` (String) → `author_id` (FK to User)
  - Added User relationship

- **Migration Script**
  - `migrate_cms_forum.py` - Automated migration for schema changes

### 🎨 **UI/UX Improvements**

#### Homepage Redesign
- Hero section with emoji and subtitle
- Recent blog posts section (5 most recent)
- Features grid showcasing panel capabilities
- Call-to-action section for new users
- Fully responsive design

#### Forum Templates (All Redesigned)
- `templates/forum/index.html`
  - Modern card-based thread listing
  - Thread badges (pinned, locked)
  - Post count and metadata display
  - Moderator action buttons
  
- `templates/forum/thread.html`
  - User avatars with initials
  - Author information display
  - Reply form with Markdown support
  - Edit/delete buttons for authors/moderators
  - Login prompt for non-authenticated users
  
- `templates/forum/create_thread.html`
  - Panel-styled form
  - Markdown support notice
  
- `templates/forum/edit_post.html`
  - Clean editor interface
  
- `templates/forum/edit_thread.html`
  - Pin/lock checkboxes for moderators

#### CMS Templates (All New)
- `templates/cms/admin_blog_list.html` - Blog management dashboard
- `templates/cms/admin_blog_edit.html` - Blog post editor
- `templates/cms/blog_index.html` - Public blog listing
- `templates/cms/blog_post.html` - Individual post view

#### Navigation Updates
- Added **Forum** link to main navigation (accessible to all)
- Added **Blog** link to main navigation (accessible to all)
- Added **Blog Management** to admin dashboard
- Forum and Blog prominently featured in site-wide navigation

### 🔧 **Backend Updates**

#### app.py
- Updated homepage route to fetch recent blog posts
- User management already supports role changes
- Audit logging for role changes

#### cms/__init__.py
- Added `BlogPost` model with full relationships
- Added blog management routes (create, edit, delete)
- Added public blog routes (index, individual posts)
- Markdown rendering with bleach sanitization

#### forum/__init__.py (Complete Rewrite)
- Added helper functions:
  - `get_current_user()` - Retrieve current user from session
  - `is_moderator_or_admin()` - Check moderator permissions
  
- Added decorators:
  - `login_required` - Protect routes requiring authentication
  - `moderator_required` - Protect moderator-only routes
  
- Updated all routes:
  - `index()` - Public access, shows pinned threads first
  - `view_thread()` - Public access, enhanced Markdown rendering
  - `reply_thread()` - Login required, checks if thread is locked
  - `create_thread()` - Login required (was admin-only)
  - `edit_post()` - Author or moderator can edit
  - `delete_post()` - Moderator-only
  - `edit_thread()` - Moderator-only, added pin/lock handling
  - `delete_thread()` - Moderator-only
  
- Added new routes:
  - `pin_thread()` - Toggle pinned status (moderator-only)
  - `lock_thread()` - Toggle locked status (moderator-only)

### 🔒 **Security & Permissions**
- CSRF protection on all form submissions
- Role-based access control for forum actions
- Audit logging for user role changes
- Input validation and sanitization
- Markdown content sanitized with bleach

### 📱 **Responsive Design**
- All new templates fully responsive
- Mobile-friendly forum layouts
- Flexible grid layouts
- Touch-friendly action buttons

### ✅ **Completed Requirements**
- ✓ CMS posts visible to all on homepage
- ✓ CMS styled as the panel
- ✓ Forum visible to all but posting requires login
- ✓ Basic user role can post and create threads
- ✓ Forum styled same as panel
- ✓ Superadmins can change permissions for all users
- ✓ Moderator group to manage forum

---

## [3.2.0] - 2025-11-19

### 🎨 **UI/UX Enhancements**

#### Modern Input Styling
- **Enhanced Input Boxes** - All text inputs now have beautiful, consistent styling
  - 3px borders with elevation shadows
  - Dark background (`--panel-hover`) for better contrast
  - 12px rounded corners for modern look
  - Smooth focus animations with accent glow
  - Applied to: email, password, text, date, textarea, select, and captcha inputs

#### Authentication Pages Redesign
- **Login Page** - Already featured modern design
  - Clean form-group structure with icon labels
  - Stylish captcha container with controls
  - Professional button styling with emojis
  
- **Register Page** - Complete redesign to match login
  - Icon labels (👤 Name, 📧 Email, 🎂 DOB, 🔒 Password)
  - Proper form-group divs for consistent spacing
  - Password strength meter integration
  - Enhanced captcha section
  - "Already have an account?" footer link
  
- **Forgot Password Page** - Modernized layout
  - 🔑 Icon header with descriptive subtitle
  - Clean single-field form
  - Stylish captcha integration
  - "Remember your password?" footer link
  
- **Reset Password Page** - Updated to match auth flow
  - 🔓 Icon header with helpful subtitle
  - Consistent form styling
  - Enhanced security verification section
  - ✅ Clear action button

#### Input Focus Effects
- **Enhanced Interactions** - Better visual feedback
  - Smooth translateY animation on focus
  - Accent-colored glow effect (rgba(31, 111, 235, 0.15))
  - Increased shadow depth (0 8px 25px)
  - Background color transitions
  - Transform effects for premium feel

#### Captcha Styling
- **Security Inputs** - Special treatment for captcha fields
  - Centered text for better code display
  - Optimized font size (1.1rem) for readability
  - Letter spacing (0.2em) for character distinction
  - Uppercase transformation built-in
  - Inherits all standard input enhancements

### 📝 **Documentation Improvements**

#### README Rewrite
- **Simplified Structure** - Completely reorganized for clarity
  - "What is This?" section explains the project upfront
  - Installation modes clearly explained with use cases
  - "Using Panel" section with practical examples
  - "Managing Panel" with common day-to-day tasks
  - Troubleshooting section with actual solutions
  
- **Better Organization** - Logical flow for all skill levels
  - Quick start for beginners
  - Detailed sections for power users
  - Separate "For Developers" section
  - Clear separation of basic and advanced topics
  
- **Plain Language** - Technical jargon removed or explained
  - "Development Mode" instead of "debug mode with SQLite config"
  - "Best for:" sections for each installation mode
  - Simple command examples with explanations
  - Friendly, conversational tone

#### Enhanced Troubleshooting
- **Common Issues** - Real problems with real solutions
  - "Can't Connect to Panel" with step-by-step debugging
  - Redis connection errors with multiple fix attempts
  - Database connection issues for PostgreSQL
  - Port conflicts with process identification
  - Each issue has copy-paste ready commands

## [3.1.0] - 2025-11-18

### ✨ **Major Installer Overhaul**

#### Interactive Installation Modes
- **Development Mode** - Quick local testing setup
  - Debug mode enabled by default
  - Direct port access (8080)
  - No systemd services
  - Perfect for development and testing
  
- **Production Mode** - Enterprise-ready deployment
  - Systemd service management
  - Nginx reverse proxy configuration
  - SSL certificate support via Let's Encrypt
  - Production-optimized settings
  
- **Custom Mode** - Choose specific components
  - Select individual features (systemd/nginx/SSL)
  - Mix development and production options
  - Flexible configuration

#### Automatic Service Orchestration
- **Auto-Start Services** - Panel services automatically start after installation
  - `ensure_redis_running()` - Auto-start and verify Redis
  - `ensure_postgresql_running()` - Auto-start and verify PostgreSQL
  - `ensure_nginx_running()` - Auto-start and verify Nginx (if enabled)
  - `setup_systemd_services()` - Configure systemd units
  - `start_systemd_services()` - Start services via systemd
  - `perform_health_check()` - Verify Panel is responding

#### Enhanced Configuration
- **Interactive Prompts** - All settings now have clear, guided prompts
  - Installation mode selection with descriptions
  - Database configuration with auto-generated passwords
  - Domain/network setup with examples
  - Admin account creation with secure defaults
  - Optional features selection
  
- **Configuration Summary** - Shows all settings before installation
  - Review mode, directory, database, domain, services
  - Confirm before proceeding
  - Prevents configuration mistakes

#### Production Features
- **Nginx Integration** - `setup_nginx_config()`
  - Automatic reverse proxy configuration
  - Domain-based virtual host setup
  - Seamless integration with existing nginx
  
- **SSL/TLS Support** - `setup_ssl_certificates()`
  - Automatic Let's Encrypt certificate acquisition
  - Certbot integration
  - Auto-renewal setup
  
- **Systemd Services** - Production-grade service management
  - panel-gunicorn.service configuration
  - rq-worker.service configuration
  - Auto-enable and start services
  - Service status verification

#### Health Checks & Verification
- **Automatic Health Check** - `perform_health_check()`
  - Tests /health endpoint
  - Retries with exponential backoff
  - Verifies Panel is responding correctly
  - Clear error messages if issues detected
  
- **Service Verification**
  - Checks if Redis is running and responding
  - Verifies PostgreSQL connectivity
  - Confirms Nginx is listening (if enabled)
  - Tests Panel HTTP responses

#### New Environment Variables
```bash
PANEL_SETUP_SYSTEMD=true/false    # Configure systemd services
PANEL_SETUP_NGINX=true/false      # Setup nginx reverse proxy
PANEL_SETUP_SSL=true/false        # Setup SSL certificates
PANEL_AUTO_START=true/false       # Auto-start after install (default: true)
```

#### Installation Process Improvements
The installer now performs these steps automatically:
1. System detection and pre-flight checks
2. Interactive mode selection (or use env vars)
3. System dependency installation
4. Auto-start PostgreSQL and Redis
5. Panel application installation
6. Systemd service configuration (if requested)
7. Nginx reverse proxy setup (if requested)
8. SSL certificate acquisition (if requested)
9. Automatic service startup
10. Health check verification
11. Display access info and next steps

#### User Experience Enhancements
- **Better Progress Reporting** - Clear status messages for each step
- **Masked Password Input** - Secure credential entry
- **Auto-Generated Credentials** - Secure random passwords when not provided
- **Service Status Display** - Shows all running services and PIDs
- **Next Steps Guide** - Clear instructions after installation
- **Troubleshooting Help** - Built-in diagnostics and log locations

### 🔧 **Bug Fixes**
- Fixed installer syntax validation (passes `bash -n`)
- Improved error handling in service startup functions
- Better handling of systemd-less environments
- Enhanced PostgreSQL socket detection for dev containers

### 📚 **Documentation**
- Added comprehensive **INSTALLER_GUIDE.md**
  - Installation modes explained
  - All environment variables documented
  - Post-installation management
  - Troubleshooting guide
  - Security best practices
  
- Updated **README.md**
  - New installation mode documentation
  - Updated environment variable reference
  - Service management instructions

### 🔍 **Testing & Quality**
- Comprehensive project health check implemented
- All 109 Python files validated (no syntax errors)
- All shell scripts validated (bash -n)
- Configuration files validated
- No critical errors detected

---

## [3.0.5] - 2025-11-17

### ✨ **New Features**

#### Installer Enhancements
- **Enhanced `--help` Output** - Display all available installer functions
  - Lists 25+ functions organized by category (Core, System, Validation, Installation, Utility)
  - Helpful for debugging and understanding installer capabilities
  - Shows function names and brief descriptions
  - Integrated into help menu for easier discovery

- **`--verify-only` Flag** - Verify existing installation without reinstalling
  - Checks `.env` file existence and configuration
  - Validates virtual environment and Flask installation
  - Tests database connection (PostgreSQL or SQLite)
  - Useful for troubleshooting existing installations

- **`--update` Flag** - Safe upgrade mechanism for existing installations
  - Creates timestamped backup before updating
  - Pulls latest code from git repository
  - Upgrades Python dependencies via pip
  - Runs database migrations if available
  - Preserves existing `.env` configuration

- **Smart Dependency Checking** - Idempotent installation
  - Detects already-installed packages before attempting installation
  - Skips existing dependencies, only installs missing ones
  - Reduces installation time on repeat runs
  - Clear logging shows what's installed vs. skipped

- **Automatic Service Configuration**
  - Redis server automatically enabled and started
  - Nginx server automatically enabled and started
  - Health checks verify services are running
  - Multiple fallback methods for service startup

#### Bug Fixes
- **Fixed Python Version Check** - Corrected version comparison logic
  - Replaced incorrect awk floating-point comparison with `sort -V`
  - Now correctly accepts Python 3.8+ (including 3.13)
  - Previously rejected valid Python versions due to logic error

- **Fixed psycopg2-binary Build Error** - Added PostgreSQL development libraries
  - apt-get: Added `libpq-dev` and `postgresql-client`
  - dnf/yum: Added `postgresql-devel`
  - apk: Added `postgresql-dev`
  - pacman: Added `postgresql-libs`
  - brew: Added `postgresql`
  - Resolves "fatal error: libpq-fe.h: No such file or directory"

- **Fixed Python 3.13 Compatibility** - Updated psycopg2-binary version
  - Updated from 2.9.9 to >=2.9.10 for Python 3.13 support
  - Added fallback to use prebuilt binary wheels when compilation fails
  - Installer now tries binary-only installation first
  - Prevents build errors from deprecated Python 3.13 APIs

- **Fixed Nginx Startup on Debian/Ubuntu** - Enhanced nginx configuration
  - Automatically removes conflicting default site on Debian/Ubuntu
  - Stops and restarts nginx to clear any errors
  - Added configuration validation and error recovery
  - Shows detailed status if nginx fails to start
  - Verifies nginx is listening on port 80
  - Services verified before panel installation begins
  
- **Auto-Install Production Dependencies** - Full automation for production setup
  - Nginx auto-installs if not present (no manual steps required)
  - PostgreSQL auto-installs when --postgresql flag is used
  - Redis auto-installs and auto-starts
  - All dependencies checked and installed automatically
  - Removes default nginx site configuration on Debian/Ubuntu
  - Complete hands-free production setup

#### Documentation Updates
- **README** - Added installer flags reference section
  - Documents `--functions`, `--verify-only`, `--update` flags
  - Updated installation examples with new options

## [3.0.4] - 2025-11-17

### 🐛 **Bug Fixes**

#### Auto-Start Process Detection
- **Fixed Flask Debug Mode Process Detection** - Auto-start now correctly detects running Panel
  - Flask's debug mode spawns child processes via reloader
  - Original PID check was unreliable (parent process exits immediately)
  - Now uses `pgrep -f "python.*app.py"` to find actual running processes
  - Displays all running PIDs (Panel and Worker may have multiple processes)
  - Updated stop instructions to recommend `pkill -f` over individual PID termination

#### Directory Creation
- **Enhanced Directory Setup** - Creates all required directories before starting services
  - Now creates: `logs/`, `instance/logs/`, `instance/audit_logs/`, `instance/backups/`
  - Prevents file write errors during startup
  - Increased startup wait time from 2s to 3s for proper initialization
  - Shows last 20 lines of log on failure for debugging

## [3.0.3] - 2025-11-17

### ✨ **New Features**

#### Redis Installation & Service Management
- **Automatic Redis Installation** - Installer now includes Redis in system dependencies
  - Supports all package managers: apt, dnf/yum, apk, pacman, brew
  - Checks if Redis is running before starting Panel services
  - Automatically starts Redis if not running (systemd, service, or daemonize)
  - Provides clear warnings and instructions if Redis fails to start

#### Domain/Hostname Configuration
- **Domain Prompt** - Interactive installer now asks for domain/hostname
  - Supports domains (panel.example.com), IPs (192.168.1.100), or localhost
  - Stores domain in `.env` file for configuration reference
  - Updates all completion messages to show configured domain

#### Comprehensive Documentation
- **Troubleshooting Section** - Added detailed troubleshooting guide to README
  - Redis connection errors (port 6379 refused)
  - Panel startup issues and port conflicts
  - Database connection problems (PostgreSQL & SQLite)
  - Worker not processing jobs
  - Step-by-step solutions with commands

### 🐛 **Bug Fixes**

#### Background Worker Redis Dependency
- **Fixed Redis Connection Error** - Worker now starts successfully
  - Error: `ConnectionError: Error 111 connecting to 127.0.0.1:6379. Connection refused.`
  - Cause: Redis was not installed or running
  - Solution: Installer now ensures Redis is installed and running before starting worker

## [3.0.2] - 2025-11-17

### ✨ **New Features**

#### Installer Auto-Start Option
- **Interactive Auto-Start** - Installer now prompts to automatically start the Panel after installation
  - Starts both web server and background worker in one step
  - Provides immediate access to the Panel without manual commands
  - Shows PIDs for easy process management
  - Displays log file locations for troubleshooting
  - Falls back to manual instructions if user declines

### 🐛 **Bug Fixes**

#### Installer UX Improvements
- **Fixed Post-Installation Confusion** - Panel now starts automatically when user confirms
  - Previously only showed manual start instructions
  - Users reported being "unable to connect" because services weren't running
  - Now provides clear choice: start now (automatic) or manual start later

## [3.0.1] - 2025-11-17

### 🐛 **Bug Fixes**

#### Installer Improvements
- **Fixed Terminal Text Selection** - Removed `-n` flag from echo commands to allow normal text selection in terminal
- **Fixed Prompt Capture Issue** - Redirected all prompts to stderr (`>&2`) to prevent prompt text from being captured in variables
  - Fixes error: "Refusing to create a venv... because it contains the PATH separator `:'"
- **Fixed Database Initialization** - Wrapped `db.create_all()` in `app.app_context()` to prevent RuntimeError
  - Fixes error: "RuntimeError: Working outside of application context"

#### Logging Improvements  
- **Fixed Logging Outside App Context** - Added try/except in `record_factory` to gracefully handle missing Flask application context
  - Returns `None` for `correlation_id` when no request context is available
  - Prevents crashes during database initialization and CLI commands

#### Uninstaller Clarification
- **Separated Uninstaller** - `uninstall.sh` is now completely standalone
  - Fixed issue where `--uninstall` flag in install.sh wasn't working with curl piping
  - Use `curl -fsSL .../uninstall.sh | bash` for uninstallation
  - Updated README and help documentation to reflect proper usage

### 📚 **Documentation**
- Updated README.md with correct uninstallation commands
- Updated install.sh --help to point to separate uninstall.sh
- Clarified that uninstaller removes files, folders, AND system dependencies by default

## [3.0.0] - 2025-01-16

### 🎉 **Major Refactoring - PostgreSQL Migration & Codebase Cleanup**

This release represents a complete modernization of Panel with a focus on simplicity, PostgreSQL, and removing legacy code.

### 🗄️ **Database Migration**
- **PostgreSQL as Primary Database** - Migrated from MariaDB/MySQL to PostgreSQL
  - Production database now uses `psycopg2-binary==2.9.9` driver
  - Maintained SQLite support for development (`PANEL_USE_SQLITE=1`)
  - Removed all MariaDB/MySQL dependencies and configurations
  - Updated all database connection strings and queries for PostgreSQL compatibility

### 🧹 **Massive Code Cleanup** - Removed **7,916 lines** across **8 legacy files**
- **Removed Legacy Installer** - Deleted bloated `getpanel.sh` (2,947 lines)
- **Removed Backup Files** - Deleted `getpanel.sh.mariadb.backup`
- **Removed Migration Docs** - Deleted temporary `POSTGRES_MIGRATION.md`
- **Removed Migration Scripts** - Deleted `scripts/migrate_to_postgres.sh` and `scripts/postgres_functions.sh`
- **Removed Deprecated Wrappers** - Deleted `scripts/install.sh`, `scripts/update.sh`, `scripts/uninstall.sh`
- **86% Size Reduction** - New installer is only **416 lines** vs old 2,947-line installer

### ✨ **New Streamlined Installer**
- **Created `install.sh`** (416 lines) - Complete rewrite from scratch
  - Environment variable driven configuration
  - Interactive and non-interactive modes
  - PostgreSQL and SQLite support
  - Cross-platform package manager support (apt, dnf, apk, pacman, brew)
  - Clean color scheme: RED, GREEN, YELLOW, MAGENTA (removed BLUE, CYAN)
  - Comprehensive error handling and validation
  - Non-interactive installation via environment variables:
    - `PANEL_NON_INTERACTIVE=true`
    - `PANEL_DB_TYPE=postgresql|sqlite`
    - `PANEL_DB_HOST`, `PANEL_DB_PORT`, `PANEL_DB_NAME`, etc.

### 🔄 **Database Admin UI Refactoring**
- **Renamed `phpmyadmin_integration.py` → `database_admin.py`**
  - `PhpMyAdminIntegration` class → `DatabaseAdmin` class
  - `PHPMYADMIN_BASE_TEMPLATE` → `DATABASE_ADMIN_BASE_TEMPLATE`
  - `PHPMYADMIN_HOME_TEMPLATE` → `DATABASE_ADMIN_HOME_TEMPLATE`
  - `PHPMYADMIN_TABLE_TEMPLATE` → `DATABASE_ADMIN_TABLE_TEMPLATE`
  - `PHPMYADMIN_QUERY_TEMPLATE` → `DATABASE_ADMIN_QUERY_TEMPLATE`
  - Updated all imports in `app.py` and `tests/test_database_integration.py`
  - Removed misleading phpMyAdmin references (Python-based UI, not PHP)
  - Supports both PostgreSQL and SQLite via built-in Python drivers

### 🎨 **Installer UI Improvements**
- **Simplified Color Scheme** - Reduced from 6 colors to 4 colors
  - Removed: `BLUE`, `CYAN`
  - Kept: `RED`, `GREEN`, `YELLOW`, `MAGENTA`
  - Updated all banners, prompts, labels, and error messages
  - Cleaner, more professional terminal output

### 📚 **Documentation Overhaul**
- **Completely Rewrote README.md**
  - Removed all MariaDB/MySQL references
  - Removed phpMyAdmin references (now "Database Admin UI")
  - Highlighted PostgreSQL-first architecture
  - Documented new 416-line installer
  - Removed deprecated installer options
  - Added clear PostgreSQL vs SQLite usage examples
  - Updated architecture diagram with `database_admin.py`
  - Simplified quick start with single curl command

### 🔧 **Breaking Changes**
- **Removed MariaDB/MySQL Support** - PostgreSQL or SQLite only
- **Removed Legacy Installers** - Only `install.sh` remains
- **Removed Deprecated Scripts** - Old wrapper scripts no longer available
- **Renamed Database Admin** - Update any custom integrations using `PhpMyAdminIntegration`

### 📦 **Dependencies**
- **Added**: `psycopg2-binary==2.9.9` - PostgreSQL driver
- **Removed**: All MariaDB/MySQL Python drivers
- **Updated**: Flask, SQLAlchemy maintained at current versions

### ✅ **Validation & Testing**
- All Python files validated with `py_compile`
- Bash installer validated with `bash -n`
- Tests updated for PostgreSQL compatibility
- Database admin UI tests updated for new class names

### 🚀 **Migration Guide**
For users upgrading from v2.x with MariaDB/MySQL:
1. **Backup your database** - Use `make db-backup` or `mysqldump`
2. **Export data to PostgreSQL format**
3. **Run new installer** - `curl -fsSL .../install.sh | bash`
4. **Import data into PostgreSQL** - Use `psql` or `pg_restore`
5. **Update environment variables** - Switch to PostgreSQL connection strings

## [2.1.0] - 2025-01-16

### 🚀 **Installation Flow Reorganization**
- **Production Mode Early Database Setup** - MariaDB and phpMyAdmin now installed immediately after selecting production mode
- **Validation Checkers** - Added comprehensive validation functions for each configuration section
  - `check_mariadb_ready()` - Verifies MariaDB service is running and accessible (10 retry attempts)
  - `check_phpmyadmin_ready()` - Confirms phpMyAdmin installation and HTTP accessibility
  - `check_database_connection()` - Tests database connectivity and creates database with UTF8MB4
  - `check_section_complete()` - Visual completion markers between configuration sections
- **Early Failure Detection** - Database issues caught early before app configuration begins
- **Better Error Handling** - Option to abort or continue when database setup fails
- **Improved UX** - Clear visual separators and progress indicators throughout installation
- **Section Markers** - Each configuration section now has a completion marker for better visibility

### ✨ **Enhanced Production Deployment**
- **Immediate Database Verification** - Database infrastructure verified before continuing with configuration
- **phpMyAdmin Instant Access** - Database management UI available immediately at http://localhost:8081
- **Better Flow** - Database setup → Verify → Admin config → App settings → Services
- **Configuration Summary** - Enhanced summary with bold section headers and clear structure

## [2.0.0] - 2025-01-16

### 🎨 **Installer UX Improvements**
- **Colorful Terminal Output** - Added magenta, yellow, white colors for better readability
- **Redesigned --help** - Professional layout with categorized options and examples
- **Fixed Color Display** - Switched from heredoc to printf for proper ANSI rendering
- **Visual Hierarchy** - Grouped options by function (Installation, Components, Automation)

### 🗑️ **Enhanced Uninstall**
- **Complete Cleanup** - Now removes logs, audit logs, and database backups
- **Clear User Messaging** - Shows exactly what will be removed
- **Safe Operation** - Confirmation required before deletion

### 🗄️ **Database & phpMyAdmin**
- **Replaced Apache with Nginx** - phpMyAdmin now served via Nginx on port 8081
- **No Port Conflicts** - Panel (80/443) and phpMyAdmin (8081) coexist peacefully
- **Enhanced Database Setup** - Uses Flask-Migrate when available, UTF8MB4 charset
- **Better Logging** - Detailed step-by-step database creation logs
- **Verification** - Tests database creation with USE/SELECT validation

### 🔧 **Bug Fixes**
- **PHP-FPM Service Detection** - Auto-detects correct service name (php8.4-fpm, etc.)
- **Syntax Errors** - Fixed orphaned if/fi blocks in installer
- **Wildcard Commands** - Replaced invalid systemctl wildcards with proper detection

### 📚 **Documentation**
- **Streamlined README** - Easier to scan with clear sections and quick start
- **Better Examples** - One-line commands for common scenarios
- **Architecture Diagram** - Visual project structure
- **Updated Links** - All documentation properly cross-referenced

## [Unreleased]

### 🧰 **Installer, Logging & Tooling** - 2025-11-16

- **Unified Panel Entrypoints**
  - Deprecated legacy helper scripts (`scripts/install.sh`, `scripts/update.sh`, `scripts/uninstall.sh`, `start-dev.sh`) in favor of the consolidated `panel.sh` CLI
  - Updated `README.md` and `README_DEV.md` to steer users toward `panel.sh` as the primary interface
- **Self-Healing & Diagnostics**
  - Added `panel-doctor.sh` to run health checks on services, sockets, ports, migrations, and directories with optional auto-fix mode
  - Improved MariaDB readiness detection in `getpanel.sh` with broader systemd unit scanning (including templated units) and richer diagnostics
- **Secrets & Environment Management**
  - Introduced `scripts/env_generator.sh` for validated `.env` generation with support for `LOG_FORMAT` configuration
- **Structured Logging Enhancements**
  - Extended `logging_config.py` with optional JSON log output and per-request correlation IDs controlled via environment variables

### 🔧 **System Health & Configuration Management** - 2025-11-15

- **Health Check Endpoints** 💓
  - Added `/health` endpoint for basic system health monitoring
  - Added `/health/detailed` endpoint for comprehensive admin health checks
  - Integrated database, Redis, and uptime monitoring
  - JSON response format for easy integration with monitoring tools
  - Authentication protection for sensitive health information

- **Configuration Validation System** ✅
  - Implemented comprehensive `ConfigValidator` with intelligent dev/production detection  
  - Enhanced error handling with proper development vs production mode differentiation
  - Added detailed validation for SECRET_KEY, database, Redis, and ET:Legacy configurations
  - Improved dependency checking with required vs optional package classifications
  - **Fixed dependency detection for PIL/Pillow imports**
  - **Enhanced dev/production mode detection for contextual warnings**
  - **Added intelligent directory validation with optional paths**
  - **Refined service connection warnings to be development-appropriate**
  - **Removed duplicate validation checks and improved error messages**
  - Smart fallback configuration reading from config.py when environment variables missing

- **Admin Configuration Interface** 🎛️
  - Created `/admin/config/validate` endpoint with full validation reporting
  - Added beautiful admin interface (`admin_config_validate.html`) with real-time validation
  - Integrated configuration validation into admin tools menu
  - Color-coded error, warning, and info sections for easy issue identification
  - Added comprehensive configuration tips and best practices documentation
  - Real-time re-validation functionality with loading states

- **Enhanced Development Experience** 🛠️
  - Automatic detection of development mode (SQLite, FLASK_ENV, missing configs)
  - Graceful handling of missing optional dependencies in development
  - Improved error messages with context-aware suggestions
  - Better separation of critical production issues vs development warnings

### ✅ **Testing & Validation** - 2025-11-15

- **Captcha System Validation** 🔍
  - Extensively tested captcha generation with multiple size configurations (50x25 to 700x280 pixels)
  - Validated optimal readability with 80px font in 350x140 pixel canvas
  - Tested ultra-compact 50x25 pixel implementation for mobile compatibility
  - Confirmed enhanced contrast with light gray background and dark blue text
  - Verified exclusion of confusing characters (0, O, I, 1, L) for better usability

- **Code Quality & Cleanup** 🧹
  - Added comprehensive `.gitignore` for Python, Flask, IDE, and temporary files
  - Cleaned up test captcha files and development artifacts
  - Resolved all configuration validation warnings with appropriate dev/production context
  - Improved dependency detection accuracy for proper virtual environment validation
  - Enhanced error messages and validation reporting for better developer experience

- **Installer Testing & Verification** 🧪
  - Validated getpanel.sh installer functionality in clean environments
  - Tested interactive and non-interactive installation modes
  - Confirmed proper dependency management and Python version checking
  - Verified repository cloning and virtual environment setup
  - Validated uninstaller safety checks and complete cleanup

- **Dependency Compatibility Verification** ✅
  - Confirmed Flask 3.0.0 compatibility with existing codebase
  - Tested Pillow 10.1.0 image processing improvements
  - Validated Redis 5.0.1 connection handling
  - Verified all updated dependencies work correctly in production environment
  - Tested pip 25.3 upgrade process and build tool compatibility

### 📦 **Dependency Updates & Optimization** - 2025-11-15

- **Latest Package Versions** 🔄
  - Updated Flask to 3.0.0 (latest stable release)
  - Updated Flask-SQLAlchemy to 3.1.1 with improved performance
  - Updated Pillow to 10.1.0 for enhanced image processing
  - Updated Redis client to 5.0.1 for better async support
  - Updated cryptography to 41.0.8 for latest security patches
  - Updated all development and testing dependencies

- **Enhanced Dependency Management** 🛠️
  - Automatic pip and build tools upgrade during installation
  - Build essentials installation (python3-dev, build-essential)
  - Optional ML dependencies with version pinning for stability
  - Dependency verification after installation
  - Better error handling for missing or incompatible packages
  - Python version compatibility warnings and recommendations

- **Optimized Requirements Structure** 📋
  - Separated core dependencies from optional enterprise features
  - Removed duplicate psutil entries and version conflicts
  - Added proper version constraints for security and compatibility
  - Documented optional dependencies with installation flags
  - Cleaner requirements.txt with categorized sections

### 🚀 **Interactive Installation System** - 2025-11-15

- **One-Command Installer & Uninstaller** 📦
  - Created `getpanel.sh` - curl-installable script for instant deployment and removal
  - Interactive configuration wizard with step-by-step setup guidance
  - Complete uninstaller with safety checks and graceful service cleanup
  - Support for development, production, and custom installation modes
  - Non-interactive mode for automation and CI/CD pipelines
  - Automatic system requirements validation (Python 3.8+, Git, Curl)

- **Advanced Configuration Options** ⚙️
  - **Database Setup**: Interactive choice between SQLite and MariaDB with connection configuration
  - **Admin User Creation**: Secure password input with email configuration
  - **Application Settings**: Host, port, debug mode, and CAPTCHA preferences
  - **Production Services**: Nginx reverse proxy, SSL certificates, systemd services
  - **Optional Features**: Redis task queue, Discord webhook notifications

- **Smart Installation & Removal Features** ✨
  - Automatic system dependency detection and installation (apt/yum/apk)
  - Latest dependency versions with automated upgrade handling
  - Build essentials and development tools installation
  - Python version compatibility checking (3.8+ required, 3.11+ recommended)
  - Pip and build tools upgrade to latest versions
  - Optional ML/Analytics dependencies (numpy, scikit-learn, boto3)
  - Dependency verification with error handling
  - Secure environment file generation with random secret keys
  - MariaDB database and user creation with proper permissions
  - Nginx configuration with domain setup and SSL certificate provisioning
  - Systemd service configuration for production deployments
  - Complete uninstaller with service cleanup and safety confirmations
  - Graceful service shutdown and configuration removal
  - Comprehensive installation summary with next steps guidance

- **Enhanced Documentation** 📚
  - Complete README rewrite with modern structure and clear installation paths
  - Interactive installer documentation with configuration examples
  - Production deployment guide with automated service setup
  - Environment variable reference and customization options

### 🔐 **Captcha System Optimization** - 2025-11-15

- **Ultra-Compact Captcha Design** 📏
  - Reduced captcha image size to ultra-compact 50x25 pixels for better UI integration
  - Optimized font size to 16px for maximum clarity in small format
  - Implemented quality enhancement filters (SMOOTH + SHARPEN) for improved readability
  - Added comprehensive fallback calculations for character width optimization
  - Generated multiple test variations to validate optimization approaches

- **Enhanced Visual Quality** ✨
  - Applied dual image filters for crisp text rendering in compact format
  - Improved contrast and readability despite reduced dimensions
  - Maintained security standards while prioritizing user experience
  - Tested progressive zoom levels (100%, 300%, 900%) before settling on optimal size

- **Development Stability** 🛠️
  - Temporarily disabled enterprise monitoring systems for stable development
  - Resolved SQLAlchemy context management issues
  - Improved Flask application startup reliability
  - Created comprehensive test suite for captcha size variations

### 🚀 **Major Enterprise Features Added**

- **Real-Time Monitoring System** 📊
  - Live server metrics tracking (CPU, memory, disk, network usage)
  - Automated alerting with configurable thresholds
  - Player session monitoring and analytics
  - Interactive monitoring dashboard with Chart.js visualizations
  - Background monitoring threads with 30-second intervals
  - Performance trends and historical data analysis

- **Advanced Log Analytics Platform** 🔍
  - Machine learning-based anomaly detection using statistical analysis
  - Automated pattern recognition and baseline establishment
  - Security event detection and automated alerting
  - Log deduplication and intelligent parsing
  - Real-time log processing with queue management
  - Comprehensive log search and filtering capabilities

- **Multi-Server Management System** 🖥️
  - Cluster orchestration with automated scaling
  - SSH-based remote server management and deployment
  - Centralized configuration management across multiple servers
  - Load balancing and health monitoring
  - Automated deployment pipelines with rollback capabilities
  - Multi-server performance coordination

### 🎨 **User Interface Enhancements**

- **Theme Editor**: Admin can customize site CSS via `/admin/theme`
- **Server Logo Support**: Upload/manage logos with Theme Editor at `/theme_asset/<filename>`
- **Enhanced Navigation**: Hide `Dashboard` and `RCON` links unless user is logged in
- **Professional Dashboards**: Modern enterprise-grade monitoring interfaces
- **Responsive Design**: Mobile-friendly monitoring and management interfaces

### 🔒 **Security & Authentication Improvements**

- **Captcha Hardening** across all authentication flows:
  - Captcha required for Forgot Password (except testing environments)
  - Enhanced Login and Reset Password captcha with audio support via espeak
  - 3-minute captcha expiry with per-IP rate limiting
  - Testing mode bypasses for automated testing compatibility
  - Pillow 10+ compatibility fixes using `textbbox` with fallbacks

### 🛠️ **Technical Infrastructure**

- **Enterprise Database Models**: Comprehensive schema for monitoring, analytics, and cluster management
- **Background Processing**: Robust threading system for real-time data processing
- **Flask App Context**: Proper context management for background services
- **Modular Architecture**: Blueprint-based system for easy feature extension
- **SQLAlchemy Modernization**: Resolved deprecations, replaced `Query.get()` with `db.session.get()`

### 📦 **Installation & Deployment**

- **Enhanced Installation System**:
  - **Unified Management**: `panel.sh` - Single command for all operations
  - **Enterprise Install**: `scripts/install.sh` - Automated enterprise feature setup
  - **Smart Updates**: `scripts/update.sh` - Handles enterprise dependencies and migrations
  - **Clean Removal**: `scripts/uninstall.sh` - Removes all enterprise components
  - Cross-platform support (Linux, macOS, Alpine)
  - Automatic enterprise dependency management
  - Virtual environment setup with ML libraries
  - Enterprise database table initialization
  - Systemd service creation and management

- **Management Commands**:
  - `./panel.sh install` - Full enterprise installation
  - `./panel.sh start` - Development mode with minimal monitoring
  - `./panel.sh start-prod` - Production mode with full enterprise features
  - `./panel.sh monitoring` - Direct access to monitoring dashboard
  - `./panel.sh status` - Service health checks
  - `./panel.sh logs` - Centralized log viewing

- **Enhanced Dependencies**:
  - Enterprise monitoring: `psutil`, `paramiko`, `PyYAML`
  - Analytics capabilities: `numpy`, `scikit-learn` (optional)
  - Graceful fallback for systems without ML support
  - Updated requirements.txt with comprehensive dependency list

### 🐛 **Bug Fixes & Stability**

- Fixed Flask application context issues in background threads
- Resolved SQLAlchemy instance registration warnings
- Improved error handling and graceful degradation
- Enhanced startup reliability and service monitoring

## [scaffold-initial-2025-11-14] - 2025-11-14

- Initial scaffold merge: Flask backend, admin UI templates, deploy/systemd examples.
- Authentication flows (register/login/forgot), local captcha generation, and password rules.
- Server model, role-based access, admin server CRUD, and audit logging with streaming CSV export.
- Confirmation modal with accessibility improvements and keyboard handling.
- Tests: unit tests for auth/models/server UI and a Playwright E2E test scaffold for modal behavior.
- CI workflow and example `requirements.txt` including Playwright.
- Utility scripts and systemd units for RQ workers, memwatch, and autodeploy.

*(This file follows Keep a Changelog format in a minimal form.)*
