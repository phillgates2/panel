#!/bin/bash

# Comprehensive Interactive Installer for Panel Application
# Run with: curl -fsSL https://raw.githubusercontent.com/phillgates2/panel/main/install-interactive.sh | bash

set -e

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

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log_success "Linux detected"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    log_success "macOS detected"
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
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y git
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git
    fi
fi
log_success "Git is available"

# Interactive prompts
echo ""
log_info "Please provide the following information for installation:"

# Installation directory
read -p "Installation directory (default: ~/panel): " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-~/panel}
INSTALL_DIR=$(eval echo $INSTALL_DIR)  # Expand ~ if used

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

# Clone repository
log_info "Cloning Panel repository..."
if [[ -d "$INSTALL_DIR" ]]; then
    log_warning "Directory $INSTALL_DIR already exists. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone https://github.com/phillgates2/panel.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
log_info "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Database setup
if [[ $DB_CHOICE -eq 1 ]]; then
    log_info "Using SQLite database"
    export PANEL_SQLITE_URI="sqlite:///$INSTALL_DIR/panel.db"
elif [[ $DB_CHOICE -eq 2 ]]; then
    log_info "Setting up PostgreSQL..."
    # Install PostgreSQL if not present
    if ! command -v psql &> /dev/null; then
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get install -y postgresql postgresql-contrib
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install postgresql
        fi
    fi

    # Create database
    sudo -u postgres createuser --createdb panel_user
    sudo -u postgres createdb -O panel_user panel_db

    read -p "PostgreSQL password for panel_user: " -s DB_PASSWORD
    echo ""
    export PANEL_SQLITE_URI="postgresql://panel_user:$DB_PASSWORD@localhost/panel_db"
fi

# Redis setup
if [[ $INSTALL_REDIS == "y" ]]; then
    log_info "Installing Redis..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y redis-server
        sudo systemctl enable redis-server
        sudo systemctl start redis-server
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install redis
        brew services start redis
    fi
    export PANEL_REDIS_URL="redis://localhost:6379/0"
else
    read -p "Redis URL (default: redis://localhost:6379/0): " REDIS_URL
    export PANEL_REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
fi

# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export PANEL_SECRET_KEY="$SECRET_KEY"

# Create .env file
log_info "Creating configuration file..."
cat > .env << EOF
PANEL_SQLITE_URI=$PANEL_SQLITE_URI
PANEL_REDIS_URL=$PANEL_REDIS_URL
PANEL_SECRET_KEY=$SECRET_KEY
PANEL_ENV=development
EOF

# Initialize database
log_info "Initializing database..."
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized')
"

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
python3 app.py
EOF
chmod +x start.sh

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
log_info "Happy coding with Panel! ??"