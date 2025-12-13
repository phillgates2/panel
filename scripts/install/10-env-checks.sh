#!/bin/bash

install_env_checks() {
    # Root check
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user with sudo access."
        exit 1
    fi

    log_info "Checking system requirements..."

    # Disk space
    local avail_space
    avail_space=$(df -m . | awk 'NR==2 {print $4}')
    if [[ $avail_space -lt 500 ]]; then
        log_error "Insufficient disk space. Need at least 500MB, available: ${avail_space}MB"
        exit 1
    fi
    log_success "Disk space check passed (${avail_space}MB available)"

    # Memory
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        local total_mem
        total_mem=$(free -m | awk 'NR==2 {print $2}')
        if [[ $total_mem -lt 1024 ]]; then
            log_warning "Low memory detected: ${total_mem}MB. Recommended: 2GB+"
        else
            log_success "Memory check passed (${total_mem}MB)"
        fi
    fi

    # OS / package manager
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Linux detected"
        PKG_MANAGER=$(detect_package_manager)
        case $PKG_MANAGER in
            apt)
                PKG_UPDATE="sudo apt-get update"
                PKG_INSTALL="sudo apt-get install -y"
                ;;
            yum)
                PKG_UPDATE="sudo yum check-update || true"
                PKG_INSTALL="sudo yum install -y"
                ;;
            dnf)
                PKG_UPDATE="sudo dnf check-update || true"
                PKG_INSTALL="sudo dnf install -y"
                ;;
            zypper)
                PKG_UPDATE="sudo zypper refresh"
                PKG_INSTALL="sudo zypper install -y"
                ;;
            pacman)
                PKG_UPDATE="sudo pacman -Sy"
                PKG_INSTALL="sudo pacman -S --noconfirm"
                ;;
            apk)
                PKG_UPDATE="sudo apk update"
                PKG_INSTALL="sudo apk add --no-cache"
                ;;
            *)
                log_error "No supported package manager found"
                exit 1
                ;;
        esac
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

    # Python
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

    # Git
    if ! command -v git &> /dev/null; then
        log_warning "Git is not installed. Installing..."
        $PKG_UPDATE
        $PKG_INSTALL git || {
            log_error "Failed to install git. Please install manually."
            exit 1
        }
    fi
    GIT_VERSION=$(git --version | grep -oE '\\d+\\.\\d+\\.\\d+' | head -1)
    log_success "Git $GIT_VERSION is available"
}
