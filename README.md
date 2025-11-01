# Dictation Manager

A Python GUI application for voice dictation with support for multiple backends (Vosk via integrated [nerd-dictation](https://github.com/ideasman42/nerd-dictation), and Whisper) with support for multiple languages.

**Now with macOS (Apple Silicon) support!** 🎉

## Features

- **Intuitive GUI**: Easy voice dictation control with Tkinter
- **Multi-language support**: Spanish and English with quick language switching
- **Model management**: Selection and switching between different Vosk models
- **Session tracking**: Automatic logging of all dictation sessions in SQLite
- **Cross-platform**: Works on Ubuntu/Linux and macOS (Apple Silicon)
- **Auto-refresh**: Status updates every 2 seconds
- **Silent operation**: No popup dialogs, seamless workflow
- **Hardware acceleration**: CUDA (NVIDIA) on Linux, optimized CPU on macOS

## System Requirements

### Ubuntu/Linux

- **OS**: Ubuntu 24.04 (or similar Linux distribution)
- **Python**: 3.8+
- **GPU**: NVIDIA GPU with CUDA support (recommended for Whisper)
- **System packages**:
  ```bash
  sudo apt install python3-tk python3-pip python3-venv portaudio19-dev xdotool
  ```

### macOS (Apple Silicon)

- **OS**: macOS (tested on Apple Silicon M1/M2)
- **Python**: 3.8+
- **Homebrew**: Required for dependencies
- **System packages**:
  ```bash
  brew install portaudio cmake pkg-config
  ```
- **Important**: You'll need to grant **Accessibility permissions** to your Terminal app in:
  - System Preferences → Privacy & Security → Accessibility

## Installation

The installation process is now **fully automated** and detects your operating system automatically!

### Quick Start (Automated Installation)

#### On macOS:

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Clone and install**:
   ```bash
   git clone <repository-url> nerd-gui
   cd nerd-gui
   chmod +x install.sh
   ./install.sh
   ```

3. **Grant Accessibility permissions**:
   - Open System Preferences → Privacy & Security → Accessibility
   - Add Terminal (or your terminal app) to the list
   - This allows the app to type dictated text

4. **Run the application**:
   ```bash
   ./run.sh
   ```

#### On Ubuntu/Linux:

1. **Clone and install**:
   ```bash
   git clone <repository-url> nerd-gui
   cd nerd-gui
   chmod +x install.sh
   ./install.sh
   ```

2. **Run the application**:
   ```bash
   ./run.sh
   ```
   Or search for "Dictation Manager" in your applications menu.

### What the installer does:

The `install.sh` script will:
- ✅ Detect your operating system (macOS or Ubuntu/Linux)
- ✅ Check for required dependencies (Homebrew on Mac, apt on Ubuntu)
- ✅ Prompt you to choose backends (Vosk, Whisper, or both)
- ✅ Install all necessary system packages
- ✅ Create virtual environments
- ✅ Install Python dependencies
- ✅ Configure paths automatically
- ✅ On macOS: Install PyAutoGUI for keyboard output
- ✅ On Linux: Install xdotool and configure desktop entry

### Platform-Specific Notes

#### macOS (Apple Silicon)

- **Keyboard Output**: Uses PyAutoGUI instead of xdotool
  - Requires Accessibility permissions (System Preferences → Privacy & Security)
- **GPU Acceleration**: Uses CPU with int8 quantization (optimized for Apple Silicon)
  - faster-whisper doesn't support MPS directly yet, but CPU performance is excellent on M1/M2
- **Models Directory**: `~/Library/Application Support/nerd-dictation`
- **Performance**: Apple Silicon CPUs are very fast for inference, expect good performance even without GPU

#### Ubuntu/Linux (NVIDIA GPU)

- **Keyboard Output**: Uses xdotool (X11 required)
- **GPU Acceleration**: CUDA with float16 precision
- **Models Directory**: `~/.config/nerd-dictation`
- **Desktop Integration**: Creates `.desktop` file for application menu

## Usage

### Starting the application

**From Applications Menu (Easiest):**

After running the installer, search for "Dictation Manager" in your applications launcher (GNOME Activities, KDE Menu, etc.)

**From Terminal:**

```bash
cd /home/tho/soft/ai/dictation
./run.sh
```

Or with explicit Python (must be system Python with tkinter):

```bash
/usr/bin/python3 main.py
```

### Controls

- **STOP button**: Stops current dictation
- **Español button**: Starts Spanish dictation (uses last Spanish model)
- **English button**: Starts English dictation (uses last English model)
- **Double-click model**: Starts dictation with that specific model

### Status panel

The status panel shows:
- **Status**: Active (🟢) or Stopped (🔴)
- **Model**: Current Vosk model name
- **Language**: Current model language

## Project Structure

```
dictation/
├── main.py                  # Application entry point
├── .env                     # Path configuration (not in git)
├── .env.example             # Configuration template
├── README.md                # This file
├── CLAUDE.md                # Claude Code guidance
├── apps/
│   └── nerd-dictation/     # Integrated nerd-dictation (Vosk backend)
├── data/
│   └── dictation.db        # SQLite database (auto-created)
├── logs/                    # Application logs
└── src/
    ├── backends/
    │   ├── base_backend.py         # Backend interface
    │   ├── vosk_backend.py         # Vosk implementation
    │   ├── whisper_backend.py      # Whisper implementation
    │   └── whisper/                # Whisper components
    ├── core/
    │   ├── config.py               # Configuration and .env management
    │   ├── database.py             # SQLite operations
    │   ├── dictation_controller.py # Backend management
    │   └── logging_controller.py   # Centralized logging
    └── ui/
        └── main_window.py          # Tkinter GUI
```

## Advanced Configuration

### Adding a new language

1. Add the language to `src/core/config.py`:
   ```python
   self.languages = {
       "spanish": {"name": "Español", "code": "es"},
       "english": {"name": "English", "code": "en"},
       "french": {"name": "Français", "code": "fr"}  # New
   }
   ```

2. Download the corresponding Vosk model to your models directory

3. Add a button in `src/ui/main_window.py` → `_create_control_buttons()`

4. Update `_detect_language()` in `config.py` for the model name pattern

## Troubleshooting

### Application won't start

**Problem**: tkinter import error
**Solution**: Make sure to use system Python with tkinter installed:
```bash
sudo apt install python3-tk
/usr/bin/python3 main.py  # Don't use asdf or other version managers
```

### Dictation doesn't start

**Problem**: nerd-dictation not executing properly
**Solution**: Verify the controller uses nerd-dictation's venv Python:
```bash
# Manual test
cd /home/tho/app_folder/nerd-dictation
./venv/bin/python ./nerd-dictation begin --vosk-model-dir=~/.config/nerd-dictation/vosk-model-es-0.42
```

### No models showing

**Problem**: Models directory empty or doesn't exist
**Solution**: Download Vosk models and place them in the directory configured in `.env`

### Verify dictation status

```bash
# Check if nerd-dictation is running
pgrep -fa "nerd-dictation begin"

# View recent sessions in database
sqlite3 data/dictation.db "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 5;"
```

## Database

The application uses SQLite to track sessions:

- **sessions table**: Records each dictation session (language, model, timestamps)
- **settings table**: User settings (currently unused)

Database located at: `${APP_DIR}/data/dictation.db`

## Development

This project uses only Python standard library:
- `tkinter`: GUI
- `sqlite3`: Database
- `subprocess`: Process control
- `pathlib`: Path handling

No additional pip packages required.

### Useful debugging commands

```bash
# List available models
ls -1 ~/.config/nerd-dictation/

# Test configuration
python3 -c "from src.core.config import Config; c = Config(); print(c.app_dir)"

# View nerd-dictation logs (if they exist)
tail -f /path/to/nerd-dictation/logs/*
```

## Resources

- [nerd-dictation GitHub](https://github.com/ideasman42/nerd-dictation)
- [Vosk Models](https://alphacephei.com/vosk/models/)
- [Vosk Documentation](https://alphacephei.com/vosk/)

## License

This project manages nerd-dictation, which has its own license.
Check the nerd-dictation repository for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
