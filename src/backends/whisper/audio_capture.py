"""
Real-time audio capture with Voice Activity Detection for Whisper backend.

This module provides continuous microphone audio capture with intelligent
voice activity detection to determine when to send audio for transcription.
"""

import pyaudio
import numpy as np
import threading
import queue
import time
from typing import Optional, Callable
from src.core.logging_controller import info, debug, warning, error, critical


class MicrophoneStream:
    """
    Captures audio from the microphone in real-time.

    Uses PyAudio to capture 16kHz mono audio, suitable for Whisper models.
    """

    def __init__(self,
                 sample_rate: int = 16000,
                 chunk_size: int = 480,
                 channels: int = 1,
                 format: int = pyaudio.paInt16,
                 device_index: Optional[int] = None):
        """
        Initialize microphone stream.

        Args:
            sample_rate: Audio sample rate (Whisper expects 16kHz)
            chunk_size: Number of audio frames per buffer (480 = 30ms at 16kHz, required for WebRTC VAD)
            channels: Number of audio channels (1 for mono)
            format: Audio format (16-bit PCM)
            device_index: Specific audio device index (None for default)
        """
        self.target_sample_rate = sample_rate  # What Whisper wants (16kHz)
        self.actual_sample_rate = sample_rate  # What we're actually using (may be different)
        self.sample_rate = sample_rate  # For compatibility
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format
        self.device_index = device_index

        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread: Optional[threading.Thread] = None

    def _get_device_native_sample_rate(self, device_index):
        """Get the native sample rate of the audio device"""
        try:
            if device_index is None:
                return None  # Use requested rate for default device

            device_info = self.audio.get_device_info_by_index(device_index)
            return int(device_info.get('defaultSampleRate', self.sample_rate))
        except Exception as e:
            warning(f"Could not get device sample rate: {e}")
            return None

    def start(self):
        """Start recording audio from microphone."""
        if self.is_recording:
            warning("Already recording")
            return

        self.is_recording = True

        # Build stream parameters
        stream_params = {
            'format': self.format,
            'channels': self.channels,
            'rate': self.sample_rate,
            'input': True,
            'frames_per_buffer': self.chunk_size,
            'stream_callback': self._audio_callback
        }

        # Add device index if specified
        if self.device_index is not None:
            stream_params['input_device_index'] = self.device_index

        # Try to open with requested sample rate
        try:
            self.stream = self.audio.open(**stream_params)
            self.actual_sample_rate = self.target_sample_rate
        except Exception as e:
            # If it fails and we have a specific device, try with device's native rate
            if self.device_index is not None:
                native_rate = self._get_device_native_sample_rate(self.device_index)
                if native_rate and native_rate != self.target_sample_rate:
                    warning(f"Device {self.device_index} doesn't support {self.target_sample_rate}Hz, using {native_rate}Hz with resampling")
                    stream_params['rate'] = native_rate
                    try:
                        self.stream = self.audio.open(**stream_params)
                        self.actual_sample_rate = native_rate
                        info(f"Using device native sample rate: {native_rate}Hz (will resample to {self.target_sample_rate}Hz)")
                    except Exception as e2:
                        error(f"Failed to open audio stream: {e2}")
                        raise
                else:
                    raise
            else:
                raise

        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()

        info(f"Started recording at {self.actual_sample_rate}Hz" +
                   (f" (resampling to {self.target_sample_rate}Hz)" if self.actual_sample_rate != self.target_sample_rate else "") +
                   (f" on device {self.device_index}" if self.device_index else ""))

    def stop(self):
        """Stop recording and cleanup resources."""
        if not self.is_recording:
            return

        self.is_recording = False

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        if self.recording_thread:
            self.recording_thread.join(timeout=1.0)

        self.audio.terminate()
        info("Stopped recording")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for incoming audio data."""
        if status:
            warning(f"Audio callback status: {status}")

        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def _record_loop(self):
        """Background thread that processes audio queue."""
        while self.is_recording:
            try:
                # Get audio data with timeout to prevent blocking
                data = self.audio_queue.get(timeout=0.1)
                yield data
            except queue.Empty:
                continue

    def read_chunk(self) -> Optional[np.ndarray]:
        """
        Read a single audio chunk.

        Returns:
            Numpy array of audio samples or None if no data available
        """
        try:
            data = self.audio_queue.get_nowait()
            # Convert bytes to numpy array of int16 samples
            audio_array = np.frombuffer(data, dtype=np.int16)
            # Convert to float32 and normalize to [-1, 1]
            audio_array = audio_array.astype(np.float32) / 32768.0

            # Resample if necessary
            if self.actual_sample_rate != self.target_sample_rate:
                # Calculate new length after resampling
                ratio = self.target_sample_rate / self.actual_sample_rate
                new_length = int(len(audio_array) * ratio)

                # Simple linear interpolation resampling
                x_old = np.linspace(0, 1, len(audio_array))
                x_new = np.linspace(0, 1, new_length)
                audio_array = np.interp(x_new, x_old, audio_array)

            return audio_array
        except queue.Empty:
            return None


class VoiceActivityDetector:
    """
    Detects voice activity in audio streams.

    Uses WebRTC VAD or energy-based detection to identify
    when speech is present and when it ends.
    """

    def __init__(self,
                 sample_rate: int = 16000,
                 frame_duration_ms: int = 30,
                 energy_threshold: float = 0.001,
                 silence_duration: float = 1.0,
                 vad_aggressiveness: int = 2):
        """
        Initialize VAD.

        Args:
            sample_rate: Audio sample rate
            frame_duration_ms: Duration of each frame in milliseconds
            energy_threshold: Minimum audio energy to consider as speech (lowered for better sensitivity)
            silence_duration: Seconds of silence before considering speech ended
            vad_aggressiveness: WebRTC VAD aggressiveness level (0-3, default 2)
        """
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.energy_threshold = energy_threshold
        self.silence_frames = int(silence_duration * 1000 / frame_duration_ms)
        self.vad_aggressiveness = vad_aggressiveness

        self.is_speaking = False
        self.silence_counter = 0
        self.audio_buffer = []

        # Try to import webrtcvad, fallback to energy-based detection
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(self.vad_aggressiveness)
            self.use_webrtcvad = True
            info(f"Using WebRTC VAD with aggressiveness level {self.vad_aggressiveness}")
        except ImportError:
            self.vad = None
            self.use_webrtcvad = False
            warning("WebRTC VAD not available, using energy-based detection")

    def process_frame(self, audio_frame: np.ndarray) -> tuple[bool, Optional[np.ndarray]]:
        """
        Process a single audio frame.

        Args:
            audio_frame: Numpy array of audio samples

        Returns:
            Tuple of (speech_detected, audio_chunk_ready_for_transcription)
        """
        if self.use_webrtcvad:
            return self._process_webrtcvad_frame(audio_frame)
        else:
            return self._process_energy_frame(audio_frame)

    def _process_webrtcvad_frame(self, audio_frame: np.ndarray) -> tuple[bool, Optional[np.ndarray]]:
        """Process frame using WebRTC VAD."""
        # Convert float32 back to int16 for WebRTC VAD
        audio_int16 = (audio_frame * 32768).astype(np.int16)

        # WebRTC VAD expects specific frame sizes
        frame_bytes = audio_int16.tobytes()

        # Check if this frame contains speech
        is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

        self.audio_buffer.extend(audio_frame)

        if is_speech:
            if not self.is_speaking:
                self.is_speaking = True
                info("Speech started (WebRTC VAD)")
            self.silence_counter = 0
        else:
            if self.is_speaking:
                self.silence_counter += 1
                debug(f"Silence detected: {self.silence_counter}/{self.silence_frames} frames")
                if self.silence_counter >= self.silence_frames:
                    # Speech ended, return buffered audio
                    self.is_speaking = False
                    audio_chunk = np.array(self.audio_buffer)
                    duration = len(audio_chunk) / self.sample_rate
                    self.audio_buffer = []
                    self.silence_counter = 0
                    info(f"Speech ended (WebRTC VAD): {len(audio_chunk)} samples ({duration:.2f}s)")
                    return (False, audio_chunk)

        return (is_speech, None)

    def _process_energy_frame(self, audio_frame: np.ndarray) -> tuple[bool, Optional[np.ndarray]]:
        """Process frame using energy-based detection."""
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_frame ** 2))

        self.audio_buffer.extend(audio_frame)

        if energy > self.energy_threshold:
            if not self.is_speaking:
                self.is_speaking = True
                info(f"Speech started (energy-based): energy={energy:.4f} > threshold={self.energy_threshold:.4f}")
            self.silence_counter = 0
            debug(f"Speech active: energy={energy:.4f}")
        else:
            if self.is_speaking:
                self.silence_counter += 1
                debug(f"Silence detected: {self.silence_counter}/{self.silence_frames} frames (energy={energy:.4f})")
                if self.silence_counter >= self.silence_frames:
                    # Speech ended, return buffered audio
                    self.is_speaking = False
                    audio_chunk = np.array(self.audio_buffer)
                    duration = len(audio_chunk) / self.sample_rate
                    self.audio_buffer = []
                    self.silence_counter = 0
                    info(f"Speech ended (energy-based): {len(audio_chunk)} samples ({duration:.2f}s)")
                    return (False, audio_chunk)
            else:
                # Not speaking and low energy - just noise
                debug(f"Background noise: energy={energy:.4f}")

        return (energy > self.energy_threshold, None)

    def reset(self):
        """Reset VAD state."""
        self.is_speaking = False
        self.silence_counter = 0
        self.audio_buffer = []


class AudioCapture:
    """
    Main audio capture class that combines microphone and VAD.

    Continuously captures audio and uses VAD to determine when
    to send audio chunks for transcription.
    """

    def __init__(self,
                 on_audio_chunk: Callable[[np.ndarray], None],
                 sample_rate: int = 16000,
                 device_index: Optional[int] = None,
                 min_audio_length: float = 0.3,
                 chunk_size: int = 480,
                 channels: int = 1,
                 vad_aggressiveness: int = 2,
                 **kwargs):
        """
        Initialize audio capture.

        Args:
            on_audio_chunk: Callback function when audio chunk is ready
            sample_rate: Audio sample rate
            device_index: Specific audio device index (None for default)
            min_audio_length: Minimum audio length in seconds to process
            chunk_size: Audio chunk size for VAD (must be 160, 320, 480, or 960)
            channels: Number of audio channels (1 for mono, 2 for stereo)
            vad_aggressiveness: WebRTC VAD aggressiveness level (0-3)
            **kwargs: Additional arguments for VAD
        """
        self.on_audio_chunk = on_audio_chunk
        self.sample_rate = sample_rate
        self.min_audio_length = min_audio_length

        self.mic_stream = MicrophoneStream(
            sample_rate=sample_rate,
            device_index=device_index,
            chunk_size=chunk_size,
            channels=channels
        )
        self.vad = VoiceActivityDetector(
            sample_rate=sample_rate,
            vad_aggressiveness=vad_aggressiveness,
            **kwargs
        )

        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None

    def start(self):
        """Start audio capture with VAD."""
        if self.is_running:
            warning("Audio capture already running")
            return

        self.is_running = True
        self.mic_stream.start()

        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()

        info("Started audio capture with VAD")

    def stop(self):
        """Stop audio capture."""
        if not self.is_running:
            return

        self.is_running = False
        self.mic_stream.stop()

        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)

        self.vad.reset()
        info("Stopped audio capture")

    def _capture_loop(self):
        """Main capture loop that runs in background thread."""
        while self.is_running:
            # Read audio chunk from microphone
            audio_frame = self.mic_stream.read_chunk()
            if audio_frame is None:
                time.sleep(0.01)
                continue

            # Process frame with VAD
            speech_detected, audio_chunk = self.vad.process_frame(audio_frame)

            # If VAD detected speech end, send chunk for transcription
            if audio_chunk is not None and len(audio_chunk) > 0:
                # Minimum chunk size to avoid processing very short audio
                min_samples = int(self.min_audio_length * self.sample_rate)
                if len(audio_chunk) >= min_samples:
                    debug(f"Audio chunk ready: {len(audio_chunk)} samples ({len(audio_chunk)/self.sample_rate:.2f}s)")
                    self.on_audio_chunk(audio_chunk)
                else:
                    debug(f"Audio chunk too short: {len(audio_chunk)} samples ({len(audio_chunk)/self.sample_rate:.2f}s) < {min_samples} samples ({self.min_audio_length}s)")