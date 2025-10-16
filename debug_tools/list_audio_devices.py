#!/usr/bin/env python3
"""
List all available audio input devices.
Use this to find the correct device index for WHISPER_DEVICE_INDEX in .env
"""

import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / "venv/lib/python3.11/site-packages"))

try:
    import pyaudio
except ImportError:
    print("ERROR: pyaudio not installed")
    print("Run: source venv/bin/activate && pip install pyaudio")
    sys.exit(1)


def list_audio_devices():
    """List all available audio input devices"""
    p = pyaudio.PyAudio()

    print("\n" + "="*60)
    print("Available Audio Input Devices")
    print("="*60 + "\n")

    input_devices = []

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)

        # Only show input devices
        if info['maxInputChannels'] > 0:
            input_devices.append((i, info))
            print(f"Index: {i}")
            print(f"  Name: {info['name']}")
            print(f"  Input Channels: {info['maxInputChannels']}")
            print(f"  Sample Rate: {int(info['defaultSampleRate'])} Hz")
            print(f"  Host API: {p.get_host_api_info_by_index(info['hostApi'])['name']}")

            # Check if it's the default
            try:
                default_input = p.get_default_input_device_info()
                if i == default_input['index']:
                    print(f"  ** DEFAULT INPUT DEVICE **")
            except:
                pass

            print()

    p.terminate()

    print("="*60)
    print(f"Found {len(input_devices)} input device(s)")
    print("="*60)
    print("\nTo use a specific device, add to .env:")
    print("WHISPER_DEVICE_INDEX=<index>")
    print("\nFor auto-detection, leave it empty:")
    print("WHISPER_DEVICE_INDEX=")
    print()


if __name__ == "__main__":
    list_audio_devices()
