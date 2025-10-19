"""
Vosk Model Manager - Automatic model download and management.

Similar to Whisper's automatic model downloading, this manager
handles Vosk model downloads, caching, and verification.

Models are loaded dynamically from models.json with fallback to hardcoded values.
"""

import os
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.core.logging_controller import info, debug, warning, error
from src.core.model_config_loader import get_model_config_loader

# Load models dynamically from JSON
def _get_vosk_models() -> Dict:
    """Get Vosk models from configuration loader."""
    loader = get_model_config_loader()
    return loader.get_vosk_models()

# Lazy-loaded VOSK_MODELS (for backward compatibility)
VOSK_MODELS = None

def get_vosk_models_dict() -> Dict:
    """Get VOSK_MODELS dictionary, loading if needed."""
    global VOSK_MODELS
    if VOSK_MODELS is None:
        VOSK_MODELS = _get_vosk_models()
    return VOSK_MODELS


class VoskModelManager:
    """
    Manages Vosk model downloads and caching.

    Similar to Whisper's automatic model management, downloads
    models on-demand to ~/.config/nerd-dictation/
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize model manager.

        Args:
            models_dir: Directory to store models (default: ~/.config/nerd-dictation)
        """
        if models_dir is None:
            self.models_dir = Path.home() / ".config" / "nerd-dictation"
        else:
            self.models_dir = Path(models_dir)

        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)

        debug(f"VoskModelManager initialized with models_dir: {self.models_dir}")

    def list_available_models(self, language: Optional[str] = None) -> Dict:
        """
        List all available models for download.

        Args:
            language: Filter by language code (e.g., 'en', 'es'). None for all.

        Returns:
            Dictionary of available models
        """
        models = get_vosk_models_dict()
        if language:
            return {language: models.get(language, {})}
        return models

    def list_downloaded_models(self) -> List[str]:
        """
        List all models that are already downloaded.

        Returns:
            List of model names (directory names)
        """
        if not self.models_dir.exists():
            return []

        models = []
        for item in self.models_dir.iterdir():
            if item.is_dir() and item.name.startswith("vosk-model"):
                models.append(item.name)

        debug(f"Found {len(models)} downloaded models: {models}")
        return sorted(models)

    def is_model_downloaded(self, model_name: str) -> bool:
        """
        Check if a specific model is already downloaded.

        Args:
            model_name: Name of the model (e.g., 'vosk-model-small-en-us-0.15')

        Returns:
            True if model exists and is valid
        """
        model_path = self.models_dir / model_name
        is_downloaded = model_path.exists() and model_path.is_dir()

        if is_downloaded:
            # Verify it has required files
            has_files = (model_path / "am").exists() or \
                       (model_path / "graph").exists() or \
                       any(model_path.glob("*.bin"))

            if not has_files:
                warning(f"Model directory exists but appears incomplete: {model_name}")
                return False

        return is_downloaded

    def get_model_path(self, language: str, size: str = "small") -> Optional[Path]:
        """
        Get path to a model, downloading if necessary.

        Args:
            language: Language code ('en', 'es')
            size: Model size ('small', 'medium', 'large', 'gigaspeech')

        Returns:
            Path to model directory, or None if download failed
        """
        # Get model info
        models = get_vosk_models_dict()
        lang_models = models.get(language)
        if not lang_models:
            error(f"Unsupported language: {language}")
            return None

        model_info = lang_models.get(size)
        if not model_info:
            error(f"Unsupported size '{size}' for language '{language}'")
            available = list(lang_models.keys())
            error(f"Available sizes: {available}")
            return None

        model_name = model_info["name"]
        model_path = self.models_dir / model_name

        # Check if already downloaded
        if self.is_model_downloaded(model_name):
            info(f"Using cached model: {model_name}")
            return model_path

        # Download model
        info(f"Model not found, downloading: {model_name} ({model_info['size']})")
        if self.download_model(language, size):
            return model_path

        return None

    def download_model(self, language: str, size: str = "small",
                      progress_callback=None) -> bool:
        """
        Download a Vosk model.

        Args:
            language: Language code ('en', 'es')
            size: Model size ('small', 'medium', 'large', 'gigaspeech')
            progress_callback: Optional callback(current, total) for download progress

        Returns:
            True if download and extraction successful
        """
        # Get model info
        models = get_vosk_models_dict()
        lang_models = models.get(language)
        if not lang_models:
            error(f"Unsupported language: {language}")
            return False

        model_info = lang_models.get(size)
        if not model_info:
            error(f"Unsupported size '{size}' for language '{language}'")
            return False

        model_name = model_info["name"]
        model_url = model_info["url"]
        zip_path = self.models_dir / f"{model_name}.zip"

        try:
            # Download with progress
            info(f"Downloading {model_name} from {model_url}")
            info(f"Size: {model_info['size']} - This may take a while...")

            def _progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(100, (downloaded / total_size) * 100)

                    # Call user callback if provided
                    if progress_callback:
                        progress_callback(downloaded, total_size)

                    # Log progress every 10%
                    if int(percent) % 10 == 0 and percent > 0:
                        debug(f"Download progress: {percent:.0f}%")

            urllib.request.urlretrieve(model_url, zip_path, _progress_hook)
            info(f"Download complete: {model_name}")

            # Extract ZIP file
            info(f"Extracting {model_name}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.models_dir)

            info(f"Extraction complete: {model_name}")

            # Cleanup ZIP file
            zip_path.unlink()
            debug(f"Removed ZIP file: {zip_path}")

            # Verify extraction
            model_path = self.models_dir / model_name
            if self.is_model_downloaded(model_name):
                info(f"Model ready: {model_path}")
                return True
            else:
                error(f"Model extraction failed: {model_name}")
                return False

        except urllib.error.URLError as e:
            error(f"Download failed: {e}")
            error(f"URL: {model_url}")
            return False
        except zipfile.BadZipFile as e:
            error(f"ZIP extraction failed: {e}")
            # Cleanup bad ZIP
            if zip_path.exists():
                zip_path.unlink()
            return False
        except Exception as e:
            error(f"Unexpected error during download: {e}")
            # Cleanup on error
            if zip_path.exists():
                zip_path.unlink()
            return False

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a downloaded model to free space.

        Args:
            model_name: Name of model to delete

        Returns:
            True if deleted successfully
        """
        model_path = self.models_dir / model_name

        if not model_path.exists():
            warning(f"Model not found: {model_name}")
            return False

        try:
            import shutil
            shutil.rmtree(model_path)
            info(f"Deleted model: {model_name}")
            return True
        except Exception as e:
            error(f"Failed to delete model {model_name}: {e}")
            return False

    def get_model_info(self, language: str, size: str) -> Optional[Dict]:
        """
        Get information about a specific model.

        Args:
            language: Language code
            size: Model size

        Returns:
            Model information dictionary or None
        """
        models = get_vosk_models_dict()
        lang_models = models.get(language)
        if not lang_models:
            return None

        return lang_models.get(size)
