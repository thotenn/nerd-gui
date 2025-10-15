"""
Whisper backend implementation for Dictation Manager.

Provides GPU-accelerated speech transcription using faster-whisper
with real-time audio capture and keyboard output.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from src.backends.base_backend import BaseBackend, BackendStatus

logger = logging.getLogger(__name__)

# Try to import Whisper components
try:
    from src.backends.whisper.audio_capture import AudioCapture
    from src.backends.whisper.transcriber import WhisperTranscriber, TranscriptionWorker
    from src.backends.whisper.keyboard_output import KeyboardOutput, TextProcessor
    WHISPER_AVAILABLE = True
    logger.info("Whisper backend components imported successfully")
except ImportError as e:
    WHISPER_AVAILABLE = False
    logger.warning(f"Whisper backend not available: {e}")
    logger.info("Install with: ./install_whisper_backend.sh")


class WhisperBackend(BaseBackend):
    """
    GPU-accelerated Whisper dictation backend.

    Combines real-time audio capture, Whisper transcription,
    and keyboard output for seamless dictation.
    """

    def __init__(self,
                 model_size: str = "medium",
                 device: str = "cuda",
                 compute_type: str = "float16",
                 sample_rate: int = 16000,
                 device_index: Optional[int] = None,
                 silence_duration: float = 1.0,
                 energy_threshold: float = 0.002,
                 min_audio_length: float = 0.3):
        """
        Initialize Whisper backend.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cuda or cpu)
            compute_type: Compute precision (float16 for GPU, float32 for CPU)
            sample_rate: Audio sample rate
            device_index: Audio device index (None for auto-detect)
            silence_duration: Seconds of silence before processing speech
            energy_threshold: Microphone sensitivity threshold
            min_audio_length: Minimum audio length in seconds to process
        """
        super().__init__("Whisper")

        # Set default attributes first
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.sample_rate = sample_rate

        # VAD configuration
        self.device_index = device_index
        self.silence_duration = silence_duration
        self.energy_threshold = energy_threshold
        self.min_audio_length = min_audio_length

        # Session tracking (initialize even if dependencies missing)
        self.session_start_time: Optional[float] = None
        self.total_text_typed = 0
        self.last_transcription_time: Optional[float] = None
        self.is_first_chunk = True  # Track if this is the first chunk of the session

        # Component placeholders
        self.transcriber = None
        self.text_processor = None
        self.keyboard_output = None
        self.audio_capture: Optional[AudioCapture] = None
        self.transcription_worker: Optional[TranscriptionWorker] = None

        if not WHISPER_AVAILABLE:
            self._set_status(BackendStatus.ERROR,
                           "Whisper dependencies not installed. Run ./install_whisper_backend.sh")
            return

        # Initialize components
        try:
            self.transcriber = WhisperTranscriber(
                model_size=model_size,
                device=device,
                compute_type=compute_type
            )

            self.text_processor = TextProcessor()
            self.keyboard_output = KeyboardOutput(on_error=self._on_error)

            # Check dependencies
            self._check_dependencies()

        except Exception as e:
            self._set_status(BackendStatus.ERROR, f"Failed to initialize Whisper: {e}")

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        deps = self.keyboard_output.check_dependencies()
        if not deps['xdotool']:
            self._set_status(BackendStatus.ERROR,
                           "xdotool not found. Install with: sudo apt install xdotool")
        elif not deps['display']:
            self._set_status(BackendStatus.ERROR,
                           "No display available. Make sure X11 is running.")

    def start(self, language: str, model_path: Optional[str] = None) -> bool:
        """
        Start Whisper dictation.

        Args:
            language: Language code (e.g., 'en', 'es')
            model_path: Optional model path (not used for Whisper)

        Returns:
            True if dictation started successfully
        """
        if self.status == BackendStatus.ERROR:
            logger.error("Cannot start Whisper backend: in error state")
            return False

        if self.is_running:
            logger.warning("Whisper backend already running")
            return True

        try:
            self._set_status(BackendStatus.STARTING)

            # Check if model is loaded
            if not self.transcriber.is_model_loaded:
                if not self.transcriber.load_model():
                    self._set_status(BackendStatus.ERROR, "Failed to load Whisper model")
                    return False

            # Verify language support
            if not self.transcriber.supports_language(language):
                self._set_status(BackendStatus.ERROR,
                               f"Language '{language}' not supported by Whisper")
                return False

            # Start keyboard output
            if not self.keyboard_output.start():
                self._set_status(BackendStatus.ERROR, "Failed to start keyboard output")
                return False

            # Reset correction state for new session
            self.keyboard_output.reset_correction_state()

            # Start transcription worker
            self.transcription_worker = TranscriptionWorker(
                transcriber=self.transcriber,
                on_result=self._on_transcription_result,
                on_error=self._on_error
            )
            self.transcription_worker.start(language)

            # Start audio capture with configured parameters
            logger.info(f"Starting audio capture: device_index={self.device_index}, "
                       f"silence_duration={self.silence_duration}s, "
                       f"energy_threshold={self.energy_threshold}, "
                       f"min_audio_length={self.min_audio_length}s")

            self.audio_capture = AudioCapture(
                on_audio_chunk=self._on_audio_chunk,
                sample_rate=self.sample_rate,
                device_index=self.device_index,
                min_audio_length=self.min_audio_length,
                silence_duration=self.silence_duration,
                energy_threshold=self.energy_threshold
            )
            self.audio_capture.start()

            # Initialize session
            self.session_start_time = time.time()
            self.total_text_typed = 0
            self.last_transcription_time = None
            self.is_first_chunk = True  # Reset for new session

            self._set_status(BackendStatus.RUNNING)
            logger.info(f"Whisper dictation started with language '{language}'")

            return True

        except Exception as e:
            error_msg = f"Failed to start Whisper backend: {e}"
            logger.error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def stop(self) -> bool:
        """
        Stop Whisper dictation and optionally unload model.

        Returns:
            True if dictation stopped successfully
        """
        if not self.is_running:
            logger.warning("Whisper backend not running")
            return True

        try:
            self._set_status(BackendStatus.STOPPING)

            # Stop audio capture first
            if self.audio_capture:
                self.audio_capture.stop()
                self.audio_capture = None

            # Stop transcription worker
            if self.transcription_worker:
                self.transcription_worker.stop()
                self.transcription_worker = None

            # Stop keyboard output
            self.keyboard_output.stop()

            # Calculate session duration
            session_duration = None
            if self.session_start_time:
                session_duration = time.time() - self.session_start_time
                logger.info(f"Session ended. Duration: {session_duration:.1f}s, "
                          f"Text typed: {self.total_text_typed} chars")

            # Update session info
            self._current_session = {
                'backend': self.name.lower(),
                'model_size': self.model_size,
                'device': self.device,
                'duration': session_duration,
                'text_typed': self.total_text_typed,
                'performance_stats': self.transcriber.get_performance_stats()
            }

            # IMPORTANT: Unload model to free VRAM
            if self.transcriber:
                self.transcriber.unload_model()
                logger.info("Whisper model unloaded from VRAM")

            self._set_status(BackendStatus.STOPPED)
            logger.info("Whisper dictation stopped")

            return True

        except Exception as e:
            error_msg = f"Failed to stop Whisper backend: {e}"
            logger.error(error_msg)
            self._set_status(BackendStatus.ERROR, error_msg)
            return False

    def get_available_models(self, language: Optional[str] = None) -> List[str]:
        """
        Get available Whisper models.

        Args:
            language: Optional language filter (not used for Whisper)

        Returns:
            List of available model sizes
        """
        return ['tiny', 'base', 'small', 'medium', 'large']

    def supports_language(self, language: str) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language code to check

        Returns:
            True if language is supported
        """
        if not WHISPER_AVAILABLE or self.transcriber is None:
            return False
        return self.transcriber.supports_language(language)

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        stats = {
            'backend': self.name,
            'status': self.status.value,
            'total_text_typed': self.total_text_typed,
            'session_duration': time.time() - self.session_start_time if self.session_start_time else None,
            'last_transcription_time': self.last_transcription_time
        }

        if self.transcriber is not None:
            transcriber_stats = self.transcriber.get_performance_stats()
            stats.update(transcriber_stats)

        return stats

    def _on_audio_chunk(self, audio_chunk):
        """
        Handle audio chunk from VAD.

        Args:
            audio_chunk: Numpy array of audio samples
        """
        if self.transcription_worker:
            self.transcription_worker.add_audio(audio_chunk)

    def _on_transcription_result(self, result: Dict[str, Any]):
        """
        Handle successful transcription.

        Args:
            result: Transcription result dictionary
        """
        try:
            text = result['text']
            if not text.strip():
                return

            # Process the text (capitalization, punctuation, etc.)
            processed_text = self.text_processor.process_text(text)

            # Add space before chunk (except for first chunk)
            # This prevents chunks from being concatenated without spaces
            if not self.is_first_chunk:
                processed_text = ' ' + processed_text
                logger.debug("Added leading space to separate from previous chunk")
            else:
                self.is_first_chunk = False
                logger.debug("First chunk of session - no leading space")

            # Type the processed text WITHOUT correction
            # Each Whisper chunk is independent (not streaming), so we just append text
            self.keyboard_output.type_text(processed_text, enable_correction=False)

            # Update statistics
            self.total_text_typed += len(processed_text)
            self.last_transcription_time = time.time()

            logger.debug(f"Typed: '{processed_text}' "
                        f"(confidence: {result.get('avg_confidence', 0):.2f}, "
                        f"RTF: {result.get('real_time_factor', 0):.2f})")

        except Exception as e:
            logger.error(f"Failed to handle transcription result: {e}")
            self._on_error(f"Result handling error: {e}")

    def _on_error(self, error_message: str):
        """
        Handle errors from components.

        Args:
            error_message: Error message
        """
        logger.error(f"Whisper backend error: {error_message}")
        if self.status != BackendStatus.ERROR:
            self._set_status(BackendStatus.ERROR, error_message)

    def set_language(self, language: str):
        """
        Change transcription language during session.

        Args:
            language: New language code
        """
        if self.transcription_worker:
            self.transcription_worker.set_language(language)
            logger.info(f"Changed transcription language to '{language}'")

    def update_model_size(self, new_model_size: str) -> bool:
        """
        Update the Whisper model size. Unloads current model and prepares for new one.

        Args:
            new_model_size: New model size (tiny, base, small, medium, large)

        Returns:
            True if update successful
        """
        logger.info(f"Updating Whisper model from '{self.model_size}' to '{new_model_size}'")

        # Stop if running
        if self.is_running:
            logger.info("Stopping current session before model update")
            self.stop()

        # Unload current model if loaded
        if self.transcriber and self.transcriber.is_model_loaded:
            self.transcriber.unload_model()
            logger.info("Previous model unloaded from VRAM")

        # Update model size
        old_model = self.model_size
        self.model_size = new_model_size

        # Update transcriber with new model size
        if self.transcriber:
            self.transcriber.model_size = new_model_size
            self.transcriber.is_model_loaded = False
            logger.info(f"Model size updated from '{old_model}' to '{new_model_size}'")
            return True

        return False

    def cleanup(self):
        """Cleanup resources and unload model."""
        if self.is_running:
            self.stop()

        if self.transcriber is not None:
            self.transcriber.unload_model()
        logger.info("Whisper backend cleaned up")