"""
Configuration management for Dictation Manager
"""

from pathlib import Path
import os


class Config:
    """Application configuration"""

    def __init__(self, database=None):
        # Load environment variables from .env file
        env_vars = self._load_env()

        # Base paths (from .env or defaults)
        self.home_dir = Path.home()
        self.app_dir = Path(env_vars.get("APP_DIR"))
        self.nerd_dictation_dir = Path(env_vars.get("NERD_DICTATION_DIR"))
        self.models_dir = Path(env_vars.get("MODELS_DIR"))

        # Database
        self.db_path = self.app_dir / "data" / "dictation.db"
        self.database = database

        # Nerd-dictation executable
        self.nerd_dictation_bin = self.nerd_dictation_dir / "nerd-dictation"

        # Backend configuration (default from .env, can be overridden by database)
        self.backend = env_vars.get("BACKEND", "vosk")  # 'vosk' or 'whisper'

        # Whisper configuration (defaults from .env, can be overridden by database)
        self.whisper_model = env_vars.get("WHISPER_MODEL", "Systran/faster-whisper-medium")  # Hugging Face model ID
        self.whisper_device = env_vars.get("WHISPER_DEVICE", "cuda")  # cuda or cpu
        self.whisper_compute_type = env_vars.get("WHISPER_COMPUTE_TYPE", "float16")  # float16 for GPU, float32 for CPU

        # Whisper Audio/VAD configuration (defaults from .env, can be overridden by database)
        device_index_str = env_vars.get("WHISPER_DEVICE_INDEX", "")
        self.whisper_device_index = int(device_index_str) if device_index_str.strip() else None
        self.whisper_silence_duration = float(env_vars.get("WHISPER_SILENCE_DURATION", "1.0"))
        self.whisper_energy_threshold = float(env_vars.get("WHISPER_ENERGY_THRESHOLD", "0.002"))
        self.whisper_min_audio_length = float(env_vars.get("WHISPER_MIN_AUDIO_LENGTH", "0.3"))

        # Debug flag (will be loaded from database)
        self.debug_enabled = False

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

        # Load settings from database if available
        if self.database:
            self.reload_from_db()

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

    def get_language_by_code(self, code):
        """
        Get language key from language code.

        Args:
            code: Language code (e.g., 'es', 'en')

        Returns:
            Language key (e.g., 'spanish', 'english') or None if not found
        """
        for key, lang_info in self.languages.items():
            if lang_info.get("code") == code:
                return key
        return None

    def get_language_name(self, code_or_key):
        """
        Get language display name from code or key.

        Args:
            code_or_key: Language code ('es', 'en') or key ('spanish', 'english')

        Returns:
            Language display name (e.g., 'Español', 'English') or 'Desconocido'
        """
        # First try to find by code
        for key, lang_info in self.languages.items():
            if lang_info.get("code") == code_or_key:
                return lang_info["name"]

        # Then try direct key lookup
        if code_or_key in self.languages:
            return self.languages[code_or_key]["name"]

        return "Desconocido"

    def reload_from_db(self):
        """
        Reload configuration from database.
        Settings in database override .env defaults.
        """
        if not self.database:
            return

        try:
            # Load backend
            backend = self.database.get_setting('backend')
            if backend:
                self.backend = backend

            # Load Whisper model
            whisper_model = self.database.get_setting('whisper_model')
            if whisper_model:
                self.whisper_model = whisper_model

            # Load Whisper configuration
            whisper_device = self.database.get_setting('whisper_device')
            if whisper_device:
                self.whisper_device = whisper_device

            whisper_compute = self.database.get_setting('whisper_compute_type')
            if whisper_compute:
                self.whisper_compute_type = whisper_compute

            # Load device index
            device_index_str = self.database.get_setting('whisper_device_index', '')
            if device_index_str.strip():
                try:
                    self.whisper_device_index = int(device_index_str)
                except ValueError:
                    pass  # Keep default

            # Load VAD parameters
            silence_str = self.database.get_setting('whisper_silence_duration')
            if silence_str:
                try:
                    self.whisper_silence_duration = float(silence_str)
                except ValueError:
                    pass  # Keep default

            energy_str = self.database.get_setting('whisper_energy_threshold')
            if energy_str:
                try:
                    self.whisper_energy_threshold = float(energy_str)
                except ValueError:
                    pass  # Keep default

            min_audio_str = self.database.get_setting('whisper_min_audio_length')
            if min_audio_str:
                try:
                    self.whisper_min_audio_length = float(min_audio_str)
                except ValueError:
                    pass  # Keep default

            # Load debug flag
            debug_str = self.database.get_setting('debug_enabled', 'false')
            self.debug_enabled = debug_str.lower() in ('true', '1', 'yes')

        except Exception as e:
            print(f"Warning: Could not reload config from database: {e}")

    def migrate_from_env(self):
        """
        Migrate configuration from .env file to database (one-time operation).

        This ensures existing users don't lose their Whisper settings when
        upgrading to the new database-based configuration system.
        """
        if not self.database:
            return

        # Check if migration has already been done
        if self.database.is_migration_complete():
            return

        print("Migrating configuration from .env to database...")

        # Load environment variables again to get potential Whisper settings
        env_vars = self._load_env()

        # Map old model names to new Hugging Face IDs
        model_name_mapping = {
            'tiny': 'Systran/faster-whisper-tiny',
            'base': 'Systran/faster-whisper-base',
            'small': 'Systran/faster-whisper-small',
            'medium': 'Systran/faster-whisper-medium',
            'large': 'Systran/faster-whisper-large-v3',
            'large-v3': 'Systran/faster-whisper-large-v3'
        }

        # Get whisper model and convert if needed
        whisper_model_raw = env_vars.get('WHISPER_MODEL')
        if whisper_model_raw:
            # Convert old names to new IDs if necessary
            whisper_model = model_name_mapping.get(whisper_model_raw.lower(), whisper_model_raw)
        else:
            whisper_model = None

        # List of settings to migrate from .env to database
        settings_to_migrate = {
            'backend': env_vars.get('BACKEND'),
            'whisper_model': whisper_model,  # Single model for all languages (converted to HF ID)
            'whisper_device': env_vars.get('WHISPER_DEVICE'),
            'whisper_compute_type': env_vars.get('WHISPER_COMPUTE_TYPE'),
            'whisper_device_index': env_vars.get('WHISPER_DEVICE_INDEX'),
            'whisper_silence_duration': env_vars.get('WHISPER_SILENCE_DURATION'),
            'whisper_energy_threshold': env_vars.get('WHISPER_ENERGY_THRESHOLD'),
            'whisper_min_audio_length': env_vars.get('WHISPER_MIN_AUDIO_LENGTH'),
        }

        # Migrate settings to database
        migrated_count = 0
        for key, value in settings_to_migrate.items():
            if value is not None and value.strip():  # Only migrate if value exists
                self.database.save_setting(key, value)
                migrated_count += 1
                print(f"  Migrated: {key} = {value}")

        # Mark migration as complete
        self.database.mark_migration_complete()

        if migrated_count > 0:
            print(f"Migration complete! Migrated {migrated_count} settings from .env to database.")
        else:
            print("Migration complete! No settings found in .env (using defaults).")