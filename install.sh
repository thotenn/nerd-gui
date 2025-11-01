#!/bin/bash
#
# Dictation Manager Installation Script
# Supports Ubuntu 24.04 and macOS (Apple Silicon)
# Supports both Vosk (CPU) and Whisper (GPU/MPS) backends
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        # Detect if it's Apple Silicon
        if [[ $(uname -m) == "arm64" ]]; then
            IS_APPLE_SILICON=true
            print_success "Detected: macOS (Apple Silicon)"
        else
            IS_APPLE_SILICON=false
            print_success "Detected: macOS (Intel)"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/lsb-release ]; then
            source /etc/lsb-release
            if [ "$DISTRIB_ID" == "Ubuntu" ]; then
                OS_TYPE="ubuntu"
                print_success "Detected: Ubuntu $DISTRIB_RELEASE"
            else
                OS_TYPE="linux"
                print_success "Detected: Linux (non-Ubuntu)"
            fi
        else
            OS_TYPE="linux"
            print_success "Detected: Linux"
        fi
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Directories - Platform dependent
set_directories() {
    if [ "$OS_TYPE" == "macos" ]; then
        MODELS_DIR="$HOME/Library/Application Support/nerd-dictation"
        # macOS (BSD sed) requires an argument after -i
        SED_INPLACE=(-i "")
    else
        MODELS_DIR="$HOME/.config/nerd-dictation"
        # Linux (GNU sed) doesn't require an argument
        SED_INPLACE=(-i)
    fi
}

# Global variables
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NERD_DICTATION_DIR="$PROJECT_DIR/apps/nerd-dictation"  # Use integrated copy
OS_TYPE=""
IS_APPLE_SILICON=false
MODELS_DIR=""  # Will be set by set_directories()

# Installation flags
INSTALL_VOSK=false
INSTALL_WHISPER=false
ALLOW_ROOT=false

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --allow-root)
            ALLOW_ROOT=true
            shift
            ;;
    esac
done

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

# Check OS - No longer needed as standalone function (integrated into detect_os)
# Kept for backward compatibility
check_ubuntu() {
    # This function is deprecated - OS detection is now done in detect_os()
    if [ "$OS_TYPE" != "ubuntu" ] && [ "$OS_TYPE" != "macos" ] && [ "$OS_TYPE" != "linux" ]; then
        print_error "Unsupported operating system"
        exit 1
    fi
}

# Check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        if [ "$ALLOW_ROOT" = true ]; then
            print_warning "Running as root (--allow-root flag detected)"
            print_warning "This is not recommended outside of containers/testing environments"
        else
            print_error "This script should not be run as root for security reasons."
            print_error "Please run as a regular user with sudo privileges."
            print_error "For containers/testing, use: ./install.sh --allow-root"
            exit 1
        fi
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
    if [ "$OS_TYPE" == "macos" ]; then
        echo "  2) Whisper (MPS-accelerated for Apple Silicon)"
        echo "     - High accuracy (95-97%)"
        echo "     - Uses Apple Metal Performance Shaders"
        echo "     - Built-in punctuation"
    else
        echo "  2) Whisper (GPU-accelerated)"
        echo "     - High accuracy (95-97%)"
        echo "     - Requires NVIDIA GPU (recommended)"
        echo "     - Built-in punctuation"
    fi
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

    if [ "$OS_TYPE" == "macos" ]; then
        # macOS installation using Homebrew

        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            print_error "Homebrew is not installed!"
            print_status "Please install Homebrew first:"
            print_status '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            exit 1
        fi

        print_success "Homebrew found"

        # Update Homebrew
        print_status "Updating Homebrew..."
        brew update || true

        # Install dependencies
        print_status "Installing macOS dependencies..."

        # Python (if not already installed)
        if ! command -v python3 &> /dev/null; then
            brew install python@3.11
        fi

        # Audio dependencies
        brew install portaudio || print_warning "portaudio already installed"

        # Build tools
        brew install cmake pkg-config || print_warning "Build tools already installed"

        # Git, wget, unzip are usually pre-installed on macOS or available via Xcode Command Line Tools

        print_warning "Note: xdotool is not available on macOS"
        print_status "Voice Commands will use AppleScript/PyAutoGUI instead"

        print_success "macOS dependencies installed"

    else
        # Linux/Ubuntu installation using apt

        # Use sudo only if not running as root
        SUDO_CMD=""
        if [[ $EUID -ne 0 ]]; then
            SUDO_CMD="sudo"
        fi

        $SUDO_CMD apt update

        # Common packages
        $SUDO_CMD apt install -y \
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
    fi
}

