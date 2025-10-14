"""
Backends package for Dictation Manager.

Supports multiple speech recognition backends:
- VoskBackend: Wrapper for nerd-dictation (Vosk-based)
- WhisperBackend: GPU-accelerated Whisper backend
"""

from .base_backend import BaseBackend
from .vosk_backend import VoskBackend
from .whisper_backend import WhisperBackend

__all__ = ['BaseBackend', 'VoskBackend', 'WhisperBackend']