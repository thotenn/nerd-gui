"""
Whisper transcription module using faster-whisper with CUDA acceleration.

Provides high-performance speech transcription using faster-whisper
with GPU acceleration for real-time dictation.
"""

import logging
import threading
import queue
import time
from typing import Optional, Callable, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
    logger.info("faster-whisper available for GPU acceleration")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not available, install with: pip install faster-whisper")


class WhisperTranscriber:
    """
    High-performance Whisper transcription using faster-whisper.

    Optimized for real-time dictation with CUDA GPU acceleration.
    """

    def __init__(self,
                 model_size: str = "medium",
                 device: str = "cuda",
                 compute_type: str = "float16",
                 language: Optional[str] = None):
        """
        Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cuda or cpu)
            compute_type: Compute precision (float16 for GPU, float32 for CPU)
            language: Default language code (e.g., 'en', 'es')
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError("faster-whisper is required. Install with: pip install faster-whisper")

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.default_language = language

        self.model: Optional[WhisperModel] = None
        self.is_model_loaded = False
        self.load_lock = threading.Lock()

        # Transcription settings optimized for real-time dictation
        self.beam_size = 5  # Balance between speed and accuracy
        self.vad_filter = True  # Enable voice activity filter
        self.temperature = 0.0  # Deterministic output

        # Performance tracking
        self.total_transcriptions = 0
        self.total_audio_duration = 0.0
        self.total_transcription_time = 0.0

    def load_model(self) -> bool:
        """
        Load Whisper model with specified configuration.

        Returns:
            True if model loaded successfully, False otherwise
        """
        with self.load_lock:
            if self.is_model_loaded:
                return True

            try:
                logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}...")
                start_time = time.time()

                # Check CUDA availability before trying to load on GPU
                if self.device == "cuda":
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            logger.warning("CUDA requested but not available, falling back to CPU")
                            self.device = "cpu"
                            self.compute_type = "float32"
                    except ImportError:
                        pass  # torch not available, let WhisperModel handle it

                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )

                load_time = time.time() - start_time
                logger.info(f"Model loaded in {load_time:.2f} seconds on {self.device}")
                self.is_model_loaded = True
                return True

            except Exception as e:
                error_msg = str(e)
                # Log the full error
                logger.error(f"Failed to load Whisper model: {error_msg}")

                # Check if it's a CUDA memory error
                if "CUDA out of memory" in error_msg or "out of memory" in error_msg.lower():
                    # Try to get GPU memory info if available
                    try:
                        import torch
                        if torch.cuda.is_available():
                            memory_allocated = torch.cuda.memory_allocated() / 1024**3
                            memory_reserved = torch.cuda.memory_reserved() / 1024**3
                            logger.error(f"GPU memory status - Allocated: {memory_allocated:.2f} GB, Reserved: {memory_reserved:.2f} GB")
                    except:
                        pass

                    # Re-raise with more context
                    raise RuntimeError(f"CUDA out of memory when loading {self.model_size} model: {error_msg}")

                self.is_model_loaded = False
                raise  # Re-raise the exception for better error handling upstream

    def unload_model(self):
        """Unload model to free GPU memory."""
        import gc
        with self.load_lock:
            if self.model:
                del self.model
                self.model = None
                self.is_model_loaded = False

                # Force garbage collection to free memory
                gc.collect()

                # Try to clear CUDA cache if available
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        logger.info("CUDA cache cleared")
                except ImportError:
                    pass  # torch not available, that's fine

                logger.info("Whisper model unloaded and memory freed")

    def transcribe(self,
                   audio: np.ndarray,
                   language: Optional[str] = None,
                   on_progress: Optional[Callable[[float], None]] = None) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio array to text.

        Args:
            audio: Numpy array of audio samples (float32, normalized)
            language: Language code (auto-detect if None)
            on_progress: Optional progress callback (0.0 to 1.0)

        Returns:
            Dictionary with transcription results or None on error
        """
        if not self.is_model_loaded:
            if not self.load_model():
                return None

        if len(audio) == 0:
            logger.warning("Empty audio array provided")
            return None

        try:
            start_time = time.time()
            audio_duration = len(audio) / 16000.0  # Assuming 16kHz sample rate

            # Use specified language or default
            transcribe_language = language or self.default_language

            logger.debug(f"Transcribing {audio_duration:.2f}s of audio with language: {transcribe_language}")

            # Run transcription
            segments, info = self.model.transcribe(
                audio,
                language=transcribe_language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                temperature=self.temperature,
                word_timestamps=True
            )

            # Collect all segments
            text_parts = []
            word_timestamps = []
            confidence_scores = []

            for segment in segments:
                text_parts.append(segment.text)
                if segment.words:
                    for word in segment.words:
                        word_timestamps.append({
                            'word': word.word,
                            'start': word.start,
                            'end': word.end,
                            'probability': getattr(word, 'probability', None)
                        })
                        if hasattr(word, 'probability') and word.probability is not None:
                            confidence_scores.append(word.probability)

            full_text = ' '.join(text_parts).strip()

            # Calculate statistics
            transcription_time = time.time() - start_time
            avg_confidence = np.mean(confidence_scores) if confidence_scores else None

            self.total_transcriptions += 1
            self.total_audio_duration += audio_duration
            self.total_transcription_time += transcription_time

            result = {
                'text': full_text,
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': audio_duration,
                'transcription_time': transcription_time,
                'real_time_factor': transcription_time / audio_duration if audio_duration > 0 else 0,
                'avg_confidence': avg_confidence,
                'word_timestamps': word_timestamps,
                'segments': [{'text': seg.text, 'start': seg.start, 'end': seg.end} for seg in segments]
            }

            logger.debug(f"Transcription: '{full_text}' (RTF: {result['real_time_factor']:.2f})")
            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages.

        Returns:
            List of language codes supported by Whisper
        """
        # Whisper supports these languages
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', 'ko',
            'ar', 'tr', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'he', 'hi',
            'th', 'vi', 'cs', 'el', 'ro', 'hu', 'uk', 'id', 'ms', 'ca'
        ]

    def supports_language(self, language: str) -> bool:
        """
        Check if a language is supported.

        Args:
            language: Language code to check

        Returns:
            True if language is supported
        """
        return language in self.get_supported_languages()

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        if self.total_transcriptions == 0:
            return {
                'total_transcriptions': 0,
                'avg_real_time_factor': 0,
                'total_audio_duration': 0,
                'total_transcription_time': 0
            }

        return {
            'total_transcriptions': self.total_transcriptions,
            'avg_real_time_factor': self.total_transcription_time / self.total_audio_duration,
            'total_audio_duration': self.total_audio_duration,
            'total_transcription_time': self.total_transcription_time,
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self.total_transcriptions = 0
        self.total_audio_duration = 0.0
        self.total_transcription_time = 0.0


class TranscriptionWorker:
    """
    Background worker for transcribing audio chunks.

    Runs transcription in separate thread to avoid blocking
    the audio capture thread.
    """

    def __init__(self,
                 transcriber: WhisperTranscriber,
                 on_result: Callable[[Dict[str, Any]], None],
                 on_error: Callable[[str], None]):
        """
        Initialize transcription worker.

        Args:
            transcriber: WhisperTranscriber instance
            on_result: Callback for successful transcription
            on_error: Callback for transcription errors
        """
        self.transcriber = transcriber
        self.on_result = on_result
        self.on_error = on_error

        self.audio_queue = queue.Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.current_language: Optional[str] = None

    def start(self, language: Optional[str] = None):
        """Start transcription worker."""
        if self.is_running:
            logger.warning("Transcription worker already running")
            return

        self.is_running = True
        self.current_language = language

        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        logger.info("Started transcription worker")

    def stop(self):
        """Stop transcription worker."""
        if not self.is_running:
            return

        self.is_running = False

        # Add sentinel value to wake up worker
        self.audio_queue.put(None)

        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)

        logger.info("Stopped transcription worker")

    def add_audio(self, audio: np.ndarray):
        """
        Add audio chunk to transcription queue.

        Args:
            audio: Numpy array of audio samples
        """
        if self.is_running:
            self.audio_queue.put(audio)

    def set_language(self, language: Optional[str]):
        """
        Set transcription language.

        Args:
            language: Language code or None for auto-detect
        """
        self.current_language = language

    def _worker_loop(self):
        """Main worker loop that processes audio queue."""
        while self.is_running:
            try:
                # Get audio from queue with timeout
                audio = self.audio_queue.get(timeout=0.1)

                # Check for sentinel value
                if audio is None:
                    break

                # Transcribe audio
                result = self.transcriber.transcribe(audio, self.current_language)

                if result:
                    self.on_result(result)
                else:
                    self.on_error("Transcription failed")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                self.on_error(f"Worker error: {e}")