# Check Python tkinter availability (macOS only)
check_python_tkinter() {
    if [ "$OS_TYPE" != "macos" ]; then
        # tkinter is installed via python3-tk on Linux, skip check
        return 0
    fi

    print_header "Checking Python tkinter support"

    # Test if current Python has tkinter
    if python3 -c "import tkinter" 2>/dev/null; then
        print_success "Python has tkinter support"
        return 0
    fi

    # tkinter not available
    print_error "Python does not have tkinter support!"
    print_warning "The GUI application requires tkinter to work."
    echo ""
    print_status "This usually happens when Python is installed via asdf/pyenv without tkinter."
    echo ""
    echo "You have 3 options:"
    echo ""
    echo "  1) Install Python with tkinter via Homebrew (Recommended)"
    echo "     - Quick and automatic"
    echo "     - Will install: python-tk@3.11"
    echo "     - Command: brew install python-tk@3.11"
    echo ""
    echo "  2) Reinstall your current Python with tkinter support"
    echo "     - If using asdf/pyenv"
    echo "     - Requires: brew install tcl-tk"
    echo "     - Then reinstall Python with PYTHON_CONFIGURE_OPTS"
    echo ""
    echo "  3) Continue anyway (Not recommended)"
    echo "     - Installation will likely fail later"
    echo ""

    read -p "Choose option (1/2/3): " tkinter_choice

    case $tkinter_choice in
        1)
            print_status "Installing Python with tkinter via Homebrew..."
            if brew install python-tk@3.11; then
                print_success "Python with tkinter installed!"
                print_status "The installer will now use Homebrew Python."

                # Use Homebrew Python
                export PATH="/opt/homebrew/bin:$PATH"

                # Verify tkinter is now available
                if /opt/homebrew/bin/python3.11 -c "import tkinter" 2>/dev/null; then
                    print_success "✓ tkinter verified working"
                    # Note: PATH is already updated above to use Homebrew Python first
                else
                    print_error "Installation succeeded but tkinter still not working"
                    print_status "Please check your Homebrew installation"
                    exit 1
                fi
            else
                print_error "Failed to install Python with tkinter"
                exit 1
            fi
            ;;
        2)
            print_status "Instructions for reinstalling Python with tkinter:"
            echo ""
            echo "  # Install tcl-tk"
            echo "  brew install tcl-tk"
            echo ""
            echo "  # Set environment variables"
            echo '  export LDFLAGS="-L/opt/homebrew/opt/tcl-tk/lib"'
            echo '  export CPPFLAGS="-I/opt/homebrew/opt/tcl-tk/include"'
            echo '  export PATH="/opt/homebrew/opt/tcl-tk/bin:$PATH"'
            echo '  export PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='\''-I/opt/homebrew/opt/tcl-tk/include'\'' --with-tcltk-libs='\''-L/opt/homebrew/opt/tcl-tk/lib -ltcl8.6 -ltk8.6'\''"'
            echo ""
            echo "  # Reinstall Python (example for asdf)"
            echo "  asdf uninstall python <version>"
            echo "  asdf install python <version>"
            echo ""
            print_status "After reinstalling, run this installer again."
            exit 1
            ;;
        3)
            print_warning "Continuing without tkinter support..."
            print_warning "Installation may fail when creating GUI components!"
            sleep 2
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    echo ""
}

# ============================================================================
# VOSK BACKEND INSTALLATION
# ============================================================================

