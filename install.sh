#!/bin/bash
#
# Dictation Manager Installation Script for Ubuntu 24.04
# Supports both Vosk (CPU) and Whisper (GPU) backends
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NERD_DICTATION_DIR="$PROJECT_DIR/apps/nerd-dictation"  # Use integrated copy
MODELS_DIR="$HOME/.config/nerd-dictation"

# Installation flags
INSTALL_VOSK=false
INSTALL_WHISPER=false

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

print_header() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║      $1${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
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

# Check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        print_error "Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Choose backends to install
choose_backends() {
    print_header "Backend Selection"

    echo "This installer supports two backends:"
    echo ""
    echo "  1) Vosk (CPU-based, via nerd-dictation)"
    echo "     - Fast, lightweight"
    echo "     - ~90% accuracy"
    echo "     - Works on any computer"
    echo ""
    echo "  2) Whisper (GPU-accelerated)"
    echo "     - High accuracy (95-97%)"
    echo "     - Requires NVIDIA GPU (recommended)"
    echo "     - Built-in punctuation"
    echo ""
    echo "  3) Both (Recommended - allows switching)"
    echo ""

    read -p "Choose installation (1/2/3): " choice

    case $choice in
        1)
            INSTALL_VOSK=true
            print_status "Will install: Vosk backend"
            ;;
        2)
            INSTALL_WHISPER=true
            print_status "Will install: Whisper backend"
            ;;
        3)
            INSTALL_VOSK=true
            INSTALL_WHISPER=true
            print_status "Will install: Both backends"
            ;;
        *)
            print_error "Invalid choice. Please run again."
            exit 1
            ;;
    esac
    echo ""
}

# Install common system dependencies
install_common_dependencies() {
    print_status "Installing common system dependencies..."

    sudo apt update

    # Common packages
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-tk \
        portaudio19-dev \
        xdotool \
        pulseaudio-utils \
        alsa-utils \
        git \
        wget \
        unzip \
        gcc \
        g++ \
        make \
        cmake \
        pkg-config

    print_success "xdotool installed (required for Voice Commands feature)"

    print_success "Common dependencies installed"
}

# ============================================================================
# VOSK BACKEND INSTALLATION
# ============================================================================

install_vosk_backend() {
    print_header "Installing Vosk Backend (nerd-dictation)"

    # Check if integrated nerd-dictation exists
    if [ ! -d "$NERD_DICTATION_DIR" ]; then
        print_error "Integrated nerd-dictation not found at $NERD_DICTATION_DIR"
        print_error "Please ensure you cloned the repository correctly"
        exit 1
    fi

    print_status "Using integrated nerd-dictation at: $NERD_DICTATION_DIR"
    cd "$NERD_DICTATION_DIR"

    # Note: nerd-dictation is now integrated into this repository
    # Updates will come through the main repository, not as a separate git submodule
    print_success "Using integrated nerd-dictation (version controlled with main repo)"

    # Create virtual environment for nerd-dictation
    if [ -d "venv" ]; then
        print_status "Virtual environment already exists"
    else
        print_status "Creating virtual environment for nerd-dictation..."
        python3 -m venv venv
    fi

    # Install dependencies
    print_status "Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip

    # Install from requirements.txt if available, otherwise use manual installation
    if [ -f "requirements.txt" ]; then
        print_status "Installing from requirements.txt..."
        pip install -r requirements.txt
    else
        print_warning "requirements.txt not found, installing manually..."
        pip install vosk sounddevice
    fi

    pip install .
    deactivate

    print_success "nerd-dictation configured"
}

download_vosk_models() {
    print_status "Downloading Vosk models..."

    mkdir -p "$MODELS_DIR"
    cd "$MODELS_DIR"

    # Spanish model (small - ~40MB)
    if [ ! -d "vosk-model-small-es-0.42" ]; then
        print_status "Downloading Spanish model (small - ~40MB)..."
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
        unzip -q vosk-model-small-es-0.42.zip
        rm vosk-model-small-es-0.42.zip
        print_success "Spanish model downloaded"
    else
        print_success "Spanish model already exists"
    fi

    # English model (small - ~40MB)
    if [ ! -d "vosk-model-small-en-us-0.15" ]; then
        print_status "Downloading English model (small - ~40MB)..."
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        print_success "English model downloaded"
    else
        print_success "English model already exists"
    fi

    # Optional: Large models
    echo ""
    print_status "Download large models for better accuracy? (~1.5GB each) (y/N)"
    read -r response

    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        cd "$MODELS_DIR"

        if [ ! -d "vosk-model-es-0.42" ]; then
            print_status "Downloading Spanish large model (1.5GB)..."
            wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
            unzip -q vosk-model-es-0.42.zip
            rm vosk-model-es-0.42.zip
            print_success "Spanish large model downloaded"
        fi

        if [ ! -d "vosk-model-en-us-0.22" ]; then
            print_status "Downloading English large model (1.8GB)..."
            wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
            unzip -q vosk-model-en-us-0.22.zip
            rm vosk-model-en-us-0.22.zip
            print_success "English large model downloaded"
        fi
    fi
}

