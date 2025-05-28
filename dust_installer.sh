#!/bin/bash

# dust-installer.sh - Standalone installer and runner for du-dust
# A terminal-based treemap visualization tool for disk usage analysis

set -e

# Configuration
DUST_VERSION="1.1.1"
INSTALL_DIR="$HOME/.local/bin"
DUST_BINARY="$INSTALL_DIR/dust"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# Detect system architecture and OS
detect_system() {
    local os=""
    local arch=""
    
    case "$(uname -s)" in
        Linux*)  os="unknown-linux-gnu" ;;
        Darwin*) os="apple-darwin" ;;
        CYGWIN*|MINGW*|MSYS*) os="pc-windows-msvc"; DUST_BINARY="$DUST_BINARY.exe" ;;
        *) log_error "Unsupported operating system: $(uname -s)"; exit 1 ;;
    esac
    
    case "$(uname -m)" in
        x86_64|amd64) arch="x86_64" ;;
        aarch64|arm64) arch="aarch64" ;;
        armv7l) arch="armv7" ;;
        *) log_error "Unsupported architecture: $(uname -m)"; exit 1 ;;
    esac
    
    echo "${arch}-${os}"
}

# Check if dust is already installed
check_existing_installation() {
    if command -v dust >/dev/null 2>&1; then
        log_info "dust is already available in PATH: $(which dust)"
        log_info "Version: $(dust --version 2>/dev/null || echo 'unknown')"
        return 0
    elif [ -f "$DUST_BINARY" ]; then
        log_info "dust found in local installation: $DUST_BINARY"
        return 0
    fi
    return 1
}

# Install using package manager if available
try_package_manager() {
    log_info "Attempting to install via package manager..."
    
    if command -v cargo >/dev/null 2>&1; then
        log_info "Installing via cargo..."
        cargo install du-dust
        return $?
    elif command -v brew >/dev/null 2>&1; then
        log_info "Installing via homebrew..."
        brew install dust
        return $?
    elif command -v apt >/dev/null 2>&1; then
        log_info "Installing via apt..."
        sudo apt update && sudo apt install -y du-dust
        return $?
    elif command -v pacman >/dev/null 2>&1; then
        log_info "Installing via pacman..."
        sudo pacman -S --noconfirm dust
        return $?
    elif command -v yum >/dev/null 2>&1; then
        log_info "Installing via yum..."
        sudo yum install -y du-dust
        return $?
    fi
    
    return 1
}

# Download and install binary
install_binary() {
    local target=$(detect_system)
    local filename="dust-v${DUST_VERSION}-${target}.tar.gz"
    local url="https://github.com/bootandy/dust/releases/download/v${DUST_VERSION}/${filename}"
    local temp_dir=$(mktemp -d)
    
    log_info "Downloading dust binary for ${target}..."
    log_info "URL: $url"
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Download
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "$temp_dir/$filename" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$temp_dir/$filename" "$url"
    else
        log_error "Neither curl nor wget found. Please install one of them."
        exit 1
    fi
    
    # Extract and install
    log_info "Extracting and installing..."
    cd "$temp_dir"
    tar -xzf "$filename"
    
    # Find the dust binary (it might be in a subdirectory)
    local dust_src=$(find . -name "dust" -type f -executable | head -n1)
    if [ -z "$dust_src" ]; then
        log_error "Could not find dust binary in downloaded archive"
        exit 1
    fi
    
    cp "$dust_src" "$DUST_BINARY"
    chmod +x "$DUST_BINARY"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_success "dust installed to $DUST_BINARY"
}

# Add to PATH if not already there
setup_path() {
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        log_info "Adding $INSTALL_DIR to PATH..."
        
        # Add to current session
        export PATH="$INSTALL_DIR:$PATH"
        
        # Add to shell rc files
        for rc_file in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
            if [ -f "$rc_file" ]; then
                if ! grep -q "$INSTALL_DIR" "$rc_file"; then
                    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$rc_file"
                    log_info "Added to $rc_file"
                fi
            fi
        done
    fi
}

# Main installation function
install_dust() {
    log_info "Starting dust installation..."
    
    if check_existing_installation; then
        log_success "dust is already installed!"
        return 0
    fi
    
    # Try package manager first
    if try_package_manager; then
        log_success "dust installed via package manager!"
        return 0
    fi
    
    # Fall back to binary installation
    log_info "Package manager installation failed, trying binary installation..."
    install_binary
    setup_path
    
    # Verify installation
    if [ -f "$DUST_BINARY" ]; then
        log_success "dust successfully installed!"
        return 0
    else
        log_error "Installation failed"
        return 1
    fi
}

# Run dust with optimized settings for tmux
run_dust() {
    local dust_cmd=""
    local target_path="${1:-.}"
    
    # Find dust command
    if command -v dust >/dev/null 2>&1; then
        dust_cmd="dust"
    elif [ -f "$DUST_BINARY" ]; then
        dust_cmd="$DUST_BINARY"
    else
        log_error "dust not found. Please run with --install first."
        exit 1
    fi
    
    # Get terminal dimensions for tmux compatibility
    local cols=$(tput cols 2>/dev/null || echo "80")
    local lines=$(tput lines 2>/dev/null || echo "24")
    
    log_info "Running dust analysis on: $target_path"
    log_info "Terminal size: ${cols}x${lines}"
    echo
    
    # Run dust with tmux-optimized settings
    TERM=xterm-256color "$dust_cmd" \
        --depth 4 \
        --number-of-lines $((lines - 10)) \
        --terminal-width "$cols" \
        --reverse \
        --no-percent-bars \
        "$target_path"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS] [PATH]"
    echo
    echo "A standalone installer and runner for dust (du + rust)"
    echo "Creates terminal-based treemap visualizations for disk usage"
    echo
    echo "OPTIONS:"
    echo "  --install, -i     Install dust if not already available"
    echo "  --help, -h        Show this help message"
    echo "  --version, -v     Show version information"
    echo
    echo "EXAMPLES:"
    echo "  $0 --install      # Install dust"
    echo "  $0                # Analyze current directory"
    echo "  $0 /home/user     # Analyze specific directory"
    echo "  $0 --install .    # Install and then analyze current directory"
    echo
    echo "TMUX Integration:"
    echo "  # Add to tmux.conf:"
    echo "  bind-key D new-window -n 'disk-usage' '$0'"
    echo "  bind-key d split-window -h '$0'"
}

# Main script logic
main() {
    case "${1:-}" in
        --install|-i)
            install_dust
            if [ -n "${2:-}" ]; then
                echo
                run_dust "$2"
            fi
            ;;
        --help|-h)
            show_usage
            ;;
        --version|-v)
            echo "dust-installer.sh v1.0"
            if command -v dust >/dev/null 2>&1 || [ -f "$DUST_BINARY" ]; then
                echo "dust version: $(dust --version 2>/dev/null || echo 'unknown')"
            fi
            ;;
        *)
            # Check if dust is available, install if not
            if ! check_existing_installation; then
                log_warning "dust not found. Installing automatically..."
                install_dust
                echo
            fi
            run_dust "${1:-.}"
            ;;
    esac
}

# Run main function with all arguments
main "$@"