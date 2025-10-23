"""
Vosk backend implementation for Dictation Manager.

Wraps the existing nerd-dictation functionality to provide
a consistent interface alongside the new Whisper backend.
"""

import subprocess
import time
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from .base_backend import BaseBackend, BackendStatus
from .vosk_model_manager import VoskModelManager

from src.core.logging_controller import info, debug, warning, error, critical


class VoskBackend(BaseBackend):
    """
    Vosk-based dictation backend using nerd-dictation.

    Provides backward compatibility with existing nerd-dictation
    implementation while exposing the unified backend interface.
    """

    def __init__(self,
                 nerd_dictation_dir: str,
                 venv_python: str,
                 models_dir: str):
        """
        Initialize Vosk backend.

        Args:
            nerd_dictation_dir: Path to nerd-dictation installation
            venv_python: Path to nerd-dictation's virtual environment python
            models_dir: Directory containing Vosk models
        """
        super().__init__("Vosk")

        self.nerd_dictation_dir = Path(nerd_dictation_dir)
        self.venv_python = venv_python
        self.models_dir = Path(models_dir)

        # Initialize model manager for automatic downloads
        self.model_manager = VoskModelManager(self.models_dir)
        info("VoskModelManager initialized - models will download automatically if needed")

        # Verify paths exist
        if not self.nerd_dictation_dir.exists():
            error(f"nerd-dictation directory not found: {nerd_dictation_dir}")
            self._set_status(BackendStatus.ERROR,
                           f"nerd-dictation not found at {nerd_dictation_dir}")

        if not os.path.exists(venv_python):
            error(f"Virtual environment python not found: {venv_python}")
            self._set_status(BackendStatus.ERROR,
                           f"Virtual environment not found at {venv_python}")

        # Session tracking
        self.session_start_time: Optional[float] = None
        self.current_language: Optional[str] = None
        self.current_model_path: Optional[str] = None
        self.current_model_size: Optional[str] = None  # Track model size
        self.nerd_dictation_process: Optional[subprocess.Popen] = None

    def start(self, language: str, model_size: str = "small") -> bool:
        """
        Start Vosk dictation using nerd-dictation.

        Args:
            language: Language code (e.g., 'en', 'es')
            model_size: Model size ('small', 'medium', 'large', 'gigaspeech')
                       OR model name/path for backward compatibility
                       Default: 'small' for fast startup

        Returns:
            True if dictation started successfully
        """
        if self.status == BackendStatus.ERROR:
            error("Cannot start Vosk backend: in error state")
            return False

        if self.is_running:
            warning("Vosk backend already running")
            return True

        try:
            self._set_status(BackendStatus.STARTING)

            # Backward compatibility: detect if model_size is actually a path or model name
            actual_model_size = self._normalize_model_size(language, model_size)

            # Get model path, downloading if necessary
            info(f"Requesting Vosk model: {language}/{actual_model_size}")
            model_full_path = self.model_manager.get_model_path(language, actual_model_size)

            if not model_full_path:
                error_msg = f"Failed to get model for language '{language}', size '{model_size}'"
                error(error_msg)
                self._set_status(BackendStatus.ERROR, error_msg)
                return False

            # Check if nerd-dictation is already running
            if self._is_nerd_dictation_running():
                info("nerd-dictation already running, stopping first...")
                self._stop_nerd_dictation()

            # Start nerd-dictation with the selected model
            cmd = [
                self.venv_python,
                str(self.nerd_dictation_dir / "nerd-dictation"),
                "begin",
                f"--vosk-model-dir={model_full_path}"
            ]

            # Set working directory to nerd-dictation
            cwd = str(self.nerd_dictation_dir)

            info(f"Starting nerd-dictation with model: {model_full_path}")
            self.nerd_dictation_process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give it a moment to start
            time.sleep(0.5)

            # Check if process started successfully
            if self.nerd_dictation_process.poll() is not None:
                # Process terminated early
                stdout, stderr = self.nerd_dictation_process.communicate()
                error_msg = f"nerd-dictation failed to start: {stderr}"
                error(error_msg)
                self._set_status(BackendStatus.ERROR, error_msg)
                return False

            # Initialize session tracking
            self.session_start_time = time.time()
            self.current_language = language
            self.current_model_path = str(model_full_path)
            self.current_model_size = actual_model_size  # Use normalized size

            self._set_status(BackendStatus.RUNNING)
            info(f"Vosk dictation started with language '{language}', "
                       f"size '{actual_model_size}' using model '{model_full_path.name}'")

            return True

        except Exception as e:
            error_msg = f"Failed to start Vosk backend: {e}"
            error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def stop(self) -> bool:
        """
        Stop Vosk dictation.

        Returns:
            True if dictation stopped successfully
        """
        if not self.is_running:
            warning("Vosk backend not running")
            return True

        try:
            self._set_status(BackendStatus.STOPPING)

            # Stop nerd-dictation
            success = self._stop_nerd_dictation()

            # Calculate session duration
            session_duration = None
            if self.session_start_time:
                session_duration = time.time() - self.session_start_time

            # Update session info
            self._current_session = {
                'backend': self.name.lower(),
                'language': self.current_language,
                'model_path': self.current_model_path,
                'model_name': Path(self.current_model_path).name if self.current_model_path else None,
                'duration': session_duration
            }

            self._set_status(BackendStatus.STOPPED)
            info("Vosk dictation stopped")

            return success

        except Exception as e:
            error_msg = f"Failed to stop Vosk backend: {e}"
            error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def get_available_models(self, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available Vosk models (both downloaded and available for download).

        Args:
            language: Optional language to filter models

        Returns:
            Dictionary with 'downloaded' and 'available' models
        """
        downloaded = self.model_manager.list_downloaded_models()
        available = self.model_manager.list_available_models(language)

        return {
            'downloaded': downloaded,
            'available': available
        }

    def supports_language(self, language: str) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language code to check

        Returns:
            True if language is supported
        """
        available = self.model_manager.list_available_models(language)
        return language in available and len(available[language]) > 0

    def _normalize_model_size(self, language: str, model_input: str) -> str:
        """
        Normalize model input to a standard size.

        Handles backward compatibility with old model names/paths.

        Args:
            language: Language code
            model_input: Can be:
                - Size: 'small', 'medium', 'large', 'gigaspeech'
                - Model name: 'vosk-model-es-0.42'
                - Full path: '/path/to/vosk-model-es-0.42'

        Returns:
            Normalized size string
        """
        # If already a valid size, return as-is
        valid_sizes = {'small', 'medium', 'large', 'gigaspeech'}
        if model_input in valid_sizes:
            return model_input

        # Extract model name from path if it's a full path
        if '/' in model_input:
            model_name = Path(model_input).name
            debug(f"Extracted model name from path: {model_name}")
        else:
            model_name = model_input

        # Map model names to sizes
        # English models
        if 'small-en' in model_name or model_name == 'vosk-model-small-en-us-0.15':
            return 'small'
        elif 'gigaspeech' in model_name or model_name == 'vosk-model-en-us-0.42-gigaspeech':
            return 'gigaspeech'
        elif language == 'en' and ('0.22' in model_name or 'lgraph' in model_name):
            # Handles both old (vosk-model-en-us-0.22) and new (vosk-model-en-us-0.22-lgraph)
            return 'medium'

        # Spanish models
        elif 'small-es' in model_name or model_name == 'vosk-model-small-es-0.42':
            return 'small'
        elif language == 'es' and 'vosk-model-es-0.42' == model_name:
            return 'large'

        # Fallback: try to detect 'small' or 'large' in name
        if 'small' in model_name.lower():
            return 'small'
        elif 'large' in model_name.lower():
            return 'large'
        elif 'medium' in model_name.lower():
            return 'medium'

        # Default fallback
        warning(f"Could not determine size from '{model_input}', defaulting to 'small'")
        return 'small'

    def _is_nerd_dictation_running(self) -> bool:
        """Check if nerd-dictation is currently running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'nerd-dictation begin'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _stop_nerd_dictation(self) -> bool:
        """Stop any running nerd-dictation processes."""
        try:
            # Try graceful shutdown first
            if self.nerd_dictation_process:
                # Check if process is still running
                if self.nerd_dictation_process.poll() is None:
                    # Try to stop gracefully using nerd-dictation end
                    try:
                        subprocess.run(
                            [self.venv_python, str(self.nerd_dictation_dir / "nerd-dictation"), "end"],
                            cwd=str(self.nerd_dictation_dir),
                            capture_output=True,
                            timeout=5
                        )
                    except subprocess.TimeoutExpired:
                        warning("Graceful shutdown timed out")

                    # Wait a bit for graceful shutdown
                    time.sleep(0.5)

                    # Check if process stopped
                    if self.nerd_dictation_process.poll() is not None:
                        self.nerd_dictation_process = None
                        return True

                # Force kill if still running
                try:
                    self.nerd_dictation_process.terminate()
                    self.nerd_dictation_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.nerd_dictation_process.kill()
                    self.nerd_dictation_process.wait(timeout=3)

                self.nerd_dictation_process = None

            # Also kill any remaining nerd-dictation processes
            subprocess.run(['pkill', '-f', 'nerd-dictation begin'], capture_output=True)

            return True

        except Exception as e:
            error(f"Failed to stop nerd-dictation: {e}")
            return False

    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information.

        Returns:
            Dictionary with status details
        """
        info = {
            'backend': self.name,
            'status': self.status.value,
            'is_running': self.is_running,
            'nerd_dictation_running': self._is_nerd_dictation_running(),
            'current_language': self.current_language,
            'current_model': Path(self.current_model_path).name if self.current_model_path else None,
            'models_dir': str(self.models_dir)
            # Note: available_models removed - expensive to compute and not needed for status updates
            # Use get_available_models() directly when needed (e.g., in settings)
        }

        if self.session_start_time:
            info['session_duration'] = time.time() - self.session_start_time

        return info