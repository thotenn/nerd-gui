#!/bin/bash

# Dictation Manager Launcher
# This script activates the virtual environment and runs the application

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Virtual environment path
VENV_PATH="$SCRIPT_DIR/venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: ./install_whisper_backend.sh"
    exit 1
fi

# Activate virtual environment and run the application
echo "🚀 Starting Dictation Manager..."
source "$VENV_PATH/bin/activate"

# Add cuDNN libraries to LD_LIBRARY_PATH for CUDA support
export LD_LIBRARY_PATH="$VENV_PATH/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"

cd "$SCRIPT_DIR"
python main.py "$@"