"""
Controller for managing dictation backends (Vosk and Whisper)

Supports multiple speech recognition backends with unified interface.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from src.backends import BaseBackend, VoskBackend, WhisperBackend

logger = logging.getLogger(__name__)


class DictationController:
    """Manages dictation backends (Vosk and Whisper)"""

    def __init__(self, config, database):
        self.config = config
        self.database = database

        # Initialize available backends
        self.backends: Dict[str, BaseBackend] = {}
        self.current_backend: Optional[BaseBackend] = None
        self.backend_type = getattr(config, 'backend', 'vosk')

        self._init_backends()

    def reload_backend_from_config(self):
        """
        Reload the backend from the current config.
        Call this after config has been reloaded from database.
        """
        new_backend = getattr(self.config, 'backend', 'vosk')

        # Check if backend type changed
        if new_backend != self.backend_type:
            logger.info(f"Backend changed in config from {self.backend_type} to {new_backend}")
            self.set_backend(new_backend)

        # For Whisper backend, check if model size changed
        if new_backend == 'whisper' and 'whisper' in self.backends:
            whisper_backend = self.backends['whisper']
            new_model = getattr(self.config, 'whisper_model', 'medium')

            # Extract model size from Hugging Face ID (e.g., "Systran/faster-whisper-medium" -> "medium")
            if '/' in new_model:
                # Handle different model name patterns
                model_part = new_model.split('/')[-1]  # Get "faster-whisper-medium" or "faster-whisper-large-v3"
                if 'faster-whisper-' in model_part:
                    new_model_size = model_part.replace('faster-whisper-', '')  # Remove prefix to get "medium" or "large-v3"
                else:
                    new_model_size = model_part
            else:
                new_model_size = new_model

            current_model = whisper_backend.model_size

            if new_model_size != current_model:
                logger.info(f"Whisper model changed from '{current_model}' to '{new_model_size}'")
                # Stop any running session first
                if self.is_running():
                    logger.info("Stopping current session before model update")
                    self.stop()
                # Update the model
                whisper_backend.update_model_size(new_model_size)
    
    def _init_backends(self):
        """Initialize available backends"""
        try:
            # Initialize Vosk backend (nerd-dictation)
            if hasattr(self.config, 'nerd_dictation_dir'):
                venv_python = self.config.nerd_dictation_dir / "venv" / "bin" / "python"
                self.backends['vosk'] = VoskBackend(
                    nerd_dictation_dir=str(self.config.nerd_dictation_dir),
                    venv_python=str(venv_python),
                    models_dir=str(self.config.models_dir)
                )
                logger.info("Vosk backend initialized")
            else:
                logger.warning("Vosk backend not available: nerd-dictation_dir not configured")

            # Initialize Whisper backend if available
            try:
                whisper_model = getattr(self.config, 'whisper_model', 'medium')

                # Parse model size from full Hugging Face ID
                if '/' in whisper_model:
                    model_part = whisper_model.split('/')[-1]
                    if 'faster-whisper-' in model_part:
                        whisper_model = model_part.replace('faster-whisper-', '')
                    else:
                        whisper_model = model_part

                whisper_device = getattr(self.config, 'whisper_device', 'cuda')
                whisper_compute_type = getattr(self.config, 'whisper_compute_type', 'float16')

                # VAD configuration
                device_index = getattr(self.config, 'whisper_device_index', None)
                silence_duration = getattr(self.config, 'whisper_silence_duration', 1.0)
                energy_threshold = getattr(self.config, 'whisper_energy_threshold', 0.002)
                min_audio_length = getattr(self.config, 'whisper_min_audio_length', 0.3)

                self.backends['whisper'] = WhisperBackend(
                    model_size=whisper_model,
                    device=whisper_device,
                    compute_type=whisper_compute_type,
                    device_index=device_index,
                    silence_duration=silence_duration,
                    energy_threshold=energy_threshold,
                    min_audio_length=min_audio_length,
                    database=self.database
                )
                logger.info(f"Whisper backend initialized with model '{whisper_model}' on {whisper_device} "
                          f"(silence={silence_duration}s, threshold={energy_threshold}, min_length={min_audio_length}s)")
            except Exception as e:
                logger.warning(f"Whisper backend not available: {e}")

            # Select default backend
            if self.backend_type in self.backends:
                self.current_backend = self.backends[self.backend_type]
                logger.info(f"Using default backend: {self.backend_type}")
            elif self.backends:
                # Fallback to first available backend
                self.backend_type = next(iter(self.backends))
                self.current_backend = self.backends[self.backend_type]
                logger.info(f"Using fallback backend: {self.backend_type}")
            else:
                logger.error("No backends available")

        except Exception as e:
            logger.error(f"Failed to initialize backends: {e}")

    def set_backend(self, backend_type: str) -> bool:
        """
        Switch to a different backend.

        Args:
            backend_type: Backend type ('vosk' or 'whisper')

        Returns:
            True if backend switched successfully
        """
        if backend_type not in self.backends:
            logger.error(f"Backend '{backend_type}' not available")
            return False

        # Stop current backend if running
        if self.current_backend and self.current_backend.is_running:
            self.stop()

        self.backend_type = backend_type
        self.current_backend = self.backends[backend_type]
        logger.info(f"Switched to {backend_type} backend (current_backend is now: {self.current_backend.name})")
        return True

    def get_available_backends(self) -> Dict[str, str]:
        """
        Get list of available backends.

        Returns:
            Dictionary mapping backend names to descriptions
        """
        return {
            'vosk': 'Vosk (CPU) - Fast, lightweight, offline',
            'whisper': 'Whisper (GPU) - High accuracy, requires GPU'
        }

    def is_running(self) -> bool:
        """Check if dictation is currently running"""
        if not self.current_backend:
            return False

        # Check backend status
        if self.current_backend.is_running:
            return True

        # Check database session
        session = self.database.get_current_session()
        return session is not None

    def start(self, language: str, model_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Start dictation with specified language and model.

        Args:
            language: Language code (e.g., 'en', 'es')
            model_path: Optional path to specific model

        Returns:
            Tuple of (success, message)
        """
        if not self.current_backend:
            return False, "No backend available"

        logger.info(f"Starting dictation with backend_type: {self.backend_type}, current_backend: {self.current_backend.name}")

        # Check if backend is in ERROR state and try to reset it
        if hasattr(self.current_backend, 'status'):
            from src.backends.base_backend import BackendStatus
            if self.current_backend.status == BackendStatus.ERROR:
                logger.info(f"Backend is in ERROR state, attempting to reset...")
                if hasattr(self.current_backend, 'reset_error_state'):
                    if self.current_backend.reset_error_state():
                        logger.info("Backend reset from ERROR state successfully")
                    else:
                        logger.warning("Failed to reset backend from ERROR state")

        # Stop any existing session first
        if self.is_running():
            self.stop()

        try:
            # Start dictation with current backend
            success = self.current_backend.start(language, model_path)

            if success:
                # Record in database
                backend_name = self.current_backend.name.lower()

                # Get proper model name
                if model_path:
                    # Vosk: use the model directory name
                    model_name = Path(model_path).name
                elif backend_name == "whisper":
                    # Whisper: use the specific model size
                    if hasattr(self.current_backend, 'model_size'):
                        model_name = f"whisper-{self.current_backend.model_size}"
                    else:
                        # Fallback: extract from config
                        model_name = self.config.whisper_model.split('/')[-1]
                else:
                    # Fallback
                    model_name = self.backend_type

                self.database.start_session(
                    language=language,
                    model_path=model_path or "",
                    model_name=model_name,
                    backend=backend_name
                )

                return True, f"Dictado iniciado con {self.current_backend.name} ({model_name})"
            else:
                error_msg = getattr(self.current_backend, 'error_message', 'Unknown error')
                return False, f"Error al iniciar {self.current_backend.name}: {error_msg}"

        except Exception as e:
            logger.error(f"Failed to start dictation: {e}")
            return False, f"Error al iniciar: {str(e)}"

    def stop(self) -> Tuple[bool, str]:
        """
        Stop current dictation session.

        Returns:
            Tuple of (success, message)
        """
        if not self.current_backend:
            return False, "No backend available"

        try:
            # Stop the backend
            success = self.current_backend.stop()

            # Update database
            self.database.stop_session()

            if success:
                return True, "Dictado detenido"
            else:
                error_msg = getattr(self.current_backend, 'error_message', 'Unknown error')
                return False, f"Error al detener: {error_msg}"

        except Exception as e:
            logger.error(f"Failed to stop dictation: {e}")
            return False, f"Error al detener: {str(e)}"

    def restart(self, language: str, model_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Restart dictation with new language/model.

        Args:
            language: Language code
            model_path: Optional model path

        Returns:
            Tuple of (success, message)
        """
        self.stop()
        # Small delay to ensure clean stop
        import time
        time.sleep(0.5)
        return self.start(language, model_path)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current dictation status.

        Returns:
            Dictionary with status information
        """
        status = {
            "running": self.is_running(),
            "backend": self.backend_type,
            "backend_name": self.current_backend.name if self.current_backend else None,
            "available_backends": list(self.backends.keys())
        }

        # Get session info from database
        session = self.database.get_current_session()
        if session:
            status.update({
                "language": session["language"],
                "model_name": session["model_name"],
                "started_at": session["started_at"],
                "backend": session.get("backend", self.backend_type)
            })

        # Get backend-specific status
        if self.current_backend:
            # Add specific model info for Whisper
            if self.backend_type == "whisper" and hasattr(self.current_backend, 'model_size'):
                if not status.get("model_name") or status["model_name"] == "whisper":
                    status["model_name"] = f"whisper-{self.current_backend.model_size}"

            if hasattr(self.current_backend, 'get_status_info'):
                backend_info = self.current_backend.get_status_info()
                status.update(backend_info)
            elif hasattr(self.current_backend, 'get_performance_stats'):
                status.update(self.current_backend.get_performance_stats())

        # Clean up stale session if backend is not running
        if session and not status["running"]:
            self.database.stop_session()

        return status

    def get_available_models(self, language: Optional[str] = None) -> Dict[str, list]:
        """
        Get available models for all backends.

        Args:
            language: Optional language to filter models

        Returns:
            Dictionary mapping backend names to model lists
        """
        models = {}
        for backend_name, backend in self.backends.items():
            try:
                models[backend_name] = backend.get_available_models(language)
            except Exception as e:
                logger.error(f"Failed to get models for {backend_name}: {e}")
                models[backend_name] = []

        return models

    def supports_language(self, language: str, backend_type: Optional[str] = None) -> bool:
        """
        Check if a language is supported.

        Args:
            language: Language code to check
            backend_type: Specific backend to check (uses current if None)

        Returns:
            True if language is supported
        """
        backend = self.backends.get(backend_type) if backend_type else self.current_backend
        if not backend:
            return False

        return backend.supports_language(language)

    def cleanup(self):
        """Cleanup all backends"""
        for backend in self.backends.values():
            if hasattr(backend, 'cleanup'):
                backend.cleanup()
            elif backend.is_running:
                backend.stop()

        logger.info("DictationController cleaned up")