# ============================================================================
# WHISPER BACKEND INSTALLATION
# ============================================================================

install_whisper_backend() {
    print_header "Installing Whisper Backend (GPU-accelerated)"

    cd "$PROJECT_DIR"

    # Check Python version
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $PYTHON_VERSION"

    if ! python3 -c "import sys; assert sys.version_info >= (3, 8)" 2>/dev/null; then
        print_error "Python 3.8 or higher is required"
        exit 1
    fi

    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        print_status "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1
        HAS_GPU=true
    else
        print_warning "NVIDIA GPU not detected. Whisper will run on CPU (slower)"
        print_warning "For GPU acceleration, install NVIDIA drivers first"
        HAS_GPU=false
    fi
    echo ""

    # Create virtual environment for Whisper
    print_status "Creating virtual environment for Whisper..."
    python3 -m venv venv

    # Activate and install dependencies
    print_status "Installing Whisper Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip

    # Install from requirements.txt
    if [ -f "requirements.txt" ]; then
        print_status "Installing from requirements.txt..."
        pip install -r requirements.txt

        # Install cuDNN for GPU support
        if [ "$HAS_GPU" = true ]; then
            print_status "Installing NVIDIA cuDNN for GPU acceleration..."
            pip install nvidia-cudnn-cu12 || print_warning "cuDNN installation failed (optional)"
            print_success "cuDNN installed"
        fi
    else
        print_error "requirements.txt not found in project root!"
        exit 1
    fi

    # Test installation
    print_status "Testing Whisper installation..."
    python -c "
from faster_whisper import WhisperModel
import torch
print('✓ faster-whisper imported successfully')

# Test model loading
print('Testing model loading (will download tiny model)...')
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Using device: {device}')
model = WhisperModel('tiny', device=device, compute_type='float16' if device == 'cuda' else 'float32')
print('✓ Whisper model loaded successfully')
print('✓ All Whisper dependencies working!')
" || {
    print_error "Whisper installation test failed"
    exit 1
}

    deactivate
    print_success "Whisper backend installed"
}

# ============================================================================
# CONFIGURATION
# ============================================================================

configure_environment() {
    print_header "Configuration"

    cd "$PROJECT_DIR"
    ENV_FILE="$PROJECT_DIR/.env"

    # Create .env from example if doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            print_status "Creating .env file from .env.example..."
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_status ".env file already exists"
        # Backup existing
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        print_status "Backed up existing .env"
    fi

    # Configure paths
    print_status "Configuring paths in .env..."

    # Update APP_DIR
    if grep -q "^APP_DIR=" "$ENV_FILE"; then
        sed -i "s|^APP_DIR=.*|APP_DIR=$PROJECT_DIR|" "$ENV_FILE"
    else
        echo "APP_DIR=$PROJECT_DIR" >> "$ENV_FILE"
    fi

    # Configure based on what was installed
    if [ "$INSTALL_VOSK" = true ]; then
        # Note: NERD_DICTATION_DIR is optional now (defaults to apps/nerd-dictation)
        # Only set MODELS_DIR
        if grep -q "^MODELS_DIR=" "$ENV_FILE"; then
            sed -i "s|^MODELS_DIR=.*|MODELS_DIR=$MODELS_DIR|" "$ENV_FILE"
        else
            echo "MODELS_DIR=$MODELS_DIR" >> "$ENV_FILE"
        fi
    fi

    # Set default backend
    if [ "$INSTALL_WHISPER" = true ] && [ "$INSTALL_VOSK" = false ]; then
        # Whisper only
        if grep -q "^BACKEND=" "$ENV_FILE"; then
            sed -i "s/^BACKEND=.*/BACKEND=whisper/" "$ENV_FILE"
        else
            echo "BACKEND=whisper" >> "$ENV_FILE"
        fi
        print_status "Default backend set to: Whisper"
    elif [ "$INSTALL_VOSK" = true ] && [ "$INSTALL_WHISPER" = false ]; then
        # Vosk only
        if grep -q "^BACKEND=" "$ENV_FILE"; then
            sed -i "s/^BACKEND=.*/BACKEND=vosk/" "$ENV_FILE"
        else
            echo "BACKEND=vosk" >> "$ENV_FILE"
        fi
        print_status "Default backend set to: Vosk"
    else
        # Both installed - let user choose or keep existing
        if ! grep -q "^BACKEND=" "$ENV_FILE"; then
            echo "BACKEND=whisper" >> "$ENV_FILE"
            print_status "Default backend set to: Whisper (you can change in .env)"
        else
            current_backend=$(grep "^BACKEND=" "$ENV_FILE" | cut -d'=' -f2)
            print_status "Current backend: $current_backend (you can change in .env)"
        fi
    fi

    print_success "Configuration completed"
}

