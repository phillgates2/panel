#!/bin/bash

# Comprehensive Interactive Installer for Panel Application
# Run with: curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/scripts/install-interactive.sh | bash
# Or: bash install-interactive.sh [--dry-run] [--non-interactive]

set -e

# Command line options
DRY_RUN=false
NON_INTERACTIVE=false
DEV_MODE=false
DOCKER_MODE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run          Show what would be installed without making changes"
            echo "  --non-interactive  Use default values for all prompts"
            echo "  --dev              Setup development environment"
            echo "  --docker           Install via Docker Compose"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Welcome message
echo "========================================"
echo "  Panel Application Installer"
echo "========================================"
echo ""
log_info "Welcome to the interactive installer for the Panel application!"
echo ""

# Check system requirements
log_info "Checking system requirements..."

# Check disk space (need at least 500MB)
AVAIL_SPACE=$(df -m . | awk 'NR==2 {print $4}')
if [[ $AVAIL_SPACE -lt 500 ]]; then
    log_error "Insufficient disk space. Need at least 500MB, available: ${AVAIL_SPACE}MB"
    exit 1
fi
log_success "Disk space check passed (${AVAIL_SPACE}MB available)"

# Check memory (need at least 1GB)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TOTAL_MEM=$(free -m | awk 'NR==2 {print $2}')
    if [[ $TOTAL_MEM -lt 1024 ]]; then
        log_warning "Low memory detected: ${TOTAL_MEM}MB. Recommended: 2GB+"
    else
        log_success "Memory check passed (${TOTAL_MEM}MB)"
    fi
fi

# Detect OS and package manager
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log_success "Linux detected"
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
        PKG_UPDATE="sudo apt-get update"
        PKG_INSTALL="sudo apt-get install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_UPDATE="sudo yum check-update || true"
        PKG_INSTALL="sudo yum install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PKG_UPDATE="sudo dnf check-update || true"
        PKG_INSTALL="sudo dnf install -y"
    else
        log_error "No supported package manager found (apt-get, yum, dnf)"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    log_success "macOS detected"
    if ! command -v brew &> /dev/null; then
        log_warning "Homebrew not found. Install from https://brew.sh"
        exit 1
    fi
    PKG_MANAGER="brew"
    PKG_UPDATE="brew update"
    PKG_INSTALL="brew install"
else
    log_error "Unsupported OS: $OSTYPE"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    log_success "Python $PYTHON_VERSION detected"
else
    log_error "Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    log_warning "Git is not installed. Installing..."
    $PKG_UPDATE
    $PKG_INSTALL git || {
        log_error "Failed to install git. Please install manually."
        exit 1
    }
fi
GIT_VERSION=$(git --version | grep -oP '\d+\.\d+\.\d+' | head -1)
log_success "Git $GIT_VERSION is available"

# Handle Docker mode
if [[ $DOCKER_MODE == true ]]; then
    log_info "Installing Panel via Docker Compose..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_error "Docker Compose not found. Please install Docker Compose first."
        exit 1
    fi
    
    INSTALL_DIR=${INSTALL_DIR:-~/panel}
    INSTALL_DIR=$(eval echo $INSTALL_DIR)
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Clone or update
    if [[ -d ".git" ]]; then
        git pull origin main
    else
        git clone https://github.com/phillgates2/panel.git .
    fi
    
    # Copy appropriate docker-compose file
    if [[ $DEV_MODE == true ]]; then
        cp deploy/docker-compose.dev.yml docker-compose.yml
        log_info "Using development Docker Compose configuration"
    else
        cp docker-compose.yml docker-compose.production.yml
        log_info "Using production Docker Compose configuration"
    fi
    
    # Start services
    log_info "Starting Docker containers..."
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    log_success "Panel installed via Docker!"
    log_info "Access Panel at: http://localhost:5000"
    log_info "Manage containers: docker-compose ps"
    log_info "View logs: docker-compose logs -f"
    exit 0
fi

# Handle Development mode
if [[ $DEV_MODE == true ]]; then
    log_info "Setting up development environment..."
    NON_INTERACTIVE=false  # Allow prompts in dev mode for some options
    ENV_CHOICE=1
    DB_CHOICE=1  # Use SQLite for dev
    INSTALL_REDIS="y"
fi

