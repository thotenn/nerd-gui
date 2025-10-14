#!/bin/bash
#
# Nerd-Dictation Installation Script for Ubuntu 24.04
# This script installs and configures nerd-dictation with Spanish and English models
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
INSTALL_DIR="$HOME/app_folder"
NERD_DICTATION_DIR="$INSTALL_DIR/nerd-dictation"
MODELS_DIR="$HOME/.config/nerd-dictation"

# Functions
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

# Check if running on Ubuntu
check_ubuntu() {
    if [ ! -f /etc/lsb-release ]; then
        print_error "This script is designed for Ubuntu"
        exit 1
    fi
    
    source /etc/lsb-release
    if [ "$DISTRIB_ID" != "Ubuntu" ]; then
        print_error "This script is designed for Ubuntu"
        exit 1
    fi
    
    print_success "Running on Ubuntu $DISTRIB_RELEASE"
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3-pip \
        python3-venv \
        portaudio19-dev \
        xdotool \
        pulseaudio-utils \
        alsa-utils \
        git \
        wget \
        unzip
    
    print_success "System dependencies installed"
}

# Clone and setup nerd-dictation
install_nerd_dictation() {
    print_status "Installing nerd-dictation..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Clone repository if not exists
    if [ -d "$NERD_DICTATION_DIR" ]; then
        print_warning "nerd-dictation directory already exists, skipping clone"
        cd "$NERD_DICTATION_DIR"
        git pull
    else
        git clone https://github.com/ideasman42/nerd-dictation.git
        cd "$NERD_DICTATION_DIR"
    fi
    
    # Create virtual environment
    print_status "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate venv and install dependencies
    print_status "Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install vosk sounddevice
    pip install .
    deactivate
    
    print_success "nerd-dictation installed successfully"
}

# Download Vosk models
download_models() {
    print_status "Downloading Vosk models..."
    
    mkdir -p "$MODELS_DIR"
    cd "$MODELS_DIR"
    
    # Spanish model (small - ~40MB)
    if [ ! -d "vosk-model-small-es-0.42" ]; then
        print_status "Downloading Spanish model (small)..."
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
        unzip -q vosk-model-small-es-0.42.zip
        rm vosk-model-small-es-0.42.zip
        print_success "Spanish model downloaded"
    else
        print_warning "Spanish model already exists, skipping"
    fi
    
    # English model (small - ~40MB)
    if [ ! -d "vosk-model-small-en-us-0.15" ]; then
        print_status "Downloading English model (small)..."
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        print_success "English model downloaded"
    else
        print_warning "English model already exists, skipping"
    fi
    
    print_success "Models downloaded successfully"
}

# Optional: Download large models for better accuracy
download_large_models() {
    print_status "Would you like to download large models for better accuracy? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        cd "$MODELS_DIR"
        
        # Spanish large model (~1.5GB)
        if [ ! -d "vosk-model-es-0.42" ]; then
            print_status "Downloading Spanish model (large - 1.5GB)..."
            wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
            unzip -q vosk-model-es-0.42.zip
            rm vosk-model-es-0.42.zip
            print_success "Spanish large model downloaded"
        else
            print_warning "Spanish large model already exists"
        fi
        
        # English large model (~1.8GB)
        if [ ! -d "vosk-model-en-us-0.22" ]; then
            print_status "Downloading English model (large - 1.8GB)..."
            wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
            unzip -q vosk-model-en-us-0.22.zip
            rm vosk-model-en-us-0.22.zip
            print_success "English large model downloaded"
        else
            print_warning "English large model already exists"
        fi
    else
        print_status "Skipping large models"
    fi
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test if nerd-dictation runs
    cd "$NERD_DICTATION_DIR"
    if ./nerd-dictation --help > /dev/null 2>&1; then
        print_success "nerd-dictation executable works"
    else
        print_error "nerd-dictation executable test failed"
        exit 1
    fi
    
    # Test if parec is available
    if command -v parec &> /dev/null; then
        print_success "PulseAudio (parec) is available"
    else
        print_error "PulseAudio (parec) not found"
        exit 1
    fi
    
    # Check if models exist
    model_count=$(find "$MODELS_DIR" -maxdepth 1 -type d -name "vosk-model-*" | wc -l)
    if [ "$model_count" -gt 0 ]; then
        print_success "Found $model_count Vosk model(s)"
    else
        print_error "No Vosk models found"
        exit 1
    fi
}

# Create bash aliases
create_aliases() {
    print_status "Creating bash aliases..."
    
    BASHRC="$HOME/.bashrc"
    
    # Check if aliases already exist
    if grep -q "# Nerd-Dictation aliases" "$BASHRC"; then
        print_warning "Aliases already exist in .bashrc, skipping"
        return
    fi
    
    # Add aliases
    cat >> "$BASHRC" << 'EOF'

# Nerd-Dictation aliases
alias dictado-es='cd ~/app_folder/nerd-dictation && ./nerd-dictation begin --vosk-model-dir=$HOME/.config/nerd-dictation/vosk-model-small-es-0.42'
alias dictado-en='cd ~/app_folder/nerd-dictation && ./nerd-dictation begin --vosk-model-dir=$HOME/.config/nerd-dictation/vosk-model-small-en-us-0.15'
alias dictado-stop='cd ~/app_folder/nerd-dictation && ./nerd-dictation end'
EOF
    
    print_success "Aliases added to .bashrc"
    print_warning "Run 'source ~/.bashrc' or restart terminal to use aliases"
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Installation completed successfully! 🎉              ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo ""
    echo -e "  ${YELLOW}Start Spanish dictation:${NC}"
    echo -e "    dictado-es"
    echo ""
    echo -e "  ${YELLOW}Start English dictation:${NC}"
    echo -e "    dictado-en"
    echo ""
    echo -e "  ${YELLOW}Stop dictation:${NC}"
    echo -e "    dictado-stop"
    echo ""
    echo -e "${BLUE}Manual usage:${NC}"
    echo ""
    echo -e "  cd $NERD_DICTATION_DIR"
    echo -e "  ./nerd-dictation begin --vosk-model-dir=$MODELS_DIR/vosk-model-small-es-0.42"
    echo -e "  ./nerd-dictation end"
    echo ""
    echo -e "${BLUE}Locations:${NC}"
    echo ""
    echo -e "  nerd-dictation: ${YELLOW}$NERD_DICTATION_DIR${NC}"
    echo -e "  Vosk models:    ${YELLOW}$MODELS_DIR${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo ""
    echo -e "  1. Run: ${YELLOW}source ~/.bashrc${NC}"
    echo -e "  2. Test with: ${YELLOW}dictado-es${NC}"
    echo -e "  3. Speak in Spanish, text will appear where your cursor is"
    echo -e "  4. Stop with: ${YELLOW}dictado-stop${NC}"
    echo ""
}

# Main installation process
main() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║      Nerd-Dictation Installation Script for Ubuntu 24.04      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_ubuntu
    install_dependencies
    install_nerd_dictation
    download_models
    download_large_models
    test_installation
    create_aliases
    print_usage
    
    print_success "All done!"
}

# Run main function
main