create_bash_aliases() {
    if [ "$INSTALL_VOSK" = false ]; then
        return  # Skip if Vosk not installed
    fi

    print_status "Creating bash aliases for Vosk..."

    BASHRC="$HOME/.bashrc"

    if grep -q "# Nerd-Dictation aliases" "$BASHRC"; then
        print_warning "Aliases already exist in .bashrc"
        return
    fi

    cat >> "$BASHRC" << EOF

# Nerd-Dictation aliases
alias dictado-es='cd $NERD_DICTATION_DIR && ./nerd-dictation begin --vosk-model-dir=$MODELS_DIR/vosk-model-small-es-0.42'
alias dictado-en='cd $NERD_DICTATION_DIR && ./nerd-dictation begin --vosk-model-dir=$MODELS_DIR/vosk-model-small-en-us-0.15'
alias dictado-stop='cd $NERD_DICTATION_DIR && ./nerd-dictation end'
EOF

    print_success "Aliases added to .bashrc"
}

# ============================================================================
# DESKTOP FILE CREATION
# ============================================================================

create_desktop_file() {
    print_header "Creating Desktop Entry"

    DESKTOP_FILE="$PROJECT_DIR/data/dictation.desktop"
    DESKTOP_INSTALL_DIR="$HOME/.local/share/applications"

    # Ensure data directory exists
    mkdir -p "$PROJECT_DIR/data"

    print_status "Generating dictation.desktop file..."

    # Create .desktop file
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Dictation Manager
Comment=Voice dictation with Vosk and Whisper backends
Exec=$PROJECT_DIR/run.sh
Icon=$PROJECT_DIR/assets/logo.png
Terminal=false
Categories=Utility;AudioVideo;Accessibility;
Keywords=dictation;voice;speech;transcription;whisper;vosk;
StartupNotify=true
EOF

    print_success "Desktop file created at: $DESKTOP_FILE"

    # Install to user applications directory
    print_status "Installing to applications menu..."

    mkdir -p "$DESKTOP_INSTALL_DIR"
    cp "$DESKTOP_FILE" "$DESKTOP_INSTALL_DIR/dictation-manager.desktop"

    # Make it executable
    chmod +x "$DESKTOP_INSTALL_DIR/dictation-manager.desktop"

    print_success "Desktop entry installed to: $DESKTOP_INSTALL_DIR"

    # Update desktop database if possible
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_INSTALL_DIR" 2>/dev/null || true
        print_success "Desktop database updated"
    fi

    print_status "Dictation Manager should now appear in your applications menu"
}

# ============================================================================
# TESTING
# ============================================================================

test_installation() {
    print_header "Testing Installation"

    if [ "$INSTALL_VOSK" = true ]; then
        print_status "Testing Vosk backend..."

        if [ -x "$NERD_DICTATION_DIR/nerd-dictation" ]; then
            print_success "nerd-dictation executable found"
        else
            print_error "nerd-dictation executable not found"
        fi

        model_count=$(find "$MODELS_DIR" -maxdepth 1 -type d -name "vosk-model-*" 2>/dev/null | wc -l)
        if [ "$model_count" -gt 0 ]; then
            print_success "Found $model_count Vosk model(s)"
        else
            print_warning "No Vosk models found"
        fi
    fi

    if [ "$INSTALL_WHISPER" = true ]; then
        print_status "Testing Whisper backend..."

        if [ -d "$PROJECT_DIR/venv" ]; then
            print_success "Whisper virtual environment created"
        else
            print_error "Whisper venv not found"
        fi

        if [ -f "$PROJECT_DIR/run.sh" ]; then
            print_success "run.sh launcher found"
        else
            print_warning "run.sh not found"
        fi
    fi

    if [ -f "$PROJECT_DIR/.env" ]; then
        print_success ".env configuration file created"
    else
        print_error ".env file not found"
    fi
}

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

