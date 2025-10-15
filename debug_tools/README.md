# Debug Tools for Dictation Manager

This directory contains debugging and diagnostic tools for the Whisper backend.

## Available Tools

### 1. debug_vad.py - Voice Activity Detection Tester

Real-time VAD testing and calibration tool. Shows live audio energy levels and helps tune VAD parameters.

**Usage:**
```bash
cd /home/tho/soft/ai/dictation
source venv/bin/activate
python debug_tools/debug_vad.py
```

**What it does:**
- Captures audio from your microphone
- Shows real-time energy levels
- Displays when speech is detected
- Shows silence counter
- Helps you find optimal `WHISPER_ENERGY_THRESHOLD` value

**Example output:**
```
Speech started (energy-based): energy=0.2596 > threshold=0.0040
Silence detected: 1/26 frames (energy=0.0030)
...
Speech ended (energy-based): 55296 samples (3.46s)
✅ Audio chunk captured: 3.46 seconds
```

**Use this when:**
- VAD is too sensitive (detects background noise)
- VAD doesn't detect your voice
- Speech is cut off too early
- You want to optimize for your microphone

---

### 2. list_audio_devices.py - Audio Device Discovery

Lists all available audio input devices on your system.

**Usage:**
```bash
cd /home/tho/soft/ai/dictation
source venv/bin/activate
python debug_tools/list_audio_devices.py
```

**What it does:**
- Scans for all audio input devices
- Shows device index, name, channels, and sample rate
- Identifies the default input device
- Helps you find the correct `WHISPER_DEVICE_INDEX`

**Example output:**
```
Index: 10
  Name: pipewire
  Input Channels: 64
  Sample Rate: 44100 Hz
  Host API: ALSA

Index: 12
  Name: default
  Input Channels: 64
  Sample Rate: 44100 Hz
  Host API: ALSA
  ** DEFAULT INPUT DEVICE **
```

**Use this when:**
- Whisper is not capturing audio
- You have multiple microphones
- You want to use a specific audio device
- Auto-detection picks the wrong device

---

## Quick Reference

### Tuning VAD Parameters

Based on debug_vad.py output, adjust these in `.env`:

| Symptom | Parameter | Adjustment |
|---------|-----------|------------|
| **Too sensitive** (noise triggers) | `WHISPER_ENERGY_THRESHOLD` | Increase to 0.005-0.01 |
| **Not sensitive** (doesn't detect voice) | `WHISPER_ENERGY_THRESHOLD` | Decrease to 0.001-0.002 |
| **Speech cut off early** | `WHISPER_SILENCE_DURATION` | Increase to 1.0-1.5 |
| **Slow to process** | `WHISPER_SILENCE_DURATION` | Decrease to 0.5-0.6 |
| **Short words ignored** | `WHISPER_MIN_AUDIO_LENGTH` | Decrease to 0.2 |

### Selecting Audio Device

Based on list_audio_devices.py output, set in `.env`:

```bash
# Use specific device (e.g., index 10)
WHISPER_DEVICE_INDEX=10

# Or leave empty for auto-detection
WHISPER_DEVICE_INDEX=
```

---

## Common Debugging Workflows

### Workflow 1: Microphone Not Working

1. Run `list_audio_devices.py` to find devices
2. Note the index of your microphone
3. Set `WHISPER_DEVICE_INDEX=<index>` in `.env`
4. Test with `debug_vad.py`
5. Restart the app

### Workflow 2: Background Noise Issues

1. Run `debug_vad.py`
2. Stay silent and note background energy levels
3. Set `WHISPER_ENERGY_THRESHOLD` to 2x the background noise
4. Test by speaking - should see "Speech started"
5. Adjust until optimal

### Workflow 3: Speech Detection Not Working

1. Run `debug_vad.py`
2. Speak and note energy levels
3. If no "Speech started", lower `WHISPER_ENERGY_THRESHOLD`
4. If cuts off early, increase `WHISPER_SILENCE_DURATION`
5. Test until speech is captured reliably

---

## Requirements

These tools require the same virtual environment as the main application:

```bash
source venv/bin/activate
```

Dependencies (already installed if Whisper backend is installed):
- pyaudio
- numpy
- faster-whisper

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pyaudio'"

**Solution:**
```bash
source venv/bin/activate
pip install pyaudio
```

### ALSA Warnings

ALSA warnings are normal and can be ignored:
```
ALSA lib pcm_dsnoop.c:567:(snd_pcm_dsnoop_open) unable to open slave
```

These don't affect functionality.

### No Audio Devices Found

**Check:**
```bash
# Test if PulseAudio is running
pactl info

# List devices manually
pactl list sources short
```

---

## See Also

- [Whisper Backend Documentation](../docs/ai/feat/1_whisper/)
- [Configuration Reference](../.env.example)
- [Main README](../README_WHISPER.md)