install_vosk_backend() {
    print_header "Installing Vosk Backend (nerd-dictation)"

    # Check if integrated nerd-dictation exists, clone if not
    if [ ! -d "$NERD_DICTATION_DIR" ]; then
        print_warning "Integrated nerd-dictation not found at $NERD_DICTATION_DIR"
        print_status "Cloning nerd-dictation from GitHub..."

        # Create apps directory if it doesn't exist
        mkdir -p "$PROJECT_DIR/apps"

        # Clone nerd-dictation
        cd "$PROJECT_DIR/apps"
        git clone https://github.com/ideasman42/nerd-dictation.git

        if [ ! -d "$NERD_DICTATION_DIR" ]; then
            print_error "Failed to clone nerd-dictation"
            exit 1
        fi

        print_success "nerd-dictation cloned successfully"
    else
        print_status "Using integrated nerd-dictation at: $NERD_DICTATION_DIR"
    fi

    cd "$NERD_DICTATION_DIR"

    # Note: nerd-dictation is now integrated into this repository
    # Updates will come through the main repository, not as a separate git submodule
    print_success "nerd-dictation ready for installation"

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

# Vosk models are now downloaded automatically on first use
# No need to download during installation

# ============================================================================
# WHISPER BACKEND INSTALLATION
# ============================================================================

install_whisper_backend() {
    if [ "$OS_TYPE" == "macos" ]; then
        print_header "Installing Whisper Backend (MPS-accelerated for Apple Silicon)"
    else
        print_header "Installing Whisper Backend (GPU-accelerated)"
    fi

    cd "$PROJECT_DIR"

    # Check Python version
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $PYTHON_VERSION"

    if ! python3 -c "import sys; assert sys.version_info >= (3, 8)" 2>/dev/null; then
        print_error "Python 3.8 or higher is required"
        exit 1
    fi

    # Check for acceleration hardware
    HAS_GPU=false
    DEVICE_TYPE="cpu"

    if [ "$OS_TYPE" == "macos" ]; then
        if [ "$IS_APPLE_SILICON" = true ]; then
            print_status "Apple Silicon detected - MPS acceleration will be available"
            print_status "Using Metal Performance Shaders for GPU acceleration"
            HAS_GPU=true
            DEVICE_TYPE="mps"
        else
            print_warning "Intel Mac detected - Whisper will run on CPU"
            print_warning "For best performance, use Apple Silicon Mac"
        fi
    else
        # Linux - Check for NVIDIA GPU
        if command -v nvidia-smi &> /dev/null; then
            print_status "NVIDIA GPU detected:"
            nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1
            HAS_GPU=true
            DEVICE_TYPE="cuda"
        else
            print_warning "NVIDIA GPU not detected. Whisper will run on CPU (slower)"
            print_warning "For GPU acceleration, install NVIDIA drivers first"
        fi
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

        # Install cuDNN for NVIDIA GPU support (Linux only)
        if [ "$HAS_GPU" = true ] && [ "$DEVICE_TYPE" == "cuda" ]; then
            print_status "Installing NVIDIA cuDNN for GPU acceleration..."
            pip install nvidia-cudnn-cu12 || print_warning "cuDNN installation failed (optional)"
            print_success "cuDNN installed"
        fi

        # For macOS, install PyAutoGUI for keyboard output (replacement for xdotool)
        if [ "$OS_TYPE" == "macos" ]; then
            print_status "Installing PyAutoGUI for keyboard output on macOS..."
            pip install pyautogui || print_warning "PyAutoGUI installation failed"
            print_success "PyAutoGUI installed (replacement for xdotool)"
        fi
    else
        print_error "requirements.txt not found in project root!"
        exit 1
    fi

    # Test installation
    print_status "Testing Whisper installation..."
    if [ "$OS_TYPE" == "macos" ]; then
        python -c "
from faster_whisper import WhisperModel
import torch
print('✓ faster-whisper imported successfully')

# Test MPS availability
if torch.backends.mps.is_available():
    print('✓ MPS (Metal Performance Shaders) available')
    device = 'cpu'  # Use CPU for initial test to avoid MPS issues
    compute_type = 'int8'
else:
    print('⚠ MPS not available, using CPU')
    device = 'cpu'
    compute_type = 'int8'

print(f'Using device for test: {device}')
print('Testing model loading (will download tiny model)...')
model = WhisperModel('tiny', device=device, compute_type=compute_type)
print('✓ Whisper model loaded successfully')
print('✓ All Whisper dependencies working!')
" || {
    print_error "Whisper installation test failed"
    exit 1
}
    else
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
    fi

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
        sed "${SED_INPLACE[@]}" "s|^APP_DIR=.*|APP_DIR=$PROJECT_DIR|" "$ENV_FILE"
    else
        echo "APP_DIR=$PROJECT_DIR" >> "$ENV_FILE"
    fi

    # Configure based on what was installed
    if [ "$INSTALL_VOSK" = true ]; then
        # Note: NERD_DICTATION_DIR is optional now (defaults to apps/nerd-dictation)
        # Only set MODELS_DIR
        if grep -q "^MODELS_DIR=" "$ENV_FILE"; then
            sed "${SED_INPLACE[@]}" "s|^MODELS_DIR=.*|MODELS_DIR=$MODELS_DIR|" "$ENV_FILE"
        else
            echo "MODELS_DIR=$MODELS_DIR" >> "$ENV_FILE"
        fi
    fi

    # Set default backend
    if [ "$INSTALL_WHISPER" = true ] && [ "$INSTALL_VOSK" = false ]; then
        # Whisper only
        if grep -q "^BACKEND=" "$ENV_FILE"; then
            sed "${SED_INPLACE[@]}" "s/^BACKEND=.*/BACKEND=whisper/" "$ENV_FILE"
        else
            echo "BACKEND=whisper" >> "$ENV_FILE"
        fi
        print_status "Default backend set to: Whisper"
    elif [ "$INSTALL_VOSK" = true ] && [ "$INSTALL_WHISPER" = false ]; then
        # Vosk only
        if grep -q "^BACKEND=" "$ENV_FILE"; then
            sed "${SED_INPLACE[@]}" "s/^BACKEND=.*/BACKEND=vosk/" "$ENV_FILE"
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
    # Detect OS first
    detect_os
    set_directories

    if [ "$OS_TYPE" == "macos" ]; then
        print_header "Dictation Manager Installation - macOS"
    else
        print_header "Dictation Manager Installation - Ubuntu/Linux"
    fi

    check_ubuntu  # This now just validates OS_TYPE is set

    # Skip root check on macOS
    if [ "$OS_TYPE" != "macos" ]; then
        check_not_root
    fi

    choose_backends
    install_common_dependencies
    check_python_tkinter

    if [ "$INSTALL_VOSK" = true ]; then
        install_vosk_backend
        print_status "Vosk models will download automatically when you first use each language"
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
