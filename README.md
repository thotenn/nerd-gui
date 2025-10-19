# Dictation Manager

A Python GUI application for voice dictation with support for multiple backends (Vosk via integrated [nerd-dictation](https://github.com/ideasman42/nerd-dictation), and Whisper) with support for multiple languages.

## Features

- **Intuitive GUI**: Easy voice dictation control with Tkinter
- **Multi-language support**: Spanish and English with quick language switching
- **Model management**: Selection and switching between different Vosk models
- **Session tracking**: Automatic logging of all dictation sessions in SQLite
- **No external dependencies**: Uses only Python standard library
- **Auto-refresh**: Status updates every 2 seconds
- **Silent operation**: No popup dialogs, seamless workflow

## System Requirements

- **OS**: Ubuntu 24.04 (or similar)
- **Python**: 3.11+
- **System packages**:
  ```bash
  sudo apt install python3-tk pulseaudio-utils
  ```
- **nerd-dictation**: Installed with its own virtual environment
- **Vosk models**: At least one model downloaded

## Installation

### 1. Clone or download the project

```bash
cd /home/tho/soft/ai/
git clone <repository-url> dictation
cd dictation
```

### 2. Configure paths

Copy the example file and adjust paths for your system:

```bash
cp .env.example .env
```

Edit `.env` with your specific paths:

```bash
APP_DIR=/home/tho/soft/ai/dictation
NERD_DICTATION_DIR=/home/tho/app_folder/nerd-dictation  # Optional, uses apps/nerd-dictation by default
MODELS_DIR=/home/tho/.config/nerd-dictation
```

**Note**: `NERD_DICTATION_DIR` is optional. The application includes an integrated copy of nerd-dictation at `apps/nerd-dictation/`. If you have a custom installation, you can specify it here.

### 3. Download Vosk models

Download models from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models/) and place them in your models directory (defined in `.env`):

```bash
# Example: recommended models
# Spanish
wget https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
unzip vosk-model-es-0.42.zip -d ~/.config/nerd-dictation/

# English
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip -d ~/.config/nerd-dictation/
```

### 4. Install nerd-dictation (Vosk backend)

The repository includes nerd-dictation at `apps/nerd-dictation/`. You need to set up its virtual environment:

```bash
cd /home/tho/soft/ai/dictation/apps/nerd-dictation
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install .
deactivate
```

**Note**: If you prefer to use a separate nerd-dictation installation, clone it elsewhere and specify the path in `.env` via `NERD_DICTATION_DIR`.

### 5. Install Whisper backend (optional, GPU recommended)

For the Whisper backend with GPU acceleration:

```bash
cd /home/tho/soft/ai/dictation
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# For GPU support (requires NVIDIA CUDA)
pip install nvidia-cudnn-cu12
deactivate
```

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