# Interactive prompts
if [[ $NON_INTERACTIVE != true ]]; then
    echo ""
    log_info "Please provide the following information for installation:"
    
    # Installation directory
    read -p "Installation directory (default: ~/panel): " INSTALL_DIR
    INSTALL_DIR=${INSTALL_DIR:-~/panel}
    
    # Database choice
    echo ""
    echo "Database options:"
    echo "1. SQLite (default, easy setup)"
    echo "2. PostgreSQL (recommended for production)"
    read -p "Choose database [1-2]: " DB_CHOICE
    DB_CHOICE=${DB_CHOICE:-1}
    
    # Redis setup
    read -p "Install Redis locally? (y/n, default: y): " INSTALL_REDIS
    INSTALL_REDIS=${INSTALL_REDIS:-y}
    
    # Environment
    echo ""
    echo "Environment options:"
    echo "1. Development"
    echo "2. Production"
    read -p "Choose environment [1-2]: " ENV_CHOICE
    ENV_CHOICE=${ENV_CHOICE:-1}
    
    if [[ $ENV_CHOICE -eq 2 ]]; then
        read -p "Domain name (for SSL): " DOMAIN
        read -p "Email for SSL certificates: " SSL_EMAIL
    fi
else
    log_info "Running in non-interactive mode with defaults"
    INSTALL_DIR=${INSTALL_DIR:-~/panel}
    DB_CHOICE=${DB_CHOICE:-1}
    INSTALL_REDIS=${INSTALL_REDIS:-y}
    ENV_CHOICE=${ENV_CHOICE:-1}
fi
INSTALL_DIR=$(eval echo $INSTALL_DIR)  # Expand ~ if used

# Display configuration summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Installation Configuration Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📁 Install Directory: $INSTALL_DIR"
echo "  🗄️  Database: $(if [[ $DB_CHOICE -eq 1 ]]; then echo 'SQLite (Development)'; else echo 'PostgreSQL (Production)'; fi)"
echo "  ⚡ Redis: $(if [[ $INSTALL_REDIS == 'y' ]]; then echo 'Local Installation'; else echo 'External Connection'; fi)"
echo "  🌍 Environment: $(if [[ $ENV_CHOICE -eq 1 ]]; then echo 'Development'; else echo 'Production'; fi)"
if [[ $ENV_CHOICE -eq 2 && -n "$DOMAIN" ]]; then
    echo "  🔒 Domain: $DOMAIN"
    echo "  📧 SSL Email: $SSL_EMAIL"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ $DRY_RUN == true ]]; then
    log_info "DRY RUN MODE: Would install with above configuration"
    exit 0
fi

if [[ $NON_INTERACTIVE != true ]]; then
    read -p "Proceed with installation? (y/n): " PROCEED
    if [[ $PROCEED != "y" ]]; then
        log_info "Installation cancelled by user"
        exit 0
    fi
fi

# Validate and create installation directory
log_info "Preparing installation directory..."
if [[ -d "$INSTALL_DIR" ]]; then
    log_warning "Directory $INSTALL_DIR already exists."
    if [[ $NON_INTERACTIVE == true ]]; then
        log_info "Non-interactive mode: updating existing installation"
        DIR_ACTION=1
    else
        read -p "Choose action: [1] Update existing, [2] Backup and reinstall, [3] Abort: " DIR_ACTION
        DIR_ACTION=${DIR_ACTION:-1}
    fi
    
    case $DIR_ACTION in
        1)
            log_info "Updating existing installation..."
            cd "$INSTALL_DIR"
            if [[ -d ".git" ]]; then
                git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)" || true
                git pull origin main || {
                    log_error "Failed to update repository"
                    exit 1
                }
            else
                log_error "Directory exists but is not a git repository"
                exit 1
            fi
            ;;
        2)
            BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
            log_info "Creating backup at $BACKUP_DIR"
            mv "$INSTALL_DIR" "$BACKUP_DIR"
            git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR" || {
                log_error "Failed to clone repository. Restoring backup..."
                mv "$BACKUP_DIR" "$INSTALL_DIR"
                exit 1
            }
            cd "$INSTALL_DIR"
            log_success "Backup created at $BACKUP_DIR"
            ;;
        3)
            log_info "Installation aborted by user"
            exit 0
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac
else
    log_info "Cloning Panel repository..."
    git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR" || {
        log_error "Failed to clone repository"
        exit 1
    }
    cd "$INSTALL_DIR"
fi