print_usage() {
    print_header "Installation Complete! 🎉"

    echo -e "${BLUE}Installed Backends:${NC}"
    echo ""

    if [ "$INSTALL_VOSK" = true ]; then
        echo -e "  ${GREEN}✓${NC} Vosk (CPU-based)"
    fi

    if [ "$INSTALL_WHISPER" = true ]; then
        echo -e "  ${GREEN}✓${NC} Whisper (GPU-accelerated)"
    fi

    echo ""
    echo -e "${BLUE}Running the Application:${NC}"
    echo ""
    echo -e "  ${YELLOW}From Applications Menu (Easiest):${NC}"
    echo -e "    Search for '${GREEN}Dictation Manager${NC}' in your app launcher"
    echo ""
    echo -e "  ${YELLOW}From Terminal:${NC}"
    echo -e "    cd $PROJECT_DIR"
    echo -e "    ./run.sh"
    echo ""

    if [ "$INSTALL_VOSK" = true ]; then
        echo -e "${BLUE}Vosk Quick Commands:${NC}"
        echo ""
        echo -e "  ${YELLOW}Spanish dictation:${NC} dictado-es"
        echo -e "  ${YELLOW}English dictation:${NC} dictado-en"
        echo -e "  ${YELLOW}Stop dictation:${NC}    dictado-stop"
        echo -e "  ${YELLOW}(Run 'source ~/.bashrc' first)${NC}"
        echo ""
    fi

    if [ "$INSTALL_WHISPER" = true ]; then
        echo -e "${BLUE}Whisper Debug Tools:${NC}"
        echo ""
        echo -e "  ${YELLOW}Test VAD:${NC}           cd $PROJECT_DIR && source venv/bin/activate && python debug_tools/debug_vad.py"
        echo -e "  ${YELLOW}List audio devices:${NC} cd $PROJECT_DIR && source venv/bin/activate && python debug_tools/list_audio_devices.py"
        echo ""
    fi

    if [ "$INSTALL_VOSK" = true ] && [ "$INSTALL_WHISPER" = true ]; then
        echo -e "${BLUE}Switching Backends:${NC}"
        echo ""
        echo -e "  Edit ${YELLOW}$PROJECT_DIR/.env${NC}"
        echo -e "  Change: ${YELLOW}BACKEND=vosk${NC} or ${YELLOW}BACKEND=whisper${NC}"
        echo ""
    fi

    echo -e "${BLUE}Configuration:${NC}"
    echo ""
    echo -e "  Config file: ${YELLOW}$PROJECT_DIR/.env${NC}"
    echo -e "  Logs:        ${YELLOW}$PROJECT_DIR/logs/dictation.log${NC}"
    echo ""

    if [ "$INSTALL_VOSK" = true ]; then
        echo -e "${BLUE}Locations:${NC}"
        echo ""
        echo -e "  nerd-dictation: ${YELLOW}$NERD_DICTATION_DIR${NC}"
        echo -e "  Vosk models:    ${YELLOW}$MODELS_DIR${NC}"
    fi

    if [ "$INSTALL_WHISPER" = true ]; then
        echo -e "  Whisper venv:   ${YELLOW}$PROJECT_DIR/venv${NC}"
        echo -e "  Debug tools:    ${YELLOW}$PROJECT_DIR/debug_tools/${NC}"
    fi

    echo ""
    echo -e "${BLUE}Voice Commands (Whisper only):${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} xdotool installed and ready"
    echo -e "  Enable in Settings → Voice Commands tab"
    echo -e "  Say: ${YELLOW}'[keyword] [command]'${NC} (e.g., 'Tony Enter')"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo ""
    echo -e "  1. Run: ${YELLOW}./run.sh${NC}"
    echo -e "  2. Click ${YELLOW}'Español'${NC} or ${YELLOW}'English'${NC} button in the GUI"
    echo -e "  3. Speak clearly into your microphone"
    echo -e "  4. Text will appear where your cursor is"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header "Dictation Manager Installation - Ubuntu 24.04"

    check_ubuntu
    check_not_root
    choose_backends
    install_common_dependencies

    if [ "$INSTALL_VOSK" = true ]; then
        install_vosk_backend
        download_vosk_models
    fi

    if [ "$INSTALL_WHISPER" = true ]; then
        install_whisper_backend
    fi

    configure_environment

    if [ "$INSTALL_VOSK" = true ]; then
        create_bash_aliases
    fi

    create_desktop_file

    test_installation
    print_usage

    print_success "Installation complete!"
}

# Run main function
main
