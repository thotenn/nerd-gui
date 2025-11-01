#!/bin/bash

# Dictation Manager Launcher
# This script activates the virtual environment and runs the application
# Supports both Linux (CUDA) and macOS (MPS)

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Virtual environment path
VENV_PATH="$SCRIPT_DIR/venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: ./install.sh"
    exit 1
fi

# Activate virtual environment and run the application
echo "🚀 Starting Dictation Manager..."
source "$VENV_PATH/bin/activate"

# Platform-specific configuration
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - No need for LD_LIBRARY_PATH
    # MPS (Metal Performance Shaders) will be detected automatically by PyTorch
    echo "Running on macOS"
else
    # Linux - Add cuDNN libraries to LD_LIBRARY_PATH for CUDA support
    # Try to find the correct Python version directory
    PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    CUDNN_PATH="$VENV_PATH/lib/python${PYTHON_VERSION}/site-packages/nvidia/cudnn/lib"

    if [ -d "$CUDNN_PATH" ]; then
        export LD_LIBRARY_PATH="$CUDNN_PATH:$LD_LIBRARY_PATH"
        echo "CUDA libraries configured"
    fi
fi

cd "$SCRIPT_DIR"
python main.py "$@"