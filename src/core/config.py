"""
Configuration management for Dictation Manager
"""

from pathlib import Path
import os


class Config:
    """Application configuration"""

    def __init__(self):
        # Load environment variables from .env file
        env_vars = self._load_env()

        # Base paths (from .env or defaults)
        self.home_dir = Path.home()
        self.app_dir = Path(env_vars.get("APP_DIR"))
        self.nerd_dictation_dir = Path(env_vars.get("NERD_DICTATION_DIR"))
        self.models_dir = Path(env_vars.get("MODELS_DIR"))

        # Database
        self.db_path = self.app_dir / "data" / "dictation.db"

        # Nerd-dictation executable
        self.nerd_dictation_bin = self.nerd_dictation_dir / "nerd-dictation"

        # Backend configuration
        self.backend = env_vars.get("BACKEND", "vosk")  # 'vosk' or 'whisper'

        # Whisper configuration
        self.whisper_model = env_vars.get("WHISPER_MODEL", "medium")  # tiny, base, small, medium, large
        self.whisper_device = env_vars.get("WHISPER_DEVICE", "cuda")  # cuda or cpu
        self.whisper_compute_type = env_vars.get("WHISPER_COMPUTE_TYPE", "float16")  # float16 for GPU, float32 for CPU

        # Whisper Audio/VAD configuration
        device_index_str = env_vars.get("WHISPER_DEVICE_INDEX", "")
        self.whisper_device_index = int(device_index_str) if device_index_str.strip() else None
        self.whisper_silence_duration = float(env_vars.get("WHISPER_SILENCE_DURATION", "1.0"))
        self.whisper_energy_threshold = float(env_vars.get("WHISPER_ENERGY_THRESHOLD", "0.002"))
        self.whisper_min_audio_length = float(env_vars.get("WHISPER_MIN_AUDIO_LENGTH", "0.3"))

        # Language configurations
        self.languages = {
            "spanish": {
                "name": "Español",
                "code": "es"
            },
            "english": {
                "name": "English",
                "code": "en"
            }
        }
        
        # Ensure directories exist
        self._create_directories()

    def _load_env(self):
        """Load environment variables from .env file"""
        env_vars = {}
        env_file = Path(__file__).parent.parent.parent / ".env"

        if not env_file.exists():
            return env_vars

        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

        return env_vars

    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        (self.app_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.app_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    def get_available_models(self):
        """Get list of available model directories"""
        if not self.models_dir.exists():
            return []
        
        models = []
        for item in self.models_dir.iterdir():
            if item.is_dir() and item.name.startswith("vosk-model"):
                models.append({
                    "path": str(item),
                    "name": item.name,
                    "language": self._detect_language(item.name)
                })
        
        return sorted(models, key=lambda x: x["name"])
    
    def _detect_language(self, model_name):
        """Detect language from model name"""
        model_lower = model_name.lower()
        if "es" in model_lower or "spanish" in model_lower:
            return "spanish"
        elif "en" in model_lower or "english" in model_lower:
            return "english"
        return "unknown"