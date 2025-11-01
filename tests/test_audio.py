#!/usr/bin/env python3
"""
Test script to verify microphone is working with PyAudio and VAD
"""

import pyaudio
import numpy as np
import webrtcvad
import sys
import time

def test_microphone():
    """Test microphone capture and VAD detection"""

    # Audio settings
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 480  # 30ms at 16kHz for VAD
    FORMAT = pyaudio.paInt16

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # List available input devices
    print("=" * 60)
    print("AVAILABLE INPUT DEVICES:")
    print("=" * 60)
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            # Convert bytes to string if needed (macOS compatibility)
            device_name = info['name']
            if isinstance(device_name, bytes):
                device_name = device_name.decode('utf-8', errors='replace')

            print(f"  [{i}] {device_name}")
            print(f"      Channels: {info['maxInputChannels']}")
            print(f"      Sample Rate: {int(info['defaultSampleRate'])}Hz")

    print("\n" + "=" * 60)
    print("TESTING MICROPHONE (default device)")
    print("=" * 60)
    print("Speak into your microphone for 10 seconds...")
    print("Press Ctrl+C to stop\n")

    # Open stream
    stream = p.open(
        format=FORMAT,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    # Initialize VAD
    vad = webrtcvad.Vad(2)  # Sensitivity 0-3 (2 = normal)

    # Test for 10 seconds
    start_time = time.time()
    speech_detected_count = 0
    total_chunks = 0
    max_amplitude = 0

    try:
        while time.time() - start_time < 10:
            # Read audio chunk
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)

            # Convert to numpy array for analysis
            audio_array = np.frombuffer(data, dtype=np.int16)
            amplitude = np.abs(audio_array).mean()
            max_amplitude = max(max_amplitude, amplitude)

            # Test VAD
            is_speech = vad.is_speech(data, SAMPLE_RATE)

            total_chunks += 1
            if is_speech:
                speech_detected_count += 1
                print(f"✓ SPEECH DETECTED - Amplitude: {amplitude:.1f}")
            else:
                # Only show amplitude every 10 chunks to avoid spam
                if total_chunks % 10 == 0:
                    print(f"  Silence - Amplitude: {amplitude:.1f}")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()

        # Results
        print("\n" + "=" * 60)
        print("TEST RESULTS:")
        print("=" * 60)
        print(f"Total chunks processed: {total_chunks}")
        print(f"Speech detected in: {speech_detected_count} chunks ({speech_detected_count/max(total_chunks,1)*100:.1f}%)")
        print(f"Max amplitude: {max_amplitude:.1f}")
        print(f"Energy threshold in settings: 0.008 (normalized: {0.008 * 32768:.1f})")

        if speech_detected_count == 0:
            print("\n❌ NO SPEECH DETECTED!")
            print("Possible issues:")
            print("  1. Wrong microphone selected (try device_index in settings)")
            print("  2. Microphone volume too low")
            print("  3. VAD sensitivity too low (try higher sensitivity)")
            print(f"  4. Max amplitude ({max_amplitude:.1f}) is very low - check mic volume")
        elif speech_detected_count < total_chunks * 0.1:
            print("\n⚠️  VERY LITTLE SPEECH DETECTED")
            print("  - Your microphone might be too quiet")
            print("  - Try increasing microphone volume in system settings")
        else:
            print("\n✓ MICROPHONE WORKING CORRECTLY")

if __name__ == "__main__":
    test_microphone()
