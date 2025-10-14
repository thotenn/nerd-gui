"""
Vosk backend implementation for Dictation Manager.

Wraps the existing nerd-dictation functionality to provide
a consistent interface alongside the new Whisper backend.
"""

import logging
import subprocess
import time
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from src.backends.base_backend import BaseBackend, BackendStatus

logger = logging.getLogger(__name__)


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

        # Verify paths exist
        if not self.nerd_dictation_dir.exists():
            logger.error(f"nerd-dictation directory not found: {nerd_dictation_dir}")
            self._set_status(BackendStatus.ERROR,
                           f"nerd-dictation not found at {nerd_dictation_dir}")

        if not os.path.exists(venv_python):
            logger.error(f"Virtual environment python not found: {venv_python}")
            self._set_status(BackendStatus.ERROR,
                           f"Virtual environment not found at {venv_python}")

        # Session tracking
        self.session_start_time: Optional[float] = None
        self.current_language: Optional[str] = None
        self.current_model_path: Optional[str] = None
        self.nerd_dictation_process: Optional[subprocess.Popen] = None

    def start(self, language: str, model_path: Optional[str] = None) -> bool:
        """
        Start Vosk dictation using nerd-dictation.

        Args:
            language: Language code (e.g., 'en', 'es')
            model_path: Optional path to specific model

        Returns:
            True if dictation started successfully
        """
        if self.status == BackendStatus.ERROR:
            logger.error("Cannot start Vosk backend: in error state")
            return False

        if self.is_running:
            logger.warning("Vosk backend already running")
            return True

        try:
            self._set_status(BackendStatus.STARTING)

            # Find or use specified model
            if model_path:
                model_full_path = self.models_dir / model_path
            else:
                model_full_path = self._find_best_model(language)

            if not model_full_path or not model_full_path.exists():
                error_msg = f"Model not found for language '{language}'"
                logger.error(error_msg)
                self._set_status(BackendStatus.ERROR, error_msg)
                return False

            # Check if nerd-dictation is already running
            if self._is_nerd_dictation_running():
                logger.info("nerd-dictation already running, stopping first...")
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

            logger.info(f"Starting nerd-dictation with model: {model_full_path}")
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
                logger.error(error_msg)
                self._set_status(BackendStatus.ERROR, error_msg)
                return False

            # Initialize session tracking
            self.session_start_time = time.time()
            self.current_language = language
            self.current_model_path = str(model_full_path)

            self._set_status(BackendStatus.RUNNING)
            logger.info(f"Vosk dictation started with language '{language}' "
                       f"using model '{model_full_path.name}'")

            return True

        except Exception as e:
            error_msg = f"Failed to start Vosk backend: {e}"
            logger.error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def stop(self) -> bool:
        """
        Stop Vosk dictation.

        Returns:
            True if dictation stopped successfully
        """
        if not self.is_running:
            logger.warning("Vosk backend not running")
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
            logger.info("Vosk dictation stopped")

            return success

        except Exception as e:
            error_msg = f"Failed to stop Vosk backend: {e}"
            logger.error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def get_available_models(self, language: Optional[str] = None) -> List[str]:
        """
        Get available Vosk models.

        Args:
            language: Optional language to filter models

        Returns:
            List of available model names
        """
        if not self.models_dir.exists():
            logger.warning(f"Models directory not found: {self.models_dir}")
            return []

        models = []
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith("vosk-model"):
                # Filter by language if specified
                if language:
                    # Check if model name contains language code
                    if f"-{language}-" in model_dir.name or model_dir.name.endswith(f"-{language}"):
                        models.append(model_dir.name)
                else:
                    models.append(model_dir.name)

        return sorted(models)

    def supports_language(self, language: str) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language code to check

        Returns:
            True if language is supported
        """
        models = self.get_available_models(language)
        return len(models) > 0

    def _find_best_model(self, language: str) -> Optional[Path]:
        """
        Find the best available model for a language.

        Prefers larger models when available.

        Args:
            language: Language code

        Returns:
            Path to best model or None if not found
        """
        models = self.get_available_models(language)
        if not models:
            return None

        # Sort models by size preference (large > medium > small > tiny)
        size_priority = {
            'large': 4,
            'medium': 3,
            'small': 2,
            'tiny': 1,
            'base': 2  # Consider base similar to small
        }

        def model_priority(model_name):
            for size, priority in size_priority.items():
                if size in model_name:
                    return priority
            return 0  # Unknown size

        models.sort(key=model_priority, reverse=True)
        best_model = models[0]

        return self.models_dir / best_model

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
                        logger.warning("Graceful shutdown timed out")

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
            logger.error(f"Failed to stop nerd-dictation: {e}")
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
            'models_dir': str(self.models_dir),
            'available_models': {
                'es': self.get_available_models('es'),
                'en': self.get_available_models('en')
            }
        }

        if self.session_start_time:
            info['session_duration'] = time.time() - self.session_start_time

        return info