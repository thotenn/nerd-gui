#!/usr/bin/env python3
"""
Debug script for testing Voice Activity Detection in real-time.
This helps tune VAD parameters by showing live audio energy levels.
"""

import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from src.core.config import Config
from src.backends.whisper.audio_capture import AudioCapture
import time


def on_audio_chunk(audio_chunk):
    """Callback when audio chunk is ready for transcription"""
    duration = len(audio_chunk) / 16000
    logger.info(f"🎤 AUDIO CHUNK READY FOR TRANSCRIPTION: {len(audio_chunk)} samples ({duration:.2f}s)")
    print("\n" + "="*60)
    print(f"✅ Audio chunk captured: {duration:.2f} seconds")
    print("="*60 + "\n")


def main():
    """Run VAD debug test"""
    print("\n" + "="*60)
    print("Voice Activity Detection Debug Tool")
    print("="*60)

    # Load configuration
    config = Config()

    print(f"\nCurrent VAD Configuration:")
    print(f"  Device Index: {config.whisper_device_index} (None = auto-detect)")
    print(f"  Silence Duration: {config.whisper_silence_duration}s")
    print(f"  Energy Threshold: {config.whisper_energy_threshold}")
    print(f"  Min Audio Length: {config.whisper_min_audio_length}s")
    print("\n" + "="*60)
    print("Starting audio capture... Speak to test VAD!")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    # Create audio capture with configured parameters
    audio_capture = AudioCapture(
        on_audio_chunk=on_audio_chunk,
        sample_rate=16000,
        device_index=config.whisper_device_index,
        silence_duration=config.whisper_silence_duration,
        energy_threshold=config.whisper_energy_threshold
    )

    try:
        audio_capture.start()

        # Keep running until interrupted
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopping...")
        audio_capture.stop()
        print("Done!")


if __name__ == "__main__":
    main()