# Create virtual environment
log_info "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip || {
    log_error "Failed to upgrade pip"
    exit 1
}

log_info "Installing required packages (this may take a few minutes)..."
if [[ -f "requirements/requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements/requirements.txt"
elif [[ -f "requirements.txt" ]]; then
    REQUIREMENTS_FILE="requirements.txt"
else
    log_error "requirements.txt not found"
    exit 1
fi

# Count packages
PKG_COUNT=$(grep -v '^#' "$REQUIREMENTS_FILE" | grep -v '^$' | wc -l)
log_info "Installing $PKG_COUNT packages from $REQUIREMENTS_FILE"

# Start timer
START_TIME=$(date +%s)

pip install -r "$REQUIREMENTS_FILE" || {
    log_error "Failed to install Python dependencies"
    log_info "Try running: pip install -r $REQUIREMENTS_FILE manually"
    exit 1
}

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
log_success "Python dependencies installed successfully ($ELAPSED seconds)"

# Database setup
if [[ $DB_CHOICE -eq 1 ]]; then
    log_info "Using SQLite database"
    export PANEL_DATABASE_URI="sqlite:///$INSTALL_DIR/panel.db"
    log_success "SQLite database will be created at: $INSTALL_DIR/panel.db"
elif [[ $DB_CHOICE -eq 2 ]]; then
    log_info "Setting up PostgreSQL..."
    
    # Install PostgreSQL if not present
    if ! command -v psql &> /dev/null; then
        log_warning "PostgreSQL not found. Installing..."
        $PKG_UPDATE
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            $PKG_INSTALL postgresql postgresql-contrib || {
                log_error "Failed to install PostgreSQL"
                exit 1
            }
            sudo systemctl enable postgresql
            sudo systemctl start postgresql
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            $PKG_INSTALL postgresql || {
                log_error "Failed to install PostgreSQL"
                exit 1
            }
            brew services start postgresql
        fi
        sleep 2  # Wait for PostgreSQL to start
    fi
    
    log_success "PostgreSQL is available"
    
    # Create database and user
    log_info "Creating database and user..."
    
    # Check if user already exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='panel_user'" | grep -q 1; then
        log_warning "User 'panel_user' already exists"
    else
        sudo -u postgres psql -c "CREATE USER panel_user WITH CREATEDB PASSWORD 'changeme';" || {
            log_error "Failed to create database user"
            exit 1
        }
    fi
    
    # Check if database already exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw panel_db; then
        log_warning "Database 'panel_db' already exists"
        if [[ $NON_INTERACTIVE == true ]]; then
            log_info "Non-interactive mode: using existing database"
        else
            read -p "Drop and recreate? (y/n): " DROP_DB
            if [[ $DROP_DB == "y" ]]; then
                sudo -u postgres dropdb panel_db
                sudo -u postgres createdb -O panel_user panel_db
            fi
        fi
    else
        sudo -u postgres createdb -O panel_user panel_db || {
            log_error "Failed to create database"
            exit 1
        }
    fi
    
    read -p "PostgreSQL password for panel_user (press Enter for default 'changeme'): " -s DB_PASSWORD
    echo ""
    DB_PASSWORD=${DB_PASSWORD:-changeme}
    
    # Update user password if changed
    if [[ "$DB_PASSWORD" != "changeme" ]]; then
        sudo -u postgres psql -c "ALTER USER panel_user WITH PASSWORD '$DB_PASSWORD';"
    fi
    
    export PANEL_DATABASE_URI="postgresql://panel_user:$DB_PASSWORD@localhost/panel_db"
    log_success "PostgreSQL database configured"
fi

# Redis setup
if [[ $INSTALL_REDIS == "y" ]]; then
    if ! command -v redis-cli &> /dev/null; then
        log_info "Installing Redis..."
        $PKG_UPDATE
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            $PKG_INSTALL redis-server || {
                log_error "Failed to install Redis"
                exit 1
            }
            sudo systemctl enable redis-server
            sudo systemctl start redis-server
            sleep 2
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            $PKG_INSTALL redis || {
                log_error "Failed to install Redis"
                exit 1
            }
            brew services start redis
            sleep 2
        fi
    fi
    
    # Verify Redis is running
    if redis-cli ping &> /dev/null; then
        REDIS_VERSION=$(redis-cli --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Redis $REDIS_VERSION is running"
    else
        log_error "Redis is installed but not responding"
        exit 1
    fi
    
    export PANEL_REDIS_URL="redis://localhost:6379/0"
else
    read -p "Redis URL (default: redis://localhost:6379/0): " REDIS_URL
    export PANEL_REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
    
    # Test Redis connection
    log_info "Testing Redis connection..."
    if timeout 3 redis-cli -u "$PANEL_REDIS_URL" ping &> /dev/null; then
        log_success "Redis connection successful"
    else
        log_warning "Could not connect to Redis at $PANEL_REDIS_URL"
        read -p "Continue anyway? (y/n): " CONTINUE
        if [[ $CONTINUE != "y" ]]; then
            exit 1
        fi
    fi
fi

# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export PANEL_SECRET_KEY="$SECRET_KEY"

# Create .env file
log_info "Creating configuration file..."

# Backup existing .env if present
if [[ -f ".env" ]]; then
    cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
    log_info "Existing .env backed up"
fi

ENV_TYPE=$(if [[ $ENV_CHOICE -eq 1 ]]; then echo "development"; else echo "production"; fi)

cat > .env << EOF
# Database Configuration
DATABASE_URL=$PANEL_DATABASE_URI
PANEL_DATABASE_URI=$PANEL_DATABASE_URI

# Redis Configuration
REDIS_URL=$PANEL_REDIS_URL
PANEL_REDIS_URL=$PANEL_REDIS_URL

# Application Configuration
SECRET_KEY=$SECRET_KEY
PANEL_SECRET_KEY=$SECRET_KEY
FLASK_ENV=$ENV_TYPE
PANEL_ENV=$ENV_TYPE

# Server Configuration
FLASK_APP=app.py
HOST=0.0.0.0
PORT=5000

# Security
SESSION_COOKIE_SECURE=$(if [[ $ENV_CHOICE -eq 2 ]]; then echo "True"; else echo "False"; fi)
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=$(if [[ $ENV_CHOICE -eq 1 ]]; then echo "DEBUG"; else echo "INFO"; fi)
EOF

# Add development-specific settings if in dev mode
if [[ $DEV_MODE == true ]]; then
    cat >> .env << 'EOF'

# Development Mode Settings
FLASK_DEBUG=True
TESTING=False
EXPLAIN_TEMPLATE_LOADING=True
PRESERVE_CONTEXT_ON_EXCEPTION=True

# Development Tools
SQLALCHEMY_ECHO=True
SQLALCHEMY_RECORD_QUERIES=True
SEND_FILE_MAX_AGE_DEFAULT=0

# Hot reload
FLASK_RUN_RELOAD=True
FLASK_RUN_DEBUGGER=True
EOF
    
    # Install development dependencies
    log_info "Installing development dependencies..."
    pip install -q -r requirements/development.txt || pip install -q pytest pytest-cov black flake8 mypy
    
    # Create development helper scripts
    cat > dev.sh << 'DEVSCRIPT'
#!/bin/bash
# Development helper script

case "${1:-run}" in
    run)
        echo "Starting development server with hot reload..."
        export FLASK_ENV=development
        export FLASK_DEBUG=1
        python -m flask run --reload --debugger
        ;;
    test)
        echo "Running tests..."
        pytest tests/ -v
        ;;
    lint)
        echo "Running linters..."
        black --check .
        flake8 app tests
        mypy app
        ;;
    format)
        echo "Formatting code..."
        black .
        ;;
    shell)
        echo "Starting Flask shell..."
        python -m flask shell
        ;;
    *)
        echo "Usage: ./dev.sh [run|test|lint|format|shell]"
        ;;
