"""
Model Configuration Loader

Loads model and language configuration from models.json file.
Provides fallback to hardcoded values if JSON file is missing or malformed.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.core.logging_controller import info, debug, warning, error

# Hardcoded fallback configuration (original values)
FALLBACK_CONFIG = {
    "vosk": {
        "en": {
            "small": {
                "name": "vosk-model-small-en-us-0.15",
                "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
                "size": "40MB",
                "description": "Small English model (~90% accuracy, fast)"
            },
            "medium": {
                "name": "vosk-model-en-us-0.22-lgraph",
                "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip",
                "size": "128MB",
                "description": "Medium English model with language model graph"
            },
            "gigaspeech": {
                "name": "vosk-model-en-us-0.42-gigaspeech",
                "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip",
                "size": "2.3GB",
                "description": "GigaSpeech English model (high accuracy)"
            }
        },
        "es": {
            "small": {
                "name": "vosk-model-small-es-0.42",
                "url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
                "size": "40MB",
                "description": "Small Spanish model (~90% accuracy, fast)"
            },
            "large": {
                "name": "vosk-model-es-0.42",
                "url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip",
                "size": "1.5GB",
                "description": "Large Spanish model (~95% accuracy, slower)"
            }
        }
    },
    "whisper": {
        "multilingual": {
            "tiny": {
                "name": "Systran/faster-whisper-tiny",
                "size": "~75MB",
                "description": "Tiny multilingual model (fastest, lowest accuracy)"
            },
            "base": {
                "name": "Systran/faster-whisper-base",
                "size": "~145MB",
                "description": "Base multilingual model (fast, good accuracy)"
            },
            "small": {
                "name": "Systran/faster-whisper-small",
                "size": "~466MB",
                "description": "Small multilingual model (balanced speed/accuracy)"
            },
            "medium": {
                "name": "Systran/faster-whisper-medium",
                "size": "~1.5GB",
                "description": "Medium multilingual model (slower, high accuracy)"
            },
            "large-v3": {
                "name": "Systran/faster-whisper-large-v3",
                "size": "~3GB",
                "description": "Large multilingual model v3 (slowest, highest accuracy)"
            }
        }
    },
    "languages": {
        "en": {
            "name": "English",
            "code": "en",
            "flag": "🇺🇸",
            "vosk_supported": True,
            "whisper_supported": True
        },
        "es": {
            "name": "Spanish",
            "code": "es",
            "flag": "🇪🇸",
            "vosk_supported": True,
            "whisper_supported": True
        }
    }
}


class ModelConfigLoader:
    """Loads model configuration from JSON file with fallback support."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the loader.

        Args:
            config_path: Path to models.json. If None, uses project root.
        """
        if config_path is None:
            # Default: models.json in project root
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "models.json"
        else:
            self.config_path = Path(config_path)

        self._config = None
        self._load_config()

    def _load_config(self):
        """Load configuration from JSON file or use fallback."""
        if not self.config_path.exists():
            warning(f"models.json not found at {self.config_path}, using fallback configuration")
            self._config = FALLBACK_CONFIG
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            info(f"Loaded model configuration from {self.config_path}")
            debug(f"Configuration: {len(self._config.get('vosk', {}))} Vosk languages, "
                  f"{len(self._config.get('whisper', {}))} Whisper configs, "
                  f"{len(self._config.get('languages', {}))} total languages")

            # Validate structure
            self._validate_config()

        except json.JSONDecodeError as e:
            error(f"Failed to parse models.json: {e}")
            error("Using fallback configuration")
            self._config = FALLBACK_CONFIG
        except Exception as e:
            error(f"Error loading models.json: {e}")
            error("Using fallback configuration")
            self._config = FALLBACK_CONFIG

    def _validate_config(self):
        """Validate configuration structure."""
        required_keys = ["vosk", "whisper", "languages"]
        for key in required_keys:
            if key not in self._config:
                warning(f"Missing '{key}' section in models.json")

        # Validate Vosk models
        vosk_models = self._config.get("vosk", {})
        for lang, sizes in vosk_models.items():
            for size, model_info in sizes.items():
                required_fields = ["name", "url", "size", "description"]
                missing = [f for f in required_fields if f not in model_info]
                if missing:
                    warning(f"Vosk model {lang}/{size} missing fields: {missing}")

        # Validate languages
        languages = self._config.get("languages", {})
        for code, lang_info in languages.items():
            required_fields = ["name", "code", "vosk_supported", "whisper_supported"]
            missing = [f for f in required_fields if f not in lang_info]
            if missing:
                warning(f"Language {code} missing fields: {missing}")

    def get_vosk_models(self, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Vosk model configurations.

        Args:
            language: Optional language code filter

        Returns:
            Dictionary of Vosk models
        """
        vosk_config = self._config.get("vosk", {})

        if language:
            return {language: vosk_config.get(language, {})}

        return vosk_config

    def get_whisper_models(self) -> Dict[str, Any]:
        """
        Get Whisper model configurations.

        Returns:
            Dictionary of Whisper models
        """
        return self._config.get("whisper", {})

    def get_languages(self, backend: Optional[str] = None) -> Dict[str, Any]:
        """
        Get language configurations.

        Args:
            backend: Optional filter by backend ('vosk' or 'whisper')

        Returns:
            Dictionary of language configurations
        """
        languages = self._config.get("languages", {})

        if backend == "vosk":
            return {
                code: info for code, info in languages.items()
                if info.get("vosk_supported", False)
            }
        elif backend == "whisper":
            return {
                code: info for code, info in languages.items()
                if info.get("whisper_supported", False)
            }

        return languages

    def get_language_info(self, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific language.

        Args:
            language_code: Language code (e.g., 'en', 'es')

        Returns:
            Language information dictionary or None
        """
        return self._config.get("languages", {}).get(language_code)

    def reload(self):
        """Reload configuration from file."""
        info("Reloading model configuration")
        self._load_config()

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config


# Singleton instance
_loader_instance = None


def get_model_config_loader() -> ModelConfigLoader:
    """
    Get the singleton ModelConfigLoader instance.

    Returns:
        ModelConfigLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ModelConfigLoader()
    return _loader_instance


def reload_model_config():
    """Reload the model configuration from file."""
    global _loader_instance
    if _loader_instance is not None:
        _loader_instance.reload()
    else:
        _loader_instance = ModelConfigLoader()
