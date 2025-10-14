"""
Abstract base class for dictation backends.

All backends must implement this interface to work with DictationController.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum


class BackendStatus(Enum):
    """Possible status values for dictation backends."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class BaseBackend(ABC):
    """
    Abstract base class that all dictation backends must inherit from.

    This ensures a consistent interface across different speech recognition
    implementations (Vosk, Whisper, etc.).
    """

    def __init__(self, name: str):
        """
        Initialize the backend.

        Args:
            name: Human-readable name of the backend (e.g., "Whisper", "Vosk")
        """
        self.name = name
        self._status = BackendStatus.STOPPED
        self._error_message: Optional[str] = None
        self._current_session: Optional[Dict[str, Any]] = None

    @property
    def status(self) -> BackendStatus:
        """Get the current status of the backend."""
        return self._status

    @property
    def error_message(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self._error_message

    @property
    def is_running(self) -> bool:
        """Check if the backend is currently running."""
        return self._status == BackendStatus.RUNNING

    @abstractmethod
    def start(self, language: str, model_path: Optional[str] = None) -> bool:
        """
        Start dictation with the specified language and model.

        Args:
            language: Language code (e.g., 'en', 'es')
            model_path: Optional path to specific model to use

        Returns:
            True if dictation started successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop dictation.

        Returns:
            True if dictation stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_available_models(self, language: Optional[str] = None) -> list:
        """
        Get list of available models for the specified language.

        Args:
            language: Optional language code to filter models

        Returns:
            List of available model names/paths
        """
        pass

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """
        Check if the backend supports the specified language.

        Args:
            language: Language code to check

        Returns:
            True if language is supported, False otherwise
        """
        pass

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current session.

        Returns:
            Dictionary with session information or None if no active session
        """
        return self._current_session.copy() if self._current_session else None

    def get_status_info(self) -> Dict[str, Any]:
        """
        Get status information for the GUI.

        Returns:
            Dictionary with status information
        """
        return {
            "backend_name": self.name,
            "status": self.status.value,
            "error_message": self.error_message,
            "is_running": self.is_running
        }

    def _set_status(self, status: BackendStatus, error_message: Optional[str] = None):
        """
        Set the backend status and optional error message.

        Args:
            status: New status value
            error_message: Optional error message for ERROR status
        """
        self._status = status
        self._error_message = error_message