esac
DEVSCRIPT
    
    chmod +x dev.sh
    log_success "Development mode configured"
    log_info "Use ./dev.sh to run development server"
fi

log_success "Configuration file created at .env"

# Initialize database
log_info "Initializing database..."

# Check if migrations directory exists
if [[ -d "migrations" ]]; then
    log_info "Running database migrations..."
    python3 << EOF || {
        log_error "Database migration failed"
        exit 1
    }
try:
    from flask_migrate import upgrade
    from app import create_app
    
    app = create_app()
    with app.app_context():
        upgrade()
        print('✓ Database migrations completed')
except ImportError:
    print('⚠ Flask-Migrate not available, using db.create_all()')
    from app import create_app, db
    app = create_app()
    with app.app_context():
        db.create_all()
        print('✓ Database initialized')
except Exception as e:
    print(f'✗ Error: {e}')
    exit(1)
EOF
else
    python3 << EOF || {
        log_error "Database initialization failed"
        exit 1
    }
try:
    from app import create_app, db
    app = create_app()
    with app.app_context():
        db.create_all()
        print('✓ Database initialized')
except Exception as e:
    print(f'✗ Error: {e}')
    exit(1)
EOF
fi

log_success "Database ready"

# Create admin user
log_info "Setting up admin user..."
if [[ $NON_INTERACTIVE == true ]]; then
    log_info "Skipping admin user creation in non-interactive mode"
    log_info "Create admin user after installation using the application"
    CREATE_ADMIN=n
else
    read -p "Create admin user? (y/n, default: y): " CREATE_ADMIN
    CREATE_ADMIN=${CREATE_ADMIN:-y}
fi

if [[ $CREATE_ADMIN == "y" ]]; then
    read -p "Admin username (default: admin): " ADMIN_USER
    ADMIN_USER=${ADMIN_USER:-admin}
    
    read -p "Admin email: " ADMIN_EMAIL
    while [[ ! "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; do
        log_warning "Invalid email format"
        read -p "Admin email: " ADMIN_EMAIL
    done
    
    read -p "Admin password: " -s ADMIN_PASSWORD
    echo ""
    read -p "Confirm password: " -s ADMIN_PASSWORD_CONFIRM
    echo ""
    
    if [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]]; then
        log_error "Passwords do not match"
    else
        python3 << EOF || log_warning "Failed to create admin user"
try:
    from app import create_app, db
    from app.models import User
    from werkzeug.security import generate_password_hash
    
    app = create_app()
    with app.app_context():
        # Check if user exists
        existing_user = User.query.filter_by(username='$ADMIN_USER').first()
        if existing_user:
            print('⚠ User $ADMIN_USER already exists')
        else:
            admin = User(
                username='$ADMIN_USER',
                email='$ADMIN_EMAIL',
                password=generate_password_hash('$ADMIN_PASSWORD'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('✓ Admin user created successfully')
except Exception as e:
    print(f'⚠ Could not create admin user: {e}')
    print('You can create an admin user later using the application')
EOF
    fi
fi

# Create systemd service for production
if [[ $ENV_CHOICE -eq 2 ]]; then
    log_info "Setting up production service..."

    # Create service file
    sudo tee /etc/systemd/system/panel.service > /dev/null << EOF
[Unit]
Description=Panel Application
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable panel
    sudo systemctl start panel

    # Setup nginx
    if ! command -v nginx &> /dev/null; then
        sudo apt-get install -y nginx
    fi

    sudo tee /etc/nginx/sites-available/panel > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/panel /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx

    # SSL with Let's Encrypt
    if [[ -n "$DOMAIN" && -n "$SSL_EMAIL" ]]; then
        sudo apt-get install -y certbot python3-certbot-nginx
        sudo certbot --nginx -d $DOMAIN --email $SSL_EMAIL --agree-tos --non-interactive
    fi
fi

# Create start script
log_info "Creating start script..."
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export $(cat .env | xargs)

# Check if port 5000 is available
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 5000 is already in use"
    echo "Stop the process using: kill \$(lsof -t -i:5000)"
    exit 1
fi

python3 app.py
EOF
chmod +x start.sh

# Create a quick test script
log_info "Creating test script..."
cat > test.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export $(cat .env | xargs)

echo "Running application tests..."
if command -v pytest &> /dev/null && [ -d "tests" ]; then
    pytest tests/ -v --maxfail=3
else
    echo "⚠️  pytest not installed or tests directory not found"
    echo "Install with: pip install pytest"
fi
EOF
chmod +x test.sh

# Copy utility scripts from scripts directory
log_info "Copying utility scripts..."
if [[ -f "scripts/status.sh" ]]; then
    cp scripts/status.sh ./status.sh
    chmod +x status.sh
fi
if [[ -f "scripts/uninstall.sh" ]]; then
    cp scripts/uninstall.sh ./uninstall.sh
    chmod +x uninstall.sh
fi

log_success "Helper scripts created (start.sh, test.sh, status.sh, uninstall.sh)"

# Success message
echo ""
log_success "Panel installation completed!"
echo ""
echo "Installation Summary:"
echo "- Installed in: $INSTALL_DIR"
echo "- Database: $(if [[ $DB_CHOICE -eq 1 ]]; then echo 'SQLite'; else echo 'PostgreSQL'; fi)"
echo "- Redis: $(if [[ $INSTALL_REDIS == 'y' ]]; then echo 'Local'; else echo 'External'; fi)"
echo "- Environment: $(if [[ $ENV_CHOICE -eq 1 ]]; then echo 'Development'; else echo 'Production'; fi)"
echo ""
echo "To start the application:"
if [[ $ENV_CHOICE -eq 1 ]]; then
    echo "  cd $INSTALL_DIR && ./start.sh"
else
    echo "  sudo systemctl status panel"
fi
echo ""
echo "Access the application at: http://localhost:5000"
if [[ $ENV_CHOICE -eq 2 && -n "$DOMAIN" ]]; then
    echo "Or with SSL at: https://$DOMAIN"
fi
echo ""
# Post-installation health check
log_info "Running post-installation checks..."

ECHO_CHECKS=""

# Check virtual environment
if [[ -d "venv" ]]; then
    ECHO_CHECKS="${ECHO_CHECKS}✓ Virtual environment created\n"
else
    ECHO_CHECKS="${ECHO_CHECKS}✗ Virtual environment missing\n"
fi

# Check .env file
if [[ -f ".env" ]]; then
    ECHO_CHECKS="${ECHO_CHECKS}✓ Configuration file created\n"
else
    ECHO_CHECKS="${ECHO_CHECKS}✗ Configuration file missing\n"
fi

# Check database
if [[ $DB_CHOICE -eq 1 ]] && [[ -f "panel.db" ]]; then
    ECHO_CHECKS="${ECHO_CHECKS}✓ SQLite database created\n"
elif [[ $DB_CHOICE -eq 2 ]]; then
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw panel_db; then
        ECHO_CHECKS="${ECHO_CHECKS}✓ PostgreSQL database exists\n"
    else
        ECHO_CHECKS="${ECHO_CHECKS}✗ PostgreSQL database not found\n"
    fi
fi

# Check Redis connection
if redis-cli -u "$PANEL_REDIS_URL" ping &> /dev/null 2>&1; then
    ECHO_CHECKS="${ECHO_CHECKS}✓ Redis connection working\n"
else
    ECHO_CHECKS="${ECHO_CHECKS}⚠ Redis connection failed\n"
fi

echo -e "\n${ECHO_CHECKS}"

log_info "Installation log available in current directory"

if [[ $ENV_CHOICE -eq 1 ]]; then
    log_info "To start development server:"
    echo "  cd $INSTALL_DIR"
    echo "  source venv/bin/activate"
    echo "  ./start.sh"
fi

log_info "For troubleshooting, check:"
echo "  - Configuration: $INSTALL_DIR/.env"
echo "  - Database file: $INSTALL_DIR/panel.db (if using SQLite)"
echo "  - Application logs when running"
echo ""

# Quick start guide
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Quick Start Guide:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Start the application:"
echo "   cd $INSTALL_DIR"
if [[ $ENV_CHOICE -eq 1 ]]; then
    echo "   ./start.sh"
else
    echo "   sudo systemctl start panel"
    echo "   sudo systemctl status panel"
fi
echo ""
echo "2️⃣  Access the application:"
echo "   🌐 http://localhost:5000"
if [[ $ENV_CHOICE -eq 2 && -n "$DOMAIN" ]]; then
    echo "   🔒 https://$DOMAIN"
fi
echo ""
echo "3️⃣  Check status:"
echo "   ./status.sh"
echo ""
echo "4️⃣  Run tests (optional):"
echo "   ./test.sh"
echo ""
echo "5️⃣  View logs:"
echo "   tail -f logs/app.log"
echo ""
echo "6️⃣  Stop the application:"
if [[ $ENV_CHOICE -eq 1 ]]; then
    echo "   Ctrl+C in the terminal running start.sh"
else
    echo "   sudo systemctl stop panel"
fi
echo ""
echo "7️⃣  Uninstall (if needed):"
echo "   ./uninstall.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
log_success "🎉 Installation complete! Happy coding with Panel! 🚀"
echo ""
log_info "Need help? Check the documentation:"
echo "   📖 https://github.com/phillgates2/panel/blob/main/README.md"
echo "   💬 https://github.com/phillgates2/panel/discussions"
echo ""